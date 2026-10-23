"""Ro'yxatdan o'tish, kirish, profil va profil rasmi."""
import os, re, sqlite3, secrets, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory
from core import *
import zahira

FAIL = {}
HOLAT = {"hold": "To'lov kutilmoqda", "pending": "Tekshirilmoqda", "paid": "Tasdiqlandi",
         "rejected": "Rad etildi", "expired": "Muddati tugadi", "cancelled": "Bekor qilindi",
         "released": "Bo'shatildi"}
LAVOZIM = ["Mider", "Kerri", "Tank (Slojniy)", "Paderjka", "To'liq paderjka"]


def urinishlar(k):
    h = time.time()
    FAIL[k] = [t for t in FAIL.get(k, []) if h - t < 600]
    return FAIL[k]


@app.route("/")
def bosh():
    u = joriy_user()
    if u:
        return redirect(url_for("admin" if u["is_admin"] else "profil"))
    return render_template("index.html")


@app.route("/royxat", methods=["POST"])
def royxat():
    n = request.form.get("username", "").strip()
    m = request.form.get("email", "").strip()
    p = request.form.get("password", "")
    p2 = request.form.get("password2", "")
    xt = None
    if not n or not m or not p:
        xt = "Barcha maydonlarni to'ldiring."
    elif not re.fullmatch(r"[A-Za-z0-9_]{3,20}", n):
        xt = "Foydalanuvchi nomi 3-20 ta harf, raqam yoki _ belgisidan iborat bo'lishi kerak."
    elif n.lower().startswith("admin"):
        xt = "Bu foydalanuvchi nomi band."
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", m) or len(m) > 120:
        xt = "Elektron pochta noto'g'ri kiritilgan."
    elif len(p) < 6 or len(p) > 100:
        xt = "Parol kamida 6 ta belgidan iborat bo'lishi kerak."
    elif p != p2:
        xt = "Parollar bir xil emas."
    elif limit(("royxat", request.remote_addr), 10, 3600):
        xt = "Juda ko'p urinish. Keyinroq qayta urinib ko'ring."
    if xt:
        flash(xt, "xato")
        return redirect(url_for("bosh", r=1))
    try:
        ex("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
           (n, m, generate_password_hash(p)))
    except sqlite3.IntegrityError:
        flash("Bu foydalanuvchi nomi band.", "xato")
        return redirect(url_for("bosh", r=1))
    zahira.tez()  # yangi login/parol darhol zahiraga tushadi
    flash("Ro'yxatdan muvaffaqiyatli o'tdingiz! Endi kirishingiz mumkin.", "ok")
    return redirect(url_for("bosh"))


@app.route("/kirish", methods=["POST"])
def kirish():
    n = request.form.get("username", "").strip()
    p = request.form.get("password", "")
    kalit = (request.remote_addr, n.lower())
    if len(urinishlar(kalit)) >= 5:
        flash("Juda ko'p noto'g'ri urinish. 10 daqiqadan keyin qayta urinib ko'ring.", "xato")
        return redirect(url_for("bosh"))
    u = q1("SELECT * FROM users WHERE username=?", (n,))
    if not u or not check_password_hash(u["password_hash"], p):
        FAIL.setdefault(kalit, []).append(time.time())
        flash("Foydalanuvchi nomi yoki parol noto'g'ri.", "xato")
        return redirect(url_for("bosh"))
    FAIL.pop(kalit, None)
    if u["is_blocked"]:
        flash("Sizning hisobingiz bloklangan. Administrator bilan bog'laning.", "xato")
        return redirect(url_for("bosh"))
    csrf = session.get("csrf")
    session.clear()
    session["csrf"] = csrf or secrets.token_hex(16)
    session["uid"] = u["id"]
    return redirect(url_for("bosh"))


@app.route("/chiqish", methods=["POST"])
def chiqish():
    session.clear()
    return redirect(url_for("bosh"))


@app.route("/profil")
@kerak
def profil():
    u = joriy_user()
    if u["is_admin"]:
        return redirect(url_for("admin"))
    t = q1("""SELECT t.* FROM teams t WHERE t.owner_id=? UNION
              SELECT t.* FROM teams t JOIN payments p ON p.team_seed=t.seed
              WHERE p.user_id=? AND p.status='paid'""", (u["id"], u["id"]))
    tolovlar = qa("""SELECT p.*, t.name AS jamoa FROM payments p
                     LEFT JOIN teams t ON t.seed=p.team_seed
                     WHERE p.user_id=? ORDER BY p.created_at DESC LIMIT 30""", (u["id"],))
    return render_template("profil.html", jamoa=t, tolovlar=tolovlar, HOLAT=HOLAT,
                           LAVOZIM=LAVOZIM, nav="home")


def rasm_turi(b):
    if b[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    return None


def eski_rasm_ochir(nom):
    if nom:
        try:
            os.remove(os.path.join(UPLOAD_DIR, os.path.basename(nom)))
        except OSError:
            pass


@app.route("/profil/tahrirlash", methods=["GET", "POST"])
@kerak
def tahrirlash():
    u = joriy_user()
    if request.method == "POST":
        t = " ".join(request.form.get("taxallus", "").split())
        d = request.form.get("daraja", "")
        p = request.form.get("pozitsiya", "")
        h = request.form.get("haqida", "").strip()
        if len(t) > 24 or len(h) > 160 or d not in DARAJALAR + [""] or p not in POZITSIYALAR + [""]:
            abort(400)
        nom = u["avatar"]
        f = request.files.get("avatar")
        if f and f.filename:
            data = f.read(MAX_RASM + 1)
            if len(data) > MAX_RASM:
                flash("Rasm hajmi 2 MB dan oshmasligi kerak.", "xato")
                return redirect(url_for("tahrirlash"))
            ext = rasm_turi(data)
            if not ext:
                flash("Faqat JPG, PNG yoki WEBP rasm yuklash mumkin.", "xato")
                return redirect(url_for("tahrirlash"))
            yangi = f"{u['id']}_{secrets.token_hex(6)}.{ext}"
            with open(os.path.join(UPLOAD_DIR, yangi), "wb") as out:
                out.write(data)
            eski_rasm_ochir(nom)
            nom = yangi
        ex("UPDATE users SET taxallus=?, daraja=?, pozitsiya=?, haqida=?, avatar=? WHERE id=?",
           (t, d, p, h, nom, u["id"]))
        flash("Profil saqlandi.", "ok")
        return redirect(url_for("admin" if u["is_admin"] else "profil"))
    return render_template("tahrirlash.html", darajalar=DARAJALAR,
                           pozitsiyalar=POZITSIYALAR, nav="home")


@app.route("/profil/rasm-ochirish", methods=["POST"])
@kerak
def rasm_ochirish():
    u = joriy_user()
    eski_rasm_ochir(u["avatar"])
    ex("UPDATE users SET avatar='' WHERE id=?", (u["id"],))
    flash("Profil rasmi o'chirildi.", "ok")
    return redirect(url_for("tahrirlash"))


@app.route("/tez-orada")
def tez_orada():
    return render_template("xato.html", kod="Tez orada", matn="Bu bo'lim tez orada qo'shiladi.")


@app.route("/rasm/<nom>")
def rasm(nom):
    if not re.fullmatch(r"\d+_[0-9a-f]{12}\.(jpg|png|webp)", nom):
        abort(404)
    return send_from_directory(UPLOAD_DIR, nom, max_age=3600)
