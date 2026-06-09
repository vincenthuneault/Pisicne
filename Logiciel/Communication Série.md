---
tags: [piscine, logiciel, communication, série, usb]
---

# Communication Série (Raspberry Pi ↔ Arduino)

Le [[Raspberry Pi 3]] et l'[[Arduino Uno]] communiquent via la liaison **USB** qui les relie physiquement. Cette même connexion sert aussi de canal de **reprogrammation locale** de l'Arduino.

## Protocole

| Paramètre | Valeur |
|---|---|
| Format des messages | **JSON** |
| Vitesse de transmission | **115 200 bauds** |

Conformément au choix d'architecture (voir [[Architecture]] et [[Programme Raspberry Pi (Python)]]), les messages JSON se répartissent en deux catégories :

- **Pi → Arduino** : commandes primitives (ouvrir/fermer/arrêter une valve avec une durée, démarrer/arrêter le moteur, demander l'état des boutons) — voir [[Firmware Arduino]] pour la liste des commandes exposées
- **Arduino → Pi** : événements et états bruts — en particulier, **chaque appui sur un bouton** ([[Boutons de contrôle|vert, rouge, bleu]]) doit être rapporté **immédiatement**, car c'est le Pi qui décide ensuite de la séquence à exécuter (voir [[Programme Raspberry Pi (Python)]])

> [!important] Réactivité requise pour le bouton rouge
> Le bouton rouge a une **priorité absolue** (voir [[Séquence d'arrêt]]) : l'Arduino doit le rapporter au Pi sans délai, et le Pi doit pouvoir traiter ce message **même pendant l'exécution d'une commande ou l'attente d'une réponse**, afin d'interrompre immédiatement toute séquence en cours.

## Schéma des messages (implémenté)

Chaque message est un objet JSON sur une seule ligne, terminé par `\n`. Noms de valves utilisés partout : `ecumoire`, `drain`, `alimentation`, `retour`.

**Pi → Arduino** (commandes primitives) :

| Message | Effet |
|---|---|
| `{"cmd":"valve_ouvrir","valve":"<nom>","duree_ms":<n>}` | Ouvre la valve pendant `n` ms, puis arrêt automatique |
| `{"cmd":"valve_fermer","valve":"<nom>","duree_ms":<n>}` | Ferme la valve pendant `n` ms, puis arrêt automatique |
| `{"cmd":"valve_arreter","valve":"<nom>"}` | Coupe immédiatement la polarité (`0`/`0`) |
| `{"cmd":"moteur_demarrer"}` | Active le relais moteur |
| `{"cmd":"moteur_arreter"}` | Désactive le relais moteur |
| `{"cmd":"etat_boutons"}` | Demande l'état courant des trois boutons |

**Arduino → Pi** (événements et réponses) :

| Message | Sens |
|---|---|
| `{"event":"bouton","nom":"<vert\|rouge>"}` | Un bouton vient d'être pressé (rapporté immédiatement, anti-rebond déjà appliqué) |
| `{"status":"ok","cmd":"<commande>"}` | Accusé de réception d'une commande primitive |
| `{"boutons":{"vert":<bool>,"rouge":<bool>}}` | Réponse à `etat_boutons` |

> [!note] Bouton bleu retiré, moteur en stub
> Le **bouton bleu (D13)** est temporairement retiré (voir [[Brochage Arduino]]) : l'Arduino ne
> rapporte donc plus que `vert` et `rouge`. Son rôle est déclenché via l'[[Interface Web (Pi)]].
> Les commandes `moteur_demarrer`/`moteur_arreter` restent dans le protocole mais sont des
> **stubs** côté firmware (relais D1 non câblé) — elles répondent quand même `{"status":"ok",…}`.

Bibliothèques utilisées : `pyserial` côté Python, `ArduinoJson` côté firmware.

> [!note]
> Le programme Python lit en continu sur un thread dédié et place les événements dans une file, afin de ne jamais bloquer la boucle principale — voir [[Implémentation des programmes]].

Voir [[Architecture]], [[Programme Raspberry Pi (Python)]] et [[Firmware Arduino]].
