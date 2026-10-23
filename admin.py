"""Admin panel: turnir buyruqlari, to'lovlar, sozlamalar va foydalanuvchilar."""
import zahira
from flask import send_file
from core import *
import os
from turnir import matches, lab, PN, narx, expire, jurnal, buyruq, tolov_amal, ad

HOLAT_O = {"k": "Kutilmoqda", "j": "Jonli", "t": "Tugagan"}


def _int(v, d=-1):
    try:
        return int(v)
    except (TypeError, ValueError):
        return d


@app.route("/admin")
@admin_kerak
def admin():
    expire()
    M, tm = matches()
    jm = lambda s: {"n": tm[s]["name"], "c": tm[s]["color"]} if s is not None and s in tm else None
    rows = [dict(i=i, lab=lab(i), s=m["s"], sa=m["sa"], sb=m["sb"], a=jm(m["a"]), b=jm(m["b"]), w=jm(m["w"]))
            for i, m in enumerate(M)]
    J = """SELECT p.*, u.username, u.taxallus, t.name AS jamoa FROM payments p
           LEFT JOIN users u ON u.id=p.user_id LEFT JOIN teams t ON t.seed=p.team_seed
           WHERE p.status=? ORDER BY COALESCE(p.submitted_at,p.created_at) DESC LIMIT 100"""
    pending, paid = qa(J, ("pending",)), qa(J, ("paid",))
    stats = dict(
        users=q1("SELECT COUNT(*) c FROM users WHERE is_admin=0")["c"],
        teams=q1("SELECT COUNT(*) c FROM teams")["c"],
        played=sum(1 for m in M if m["s"] == "t"),
        pending=len(pending),
        revenue=q1("SELECT COALESCE(SUM(amount),0) c FROM payments WHERE status='paid'")["c"])
    return render_template("admin.html", nav="adm", rows=rows, pending=pending, paid=paid, stats=stats,
                           cfg=dict(price=narx(), card=q1("SELECT v FROM settings WHERE k='karta'")["v"],
                                    note=q1("SELECT v FROM settings WHERE k='izoh'")["v"]),
                           log=qa("SELECT * FROM cmdlog ORDER BY id DESC LIMIT 40"),
                           users=qa("SELECT * FROM users ORDER BY id DESC"),
                           zahiralar=zahira.royxat()[:10], data_dir=DATA,
                           ikkinchi=bool(os.environ.get("DOTA_ZAHIRA2")),
                           PN=PN, HOLAT_O=HOLAT_O, ad=ad)


def _qayt(msg, ok, ankor=""):
    flash(msg, "ok" if ok else "xato")
    return redirect(url_for("admin") + ankor)


@app.route("/admin/match", methods=["POST"])
@admin_kerak
def admin_match():
    f = request.form
    ok, msg = buyruq(f.get("cmd", ""), _int(f.get("i")), _int(f.get("side")), f.get("score", ""))
    return _qayt(msg, ok, "#turnir")


@app.route("/admin/tolov", methods=["POST"])
@admin_kerak
def admin_tolov():
    f = request.form
    ok, msg = tolov_amal(_int(f.get("id")), f.get("act", ""), f.get("why", ""))
    return _qayt(msg, ok, "#tolov")


@app.route("/admin/sozlama", methods=["POST"])
@admin_kerak
def admin_sozlama():
    f = request.form
    pr = _int(f.get("price"))
    if not 1000 <= pr <= 10_000_000:
        return _qayt("Narx 1 000 dan 10 000 000 so'mgacha bo'lsin.", False, "#tolov")
    for k, v in (("narx", str(pr)), ("karta", f.get("card", "").strip()[:120]), ("izoh", f.get("note", "").strip()[:200])):
        ex("UPDATE settings SET v=? WHERE k=?", (v, k))
    jurnal("To'lov sozlamalari yangilandi", "Narx: %d so'm" % pr)
    return _qayt("Sozlamalar saqlandi.", True, "#tolov")


@app.route("/admin/blok/<int:uid>", methods=["POST"])
@admin_kerak
def blok(uid):
    x = q1("SELECT * FROM users WHERE id=?", (uid,))
    if not x or x["is_admin"]:
        return _qayt("Bu foydalanuvchi ustida amal bajarib bo'lmaydi.", False, "#users")
    ex("UPDATE users SET is_blocked = 1 - is_blocked WHERE id=?", (uid,))
    return _qayt("Foydalanuvchi holati o'zgartirildi.", True, "#users")


@app.route("/admin/ochirish/<int:uid>", methods=["POST"])
@admin_kerak
def ochirish(uid):
    x = q1("SELECT * FROM users WHERE id=?", (uid,))
    if not x or x["is_admin"]:
        return _qayt("Bu foydalanuvchini o'chirib bo'lmaydi.", False, "#users")
    if (q1("SELECT 1 FROM teams WHERE owner_id=?", (uid,))
            or q1("SELECT 1 FROM payments WHERE user_id=? AND status IN ('hold','pending','paid')", (uid,))):
        return _qayt("Foydalanuvchining jamoasi yoki band qilingan joyi bor. Avval ularni tartibga soling.", False, "#users")
    from auth import eski_rasm_ochir
    eski_rasm_ochir(x["avatar"])
    ex("DELETE FROM users WHERE id=?", (uid,))
    return _qayt("Foydalanuvchi o'chirildi.", True, "#users")


@app.route("/admin/zahira/qil", methods=["POST"])
@admin_kerak
def zahira_qil_r():
    try:
        zahira.zahira_qil()
    except Exception as e:
        return _qayt("Zahira olinmadi: %s" % e, False, "#zahira")
    return _qayt("Zahira nusxa olindi.", True, "#zahira")


@app.route("/admin/zahira/yuklab")
@admin_kerak
def zahira_yuklab():
    nom = "dota2-zahira-%s.zip" % datetime.now().strftime("%Y%m%d-%H%M")
    return send_file(zahira.toliq_zip(), as_attachment=True, download_name=nom, mimetype="application/zip")
