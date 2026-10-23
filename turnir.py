"""Turnir: jamoalar, joylar va to'lovlar, jamoa chati, xabarlar (shaxsiy va support)."""
import sqlite3, re
from core import *

HOLD = 15 * 60
PN = ["Mider", "Kerri", "Tank (Slojniy)", "Paderjka", "To'liq paderjka"]
RN = ["Chorak final", "Yarim final", "Final"]
SRC = {4: (0, 1), 5: (2, 3), 6: (4, 5)}
PAR = {0: 4, 1: 4, 2: 5, 3: 5, 4: 6, 5: 6}
FAOL = "('hold','pending','paid')"


def sozlama(k, d=""):
    r = q1("SELECT v FROM settings WHERE k=?", (k,))
    return r["v"] if r else d


def narx():
    try:
        return int(sozlama("narx", "15000"))
    except ValueError:
        return 15000


def ad(u):
    return u["taxallus"] or u["username"]


def jurnal(cmd, res):
    ex("INSERT INTO cmdlog(ts,cmd,res) VALUES(?,?,?)", (hozir(), cmd, res))


def sys_chat(seed, text):
    ex("INSERT INTO team_chat(team_seed,user_id,name,label,text,ts,sys) VALUES(?,NULL,'','',?,?,1)",
       (seed, text, hozir()))


def support_xabar(uid, text):
    ex("INSERT INTO messages(thread,sender,text,ts) VALUES(?,?,?,?)", ("s:%d" % uid, "@adm", text, hozir()))


def expire():
    ex("UPDATE payments SET status='expired' WHERE status='hold' AND created_at<?", (hozir() - HOLD,))


def lab(i):
    r = 0 if i < 4 else 1 if i < 6 else 2
    return RN[r] + ((" %d" % (i + 1 if r == 0 else i - 3)) if r < 2 else "")


def matches():
    """7 ta o'yin holati va jamoalar (seed -> qator). Keyingi bosqich jamoalari g'oliblardan olinadi."""
    tm = {r["seed"]: r for r in qa("SELECT * FROM teams")}
    rs = {r["idx"]: r for r in qa("SELECT * FROM matches")}

    def g(j):
        w = rs[j]["winner"]
        return w if w is not None and w in tm else None
    M = []
    for i in range(7):
        if i < 4:
            a = 2 * i if 2 * i in tm else None
            b = 2 * i + 1 if 2 * i + 1 in tm else None
        else:
            a, b = g(SRC[i][0]), g(SRC[i][1])
        r = rs[i]
        M.append(dict(s=r["status"], sa=r["sa"], sb=r["sb"], a=a, b=b, w=r["winner"]))
    return M, tm


def lk(seed, M):
    """Jamoaning joriy (eng yuqori bosqich) o'yini boshlangan bo'lsa, tarkib qulflanadi."""
    for i in range(6, -1, -1):
        if seed in (M[i]["a"], M[i]["b"]):
            return M[i]["s"] != "k"
    return False


def azo_jamoa(u):
    """Foydalanuvchi a'zo bo'lgan jamoa seed'i (sardor yoki to'langan joy egasi) yoki -1."""
    r = q1("SELECT seed FROM teams WHERE owner_id=?", (u["id"],))
    if r:
        return r["seed"]
    r = q1("SELECT team_seed FROM payments WHERE user_id=? AND status='paid'", (u["id"],))
    return r["team_seed"] if r else -1


def holat(u):
    expire()
    M, tm = matches()
    uid, adm = u["id"], bool(u["is_admin"])
    own = {r["id"]: r for r in qa("SELECT id,username,taxallus FROM users")}
    teams = [None] * 8
    for s, t in tm.items():
        teams[s] = {"n": t["name"], "c": t["color"], "o": t["owner_id"], "lk": lk(s, M)}
    sl = {}
    for p in qa("SELECT * FROM payments WHERE status IN " + FAOL):
        x = own.get(p["user_id"])
        d = {"u": p["user_id"], "n": ad(x) if x else "?", "st": p["status"]}
        if p["user_id"] == uid:
            d["id"], d["amt"] = p["id"], p["amount"]
            if p["status"] == "hold":
                d["ex"] = max(0, p["created_at"] + HOLD - hozir())
        sl["%d.%d" % (p["team_seed"], p["pos"])] = d
    my = azo_jamoa(u)
    mem = sorted(tm) if adm else ([my] if my >= 0 else [])
    chat = {}
    for s in mem:
        rows = qa("SELECT * FROM (SELECT * FROM team_chat WHERE team_seed=? ORDER BY id DESC LIMIT 100) ORDER BY id", (s,))
        chat[s] = [{"u": r["user_id"], "n": r["name"], "p": r["label"], "m": r["text"], "t": r["ts"], "s": r["sys"]} for r in rows]
    return dict(me=dict(id=uid, adm=adm, name=ad(u)), teams=teams, mt=M, sl=sl,
                cfg=dict(price=narx(), card=sozlama("karta"), note=sozlama("izoh")),
                my=my, mem=mem, chat=chat)


