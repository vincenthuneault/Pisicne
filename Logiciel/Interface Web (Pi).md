---
tags: [piscine, logiciel, raspberry-pi, web, interface]
---

# Interface Web (Pi)

Interface web **locale** servie par le [[Raspberry Pi 3]], qui permet de contrôler le système
sans les [[Boutons de contrôle|boutons physiques]], d'**ajuster les paramètres** des séquences,
et de **reprogrammer l'[[Arduino Uno]]**. C'est une première brique concrète de l'[[Accès distant]]
*(la version Internet/distante reste reportée)* — ici, accès **LAN uniquement, sans
authentification** (réseau domestique).

> [!important] Un seul processus détient le port série
> Comme un seul processus peut ouvrir `/dev/ttyACM0`, le serveur web **est** l'entrée principale
> du système : il détient l'unique [[Communication Série|liaison série]] et la partage avec
> l'orchestrateur. On ne lance donc **pas** `piscine.py` séparément quand le serveur tourne
> (voir [[Implémentation des programmes]]).

## Lancement

```
python3 raspberry-pi/app.py
# test de l'UI sans Arduino branché :
PISCINE_SIMULATION=1 python3 raspberry-pi/app.py
```

Puis ouvrir `http://<adresse-du-pi>:8080` depuis un navigateur du réseau local.

## Sections de la page

1. **État** — badge `EN MARCHE` / `ÉTEINT`, rafraîchi par sondage régulier ; indique aussi
   si une séquence ou un flashage est en cours.
2. **Contrôle** — boutons déclenchant les séquences (`Démarrage simple`,
   `Démarrage avec priming`, `Ajout d'eau`) et un grand bouton **Arrêt d'urgence**
   (équivalent du [[Séquence d'arrêt|bouton rouge]], priorité absolue).
3. **Mode manuel** — ouvre/ferme/arrête chaque valve (avec durée) et pilote le moteur, comme
   `test_materiel.py`. **Désactivé pendant une séquence** ou un flashage.
4. **Paramètres** — formulaire éditant les délais/paramètres des séquences (fichier `config.json`).
5. **Firmware** — téléverse un sketch `.ino` et flashe l'Arduino (voir plus bas).

## Paramètres ajustables (`config.json`)

Les délais autrefois codés en dur dans `piscine.py` vivent maintenant dans
`raspberry-pi/config.json` (lu/écrit par `config.py`, validé : nombres > 0). Modifiables depuis
la page, appliqués au **prochain lancement** de séquence :

- `course_complete_ms` — course complète d'une valve (≈ 10 000 ms, voir [[Contrôle des valves (H-bridge)]])
- `priming` — `amorcage_initial_s`, `stabilisation_s`, `nb_cycles`,
  `impulsion_ouverture_ms`, `impulsion_fermeture_ms` (voir [[Séquence de démarrage avec priming]])
- `ajout_eau` — `impulsion_ouverture_ms`, `duree_maintien_s` (voir [[Séquence d'ajout d'eau]])

## Reprogrammation de l'Arduino (flashage)

La page permet de **téléverser un `.ino`** puis de **flasher** l'Arduino via la même liaison USB.
Le flashage exige un accès **exclusif** au port série : le serveur met donc l'orchestrateur en
pause, **ferme la liaison série**, lance la compilation+téléversement, puis **rouvre** tout
(voir `flashage.py`).

> [!note] Prérequis sur le Pi
> Le flashage utilise **arduino-cli**, à installer avec le cœur AVR et la bibliothèque ArduinoJson :
> ```
> arduino-cli core install arduino:avr
> arduino-cli lib install ArduinoJson
> ```
> Et les dépendances Python : `pip install -r raspberry-pi/requirements.txt` (pyserial, flask).

## Points d'API (référence)

| Méthode | Route | Effet |
|---|---|---|
| GET | `/api/etat` | État du système (sondage) |
| GET / POST | `/api/config` | Lire / enregistrer les paramètres |
| POST | `/api/sequence/<nom>` | Lancer `demarrage` \| `priming` \| `ajout_eau` |
| POST | `/api/arret` | Arrêt d'urgence (priorité absolue) |
| POST | `/api/manuel/valve` | `{valve, action, duree_ms}` |
| POST | `/api/manuel/moteur` | `{action}` |
| GET | `/api/manuel/boutons` | État courant des boutons |
| POST | `/api/firmware` | Téléverser un `.ino` |
| POST | `/api/firmware/flash` | Compiler + flasher l'Arduino |

Voir [[Programme Raspberry Pi (Python)]] (logique des séquences), [[Communication Série]]
(protocole avec l'Arduino), [[Implémentation des programmes]] (fichiers source) et
[[Accès distant]] (vision distante à long terme).
