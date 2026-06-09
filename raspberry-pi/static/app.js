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

    sequenceEnCours = etat.sequence_en_cours || etat.flashage_en_cours;
    majDisponibiliteManuel();
  } catch (e) {
    document.getElementById("badge-etat").textContent = "Hors ligne";
  }
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
