---
tags: [piscine, logiciel, séquence, priming, démarrage]
---

# Séquence de démarrage avec priming des tuyaux

Exécutée par le [[Programme Raspberry Pi (Python)|programme Python du Raspberry Pi]] (voir [[Architecture]] pour le choix d'architecture « Pi chef d'orchestre » — l'Arduino ne fait qu'exécuter les commandes primitives reçues), déclenchée par un appui sur le **bouton bleu** ([[Boutons de contrôle]]) **lorsque le système est éteint** (comportement conditionnel), ou par la commande à distance correspondante.

Comme pour toutes les séquences, un appui sur le **bouton rouge** interrompt celle-ci immédiatement, à n'importe quelle étape (y compris en plein milieu d'une attente ou d'un cycle de priming), et bascule vers la [[Séquence d'arrêt]] (priorité absolue — voir cette note).

## Différence avec le bouton vert

Cette séquence est **différente** de la [[Séquence de démarrage]] simple déclenchée par le bouton vert : elle ré-amorce (« prime ») les tuyaux du système avant de le considérer pleinement fonctionnel. Elle est destinée aux cas où le système est resté éteint assez longtemps pour que les conduites aient perdu leur amorçage (perte de prime / air dans les lignes) — ce qui exige un redémarrage progressif et contrôlé pour **éviter que la pompe ne tourne dans le vide**, compte tenu de la position du système par rapport à la piscine (voir [[Contexte et objectifs]]).

## Étapes

### 1. Amorçage initial — 15 secondes
- Ouvrir **complètement** la [[Valve Écumoire]]
- Ouvrir la [[Valve Alimentation (Priming)|valve d'alimentation en eau]]
- Maintenir cet état pendant **15 secondes**

### 2. Ouverture de la sortie
- Une fois les 15 secondes écoulées, ouvrir **complètement** la [[Valve Retour Piscine|valve de sortie (retour vers la piscine)]]

### 3. Démarrage du moteur
- Une fois la valve de sortie complètement ouverte, démarrer le moteur ([[Relais Moteur]])

### 4. Stabilisation — 10 secondes
- Laisser le système se stabiliser pendant **10 secondes**, moteur en marche

### 5. Priming de la ligne de l'écumoire (mode duty cycle, répété 10 fois)
- La [[Valve Écumoire]] passe en mode priming par impulsions :
  - Ouvrir la valve à environ **5 %** (impulsion d'ouverture de **0.5 seconde**, sur la base d'une course complète de 10 secondes — voir [[Contrôle des valves (H-bridge)]])
  - La **refermer immédiatement**
  - **Répéter ce cycle 10 fois**

### 6. Ouverture complète et fin de la séquence
- Après les 10 cycles, ouvrir **complètement** la [[Valve Écumoire]]
- Le système est alors considéré **fonctionnel** — la séquence de démarrage avec priming est terminée

À la fin de cette séquence, le système passe à l'état `EN_MARCHE` (voir la section *État du système* de [[Programme Raspberry Pi (Python)]]).

## Résumé visuel

```
t=0s   : Écumoire OUVERTE (complète), Alimentation OUVERTE
t=15s  : Sortie (retour) OUVERTE (complète)
t=15s+ : Moteur ON (une fois la sortie complètement ouverte)
t=25s  : Fin de la stabilisation (10 s)
t=25s+ : Écumoire → 10x [impulsion 0.5 s (~5 %) → fermeture immédiate]
ensuite: Écumoire OUVERTE (complète) — système fonctionnel
```

> [!note] Paramètres à calibrer
> Les durées (15 s, 10 s), le nombre de cycles (10) et le degré d'ouverture (~5 % via 0.5 s) sont des valeurs fournies par le concepteur du système ; elles pourront être ajustées si le comportement réel le justifie.

Voir [[Programme Raspberry Pi (Python)]] pour l'implémentation (c'est le Pi qui gère tous ces délais et envoie les commandes primitives à l'Arduino une à une), [[Séquence de démarrage]] pour la version simple (bouton vert), et [[Séquence d'arrêt]] pour la procédure d'arrêt.
