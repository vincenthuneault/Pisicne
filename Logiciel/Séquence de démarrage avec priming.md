---
tags: [piscine, logiciel, séquence, priming, démarrage]
---

# Séquence de démarrage avec priming des tuyaux

Exécutée par le [[Programme Raspberry Pi (Python)|programme Python du Raspberry Pi]] (voir [[Architecture]] pour le choix d'architecture « Pi chef d'orchestre » — l'Arduino ne fait qu'exécuter les commandes primitives reçues), déclenchée par un appui sur le **bouton bleu** ([[Boutons de contrôle]]) **lorsque le système est éteint** (comportement conditionnel), ou par la commande à distance correspondante.

Comme pour toutes les séquences, un appui sur le **bouton rouge** interrompt celle-ci immédiatement, à n'importe quelle étape (y compris en plein milieu d'une attente ou d'un cycle de priming), et bascule vers la [[Séquence d'arrêt]] (priorité absolue — voir cette note).

## Différence avec le bouton vert

Cette séquence est **différente** de la [[Séquence de démarrage]] simple déclenchée par le bouton vert : elle ré-amorce (« prime ») les tuyaux du système avant de le considérer pleinement fonctionnel. Elle est destinée aux cas où le système est resté éteint assez longtemps pour que les conduites aient perdu leur amorçage (perte de prime / air dans les lignes) — ce qui exige un redémarrage progressif et contrôlé pour **éviter que la pompe ne tourne dans le vide**, compte tenu de la position du système par rapport à la piscine (voir [[Contexte et objectifs]]).

## Étapes

> [!important] Corrections après essais terrain
> Corrections par rapport à la version initiale : (1) la [[Valve Alimentation (Priming)|valve d'alimentation]] reste **ouverte** (injection d'eau continue) jusqu'à un certain délai **après le démarrage du moteur**, configurable, puis est refermée (la laisser ouverte indéfiniment viderait la réserve d'eau) ; (2) le priming par à-coups (« jerk ») se fait sur le **[[Valve Drain de fond|drain de fond]]**, et non sur l'écumoire (qui est déjà grande ouverte).

### 1. Amorçage initial — 15 secondes
- Ouvrir **complètement** la [[Valve Écumoire]]
- Ouvrir la [[Valve Alimentation (Priming)|valve d'alimentation en eau]] pour **injecter de l'eau**
- Maintenir cet état pendant **15 secondes**

### 2. Ouverture de la sortie
- Ouvrir **complètement** la [[Valve Retour Piscine|valve de sortie (retour vers la piscine)]] — l'**alimentation reste ouverte**

### 3. Démarrage du moteur
- Une fois la valve de sortie complètement ouverte, démarrer le moteur ([[Relais Moteur]]) — l'**alimentation reste ouverte**

### 3b. Refermer l'alimentation — délai configurable après le démarrage du moteur
- Maintenir l'[[Valve Alimentation (Priming)|alimentation]] ouverte pendant un délai **configurable** (`priming.delai_fermeture_alimentation_s`, défaut **10 s**) après le démarrage du moteur
- Puis **refermer complètement** la valve d'alimentation — la laisser ouverte indéfiniment viderait la réserve d'eau

### 4. Stabilisation — 10 secondes
- Laisser le système se stabiliser pendant **10 secondes**, moteur en marche, alimentation refermée

### 5. Priming de la ligne du DRAIN DE FOND (mode duty cycle, répété 10 fois)
- Le [[Valve Drain de fond|drain de fond]] (qui part **fermé**) passe en mode priming par impulsions :
  - Ouvrir la valve par une **impulsion d'ouverture** de courte durée (par défaut **0.5 s**, voir [[Contrôle des valves (H-bridge)]])
  - La **refermer immédiatement**
  - **Répéter ce cycle 10 fois**

### 6. Ouverture complète et fin de la séquence
- Après les 10 cycles, ouvrir **complètement** le [[Valve Drain de fond|drain de fond]]
- Le système est alors considéré **fonctionnel** — la séquence de démarrage avec priming est terminée

À la fin de cette séquence, le système passe à l'état `EN_MARCHE` (voir la section *État du système* de [[Programme Raspberry Pi (Python)]]).

## Résumé visuel

```
t=0s   : Écumoire OUVERTE (complète), Alimentation OUVERTE (injection d'eau)
t=15s  : Sortie (retour) OUVERTE (complète) — Alimentation toujours OUVERTE
t≈30s  : Moteur ON (une fois la sortie complètement ouverte) — Alimentation toujours OUVERTE
+10s   : Alimentation FERMÉE (délai configurable après démarrage moteur)
+10s   : Fin de la stabilisation
ensuite: Drain de fond → 10x [impulsion 0.5 s → fermeture immédiate]
puis   : Drain de fond OUVERT (complet) — système fonctionnel
```

> [!note] Paramètres à calibrer (modifiables dans l'[[Interface Web (Pi)]])
> Les durées (amorçage, délai de fermeture de l'alimentation, stabilisation), le nombre de cycles et la durée d'impulsion du jerk sont éditables depuis l'interface web (`config.json`). La **course complète d'une valve est d'environ 15 secondes** (mesurée sur le matériel — voir [[Contrôle des valves (H-bridge)]]).

Voir [[Programme Raspberry Pi (Python)]] pour l'implémentation (c'est le Pi qui gère tous ces délais et envoie les commandes primitives à l'Arduino une à une), [[Séquence de démarrage]] pour la version simple (bouton vert), et [[Séquence d'arrêt]] pour la procédure d'arrêt.
