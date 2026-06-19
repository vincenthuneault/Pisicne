"use strict";

// ===================== Utilitaires =====================

function toast(message, type) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = "toast visible " + (type || "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.className = "toast"; }, 3000);
}

async function postJSON(url, corps) {
  const reponse = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: corps === undefined ? undefined : JSON.stringify(corps),
  });
  let data = {};
  try { data = await reponse.json(); } catch (e) { /* pas de corps */ }
  return { ok: reponse.ok, data };
}

function afficherResultat(res) {
  const msg = (res.data && res.data.message) || (res.ok ? "OK" : "Erreur");
  toast(msg, res.ok ? "succes" : "erreur");
}

// ===================== Zone d'alertes (haut de page) =====================
//
// Modèle simple : chaque alerte a un id stable (ex. "chlore", "offline").
// setAlerte(id, message, type) ajoute/met à jour (message falsy = retire).

const alertes = {};

function setAlerte(id, message, type) {
  if (message) alertes[id] = { message, type: type || "" };
  else delete alertes[id];
  rendreAlertes();
}

function rendreAlertes() {
  const zone = document.getElementById("alertes");
  const liste = Object.values(alertes);
  if (!liste.length) {
    zone.hidden = true;
    zone.innerHTML = "";
    return;
  }
  zone.hidden = false;
  zone.innerHTML = liste
    .map((a) => `<div class="alerte ${a.type}">${a.message}</div>`)
    .join("");
}

// ===================== Formatage durées / dates =====================

function formatDate(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString("fr-CA", { dateStyle: "medium", timeStyle: "short" });
}

function formatRestant(s) {
  if (s <= 0) return s < -3600 ? "en retard" : "maintenant";
  const j = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (j > 0) return `dans ${j} j ${h} h`;
  if (h > 0) return `dans ${h} h ${m} min`;
  return `dans ${m} min`;
}

// ===================== État (polling) =====================

let sequenceEnCours = false;

// Noms internes des valves → libellés affichés, dans l'ordre voulu.
const VALVES_LIBELLE = {
  ecumoire: "Écumoire",
  drain: "Drain de fond",
  alimentation: "Alimentation",
  retour: "Retour piscine",
};
const FLECHE_MOUVEMENT = { ouverture: "▲ ouvre", fermeture: "▼ ferme", arret: "" };

async function rafraichirEtat() {
  try {
    const reponse = await fetch("/api/etat");
    const etat = await reponse.json();

    const badge = document.getElementById("badge-etat");
    const enMarche = etat.etat === "EN_MARCHE";
    badge.textContent = enMarche ? "EN MARCHE" : "ÉTEINT";
    badge.className = "badge " + (enMarche ? "marche" : "eteint");

    const info = document.getElementById("badge-sequence");
    if (etat.flashage_en_cours) info.textContent = "⚡ Flashage…";
    else if (etat.sequence_en_cours) info.textContent = "⏳ Séquence en cours…";
    else info.textContent = "";

    majEtatMateriel(etat);
    await majTimeline(etat);
    if (etat.chlore) majChlore(etat.chlore);

    sequenceEnCours = etat.sequence_en_cours || etat.flashage_en_cours;
    majDisponibiliteManuel();
    setAlerte("offline", null);  // connexion OK
  } catch (e) {
    document.getElementById("badge-etat").textContent = "Hors ligne";
    setAlerte("offline", "⚠️ Hors ligne — pas de réponse du serveur", "erreur");
  }
}

// ===================== Chloration =====================

function majChlore(c) {
  // Info sur une seule ligne (dans « État du matériel »)
  const ligne = document.getElementById("chlore-ligne");
  if (c.jamais) {
    ligne.textContent = "🧪 Chloration : aucun ajout enregistré";
  } else if (c.du) {
    ligne.textContent = "🧪 Chloration : à ajouter (" + formatRestant(c.restant_s) + ")";
  } else {
    ligne.textContent = "🧪 Chloration : prochaine " + formatRestant(c.restant_s)
      + " · le " + formatDate(c.prochaine_echeance_ts);
  }
  ligne.classList.toggle("du", !!c.du);

  // Bannière d'alerte en haut de page
  if (c.du) {
    setAlerte("chlore", c.jamais
      ? "🧪 Chloration : aucun ajout enregistré — pense à en mettre puis clique « J'ai ajouté du chlore »"
      : "🧪 Chloration due — ajoute du chlore puis confirme avec « J'ai ajouté du chlore »", "attention");
  } else {
    setAlerte("chlore", null);
  }

  // Toast au passage « pas dû » → « dû »
  if (c.du && majChlore._dernierDu === false) {
    toast("🧪 Il est temps d'ajouter du chlore", "attention");
  }
  majChlore._dernierDu = !!c.du;
}

