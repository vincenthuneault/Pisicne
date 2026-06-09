#!/usr/bin/env python3
"""
Programme Raspberry Pi — cerveau du système de filtration de piscine.

C'est ICI que vit toute la logique : décision de la séquence à exécuter,
minutage (délais, duty cycles, durée d'une heure), suivi de l'état global
du système (EN_MARCHE / ETEINT) et gestion de la priorité absolue du
bouton rouge (interruption immédiate de toute séquence en cours).

L'Arduino n'est qu'une interface matérielle « bête » : il exécute des
commandes primitives et rapporte les appuis sur les boutons en JSON, via
liaison série à 115200 bauds. Voir la documentation Obsidian : Architecture,
Programme Raspberry Pi (Python), Communication Série.

Les délais et paramètres des séquences sont externalisés dans config.json
(voir config.py) et modifiables via l'interface web (voir app.py).

Ce module est importable : il n'ouvre la liaison série et ne lance aucune
séquence à l'import. L'entrée principale du système est app.py (serveur web +
orchestrateur). main() ci-dessous reste un mode de repli « boutons seuls »,
sans interface web.

Dépendance : pyserial (pip install pyserial)
"""

import json
import os
import queue
import sys
import threading
import time

import serial

import config as config_module

# Port série de l'Arduino. Surchargé par la variable d'environnement
# PISCINE_PORT_SERIE (ex. /dev/ttyUSB0 pour un Arduino à adaptateur CH340,
# /dev/ttyACM0 pour un Uno officiel).
PORT_SERIE = os.environ.get("PISCINE_PORT_SERIE", "/dev/ttyACM0")
BAUDS = 115200

NOMS_VALVES = ("ecumoire", "drain", "alimentation", "retour")

ETEINT = "ETEINT"
EN_MARCHE = "EN_MARCHE"

# Mode simulation : aucune liaison série réelle (pour tester l'UI sans Arduino).
SIMULATION = os.environ.get("PISCINE_SIMULATION") == "1"


# ===================== État global du système =====================
#
# Par défaut ETEINT : en cas de plantage/redémarrage, le système doit
# repartir dans un état sûr (voir Programme Raspberry Pi (Python) > État
# du système).

class EtatSysteme:
    def __init__(self):
        self._etat = ETEINT
        self._verrou = threading.Lock()

    def obtenir(self):
        with self._verrou:
            return self._etat

    def definir(self, nouvel_etat):
        with self._verrou:
            self._etat = nouvel_etat


# ===================== Suivi (estimé) de la position des valves =====================
#
# Le système est en BOUCLE OUVERTE : aucun capteur de position. On ESTIME donc
# la position de chaque valve (0 % = fermée, 100 % = ouverte) par « dead
# reckoning » à partir des commandes envoyées (sens + durée) et du temps
# écoulé, en se basant sur la course complète (course_complete_ms). C'est une
# ESTIMATION logicielle, pas une mesure — affichée comme telle dans l'UI.

