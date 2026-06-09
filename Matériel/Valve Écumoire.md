---
tags: [piscine, matériel, valve, h-bridge, priming]
---

# Valve Écumoire

- **Broches Arduino** : D3, D4
- **Type de commande** : H-bridge (pont en H, 2 broches numériques)
- **Fonction** : ouvre/ferme la valve qui contrôle l'arrivée d'eau provenant de l'écumoire (skimmer) vers le système de filtration

## Commande

Pilotée comme les autres valves motorisées via [[Contrôle des valves (H-bridge)|le principe générique de commande H-bridge]] : D3/D4 = `1`/`0` pour ouvrir, `0`/`1` pour fermer, `0`/`0` pour arrêter. Course complète ≈ 10 secondes.

C'est la **seule valve** du système utilisée en mode d'**ouverture partielle répétée** (voir ci-dessous, dans le cadre de la [[Séquence de démarrage avec priming]]) — dans tous les autres cas, elle est commandée en ouverture/fermeture complète.

## Mode priming (duty cycle)

Dans la [[Séquence de démarrage avec priming]] (déclenchée par le bouton bleu lorsque le système est éteint — voir [[Boutons de contrôle]]), cette valve est utilisée pour amorcer **graduellement** sa propre ligne, après une période de stabilisation où le système tourne déjà via le retour vers la piscine :

- La valve s'ouvre **brièvement** — une impulsion d'ouverture de **0.5 seconde** (≈ 5 % d'ouverture, sur la base d'une course complète de 10 secondes — voir [[Contrôle des valves (H-bridge)]])
- Elle est ensuite **refermée immédiatement**
- Ce cycle « impulsion de 0.5 s → fermeture immédiate » est **répété 10 fois**
- Une fois les 10 cycles complétés, la valve est **ouverte complètement** — le système est alors considéré fonctionnel

### Paramètres du duty cycle

| Paramètre | Valeur |
|---|---|
| Durée de l'impulsion d'ouverture | 0.5 seconde (≈ 5 % d'ouverture) |
| Action après l'impulsion | Fermeture immédiate |
| Nombre de cycles | 10 |
| Étape finale | Ouverture complète de la valve |

> [!note]
> Ces valeurs sont fournies par le concepteur du système ; elles pourront être ajustées si le comportement réel le justifie.

Voir aussi [[Valve Drain de fond]], [[Valve Alimentation (Priming)]], [[Valve Retour Piscine]], [[Brochage Arduino]] et [[Séquence de démarrage avec priming]].