@app.route("/turnir")
@kerak
def turnir():
    return render_template("turnir.html", nav="tour", RANGLAR=RANGLAR)


@app.route("/api/turnir")
@api_kerak
def api_turnir():
    return jsonify(holat(joriy_user()))


@app.route("/api/jamoa/yarat", methods=["POST"])
@api_kerak
def jamoa_yarat():
    u = joriy_user()
    d = request.get_json(silent=True) or {}
    if u["is_admin"]:
        return xato("Admin jamoa yarata olmaydi.")
    n = " ".join(str(d.get("n", "")).split())
    c = d.get("c")
    if not 3 <= len(n) <= 22 or any(ord(ch) < 32 for ch in n):
        return xato("Jamoa nomi 3-22 ta belgidan iborat bo'lsin.")
    if c not in RANGLAR:
        return xato("Rang noto'g'ri.")
    expire()
    M, tm = matches()
    if any(m["s"] != "k" for m in M):
        return xato("Turnir boshlangan: yangi jamoa qo'shib bo'lmaydi.")
    if (q1("SELECT 1 FROM payments WHERE user_id=? AND status IN " + FAOL, (u["id"],))
            or q1("SELECT 1 FROM teams WHERE owner_id=?", (u["id"],))):
        return xato("Siz allaqachon jamoadasiz. Yangi jamoa yaratish uchun avval jamoadan chiqing yoki uni o'chiring.")
    free = [s for s in range(8) if s not in tm]
    if not free:
        return xato("Turnirda joy qolmadi: 8 ta jamoa to'ldi.")
    if limit(("jamoa", u["id"]), 5, 3600):
        return xato("Juda ko'p urinish. Keyinroq qayta urinib ko'ring.", 429)
    try:
        ex("INSERT INTO teams(seed,name,color,owner_id,created_at) VALUES(?,?,?,?,?)",
           (free[0], n, c, u["id"], hozir()))
    except sqlite3.IntegrityError:
        if q1("SELECT 1 FROM teams WHERE name=?", (n,)):
            return xato("Bunday nomli jamoa allaqachon bor.")
        return xato("Joy band bo'lib qoldi. Qayta urinib ko'ring.")
    sys_chat(free[0], "Jamoa yaratildi. Xush kelibsiz, %s!" % ad(u))
    return jsonify(ok=True, seed=free[0])


@app.route("/api/jamoa/ochir", methods=["POST"])
@api_kerak
def jamoa_ochir():
    u = joriy_user()
    t = q1("SELECT * FROM teams WHERE owner_id=?", (u["id"],))
    if not t:
        return xato("Sizning jamoangiz yo'q.")
    s = t["seed"]
    M, _ = matches()
    if any(m["s"] != "k" and s in (m["a"], m["b"]) for m in M):
        return xato("Turnir boshlangan: jamoani o'chirib bo'lmaydi.")
    if q1("SELECT 1 FROM payments WHERE team_seed=? AND status IN ('pending','paid')", (s,)):
        return xato("Jamoada to'langan yoki tekshiruvdagi joylar bor. Avval support xizmatiga murojaat qiling.")
    ex("UPDATE payments SET status='cancelled' WHERE team_seed=? AND status='hold'", (s,))
    ex("DELETE FROM team_chat WHERE team_seed=?", (s,))
    ex("DELETE FROM teams WHERE id=?", (t["id"],))
    return jsonify(ok=True)


