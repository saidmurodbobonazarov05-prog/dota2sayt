"""Umumiy qism: Flask ilovasi, ma'lumotlar bazasi va yordamchi funksiyalar."""
import os, time, sqlite3, secrets
from datetime import datetime
from functools import wraps
from flask import (Flask, g, render_template, request, redirect, url_for,
                   session, flash, abort, jsonify)

BASE = os.path.dirname(os.path.abspath(__file__))
# MA'LUMOTLAR KODDAN ALOHIDA PAPKADA turadi: saytni yangilash yoki papkani o'chirish ularga tegmaydi.
DATA = os.environ.get("DOTA_DATA") or os.path.join(os.path.expanduser("~"), "dota2_malumot")
DB = os.environ.get("DOTA_DB") or os.path.join(DATA, "sayt.db")
KEY_FILE = os.path.join(DATA, ".secret_key")
UPLOAD_DIR = os.path.join(DATA, "rasmlar")
ZAHIRA_DIR = os.path.join(DATA, "zahira")
os.makedirs(DATA, mode=0o700, exist_ok=True)
MAX_RASM = 2 * 1024 * 1024

DARAJALAR = ["Herald", "Guardian", "Crusader", "Archon", "Legend", "Ancient", "Divine", "Immortal"]
POZITSIYALAR = ["1-pozitsiya: Mider", "2-pozitsiya: Kerri", "3-pozitsiya: Tank (Slojniy)",
                "4-pozitsiya: Paderjka", "5-pozitsiya: To'liq paderjka"]
RANGLAR = ["#4fc3f7", "#ff7043", "#ffd54f", "#ab47bc", "#ef5350", "#26c6da", "#9ccc65", "#f06292"]



def _eski_kochir():
    """Eski tuzilma (baza kod papkasining ichida) bo'lsa, ma'lumotlarni yangi joyga ko'chiradi (nusxa)."""
    import shutil
    eski = os.path.join(BASE, "sayt.db")
    if not os.environ.get("DOTA_DB") and not os.path.exists(DB) and os.path.exists(eski):
        s_, d_ = sqlite3.connect(eski), sqlite3.connect(DB)
        s_.backup(d_)
        d_.close()
        s_.close()
        er = os.path.join(BASE, "static", "uploads", "avatars")
        os.makedirs(UPLOAD_DIR, mode=0o700, exist_ok=True)
        if os.path.isdir(er):
            for f in os.listdir(er):
                if not f.startswith("."):
                    shutil.copy2(os.path.join(er, f), os.path.join(UPLOAD_DIR, f))
        print("Eski ma'lumotlar ko'chirildi:", DB)
    ek = os.path.join(BASE, ".secret_key")
    if not os.path.exists(KEY_FILE) and os.path.exists(ek):
        shutil.copy2(ek, KEY_FILE)


_eski_kochir()
app = Flask(__name__)
app.json.ensure_ascii = False
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "w") as f:
        f.write(secrets.token_hex(32))
    os.chmod(KEY_FILE, 0o600)
