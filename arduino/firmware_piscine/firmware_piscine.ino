/*
 * Firmware Piscine — interface matérielle « bête » pour le Raspberry Pi
 *
 * Ce programme NE CONTIENT AUCUNE LOGIQUE DE SÉQUENCE. Il se contente :
 *   - d'exécuter des commandes primitives reçues du Raspberry Pi en JSON
 *     (ouvrir/fermer/arrêter une valve, démarrer/arrêter le moteur)
 *   - de rapporter immédiatement au Pi chaque appui sur un bouton, en JSON
 *
 * Toute la logique (séquences, minutage, état du système, priorité du
 * bouton rouge) vit dans le programme Python du Raspberry Pi.
 * Voir la documentation Obsidian : Architecture, Firmware Arduino,
 * Communication Série, Brochage Arduino.
 *
 * Liaison série : JSON, 115200 bauds.
 * Bibliothèque requise : ArduinoJson (https://arduinojson.org/)
 *
 * Conception non bloquante : aucun delay() long n'est utilisé, afin que
 * la lecture des boutons (en particulier le bouton rouge, prioritaire)
 * reste réactive en tout temps.
 */

#include <ArduinoJson.h>

// ===================== Brochage =====================

// NOTE : le relais moteur n'a PAS de broche assignée pour l'instant.
// L'ancienne broche D1 ne peut pas être utilisée (= TX du port série,
// pilotée par Serial). Les commandes moteur_demarrer/moteur_arreter sont
// conservées sous forme de stubs (voir traiterCommandeEntrante) en attendant
// le recâblage sur une broche libre (ex. D2).
// TODO: réassigner le relais moteur à une broche libre (pas D0/D1 = série).

const uint8_t PIN_ECUMOIRE_A     = 3;
const uint8_t PIN_ECUMOIRE_B     = 4;
const uint8_t PIN_DRAIN_A        = 5;
const uint8_t PIN_DRAIN_B        = 6;
const uint8_t PIN_ALIMENTATION_A = 7;
const uint8_t PIN_ALIMENTATION_B = 8;
const uint8_t PIN_RETOUR_A       = 9;
const uint8_t PIN_RETOUR_B       = 10;

// NOTE : le bouton bleu n'a PAS de broche assignée pour l'instant.
// L'ancienne broche D13 ne peut pas être utilisée de façon fiable en entrée
// (= LED intégrée de la carte, qui fausse INPUT_PULLUP). En attendant son
// recâblage (ex. A0), le déclenchement « bouton bleu » se fait via
// l'interface web du Raspberry Pi.
// TODO: réassigner le bouton bleu à une broche libre (ex. A0).
const uint8_t PIN_BOUTON_VERT  = 11;
const uint8_t PIN_BOUTON_ROUGE = 12;

// ===================== Valves (H-bridge L298N, Enable toujours actif) =====================
//
// Polarité :  IO A | IO B | Effet
//              1   |  0   | ouvre
//              0   |  1   | ferme
//              0   |  0   | arrêt (aucune consommation, position maintenue)
//
// Le Pi fournit toujours une durée (duree_ms). Cette durée permet :
//   - une course complète (≈10000 ms) pour ouvrir/fermer entièrement
//   - une impulsion plus courte pour une ouverture partielle / un priming
// Une fois la durée écoulée, la valve est automatiquement remise à l'arrêt
// (0/0) — c'est ce mécanisme non bloquant qui remplace un delay().

enum Mouvement { ARRET, OUVERTURE, FERMETURE };

struct Valve {
  const char* nom;
  uint8_t pinA;
  uint8_t pinB;
  Mouvement mouvement;
  unsigned long finMouvement; // millis() cible ; 0 = pas de limite de temps
};

Valve valves[] = {
  { "ecumoire",     PIN_ECUMOIRE_A,     PIN_ECUMOIRE_B,     ARRET, 0 },
  { "drain",        PIN_DRAIN_A,        PIN_DRAIN_B,        ARRET, 0 },
  { "alimentation", PIN_ALIMENTATION_A, PIN_ALIMENTATION_B, ARRET, 0 },
  { "retour",       PIN_RETOUR_A,       PIN_RETOUR_B,       ARRET, 0 },
};
const uint8_t NB_VALVES = sizeof(valves) / sizeof(valves[0]);

// ===================== Boutons (pull-up : repos = HIGH, pressé = LOW) =====================

struct Bouton {
  const char* nom;
  uint8_t pin;
  bool dernierEtatBrut;
  bool etatStable;
  unsigned long dernierChangement;
};

Bouton boutons[] = {
  { "vert",  PIN_BOUTON_VERT,  HIGH, HIGH, 0 },
  { "rouge", PIN_BOUTON_ROUGE, HIGH, HIGH, 0 },
  // « bleu » retiré pour l'instant (ancienne broche D13 = LED intégrée) —
  // déclenchement via l'interface web du Pi. Voir note de brochage ci-dessus.
};
const uint8_t NB_BOUTONS = sizeof(boutons) / sizeof(boutons[0]);
const unsigned long ANTI_REBOND_MS = 50;

// ===================== Initialisation =====================

void setup() {
  Serial.begin(115200);

  // Le relais moteur n'a pas de broche assignée pour l'instant (voir brochage).
  // Rien à initialiser ici ; moteur_demarrer/arreter sont des stubs.

  // État sûr par défaut : toutes les valves à l'arrêt (polarité 0/0)
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    pinMode(valves[i].pinA, OUTPUT);
    pinMode(valves[i].pinB, OUTPUT);
    arreterValve(i);
  }

  for (uint8_t i = 0; i < NB_BOUTONS; i++) {
    pinMode(boutons[i].pin, INPUT_PULLUP);
  }
}

// ===================== Boucle principale (non bloquante) =====================

