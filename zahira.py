"""Zahira nusxalar, tiklash va eski bazani qo'shish. Maqsad: login va parollar hech qachon yo'qolmasin."""
import os, io, json, time, shutil, sqlite3, tempfile, zipfile, threading
from datetime import datetime
from core import DB, DATA, UPLOAD_DIR, ZAHIRA_DIR

USER_COLS = ["username", "email", "password_hash", "is_admin", "is_blocked", "created_at",
             "daraja", "pozitsiya", "qahramon", "taxallus", "haqida", "avatar"]
_oxirgi = 0.0
_kilit = threading.Lock()


def _yol(nom):
    return os.path.join(ZAHIRA_DIR, nom)


def eksport_json(yol):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("SELECT %s FROM users ORDER BY id" % ",".join(USER_COLS))]
    c.close()
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    os.chmod(yol, 0o600)


def zahira_qil():
    """Bazaning izchil nusxasini oladi (sayt ishlab turganda ham xavfsiz)."""
    global _oxirgi
    with _kilit:
        os.makedirs(ZAHIRA_DIR, mode=0o700, exist_ok=True)
        nom = "sayt-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db"
        yo = _yol(nom)
        i = 2
        while os.path.exists(yo):
            yo = _yol(nom[:-3] + "-%d.db" % i)
            i += 1
        s_, d_ = sqlite3.connect(DB, timeout=10), sqlite3.connect(yo)
        s_.backup(d_)
        d_.close()
        s_.close()
        os.chmod(yo, 0o600)
        eksport_json(_yol("foydalanuvchilar.json"))
        ikk = os.environ.get("DOTA_ZAHIRA2")  # ikkinchi joy: boshqa disk, fleshka, bulut papkasi
        if ikk:
            try:
                os.makedirs(ikk, exist_ok=True)
                shutil.copy2(yo, ikk)
                shutil.copy2(_yol("foydalanuvchilar.json"), ikk)
            except OSError as e:
                print("Ikkinchi zahira joyiga yozib bo'lmadi:", e)
        _tozala()
        _oxirgi = time.time()
        return yo


def tez():
    """Yangi hisob ochilganda: oxirgi zahiradan 5 soniya o'tgan bo'lsa, darhol nusxa oladi.
    Aks holda fon jarayoni 15 soniya ichida oladi."""
    if time.time() - _oxirgi >= 5:
        try:
            zahira_qil()
        except Exception as e:  # zahira xatosi saytni to'xtatmasligi kerak
            print("Zahira xatosi:", e)


def royxat():
    if not os.path.isdir(ZAHIRA_DIR):
        return []
    out = []
    for f in os.listdir(ZAHIRA_DIR):
        if f.endswith(".db"):
            st = os.stat(_yol(f))
            out.append({"nom": f, "hajm": st.st_size, "vaqt": int(st.st_mtime), "_k": (st.st_mtime_ns, f)})
    out.sort(key=lambda x: x.pop("_k"), reverse=True)  # eng yangisi birinchi (vaqt bo'yicha)
    return out


def _tozala():
    """Oxirgi 48 ta nusxa + oxirgi 30 kunning har kunidan bittasi saqlanadi."""
    L = [x["nom"] for x in royxat() if x["nom"].startswith("sayt-")]
    keep, kunlar = set(L[:48]), set()
    for f in L[48:]:
        kun = f[5:13]
        if kun not in kunlar and len(kunlar) < 30:
            kunlar.add(kun)
            keep.add(f)
    for f in L:
        if f not in keep:
            os.remove(_yol(f))


def toliq_zip():
    """Admin yuklab olishi uchun: baza + profil rasmlari + foydalanuvchilar JSON."""
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "sayt.db")
        s_, d_ = sqlite3.connect(DB, timeout=10), sqlite3.connect(p)
        s_.backup(d_)
        d_.close()
        s_.close()
        eksport_json(os.path.join(t, "foydalanuvchilar.json"))
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(p, "sayt.db")
            z.write(os.path.join(t, "foydalanuvchilar.json"), "foydalanuvchilar.json")
            if os.path.isdir(UPLOAD_DIR):
                for f in os.listdir(UPLOAD_DIR):
                    if not f.startswith("."):
                        z.write(os.path.join(UPLOAD_DIR, f), "rasmlar/" + f)
    buf.seek(0)
    return buf


def _butun(yol):
    try:
        c = sqlite3.connect(yol)
        r = c.execute("PRAGMA integrity_check").fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users")
        c.close()
        return r == "ok"
    except sqlite3.DatabaseError:
        return False