function majEtatMateriel(etat) {
  // Barres de position des valves
  const conteneur = document.getElementById("etat-valves");
  const valves = etat.valves || {};
  let html = "";
  for (const nom of Object.keys(VALVES_LIBELLE)) {
    const v = valves[nom] || { position: 0, mouvement: "arret" };
    const enMouv = v.mouvement !== "arret";
    html += `<div class="valve-etat">
        <span class="nom">${VALVES_LIBELLE[nom]}</span>
        <div class="barre"><div class="remplissage${enMouv ? " bouge" : ""}" style="width:${v.position}%"></div></div>
        <span class="pct">${v.position}% <span class="mouv">${FLECHE_MOUVEMENT[v.mouvement] || ""}</span></span>
      </div>`;
  }
  conteneur.innerHTML = html;

  // Moteur (relais) — état commandé (le relais est un stub non câblé)
  const moteur = document.getElementById("indic-moteur");
  moteur.textContent = "Moteur (relais) : " + (etat.moteur ? "EN MARCHE" : "arrêté");
  moteur.className = "indic " + (etat.moteur ? "on" : "off");

  // Boutons
  const b = etat.boutons || {};
  majIndicBouton("indic-bvert", "Bouton vert", b.vert);
  majIndicBouton("indic-brouge", "Bouton rouge", b.rouge);

  // Schéma de procédé animé
  majSchema(etat);
}

// ===================== Schéma de procédé (P&ID animé) =====================

const SEUIL_OUVERT = 5;  // % au-delà duquel on considère qu'il y a passage d'eau

function classeValve(v) {
  if (v.position <= 2) return "fermee";
  if (v.position >= 98) return "ouverte";
  return "partielle";
}

function majSchema(etat) {
  const svg = document.getElementById("schema");
  if (!svg) return;
  const valves = etat.valves || {};
  const moteurOn = !!etat.moteur;

  // --- Valves : couleur selon position + pulsation si en mouvement ---
  for (const nom of Object.keys(VALVES_LIBELLE)) {
    const groupe = document.getElementById("valve-" + nom);
    if (!groupe) continue;
    const v = valves[nom] || { position: 0, mouvement: "arret" };
    groupe.classList.remove("fermee", "partielle", "ouverte", "bouge");
    groupe.classList.add(classeValve(v));
    if (v.mouvement && v.mouvement !== "arret") groupe.classList.add("bouge");
    const pct = document.getElementById("pct-" + nom);
    if (pct) pct.textContent = v.position + "%";
  }

  // --- Moteur + rotor de pompe ---
  document.getElementById("moteur").classList.toggle("on", moteurOn);
  document.getElementById("pompe").classList.toggle("tourne", moteurOn);

  // --- Débit : quels segments transportent de l'eau en ce moment ---
  const ouvert = (nom) => ((valves[nom] || {}).position || 0) > SEUIL_OUVERT;
  const alimentation       = ouvert("alimentation");  // injection (priming / ajout d'eau)

  // Aspiration depuis la piscine (écumoire / drain → pompe) : seulement quand
  // le moteur tourne (c'est lui qui aspire). C'est le « bord » qui s'active au
  // démarrage du moteur.
  const aspirationEcumoire = moteurOn && ouvert("ecumoire");
  const aspirationDrain    = moteurOn && ouvert("drain");

  // Refoulement (pompe → filtre → nature2 → retour → piscine) : en marche
  // normale (moteur). MAIS aussi pendant le PRIMING : avant le démarrage du
  // moteur, l'eau injectée par l'alimentation est poussée pompe → piscine —
  // à condition que le retour soit ouvert (sinon l'eau ne peut pas sortir).
  const refoulement        = moteurOn || (alimentation && ouvert("retour"));

  const flux = {
    "flux-ecumoire-in": aspirationEcumoire,
    "flux-ecumoire-out": aspirationEcumoire,
    "flux-drain-in": aspirationDrain,
    "flux-drain-out": aspirationDrain,
    "flux-alim-in": alimentation,
    "flux-alim-out": alimentation,
    "flux-pompe-filtre": refoulement,
    "flux-filtre-chauffe": refoulement,
    "flux-chauffe-nature": refoulement,
    "flux-nature-retour": refoulement,
    "flux-retour-piscine": refoulement,
  };
  for (const [id, actif] of Object.entries(flux)) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("actif", actif);
  }
}

