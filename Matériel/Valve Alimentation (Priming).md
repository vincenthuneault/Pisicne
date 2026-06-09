---
tags: [piscine, matériel, valve, h-bridge, priming]
---

# Valve Alimentation (Priming)

- **Broches Arduino** : D7, D8
- **Type de commande** : H-bridge (pont en H, 2 broches numériques)
- **Fonction** : valve d'alimentation en eau, utilisée pour deux usages distincts — le **priming** au démarrage et l'**ajout d'eau** en cours de fonctionnement

## Usage 1 — Priming au démarrage

Avant de démarrer la pompe, cette valve est **ouverte complètement** pour remplir/amorcer le circuit avec de l'eau, ce qui évite de faire fonctionner le moteur à sec (risque de dommage). Une fois le priming terminé, la valve est **refermée complètement** et le [[Relais Moteur]] est activé. Voir [[Séquence de démarrage]].

## Usage 2 — Ajout d'eau pendant le fonctionnement

Lorsque le système est déjà en marche, cette valve peut être ouverte **partiellement à environ 10 %** et maintenue ainsi pendant **1 heure**, afin que la source d'alimentation puisse fournir un débit soutenu sans s'épuiser. Voir [[Séquence d'ajout d'eau]].

## Commande

Pilotée comme les autres valves motorisées via [[Contrôle des valves (H-bridge)|le principe générique de commande H-bridge]] : D7/D8 = `1`/`0` pour ouvrir, `0`/`1` pour fermer, `0`/`0` pour arrêter. Course complète ≈ 10 secondes.

- **Priming** : ouverture/fermeture **complète** (≈ 10 s de polarité appliquée)
- **Ajout d'eau** : ouverture **partielle** (≈ 1 s de polarité d'ouverture ≈ 10 %, puis arrêt `0`/`0`, maintenue 1 heure, puis fermeture complète)

Voir aussi [[Valve Écumoire]], [[Valve Drain de fond]], [[Valve Retour Piscine]] et [[Brochage Arduino]].