class SuiviValves:
    def __init__(self, course_complete_ms=15000):
        self.course_s = max(0.1, course_complete_ms / 1000)
        self._verrou = threading.Lock()
        self._v = {nom: {"pos": 0.0, "dir": "arret", "t0": 0.0, "t_fin": 0.0}
                   for nom in NOMS_VALVES}

    def definir_course(self, course_complete_ms):
        with self._verrou:
            self.course_s = max(0.1, course_complete_ms / 1000)

    def _pos_instant(self, e, maintenant):
        """Position courante (0..1) sans rien muter."""
        if e["dir"] == "arret":
            return e["pos"]
        borne = maintenant if e["t_fin"] == 0.0 else min(maintenant, e["t_fin"])
        delta = max(0.0, borne - e["t0"]) / self.course_s
        if e["dir"] == "ouverture":
            return min(1.0, e["pos"] + delta)
        return max(0.0, e["pos"] - delta)

    def _figer(self, e, maintenant):
        e["pos"] = max(0.0, min(1.0, self._pos_instant(e, maintenant)))
        e["dir"] = "arret"
        e["t0"] = 0.0
        e["t_fin"] = 0.0

    def demarrer(self, nom, direction, duree_ms):
        if nom not in self._v:
            return
        maintenant = time.monotonic()
        with self._verrou:
            e = self._v[nom]
            e["pos"] = self._pos_instant(e, maintenant)  # repart de la position courante
            e["dir"] = direction
            e["t0"] = maintenant
            e["t_fin"] = (maintenant + duree_ms / 1000) if duree_ms > 0 else 0.0

    def arreter(self, nom):
        if nom not in self._v:
            return
        maintenant = time.monotonic()
        with self._verrou:
            self._figer(self._v[nom], maintenant)

    def etat(self):
        """{nom: {"position": 0..100, "mouvement": "ouverture|fermeture|arret"}}."""
        maintenant = time.monotonic()
        with self._verrou:
            resultat = {}
            for nom, e in self._v.items():
                if e["dir"] != "arret":
                    p = self._pos_instant(e, maintenant)
                    fini = (e["t_fin"] != 0.0 and maintenant >= e["t_fin"]) or p <= 0.0 or p >= 1.0
                    if fini:
                        self._figer(e, maintenant)
                resultat[nom] = {
                    "position": round(self._pos_instant(e, maintenant) * 100),
                    "mouvement": e["dir"],
                }
            return resultat


# ===================== Liaison série JSON avec l'Arduino =====================

class LiaisonArduino:
    """Encapsule la communication série JSON avec l'Arduino.

    Un thread de lecture dédié dépile les lignes reçues et place les
    événements de bouton (ex. appuis) dans une file consommée par
    l'orchestrateur, afin de ne jamais bloquer sur Serial.readline(). Les
    réponses d'état des boutons ({"boutons": …}) sont routées séparément.

    Suit aussi, à titre estimé, la position des valves (SuiviValves) et l'état
    commandé du moteur, pour affichage dans l'interface web.

    Le port peut être fermé puis rouvert (fermer()/rouvrir()) pour libérer le
    port série le temps de reprogrammer l'Arduino (voir flashage.py).

    En mode simulation (PISCINE_SIMULATION=1), aucune série réelle n'est
    ouverte : les commandes sont simplement journalisées.
    """

    def __init__(self, port=PORT_SERIE, bauds=BAUDS, simulation=SIMULATION):
        self.port = port
        self.bauds = bauds
        self.simulation = simulation
        self.evenements = queue.Queue()
        self._reponses_boutons = queue.Queue()
        self.suivi = SuiviValves()
        self.moteur_actif = False
        self.dernier_etat_boutons = {"vert": False, "rouge": False}
        self._ser = None
        self._verrou_ecriture = threading.Lock()
        self._actif = False
        self._thread = None
        self.rouvrir()

    # --- Cycle de vie du port (utile pour le flashage) ---

    def rouvrir(self):
        """(Ré)ouvre le port série et (re)démarre le thread de lecture."""
        if self._actif:
            return
        if not self.simulation:
            self._ser = serial.Serial(self.port, self.bauds, timeout=1)
            # L'ouverture du port réinitialise l'Arduino (toggle DTR/RTS) : il
            # faut laisser le firmware redémarrer avant d'envoyer la moindre
            # commande, sinon les premières (ex. l'arrêt de sécurité) sont perdues.
            time.sleep(2)
        self._actif = True
        if not self.simulation:
            self._thread = threading.Thread(target=self._lire_en_continu, daemon=True)
            self._thread.start()

    def fermer(self):
        """Ferme le port série et arrête le thread de lecture (libère le port)."""
        self._actif = False
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
        self._thread = None
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None

    def _lire_en_continu(self):
        while self._actif:
            try:
                ligne = self._ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException:
                if not self._actif:
                    break
                continue
            except (OSError, AttributeError):
                break
            if not ligne:
                continue
            try:
                message = json.loads(ligne)
            except json.JSONDecodeError:
                continue
            if message.get("event") == "bouton":
                self.evenements.put(message)
            elif "boutons" in message:
                self._reponses_boutons.put(message["boutons"])

    def _envoyer(self, commande):
        if self.simulation:
            print(f"[SIMULATION] → Arduino : {json.dumps(commande)}", file=sys.stderr)
            return
        ligne = (json.dumps(commande) + "\n").encode("utf-8")
        with self._verrou_ecriture:
            if self._ser is None:
                raise RuntimeError("Liaison série fermée (flashage en cours ?)")
            self._ser.write(ligne)

    # --- Commandes primitives exposées par le firmware Arduino ---
    #     (chacune met aussi à jour le suivi de position / d'état)

    def ouvrir_valve(self, nom_valve, duree_ms=0):
        self.suivi.demarrer(nom_valve, "ouverture", int(duree_ms))
        self._envoyer({"cmd": "valve_ouvrir", "valve": nom_valve, "duree_ms": int(duree_ms)})

    def fermer_valve(self, nom_valve, duree_ms=0):
        self.suivi.demarrer(nom_valve, "fermeture", int(duree_ms))
        self._envoyer({"cmd": "valve_fermer", "valve": nom_valve, "duree_ms": int(duree_ms)})

    def arreter_valve(self, nom_valve):
        self.suivi.arreter(nom_valve)
        self._envoyer({"cmd": "valve_arreter", "valve": nom_valve})

    def demarrer_moteur(self):
        self.moteur_actif = True
        self._envoyer({"cmd": "moteur_demarrer"})

    def arreter_moteur(self):
        self.moteur_actif = False
        self._envoyer({"cmd": "moteur_arreter"})

    def lire_etat_boutons(self, timeout=2):
        """Demande et renvoie l'état courant des boutons ({"vert":bool, ...}).

        Met à jour le cache `dernier_etat_boutons`. Renvoie None si aucune
        réponse n'arrive.
        """
        if self.simulation:
            self.dernier_etat_boutons = {"vert": False, "rouge": False}
            return self.dernier_etat_boutons
        # Vider les réponses obsolètes éventuelles
        while not self._reponses_boutons.empty():
            self._reponses_boutons.get_nowait()
        self._envoyer({"cmd": "etat_boutons"})
        try:
            etat = self._reponses_boutons.get(timeout=timeout)
            self.dernier_etat_boutons = etat
            return etat
        except queue.Empty:
            return None