void loop() {
  traiterCommandeEntrante();
  mettreAJourValves();
  surveillerBoutons();
}

// ===================== Commande des valves =====================

void appliquerPolarite(uint8_t i, Mouvement mouvement) {
  Valve &v = valves[i];
  switch (mouvement) {
    case OUVERTURE:
      digitalWrite(v.pinA, HIGH);
      digitalWrite(v.pinB, LOW);
      break;
    case FERMETURE:
      digitalWrite(v.pinA, LOW);
      digitalWrite(v.pinB, HIGH);
      break;
    default:
      digitalWrite(v.pinA, LOW);
      digitalWrite(v.pinB, LOW);
      break;
  }
  v.mouvement = mouvement;
}

void ouvrirValve(uint8_t i, unsigned long dureeMs) {
  appliquerPolarite(i, OUVERTURE);
  valves[i].finMouvement = (dureeMs > 0) ? millis() + dureeMs : 0;
}

void fermerValve(uint8_t i, unsigned long dureeMs) {
  appliquerPolarite(i, FERMETURE);
  valves[i].finMouvement = (dureeMs > 0) ? millis() + dureeMs : 0;
}

void arreterValve(uint8_t i) {
  appliquerPolarite(i, ARRET);
  valves[i].finMouvement = 0;
}

int trouverValve(const char* nom) {
  if (nom == nullptr) return -1;
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    if (strcmp(valves[i].nom, nom) == 0) return i;
  }
  return -1;
}

// Coupe automatiquement le mouvement d'une valve une fois sa durée écoulée
// (équivalent non bloquant d'un "ouvrir pendant X ms puis arrêter").
void mettreAJourValves() {
  unsigned long maintenant = millis();
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    if (valves[i].mouvement != ARRET
        && valves[i].finMouvement != 0
        && (long)(maintenant - valves[i].finMouvement) >= 0) {
      arreterValve(i);
    }
  }
}

// ===================== Lecture des boutons =====================

void surveillerBoutons() {
  unsigned long maintenant = millis();
  for (uint8_t i = 0; i < NB_BOUTONS; i++) {
    bool lecture = digitalRead(boutons[i].pin);

    if (lecture != boutons[i].dernierEtatBrut) {
      boutons[i].dernierChangement = maintenant;
      boutons[i].dernierEtatBrut = lecture;
    }

    if ((maintenant - boutons[i].dernierChangement) > ANTI_REBOND_MS
        && lecture != boutons[i].etatStable) {
      boutons[i].etatStable = lecture;
      if (lecture == LOW) { // pull-up : LOW = pressé (front descendant stable)
        envoyerEvenementBouton(boutons[i].nom);
      }
    }
  }
}

void envoyerEvenementBouton(const char* nomBouton) {
  StaticJsonDocument<64> doc;
  doc["event"] = "bouton";
  doc["nom"] = nomBouton;
  serializeJson(doc, Serial);
  Serial.println();
}

// ===================== Communication série (commandes JSON du Pi) =====================
//
// Commandes reconnues (un objet JSON par ligne, terminé par '\n') :
//   {"cmd":"valve_ouvrir",  "valve":"<nom>", "duree_ms": <n>}
//   {"cmd":"valve_fermer",  "valve":"<nom>", "duree_ms": <n>}
//   {"cmd":"valve_arreter", "valve":"<nom>"}
//   {"cmd":"moteur_demarrer"}
//   {"cmd":"moteur_arreter"}
//   {"cmd":"etat_boutons"}
// noms de valve : "ecumoire", "drain", "alimentation", "retour"

void traiterCommandeEntrante() {
  if (!Serial.available()) return;

  StaticJsonDocument<128> doc;
  DeserializationError erreur = deserializeJson(doc, Serial);
  if (erreur) return; // ligne incomplète ou invalide : ignorée

  const char* commande = doc["cmd"];
  if (commande == nullptr) return;

  if (strcmp(commande, "valve_ouvrir") == 0) {
    int i = trouverValve(doc["valve"]);
    if (i >= 0) ouvrirValve(i, doc["duree_ms"] | 0UL);
    repondreOk(commande);
  }
  else if (strcmp(commande, "valve_fermer") == 0) {
    int i = trouverValve(doc["valve"]);
    if (i >= 0) fermerValve(i, doc["duree_ms"] | 0UL);
    repondreOk(commande);
  }
  else if (strcmp(commande, "valve_arreter") == 0) {
    int i = trouverValve(doc["valve"]);
    if (i >= 0) arreterValve(i);
    repondreOk(commande);
  }
  else if (strcmp(commande, "moteur_demarrer") == 0) {
    // STUB : aucune broche relais assignée pour l'instant (ex-D1 = TX série).
    // TODO: piloter la broche du relais moteur une fois recâblé (ex. D2).
    repondreOk(commande);
  }
  else if (strcmp(commande, "moteur_arreter") == 0) {
    // STUB : aucune broche relais assignée pour l'instant (ex-D1 = TX série).
    // TODO: piloter la broche du relais moteur une fois recâblé (ex. D2).
    repondreOk(commande);
  }
  else if (strcmp(commande, "etat_boutons") == 0) {
    envoyerEtatBoutons();
  }
}

void repondreOk(const char* commande) {
  StaticJsonDocument<64> doc;
  doc["status"] = "ok";
  doc["cmd"] = commande;
  serializeJson(doc, Serial);
  Serial.println();
}

void envoyerEtatBoutons() {
  StaticJsonDocument<128> doc;
  JsonObject etats = doc.createNestedObject("boutons");
  for (uint8_t i = 0; i < NB_BOUTONS; i++) {
    etats[boutons[i].nom] = (boutons[i].etatStable == LOW);
  }
  serializeJson(doc, Serial);
  Serial.println();
}
