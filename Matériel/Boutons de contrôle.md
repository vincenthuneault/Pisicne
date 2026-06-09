---
tags: [piscine, matériel, boutons, interface-utilisateur]
---

# Boutons de contrôle

Trois boutons physiques permettent de déclencher les actions principales du système. L'[[Arduino Uno]] se contente de **lire et de rapporter** chaque appui au [[Raspberry Pi 3]] — c'est le [[Programme Raspberry Pi (Python)|programme Python du Pi]] qui décide de l'action à exécuter (voir [[Architecture]] pour le choix d'architecture « Pi chef d'orchestre »).

| Bouton | Couleur | Broche | Action déclenchée |
|---|---|---|---|
| Lancement | 🟢 Vert | D11 | Démarre la [[Séquence de démarrage|séquence de mise en marche simple]] du système : ouvre toutes les valves, puis enclenche le contacteur du moteur |
| Arrêt | 🔴 Rouge | D12 | Déclenche la [[Séquence d'arrêt|séquence d'arrêt]] du système : éteint le moteur, puis ferme toutes les valves |
| Ajout d'eau / Lancement avec priming | 🔵 Bleu | ~~D13~~ *(retiré)* | **Conditionnel à l'état du système** — voir ci-dessous |

> [!warning] Bouton bleu (D13) temporairement retiré
> La broche **D13** ne convient pas en entrée (LED intégrée de la carte qui fausse `INPUT_PULLUP`) — voir [[Brochage Arduino]]. Le **bouton bleu physique est donc retiré pour l'instant**. Sa logique conditionnelle reste implémentée côté Pi et **déclenchable via l'[[Interface Web (Pi)]]** (boutons « Démarrage avec priming » et « Ajout d'eau »), en attendant un recâblage du bouton sur une broche libre (ex. A0).

## Comportement conditionnel du bouton bleu

Contrairement aux boutons vert et rouge, le bouton bleu déclenche une action **différente selon l'état courant du système** (en marche ou éteint) :

| État du système au moment de l'appui | Action déclenchée |
|---|---|
| 🟢 Système **en fonction** | [[Séquence d'ajout d'eau]] — ouverture partielle (≈10 %) de la valve d'alimentation, maintenue 1 heure |
| 🔴 Système **éteint** | [[Séquence de démarrage avec priming]] — lance le système en ré-amorçant progressivement les tuyaux (différente et plus élaborée que la séquence simple du bouton vert) |

> [!important] Deux séquences de démarrage distinctes
> Le système comporte **deux** séquences de démarrage différentes :
> - [[Séquence de démarrage]] (simple) — déclenchée par le **bouton vert** : ouvre toutes les valves et démarre le moteur, sans étape de priming
> - [[Séquence de démarrage avec priming]] — déclenchée par le **bouton bleu lorsque le système est éteint** : ré-amorce progressivement les tuyaux (étapes chronométrées, priming par duty cycle de la [[Valve Écumoire]]) avant de considérer le système fonctionnel

> [!note]
> Cette logique conditionnelle exige que le **programme Python du Pi** (et non le firmware Arduino — voir [[Architecture]]) connaisse l'état courant du système (en fonction / éteint) pour décider quelle séquence exécuter au moment de l'appui. Voir la section *État du système* dans [[Programme Raspberry Pi (Python)]].
>
> Le **bouton rouge**, lui, n'a pas ce genre d'ambiguïté : il déclenche **toujours** la [[Séquence d'arrêt]], avec une **priorité absolue** qui interrompt immédiatement toute autre séquence en cours (voir cette note).

## Câblage — pull-up requis

Les trois boutons nécessitent une résistance de **pull-up** en programmation (`pinMode(pin, INPUT_PULLUP)`). Conséquence sur la logique :

- État au repos (bouton relâché) : `HIGH`
- État pressé : `LOW`

Le code doit donc détecter un **front descendant** (`HIGH → LOW`) pour identifier un appui sur le bouton, idéalement avec un anti-rebond (debounce).

## Séquences associées

- **Bouton vert** → toujours [[Séquence de démarrage]] (simple)
- **Bouton rouge** → toujours [[Séquence d'arrêt]]
- **Bouton bleu** → [[Séquence d'ajout d'eau]] *(système en marche)* **ou** [[Séquence de démarrage avec priming]] *(système éteint)*, selon l'état courant

Voir [[Brochage Arduino]], [[Firmware Arduino]] (lecture des boutons côté Arduino) et [[Programme Raspberry Pi (Python)]] (décision et exécution des séquences).