# ===================== Priorité absolue du bouton rouge =====================
#
# Les séquences ne sont PAS du code séquentiel bloquant : elles vérifient
# régulièrement (à chaque attente, à chaque étape) si une urgence a été
# déclenchée, et s'interrompent immédiatement le cas échéant — peu importe
# l'étape en cours. C'est ce mécanisme qui donne au bouton rouge sa
# priorité absolue.

class Interruption(Exception):
    """Levée pour abandonner une séquence suite à un appui sur le bouton rouge."""


class GestionnaireUrgence:
    def __init__(self):
        self._urgence = threading.Event()

    def declencher(self):
        self._urgence.set()

    def reinitialiser(self):
        self._urgence.clear()

    def verifier(self):
        if self._urgence.is_set():
            raise Interruption()

    def attendre(self, duree_s):
        """Attente interruptible : remplace time.sleep() dans les séquences.

        Découpée en petites tranches pour rester réactive à une urgence
        même pendant une longue attente (ex. l'heure d'ajout d'eau).
        """
        echeance = time.monotonic() + duree_s
        while True:
            self.verifier()
            reste = echeance - time.monotonic()
            if reste <= 0:
                return
            time.sleep(min(0.1, reste))


# ===================== Séquences =====================
#
# Chaque séquence reçoit la liaison Arduino, le gestionnaire d'urgence et la
# configuration (délais/paramètres lus depuis config.json). Elles lèvent
# Interruption (via urgence.attendre / urgence.verifier) si le bouton rouge
# est pressé en cours de route. Les étapes reproduisent celles décrites dans
# la documentation Obsidian.
#
# Remarque importante (corrigée après essais terrain) : la valve
# d'ALIMENTATION (réserve d'eau) ne doit PAS rester ouverte en fonctionnement
# normal — l'ouvrir vide la réserve. Elle ne sert que ponctuellement (priming,
# ajout d'eau). Le priming par à-coups (« jerk ») se fait sur le DRAIN DE FOND.

