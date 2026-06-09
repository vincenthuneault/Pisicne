---
tags: [piscine, matériel, raspberry-pi]
---

# Raspberry Pi 3

Le **cerveau** du système d'automatisation de la piscine.

## Rôles

- Centralise la logique d'automatisation et de séquencement (lancement, arrêt, ajout d'eau).
- Communique avec l'[[Arduino Uno]] via une connexion **USB** (voir [[Communication Série]]).
- Fournit l'**[[Accès distant]]** au système (supervision et contrôle à distance).

## Logiciel

Le programme exécuté sur le Raspberry Pi est écrit en **Python** — voir [[Programme Raspberry Pi (Python)]].

## Lien avec l'Arduino

L'Arduino Uno est branché en USB sur le Raspberry Pi. Cette même connexion permet :
- l'échange de commandes/états entre le Pi et l'Arduino,
- la **reprogrammation locale** de l'Arduino directement depuis le Raspberry Pi.

Voir [[Architecture]] pour la vue d'ensemble du système.