def tekshir():
    """Ishga tushganda bazani tekshiradi. Buzilgan bo'lsa, eng yangi butun zahiradan o'zi tiklaydi."""
    if not os.path.exists(DB):
        return "yangi"
    if _butun(DB):
        return "ok"
    t = datetime.now().strftime("%Y%m%d-%H%M%S")
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(DB + ext):
            os.replace(DB + ext, DB + ".buzilgan-" + t + ext)
    for z in royxat():
        if _butun(_yol(z["nom"])):
            shutil.copy2(_yol(z["nom"]), DB)
            return "tiklandi:" + z["nom"]
    return "zahira topilmadi"


def tikla(fayl):
    """Qo'lda tiklash (sayt to'xtatilgan bo'lishi kerak). Joriy bazaning nusxasi avval saqlanadi."""
    if not os.path.exists(fayl) or not _butun(fayl):
        raise ValueError("Fayl topilmadi yoki buzilgan.")
    if os.path.exists(DB):
        os.makedirs(ZAHIRA_DIR, mode=0o700, exist_ok=True)
        shutil.copy2(DB, _yol("tiklashdan-oldin-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".bak"))
    for ext in ("-wal", "-shm"):
        if os.path.exists(DB + ext):
            os.remove(DB + ext)
    shutil.copy2(fayl, DB)


def eski_qoshish(yol):
    """Eski baza (.db) yoki JSON dan foydalanuvchilarni qo'shadi. Mavjudlari o'zgarmaydi. Parollar saqlanadi."""
    if yol.endswith(".json"):
        with open(yol, encoding="utf-8") as f:
            rows = json.load(f)
    else:
        c = sqlite3.connect("file:%s?mode=ro" % yol, uri=True)
        c.row_factory = sqlite3.Row
        have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        sel = [k for k in USER_COLS if k in have]
        rows = [dict(r) for r in c.execute("SELECT %s FROM users ORDER BY id" % ",".join(sel))]
        c.close()
    d = sqlite3.connect(DB, timeout=10)
    d.execute("PRAGMA foreign_keys=ON")
    has_admin = d.execute("SELECT 1 FROM users WHERE is_admin=1").fetchone() is not None
    hisob = {"qoshildi": 0, "bor edi": 0, "admin oddiyga": 0}
    eskirasm = os.path.join(os.path.dirname(os.path.abspath(yol)), "static", "uploads", "avatars")
    for r in rows:
        if not r.get("username") or not r.get("password_hash"):
            continue
        if d.execute("SELECT 1 FROM users WHERE username=?", (r["username"],)).fetchone():
            hisob["bor edi"] += 1
            continue
        adm = int(bool(r.get("is_admin")))
        if adm and has_admin:
            adm = 0
            hisob["admin oddiyga"] += 1
        elif adm:
            has_admin = True
        vals = {k: r.get(k, "") for k in USER_COLS}
        vals.update(is_admin=adm, is_blocked=int(bool(r.get("is_blocked"))), email=r.get("email") or "-")
        if not vals["created_at"]:
            vals["created_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        d.execute("INSERT INTO users(%s) VALUES(%s)" % (",".join(USER_COLS), ",".join("?" * len(USER_COLS))),
                  [vals[k] if vals[k] is not None else "" for k in USER_COLS])
        if vals["avatar"] and os.path.exists(os.path.join(eskirasm, vals["avatar"])):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            shutil.copy2(os.path.join(eskirasm, vals["avatar"]), os.path.join(UPLOAD_DIR, vals["avatar"]))
        hisob["qoshildi"] += 1
    d.commit()
    d.close()
    return hisob


def _mtime():
    m = 0
    for ext in ("", "-wal"):
        try:
            m = max(m, os.stat(DB + ext).st_mtime)
        except OSError:
            pass
    return m


def boshlash():
    """Ishga tushganda zahira oladi va fon rejimida har 15 soniyada o'zgarishni tekshirib turadi."""
    try:
        zahira_qil()
    except Exception as e:
        print("Zahira xatosi:", e)

    def ish():
        oxirgi = _mtime()
        while True:
            time.sleep(15)
            try:
                m = _mtime()
                if m != oxirgi and time.time() - _oxirgi >= 5:
                    zahira_qil()
                    oxirgi = _mtime()
            except Exception as e:
                print("Zahira xatosi:", e)
    threading.Thread(target=ish, daemon=True).start()
