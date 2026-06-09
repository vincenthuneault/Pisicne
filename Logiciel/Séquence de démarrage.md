---
tags: [piscine, logiciel, séquence, démarrage]
---

# Séquence de démarrage (simple)

Exécutée par le [[Programme Raspberry Pi (Python)|programme Python du Raspberry Pi]] (voir [[Architecture]] pour le choix d'architecture « Pi chef d'orchestre »), déclenchée par un appui sur le **bouton vert** ([[Boutons de contrôle]]) — rapporté par l'[[Arduino Uno]] — ou par une commande de lancement à distance.

## Étapes

Cette séquence est volontairement **simple** :

1. Ouvrir **toutes les valves** : [[Valve Écumoire]], [[Valve Drain de fond]], [[Valve Alimentation (Priming)|valve d'alimentation]] et [[Valve Retour Piscine|valve de retour]]
2. Enclencher le contacteur du moteur ([[Relais Moteur]])

À la fin de cette séquence, le système passe à l'état `EN_MARCHE` (voir la section *État du système* de [[Programme Raspberry Pi (Python)]]) — ce qui détermine notamment le comportement futur du bouton bleu ([[Séquence d'ajout d'eau]]).

Comme pour toutes les séquences, un appui sur le **bouton rouge** interrompt celle-ci immédiatement, à n'importe quelle étape, et bascule vers la [[Séquence d'arrêt]] (priorité absolue — voir cette note).

## Différence avec le bouton bleu (système éteint)

Cette séquence simple est **différente** de la [[Séquence de démarrage avec priming]], déclenchée par le **bouton bleu lorsque le système est éteint** (comportement conditionnel — voir [[Boutons de contrôle]]). Cette dernière ré-amorce progressivement les tuyaux du système pour éviter que la pompe ne tourne dans le vide (voir [[Contexte et objectifs]]), alors que la séquence simple du bouton vert se contente d'ouvrir les valves et de démarrer le moteur — destinée aux cas où les conduites sont déjà amorcées (ex. : système éteint depuis peu).

> [!note]
> L'ordre exact d'ouverture des valves (toutes en même temps ou séquentiellement) reste à préciser si nécessaire — à documenter selon le comportement réel observé.

Voir [[Programme Raspberry Pi (Python)]] pour l'implémentation, et [[Séquence d'arrêt]] pour la procédure inverse.