def sequence_demarrage(arduino, urgence, config):
    """Bouton vert : ouvrir les valves de filtration (PAS l'alimentation), puis moteur."""
    course_ms = config.course_complete_ms
    # Écumoire, drain de fond, retour — mais PAS l'alimentation (sinon la
    # réserve d'eau se vide).
    for nom in ("ecumoire", "drain", "retour"):
        arduino.ouvrir_valve(nom, course_ms)
    urgence.attendre(course_ms / 1000)
    arduino.demarrer_moteur()


def sequence_demarrage_avec_priming(arduino, urgence, config):
    """Bouton bleu, système éteint : démarrage avec ré-amorçage des tuyaux.

    Le priming par impulsions (« jerk ») se fait sur le DRAIN DE FOND.
    L'alimentation n'est ouverte que brièvement pour injecter de l'eau au
    départ, puis refermée (sinon la réserve d'eau se vide).
    """
    course_ms = config.course_complete_ms
    p = config.priming

    # 1) Amorçage initial : écumoire grande ouverte + injection d'eau (alimentation)
    arduino.ouvrir_valve("ecumoire", course_ms)
    arduino.ouvrir_valve("alimentation", course_ms)
    urgence.attendre(p["amorcage_initial_s"])

    # 1b) Refermer l'alimentation : l'injection d'eau initiale est faite
    #     (la laisser ouverte viderait la réserve d'eau).
    arduino.fermer_valve("alimentation", course_ms)
    urgence.attendre(course_ms / 1000)

    # 2) Ouverture complète de la valve de retour vers la piscine
    arduino.ouvrir_valve("retour", course_ms)
    urgence.attendre(course_ms / 1000)

    # 3) Démarrage du moteur (retour complètement ouvert)
    arduino.demarrer_moteur()

    # 4) Stabilisation, moteur en marche
    urgence.attendre(p["stabilisation_s"])

    # 5) Priming de la ligne du DRAIN DE FOND : impulsions d'ouverture puis
    #    fermeture (le drain part fermé ; on l'amorce progressivement par à-coups).
    for _ in range(p["nb_cycles"]):
        arduino.ouvrir_valve("drain", p["impulsion_ouverture_ms"])
        urgence.attendre(p["impulsion_ouverture_ms"] / 1000)
        arduino.fermer_valve("drain", p["impulsion_fermeture_ms"])
        urgence.attendre(p["impulsion_fermeture_ms"] / 1000)

    # 6) Ouverture complète du drain de fond — système fonctionnel
    arduino.ouvrir_valve("drain", course_ms)
    urgence.attendre(course_ms / 1000)


def sequence_arret(arduino, config):
    """Bouton rouge (priorité absolue) : moteur d'abord, puis toutes les valves.

    Cette séquence n'est volontairement PAS interruptible : c'est elle-même
    la réaction à l'urgence, elle doit toujours aller jusqu'au bout.
    """
    course_ms = config.course_complete_ms
    arduino.arreter_moteur()
    for nom in NOMS_VALVES:
        arduino.fermer_valve(nom, course_ms)


def sequence_ajout_eau(arduino, urgence, config):
    """Bouton bleu, système en marche : alimentation à ~10 % pendant 1 heure."""
    a = config.ajout_eau
    # Impulsion courte ≈ 10 % d'ouverture ; le firmware Arduino arrête
    # automatiquement le mouvement une fois la durée écoulée, figeant la valve
    # à ce degré d'ouverture (polarité 0/0).
    arduino.ouvrir_valve("alimentation", a["impulsion_ouverture_ms"])
    urgence.attendre(a["impulsion_ouverture_ms"] / 1000)

    urgence.attendre(a["duree_maintien_s"])  # maintien à ~10 %

    arduino.fermer_valve("alimentation", config.course_complete_ms)


