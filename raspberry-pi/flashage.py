#!/usr/bin/env python3
"""
Reprogrammation de l'Arduino depuis le Raspberry Pi, via arduino-cli.

Le firmware (.ino) téléversé depuis l'interface web est compilé puis flashé
sur l'Arduino à travers la même liaison USB que la communication série. Comme
arduino-cli a besoin d'un accès EXCLUSIF au port, on libère d'abord la liaison
série de l'application (orchestrateur en pause + port fermé), on flashe, puis
on rouvre tout.

Prérequis sur le Pi (voir doc « Interface Web (Pi) ») :
    arduino-cli core install arduino:avr
    arduino-cli lib install ArduinoJson
"""

import os
import shutil
import subprocess

FQBN = "arduino:avr:uno"

# Dossier de staging du sketch reçu. arduino-cli impose que le fichier .ino
# principal porte le même nom que son dossier parent.
DOSSIER_STAGING = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firmware_recu")
NOM_SKETCH = "firmware_recu"


def stocker_ino(contenu_octets):
    """Écrit le .ino reçu dans le dossier de staging ; renvoie le chemin du sketch."""
    os.makedirs(DOSSIER_STAGING, exist_ok=True)
    chemin_ino = os.path.join(DOSSIER_STAGING, NOM_SKETCH + ".ino")
    with open(chemin_ino, "wb") as f:
        f.write(contenu_octets)
    return DOSSIER_STAGING


def _executer(commande):
    """Lance une commande, renvoie (code_retour, sortie_combinée)."""
    try:
        resultat = subprocess.run(
            commande,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        return resultat.returncode, resultat.stdout
    except FileNotFoundError:
        return 127, (
            "arduino-cli introuvable. Installer arduino-cli sur le Pi, puis :\n"
            "  arduino-cli core install arduino:avr\n"
            "  arduino-cli lib install ArduinoJson\n"
        )
    except subprocess.TimeoutExpired:
        return 124, "Délai dépassé pendant la compilation/le téléversement."


def flasher(dossier_sketch, arduino, orchestrateur):
    """Compile et téléverse `dossier_sketch` sur l'Arduino.

    Met l'orchestrateur en pause et ferme la liaison série le temps du
    flashage, puis rouvre tout. Renvoie (succes: bool, log: str).
    """
    journal = []
    orchestrateur.pause_pour_flashage()
    port = arduino.port
    simulation = arduino.simulation
    arduino.fermer()
    try:
        if simulation:
            journal.append("[SIMULATION] flashage simulé — aucune commande réelle exécutée.")
            return True, "\n".join(journal)

        journal.append(f"$ arduino-cli compile --fqbn {FQBN} {dossier_sketch}")
        code, sortie = _executer(["arduino-cli", "compile", "--fqbn", FQBN, dossier_sketch])
        journal.append(sortie.rstrip())
        if code != 0:
            journal.append(f"Échec de la compilation (code {code}).")
            return False, "\n".join(journal)

        journal.append(f"$ arduino-cli upload -p {port} --fqbn {FQBN} {dossier_sketch}")
        code, sortie = _executer(
            ["arduino-cli", "upload", "-p", port, "--fqbn", FQBN, dossier_sketch]
        )
        journal.append(sortie.rstrip())
        if code != 0:
            journal.append(f"Échec du téléversement (code {code}).")
            return False, "\n".join(journal)

        journal.append("Téléversement réussi.")
        return True, "\n".join(journal)
    finally:
        # Toujours rendre la main à l'application, même en cas d'échec.
        try:
            arduino.rouvrir()
        except Exception as e:  # noqa: BLE001
            journal.append(f"[AVERTISSEMENT] réouverture du port échouée : {e}")
        orchestrateur.reprise_apres_flashage()


def nettoyer_staging():
    """Supprime le dossier de staging (optionnel)."""
    shutil.rmtree(DOSSIER_STAGING, ignore_errors=True)
