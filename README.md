# VideoEditor2000

Kompyuter uchun minimalistik video muharrir (Windows / macOS / Linux).

## Hozir nima qila oladi

**Videoni sifatni yo'qotmasdan qirqish.** Video qayta kodlanmaydi: siqilgan
video va audio paketlar yangi faylga o'zgarishsiz ko'chiriladi (`ffmpeg -c copy`).
Shuning uchun:

- sifat asl fayl bilan **100% bir xil** bo'ladi (testlar har bir paketni baytma-bayt solishtiradi);
- bir soatlik video ham bir necha soniyada saqlanadi;
- format, kodek, o'lcham, audio yo'laklari va metama'lumotlar o'zgarmaydi.

Bitta cheklovi bor: qayta kodlashsiz video faqat **kalit kadrdan** (keyframe)
boshlanishi mumkin. Shu sababli boshlanish nuqtasi undan oldingi eng yaqin
kalit kadrga avtomatik suriladi. Dastur buni ochiq ko'rsatadi: vaqt chizig'idagi
kichik chiziqchalar kalit kadrlarni bildiradi, surilganda esa pastda xabar
chiqadi. Tugash nuqtasi istalgan kadrga qo'yiladi.

## Foydalanish

1. Videoni oynaga sudrab tashlang yoki **Video tanlash** tugmasini bosing.
2. Vaqt chizig'idagi sariq tutqichlarni suring, yoki videoni kerakli joyga
   olib borib **[ Shu yerdan** / **Shu yergacha ]** tugmalarini bosing,
   yoki vaqtni qo'lda yozing (`1:23.5`, `83.5`).
3. **Tanlovni ko'rish** bilan natijani tekshiring.
4. **Qirqib saqlash** — tamom.

### Klaviatura

| Tugma | Amal |
|---|---|
| `Bo'sh joy` / `K` | O'ynatish / to'xtatish |
| `I` / `O` | Boshlanish / tugashni kursor joyiga qo'yish |
| `←` / `→` | Bir kadr orqaga / oldinga |
| `Shift+←` / `Shift+→` | 1 soniya |
| `J` / `L` | 5 soniya |
| `Home` / `End` | Tanlov boshiga / oxiriga |
| `P` | Tanlovni ko'rish |
| `Ctrl+O` | Video ochish |
| `Ctrl+S` | Qirqib saqlash |
| `Esc` | Saqlashni bekor qilish |

## O'rnatish

**Tayyor dastur (Windows):** GitHub → *Actions* → oxirgi "Windows build" →
*Artifacts* bo'limidan `VideoEditor2000-windows` ni yuklab oling, arxivni
oching va `VideoEditor2000.exe` ni ishga tushiring. `v*` tegi qo'yilganda
arxiv *Releases* sahifasiga ham chiqadi.

**Manba koddan:**

```bash
pip install -r requirements.txt
python run.py            # yoki: python run.py video.mp4
```

ffmpeg alohida o'rnatilishi shart emas: u `imageio-ffmpeg` paketi bilan birga
keladi. Boshqa ffmpeg ishlatish uchun `VIDEOEDITOR_FFMPEG` muhit o'zgaruvchisiga
yo'lini yozing.

**.exe yig'ish:** `pip install pyinstaller && pyinstaller --noconfirm build.spec`

## Tuzilishi

```
videoeditor/
  core/            Qt'siz yadro (alohida test qilinadi)
    media.py       video tahlili, kalit kadrlar (PyAV)
    trim.py        sifatni yo'qotmasdan qirqish (ffmpeg -c copy)
    timefmt.py     vaqt formatlari
    ffmpeg.py      ffmpeg ni topish
  ui/
    main_window.py asosiy oyna
    timeline.py    vaqt chizig'i
    style.py       ranglar va uslub
tests/             pytest
```

Testlar: `python -m pytest -q tests`

## Keyingi rejalar

- [ ] Bir videodan bir nechta bo'lakni kesib, birlashtirish
- [ ] Bir nechta videoni ketma-ket ulash
- [ ] Kadrga aniq qirqish ("smart cut": faqat chetidagi bir necha kadr qayta kodlanadi)
- [ ] Audioni ajratib olish / ovozni o'chirish
- [ ] Aylantirish va kadrlash (crop)
- [ ] Siqish / formatni o'zgartirish
