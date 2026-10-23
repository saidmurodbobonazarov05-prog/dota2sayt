DOTA 2 NASHRI - turnir sayti (Flask + SQLite)
=============================================

Sayt faqat saralash, ro'yxatga olish, to'lovni tasdiqlash va g'olibni aniqlash uchun.
Haqiqiy o'yin Dota 2 da (Steam) o'ynaladi, natijani admin kuzatib, buyruq bilan kiritadi.

ISHGA TUSHIRISH (Kali Linux)
----------------------------
1)  unzip dota2sayt.zip && cd dota2sayt
2)  python3 -m venv venv && source venv/bin/activate
3)  pip install -r requirements.txt
4)  python app.py admin-yaratish        <- faqat yangi o'rnatishda (admin login/parol/pochta)
5)  python app.py                       <- sayt: http://127.0.0.1:5000

ESKI SAYTDAN YANGISIGA O'TISH (hammasi bitta bo'ladi)
-----------------------------------------------------
A) Yangi zipni eski papka ustiga ochgan bo'lsangiz (eski sayt.db shu papkada qolgan):
   hech narsa qilmaysiz. Birinchi ishga tushirishda sayt.db va rasmlar o'zi
   ~/dota2_malumot/ papkasiga ko'chadi. Barcha eski login va parollar, admin ham o'tadi.
B) Yangi papkaga ochgan bo'lsangiz, eski bazani qo'shing:
      python app.py eski-bazani-qoshish
   (u ~/Загрузки/dota2sayt/sayt.db ni o'zi topadi; boshqa joyda bo'lsa yo'lini yozing:
      python app.py eski-bazani-qoshish /yo'l/sayt.db )
   Eski foydalanuvchilar login va parollari bilan qo'shiladi, mavjudlari o'zgarmaydi.
   Agar yangi bazada admin bo'lmasa, eski admin ham admin bo'lib o'tadi.

LOGIN VA PAROLLAR QANDAY HIMOYALANGAN (uchib ketmasligi uchun)
--------------------------------------------------------------
1. Ma'lumotlar saytning kodidan ALOHIDA papkada turadi:  ~/dota2_malumot/
   Saytni yangilash, zipni qayta ochish yoki sayt papkasini o'chirish ularga tegmaydi.
   (Boshqa joy kerak bo'lsa:  DOTA_DATA=/yo'l python app.py )
2. Baza o'chish, qulash va elektr uzilishiga bardoshli rejimda ishlaydi (WAL + to'liq yozuv).
3. AVTOMATIK ZAHIRA: har yangi hisob ochilganda va har o'zgarishdan keyin 15 soniya ichida
   ~/dota2_malumot/zahira/ ga nusxa olinadi (oxirgi 48 ta + oxirgi 30 kunning har kunidan bittasi).
   Shu papkada foydalanuvchilar.json ham yangilanib turadi (login va parol xeshlari bilan).
4. O'ZI TIKLANADI: sayt ishga tushganda baza buzilgan bo'lsa, eng yangi butun zahiradan
   avtomatik tiklanadi va ekranga xabar chiqadi.
5. IKKINCHI JOY (tavsiya): kompyuter butunlay buzilsa ham saqlanib qolishi uchun zahirani
   boshqa diskka/fleshkaga ham yozdiring:
      DOTA_ZAHIRA2=/media/fleshka/dota2 python app.py
6. Admin panelida "Zahira nusxalar" bo'limi bor: "Hozir zahira olish" va
   "Yuklab olish (baza va rasmlar)" - zip faylni o'z kompyuteringiz yoki telefoningizga saqlab qo'ying.

Parollar oddiy matn bo'lib saqlanmaydi (shifrlangan xesh). Shuning uchun ularni kimdir ko'ra
olmaydi, lekin zahira fayllarini (ayniqsa zip va JSON) begonalarga bermang.

QO'LDA TIKLASH (kompyuter almashtirilsa, baza yo'qolsa)
-------------------------------------------------------
  python app.py zahira                         hozir zahira olish
  python app.py tiklash <zahira fayli.db>      zahiradan tiklash (avval saytni to'xtating)
  python app.py eski-bazani-qoshish fayl.json  foydalanuvchilar.json dan qo'shish
  python app.py eksport fayl.json              foydalanuvchilarni JSON ga chiqarish
Yangi kompyuterda: zipni yuklab oling (admin panel), ichidagi sayt.db ni ~/dota2_malumot/ ga,
rasmlar/ ni ~/dota2_malumot/rasmlar/ ga qo'ying va saytni ishga tushiring.

ADMIN
-----
- Admin faqat terminalda yaratiladi. Login va parol hech qayerda yozilmagan.
- Admin oddiy kirish oynasidan kiradi va avtomatik admin panelga o'tadi.
- Parolni unutsangiz:  python app.py admin-parol-tiklash
- "admin" bilan boshlanadigan nom bilan oddiy foydalanuvchi ro'yxatdan o'ta olmaydi.
- Bir nom uchun 5 marta noto'g'ri parol kiritilsa, 10 daqiqaga bloklanadi.

QANDAY ISHLAYDI
---------------
1. Foydalanuvchi ro'yxatdan o'tadi, profilini to'ldiradi (rasm, taxallus, daraja, pozitsiya).
2. "Turnirga qo'shiling": jamoa yaratadi yoki setkadagi jamoaning bo'sh joyini bosadi.
3. Joy 15 daqiqaga rezerv qilinadi. Foydalanuvchi to'lov (standart 15 000 so'm) qiladi va
   tranzaksiya raqamini kiritib "To'lov qildim" ni bosadi.
4. Admin "To'lovlar" bo'limida tasdiqlaydi yoki rad etadi. Tasdiqlansa joy foydalanuvchiniki
   bo'ladi va jamoa chatiga ochiladi.
5. Admin o'yinni Steam'da kuzatadi, so'ng "O'yinni boshlash" va "[Jamoa] g'olib" buyruqlarini
   beradi. G'olib jamoa keyingi bosqichga o'zi o'tadi. Hamma buyruqlar jurnalga yoziladi.
6. Xabarlar: foydalanuvchilar bir-biriga shaxsiy yozadi va support xizmatiga (adminga) murojaat qiladi.
   Admin faqat support so'rovlarini ko'radi, shaxsiy yozishmalarni emas.

SOZLAMALAR (Admin panel -> To'lov sozlamalari)
----------------------------------------------
Joy narxi va to'lov rekvizitlari (karta raqami, ism) admin panelida kiritiladi.
To'lov hozir qo'lda tekshiriladi. Click/Payme/Uzum kabi avtomatik to'lov keyin ulanishi mumkin.

INTERNETGA CHIQARISH (ixtiyoriy)
--------------------------------
- Faqat HTTPS orqali ishlating (nginx yoki Caddy orqasida) va   HTTPS=1 python app.py   deb ishga tushiring.
- Ishlab chiqarish serveri:  pip install waitress  ->  waitress-serve --port=5000 app:app
- Boshqa kompyuterlardan kirish uchun:  HOST=0.0.0.0 python app.py   (faqat himoyalangan tarmoqda)
- ~/dota2_malumot/.secret_key faylini hech kimga bermang.
