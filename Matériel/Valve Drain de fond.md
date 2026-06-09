---
tags: [piscine, matériel, valve, h-bridge]
---

# Valve Drain de fond

- **Broches Arduino** : D5, D6
- **Type de commande** : H-bridge (pont en H, 2 broches numériques)
- **Fonction** : ouvre/ferme la valve qui contrôle l'arrivée d'eau provenant du drain de fond (bonde de fond) vers le système de filtration

## Commande

Pilotée comme les autres valves motorisées via [[Contrôle des valves (H-bridge)|le principe générique de commande H-bridge]] : D5/D6 = `1`/`0` pour ouvrir, `0`/`1` pour fermer, `0`/`0` pour arrêter. Course complète ≈ 10 secondes. Dans le système, cette valve est ouverte/fermée **complètement** (pas de mode partiel).

Voir aussi [[Valve Écumoire]], [[Valve Alimentation (Priming)]], [[Valve Retour Piscine]] et [[Brochage Arduino]].
