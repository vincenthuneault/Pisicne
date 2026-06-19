/*
 * Firmware Piscine — interface matérielle « bête » pour le Raspberry Pi
 *
 * Ce programme NE CONTIENT AUCUNE LOGIQUE DE SÉQUENCE. Il se contente :
 *   - d'exécuter des commandes primitives reçues du Raspberry Pi en JSON
 *     (ouvrir/fermer/arrêter une valve, démarrer/arrêter le moteur)
 *   - de rapporter immédiatement au Pi chaque appui sur un bouton, en JSON
 *   - de rapporter, sur demande, l'état de ses sorties (etat_sorties)
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
 *
 * ===================== Mémoire d'état SANS capteur =====================
 *
 * Le système est en BOUCLE OUVERTE (aucun capteur de position). Pour
 * permettre au Pi de récupérer l'état après un redémarrage, l'Arduino
 * encode l'état ENGAGÉ de chaque valve dans le repos de son pont en H :
 *
 *     repos « ouvert »  = FREIN  (A=1, B=1)   ← l'eau passe
 *     repos « fermé »   = NEUTRE (A=0, B=0)
 *
 * Les deux repos n'ENTRAÎNENT pas le moteur (pas de différentiel) : la
 * valve tient sa position mécaniquement. Le motif 11 / 00 sert uniquement
 * de DRAPEAU d'état, lisible par l'Arduino lui-même et rapportable au Pi.
 *
 * C'est le Pi qui DÉCIDE de l'état engagé : il envoie « valve_confirmer »
 * (ouvert/fermé) avant la fin d'un cycle complet. Une impulsion partielle
 * (priming, ajout d'eau ~10 %) n'est jamais confirmée → le drapeau reste
 * au dernier état engagé (ex. « fermé puis ouvert à 7 % » reste « fermé »).
 * Au redémarrage, le Pi relit ces drapeaux et re-pousse chaque valve à fond
 * dans le sens reçu pour regagner une position CERTAINE.
 *
 * Le drapeau est aussi sauvegardé en EEPROM : si l'Arduino est tout de même
 * réinitialisé (flashage, glitch d'alimentation), setup() restaure le repos
 * 11/00 au lieu de tout remettre à zéro.
 *
 * ===================== Protection moteur (anti-deadhead) =====================
 *
 * Une pompe de piscine ne doit JAMAIS tourner à vanne fermée (surpression).
 * Interlock matériel autonome : le moteur n'est alimenté QUE si
 *     (écumoire OU drain de fond engagée ouverte) ET (retour engagé ouvert).
 * Sinon le moteur est coupé, même si le Pi le demande. Vérifié en continu :
 * si une valve d'entrée/sortie se referme, le moteur retombe immédiatement.
 */

#include <ArduinoJson.h>
#include <EEPROM.h>

// ===================== Brochage =====================

// Relais moteur : broche D2 (libre). À recâbler physiquement sur D2.
// (L'ancienne D1 ne pouvait pas servir : c'est le TX du port série.)
const uint8_t PIN_MOTEUR = 2;

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
//              1   |  0   | ouvre (entraîne)
//              0   |  1   | ferme (entraîne)
//              0   |  0   | NEUTRE — repos « fermé » (roue libre, position tenue)
//              1   |  1   | FREIN  — repos « ouvert » (bornes liées, position tenue)
//
// Le Pi fournit toujours une durée (duree_ms) pour la phase d'entraînement :
//   - course complète (≈15000 ms) pour ouvrir/fermer entièrement
//   - impulsion plus courte pour une ouverture partielle / un priming
// Une fois la durée écoulée, la valve passe automatiquement à son REPOS
// (frein 11 si engagée ouverte, neutre 00 sinon) — non bloquant.

enum Mouvement { ARRET, OUVERTURE, FERMETURE };

struct Valve {
  const char* nom;
  uint8_t pinA;
  uint8_t pinB;
  Mouvement mouvement;
  unsigned long finMouvement; // millis() cible ; 0 = pas de limite de temps
  bool engageOuvert;          // drapeau d'état engagé (true=ouvert/frein, false=fermé/neutre)
};

