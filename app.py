"""Dota 2 Nashri: ishga tushirish va terminal buyruqlari.

  python app.py                          saytni ishga tushirish
  python app.py admin-yaratish           admin hisobini yaratish
  python app.py admin-parol-tiklash      admin parolini yangilash
  python app.py zahira                   hozir zahira nusxa olish
  python app.py tiklash <fayl.db>        zahiradan tiklash (sayt to'xtatilgan bo'lsin)
  python app.py eski-bazani-qoshish [fayl.db yoki .json]
                                         eski saytdagi foydalanuvchilarni (login/parol bilan) qo'shish
  python app.py eksport <fayl.json>      foydalanuvchilarni JSON ga chiqarish
"""
import os, sys, getpass, sqlite3
from werkzeug.security import generate_password_hash
import core
from core import app, init_db, DB, DATA
import auth, turnir, admin  # noqa: F401  (marshrutlarni ro'yxatdan o'tkazadi)
import zahira

BUYRUQLAR = ("admin-yaratish", "admin-parol-tiklash", "zahira", "tiklash", "eski-bazani-qoshish", "eksport")
SERVER = not (len(sys.argv) > 1 and sys.argv[1] in BUYRUQLAR)

holat = zahira.tekshir()          # baza buzilgan bo'lsa, zahiradan o'zi tiklanadi
if holat.startswith("tiklandi"):
    print("DIQQAT: baza buzilgan edi, zahiradan tiklandi:", holat.split(":", 1)[1])
elif holat == "zahira topilmadi":
    sys.exit("XATO: baza buzilgan va zahira topilmadi. Kerak bo'lsa: python app.py eski-bazani-qoshish <fayl>")
init_db()
if SERVER and os.environ.get("DOTA_NO_BG") != "1":
    zahira.boshlash()


def parol_so_ra():
    p = getpass.getpass("Yangi parol (kamida 8 ta belgi): ")
    if len(p) < 8 or p != getpass.getpass("Parolni takrorlang: "):
        sys.exit("Xato: parol qisqa yoki ikkalasi mos emas.")
    return p


def admin_yaratish():
    c = sqlite3.connect(DB)
    if c.execute("SELECT 1 FROM users WHERE is_admin=1").fetchone():
        sys.exit("Admin allaqachon mavjud. Parolni yangilash uchun: python app.py admin-parol-tiklash")
    n = input("Admin foydalanuvchi nomi: ").strip()
    m = input("Admin elektron pochtasi: ").strip()
    if len(n) < 3 or "@" not in m:
        sys.exit("Xato: nom kamida 3 ta belgi, pochta to'g'ri bo'lishi kerak.")
    p = parol_so_ra()
    try:
        c.execute("INSERT INTO users(username,email,password_hash,is_admin) VALUES(?,?,?,1)",
                  (n, m, generate_password_hash(p)))
        c.commit()
    except sqlite3.IntegrityError:
        sys.exit("Xato: bunday foydalanuvchi nomi mavjud.")
    zahira.zahira_qil()
    print("Admin yaratildi! Endi saytda shu login va parol bilan kiring.")


def admin_parol_tiklash():
    c = sqlite3.connect(DB)
    a = c.execute("SELECT id,username FROM users WHERE is_admin=1").fetchall()
    if not a:
        sys.exit("Admin topilmadi. Avval: python app.py admin-yaratish")
    uid, nom = a[0]
    print("Admin:", nom)
    c.execute("UPDATE users SET password_hash=?, is_blocked=0 WHERE id=?", (generate_password_hash(parol_so_ra()), uid))
    c.commit()
    zahira.zahira_qil()
    print("Parol yangilandi.")


def eski_topish():
    h = os.path.expanduser("~")
    nomzod = [os.path.join(h, d, "dota2sayt", "sayt.db") for d in ("Загрузки", "Downloads", "")] + [os.path.join(os.getcwd(), "sayt.db")]
    return [p for p in dict.fromkeys(nomzod) if os.path.exists(p) and os.path.abspath(p) != os.path.abspath(DB)]


if __name__ == "__main__":
    kom = sys.argv[1] if len(sys.argv) > 1 else ""
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    if kom == "admin-yaratish":
        admin_yaratish()
    elif kom == "admin-parol-tiklash":
        admin_parol_tiklash()
    elif kom == "zahira":
        print("Zahira olindi:", zahira.zahira_qil())
    elif kom == "tiklash":
        if not arg:
            sys.exit("Foydalanish: python app.py tiklash <zahira fayli.db>")
        try:
            zahira.tikla(arg)
        except ValueError as e:
            sys.exit("Xato: %s" % e)
        print("Baza tiklandi. Endi saytni ishga tushiring.")
    elif kom == "eski-bazani-qoshish":
        yo = arg or None
        if not yo:
            f = eski_topish()
            if not f:
                sys.exit("Eski baza topilmadi. Yo'lini yozing: python app.py eski-bazani-qoshish /yo'l/sayt.db")
            yo = f[0]
            print("Topildi:", yo)
        if not os.path.exists(yo):
            sys.exit("Fayl topilmadi: %s" % yo)
        h = zahira.eski_qoshish(yo)
        zahira.zahira_qil()
        print("Natija:", h["qoshildi"], "ta foydalanuvchi qo'shildi,", h["bor edi"], "tasi allaqachon bor edi.")
        if h["admin oddiyga"]:
            print("Eslatma: eski adminlar oddiy foydalanuvchi sifatida qo'shildi (yangi bazada admin bor).")
    elif kom == "eksport":
        zahira.eksport_json(arg or "foydalanuvchilar.json")
        print("Yozildi:", arg or "foydalanuvchilar.json", "(parollar shifrlangan holda; faylni himoyalang)")
    else:
        print("Ma'lumotlar papkasi:", DATA)
        app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")), debug=False)
