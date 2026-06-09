---
tags: [piscine, logiciel, implémentation, code]
---

# Implémentation des programmes

Cette note recense l'emplacement et la structure du **code source** du projet (par opposition aux notes de [[Programme Raspberry Pi (Python)|conception]] qui décrivent le *pourquoi* et le *comment* attendu). Le code se trouve à la racine du dépôt, à côté du coffre Obsidian.

## Raspberry Pi — `raspberry-pi/`

| Fichier | Rôle |
|---|---|
| `app.py` | **Entrée principale** : serveur web Flask + orchestrateur (détient l'unique liaison série). Voir [[Interface Web (Pi)]] |
| `piscine.py` | Logique métier : liaison série JSON, état du système, gestionnaire d'urgence (priorité du bouton rouge), les quatre séquences, et l'orchestrateur. Importé par `app.py` ; `main()` reste un mode de repli « boutons seuls » |
| `config.py` / `config.json` | Délais et paramètres des séquences, externalisés et validés ; modifiables via l'interface web |
| `flashage.py` | Reprogrammation de l'Arduino via `arduino-cli` (libère puis rouvre le port série) |
| `templates/index.html`, `static/style.css`, `static/app.js` | Page web (état, contrôle, mode manuel, paramètres, firmware) |
| `test_materiel.py` | Outil de test manuel en ligne de commande : menu interactif pour exercer chaque sortie/entrée individuellement, sans passer par les séquences — voir ci-dessous. *(À ne pas lancer en même temps que `app.py` : un seul processus peut ouvrir le port série.)* |
| `requirements.txt` | Dépendances : `pyserial`, `flask` |

> [!note] Architecture d'exécution
> Comme un seul processus peut détenir `/dev/ttyACM0`, **`app.py` est le point d'entrée** : il
> crée l'unique `LiaisonArduino`, lance l'`Orchestrateur` (écoute des boutons physiques) dans un
> thread, exécute un arrêt de sécurité au démarrage, puis sert l'interface web. Les délais ne
> sont plus codés en dur dans `piscine.py` : ils proviennent de `config.json` (via `config.py`).
> Voir [[Interface Web (Pi)]].

Structure de `piscine.py` :

- **`EtatSysteme`** — état global `EN_MARCHE` / `ETEINT`, protégé par verrou ; initialisé à `ETEINT` (sécurité par défaut, voir [[Programme Raspberry Pi (Python)#État du système]])
- **`LiaisonArduino`** — encapsule `pyserial` ; un thread de lecture dédié (arrêtable) dépile les lignes JSON et place les événements (`{"event":"bouton",...}`) dans une `queue.Queue`, en routant les réponses d'état des boutons à part ; expose une méthode par commande primitive (`ouvrir_valve`, `fermer_valve`, `arreter_valve`, `demarrer_moteur`, `arreter_moteur`, `lire_etat_boutons`) ainsi que `fermer()`/`rouvrir()` pour libérer le port le temps du flashage. Suit aussi la **position estimée des valves** (`SuiviValves`, dead reckoning à partir des commandes — système en boucle ouverte) et l'état commandé du moteur, exposés à l'UI via `etat_courant()`. Un mode **simulation** (`PISCINE_SIMULATION=1`) permet de tester sans Arduino.
- **`GestionnaireUrgence`** / **`Interruption`** — implémentent la [[Programme Raspberry Pi (Python)#Bouton rouge — priorité absolue (interruption)|priorité absolue du bouton rouge]] : un `threading.Event` est vérifié à chaque étape d'une séquence et pendant chaque attente via `attendre()`, une attente interruptible découpée en tranches de 0.1 s qui lève `Interruption` dès que l'urgence est déclenchée
- **Séquences** (`sequence_demarrage`, `sequence_demarrage_avec_priming`, `sequence_arret`, `sequence_ajout_eau`) — fonctions reproduisant exactement les étapes et minutages décrits dans [[Séquence de démarrage]], [[Séquence de démarrage avec priming]], [[Séquence d'arrêt]] et [[Séquence d'ajout d'eau]]. Toutes (sauf l'arrêt, volontairement non interruptible puisqu'il *est* la réaction à l'urgence) vérifient l'urgence en continu
- **`Orchestrateur`** — reçoit les déclencheurs (boutons physiques **et** requêtes de l'[[Interface Web (Pi)]]), sérialisés par un verrou ; applique la [[Boutons de contrôle|logique conditionnelle du bouton bleu]] selon l'état courant, lance chaque séquence dans son propre thread (pour rester réactif au bouton rouge) et met à jour l'état du système une fois la séquence terminée avec succès. Expose aussi des méthodes pour le web (`lancer_sequence`, `arret_urgence`, commandes manuelles, `pause_pour_flashage`/`reprise_apres_flashage`)

### Outil de test manuel — `test_materiel.py`

Avant de tester les séquences complètes, ce script permet de valider le câblage et le firmware **sortie par sortie / entrée par entrée**, via un menu en ligne de commande :

1. Ouvrir une valve (nom + durée, par défaut la course complète de 10 s)
2. Fermer une valve (nom + durée)
3. Arrêter une valve immédiatement (fige sa position — utile pour vérifier une ouverture partielle)
4. Démarrer le moteur
5. Arrêter le moteur
6. Lire l'état courant des boutons (commande `etat_boutons`)
7. Écouter les appuis sur les boutons pendant 15 s et afficher chaque événement reçu en temps réel

Il réutilise directement `LiaisonArduino` de `piscine.py` — donc le même protocole JSON à 115 200 bauds — sans exécuter aucune séquence ; chaque action envoie une seule commande primitive isolée. Lancer avec :

```
python3 raspberry-pi/test_materiel.py
```

## Arduino — `arduino/firmware_piscine/`

| Fichier | Rôle |
|---|---|
| `firmware_piscine.ino` | Sketch complet : initialisation des broches, lecture anti-rebond des boutons, exécution non bloquante des commandes primitives, communication JSON |

Points clés de `firmware_piscine.ino` :

- Conformément au choix [[Architecture#Choix d'architecture : « Pi chef d'orchestre / Arduino interface bête »|« Pi chef d'orchestre »]], **aucune séquence** n'y est codée — seulement les commandes primitives décrites dans [[Communication Série#Schéma des messages (implémenté)|le schéma des messages]]
- Les valves sont pilotées via une structure `Valve` générique : appliquer la polarité demandée, mémoriser un instant de fin (`millis() + durée`), et la couper automatiquement (`mettreAJourValves()`) une fois la durée écoulée — c'est ce mécanisme non bloquant qui remplace un `delay()`
- Les boutons sont lus avec anti-rebond logiciel (50 ms) et logique inversée (`INPUT_PULLUP`, pressé = `LOW`) ; chaque appui stable est rapporté immédiatement en JSON
- `setup()` place le système dans l'état sûr par défaut : relais désactivé, polarités des valves coupées (`0`/`0`)
- Bibliothèque requise : **ArduinoJson**

## Pour aller plus loin

- [[Architecture]] — vue d'ensemble et choix « Pi chef d'orchestre / Arduino interface bête »
- [[Communication Série]] — schéma complet des messages JSON échangés
- [[Programme Raspberry Pi (Python)]] et [[Firmware Arduino]] — notes de conception détaillées derrière chaque programme