// Ordre = index utilisés par l'interlock moteur (voir circulationOk()).
Valve valves[] = {
  { "ecumoire",     PIN_ECUMOIRE_A,     PIN_ECUMOIRE_B,     ARRET, 0, false },
  { "drain",        PIN_DRAIN_A,        PIN_DRAIN_B,        ARRET, 0, false },
  { "alimentation", PIN_ALIMENTATION_A, PIN_ALIMENTATION_B, ARRET, 0, false },
  { "retour",       PIN_RETOUR_A,       PIN_RETOUR_B,       ARRET, 0, false },
};
const uint8_t NB_VALVES = sizeof(valves) / sizeof(valves[0]);

const uint8_t IDX_ECUMOIRE = 0;
const uint8_t IDX_DRAIN     = 1;
const uint8_t IDX_RETOUR    = 3;

// ===================== Moteur =====================

bool moteurDemande = false; // dernière commande reçue du Pi (avant interlock)

// ===================== EEPROM (filet anti-reset) =====================
//
// Sauvegarde du masque de bits des drapeaux engageOuvert, pour restaurer le
// repos 11/00 si l'Arduino est réinitialisé. Le moteur N'EST PAS restauré
// (moteurDemande repart à false = état sûr ; le Pi le recommandera au besoin).

const int  EEPROM_ADDR_MAGIC  = 0;
const int  EEPROM_ADDR_MASQUE = 1;
const byte EEPROM_MAGIC       = 0xA5;

void sauvegarderEtatEEPROM() {
  byte masque = 0;
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    if (valves[i].engageOuvert) masque |= (1 << i);
  }
  EEPROM.update(EEPROM_ADDR_MAGIC, EEPROM_MAGIC);
  EEPROM.update(EEPROM_ADDR_MASQUE, masque);
}

void restaurerEtatEEPROM() {
  if (EEPROM.read(EEPROM_ADDR_MAGIC) != EEPROM_MAGIC) {
    for (uint8_t i = 0; i < NB_VALVES; i++) valves[i].engageOuvert = false;
    return;
  }
  byte masque = EEPROM.read(EEPROM_ADDR_MASQUE);
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    valves[i].engageOuvert = (masque >> i) & 0x01;
  }
}

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

  pinMode(PIN_MOTEUR, OUTPUT);
  digitalWrite(PIN_MOTEUR, LOW); // moteur coupé au démarrage (état sûr)

  for (uint8_t i = 0; i < NB_VALVES; i++) {
    pinMode(valves[i].pinA, OUTPUT);
    pinMode(valves[i].pinB, OUTPUT);
  }

  // Restaure les drapeaux engagés (EEPROM) et applique le repos 11/00
  // correspondant : si l'Arduino a été réinitialisé, on ne perd pas l'état.
  restaurerEtatEEPROM();
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    appliquerRepos(i);
  }

  for (uint8_t i = 0; i < NB_BOUTONS; i++) {
    pinMode(boutons[i].pin, INPUT_PULLUP);
  }
}

// ===================== Boucle principale (non bloquante) =====================

void loop() {
  traiterCommandeEntrante();
  mettreAJourValves();
  appliquerMoteur();   // interlock vérifié en continu
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

// Repos d'une valve à l'arrêt : motif-drapeau selon l'état engagé.
//   engagé ouvert → FREIN  (1/1)    engagé fermé → NEUTRE (0/0)
void appliquerRepos(uint8_t i) {
  Valve &v = valves[i];
  if (v.engageOuvert) {
    digitalWrite(v.pinA, HIGH);
    digitalWrite(v.pinB, HIGH);
  } else {
    digitalWrite(v.pinA, LOW);
    digitalWrite(v.pinB, LOW);
  }
  v.mouvement = ARRET;
  v.finMouvement = 0;
}

void ouvrirValve(uint8_t i, unsigned long dureeMs) {
  appliquerPolarite(i, OUVERTURE);
  valves[i].finMouvement = (dureeMs > 0) ? millis() + dureeMs : 0;
}

void fermerValve(uint8_t i, unsigned long dureeMs) {
  appliquerPolarite(i, FERMETURE);
  valves[i].finMouvement = (dureeMs > 0) ? millis() + dureeMs : 0;
}

// Arrêt explicite en cours de course : on revient au REPOS de l'état engagé
// courant (la commande d'arrêt ne change pas l'engagement).
void arreterValve(uint8_t i) {
  appliquerRepos(i);
}

int trouverValve(const char* nom) {
  if (nom == nullptr) return -1;
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    if (strcmp(valves[i].nom, nom) == 0) return i;
  }
  return -1;
}