@app.route("/api/joy/band", methods=["POST"])
@api_kerak
def joy_band():
    u = joriy_user()
    d = request.get_json(silent=True) or {}
    try:
        t, k = int(d.get("t")), int(d.get("k"))
    except (TypeError, ValueError):
        return xato("Noto'g'ri so'rov.")
    if u["is_admin"]:
        return xato("Admin faqat kuzatadi: o'yinchi bo'la olmaydi.")
    expire()
    M, tm = matches()
    if t not in tm or not 0 <= k < 5:
        return xato("Bu joyga hali jamoa kelmagan.")
    if lk(t, M):
        return xato("O'yin boshlangan, tarkib qulflangan.")
    own = q1("SELECT seed,name FROM teams WHERE owner_id=?", (u["id"],))
    if own and own["seed"] != t:
        return xato('Siz "%s" jamoasining sardorisiz. Boshqa jamoaga o\'tish uchun avval o\'z jamoangizni o\'chiring.' % own["name"])
    my = q1("SELECT status FROM payments WHERE user_id=? AND status IN " + FAOL, (u["id"],))
    if my:
        return xato("Sizda tugallanmagan rezerv bor. Avval uni yakunlang yoki bekor qiling." if my["status"] == "hold"
                    else "Sizda band qilingan joy bor. Almashtirish uchun support xizmatiga yozing.")
    if limit(("band", u["id"]), 12, 600):
        return xato("Juda ko'p urinish. Keyinroq qayta urinib ko'ring.", 429)
    try:
        c = ex("INSERT INTO payments(user_id,team_seed,pos,amount,status,created_at) VALUES(?,?,?,?,'hold',?)",
               (u["id"], t, k, narx(), hozir()))
    except sqlite3.IntegrityError:
        return xato("Bu joy boshqa o'yinchi tomonidan band qilingan yoki rezerv qilingan.")
    return jsonify(ok=True, id=c.lastrowid)


def _mening_tolovim(u, pid):
    expire()
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    return q1("SELECT * FROM payments WHERE id=? AND user_id=? AND status='hold'", (pid, u["id"]))


