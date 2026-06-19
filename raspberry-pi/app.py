#!/usr/bin/env python3
"""
Interface web du Raspberry Pi — contrôle local du système de filtration.

Entrée principale du système : ce serveur Flask détient l'UNIQUE liaison
série avec l'Arduino (un seul processus peut ouvrir /dev/ttyACM0) et la
partage avec l'orchestrateur. Il expose :

  - l'état du système (polling)
  - le déclenchement des séquences + un arrêt d'urgence
  - un mode manuel valve-par-valve / moteur (débogage / câblage)
  - l'édition des délais et paramètres (config.json)
  - le téléversement d'un nouveau firmware .ino et le flashage de l'Arduino

Réseau : LAN uniquement, sans authentification (réseau domestique). L'accès
Internet distant reste hors scope (voir doc « Accès distant »).

Lancement :
    python3 app.py
    # test de l'UI sans Arduino :
    PISCINE_SIMULATION=1 python3 app.py
Puis ouvrir http://<adresse-du-pi>:8080
"""

import os
import threading

from flask import Flask, jsonify, render_template, request

import config as config_module
import flashage
from piscine import LiaisonArduino, Orchestrateur, timeline_sequence

PORT_WEB = int(os.environ.get("PISCINE_PORT_WEB", "8080"))

app = Flask(__name__)


@app.after_request
def _empecher_cache(reponse):
    # Évite que les navigateurs gardent en cache une ancienne version de la
    # page/JS/CSS : sans ça, deux appareils peuvent afficher des versions
    # différentes de l'interface après une mise à jour du code.
    reponse.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return reponse


arduino = LiaisonArduino()
orchestrateur = Orchestrateur(arduino)


def _reponse(succes, message, code=200):
    return jsonify({"ok": succes, "message": message}), (code if succes else 400)


# ===================== Page =====================

@app.get("/")
def index():
    return render_template("index.html")


# ===================== État =====================

@app.get("/api/etat")
def api_etat():
    return jsonify(orchestrateur.etat_courant())


# ===================== Paramètres =====================

@app.get("/api/config")
def api_config_lire():
    return jsonify(config_module.charger().to_dict())


@app.post("/api/config")
def api_config_ecrire():
    donnees = request.get_json(silent=True)
    if not isinstance(donnees, dict):
        return _reponse(False, "Corps JSON attendu")
    try:
        nouvelle = config_module.sauvegarder(donnees)
    except config_module.ErreurConfig as e:
        return _reponse(False, str(e))
    orchestrateur.recharger_config()
    return jsonify({"ok": True, "message": "Paramètres enregistrés",
                    "config": nouvelle.to_dict()})


# ===================== Contrôle (séquences) =====================

@app.post("/api/sequence/<nom>")
def api_sequence(nom):
    succes, message = orchestrateur.lancer_sequence(nom)
    return _reponse(succes, message)


@app.get("/api/sequence/<nom>/timeline")
def api_sequence_timeline(nom):
    """Jalons (nom + instant en secondes) calculés depuis la config courante,
    pour afficher la frise chronologique + barre de progression côté UI."""
    timeline = timeline_sequence(nom, orchestrateur.config)
    if timeline is None:
        return _reponse(False, f"Séquence inconnue : « {nom} »", 404)
    return jsonify(timeline)


@app.post("/api/arret")
def api_arret():
    succes, message = orchestrateur.arret_urgence()
    return _reponse(succes, message)


# ===================== Contrôle manuel =====================

@app.post("/api/manuel/valve")
def api_manuel_valve():
    donnees = request.get_json(silent=True) or {}
    valve = donnees.get("valve")
    action = donnees.get("action")
    duree_ms = donnees.get("duree_ms", 0)
    try:
        duree_ms = int(duree_ms)
    except (TypeError, ValueError):
        return _reponse(False, "duree_ms invalide")
    succes, message = orchestrateur.commande_manuelle_valve(valve, action, duree_ms)
    return _reponse(succes, message)


@app.post("/api/manuel/moteur")
def api_manuel_moteur():
    donnees = request.get_json(silent=True) or {}
    action = donnees.get("action")
    succes, message = orchestrateur.commande_manuelle_moteur(action)
    return _reponse(succes, message)


@app.get("/api/manuel/boutons")
def api_manuel_boutons():
    etat = orchestrateur.lire_boutons()
    if etat is None:
        return _reponse(False, "Pas de réponse de l'Arduino")
    return jsonify({"ok": True, "boutons": etat})


# ===================== Firmware =====================

@app.post("/api/firmware")
def api_firmware_upload():
    fichier = request.files.get("firmware")
    if fichier is None or not fichier.filename:
        return _reponse(False, "Aucun fichier reçu")
    if not fichier.filename.endswith(".ino"):
        return _reponse(False, "Le fichier doit être un sketch .ino")
    flashage.stocker_ino(fichier.read())
    return jsonify({"ok": True, "message": f"Firmware « {fichier.filename} » reçu, prêt à flasher"})


@app.post("/api/firmware/flash")
def api_firmware_flash():
    chemin_ino = os.path.join(flashage.DOSSIER_STAGING, flashage.NOM_SKETCH + ".ino")
    if not os.path.exists(chemin_ino):
        return _reponse(False, "Aucun firmware téléversé — choisir un fichier .ino d'abord")
    succes, log = flashage.flasher(flashage.DOSSIER_STAGING, arduino, orchestrateur)
    return jsonify({"ok": succes, "log": log})


# ===================== Démarrage =====================

def demarrer():
    # Écoute des boutons physiques (vert/rouge) en arrière-plan.
    threading.Thread(target=orchestrateur.boucle, daemon=True).start()
    # Sonde périodique de l'état des boutons (pour l'affichage dans l'UI).
    threading.Thread(target=orchestrateur.moniteur_boutons, daemon=True).start()
    # Récupération d'état : on adopte l'état réel rapporté par l'Arduino (avec
    # homing pour une position certaine) au lieu de tout couper. Repli sûr sur
    # arret_initial() si l'Arduino ne répond pas. Voir Orchestrateur.recuperer_etat.
    orchestrateur.recuperer_etat()


if __name__ == "__main__":
    demarrer()
    # use_reloader=False : un seul processus doit détenir le port série.
    app.run(host="0.0.0.0", port=PORT_WEB, threaded=True, use_reloader=False)
