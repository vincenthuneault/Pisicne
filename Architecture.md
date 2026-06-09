---
tags: [piscine, architecture]
---

# Architecture du système

## Vue d'ensemble

```
[Accès distant] ──▶ [Raspberry Pi 3] ──USB──▶ [Arduino Uno] ──▶ Relais / H-bridges / Boutons
                       (cerveau)              (interface matériel)
```

- Le **[[Raspberry Pi 3]]** est le cerveau du système : il prend les décisions, gère la logique d'automatisation et expose l'**[[Accès distant|accès à distance]]** *(reporté)*. Son logiciel est écrit en **Python** — voir [[Programme Raspberry Pi (Python)]].
- L'**[[Arduino Uno]]** est connecté en **USB** au Raspberry Pi. Il sert uniquement d'interface avec le matériel (lecture des boutons, pilotage des relais et des valves) et peut être **reprogrammé localement** via cette même connexion USB.
- La communication entre les deux se fait via [[Communication Série|liaison série JSON, à 115 200 bauds, sur USB]].

> [!important] Choix d'architecture : « Pi chef d'orchestre / Arduino interface bête »
> L'**Arduino ne contient aucune logique de séquence**. Il expose uniquement des **commandes primitives** (ouvrir/fermer/arrêter une valve, démarrer/arrêter le moteur, lire les boutons) et rapporte les événements bruts (appuis sur boutons) au Pi. C'est le **programme Python du Pi** qui contient toute la logique : décision de la séquence à exécuter, minutage (délais, duty cycles, durées d'une heure), suivi de l'état global du système (`EN_MARCHE`/`ÉTEINT`), et gestion de la **priorité absolue du bouton rouge** (interruption immédiate de toute séquence en cours). Le système fonctionne entièrement **en boucle ouverte** : aucun capteur de rétroaction ne confirme le bon déroulement d'une étape — voir [[Programme Raspberry Pi (Python)]] pour le détail.

## Répartition des responsabilités

| Composant | Rôle | Logiciel |
|---|---|---|
| Raspberry Pi 3 | Logique d'automatisation, séquencement, accès à distance, interface utilisateur | [[Programme Raspberry Pi (Python)|Python]] |
| Arduino Uno | Interface matérielle temps réel : lecture des boutons, commande des relais et des H-bridges | [[Firmware Arduino|C/C++ (Arduino)]] |

## Composants matériels pilotés par l'Arduino

- [[Relais Moteur]] — alimentation du moteur de la pompe
- [[Valve Écumoire]] — H-bridge
- [[Valve Drain de fond]] — H-bridge
- [[Valve Alimentation (Priming)]] — alimentation en eau pour le priming avant le lancement du moteur
- [[Valve Retour Piscine]] — retour de l'eau vers la piscine
- [[Boutons de contrôle]] — bouton vert (lancement), rouge (arrêt), bleu (ajout d'eau)

Voir la table complète des broches dans [[Brochage Arduino]].
