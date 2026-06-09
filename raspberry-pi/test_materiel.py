#!/usr/bin/env python3
"""
Test manuel du matériel — menu interactif pour vérifier individuellement
chaque sortie pilotée par l'Arduino (valves, moteur) et chaque entrée
(boutons), SANS passer par la logique de séquencement du programme
principal (piscine.py).

Utile pour valider le câblage et le firmware avant de tester les séquences
complètes : ouvrir/fermer/arrêter chaque valve isolément, démarrer/arrêter
le moteur, lire l'état des boutons, observer les appuis en temps réel.

Réutilise LiaisonArduino (et donc le protocole JSON à 115200 bauds) du
programme principal — voir Communication Série et Implémentation des
programmes dans la documentation Obsidian.
"""

import time

import config as config_module
from piscine import NOMS_VALVES, LiaisonArduino

# Course complète lue depuis la configuration (voir config.json / config.py).
COURSE_COMPLETE_MS = int(config_module.charger().course_complete_ms)


def demander_valve():
    print("Valves disponibles : " + ", ".join(NOMS_VALVES))
    nom = input("Nom de la valve : ").strip()
    if nom not in NOMS_VALVES:
        print(f"Valve inconnue : « {nom} »")
        return None
    return nom


def demander_duree_ms():
    course_s = COURSE_COMPLETE_MS / 1000
    brut = input(f"Durée en secondes (Entrée = {course_s:g} s = course complète) : ").strip()
    if not brut:
        return COURSE_COMPLETE_MS
    try:
        return int(float(brut) * 1000)
    except ValueError:
        print("Valeur invalide — course complète utilisée.")
        return COURSE_COMPLETE_MS


def afficher_evenements_en_attente(arduino):
    """Affiche, sans bloquer, tout message déjà reçu de l'Arduino."""
    while not arduino.evenements.empty():
        print(f"  >>> reçu de l'Arduino : {arduino.evenements.get_nowait()}")


# ===================== Actions du menu =====================

def test_ouvrir_valve(arduino):
    nom = demander_valve()
    if nom is None:
        return
    duree_ms = demander_duree_ms()
    print(f"→ Ouverture de « {nom} » pendant {duree_ms} ms...")
    arduino.ouvrir_valve(nom, duree_ms)


def test_fermer_valve(arduino):
    nom = demander_valve()
    if nom is None:
        return
    duree_ms = demander_duree_ms()
    print(f"→ Fermeture de « {nom} » pendant {duree_ms} ms...")
    arduino.fermer_valve(nom, duree_ms)


def test_arreter_valve(arduino):
    nom = demander_valve()
    if nom is None:
        return
    print(f"→ Arrêt immédiat de « {nom} » (fige la position courante, 0/0)...")
    arduino.arreter_valve(nom)


def test_demarrer_moteur(arduino):
    print("→ Démarrage du moteur (relais activé)...")
    arduino.demarrer_moteur()


def test_arreter_moteur(arduino):
    print("→ Arrêt du moteur (relais désactivé)...")
    arduino.arreter_moteur()


def test_etat_boutons(arduino):
    print("→ Demande de l'état courant des boutons...")
    arduino.demander_etat_boutons()
    try:
        reponse = arduino.evenements.get(timeout=2)
        print(f"  >>> état reçu : {reponse}")
    except Exception:
        print("  (aucune réponse reçue — vérifier la connexion série)")


def test_ecouter_boutons(arduino):
    duree_s = 15
    print(f"→ Écoute des appuis sur les boutons pendant {duree_s} s.")
    print("  Appuyez sur le bouton vert, rouge ou bleu pour voir l'événement apparaître...")
    echeance = time.monotonic() + duree_s
    while time.monotonic() < echeance:
        try:
            evenement = arduino.evenements.get(timeout=0.5)
        except Exception:
            continue
        print(f"  >>> reçu : {evenement}")
    print("  Fin de l'écoute.")


MENU = """
========== Test matériel — Piscine ==========
 1. Ouvrir une valve
 2. Fermer une valve
 3. Arrêter une valve (figer la position)
 4. Démarrer le moteur
 5. Arrêter le moteur
 6. Lire l'état courant des boutons
 7. Écouter les appuis sur les boutons (15 s)
 0. Quitter
==============================================
"""

ACTIONS = {
    "1": test_ouvrir_valve,
    "2": test_fermer_valve,
    "3": test_arreter_valve,
    "4": test_demarrer_moteur,
    "5": test_arreter_moteur,
    "6": test_etat_boutons,
    "7": test_ecouter_boutons,
}


def main():
    arduino = LiaisonArduino()
    print("Connexion série établie avec l'Arduino (115200 bauds).")
    print("Rappel : ce script ne lance AUCUNE séquence — il envoie des commandes primitives isolées.")

    while True:
        afficher_evenements_en_attente(arduino)
        print(MENU)
        choix = input("Choix : ").strip()

        if choix == "0":
            break

        action = ACTIONS.get(choix)
        if action is None:
            print("Choix invalide.")
            continue

        action(arduino)
        time.sleep(0.2)
        afficher_evenements_en_attente(arduino)


if __name__ == "__main__":
    main()
