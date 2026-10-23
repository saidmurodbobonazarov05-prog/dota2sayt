(() => {
  "use strict";
  const $ = s => document.querySelector(s), B = document.body.dataset;
  const ic = (n, c = "") => `<svg class="ic ${c}"><use href="#i-${n}"/></svg>`;
  const esc = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const hm = t => new Date(t * 1000).toTimeString().slice(0, 5);
  const PN = ["Mider", "Kerri", "Tank (Slojniy)", "Paderjka", "To'liq paderjka"];
  const RI = ["target", "sword", "shield", "eye", "plus"];
  const RN = ["Chorak final", "Yarim final", "Final"], ST = { t: "Tugagan", j: "Jonli", k: "Kutilmoqda" };
  const POX = [20, 270, 520], TOP = [15, 155, 295, 435, 85, 365, 225];
  const RP = [[290, 500], [200, 705], [92, 300], [170, 440], [340, 690]];
  const CHIPS = ["Mid'ga gank!", "Roshan!", "Ehtiyot bo'ling!", "Yaxshi o'yin!"];
  let S = null, mi = null, ct = -1, PAYT = null, PT = 0, sig = "", built = false;

  const tst = t => { const e = $("#ts"); e.textContent = t; e.classList.remove("sh"); void e.offsetWidth; e.classList.add("sh"); };
  async function api(u, b) {
    const o = b === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF": B.csrf }, body: JSON.stringify(b) };
    const r = await fetch(u, o);
    if (r.status === 401) { location.href = "/"; throw new Error("401"); }
    let j = {}; try { j = await r.json(); } catch (e) { /* bo'sh javob */ }
    if (!r.ok) { tst(j.xato || "Xatolik yuz berdi."); throw new Error(j.xato || r.status); }
    return j;
  }
  async function load() {
    const j = await api("/api/turnir"), now = Date.now();
    for (const k in j.sl) if (j.sl[k].ex != null) j.sl[k].end = now + j.sl[k].ex * 1000;
    S = j; render();
  }
  const slot = (t, k) => S.sl[t + "." + k] || null;
  const iMine = p => !!p && p.u === S.me.id;
  const myPos = t => { for (let k = 0; k < 5; k++) { const p = slot(t, k); if (iMine(p) && p.st === "paid") return k; } return null; };
  const cntf = i => { let n = 0, t = 0; for (const x of [S.mt[i].a, S.mt[i].b]) if (x != null) for (let k = 0; k < 5; k++) { t++; const p = slot(x, k); if (p && p.st === "paid") n++; } return n + "/" + t; };
  const lab = i => { const r = i < 4 ? 0 : i < 6 ? 1 : 2; return RN[r] + (r < 2 ? " " + (r ? i - 3 : i + 1) : ""); };

  /* ---------- yulduzli fon ---------- */
  function stars(cv) {
    const x = cv.getContext && cv.getContext("2d"); if (!x) return;
    let W, H, A = [], sh = null;
    const rs = () => { W = cv.width = cv.offsetWidth; H = cv.height = cv.offsetHeight; A = Array.from({ length: Math.round(W * H / 9000) }, () => ({ x: Math.random() * W, y: Math.random() * H, r: Math.random() * 1.4 + .2, p: Math.random() * 6, v: Math.random() * .15 + .02 })); };
    rs(); addEventListener("resize", rs);
    (function f(t) {
      if (cv.offsetParent !== null) {
        x.clearRect(0, 0, W, H);
        for (const s of A) { s.y -= s.v; if (s.y < 0) s.y = H; x.globalAlpha = .25 + .5 * Math.abs(Math.sin(t / 900 + s.p)); x.fillStyle = s.r > 1.1 ? "#ffd9a8" : "#cfe0ff"; x.beginPath(); x.arc(s.x, s.y, s.r, 0, 7); x.fill(); }
        if (!sh && Math.random() < .002) sh = { x: Math.random() * W * .7, y: Math.random() * H * .4, l: 0 };
        if (sh) { x.globalAlpha = 1; const g = x.createLinearGradient(sh.x, sh.y, sh.x - sh.l, sh.y - sh.l * .4); g.addColorStop(0, "#fff"); g.addColorStop(1, "rgba(255,255,255,0)"); x.strokeStyle = g; x.lineWidth = 2; x.beginPath(); x.moveTo(sh.x, sh.y); x.lineTo(sh.x - sh.l, sh.y - sh.l * .4); x.stroke(); sh.x += 14; sh.y += 5.6; sh.l = Math.min(sh.l + 6, 130); if (sh.x > W + 150) sh = null; }
      }
      requestAnimationFrame(f);
    })(0);
  }

  /* ---------- setka ---------- */
  function renderBar() {
    const el = $("#tc"), n = S.teams.filter(Boolean).length;
    let h = `<span>${ic("users")}Jamoalar: <b>${n}/8</b></span>`;
    if (S.me.adm) h += `<span>${ic("crown")}Admin ko'rinishi: faqat kuzatish</span>`;
    else if (S.my < 0) h += '<span class="mut">Siz hali jamoada emassiz. Jamoa yarating yoki setkadagi jamoaga qo\'shiling.</span>';
    else {
      const T = S.teams[S.my], own = T.o === S.me.id, p = myPos(S.my);
      h += `<span>${ic(own ? "crown" : "shield")}<b style="color:${T.c}">${esc(T.n)}</b> · ${own ? "Sardor" : "A'zo"}${p != null ? " · " + PN[p] : ""}</span><button class="mb sec" data-a="view" type="button">Jamoani ko'rish</button><button class="mb" data-a="${own ? "del" : "leave"}" type="button">${own ? "Jamoani o'chirish" : "Joyni bo'shatishni so'rash"}</button>`;
    }
    el.innerHTML = h;
  }
  function renderStage() {
    const C = [[0, 4], [1, 4], [2, 5], [3, 5], [4, 6], [5, 6]]; let p = "";
    for (const [f, t] of C) {
      const x1 = POX[f < 4 ? 0 : 1] + 210, y1 = TOP[f] + 47, x2 = POX[t < 4 ? 0 : t < 6 ? 1 : 2], y2 = TOP[t] + 47, mx = (x1 + x2) / 2;
      p += `<path class="${S.mt[f].s === "t" ? "hot" : "dim"}" d="M${x1} ${y1}H${mx}V${y2}H${x2}"/><circle cx="${x2}" cy="${y2}" r="3.5" class="nd"/>`;
    }
    p += `<path class="${S.mt[6].s === "t" ? "hot" : "dim"}" d="M730 272H800"/>`;
    const tm = (t, sc, w) => `<div class="tm${w ? " w" : ""}${t == null ? " em2" : ""}"><span><i style="background:${t == null ? "#444" : S.teams[t].c}"></i>${t == null ? "Jamoa kutilmoqda" : esc(S.teams[t].n)}</span><b>${sc ?? "–"}</b></div>`;
    const cards = S.mt.map((m, i) => { const r = i < 4 ? 0 : i < 6 ? 1 : 2, c = cntf(i); return `<div class="mc ${m.s}" data-i="${i}" style="left:${POX[r]}px;top:${TOP[i]}px;--d:${r * 2 + i % 2}"><div class="hd"><span>${lab(i)}</span><span class="st">${m.s === "j" ? '<u class="ld"></u>' : ""}${ST[m.s]}</span></div>${tm(m.a, m.sa, m.s === "t" && m.sa > m.sb)}${tm(m.b, m.sb, m.s === "t" && m.sb > m.sa)}<div class="ft">${c === "0/0" ? "Jamoa kutilmoqda" : "Joylar: " + c + " · Xaritani ochish"}</div></div>`; }).join("");
    const w = S.mt[6].s === "t" && S.mt[6].w != null ? S.teams[S.mt[6].w] : null;
    $("#stg").innerHTML = `<svg class="cn" width="1000" height="560">${p}</svg>${cards}<div class="ch" style="left:800px;top:192px"><svg class="ring" viewBox="0 0 160 160"><circle cx="80" cy="80" r="74" class="r1"/><circle cx="80" cy="80" r="62" class="r2"/></svg><div>${ic("trophy", "tc")}<b>CHEMPION</b>${w ? `<small class="champ" style="color:${w.c}">${esc(w.n)}</small>` : "<small>Final natijasi kutilmoqda</small>"}</div></div>`
      + (S.teams.some(Boolean) ? "" : '<div class="emp">Hali birorta jamoa yo\'q. Birinchi bo\'lib jamoa yarating!</div>');
    $("#stg").classList.toggle("noa", built);
  }

  /* ---------- xarita ---------- */
  const hexp = r => [0, 1, 2, 3, 4, 5].map(i => (r * Math.cos(Math.PI / 3 * i)).toFixed(1) + "," + (r * Math.sin(Math.PI / 3 * i)).toFixed(1)).join(" ");
  const HX = hexp(30), HX2 = hexp(10), HX3 = hexp(11);
  const twr = (p, i, c) => `<g class="tw" style="--i:${i}"><polygon points="${HX3}" transform="translate(${p[0]} ${p[1]})" fill="#0f1219" stroke="${c}" stroke-width="2.5"/><circle cx="${p[0]}" cy="${p[1]}" r="2.5" fill="${c}"/></g>`;
  const TR = [[100, 560], [100, 380], [100, 240], [260, 700], [430, 700], [600, 700], [230, 570], [320, 480]];
  const base2 = (x, y, c) => `<g class="bs"><circle cx="${x}" cy="${y}" r="46" fill="#0d1014" stroke="${c}" stroke-width="2"/><circle cx="${x}" cy="${y}" r="33" fill="none" stroke="${c}" stroke-opacity=".5" stroke-dasharray="3 6"/><polygon points="${hexp(14)}" transform="translate(${x} ${y}) rotate(30)" fill="${c}"/></g>`;
  const RV = "M45 70C250 260 360 370 440 440S680 690 755 745", F = 'x="20" y="20" width="760" height="760"';
  const MAP = `<defs><pattern id="gp" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".05"/></pattern>
<radialGradient id="gr" cx="22%" cy="78%" r="58%"><stop offset="0" stop-color="#2f9e79" stop-opacity=".3"/><stop offset="1" stop-color="#2f9e79" stop-opacity="0"/></radialGradient>
<radialGradient id="gd" cx="78%" cy="22%" r="58%"><stop offset="0" stop-color="#c0453f" stop-opacity=".3"/><stop offset="1" stop-color="#c0453f" stop-opacity="0"/></radialGradient>
<radialGradient id="vg" cx="50%" cy="50%" r="70%"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>
<linearGradient id="sg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8fb4ff" stop-opacity="0"/><stop offset="1" stop-color="#8fb4ff" stop-opacity=".14"/></linearGradient>
<clipPath id="mc"><rect ${F} rx="10"/></clipPath></defs>
<rect ${F} rx="10" fill="#0b0d12"/><rect ${F} fill="url(#gp)"/><rect ${F} fill="url(#gr)"/><rect ${F} fill="url(#gd)"/>
<path d="${RV}" fill="none" stroke="#2d4a63" stroke-opacity=".55" stroke-width="44" stroke-linecap="round"/><path d="${RV}" class="rvf" fill="none" stroke="#9fc2e6" stroke-opacity=".4" stroke-width="2"/>
<g fill="#0c1410" stroke="#fff" stroke-opacity=".06"><ellipse cx="250" cy="330" rx="70" ry="48"/><ellipse cx="190" cy="580" rx="58" ry="44"/><ellipse cx="370" cy="600" rx="55" ry="40"/></g><g fill="#160e0e" stroke="#fff" stroke-opacity=".06"><ellipse cx="550" cy="470" rx="70" ry="48"/><ellipse cx="610" cy="220" rx="58" ry="44"/><ellipse cx="430" cy="200" rx="55" ry="40"/></g>
<g fill="none" stroke="#5c4d36" stroke-opacity=".6" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"><path class="ln" d="M100 700V100H700"/><path class="ln" d="M100 700H700V100"/><path class="ln" d="M100 700L700 100"/></g>
<g class="ln2" fill="none" stroke="#d9c08a" stroke-opacity=".28" stroke-width="1.5" stroke-dasharray="6 10"><path d="M100 700V100H700"/><path d="M100 700H700V100"/><path d="M100 700L700 100"/></g>
<g clip-path="url(#mc)"><g class="sw"><path d="M400 400L400 -60A460 460 0 0 1 727 74Z" fill="url(#sg)"/></g></g>
${TR.map((p, i) => twr(p, i, "#3fa37a")).join("")}${TR.map((p, i) => twr([800 - p[0], 800 - p[1]], i, "#c0453f")).join("")}${base2(105, 695, "#3fa37a")}${base2(695, 105, "#c0453f")}
<g class="rs"><polygon points="${hexp(28)}" transform="translate(520 520)" fill="#150f1f" stroke="#8b6bd1" stroke-width="2"/><text x="520" y="524" fill="#b9a2ee" font-size="10" text-anchor="middle" letter-spacing="2" font-family="system-ui">ROSHAN</text></g>
<text x="105" y="772" fill="#3fa37a" font-size="13" text-anchor="middle" letter-spacing="4" font-family="system-ui">RADIANT</text><text x="695" y="50" fill="#c0453f" font-size="13" text-anchor="middle" letter-spacing="4" font-family="system-ui">DIRE</text>
<rect ${F} rx="10" fill="url(#vg)" pointer-events="none"/><rect ${F} rx="10" fill="none" stroke="#3b3a4d" stroke-width="2"/><path d="M20 70V20H70M730 20H780V70M780 730V780H730M70 780H20V730" fill="none" stroke="#c58a4e" stroke-width="3"/>`;
  const sideT = s => { const m = S.mt[mi]; return s ? m.b : m.a; };
  function mk(s, k, x, y, col) {
    const t = sideT(s), p = slot(t, k), n = p && p.st === "paid" ? p.n : null, r = p && !n ? p : null, mp = iMine(p), me = !!n && mp;
    const lb = n ? (me ? "Siz" : n) : r ? (mp ? (r.st === "pending" ? "Tekshiruvda" : "To'lov kerak") : "Rezerv") : "Bo'sh";
    return `<g transform="translate(${x} ${y})"><g class="mk${n ? "" : r ? " rz" : " em"}${me ? " me" : ""}" data-s="${s}" data-k="${k}" style="--i:${s * 5 + k};--c:${col}"><polygon class="hx" points="${HX}"/>${n ? `<text class="in" y="8">${esc(n[0])}</text>` : `<use href="#i-${r ? "clock" : RI[k]}" x="-12" y="-12" width="24" height="24" class="ico"/>`}<path class="rt2" d="M-40 -28V-40H-28M28 -40H40V-28M40 28V40H28M-28 40H-40V28"/><polygon class="bg" points="${HX2}" transform="translate(25 -25)"/><text class="bn" x="25" y="-21">${k + 1}</text><g class="nm"><rect x="-46" y="38" width="92" height="20" rx="3"/><text y="52">${esc(lb)}</text></g><title>${PN[k]} — ${n ? "boshlig'i: " + esc(n) : r ? "rezerv qilingan" : "bo'sh joy, bosib band qiling"}</title></g></g>`;
  }
  function drawMk() {
    let h = "";
    for (const s of [0, 1]) { const t = sideT(s); if (t == null) continue; for (let k = 0; k < 5; k++) { const [x, y] = RP[k]; h += mk(s, k, s ? 800 - x : x, s ? 800 - y : y, S.teams[t].c); } }
    $("#mks").innerHTML = h;
  }
  function panel() {
    let h = "";
    for (const s of [0, 1]) {
      const t = sideT(s), T = t == null ? null : S.teams[t];
      h += `<div class="pt" style="--c:${T ? T.c : "#666"}"><h4>${T ? esc(T.n) : "Jamoa kutilmoqda"}<small>${s ? "Dire" : "Radiant"}</small></h4>`;
      if (!T) h += '<p class="mt">Hali jamoa yo\'q</p>';
      else {
        for (let k = 0; k < 5; k++) {
          const p = slot(t, k), mp = iMine(p), n = p && p.st === "paid" ? p.n : null;
          h += `<div class="pr${mp ? " me" : ""}" data-s="${s}" data-k="${k}"><span class="pn">${k + 1}</span><span class="pnm">${ic(RI[k])}${PN[k]}</span><b>${n ? esc(n) : p ? esc(p.n) + " · rezerv" : "Bo'sh"}</b>${n && !mp && !S.me.adm ? `<button class="dmb" data-dm="${p.u}" type="button" title="Shaxsiy xabar">${ic("mail")}</button>` : ""}${T.lk ? "" : `<button class="${!p || (mp && p.st === "hold") ? "" : "dn"}">${!p ? "Band qilish" : mp ? (p.st === "hold" ? "To'lovni yakunlash" : p.st === "pending" ? "Tekshiruvda" : "Sizniki") : (p.st === "paid" ? "Band" : "Rezerv")}</button>`}</div>`;
        }
        if (S.my === t && !S.me.adm) h += `<div class="tact"><button class="mb" data-a="${T.o === S.me.id ? "del" : "leave"}" type="button">${T.o === S.me.id ? "Jamoani o'chirish" : "Joyni bo'shatishni so'rash"}</button></div>`;
      }
      h += "</div>";
    }
    $("#mpl").innerHTML = h;
  }
  function chatUI() {
    const m = S.mt[mi], Sd = [0, 1].filter(s => sideT(s) != null), el = $("#chat");
    if (!Sd.length) { el.innerHTML = ""; return; }
    if (!Sd.includes(ct)) ct = Sd.find(s => S.mem.includes(sideT(s))) ?? Sd[0];
    const t = sideT(ct), ok = S.mem.includes(t), old = el.querySelector("input"), v = old ? old.value : "", foc = old && document.activeElement === old;
    el.style.setProperty("--c", S.teams[t].c);
    el.innerHTML = `<div class="ct">${Sd.map(s => { const x = sideT(s); return `<button type="button" class="ctab${s === ct ? " on" : ""}" data-s="${s}" style="--c:${S.teams[x].c}">${esc(S.teams[x].n)}</button>`; }).join("")}</div>` +
      (ok ? `<div class="cl" id="cmsg"></div><div class="chips">${CHIPS.map(c => `<button type="button" class="chip">${esc(c)}</button>`).join("")}</div><form class="cf" id="cf"><input name="cm" maxlength="300" placeholder="Jamoa suhbatiga yozing..." autocomplete="off"><button aria-label="Yuborish">${ic("send")}</button></form>`
        : `<div class="lock">${ic("lock")}<p>Bu jamoaning suhbati yopiq.</p><small>Suhbatga qo'shilish uchun shu jamoada joy band qiling.</small></div>`);
    if (ok) { const i = el.querySelector("input"); i.value = v; if (foc) i.focus(); chatMsgs(true); }
  }
  function chatMsgs(force) {
    const t = sideT(ct), e = $("#cmsg"); if (!e) return;
    const A = S.chat[t] || [], atb = e.scrollHeight - e.scrollTop - e.clientHeight < 40;
    e.innerHTML = A.length ? A.map(x => x.s ? `<div class="cm sys">${esc(x.m)}</div>` : `<div class="cm${x.u === S.me.id ? " me" : ""}"><b>${esc(x.n)}</b>${x.p ? `<i>${esc(x.p)}</i>` : ""}<span>${esc(x.m)}</span><time>${hm(x.t)}</time></div>`).join("") : '<div class="cm sys">Hali xabar yo\'q. Birinchi bo\'lib yozing!</div>';
    if (atb || force) e.scrollTop = e.scrollHeight;
  }
  function drawMap() {
    const m = S.mt[mi], A = m.a == null ? null : S.teams[m.a], Bt = m.b == null ? null : S.teams[m.b], c = t => t ? t.c : "#888", nm = t => t ? esc(t.n) : "Jamoa kutilmoqda";
    $("#mh").innerHTML = `<span style="color:${c(A)}">${nm(A)}</span><span class="sc">${m.s === "t" ? m.sa + " : " + m.sb : "VS"}</span><span style="color:${c(Bt)}">${nm(Bt)}</span><em class="bd ${m.s}">${ST[m.s]}</em>`;
    $("#mhint").textContent = `Joyni band qilish: ${fmt(S.cfg.price)} so'm. Bo'sh joyni bosing va to'lovni yuboring: admin tasdiqlagach joy sizniki bo'ladi. O'yin Steam'da o'ynaladi, natijani admin kiritadi.`;
    $("#msvg").innerHTML = MAP + '<g id="mks"></g>'; drawMk(); panel(); chatUI();
  }
  function openM(i, el) {
    mi = i; ct = -1; const r = el.getBoundingClientRect(), o = $("#mp");
    o.style.setProperty("--x", r.left + r.width / 2 + "px"); o.style.setProperty("--y", r.top + r.height / 2 + "px");
    drawMap(); o.classList.remove("rdy", "open"); o.classList.add("on");
    setTimeout(() => o.classList.add("open"), 40); setTimeout(() => o.classList.add("rdy"), 3400);
  }
  function closeM() { const o = $("#mp"); o.classList.remove("open"); setTimeout(() => { o.classList.remove("on", "rdy"); }, 750); }
  const ovOn = () => $("#mp").classList.contains("on");

  /* ---------- joy band qilish va to'lov ---------- */
  async function act(s, k) {
    const m = S.mt[mi], t = s ? m.b : m.a; if (t == null) return tst("Bu joyga hali jamoa kelmagan.");
    const p = slot(t, k), mp = iMine(p);
    if (S.teams[t].lk) return tst(p && p.st === "paid" ? `${PN[k]} boshlig'i: ${p.n}. O'yin boshlangan, tarkib qulflangan.` : "O'yin boshlangan, tarkib qulflangan.");
    if (p) {
      if (mp) { if (p.st === "hold") return openPay(t, k); if (p.st === "pending") return tst("To'lovingiz admin tomonidan tekshirilmoqda."); return tst("Bu joy sizniki. Joyni bo'shatish yoki almashtirish uchun support xizmatiga yozing."); }
      return tst(p.st === "paid" ? `${PN[k]} joyining boshlig'i: ${p.n}` : `${PN[k]} joyi boshqa o'yinchi tomonidan rezerv qilingan.`);
    }
    if (S.me.adm) return tst("Admin faqat kuzatadi: o'yinchi bo'la olmaydi.");
    await api("/api/joy/band", { t, k }); await load(); openPay(t, k);
  }
  function closePay() { $("#pay").style.display = "none"; clearInterval(PT); PAYT = null; }
  function tickPay() {
    if (!PAYT) return; const p = slot(PAYT[0], PAYT[1]);
    if (!iMine(p) || p.st !== "hold") { closePay(); return; }
    const l = p.end - Date.now();
    if (l <= 0) { closePay(); tst("Rezerv muddati tugadi. Joyni qayta band qiling."); load(); return; }
    const e = $("#ptm"); if (e) e.textContent = `Rezerv amal qiladi: ${String(Math.floor(l / 60000)).padStart(2, "0")}:${String(Math.floor(l / 1000) % 60).padStart(2, "0")}`;
  }
  function openPay(t, k) {
    const p = slot(t, k), T = S.teams[t]; if (!iMine(p) || p.st !== "hold" || !T) return;
    $("#payb").innerHTML = `<h3>Joyni band qilish</h3><div class="pinfo"><div><span>Jamoa</span><b style="color:${T.c}">${esc(T.n)}</b></div><div><span>Lavozim</span><b>${PN[k]}</b></div><div><span>Summa</span><b class="amt">${fmt(p.amt)} so'm</b></div></div>
${S.cfg.card ? `<div class="rq"><span>To'lov rekvizitlari</span><b>${esc(S.cfg.card)}</b>${S.cfg.note ? `<small>${esc(S.cfg.note)}</small>` : ""}</div>` : '<div class="rq warn">To\'lov rekvizitlari hali kiritilmagan. Admin bilan support orqali bog\'laning.</div>'}
<ol class="steps"><li>Summani yuqoridagi rekvizitga o'tkazing.</li><li>Tranzaksiya raqami yoki kartaning oxirgi 4 raqamini kiriting.</li><li>"To'lov qildim" tugmasini bosing. Admin tasdiqlagach joy sizniki bo'ladi.</li></ol>
<form id="payf"><input name="ref" maxlength="30" placeholder="Tranzaksiya raqami yoki karta oxirgi 4 raqami" autocomplete="off"><div id="pm3"></div><div class="timer" id="ptm"></div><div class="acts"><button>To'lov qildim</button><a href="#" class="btn2" id="pcx">Rezervni bekor qilish</a></div></form>`;
    PAYT = [t, k]; $("#pay").style.display = "grid"; clearInterval(PT); PT = setInterval(tickPay, 1000); tickPay();
  }
  $("#pay").addEventListener("submit", async e => {
    e.preventDefault(); if (!PAYT) return; const p = slot(PAYT[0], PAYT[1]); if (!p) return;
    const ref = e.target.elements.ref.value.trim();
    if (!/^[A-Za-z0-9 \-]{4,30}$/.test(ref)) { const m = $("#pm3"); m.textContent = "Tranzaksiya raqami yoki karta oxirgi 4 raqamini kiriting (4-30 belgi)."; m.className = "msg xato"; return; }
    try { await api("/api/joy/yubor", { id: p.id, ref }); closePay(); tst("To'lovingiz yuborildi. Admin tasdiqlagach joy sizniki bo'ladi."); await load(); } catch (x) { /* xato ko'rsatildi */ }
  });
  $("#pay").addEventListener("click", async e => {
    if (e.target.id !== "pcx") return; e.preventDefault();
    const p = PAYT && slot(PAYT[0], PAYT[1]);
    try { if (p) await api("/api/joy/bekor", { id: p.id }); closePay(); tst("Rezerv bekor qilindi."); await load(); } catch (x) { /* xato ko'rsatildi */ }
  });

  /* ---------- jamoa amallari ---------- */
  async function teamAct(e) {
    const b = e.target.closest("[data-a]"); if (!b) return; const t = S.my, a = b.dataset.a; if (t < 0) return;
    if (a === "view") { const i = S.mt.map((m, j) => (m.a === t || m.b === t) ? j : -1).filter(j => j >= 0).pop(); const c = document.querySelector(`.mc[data-i="${i}"]`); return c && openM(i, c); }
    if (a === "leave") { const k = myPos(t); location.href = "/xabarlar?t=" + encodeURIComponent(`${S.teams[t].n} jamoasidagi ${k != null ? PN[k] : ""} joyini bo'shatishni so'rayman.`); return; }
    if (!b.dataset.c) { b.dataset.c = 1; b.classList.add("cf2"); b.textContent = "Tasdiqlang"; setTimeout(() => { if (b.isConnected) { renderBar(); if (ovOn()) panel(); } }, 4000); return; }
    try { await api("/api/jamoa/ochir", {}); tst("Jamoa o'chirildi. Endi yangi jamoa yaratishingiz yoki boshqasiga qo'shilishingiz mumkin."); if (ovOn()) closeM(); await load(); } catch (x) { /* xato ko'rsatildi */ }
  }
  $("#tc").addEventListener("click", teamAct); $("#mpl").addEventListener("click", teamAct);

  /* ---------- chat ---------- */
  $("#chat").addEventListener("click", async e => {
    const b = e.target.closest(".ctab,.chip"); if (!b) return;
    if (b.classList.contains("chip")) return send(b.textContent);
    ct = +b.dataset.s; chatUI();
  });
  $("#chat").addEventListener("submit", e => { e.preventDefault(); const i = e.target.elements.cm; const v = i.value; i.value = ""; send(v); });
  async function send(m) { m = m.trim(); if (!m) return; try { await api("/api/chat/yubor", { t: sideT(ct), m }); await load(); } catch (x) { /* xato ko'rsatildi */ } }

  /* ---------- umumiy hodisalar ---------- */
  $("#stg").addEventListener("click", e => {
    const c = e.target.closest(".mc"); if (!c) return; const i = +c.dataset.i;
    if (S.mt[i].a == null && S.mt[i].b == null) return tst("Bu o'yinga hali jamoa kelmagan. Jamoa yarating!");
    openM(i, c);
  });
  $("#mp").addEventListener("click", e => {
    const d = e.target.closest(".dmb"); if (d) { location.href = "/xabarlar?u=" + d.dataset.dm; return; }
    const x = e.target.closest(".mk,.pr"); if (x && x.dataset.k != null) act(+x.dataset.s, +x.dataset.k).catch(() => { });
  });
  $("#mpl").addEventListener("mouseover", e => {
    const r = e.target.closest(".pr"); document.querySelectorAll("#mp .mk.hl").forEach(x => x.classList.remove("hl"));
    if (r) { const m = $(`#mp .mk[data-s="${r.dataset.s}"][data-k="${r.dataset.k}"]`); if (m) m.classList.add("hl"); }
  });
  $("#mx").onclick = closeM;
  addEventListener("keydown", e => { if (e.key === "Escape") { if ($("#pay").style.display === "grid") { closePay(); } else if (ovOn()) closeM(); } });
  const nf = $("#nf");
  if (nf) nf.onsubmit = async e => {
    e.preventDefault(); const n = nf.elements.tn.value.trim(), c = nf.querySelector("input[name=col]:checked").value;
    if (n.length < 3) return tst("Jamoa nomi kamida 3 ta belgidan iborat bo'lsin.");
    try { const j = await api("/api/jamoa/yarat", { n, c }); nf.reset(); await load(); const card = document.querySelector(`.mc[data-i="${j.seed >> 1}"]`); if (card) { card.classList.remove("fl2"); void card.offsetWidth; card.classList.add("fl2"); } tst(`"${n}" jamoasi yaratildi! Endi o'yinni bosib joyingizni egallang.`); } catch (x) { /* xato ko'rsatildi */ }
  };

  function render() {
    const s = JSON.stringify([S.teams, S.mt, Object.entries(S.sl).map(([k, p]) => [k, p.u, p.st]), S.chat, S.my, S.cfg]);
    if (s === sig) return; sig = s;
    renderBar(); renderStage(); built = true;
    if (ovOn() && mi != null) { drawMk(); panel(); chatUI(); }
  }
  stars($("#cv"));
  load().catch(() => { });
  setInterval(() => { if (!document.hidden && !PAYT) load().catch(() => { }); }, 4000);
})();
