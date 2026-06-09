---
tags: [piscine, matériel, arduino]
---

# Arduino Uno

Interface matérielle entre le [[Raspberry Pi 3]] et le matériel physique du système de filtration.

## Connexion

- Branché au Raspberry Pi 3 par **USB**.
- Cette connexion sert à la fois de **liaison de communication** ([[Communication Série]]) et de **lien de programmation**, ce qui permet de reprogrammer l'Arduino localement, directement depuis le Raspberry Pi.

## Rôle

L'Arduino ne contient pas la logique d'automatisation : il reçoit des commandes du Raspberry Pi et/ou lit l'état des boutons physiques, puis pilote le matériel en conséquence (relais, H-bridges des valves).

## Matériel interfacé

Voir la table complète dans [[Brochage Arduino]] :

- [[Relais Moteur]] (D1)
- [[Valve Écumoire]] (D3, D4)
- [[Valve Drain de fond]] (D5, D6)
- [[Valve Alimentation (Priming)]] (D7, D8)
- [[Valve Retour Piscine]] (D9, D10)
- [[Boutons de contrôle]] (D11, D12, D13)

Voir aussi [[Firmware Arduino]] pour le code embarqué.