@app.route("/api/joy/yubor", methods=["POST"])
@api_kerak
def joy_yubor():
    u = joriy_user()
    d = request.get_json(silent=True) or {}
    p = _mening_tolovim(u, d.get("id"))
    if not p:
        return xato("Rezerv topilmadi yoki muddati tugagan. Joyni qayta band qiling.")
    ref = str(d.get("ref", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9 \-]{4,30}", ref):
        return xato("Tranzaksiya raqami yoki karta oxirgi 4 raqamini kiriting (4-30 belgi).")
    ex("UPDATE payments SET status='pending', ref=?, submitted_at=? WHERE id=?", (ref, hozir(), p["id"]))
    return jsonify(ok=True)


@app.route("/api/joy/bekor", methods=["POST"])
@api_kerak
def joy_bekor():
    u = joriy_user()
    p = _mening_tolovim(u, (request.get_json(silent=True) or {}).get("id"))
    if not p:
        return xato("Rezerv topilmadi.")
    ex("UPDATE payments SET status='cancelled', decided_at=? WHERE id=?", (hozir(), p["id"]))
    return jsonify(ok=True)


@app.route("/api/chat/yubor", methods=["POST"])
@api_kerak
def chat_yubor():
    u = joriy_user()
    d = request.get_json(silent=True) or {}
    try:
        t = int(d.get("t"))
    except (TypeError, ValueError):
        return xato("Noto'g'ri so'rov.")
    m = str(d.get("m", "")).strip()[:300]
    if not m:
        return xato("Xabar bo'sh.")
    if not q1("SELECT 1 FROM teams WHERE seed=?", (t,)):
        return xato("Jamoa topilmadi.")
    if not u["is_admin"] and azo_jamoa(u) != t:
        return xato("Bu jamoaning suhbati yopiq.", 403)
    if limit(("chat", u["id"]), 20, 60):
        return xato("Juda tez yozyapsiz. Biroz kuting.", 429)
    if u["is_admin"]:
        lb = "Admin"
    else:
        p = q1("SELECT pos FROM payments WHERE user_id=? AND status='paid'", (u["id"],))
        lb = PN[p["pos"]] if p else "Sardor"
    ex("INSERT INTO team_chat(team_seed,user_id,name,label,text,ts,sys) VALUES(?,?,?,?,?,?,0)",
       (t, u["id"], ad(u), lb, m, hozir()))
    return jsonify(ok=True)


# ---------------- Xabarlar: shaxsiy va support ----------------
def me_key(u):
    return "@adm" if u["is_admin"] else str(u["id"])


def thr_ruxsat(u, k):
    if not isinstance(k, str):
        return False
    if k.startswith("s:"):
        return k[2:].isdigit() and (bool(u["is_admin"]) or int(k[2:]) == u["id"])
    if k.startswith("u:") and not u["is_admin"]:
        p = k[2:].split("|")
        return len(p) == 2 and all(x.isdigit() for x in p) and int(p[0]) < int(p[1]) and str(u["id"]) in p
    return False


def unread_count(u):
    me = me_key(u)
    if u["is_admin"]:
        cond, args = "m.thread LIKE 's:%'", []
    else:
        cond = "(m.thread=? OR m.thread LIKE ? OR m.thread LIKE ?)"
        args = ["s:%d" % u["id"], "u:%d|%%" % u["id"], "u:%%|%d" % u["id"]]
    return q1("SELECT COUNT(*) c FROM messages m WHERE m.sender!=? AND m.id>COALESCE("
              "(SELECT last_id FROM reads r WHERE r.thread=m.thread AND r.reader=?),0) AND " + cond,
              [me, me] + args)["c"]


@app.context_processor
def _belgi():
    u = joriy_user()
    return {"unread": unread_count(u) if u else 0}


def _kim(u, k):
    if k.startswith("s:"):
        if not u["is_admin"]:
            return {"id": None, "n": "Support xizmati"}
        x = q1("SELECT id,username,taxallus FROM users WHERE id=?", (int(k[2:]),))
        return {"id": x["id"], "n": ad(x)} if x else {"id": None, "n": "(o'chirilgan foydalanuvchi)"}
    o = [int(x) for x in k[2:].split("|") if int(x) != u["id"]][0]
    x = q1("SELECT id,username,taxallus FROM users WHERE id=?", (o,))
    return {"id": o, "n": ad(x) if x else "(o'chirilgan foydalanuvchi)"}


@app.route("/xabarlar")
@kerak
def xabarlar():
    return render_template("xabarlar.html", nav="msg")


@app.route("/api/xabar/royxat")
@api_kerak
def xabar_royxat():
    u = joriy_user()
    me = me_key(u)
    if u["is_admin"]:
        keys = {r["thread"] for r in qa("SELECT DISTINCT thread FROM messages WHERE thread LIKE 's:%'")}
    else:
        keys = {"s:%d" % u["id"]}
        keys |= {r["thread"] for r in qa("SELECT DISTINCT thread FROM messages WHERE thread LIKE 'u:%'")
                 if thr_ruxsat(u, r["thread"])}
    out = []
    for k in keys:
        last = q1("SELECT sender,text,ts FROM messages WHERE thread=? ORDER BY id DESC LIMIT 1", (k,))
        un = q1("SELECT COUNT(*) c FROM messages WHERE thread=? AND sender!=? AND id>COALESCE("
                "(SELECT last_id FROM reads WHERE thread=? AND reader=?),0)", (k, me, k, me))["c"]
        out.append(dict(k=k, sup=k.startswith("s:"), who=_kim(u, k), un=un,
                        last=dict(me=last["sender"] == me, m=last["text"], t=last["ts"]) if last else None))
    out.sort(key=lambda x: (0 if x["sup"] and not u["is_admin"] else 1, -(x["last"]["t"] if x["last"] else 0)))
    return jsonify(threads=out, adm=bool(u["is_admin"]))


@app.route("/api/xabar/chat")
@api_kerak
def xabar_chat():
    u = joriy_user()
    k = request.args.get("k", "")
    if not thr_ruxsat(u, k):
        return xato("Suhbat topilmadi.", 404)
    me = me_key(u)
    rows = qa("SELECT * FROM (SELECT * FROM messages WHERE thread=? ORDER BY id DESC LIMIT 200) ORDER BY id", (k,))
    if rows:
        ex("INSERT INTO reads(thread,reader,last_id) VALUES(?,?,?) ON CONFLICT(thread,reader) "
           "DO UPDATE SET last_id=excluded.last_id", (k, me, rows[-1]["id"]))
    nm = {}
    out = []
    for r in rows:
        s = r["sender"]
        if s not in nm:
            if s == "@adm":
                nm[s] = "Support"
            else:
                x = q1("SELECT id,username,taxallus FROM users WHERE id=?", (int(s),))
                nm[s] = ad(x) if x else "?"
        out.append(dict(id=r["id"], me=s == me, n=nm[s], m=r["text"], t=r["ts"]))
    return jsonify(msgs=out, who=_kim(u, k))


@app.route("/api/xabar/yubor", methods=["POST"])
@api_kerak
def xabar_yubor():
    u = joriy_user()
    d = request.get_json(silent=True) or {}
    k = d.get("k")
    m = str(d.get("m", "")).strip()[:500]
    if not thr_ruxsat(u, k):
        return xato("Suhbat topilmadi.", 404)
    if not m:
        return xato("Xabar bo'sh.")
    if k.startswith("s:") and not q1("SELECT 1 FROM users WHERE id=? AND is_admin=0", (int(k[2:]),)):
        return xato("Foydalanuvchi topilmadi.", 404)
    if k.startswith("u:") and not all(q1("SELECT 1 FROM users WHERE id=? AND is_admin=0", (int(x),)) for x in k[2:].split("|")):
        return xato("Foydalanuvchi topilmadi.", 404)
    if limit(("xabar", u["id"]), 30, 60):
        return xato("Juda tez yozyapsiz. Biroz kuting.", 429)
    ex("INSERT INTO messages(thread,sender,text,ts) VALUES(?,?,?,?)", (k, me_key(u), m, hozir()))
    return jsonify(ok=True)


@app.route("/api/xabar/yangi", methods=["POST"])
@api_kerak
def xabar_yangi():
    u = joriy_user()
    if u["is_admin"]:
        return xato("Admin faqat support so'rovlariga javob beradi.")
    try:
        o = int((request.get_json(silent=True) or {}).get("u"))
    except (TypeError, ValueError):
        return xato("Noto'g'ri so'rov.")
    if o == u["id"]:
        return xato("O'zingizga yoza olmaysiz.")
    if not q1("SELECT 1 FROM users WHERE id=? AND is_admin=0 AND is_blocked=0", (o,)):
        return xato("Foydalanuvchi topilmadi.", 404)
    a, b = sorted((u["id"], o))
    return jsonify(ok=True, k="u:%d|%d" % (a, b))


@app.route("/api/qidir")
@api_kerak
def qidir():
    u = joriy_user()
    q = request.args.get("q", "").strip().lower()[:20]
    if not q or u["is_admin"]:
        return jsonify(users=[])
    p = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    rows = qa("SELECT id,username,taxallus FROM users WHERE is_admin=0 AND is_blocked=0 AND id!=? AND "
              "(lower(username) LIKE ? ESCAPE '\\' OR lower(taxallus) LIKE ? ESCAPE '\\') LIMIT 6", (u["id"], p, p))
    return jsonify(users=[{"id": r["id"], "n": ad(r), "un": r["username"]} for r in rows])


@app.route("/api/belgi")
@api_kerak
def belgi():
    u = joriy_user()
    pend = q1("SELECT COUNT(*) c FROM payments WHERE status='pending'")["c"] if u["is_admin"] else 0
    return jsonify(un=unread_count(u), pend=pend)


# ---------------- Admin buyruqlari (admin.py chaqiradi) ----------------
def buyruq(cmd, i, side, score):
    M, tm = matches()
    if cmd == "clear":
        ex("UPDATE matches SET status='k', sa=NULL, sb=NULL, winner=NULL")
        jurnal("Barcha natijalarni tozalash", "Turnir boshidan boshlandi")
        return True, "Barcha natijalar tozalandi."
    if i not in range(7):
        return False, "Noto'g'ri o'yin."
    m = M[i]
    A, B = m["a"], m["b"]
    if cmd == "start":
        if A is None or B is None:
            return False, "Ikkala jamoa aniqlanishi kerak."
        if m["s"] != "k":
            return False, "O'yin allaqachon boshlangan."
        ex("UPDATE matches SET status='j', sa=NULL, sb=NULL, winner=NULL WHERE idx=?", (i,))
        for s in (A, B):
            sys_chat(s, "O'yin boshlandi.")
        n = "%s va %s o'yini boshlandi" % (tm[A]["name"], tm[B]["name"])
        jurnal("%s: o'yinni boshlash" % lab(i), n)
        return True, n + "."
    if cmd in ("win", "reset") and i in PAR and M[PAR[i]]["s"] != "k":
        return False, "Keyingi o'yin boshlangan. Avval uni bekor qiling."
    if cmd == "win":
        if A is None or B is None:
            return False, "Ikkala jamoa aniqlanishi kerak."
        if score not in ("2:0", "2:1") or side not in (0, 1):
            return False, "Hisob yoki g'olib noto'g'ri."
        w = B if side else A
        hi, lo = (int(x) for x in score.split(":"))
        sa, sb = (lo, hi) if side else (hi, lo)
        ex("UPDATE matches SET status='t', sa=?, sb=?, winner=? WHERE idx=?", (sa, sb, w, i))
        wn = tm[w]["name"]
        for s in (A, B):
            sys_chat(s, "O'yin tugadi: %s g'olib (%d:%d)." % (wn, hi, lo))
        if i in PAR:
            sys_chat(w, "Tabriklaymiz! Siz %s bosqichiga o'tdingiz." % lab(PAR[i]))
            nx = "%s -> %s bosqichiga o'tdi" % (wn, lab(PAR[i]))
        else:
            sys_chat(w, "Tabriklaymiz! Siz chempionsiz!")
            nx = "%s CHEMPION bo'ldi" % wn
        jurnal("%s: %s g'olib (%d:%d)" % (lab(i), wn, hi, lo), nx)
        return True, nx + "."
    if cmd == "reset":
        if m["s"] == "k":
            return False, "Bu o'yinda natija yo'q."
        ex("UPDATE matches SET status='k', sa=NULL, sb=NULL, winner=NULL WHERE idx=?", (i,))
        jurnal("%s: natijani bekor qilish" % lab(i), "O'yin dastlabki holatga qaytdi")
        return True, "Natija bekor qilindi."
    return False, "Noma'lum buyruq."


def tolov_amal(pid, act, why=""):
    expire()
    p = q1("SELECT * FROM payments WHERE id=?", (pid,))
    if not p:
        return False, "To'lov topilmadi."
    x = q1("SELECT id,username,taxallus FROM users WHERE id=?", (p["user_id"],))
    t = q1("SELECT name FROM teams WHERE seed=?", (p["team_seed"],))
    nm, tn, ps = (ad(x) if x else "?"), (t["name"] if t else "?"), PN[p["pos"]]
    info = "%s · %s · %s · %s so'm" % (nm, tn, ps, f"{p['amount']:,}".replace(",", " "))
    if act == "ok" and p["status"] == "pending":
        ex("UPDATE payments SET status='paid', decided_at=? WHERE id=?", (hozir(), pid))
        sys_chat(p["team_seed"], "%s %s joyini band qildi." % (nm, ps))
        support_xabar(p["user_id"], "To'lovingiz tasdiqlandi: %s jamoasida %s joyi sizniki." % (tn, ps))
        jurnal("To'lovni tasdiqlash: " + info, "%s joyi band qilindi" % nm)
        return True, "To'lov tasdiqlandi."
    if act == "no" and p["status"] == "pending":
        why = why.strip()[:150]
        ex("UPDATE payments SET status='rejected', why=?, decided_at=? WHERE id=?", (why, hozir(), pid))
        support_xabar(p["user_id"], "To'lovingiz tasdiqlanmadi.%s Savol bo'lsa shu yerda yozing." % (" Sabab: %s." % why if why else ""))
        jurnal("To'lovni rad etish: " + info, "Joy bo'shatildi")
        return True, "To'lov rad etildi."
    if act == "rel" and p["status"] == "paid":
        ex("UPDATE payments SET status='released', decided_at=? WHERE id=?", (hozir(), pid))
        sys_chat(p["team_seed"], "%s %s joyidan chiqdi." % (nm, ps))
        support_xabar(p["user_id"], "%s jamoasidagi %s joyingiz bo'shatildi." % (tn, ps))
        jurnal("Joyni bo'shatish: " + info, "Joy bo'sh")
        return True, "Joy bo'shatildi."
    return False, "Bu amalni hozir bajarib bo'lmaydi."
