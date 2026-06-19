#!/usr/bin/env python3
"""
Rappel de chloration — minuterie « quand remettre du chlore ».

L'utilisateur signale, via l'interface web, chaque ajout de chlore
(POST /api/chlore → marquer_ajout()). On mémorise l'instant du dernier ajout
dans un petit fichier d'état (etat_chlore.json), SÉPARÉ de config.json :
l'intervalle souhaité est un paramètre (config.json, voir config.py), tandis
que la date du dernier ajout est un ÉTAT runtime qui doit survivre aux
redémarrages / plantages de l'application.

statut(intervalle_jours) calcule, à partir de cet état et de l'intervalle,
si la chloration est due (et le temps restant) — consommé par l'interface
web (bannière d'alerte + section Chloration).

Aucune dépendance externe.
"""

import json
import os
import threading
import time

CHEMIN_ETAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "etat_chlore.json")

_verrou = threading.Lock()


def _lire():
    try:
        with open(CHEMIN_ETAT, "r", encoding="utf-8") as f:
            donnees = json.load(f)
        return donnees if isinstance(donnees, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def marquer_ajout(maintenant=None):
    """Enregistre « du chlore vient d'être ajouté » (maintenant par défaut).

    Renvoie le timestamp Unix enregistré."""
    ts = time.time() if maintenant is None else float(maintenant)
    with _verrou:
        with open(CHEMIN_ETAT, "w", encoding="utf-8") as f:
            json.dump({"dernier_ajout_ts": ts}, f, indent=2)
            f.write("\n")
    return ts


def statut(intervalle_jours):
    """État de la chloration pour l'interface.

    Renvoie un dict : dernier_ajout_ts, prochaine_echeance_ts (None si jamais),
    restant_s (secondes avant échéance ; négatif si en retard), du (bool),
    jamais (bool : aucun ajout encore enregistré), intervalle_jours.
    """
    with _verrou:
        donnees = _lire()

    intervalle_s = max(0.0, float(intervalle_jours) * 86400)
    dernier = donnees.get("dernier_ajout_ts")
    maintenant = time.time()

    if not isinstance(dernier, (int, float)):
        # Jamais enregistré : considéré « à faire » pour inviter à un premier ajout.
        return {
            "jamais": True,
            "du": True,
            "dernier_ajout_ts": None,
            "prochaine_echeance_ts": None,
            "restant_s": 0,
            "intervalle_jours": float(intervalle_jours),
        }

    echeance = dernier + intervalle_s
    restant = echeance - maintenant
    return {
        "jamais": False,
        "du": restant <= 0,
        "dernier_ajout_ts": dernier,
        "prochaine_echeance_ts": echeance,
        "restant_s": restant,
        "intervalle_jours": float(intervalle_jours),
    }
