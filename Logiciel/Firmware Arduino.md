---
tags: [piscine, logiciel, arduino, firmware]
---

# Firmware Arduino

Code embarqué exécuté sur l'[[Arduino Uno]]. Conformément au choix d'architecture (voir [[Architecture]] et [[Programme Raspberry Pi (Python)]]), l'Arduino est une **interface matérielle « bête »** : il ne connaît **aucune séquence** — toute la logique de séquencement et de décision est centralisée dans le programme Python du [[Raspberry Pi 3]]. L'Arduino se contente d'exécuter des **commandes primitives** reçues du Pi et de lui rapporter l'état brut du matériel (boutons, etc.).

## Reprogrammation

Le firmware peut être mis à jour **localement**, directement depuis le [[Raspberry Pi 3]], via la connexion **USB** qui relie les deux appareils (la même liaison sert à la communication série, voir [[Communication Série]]).

## Responsabilités principales

- Initialiser les broches :
  - Sorties : D1 (relais), D3-D4, D5-D6, D7-D8, D9-D10 (H-bridges des valves — voir [[Contrôle des valves (H-bridge)]])
  - Entrées avec pull-up : D11, D12, D13 (boutons)
- Lire l'état des boutons (avec gestion de l'anti-rebond et de la logique inversée par le pull-up) et **rapporter immédiatement** chaque appui au Raspberry Pi via JSON
- Recevoir des **commandes primitives** du Raspberry Pi (voir ci-dessous) et les exécuter
- Renvoyer l'état brut du matériel au Raspberry Pi (état des sorties, des boutons) sur demande ou en continu

> [!important] Aucune logique de séquence dans le firmware
> Le firmware **n'implémente pas** les séquences de démarrage/arrêt/ajout d'eau, ni la logique conditionnelle du bouton bleu, ni le suivi de l'état global du système (`EN_MARCHE`/`ÉTEINT`). Toutes ces responsabilités appartiennent au [[Programme Raspberry Pi (Python)|programme Python du Raspberry Pi]] — voir cette note pour le détail des séquences.

## Commandes primitives exposées au Raspberry Pi

L'Arduino expose un jeu de commandes primitives, reçues en **JSON** sur le port série (voir [[Communication Série]]), par exemple :

| Commande (concept) | Effet |
|---|---|
| Ouvrir une valve (pendant une durée) | Applique la polarité d'ouverture sur la paire de broches concernée pendant la durée donnée, puis coupe (`0`/`0`) |
| Fermer une valve (pendant une durée) | Applique la polarité de fermeture pendant la durée donnée, puis coupe (`0`/`0`) |
| Arrêter une valve immédiatement | Coupe la polarité (`0`/`0`) — utile pour figer une ouverture partielle |
| Démarrer le moteur | **Stub** — aucune broche relais assignée pour l'instant (ex-D1 = TX série) ; répond `ok` sans effet matériel (voir note ci-dessous) |
| Arrêter le moteur | **Stub** — idem |
| Lire l'état des boutons | Retourne l'état courant (pressé/relâché) des boutons **vert et rouge** (le bouton bleu D13 est retiré) |

> [!warning] D1 (moteur) et D13 (bouton bleu) retirés pour l'instant
> Conformément à [[Brochage Arduino]] : **D1** (= TX série) et **D13** (= LED intégrée) ne
> conviennent pas. Dans le firmware actuel, le **relais moteur n'a pas de broche** (les commandes
> `moteur_demarrer`/`moteur_arreter` sont des **stubs** marqués `// TODO`), et le **bouton bleu
> est retiré** du tableau des boutons surveillés. Le rôle du bouton bleu passe par l'[[Interface Web (Pi)]].
> Ces deux fonctions seront recâblées plus tard (ex. relais → D2, bouton bleu → A0).

C'est le **Pi** qui décide *quand* et *dans quel ordre* envoyer ces commandes, et qui gère lui-même les délais (15 s, 10 s, duty cycle, 1 heure, etc.) propres à chaque séquence — voir [[Programme Raspberry Pi (Python)]].

## Bouton rouge — priorité absolue

Un appui sur le **bouton rouge** est rapporté au Pi **immédiatement**, avec une **priorité absolue** : le Pi doit interrompre toute séquence en cours et déclencher l'arrêt d'urgence (moteur coupé, puis valves fermées), peu importe l'étape en cours (voir [[Boutons de contrôle]] et [[Séquence d'arrêt]]). Le firmware doit donc s'assurer que la lecture des boutons n'est **jamais bloquée** par l'exécution d'une commande primitive en cours (éviter les `delay()` longs et bloquants ; structurer le code pour rester réactif).

## Fonction réutilisable : commande des valves

Les quatre valves sont commandées selon le **même principe** (voir [[Contrôle des valves (H-bridge)]]), ce qui se prête à une fonction unique réutilisée dans le firmware pour exécuter les commandes primitives, par ex. :

```
ouvrirValve(pinA, pinB, durée)   // applique la polarité d'ouverture pendant `durée`, puis coupe (0/0)
fermerValve(pinA, pinB, durée)   // applique la polarité de fermeture pendant `durée`, puis coupe (0/0)
arreterValve(pinA, pinB)         // coupe immédiatement (0/0) — utile pour une ouverture partielle
```

- Une **ouverture/fermeture complète** correspond à `durée = 10 secondes`.
- Une **ouverture partielle** (ex. : impulsion de 0.5 s pour le mode priming de l'[[Valve Écumoire|écumoire]], ou de ~1 s pour l'ouverture à 10 % lors de l'[[Séquence d'ajout d'eau|ajout d'eau]]) correspond à une `durée` plus courte.
- Le minutage des **séquences complètes** (duty cycle, attentes, répétitions) est géré côté Pi, qui enchaîne les appels à ces commandes primitives — voir [[Programme Raspberry Pi (Python)]].

## État par défaut au démarrage / après un plantage

Au démarrage (mise sous tension ou redémarrage du firmware), l'Arduino doit se mettre dans un **état sûr par défaut** : moteur arrêté (relais désactivé), polarités des valves coupées (`0`/`0`, aucun mouvement). C'est ensuite au [[Programme Raspberry Pi (Python)|programme Python]] de décider de la suite (voir la section *État par défaut* de cette note) — l'état global du système est considéré `ÉTEINT` par défaut.

> [!note] Implémentation
> Le firmware complet se trouve dans `arduino/firmware_piscine/firmware_piscine.ino` (voir [[Implémentation des programmes]]). Il est écrit en C/C++ avec la bibliothèque **ArduinoJson**, et suit exactement le jeu de commandes et les noms de valves (`ecumoire`, `drain`, `alimentation`, `retour`) décrits ci-dessus et dans [[Communication Série]].

Voir [[Architecture]] pour le contexte global.
