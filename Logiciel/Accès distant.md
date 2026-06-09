---
tags: [piscine, logiciel, accès-distant]
---

# Accès distant

> [!info] Une interface web **locale** existe désormais
> Une première brique concrète est en place : l'**[[Interface Web (Pi)]]**, servie par le Pi sur
> le réseau **local** (`http://<pi>:8080`). Elle permet déjà de contrôler le système, d'ajuster
> les paramètres et de reprogrammer l'Arduino. Cette présente note couvre la suite : l'accès
> **depuis l'extérieur** (Internet), qui reste **reporté**.

> [!warning] Accès Internet : reporté — pas pour le moment
> L'accès à distance **depuis l'extérieur** n'est pas implémenté. Cette note décrit l'intention à long terme (exposition sécurisée, VPN/tunnel, authentification) ; ce n'est pas une priorité tant que l'automatisation locale et l'[[Interface Web (Pi)|interface web locale]] suffisent.

Le [[Raspberry Pi 3]] est destiné à éventuellement centraliser l'**accès à distance** au système de filtration de la piscine, en plus d'agir comme cerveau de l'automatisation. Cette fonctionnalité ferait partie du [[Programme Raspberry Pi (Python)|programme Python]] qui s'exécute sur le Pi.

## Objectifs (vision à long terme)

- Permettre de consulter l'état du système à distance (moteur en marche/arrêt, état des valves, niveau d'eau, etc.)
- Permettre de déclencher les mêmes actions que les [[Boutons de contrôle|boutons physiques]] (lancement, arrêt, ajout d'eau) depuis l'extérieur
- Recevoir des notifications/alertes en cas de problème (ex. : échec du priming, arrêt inattendu)

## Points à documenter

- Méthode d'accès (interface web, application, VPN/tunnel, API, etc.) et bibliothèque/framework Python utilisé (ex. `Flask`, `FastAPI`)
- Mécanisme d'authentification et de sécurisation de l'accès
- Interaction avec la logique d'automatisation décrite dans [[Programme Raspberry Pi (Python)]] et [[Communication Série]]

> [!note]
> Section à compléter au fur et à mesure du choix et du développement de la solution d'accès distant.

Voir [[Architecture]] pour le contexte global du système.
