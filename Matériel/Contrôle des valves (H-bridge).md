---
tags: [piscine, matériel, valve, h-bridge, référence]
---

# Contrôle des valves (H-bridge)

Les quatre valves motorisées du système ([[Valve Écumoire]], [[Valve Drain de fond]], [[Valve Alimentation (Priming)]], [[Valve Retour Piscine]]) sont chacune pilotées par un **H-bridge L298N** sur **2 broches numériques** (les entrées de direction `IN1`/`IN2` du canal correspondant). Le principe de commande est identique pour les quatre — seules les broches changent (voir [[Brochage Arduino]]).

Cette note documente le principe **générique** de commande, destiné à être implémenté comme une **fonction réutilisable** dans le [[Firmware Arduino]] (ex. : `ouvrirValve(pinA, pinB, durée)`).

> [!note] Broche Enable du L298N
> Le L298N possède aussi une broche **Enable** par canal (`ENA`/`ENB`), qui doit être active pour que le pont en H fonctionne. Dans ce système, l'Enable est **toujours actif** — elle n'a donc pas besoin d'être pilotée dynamiquement par l'Arduino (câblée à l'état actif en permanence, ex. reliée au +5V). Seules les deux broches de direction (`IN1`/`IN2`) sont commandées, ce qui correspond au [[Brochage Arduino|brochage documenté]] (2 broches par valve).

## Principe de commande

| IO A | IO B | Effet |
|---|---|---|
| `1` | `0` | Le moteur de la valve **ouvre** (polarité dans un sens) |
| `0` | `1` | Le moteur de la valve **ferme** (polarité inversée) |
| `0` | `0` | Le moteur **s'arrête** (aucune polarité appliquée) |

### Points clés

- **Course complète** : ouvrir ou fermer une valve **au complet** prend environ **15 secondes** (mesuré sur le matériel ; paramètre `course_complete_ms`, modifiable dans l'[[Interface Web (Pi)]]).
- **Maintien de la polarité** : la polarité peut être maintenue indéfiniment une fois la valve en position — le moteur **arrête de consommer** du courant lorsqu'il atteint la butée de fin de course. Il n'est donc pas nécessaire de couper les IO après une ouverture/fermeture complète.
- **Inversion pour fermer** : il suffit d'inverser la polarité (IO A ↔ IO B) pour faire fermer une valve précédemment ouverte.
- **Arrêt en cours de course** : pour interrompre le mouvement (par ex. obtenir une **ouverture partielle**), les **deux IO doivent être mis à `0`**.

## Ouverture partielle (par minutage)

Le degré d'ouverture peut être contrôlé en chronométrant la durée pendant laquelle la polarité d'ouverture est appliquée, **proportionnellement à la course complète de 10 secondes**. Par exemple :

| Durée d'ouverture appliquée | Ouverture résultante (≈) |
|---|---|
| 1 seconde | ~10 % |
| 0.5 seconde | ~5 % |
| 10 secondes | 100 % (complètement ouverte) |

Procédure : appliquer la polarité d'ouverture (`1`/`0`) pendant la durée voulue, puis remettre les deux IO à `0` pour arrêter le mouvement à ce degré d'ouverture.

> [!note]
> Cette relation est approximative et suppose une vitesse de course constante — à valider/calibrer empiriquement sur le matériel réel.

## Utilisation dans le système

- **Ouverture/fermeture complète** — utilisée pour la majorité des opérations (ex. : [[Valve Écumoire]], [[Valve Retour Piscine]] et [[Valve Alimentation (Priming)]] dans la [[Séquence de démarrage]])
- **Ouverture partielle répétée (duty cycle)** — utilisée pour le **mode priming** de l'[[Valve Écumoire|écumoire]] dans la [[Séquence de démarrage avec priming]], où de courtes impulsions d'ouverture suivies de fermetures permettent d'amorcer la ligne graduellement sans déprimer le moteur
- **Ouverture partielle maintenue** — utilisée pour la [[Valve Alimentation (Priming)|valve d'alimentation]] dans la [[Séquence d'ajout d'eau]] (ouverture à ~10 %, maintenue pendant 1 heure)

> [!note] Contrôle en boucle ouverte
> Le système ne dispose d'aucun capteur de rétroaction (fin de course, débit, pression) — voir [[Programme Raspberry Pi (Python)]]. Tous les minutages ci-dessus sont des valeurs fixes déterminées à l'avance ; le système fait une confiance totale à ces durées.
