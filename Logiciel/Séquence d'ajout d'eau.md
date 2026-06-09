---
tags: [piscine, logiciel, séquence, ajout-eau]
---

# Séquence d'ajout d'eau

Exécutée par le [[Programme Raspberry Pi (Python)|programme Python du Raspberry Pi]] (voir [[Architecture]] pour le choix d'architecture « Pi chef d'orchestre »), déclenchée par un appui sur le **bouton bleu** ([[Boutons de contrôle]]) — rapporté par l'[[Arduino Uno]] — **uniquement lorsque le système est déjà en fonction**, ou par une commande à distance correspondante.

> [!note] Comportement conditionnel du bouton bleu
> Le bouton bleu n'exécute cette séquence que si le système est **en marche** au moment de l'appui. S'il est appuyé alors que le système est **éteint**, c'est la [[Séquence de démarrage avec priming]] qui est déclenchée à la place (différente de la séquence simple du bouton vert — voir [[Boutons de contrôle]] et la section *État du système* de [[Programme Raspberry Pi (Python)]]).

Comme pour toutes les séquences, un appui sur le **bouton rouge** interrompt celle-ci immédiatement, à n'importe quel moment de l'heure d'ouverture, et bascule vers la [[Séquence d'arrêt]] (priorité absolue — voir cette note).

## Contexte

Contrairement aux séquences de [[Séquence de démarrage|démarrage]] et d'[[Séquence d'arrêt|arrêt]], cette fonction s'exécute **pendant que le système est déjà en marche** (moteur en fonction, valves de filtration ouvertes).

## Étapes

1. Ouvrir la [[Valve Alimentation (Priming)|valve d'alimentation en eau]] à **10 % seulement** — *pas* en grand ouvert
2. Maintenir cette ouverture partielle pendant **1 heure**
3. Refermer complètement la valve d'alimentation

## Pourquoi seulement 10 % d'ouverture ?

Une ouverture complète viderait rapidement la capacité d'alimentation en eau. En limitant l'ouverture à environ 10 %, le débit est réduit, ce qui permet à la source d'alimentation de **fournir de l'eau de façon soutenue sur une période prolongée** (1 heure) sans s'épuiser.

## Implémentation (ouverture partielle)

Selon le principe décrit dans [[Contrôle des valves (H-bridge)]] :
- Course complète ≈ 10 secondes → une ouverture de ~10 % correspond à une impulsion d'ouverture d'environ **1 seconde**, suivie d'un arrêt (`0`/`0`) pour figer la valve à ce degré d'ouverture
- La valve reste ensuite dans cette position (polarité coupée, aucune consommation) pendant toute la durée d'1 heure
- À la fin de la période, appliquer la polarité de fermeture pendant la course complète (≈ 10 s, ou davantage par sécurité) pour refermer entièrement la valve

> [!note]
> Contrairement au mode priming de l'[[Valve Écumoire|écumoire]] (impulsions répétées dans la [[Séquence de démarrage avec priming]]), ici la valve est ouverte **une seule fois** à un degré partiel et **maintenue** dans cette position pendant toute la durée — pas de duty cycle répété.

Voir [[Programme Raspberry Pi (Python)]] pour l'implémentation (c'est le Pi qui mesure l'heure d'ouverture et envoie les commandes primitives à l'Arduino) et [[Boutons de contrôle]] pour le déclencheur.
