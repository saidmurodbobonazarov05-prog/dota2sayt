(() => {
  "use strict";
  const $ = s => document.querySelector(s), B = document.body.dataset, ADM = B.adm === "1";
  const esc = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ic = (n, c = "") => `<svg class="ic ${c}"><use href="#i-${n}"/></svg>`;
  const hm = t => new Date(t * 1000).toTimeString().slice(0, 5);
  const P = new URLSearchParams(location.search);
  let T = [], SEL = null, PEND = null, RES = null, sig = "";

  async function api(u, b) {
    const o = b === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF": B.csrf }, body: JSON.stringify(b) };
    const r = await fetch(u, o);
    if (r.status === 401) { location.href = "/"; throw new Error("401"); }
    let j = {}; try { j = await r.json(); } catch (e) { /* bo'sh javob */ }
    if (!r.ok) { alert(j.xato || "Xatolik yuz berdi."); throw new Error(j.xato || r.status); }
    return j;
  }
  const av = (w, sup) => sup && !ADM ? ic("headset") : esc((w.n || "?")[0].toUpperCase());

  function renderList() {
    let h = "";
    if (RES && !ADM) {
      h = '<div class="mh">Natijalar</div>' + (RES.length ? RES.map(x => `<div class="mi" data-u="${x.id}"><span class="mav">${esc(x.n[0].toUpperCase())}</span><span class="mt2"><b>${esc(x.n)}</b><small>Yangi suhbat boshlash</small></span></div>`).join("") : '<p class="mut pad">Hech kim topilmadi.</p>');
    } else {
      const L = T.slice();
      if (PEND && !L.some(x => x.k === PEND.k)) L.push({ k: PEND.k, who: PEND.who, sup: false, un: 0, last: null });
      h = L.length ? L.map(x => `<div class="mi${SEL === x.k ? " on" : ""}" data-k="${esc(x.k)}"><span class="mav">${av(x.who, x.sup)}</span><span class="mt2"><b>${esc(x.who.n)}${x.sup && ADM ? " · support" : ""}</b><small>${x.last ? (x.last.me ? "Siz: " : "") + esc(x.last.m) : (x.sup ? "Admin bilan bog'lanish" : "Yangi suhbat")}</small></span>${x.un ? `<i class="ub">${x.un}</i>` : ""}</div>`).join("") : '<p class="mut pad">Hali support so\'rovlari yo\'q.</p>';
    }
    $("#mlist").innerHTML = h;
  }

  async function loadList() {
    const j = await api("/api/xabar/royxat");
    T = j.threads;
    const s = JSON.stringify([T.map(x => [x.k, x.un, x.last && x.last.t]), SEL, RES]);
    if (s !== sig) { sig = s; renderList(); }
    const n = T.reduce((a, x) => a + (x.k === SEL ? 0 : x.un), 0), b = document.getElementById("mb");
    if (b) { b.textContent = n || ""; b.style.display = n ? "" : "none"; }
  }

  async function loadThread(force) {
    const e = $("#mth");
    if (!SEL) {
      $("#mf").hidden = true; $("#mhd2").innerHTML = "";
      e.innerHTML = '<div class="cm sys">Suhbatni tanlang yoki yangi suhbat boshlang.</div>'; return;
    }
    const k = SEL, j = await api("/api/xabar/chat?k=" + encodeURIComponent(k));
    if (k !== SEL) return;
    const sup = k.startsWith("s:"), cust = sup && !ADM;
    if (!T.some(x => x.k === k)) PEND = { k, who: j.who };
    $("#mf").hidden = false;
    $("#mhd2").innerHTML = `<span class="mav">${av(j.who, sup)}</span><span>${esc(j.who.n)} <small>${sup ? (ADM ? "· support so'rovi" : "· admin javob beradi") : "· shaxsiy suhbat"}</small></span>`;
    const atb = e.scrollHeight - e.scrollTop - e.clientHeight < 40;
    e.innerHTML = (cust ? '<div class="cm sys">Savol yoki muammoingizni yozing. Admin xabaringizni ko\'radi va shu yerda javob beradi.</div>' : "") +
      (j.msgs.length ? j.msgs.map(x => `<div class="cm${x.me ? " me" : ""}"><b>${x.me ? "Siz" : esc(x.n)}</b><span>${esc(x.m)}</span><time>${hm(x.t)}</time></div>`).join("") : (cust ? "" : '<div class="cm sys">Suhbat bo\'sh. Birinchi xabarni yozing.</div>'));
    if (atb || force) e.scrollTop = e.scrollHeight;
  }

  async function open(k, force) { SEL = k; sig = ""; await loadThread(force !== false); await loadList(); renderList(); }

  $("#mlist").addEventListener("click", async e => {
    const i = e.target.closest(".mi"); if (!i) return;
    if (i.dataset.u) {
      const j = await api("/api/xabar/yangi", { u: +i.dataset.u });
      RES = null; if ($("#mq")) $("#mq").value = ""; await open(j.k);
    } else open(i.dataset.k);
  });
  let dt = 0;
  if ($("#mq")) $("#mq").addEventListener("input", () => {
    clearTimeout(dt);
    dt = setTimeout(async () => {
      const q = $("#mq").value.trim();
      RES = q ? (await api("/api/qidir?q=" + encodeURIComponent(q))).users : null;
      sig = ""; renderList();
    }, 200);
  });
  $("#mf").onsubmit = async e => {
    e.preventDefault();
    const i = e.target.elements.t, m = i.value.trim();
    if (!m || !SEL) return;
    i.value = "";
    await api("/api/xabar/yubor", { k: SEL, m });
    await loadThread(true); await loadList();
  };

  (async () => {
    await loadList();
    try {
      if (P.get("u") && !ADM) { const j = await api("/api/xabar/yangi", { u: +P.get("u") }); await open(j.k); }
      else if (ADM) { if (T[0]) await open(T[0].k); else await loadThread(); }
      else {
        await open("s:" + B.uid);
        if (P.get("t")) { const i = $("#mf").elements.t; i.value = P.get("t").slice(0, 500); i.focus(); }
      }
    } catch (e) { /* xato api() ichida ko'rsatilgan */ }
    setInterval(async () => { if (document.hidden) return; try { await loadList(); if (SEL) await loadThread(); } catch (e) { /* keyingi urinish */ } }, 3000);
  })();
})();