app.secret_key = open(KEY_FILE).read().strip()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  MAX_CONTENT_LENGTH=3 * 1024 * 1024)
os.makedirs(UPLOAD_DIR, exist_ok=True)
if os.environ.get("HTTPS") == "1":  # HTTPS orqasida ishlaganda
    app.config["SESSION_COOKIE_SECURE"] = True

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL COLLATE NOCASE,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0,
  is_blocked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  daraja TEXT NOT NULL DEFAULT '', pozitsiya TEXT NOT NULL DEFAULT '',
  qahramon TEXT NOT NULL DEFAULT '', taxallus TEXT NOT NULL DEFAULT '',
  haqida TEXT NOT NULL DEFAULT '', avatar TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS teams(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seed INTEGER UNIQUE NOT NULL,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  color TEXT NOT NULL,
  owner_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
  created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS matches(
  idx INTEGER PRIMARY KEY, status TEXT NOT NULL DEFAULT 'k',
  sa INTEGER, sb INTEGER, winner INTEGER);
CREATE TABLE IF NOT EXISTS payments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL, team_seed INTEGER NOT NULL, pos INTEGER NOT NULL,
  amount INTEGER NOT NULL, status TEXT NOT NULL, ref TEXT, why TEXT,
  created_at INTEGER NOT NULL, submitted_at INTEGER, decided_at INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS uq_slot ON payments(team_seed, pos)
  WHERE status IN ('hold','pending','paid');
CREATE UNIQUE INDEX IF NOT EXISTS uq_user ON payments(user_id)
  WHERE status IN ('hold','pending','paid');
CREATE TABLE IF NOT EXISTS team_chat(
  id INTEGER PRIMARY KEY AUTOINCREMENT, team_seed INTEGER NOT NULL,
  user_id INTEGER, name TEXT, label TEXT, text TEXT NOT NULL,
  ts INTEGER NOT NULL, sys INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, thread TEXT NOT NULL,
  sender TEXT NOT NULL, text TEXT NOT NULL, ts INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ix_msg ON messages(thread, id);
CREATE TABLE IF NOT EXISTS reads(
  thread TEXT NOT NULL, reader TEXT NOT NULL, last_id INTEGER NOT NULL,
  PRIMARY KEY(thread, reader));
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS cmdlog(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL,
  cmd TEXT NOT NULL, res TEXT NOT NULL);
"""
ESKI_POZITSIYALAR = {"1-pozitsiya: Carry": POZITSIYALAR[1], "2-pozitsiya: Mid": POZITSIYALAR[0],
                     "3-pozitsiya: Offlane": POZITSIYALAR[2], "4-pozitsiya: Soft support": POZITSIYALAR[3],
                     "5-pozitsiya: Hard support": POZITSIYALAR[4]}


def pragmalar(c):
    """O'chish/yonish/qulash holatida ham ma'lumot buzilmasligi uchun (WAL + to'liq sinxron yozuv)."""
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=FULL")
    c.execute("PRAGMA foreign_keys=ON")


def init_db():
    c = sqlite3.connect(DB, timeout=10)
    pragmalar(c)
    c.executescript(SCHEMA)
    cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for n in ("daraja", "pozitsiya", "qahramon", "taxallus", "haqida", "avatar"):
        if n not in cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {n} TEXT NOT NULL DEFAULT ''")
    for e, y in ESKI_POZITSIYALAR.items():
        c.execute("UPDATE users SET pozitsiya=? WHERE pozitsiya=?", (y, e))
    c.executemany("INSERT OR IGNORE INTO matches(idx) VALUES(?)", [(i,) for i in range(7)])
    c.executemany("INSERT OR IGNORE INTO settings(k,v) VALUES(?,?)",
                  [("narx", "15000"), ("karta", ""), ("izoh", "")])
    c.commit()
    c.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA synchronous=FULL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def _yop(_):
    d = g.pop("db", None)
    if d:
        d.close()


def qa(sql, a=()):
    return get_db().execute(sql, a).fetchall()


def q1(sql, a=()):
    return get_db().execute(sql, a).fetchone()


def ex(sql, a=()):
    d = get_db()
    c = d.execute(sql, a)
    d.commit()
    return c


def hozir():
    return int(time.time())


_LIM = {}


def limit(kalit, n, soniya):
    """True qaytarsa: urinishlar soni chegaradan oshgan."""
    h = time.time()
    L = [t for t in _LIM.get(kalit, []) if h - t < soniya]
    if len(L) >= n:
        _LIM[kalit] = L
        return True
    L.append(h)
    _LIM[kalit] = L
    return False


def joriy_user():
    if "u" in g:
        return g.u
    u = None
    uid = session.get("uid")
    if uid:
        u = q1("SELECT * FROM users WHERE id=?", (uid,))
        if not u or u["is_blocked"]:
            session.pop("uid", None)
            u = None
    g.u = u
    return u


def kerak(f):
    @wraps(f)
    def w(*a, **k):
        if not joriy_user():
            return redirect(url_for("bosh"))
        return f(*a, **k)
    return w


def api_kerak(f):
    @wraps(f)
    def w(*a, **k):
        if not joriy_user():
            return jsonify(xato="Avval tizimga kiring."), 401
        return f(*a, **k)
    return w


def admin_kerak(f):
    @wraps(f)
    def w(*a, **k):
        u = joriy_user()
        if not u or not u["is_admin"]:
            abort(404)
        return f(*a, **k)
    return w


def xato(m, kod=400):
    return jsonify(xato=m), kod


@app.before_request
def csrf_tekshirish():
    if request.method == "POST":
        t = request.form.get("csrf") or request.headers.get("X-CSRF")
        if not t or not secrets.compare_digest(t, session.get("csrf", "")):
            if request.path.startswith("/api/"):
                return xato("Sessiya eskirgan. Sahifani yangilang.")
            abort(400)


@app.context_processor
def umumiy():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {"csrf": session["csrf"], "user": joriy_user()}


@app.after_request
def himoya(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "same-origin"
    r.headers["Content-Security-Policy"] = ("default-src 'self'; img-src 'self' data:; "
                                            "style-src 'self' 'unsafe-inline'; script-src 'self'; "
                                            "frame-ancestors 'none'; form-action 'self'")
    if request.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


@app.template_filter("vaqt")
def vaqt(ts):
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M") if ts else ""


@app.template_filter("pul")
def pul(n):
    return f"{int(n):,}".replace(",", " ")


def _xato_sahifa(kod, matn):
    if request.path.startswith("/api/"):
        return jsonify(xato=matn), kod
    return render_template("xato.html", kod=kod, matn=matn), kod


@app.errorhandler(404)
def _404(_):
    return _xato_sahifa(404, "Sahifa topilmadi.")


@app.errorhandler(400)
def _400(_):
    return _xato_sahifa(400, "Noto'g'ri so'rov. Sahifani yangilab qayta urinib ko'ring.")


@app.errorhandler(413)
def _413(_):
    if request.path.startswith("/api/"):
        return jsonify(xato="Fayl juda katta."), 413
    flash("Fayl hajmi juda katta. Rasm 2 MB dan oshmasligi kerak.", "xato")
    return redirect(url_for("tahrirlash"))
