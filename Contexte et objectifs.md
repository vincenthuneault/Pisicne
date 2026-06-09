---
tags: [piscine, contexte, contraintes]
---
Peux 
# Contexte et objectifs du projet

## Situation physique

Le système de filtration est situé à environ **50 pieds de la piscine** et **6 pieds au-dessus du niveau de l'eau**. Cette différence de hauteur et de distance crée une contrainte importante : le système peut se **déprimer** (perdre son amorçage / faire le vide) lorsque les valves d'entrée et de sortie sont fermées puis rouvertes sans précaution.

## Pourquoi automatiser

Plusieurs situations exigent de **fermer les valves d'entrée et de sortie** du système :

1. **Réduction de la consommation électrique** — fermer le système (et donc la pompe) lorsque la filtration n'est pas nécessaire.
2. **Maintenance du filtre / du moteur** — il faut isoler le système de la piscine avant d'intervenir.
3. **Ajout de chlore dans le Nature2** — nécessite d'ouvrir le système, donc de l'isoler au préalable.

> [!important] Règle fondamentale
> Dans **tous** ces cas, les valves d'**entrée** ([[Valve Écumoire]] / [[Valve Drain de fond]]) et de **sortie** ([[Valve Retour Piscine]]) doivent être fermées avant d'ouvrir le système.

## Le problème : la dépression

Si le système est rouvert (moteur démarré) alors qu'il est **déprimé** (vide d'eau / sous vide d'air), la **pompe tourne dans le vide** — ce qui peut l'endommager et empêche toute filtration.

## La solution : une séquence de redémarrage contrôlée

Pour éviter ce problème dans les cas où les tuyaux ont perdu leur amorçage, le redémarrage du système doit suivre une **séquence précise** d'ouverture des valves et de démarrage du moteur, détaillée dans [[Séquence de démarrage avec priming]] (déclenchée par le bouton bleu lorsque le système est éteint). Le bouton vert, lui, déclenche une [[Séquence de démarrage|séquence de démarrage simple]], pour les cas où les tuyaux sont déjà amorcés. Ces séquences sont au cœur de la logique implémentée dans le [[Firmware Arduino]].

Voir aussi [[Architecture]] pour la vue d'ensemble technique du système.