// ===================== Timeline de séquence (frise + progression) =====================

const TITRES_SEQUENCE = {
  demarrage: "Démarrage simple",
  priming: "Démarrage avec priming",
  ajout_eau: "Ajout d'eau",
};

let timelineSequenceChargee = null;  // nom de la séquence dont la frise est affichée
let timelineDonnees = null;          // {duree_totale_s, etapes}
let timelineMasquageTimeout = null;

async function majTimeline(etat) {
  const nom = etat.sequence_nom || null;

  if (nom && nom !== timelineSequenceChargee) {
    clearTimeout(timelineMasquageTimeout);
    try {
      const reponse = await fetch("/api/sequence/" + nom + "/timeline");
      if (reponse.ok) {
        timelineDonnees = await reponse.json();
        timelineSequenceChargee = nom;
        rendreTimeline(nom, timelineDonnees);
      }
    } catch (e) { /* on retentera au prochain rafraîchissement */ }
  }

  if (timelineSequenceChargee && timelineDonnees) {
    if (etat.sequence_en_cours) {
      majProgressionTimeline(etat.sequence_ecoulee_s || 0);
    } else {
      // Séquence terminée : on affiche la frise complète puis on la masque.
      majProgressionTimeline(timelineDonnees.duree_totale_s);
      const nomTermine = timelineSequenceChargee;
      timelineMasquageTimeout = setTimeout(() => {
        if (timelineSequenceChargee === nomTermine) {
          document.getElementById("timeline-section").hidden = true;
          timelineSequenceChargee = null;
          timelineDonnees = null;
        }
      }, 4000);
    }
  }
}

function rendreTimeline(nom, timeline) {
  document.getElementById("timeline-titre").textContent =
    "Progression — " + (TITRES_SEQUENCE[nom] || nom);

  const jalons = document.getElementById("timeline-jalons");
  const duree = timeline.duree_totale_s || 1;
  jalons.innerHTML = timeline.etapes.map((etape) => {
    const pct = Math.max(0, Math.min(100, (etape.t / duree) * 100));
    return `<div class="jalon" data-t="${etape.t}" style="left:${pct}%">
        <span class="jalon-point"></span>
        <span class="jalon-label">${etape.nom}</span>
      </div>`;
  }).join("");

  document.getElementById("timeline-progression").style.width = "0%";
  document.getElementById("timeline-section").hidden = false;
}

function majProgressionTimeline(ecoulee) {
  const duree = (timelineDonnees && timelineDonnees.duree_totale_s) || 1;
  const pct = Math.max(0, Math.min(100, (ecoulee / duree) * 100));
  document.getElementById("timeline-progression").style.width = pct + "%";
  document.querySelectorAll("#timeline-jalons .jalon").forEach((el) => {
    el.classList.toggle("atteint", ecoulee >= parseFloat(el.dataset.t));
  });
  document.getElementById("timeline-temps").textContent =
    `${Math.round(ecoulee)} s / ${Math.round(duree)} s`;
}

function majIndicBouton(id, libelle, presse) {
  const el = document.getElementById(id);
  el.textContent = `${libelle} : ${presse ? "pressé" : "relâché"}`;
  el.className = "indic " + (presse ? "on" : "off");
}

function majDisponibiliteManuel() {
  document.querySelectorAll(".btn-mini").forEach((b) => {
    if (b.id === "btn-flasher") return;
    b.disabled = sequenceEnCours;
  });
}

// ===================== Contrôle (séquences) =====================

