---
tags: [piscine, matériel, valve, h-bridge]
---

# Valve Retour Piscine

- **Broches Arduino** : D9, D10
- **Type de commande** : H-bridge (pont en H, 2 broches numériques)
- **Fonction** : ouvre/ferme la valve qui contrôle le retour de l'eau filtrée vers la piscine

## Commande

Pilotée comme les autres valves motorisées via [[Contrôle des valves (H-bridge)|le principe générique de commande H-bridge]] : D9/D10 = `1`/`0` pour ouvrir, `0`/`1` pour fermer, `0`/`0` pour arrêter. Course complète ≈ 10 secondes. Dans le système, cette valve est ouverte/fermée **complètement** (pas de mode partiel).

Voir aussi [[Valve Écumoire]], [[Valve Drain de fond]], [[Valve Alimentation (Priming)]] et [[Brochage Arduino]].