# Nom logique → fonction de séquence (déclenchables par l'orchestrateur / le web).
SEQUENCES = {
    "demarrage": sequence_demarrage,
    "priming": sequence_demarrage_avec_priming,
    "ajout_eau": sequence_ajout_eau,
}


# ===================== Orchestration =====================

class Orchestrateur:
    """Reçoit les déclencheurs (boutons physiques OU interface web), applique la
    logique d'état et lance les séquences. Toutes les entrées passent par un
    verrou afin de sérialiser boutons physiques et requêtes web.
    """

    def __init__(self, arduino, config=None):
        self.arduino = arduino
        self.config = config if config is not None else config_module.charger()
        self.arduino.suivi.definir_course(self.config.course_complete_ms)
        self.etat = EtatSysteme()
        self.urgence = GestionnaireUrgence()
        self._thread_sequence = None
        self._verrou_commande = threading.Lock()
        self._flashage = False

    # --- Configuration ---

    def recharger_config(self):
        self.config = config_module.charger()
        self.arduino.suivi.definir_course(self.config.course_complete_ms)

    # --- État courant (pour l'interface web) ---

    def _sequence_en_cours(self):
        t = self._thread_sequence
        return t is not None and t.is_alive()

    def etat_courant(self):
        return {
            "etat": self.etat.obtenir(),
            "sequence_en_cours": self._sequence_en_cours(),
            "flashage_en_cours": self._flashage,
            "valves": self.arduino.suivi.etat(),
            "moteur": self.arduino.moteur_actif,
            "boutons": self.arduino.dernier_etat_boutons,
        }

    # --- Lancement / arrêt des séquences ---

    def _lancer(self, fonction_sequence, etat_si_succes=None):
        """Exécute une séquence dans un thread dédié, en suivant son issue."""
        self.urgence.reinitialiser()

        def cible():
            try:
                fonction_sequence(self.arduino, self.urgence, self.config)
            except Interruption:
                return  # le bouton rouge a déjà pris le relais (arrêt d'urgence)
            except Exception as e:  # noqa: BLE001 — on ne veut pas tuer le thread silencieusement
                print(f"[ERREUR] séquence interrompue : {e}", file=sys.stderr)
                return
            if etat_si_succes is not None:
                self.etat.definir(etat_si_succes)

        thread = threading.Thread(target=cible, daemon=True)
        self._thread_sequence = thread
        thread.start()

    def _arret_urgence(self):
        """Interrompt toute séquence en cours et exécute l'arrêt — priorité absolue."""
        self.urgence.declencher()
        thread = self._thread_sequence
        if thread is not None and thread.is_alive():
            thread.join()
        sequence_arret(self.arduino, self.config)
        self.etat.definir(ETEINT)

    # --- API appelée par les boutons physiques ET l'interface web ---

    def traiter_bouton(self, nom_bouton):
        """Point d'entrée des événements de bouton physiques."""
        with self._verrou_commande:
            if nom_bouton == "rouge":
                self._arret_urgence()
                return
            if self._flashage or self._sequence_en_cours():
                return
            if nom_bouton == "vert":
                self._lancer(sequence_demarrage, etat_si_succes=EN_MARCHE)
            elif nom_bouton == "bleu":
                # Comportement conditionnel (voir doc Boutons de contrôle)
                if self.etat.obtenir() == EN_MARCHE:
                    self._lancer(sequence_ajout_eau)
                else:
                    self._lancer(sequence_demarrage_avec_priming, etat_si_succes=EN_MARCHE)

    def lancer_sequence(self, nom):
        """Déclenche explicitement une séquence depuis l'interface web.

        Renvoie (succes: bool, message: str).
        """
        with self._verrou_commande:
            if self._flashage:
                return False, "Flashage en cours — commande refusée"
            if self._sequence_en_cours():
                return False, "Une séquence est déjà en cours"
            if nom == "ajout_eau" and self.etat.obtenir() != EN_MARCHE:
                return False, "Le système doit être en marche pour l'ajout d'eau"
            if nom == "demarrage":
                self._lancer(sequence_demarrage, etat_si_succes=EN_MARCHE)
            elif nom == "priming":
                self._lancer(sequence_demarrage_avec_priming, etat_si_succes=EN_MARCHE)
            elif nom == "ajout_eau":
                self._lancer(sequence_ajout_eau)
            else:
                return False, f"Séquence inconnue : « {nom} »"
            return True, f"Séquence « {nom} » lancée"

    def arret_urgence(self):
        """Arrêt d'urgence déclenché depuis l'interface web (= bouton rouge)."""
        with self._verrou_commande:
            if self._flashage:
                return False, "Flashage en cours — communication série indisponible"
            self._arret_urgence()
            return True, "Arrêt d'urgence exécuté"

    # --- Contrôle manuel (mode débogage / câblage, via l'interface web) ---

    def _manuel_autorise(self):
        if self._flashage:
            return False, "Flashage en cours — commande refusée"
        if self._sequence_en_cours():
            return False, "Une séquence est en cours — contrôle manuel indisponible"
        return True, ""

    def commande_manuelle_valve(self, valve, action, duree_ms=0):
        with self._verrou_commande:
            ok, message = self._manuel_autorise()
            if not ok:
                return False, message
            if valve not in NOMS_VALVES:
                return False, f"Valve inconnue : « {valve} »"
            if action == "ouvrir":
                self.arduino.ouvrir_valve(valve, duree_ms)
            elif action == "fermer":
                self.arduino.fermer_valve(valve, duree_ms)
            elif action == "arreter":
                self.arduino.arreter_valve(valve)
            else:
                return False, f"Action inconnue : « {action} »"
            return True, f"{action} {valve} ({int(duree_ms)} ms)"

    def commande_manuelle_moteur(self, action):
        with self._verrou_commande:
            ok, message = self._manuel_autorise()
            if not ok:
                return False, message
            if action == "demarrer":
                self.arduino.demarrer_moteur()
            elif action == "arreter":
                self.arduino.arreter_moteur()
            else:
                return False, f"Action inconnue : « {action} »"
            return True, f"moteur {action}"

    def lire_boutons(self):
        """Renvoie le dernier état connu des boutons (rafraîchi par le moniteur)."""
        return self.arduino.dernier_etat_boutons

    def moniteur_boutons(self, intervalle_s=1.5):
        """Sonde périodiquement l'état des boutons et met à jour le cache.

        Tourne dans un thread dédié (voir app.py). Mis en pause pendant un
        flashage (port série indisponible).
        """
        while True:
            if not self._flashage:
                try:
                    self.arduino.lire_etat_boutons()
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(intervalle_s)

    # --- Coordination du flashage (libère le port série) ---

    def pause_pour_flashage(self):
        """Bloque toute commande et signale qu'un flashage va commencer."""
        with self._verrou_commande:
            self._flashage = True

    def reprise_apres_flashage(self):
        with self._verrou_commande:
            self._flashage = False

    # --- Boucle d'écoute des boutons physiques ---

    def boucle(self):
        while True:
            message = self.arduino.evenements.get()
            if message.get("event") == "bouton":
                self.traiter_bouton(message.get("nom"))

    def arret_initial(self):
        """Sécurité au démarrage : repart d'un état sûr connu (système éteint)."""
        sequence_arret(self.arduino, self.config)
        self.etat.definir(ETEINT)


def main():
    """Mode de repli « boutons seuls » (sans interface web). Entrée principale : app.py."""
    arduino = LiaisonArduino()
    orchestrateur = Orchestrateur(arduino)
    threading.Thread(target=orchestrateur.moniteur_boutons, daemon=True).start()
    orchestrateur.arret_initial()
    orchestrateur.boucle()


if __name__ == "__main__":
    main()