document.querySelectorAll("[data-sequence]").forEach((bouton) => {
  bouton.addEventListener("click", async () => {
    const res = await postJSON("/api/sequence/" + bouton.dataset.sequence);
    afficherResultat(res);
    rafraichirEtat();
  });
});

document.getElementById("btn-arret").addEventListener("click", async () => {
  const res = await postJSON("/api/arret");
  afficherResultat(res);
  rafraichirEtat();
});

// ===================== Chloration =====================

document.getElementById("btn-chlore").addEventListener("click", async () => {
  const res = await postJSON("/api/chlore");
  afficherResultat(res);
  if (res.data && res.data.chlore) majChlore(res.data.chlore);
});

// ===================== Mode manuel =====================

document.querySelectorAll(".ligne-valve").forEach((ligne) => {
  const valve = ligne.dataset.valve;
  const champDuree = ligne.querySelector(".duree");
  ligne.querySelectorAll("[data-action]").forEach((bouton) => {
    bouton.addEventListener("click", async () => {
      const duree_ms = Math.round(parseFloat(champDuree.value || "0") * 1000);
      const res = await postJSON("/api/manuel/valve", {
        valve, action: bouton.dataset.action, duree_ms,
      });
      afficherResultat(res);
    });
  });
});

document.querySelectorAll("[data-moteur]").forEach((bouton) => {
  bouton.addEventListener("click", async () => {
    const res = await postJSON("/api/manuel/moteur", { action: bouton.dataset.moteur });
    afficherResultat(res);
  });
});

document.getElementById("btn-lire-boutons").addEventListener("click", async () => {
  const reponse = await fetch("/api/manuel/boutons");
  const data = await reponse.json();
  const cible = document.getElementById("etat-boutons");
  if (data.ok) {
    cible.textContent = Object.entries(data.boutons)
      .map(([nom, presse]) => `${nom}: ${presse ? "pressé" : "relâché"}`)
      .join("  •  ");
  } else {
    cible.textContent = data.message || "Pas de réponse";
  }
});

// ===================== Paramètres =====================

function valeurImbriquee(obj, chemin) {
  return chemin.split(".").reduce((o, c) => (o == null ? undefined : o[c]), obj);
}

async function chargerConfig() {
  const reponse = await fetch("/api/config");
  const config = await reponse.json();
  document.querySelectorAll("#form-config input").forEach((input) => {
    const valeur = valeurImbriquee(config, input.name);
    if (valeur !== undefined) input.value = valeur;
  });
}

document.getElementById("form-config").addEventListener("submit", async (e) => {
  e.preventDefault();
  const config = {};
  document.querySelectorAll("#form-config input").forEach((input) => {
    const parties = input.name.split(".");
    let cible = config;
    for (let i = 0; i < parties.length - 1; i++) {
      cible[parties[i]] = cible[parties[i]] || {};
      cible = cible[parties[i]];
    }
    cible[parties[parties.length - 1]] = parseFloat(input.value);
  });
  const res = await postJSON("/api/config", config);
  afficherResultat(res);
});

// ===================== Firmware =====================

document.getElementById("form-firmware").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fichier = document.getElementById("fichier-firmware").files[0];
  if (!fichier) { toast("Choisir un fichier .ino", "erreur"); return; }
  const corps = new FormData();
  corps.append("firmware", fichier);
  const reponse = await fetch("/api/firmware", { method: "POST", body: corps });
  const data = await reponse.json();
  toast(data.message || (reponse.ok ? "Téléversé" : "Erreur"), reponse.ok ? "succes" : "erreur");
});

document.getElementById("btn-flasher").addEventListener("click", async () => {
  const log = document.getElementById("log-firmware");
  log.textContent = "Flashage en cours… (la compilation peut prendre ~1 min sur le Pi)";
  rafraichirEtat();
  const res = await postJSON("/api/firmware/flash");
  log.textContent = (res.data && res.data.log) || "(aucun log)";
  toast(res.data && res.data.ok ? "Flashage réussi" : "Échec du flashage",
        res.data && res.data.ok ? "succes" : "erreur");
  rafraichirEtat();
});

// ===================== Initialisation =====================

chargerConfig();
rafraichirEtat();
setInterval(rafraichirEtat, 1000);  // 1 s : suit le mouvement des valves en direct
