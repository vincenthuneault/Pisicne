#!/usr/bin/env python3
"""
Configuration des séquences — délais et paramètres ajustables.

Ces valeurs étaient autrefois codées en dur dans piscine.py ; elles sont
maintenant externalisées dans config.json afin d'être modifiables depuis
l'interface web du Raspberry Pi (voir app.py). Toutes les durées de
séquence (course des valves, attentes, duty cycle de priming, durée de
l'ajout d'eau) sont lues ici.

Le système reste en boucle ouverte : ces valeurs sont fixes et déterminées
à l'avance (voir la doc Obsidian « Contrôle en boucle ouverte »).
"""

import json
import os
import threading

CHEMIN_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Valeurs par défaut = valeurs historiques de piscine.py. Servent de repli si
# config.json est absent, incomplet ou invalide.
DEFAUTS = {
    "course_complete_ms": 10000,
    "priming": {
        "amorcage_initial_s": 15,
        "stabilisation_s": 10,
        "nb_cycles": 10,
        "impulsion_ouverture_ms": 500,
        "impulsion_fermeture_ms": 500,
    },
    "ajout_eau": {
        "impulsion_ouverture_ms": 1000,
        "duree_maintien_s": 3600,
    },
}

# Champs entiers (nb de cycles) vs champs pouvant être décimaux (durées).
_CHAMPS_ENTIERS = {("priming", "nb_cycles")}

_verrou = threading.Lock()


class ErreurConfig(ValueError):
    """Paramètre manquant, de mauvais type ou hors bornes."""


class Config:
    """Vue pratique (accès par attribut) sur le dictionnaire de configuration."""

    def __init__(self, donnees):
        self.donnees = donnees

    @property
    def course_complete_ms(self):
        return self.donnees["course_complete_ms"]

    @property
    def priming(self):
        return self.donnees["priming"]

    @property
    def ajout_eau(self):
        return self.donnees["ajout_eau"]

    def to_dict(self):
        return json.loads(json.dumps(self.donnees))  # copie profonde


def _fusionner_defauts(donnees):
    """Complète `donnees` avec les valeurs par défaut manquantes (tolérant)."""
    resultat = json.loads(json.dumps(DEFAUTS))
    if isinstance(donnees, dict):
        for cle, valeur in donnees.items():
            if isinstance(valeur, dict) and isinstance(resultat.get(cle), dict):
                resultat[cle].update(valeur)
            else:
                resultat[cle] = valeur
    return resultat


def _valider(donnees):
    """Vérifie présence, type numérique et positivité de chaque paramètre.

    Renvoie un dictionnaire normalisé (entiers/flottants), lève ErreurConfig
    en cas de problème. On valide sur la structure des DEFAUTS, ce qui ignore
    aussi les clés inconnues.
    """
    normalise = json.loads(json.dumps(DEFAUTS))

    def lire(chemin, conteneur_def, conteneur_src, conteneur_dst):
        for cle, defaut in conteneur_def.items():
            chemin_cle = chemin + (cle,)
            if isinstance(defaut, dict):
                source = conteneur_src.get(cle, {}) if isinstance(conteneur_src, dict) else {}
                lire(chemin_cle, defaut, source, conteneur_dst[cle])
                continue
            brut = conteneur_src.get(cle, defaut) if isinstance(conteneur_src, dict) else defaut
            if isinstance(brut, bool) or not isinstance(brut, (int, float)):
                raise ErreurConfig(f"« {'.'.join(chemin_cle)} » doit être un nombre")
            if brut <= 0:
                raise ErreurConfig(f"« {'.'.join(chemin_cle)} » doit être > 0")
            conteneur_dst[cle] = int(brut) if chemin_cle in _CHAMPS_ENTIERS else float(brut)

    lire((), DEFAUTS, donnees, normalise)
    return normalise


def charger():
    """Charge config.json (repli sur les valeurs par défaut si absent/invalide)."""
    with _verrou:
        try:
            with open(CHEMIN_CONFIG, "r", encoding="utf-8") as f:
                brut = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            brut = {}
        donnees = _fusionner_defauts(brut)
        try:
            donnees = _valider(donnees)
        except ErreurConfig:
            donnees = json.loads(json.dumps(DEFAUTS))
        return Config(donnees)


def sauvegarder(donnees):
    """Valide puis écrit la configuration ; renvoie le Config normalisé.

    Lève ErreurConfig si un paramètre est invalide (rien n'est écrit).
    """
    normalise = _valider(donnees)
    with _verrou:
        with open(CHEMIN_CONFIG, "w", encoding="utf-8") as f:
            json.dump(normalise, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return Config(normalise)