// Coupe automatiquement l'entraînement d'une valve une fois sa durée écoulée
// et la met à son repos-drapeau (équivalent non bloquant d'un « entraîner X ms
// puis tenir la position »).
void mettreAJourValves() {
  unsigned long maintenant = millis();
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    if (valves[i].mouvement != ARRET
        && valves[i].finMouvement != 0
        && (long)(maintenant - valves[i].finMouvement) >= 0) {
      appliquerRepos(i);
    }
  }
}

// ===================== Moteur + interlock anti-deadhead =====================

// Vrai s'il existe un chemin de circulation valide : au moins une entrée
// (écumoire ou drain) ET la sortie (retour) engagées ouvertes.
bool circulationOk() {
  bool entree = valves[IDX_ECUMOIRE].engageOuvert || valves[IDX_DRAIN].engageOuvert;
  bool sortie = valves[IDX_RETOUR].engageOuvert;
  return entree && sortie;
}

// Moteur alimenté seulement si demandé ET circulation valide (sinon coupé).
void appliquerMoteur() {
  bool actif = moteurDemande && circulationOk();
  digitalWrite(PIN_MOTEUR, actif ? HIGH : LOW);
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
//   {"cmd":"valve_ouvrir",    "valve":"<nom>", "duree_ms": <n>}
//   {"cmd":"valve_fermer",    "valve":"<nom>", "duree_ms": <n>}
//   {"cmd":"valve_arreter",   "valve":"<nom>"}
//   {"cmd":"valve_confirmer", "valve":"<nom>", "ouvert": true|false}
//   {"cmd":"moteur_demarrer"}
//   {"cmd":"moteur_arreter"}
//   {"cmd":"etat_boutons"}
//   {"cmd":"etat_sorties"}
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
  else if (strcmp(commande, "valve_confirmer") == 0) {
    // Le Pi asserte l'état engagé (ouvert/fermé). Met à jour le drapeau,
    // le sauvegarde, et rafraîchit le repos si la valve est déjà arrêtée.
    int i = trouverValve(doc["valve"]);
    if (i >= 0) {
      valves[i].engageOuvert = doc["ouvert"] | false;
      sauvegarderEtatEEPROM();
      if (valves[i].mouvement == ARRET) appliquerRepos(i);
    }
    repondreOk(commande);
  }
  else if (strcmp(commande, "moteur_demarrer") == 0) {
    moteurDemande = true;
    appliquerMoteur(); // l'interlock peut le refuser (deadhead)
    repondreOk(commande);
  }
  else if (strcmp(commande, "moteur_arreter") == 0) {
    moteurDemande = false;
    appliquerMoteur();
    repondreOk(commande);
  }
  else if (strcmp(commande, "etat_boutons") == 0) {
    envoyerEtatBoutons();
  }
  else if (strcmp(commande, "etat_sorties") == 0) {
    envoyerEtatSorties();
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

const char* nomMouvement(Mouvement m) {
  if (m == OUVERTURE) return "ouverture";
  if (m == FERMETURE) return "fermeture";
  return "arret";
}

// Rapport complet des sorties, pour la récupération d'état au boot du Pi.
void envoyerEtatSorties() {
  StaticJsonDocument<384> doc;
  JsonObject sorties = doc.createNestedObject("sorties");
  JsonObject vv = sorties.createNestedObject("valves");
  for (uint8_t i = 0; i < NB_VALVES; i++) {
    JsonObject o = vv.createNestedObject(valves[i].nom);
    o["ouvert"] = valves[i].engageOuvert;            // drapeau engagé
    o["mouvement"] = nomMouvement(valves[i].mouvement);
  }
  sorties["moteur"] = (moteurDemande && circulationOk()); // sortie réelle
  sorties["moteur_demande"] = moteurDemande;
  sorties["circulation_ok"] = circulationOk();
  serializeJson(doc, Serial);
  Serial.println();
}
