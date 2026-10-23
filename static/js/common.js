(() => {
  const $ = s => document.querySelector(s), B = document.body.dataset;
  // Kirish va ro'yxatdan o'tish oynalarini almashtirish
  const fk = $("#fk"), fr = $("#fr");
  if (fk && fr) {
    const sw = r => { fk.hidden = r; fr.hidden = !r; };
    $("#toR").onclick = e => { e.preventDefault(); sw(true); };
    $("#toK").onclick = e => { e.preventDefault(); sw(false); };
  }
  // Xavfli amallarni tasdiqlash
  document.addEventListener("submit", e => {
    const m = e.target.dataset && e.target.dataset.confirm;
    if (m && !confirm(m)) e.preventDefault();
  });
  // Profil tahrirlash: rasm ko'rinishi va belgilar hisobi
  const f = $("#file"), av = $("#avbig"), h = $("#haqida"), c = $("#cnt");
  if (f && av) f.onchange = () => {
    const x = f.files[0]; if (!x) return;
    const i = document.createElement("img"); i.src = URL.createObjectURL(x);
    av.textContent = ""; av.appendChild(i);
  };
  if (h && c) { const n = () => c.textContent = h.value.length + "/160"; h.oninput = n; n(); }
  // O'qilmagan xabarlar belgisi
  if (B.uid) {
    const set = (id, n) => { const e = document.getElementById(id); if (e) { e.textContent = n || ""; e.style.display = n ? "" : "none"; } };
    const up = async () => {
      try { const r = await fetch("/api/belgi"); if (!r.ok) return; const j = await r.json(); set("mb", j.un); }
      catch (e) { /* tarmoq xatosi: keyingi urinishda */ }
    };
    setInterval(() => { if (!document.hidden) up(); }, 6000);
  }
})();
