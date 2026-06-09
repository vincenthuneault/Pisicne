---
tags: [piscine, accueil]
---

# Projet Piscine — Automatisation du système de filtration

Système d'automatisation de la pompe filtreuse de piscine, centralisé autour d'un **Raspberry Pi 3** (programme **Python**) qui agit comme cerveau du système. Un **Arduino Uno**, connecté en USB au Raspberry Pi, sert d'**interface matérielle « bête »** : il exécute des commandes primitives (valves, relais) et rapporte les appuis sur les boutons — toute la logique de séquencement vit dans le programme Python du Pi (voir [[Architecture]]).

## Navigation

- [[Contexte et objectifs]] — pourquoi ce projet existe (contraintes physiques, risque de dépression)
- [[Architecture]] — vue d'ensemble du système et rôles des composants
- [[Brochage Arduino]] — table de référence de toutes les broches utilisées
- Matériel
  - [[Raspberry Pi 3]]
  - [[Arduino Uno]]
  - [[Contrôle des valves (H-bridge)]] — principe générique de commande, partagé par les 4 valves
  - [[Relais Moteur]]
  - [[Valve Écumoire]]
  - [[Valve Drain de fond]]
  - [[Valve Alimentation (Priming)]]
  - [[Valve Retour Piscine]]
  - [[Boutons de contrôle]]
- Logiciel
  - [[Programme Raspberry Pi (Python)]]
  - [[Firmware Arduino]]
  - [[Implémentation des programmes]] — emplacement et structure du code source (`raspberry-pi/`, `arduino/`)
  - [[Séquence de démarrage]] — simple (bouton vert)
  - [[Séquence de démarrage avec priming]] — bouton bleu, système éteint
  - [[Séquence d'arrêt]]
  - [[Séquence d'ajout d'eau]] — bouton bleu, système en marche
  - [[Communication Série]]
  - [[Interface Web (Pi)]] — page web locale : contrôle, paramètres, flashage de l'Arduino
  - [[Accès distant]] *(accès Internet reporté ; interface web locale disponible)*

## Résumé du fonctionnement

1. Le **bouton vert** déclenche la [[Séquence de démarrage|séquence de démarrage simple]] : ouvre toutes les valves et enclenche le moteur.
2. Le **bouton rouge** déclenche la [[Séquence d'arrêt|séquence d'arrêt]] : éteint le moteur, puis ferme toutes les valves — avec une **priorité absolue** qui interrompt immédiatement toute autre séquence en cours.
3. Le **bouton bleu** *(physiquement retiré pour l'instant — broche D13 inadaptée ; déclenché via l'[[Interface Web (Pi)]])* a un comportement **conditionnel à l'état du système** (voir [[Boutons de contrôle]]) :
   - Système **en marche** → [[Séquence d'ajout d'eau]] (ouverture partielle à 10 % de la valve d'alimentation, maintenue 1 heure)
   - Système **éteint** → [[Séquence de démarrage avec priming]] (réamorçage progressif des tuyaux, étapes chronométrées, mode priming par duty cycle de l'écumoire)

Toute la logique de séquencement vit dans le **programme Python du Raspberry Pi**, qui pilote l'Arduino Uno (interface matérielle « bête ») via une liaison série JSON à 115 200 bauds — voir [[Architecture]] pour le détail de ce choix.

> [!tip]
> Pour comprendre **pourquoi** ces séquences existent (position du système par rapport à la piscine, risque de dépression du moteur), voir [[Contexte et objectifs]].
