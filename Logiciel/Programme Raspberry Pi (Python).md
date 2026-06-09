---
tags: [piscine, logiciel, raspberry-pi, python]
---

# Programme Raspberry Pi (Python)

Le logiciel exécuté sur le [[Raspberry Pi 3]] — le **cerveau** du système — est écrit en **Python**.

## Choix d'architecture : le Pi orchestre, l'Arduino exécute

Le système suit le modèle **« Pi chef d'orchestre / Arduino interface bête »** :

- L'**[[Arduino Uno]]** ne connaît **aucune séquence**. Il expose des **commandes primitives** (ouvrir/fermer/arrêter une valve, démarrer/arrêter le moteur, lire les boutons) et rapporte les événements bruts (appuis sur boutons) — voir [[Firmware Arduino]].
- Le **programme Python du Pi** contient **toute la logique** : séquencement, minutage (délais, duty cycles, durées d'une heure, etc.), décisions conditionnelles (comportement du bouton bleu), suivi de l'état global du système, et gestion des priorités/interruptions.

Ce choix centralise la complexité côté Pi (plus simple à développer/déboguer/modifier qu'un firmware embarqué) et garde l'Arduino simple et fiable.

## Rôles

- **Recevoir les événements** de l'Arduino (appuis sur les boutons [[Boutons de contrôle|vert, rouge, bleu]]) via [[Communication Série|le lien série JSON]]
- **Décider et exécuter les séquences** appropriées en fonction de l'événement et de l'état courant du système :
  - [[Séquence de démarrage]] (bouton vert)
  - [[Séquence de démarrage avec priming]] (bouton bleu, système éteint)
  - [[Séquence d'arrêt]] (bouton rouge)
  - [[Séquence d'ajout d'eau]] (bouton bleu, système en marche)
- **Piloter l'Arduino** en lui envoyant, dans l'ordre voulu et avec ses propres délais (`time.sleep` ou minuterie non bloquante), les commandes primitives nécessaires à chaque séquence
- **Maintenir l'état global du système** (`EN_MARCHE` / `ÉTEINT`) — voir ci-dessous
- Exposer l'**[[Accès distant]]** *(reporté — voir cette note)*

## État du système

Le programme Python garde en mémoire un **état global** (`EN_MARCHE` / `ÉTEINT`), qui détermine notamment le comportement conditionnel du **bouton bleu** (voir [[Boutons de contrôle]]) :

| État courant | Appui sur bouton bleu déclenche |
|---|---|
| `EN_MARCHE` | [[Séquence d'ajout d'eau]] |
| `ÉTEINT` | [[Séquence de démarrage avec priming]] |

Cet état est mis à jour à la fin de chaque séquence :
- [[Séquence de démarrage]] ou [[Séquence de démarrage avec priming]] → `EN_MARCHE`
- [[Séquence d'arrêt]] → `ÉTEINT`

### État par défaut / récupération après un plantage

> [!important] Sécurité par défaut
> Si le programme plante ou redémarre (et plus généralement à l'initialisation), l'**état par défaut du système doit être `ÉTEINT`**. Le programme ne doit jamais *présumer* que le système est en marche après un redémarrage — par sécurité, il faut considérer le système éteint et, si nécessaire, exécuter une [[Séquence d'arrêt|séquence d'arrêt]] de sécurité (couper le moteur, fermer les valves) avant de reprendre une utilisation normale.

## Bouton rouge — priorité absolue (interruption)

Le bouton rouge a une **priorité absolue sur tout** : dès que son appui est rapporté par l'Arduino, le programme doit **immédiatement interrompre** toute séquence en cours (peu importe l'étape où elle se trouve) et exécuter la [[Séquence d'arrêt]] : couper le moteur **en premier**, puis fermer toutes les valves.

Conséquences pour l'implémentation :
- Les séquences ne doivent pas être de simples blocs de code séquentiels et bloquants — il faut une structure capable de **vérifier en continu** (ou réagir à un événement asynchrone) si le bouton rouge a été pressé, à tout moment, y compris au milieu d'une attente ou d'un duty cycle
- Approches possibles : machine à états avec vérifications fréquentes, tâche/thread dédié à l'écoute du port série avec un mécanisme d'interruption (event/flag) consulté entre chaque étape et pendant les attentes, etc.

> [!note] Implémentation
> Le programme complet se trouve dans `raspberry-pi/piscine.py` (voir [[Implémentation des programmes]]). Il utilise un thread de lecture série dédié, un `threading.Event` (`GestionnaireUrgence`) consulté à chaque étape et pendant chaque attente (`attendre()` interruptible, en tranches de 0.1 s), et exécute chaque séquence dans son propre thread afin que le bouton rouge puisse l'interrompre à tout moment.

## Communication avec l'Arduino

Voir [[Communication Série]] pour le détail du protocole : messages **JSON** sur liaison série USB à **115 200 bauds**.

## Contrôle en boucle ouverte

Le système fonctionne **entièrement en boucle ouverte** : aucun capteur de rétroaction (débit, pression, fin de course) ne confirme qu'une valve a atteint sa position ou que le système est correctement amorcé. Toutes les durées (course des valves, temps d'attente, duty cycles) sont des valeurs **fixes, déterminées à l'avance** par le concepteur du système (voir [[Contexte et objectifs]] et chaque séquence). Le programme doit donc faire une confiance totale à ces minutages — il n'y a pas de vérification automatique du bon déroulement d'une étape.

## Accès distant *(reporté)*

L'accès à distance n'est **pas implémenté pour le moment** — voir [[Accès distant]].

Voir [[Implémentation des programmes]] pour le code complet (Pi et Arduino), [[Firmware Arduino]] pour le pendant côté Arduino, et [[Architecture]] pour la vue d'ensemble du système.
