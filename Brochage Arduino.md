---
tags: [piscine, arduino, brochage, référence]
---

# Brochage de l'Arduino Uno

Table de référence de toutes les broches numériques utilisées par l'[[Arduino Uno]].

| Broche(s) | Fonction | Type de commande | Note |
|---|---|---|---|
| D3, D4 | [[Valve Écumoire]] | H-bridge (2 pins) | Contrôle l'ouverture/fermeture de la valve d'écumoire |
| D5, D6 | [[Valve Drain de fond]] | H-bridge (2 pins) | Contrôle l'ouverture/fermeture de la valve de drain de fond |
| D7, D8 | [[Valve Alimentation (Priming)]] | H-bridge (2 pins) | Valve d'alimentation en eau, utilisée pour le priming avant le lancement du moteur |
| D9, D10 | [[Valve Retour Piscine]] | H-bridge (2 pins) | Contrôle la valve de retour de l'eau vers la piscine |
| D11 | Bouton vert — Lancement | Entrée numérique avec **pull-up** | Déclenche la séquence de démarrage du système |
| D12 | Bouton rouge — Arrêt | Entrée numérique avec **pull-up** | Déclenche l'arrêt du système |

> [!warning] Broches D1 et D13 retirées pour l'instant
> Deux fonctions ont été **temporairement retirées du brochage** car leurs broches d'origine ne conviennent pas sur un Arduino Uno :
> - **D1 → [[Relais Moteur]]** : D1 est la broche **TX** du port série. `Serial.begin()` la pilote, donc le relais claquerait à chaque message échangé avec le Pi. Le relais moteur n'a **plus de broche assignée** ; les commandes `moteur_demarrer`/`moteur_arreter` restent exposées mais sont des **stubs** (sans effet matériel) côté firmware, en attendant un recâblage (ex. **D2**, libre).
> - **D13 → Bouton bleu** : D13 est câblée à la **LED intégrée** de la carte, ce qui fausse une entrée `INPUT_PULLUP`. Le bouton bleu physique est retiré ; son rôle (ajout d'eau / priming conditionnel) est déclenchable via l'**[[Interface Web (Pi)]]**, en attendant un recâblage (ex. **A0**).
>
> Broches libres pour ces recâblages : **D2** et **A0–A5**.

> [!note] Pull-up sur les boutons
> Les boutons (D11, D12) requièrent une résistance de pull-up en programmation (`INPUT_PULLUP`). L'état logique est donc **inversé** : la broche lit `HIGH` au repos et `LOW` lorsque le bouton est pressé.

Voir [[Boutons de contrôle]] pour le détail des actions associées à chaque bouton, et [[Architecture]] pour la vue d'ensemble du système.
