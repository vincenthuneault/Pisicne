---
tags: [piscine, logiciel, séquence, arrêt]
---

# Séquence d'arrêt

Exécutée par le [[Programme Raspberry Pi (Python)|programme Python du Raspberry Pi]] (voir [[Architecture]] pour le choix d'architecture « Pi chef d'orchestre »), déclenchée par un appui sur le **bouton rouge** ([[Boutons de contrôle]]) — rapporté par l'[[Arduino Uno]] — ou par une commande d'arrêt à distance.

À la fin de cette séquence, le système passe à l'état `ÉTEINT` (voir la section *État du système* de [[Programme Raspberry Pi (Python)]]) — ce qui détermine notamment le comportement futur du bouton bleu (déclenchera alors la [[Séquence de démarrage avec priming]] plutôt que la [[Séquence d'ajout d'eau]]).

## Objectif

Mettre le système hors service en isolant la piscine (toutes les valves fermées), conformément à la règle décrite dans [[Contexte et objectifs]] — applicable autant pour réduire la consommation électrique que pour préparer une maintenance ou l'ajout de chlore au Nature2.

## Priorité absolue du bouton rouge

> [!important]
> Le bouton rouge est **prioritaire sur tout** : dès qu'il est pressé, cette séquence doit s'exécuter **immédiatement**, peu importe ce que le système est en train de faire — y compris en interrompant en plein milieu une [[Séquence de démarrage]], une [[Séquence de démarrage avec priming]] ou une [[Séquence d'ajout d'eau]] déjà en cours. Aucune autre logique ne doit retarder l'exécution de cet arrêt.
>
> Cela signifie que le programme Python doit pouvoir **détecter l'appui du bouton rouge à tout moment** — y compris pendant les attentes (`sleep`) et les duty cycles d'une autre séquence — et basculer immédiatement vers cette séquence d'arrêt. Voir la section *Bouton rouge — priorité absolue* de [[Programme Raspberry Pi (Python)]] pour les implications sur l'implémentation.

## Étapes

### 1. Arrêt du moteur
- Désactiver le [[Relais Moteur]] (commande primitive envoyée à l'Arduino)

### 2. Fermeture de toutes les valves
- Fermer la [[Valve Écumoire]]
- Fermer la [[Valve Drain de fond]]
- Fermer la [[Valve Retour Piscine]]
- Fermer la [[Valve Alimentation (Priming)|valve d'alimentation en eau]]

> [!note]
> L'ordre est simple et fixe : le moteur est coupé **en premier**, puis toutes les valves sont fermées — peu importe leur état courant (ouvertes, partiellement ouvertes, en cours de mouvement). Chaque fermeture complète prend ≈ 10 secondes (voir [[Contrôle des valves (H-bridge)]]); les éventuelles temporisations entre les fermetures restent à préciser/calibrer.

Voir [[Programme Raspberry Pi (Python)]] pour l'implémentation, et [[Séquence de démarrage]] / [[Séquence de démarrage avec priming]] pour les procédures inverses.
