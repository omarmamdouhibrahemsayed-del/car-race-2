#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
  TURBO RUSH 10  -  لعبة سباق سيارات Pseudo-3D بكسل آرت (Pygame)
=====================================================================
  * كاميرا خلفية (Third-person rear view) مع منظور Pseudo-3D (Scaling road)
  * 10 سيارات في السباق: اللاعب + 9 سيارات ذكاء اصطناعي
  * كل الرسومات بكسل آرت مرسومة بالكود (لا صور ولا نماذج 3D)
  * كل الأصوات مولّدة بالكود (موتور، كلاكس، تصادم، ...)
  * متجر فيه 10 سيارات، ومكافأة 1000 جنيه عند المركز الأول
  * تقريب/إبعاد الكاميرا ديناميكياً مع عرض حالة المنظور

  التشغيل:   python turbo_rush.py
  المكتبات:  pip install pygame arabic-reshaper python-bidi
=====================================================================
"""
import array
import json
import math
import os
import random
import sys

import pygame

# دعم العربية (اختياري): بدونها تعمل الواجهة بالإنجليزية
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except Exception:  # pragma: no cover
    HAS_BIDI = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "turbo_rush_save.json")

# ----------------------------------------------------------------------
#  الثوابت العامة
# ----------------------------------------------------------------------
W, H = 320, 180                 # دقة الرسم الداخلية (بكسل آرت)
SCALE = 3
SW, SH = W * SCALE, H * SCALE   # حجم النافذة 960x540
FPS = 60

SEG_LEN = 200                   # طول مقطع الطريق
ROAD_W = 2000                   # نصف عرض الطريق (وحدات العالم)
LANES = 3
DRAW_DIST = 130                 # عدد المقاطع المرسومة أمام الكاميرا
RUMBLE_LEN = 3
HZ = int(H * 0.44)              # خط الأفق
REF_MAX = SEG_LEN * 60.0        # السرعة المرجعية (وحدة/ثانية) = 12000
BASE_FOV = 100.0
BASE_DEPTH = 1.0 / math.tan(math.radians(BASE_FOV / 2))

CAR_W = 0.26                    # عرض السيارة (كنسبة من ROAD_W)
CAR_LEN = 430                   # طول السيارة للتصادم (على محور z)
CAR_HIT_X = 0.24                # عرض التصادم الجانبي
CENTRIF = 0.30                  # قوة الطرد المركزي في المنعطفات
LAPS = 3
N_CARS = 10
PRIZE = 1000                    # مكافأة المركز الأول (جنيه)
START_MONEY = 1500
LINE_I = 6                      # رقم مقطع خط البداية
LINE_Z = LINE_I * SEG_LEN
BGW = 640                       # عرض طبقات الخلفية المتكررة


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def shade(c, f):
    return (clamp(int(c[0] * f), 0, 255), clamp(int(c[1] * f), 0, 255), clamp(int(c[2] * f), 0, 255))


def light(c, f):
    return (int(c[0] + (255 - c[0]) * f), int(c[1] + (255 - c[1]) * f), int(c[2] + (255 - c[2]) * f))


def ease_in(a, b, p):
    return a + (b - a) * (p * p)


def ease_in_out(a, b, p):
    return a + (b - a) * ((-math.cos(p * math.pi) / 2) + 0.5)


# ----------------------------------------------------------------------
#  النصوص (عربي / English)
# ----------------------------------------------------------------------
STR = {
    "en": {
        "subtitle": "10-CAR PIXEL RACING",
        "start": "Start Race", "shop": "Car Shop", "lang": "Language: English",
        "sound_on": "Sound: ON", "sound_off": "Sound: OFF", "quit": "Quit",
        "money": "MONEY", "cur": "EGP", "speed": "SPEED", "kmh": "km/h",
        "lap": "LAP {a}/{b}", "place": "POSITION", "standings": "STANDINGS",
        "you": "YOU", "camera": "Camera", "cam_0": "Close", "cam_1": "Normal", "cam_2": "Far",
        "fov": "FOV", "zoom": "Zoom", "go": "GO!", "finish": "FINISH!",
        "win": "YOU WON 1st PLACE!", "prize": "Reward: +{n} EGP",
        "lose": "You finished {n} of 10 - try again!",
        "results": "RACE RESULTS", "enter_menu": "Enter: menu    R: race again",
        "buy": "Buy", "equip": "Use this car", "owned": "Owned", "equipped": "Equipped",
        "price": "Price", "top": "Top speed", "accel": "Acceleration", "handling": "Handling",
        "not_enough": "Not enough money!", "bought": "Purchased & equipped!", "selected": "Car selected!",
        "shop_hint": "Left/Right: browse   Enter: buy / use   Esc: back",
        "paused": "PAUSED", "paused_hint": "Enter: resume    Backspace: menu",
        "honk": "HONK!", "free": "Free",
        "ctrl1": "W/Up: gas   S/Down: brake   A D / Left Right: steer",
        "ctrl2": "Space/H: horn   Q/E/Wheel: camera zoom   C: camera   P: pause   M: mute",
        "shop_title": "CAR SHOP", "pos_lbl": "POS",
    },
    "ar": {
        "subtitle": "سباق بكسل آرت بعشر سيارات",
        "start": "ابدأ السباق", "shop": "متجر السيارات", "lang": "اللغة: العربية",
        "sound_on": "الصوت: يعمل", "sound_off": "الصوت: متوقف", "quit": "خروج",
        "money": "المال", "cur": "جنيه", "speed": "السرعة", "kmh": "كم/س",
        "lap": "اللفة {a}/{b}", "place": "المركز", "standings": "الترتيب",
        "you": "أنت", "camera": "الكاميرا", "cam_0": "قريبة", "cam_1": "متوسطة", "cam_2": "بعيدة",
        "fov": "زاوية الرؤية", "zoom": "التقريب", "go": "انطلق!", "finish": "انتهى السباق!",
        "win": "مبروك! فزت بالمركز الأول!", "prize": "المكافأة: +{n} جنيه",
        "lose": "جئت في المركز {n} من 10 - حاول مرة أخرى!",
        "results": "نتائج السباق", "enter_menu": "Enter: القائمة    R: سباق جديد",
        "buy": "شراء", "equip": "استخدام السيارة", "owned": "مملوكة", "equipped": "مستخدمة حالياً",
        "price": "السعر", "top": "السرعة القصوى", "accel": "التسارع", "handling": "التحكم",
        "not_enough": "رصيدك غير كافٍ!", "bought": "تم الشراء والاختيار!", "selected": "تم اختيار السيارة!",
        "shop_hint": "يمين/يسار: تصفح   Enter: شراء / استخدام   Esc: رجوع",
        "paused": "إيقاف مؤقت", "paused_hint": "Enter: متابعة    Backspace: القائمة",
        "honk": "كلاكس!", "free": "مجاناً",
        "ctrl1": "W/Up: تسارع   S/Down: فرامل   A D / الأسهم: توجيه",
        "ctrl2": "Space/H: كلاكس   Q/E/عجلة الماوس: تقريب   C: الكاميرا   P: إيقاف   M: كتم",
        "shop_title": "متجر السيارات", "pos_lbl": "المركز",
    },
}

AI_NAMES = [("Ahmed", "أحمد"), ("Omar", "عمر"), ("Khaled", "خالد"), ("Youssef", "يوسف"),
            ("Hassan", "حسن"), ("Karim", "كريم"), ("Mostafa", "مصطفى"), ("Tarek", "طارق"),
            ("Sami", "سامي"), ("Adel", "عادل")]

# ----------------------------------------------------------------------
#  بيانات السيارات العشر (المتجر)
# ----------------------------------------------------------------------
CARS = [
    dict(en="Rookie GT",    ar="روكي جي تي",     price=0,    top=0.95, acc=0.90, hnd=1.00, body=(45, 110, 225),  style=()),
    dict(en="Street Fox",   ar="الثعلب",          price=700,  top=0.99, acc=0.95, hnd=1.02, body=(235, 130, 30),  style=()),
    dict(en="Green Hornet", ar="الدبور الأخضر",   price=1200, top=1.02, acc=1.00, hnd=1.00, body=(40, 170, 70),   style=("stripe",)),
    dict(en="Red Falcon",   ar="الصقر الأحمر",    price=1800, top=1.05, acc=1.05, hnd=1.03, body=(215, 40, 45),   style=("spoiler",)),
    dict(en="Silver Arrow", ar="السهم الفضي",     price=2400, top=1.08, acc=1.08, hnd=1.05, body=(185, 192, 205), style=("stripe",)),
    dict(en="Purple Storm", ar="العاصفة",         price=3000, top=1.10, acc=1.12, hnd=1.08, body=(150, 60, 200),  style=("spoiler",)),
    dict(en="Yellow Bolt",  ar="الصاعقة",         price=3800, top=1.13, acc=1.12, hnd=1.10, body=(240, 210, 30),  style=("stripe", "spoiler")),
    dict(en="Black Mamba",  ar="الأفعى السوداء",  price=4800, top=1.16, acc=1.16, hnd=1.12, body=(52, 52, 64),    style=("stripe", "spoiler")),
    dict(en="Cyan Phantom", ar="الشبح",           price=6000, top=1.19, acc=1.20, hnd=1.15, body=(30, 200, 210),  style=("spoiler",)),
    dict(en="Golden King",  ar="الملك الذهبي",    price=8000, top=1.23, acc=1.25, hnd=1.18, body=(235, 188, 50),  style=("stripe", "spoiler")),
]

# ----------------------------------------------------------------------
#  السمات (ثلاث بيئات للسباق)
# ----------------------------------------------------------------------
THEMES = [
    dict(name="day", sky_top=(66, 146, 235), sky_bot=(190, 228, 250), haze=(176, 214, 240),
         grass=((62, 172, 72), (54, 158, 64)), road=((104, 104, 112), (96, 96, 104)),
         rumble=((214, 52, 52), (238, 238, 238)), lane=(226, 226, 226),
         m1=(120, 150, 200), m2=(72, 120, 110), sun=(255, 244, 170), cloud=(255, 255, 255),
         side=["pine", "pine", "bush", "autumn", "bb0", "bb1", "rock"]),
    dict(name="sunset", sky_top=(110, 56, 150), sky_bot=(255, 170, 100), haze=(240, 170, 130),
         grass=((92, 142, 64), (82, 128, 56)), road=((98, 92, 104), (90, 84, 96)),
         rumble=((214, 52, 52), (238, 238, 238)), lane=(236, 226, 206),
         m1=(160, 90, 130), m2=(98, 56, 88), sun=(255, 220, 120), cloud=(255, 200, 180),
         side=["autumn", "pine", "autumn", "bush", "bb1", "bb2", "rock"]),
    dict(name="desert", sky_top=(60, 150, 230), sky_bot=(250, 232, 190), haze=(240, 222, 180),
         grass=((226, 194, 112), (214, 180, 98)), road=((110, 104, 100), (102, 96, 92)),
         rumble=((214, 52, 52), (238, 238, 238)), lane=(236, 230, 210),
         m1=(214, 146, 100), m2=(176, 108, 76), sun=(255, 250, 200), cloud=(255, 255, 255),
         side=["cactus", "rock", "cactus", "bb0", "bb2", "bush"]),
]


# ======================================================================
#  الصوت: كل الأصوات مولّدة بالكود عبر pygame.mixer
# ======================================================================
class Audio:
    N_ENG = 20

    def __init__(self):
        self.ok = False
        self.muted = False
        self.cur = -1
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.sr, _fmt, self.nch = pygame.mixer.get_init()
            pygame.mixer.set_num_channels(12)
            self._build()
            self.c_eng = pygame.mixer.Channel(0)
            self.c_wind = pygame.mixer.Channel(1)
            self.c_off = pygame.mixer.Channel(2)
            self.c_horn = pygame.mixer.Channel(3)
            self.c_crash = pygame.mixer.Channel(4)
            self.c_ui = pygame.mixer.Channel(5)
            self.c_ai = pygame.mixer.Channel(6)
            self.ok = True
        except Exception as e:  # الصوت غير متاح -> تعمل اللعبة بدون صوت
            print("Audio disabled:", e)
            self.ok = False

    # ---------- بناء الأصوات ----------
    def _mk(self, samples):
        a = array.array("h")
        for s in samples:
            v = int(clamp(s, -1.0, 1.0) * 32000)
            a.append(v)
            if self.nch == 2:
                a.append(v)
        return pygame.mixer.Sound(buffer=a.tobytes())

    def _tone(self, freq, dur, vol=0.5, decay=2.0, harm=0.0):
        sr = self.sr
        n = int(sr * dur)
        out = []
        for i in range(n):
            t = i / sr
            e = min(1.0, i / (0.005 * sr)) * (1 - i / n) ** decay
            v = math.sin(2 * math.pi * freq * t) + harm * math.sin(4 * math.pi * freq * t)
            out.append(v * e * vol)
        return out

    def _engine_loop(self, f):
        sr = self.sr
        p = max(8, int(sr / f))
        unit = 2 * p
        wave = []
        for i in range(unit):
            ph = 2 * math.pi * i / p
            v = 0.0
            for h in range(1, 8):
                v += math.sin(h * ph + 0.7 * h) / (h ** 0.85)
            v += 0.7 * math.sin(0.5 * ph)          # نبضات الاحتراق
            wave.append(math.tanh(v * 0.55) * 0.62)
        reps = max(1, int(0.25 * sr / unit) + 1)
        rnd = random.Random(int(f))
        out = []
        for _ in range(reps):
            for w in wave:
                out.append(w + rnd.uniform(-0.04, 0.04))
        return out

    def _build(self):
        sr = self.sr
        rnd = random.Random(7)
        # محرك بعدة مستويات من اللفات (RPM)
        self.eng = []
        for k in range(self.N_ENG):
            f = 38 + 135 * (k / (self.N_ENG - 1)) ** 1.1
            self.eng.append(self._mk(self._engine_loop(f)))
        # كلاكس طويل (حلقة) وقصير (للسيارات الأخرى)
        n = int(sr * 0.5)
        horn = []
        for i in range(n):
            t = i / sr
            v = (math.sin(2 * math.pi * 400 * t) + math.sin(2 * math.pi * 500 * t)
                 + 0.5 * math.sin(2 * math.pi * 1200 * t) + 0.4 * math.sin(2 * math.pi * 1500 * t))
            horn.append(math.tanh(v * 0.9) * 0.45)
        self.horn_long = self._mk(horn)
        n = int(sr * 0.35)
        horn2 = []
        for i in range(n):
            t = i / sr
            e = min(1.0, i / (0.01 * sr)) * (1 - (i / n) ** 4)
            v = math.sin(2 * math.pi * 330 * t) + math.sin(2 * math.pi * 415 * t) + 0.4 * math.sin(2 * math.pi * 990 * t)
            horn2.append(math.tanh(v * 0.9) * 0.4 * e)
        self.horn_short = self._mk(horn2)
        # تصادم
        n = int(sr * 0.45)
        crash = []
        for i in range(n):
            t = i / n
            crash.append(rnd.uniform(-1, 1) * (1 - t) ** 2 * 0.8
                         + 0.7 * math.sin(2 * math.pi * (110 - 70 * t) * i / sr) * (1 - t) ** 1.5)
        self.crash = self._mk(crash)
        # رياح (حلقة)
        y = 0.0
        wind = []
        for _ in range(int(sr * 0.7)):
            y += 0.30 * (rnd.uniform(-1, 1) - y)
            wind.append(y * 1.5)
        self.wind = self._mk(wind)
        # اهتزاز خارج الطريق (حلقة)
        y = 0.0
        rum = []
        for i in range(int(sr * 0.5)):
            y += 0.06 * (rnd.uniform(-1, 1) - y)
            rum.append(clamp(y * 7, -1, 1) * (0.7 + 0.3 * math.sin(i * 0.02)))
        self.rumble = self._mk(rum)
        # واجهة
        self.s_click = self._mk(self._tone(900, 0.05, 0.4))
        self.s_beep = self._mk(self._tone(660, 0.18, 0.5, 1.0))
        self.s_go = self._mk(self._tone(990, 0.45, 0.55, 1.2, 0.4))
        self.s_buy = self._mk(self._tone(660, 0.09, 0.5) + self._tone(880, 0.09, 0.5) + self._tone(1320, 0.2, 0.5))
        self.s_err = self._mk(self._tone(180, 0.25, 0.6, 1.0, 0.5))
        win = []
        for f, d in zip((523, 659, 784, 1047, 784, 1047, 1319), (0.12,) * 6 + (0.55,)):
            win += self._tone(f, d, 0.5, 1.3, 0.3)
        self.s_win = self._mk(win)
        lose = []
        for f, d in zip((392, 349, 311, 262), (0.2, 0.2, 0.2, 0.55)):
            lose += self._tone(f, d, 0.5, 1.2, 0.4)
        self.s_lose = self._mk(lose)

    # ---------- التحكم ----------
    def toggle_mute(self):
        self.muted = not self.muted
        if self.ok and self.muted:
            pygame.mixer.stop()
            self.cur = -1

    def engine(self, rpm, thr):
        if not self.ok or self.muted:
            return
        lvl = int(clamp(rpm, 0, 1) * (self.N_ENG - 1))
        if lvl != self.cur or not self.c_eng.get_busy():
            self.c_eng.play(self.eng[lvl], loops=-1)
            self.cur = lvl
        self.c_eng.set_volume(0.28 + 0.30 * clamp(thr, 0, 1))

    def stop_engine(self):
        if self.ok:
            self.c_eng.stop()
            self.c_wind.stop()
            self.c_off.stop()
            self.c_horn.stop()
            self.cur = -1

    def set_wind(self, v):
        if not self.ok or self.muted:
            return
        if v < 0.05:
            self.c_wind.stop()
            return
        if not self.c_wind.get_busy():
            self.c_wind.play(self.wind, loops=-1)
        self.c_wind.set_volume(clamp(v, 0, 1) * 0.25)

    def set_offroad(self, on, v=0.5):
        if not self.ok or self.muted:
            return
        if on:
            if not self.c_off.get_busy():
                self.c_off.play(self.rumble, loops=-1)
            self.c_off.set_volume(clamp(v, 0.1, 1.0) * 0.6)
        else:
            self.c_off.stop()

    def horn(self, on):
        if not self.ok or self.muted:
            return
        if on:
            if not self.c_horn.get_busy():
                self.c_horn.play(self.horn_long, loops=-1)
                self.c_horn.set_volume(0.7)
        else:
            self.c_horn.stop()

    def honk_ai(self, vol):
        if self.ok and not self.muted and not self.c_ai.get_busy():
            self.c_ai.play(self.horn_short)
            self.c_ai.set_volume(clamp(vol, 0.05, 0.5))

    def crash_snd(self, vol=0.8):
        if self.ok and not self.muted:
            self.c_crash.play(self.crash)
            self.c_crash.set_volume(clamp(vol, 0.2, 1.0))

    def ui(self, name):
        if self.ok and not self.muted:
            self.c_ui.play(getattr(self, "s_" + name))
            self.c_ui.set_volume(0.6)


# ======================================================================
#  الرسومات: بكسل آرت مرسوم بالكود
# ======================================================================
def add_outline(s, col=(12, 12, 20)):
    w, h = s.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    out.blit(s, (1, 1))
    mask = pygame.mask.from_surface(out, 10)
    for y in range(h + 2):
        for x in range(w + 2):
            if not mask.get_at((x, y)):
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w + 2 and 0 <= ny < h + 2 and mask.get_at((nx, ny)):
                        out.set_at((x, y), col)
                        break
    return out


def make_car(m, braking=False):
    """سيارة من الخلف (40x22) + إطار أسود."""
    body = m["body"]
    dk = shade(body, 0.60)
    lt = light(body, 0.40)
    s = pygame.Surface((40, 22), pygame.SRCALPHA)

    def R(c, r):
        pygame.draw.rect(s, c, r)

    # الإطارات
    R((24, 24, 28), (0, 11, 7, 11))
    R((24, 24, 28), (33, 11, 7, 11))
    R((72, 72, 80), (1, 12, 2, 9))
    R((72, 72, 80), (34, 12, 2, 9))
    # الهيكل
    R(body, (3, 9, 34, 11))
    R(dk, (3, 17, 34, 3))
    R(lt, (3, 9, 34, 1))
    R(body, (8, 1, 24, 9))
    R(lt, (9, 1, 22, 1))
    # الزجاج الخلفي
    R((36, 62, 100), (10, 2, 20, 7))
    R((96, 146, 196), (10, 2, 20, 1))
    R((62, 102, 152), (11, 3, 6, 2))
    R(dk, (19, 2, 2, 7))
    st = m["style"]
    if "stripe" in st:
        bright = sum(body) / 3.0
        sc = (240, 240, 240) if bright < 170 else (40, 40, 52)
        R(sc, (18, 9, 4, 8))
        R(sc, (18, 1, 4, 1))
    # الأضواء الخلفية
    if braking:
        c1, c2, glow = (255, 60, 50), (255, 150, 130), (255, 220, 200)
    else:
        c1, c2, glow = (200, 18, 30), (255, 80, 80), None
    R((90, 10, 18), (13, 12, 14, 2))
    R(c1, (4, 10, 10, 5))
    R(c1, (26, 10, 10, 5))
    R(c2, (6, 11, 6, 2))
    R(c2, (28, 11, 6, 2))
    if glow:
        R(glow, (7, 11, 3, 2))
        R(glow, (29, 11, 3, 2))
        R(c2, (14, 12, 12, 1))
    # اللوحة والعادم
    R((236, 236, 226), (16, 14, 8, 4))
    R((70, 70, 80), (17, 16, 6, 1))
    R((100, 100, 108), (8, 19, 4, 2))
    R((100, 100, 108), (28, 19, 4, 2))
    R(dk, (2, 19, 36, 1))
    if "spoiler" in st:
        R(dk, (3, 5, 34, 2))
        R(lt, (3, 5, 34, 1))
        R(dk, (8, 7, 3, 3))
        R(dk, (29, 7, 3, 3))
    return add_outline(s)


def make_pine(c_dark, c_light, trunk=(92, 58, 34)):
    s = pygame.Surface((40, 64), pygame.SRCALPHA)
    pygame.draw.rect(s, trunk, (18, 50, 5, 14))
    pygame.draw.rect(s, shade(trunk, 0.7), (21, 50, 2, 14))
    for t in range(4):
        top = 2 + t * 11
        hw = 9 + t * 3
        base = top + 20
        pygame.draw.polygon(s, c_dark, [(20, top), (20 - hw, base), (20 + hw, base)])
        pygame.draw.polygon(s, c_light, [(20, top), (20 - hw, base), (20, base)])
    return add_outline(s)


def make_bush():
    s = pygame.Surface((30, 16), pygame.SRCALPHA)
    for cx, cy, r in ((8, 10, 7), (15, 8, 8), (22, 10, 7)):
        pygame.draw.circle(s, (30, 112, 52), (cx, cy), r)
    for cx, cy, r in ((7, 8, 4), (14, 6, 5), (21, 8, 4)):
        pygame.draw.circle(s, (56, 156, 74), (cx, cy), r)
    return add_outline(s)


def make_rock():
    s = pygame.Surface((32, 18), pygame.SRCALPHA)
    pygame.draw.polygon(s, (112, 112, 124), [(2, 17), (6, 7), (14, 2), (24, 5), (30, 17)])
    pygame.draw.polygon(s, (150, 150, 162), [(6, 7), (14, 2), (18, 3), (12, 10), (7, 12)])
    pygame.draw.rect(s, (78, 78, 90), (3, 13, 27, 4))
    return add_outline(s)


def make_cactus():
    s = pygame.Surface((18, 42), pygame.SRCALPHA)
    g, g2 = (48, 150, 68), (90, 190, 100)
    pygame.draw.rect(s, g, (6, 3, 6, 39))
    pygame.draw.rect(s, g, (1, 16, 6, 3))
    pygame.draw.rect(s, g, (1, 10, 3, 9))
    pygame.draw.rect(s, g, (11, 24, 6, 3))
    pygame.draw.rect(s, g, (14, 15, 3, 12))
    pygame.draw.rect(s, g2, (7, 4, 2, 37))
    pygame.draw.rect(s, g2, (2, 11, 1, 7))
    return add_outline(s)


def make_billboard(c1, c2):
    s = pygame.Surface((44, 40), pygame.SRCALPHA)
    pygame.draw.rect(s, (70, 70, 80), (8, 22, 3, 18))
    pygame.draw.rect(s, (70, 70, 80), (33, 22, 3, 18))
    pygame.draw.rect(s, (240, 240, 240), (0, 2, 44, 22))
    pygame.draw.rect(s, c1, (2, 4, 40, 18))
    for k in range(5):
        pygame.draw.rect(s, c2, (5 + k * 8, 7, 4, 12))
    pygame.draw.circle(s, c2, (22, 13), 5)
    pygame.draw.circle(s, c1, (22, 13), 2)
    return add_outline(s)


def make_arch():
    s = pygame.Surface((160, 60), pygame.SRCALPHA)
    pygame.draw.rect(s, (230, 230, 235), (0, 0, 7, 60))
    pygame.draw.rect(s, (230, 230, 235), (153, 0, 7, 60))
    pygame.draw.rect(s, (200, 40, 40), (0, 30, 7, 8))
    pygame.draw.rect(s, (200, 40, 40), (153, 30, 7, 8))
    pygame.draw.rect(s, (30, 30, 36), (0, 0, 160, 16))
    for yy in range(4):
        for xx in range(0, 160, 4):
            if (xx // 4 + yy) % 2 == 0:
                pygame.draw.rect(s, (240, 240, 240), (xx, yy * 4, 4, 4))
    return add_outline(s)


def build_assets():
    A = {}
    A["pine"] = (make_pine((24, 104, 56), (40, 140, 70)), 0.42, True)
    A["autumn"] = (make_pine((196, 92, 30), (232, 148, 44), (96, 60, 36)), 0.42, True)
    A["bush"] = (make_bush(), 0.30, False)
    A["rock"] = (make_rock(), 0.28, True)
    A["cactus"] = (make_cactus(), 0.18, True)
    A["bb0"] = (make_billboard((220, 60, 60), (250, 220, 60)), 0.62, True)
    A["bb1"] = (make_billboard((50, 110, 220), (255, 255, 255)), 0.62, True)
    A["bb2"] = (make_billboard((40, 160, 90), (255, 210, 60)), 0.62, True)
    A["arch"] = (make_arch(), 2.5, False)
    return A


def make_ridge(width, h, color, hi, comps, seed):
    s = pygame.Surface((width, h), pygame.SRCALPHA)
    rng = random.Random(seed)
    phases = [rng.uniform(0, 6.28) for _ in comps]
    for x in range(width):
        xx = (x // 2) * 2
        v = 0.55
        for (k, a), p in zip(comps, phases):
            v += a * math.sin(2 * math.pi * k * xx / width + p)
        hh = int(clamp(v, 0.1, 1.0) * h)
        pygame.draw.line(s, color, (x, h - hh), (x, h))
        s.set_at((x, h - hh), hi)
    return s


# ======================================================================
#  المسار (Track) والمُرسِم (Renderer) - Pseudo-3D
# ======================================================================
class Seg:
    __slots__ = ("i", "z1", "z2", "y1", "y2", "curve", "dark", "sprites", "cars", "start")

    def __init__(self, i, y1, y2, curve):
        self.i = i
        self.z1 = i * SEG_LEN
        self.z2 = (i + 1) * SEG_LEN
        self.y1 = y1
        self.y2 = y2
        self.curve = curve
        self.dark = (i // RUMBLE_LEN) % 2
        self.sprites = []
        self.cars = []
        self.start = False


def build_track(assets, theme, rng):
    segs = []

    def last_y():
        return segs[-1].y2 if segs else 0.0

    def add(curve, y):
        segs.append(Seg(len(segs), last_y(), y, curve))

    def road(enter, hold, leave, curve, y):
        sy = last_y()
        ey = sy + y * SEG_LEN
        tot = float(enter + hold + leave)
        for n in range(enter):
            add(ease_in(0, curve, n / float(enter)), ease_in_out(sy, ey, n / tot))
        for n in range(hold):
            add(curve, ease_in_out(sy, ey, (enter + n) / tot))
        for n in range(leave):
            add(ease_in_out(curve, 0, n / float(leave)), ease_in_out(sy, ey, (enter + hold + n) / tot))

    LOW, MED, HIGH = 10, 22, 34
    road(8, 40, 8, 0, 0)          # بداية مستقيمة (حيث تقف السيارات)
    road(25, 25, 25, 0, LOW)
    road(25, 45, 25, 3, 0)
    road(15, 20, 15, 0, -LOW)
    road(25, 35, 25, -4, LOW)
    road(10, 30, 10, 0, 0)
    road(25, 40, 25, 5, -MED)
    road(15, 15, 15, 0, MED)
    road(20, 30, 20, -2, 0)
    road(20, 20, 20, 4, 0)        # منعطفات S
    road(20, 20, 20, -4, 0)
    road(30, 60, 30, 0, 0)        # مستقيم طويل
    road(20, 40, 20, 0, HIGH)
    road(30, 30, 30, -5, -MED)
    road(20, 20, 20, 0, -MED)
    road(25, 50, 25, 4, LOW)
    road(15, 25, 15, 0, 0)
    road(30, 45, 30, -3, 0)
    road(20, 30, 20, 3, -LOW)
    road(20, 40, 20, -2, 0)
    # العودة لمستوى الأرض لتتصل اللفات بسلاسة
    road(40, 40, 40, 0, -last_y() / SEG_LEN)
    segs[-1].y2 = 0.0

    # خط البداية/النهاية
    segs[LINE_I].start = True
    segs[LINE_I + 1].start = True

    # عناصر جانب الطريق
    names = theme["side"]
    N = len(segs)
    for i in range(0, N, 4):
        if LINE_I - 6 <= i <= LINE_I + 6:
            continue
        for side in (-1, 1):
            if rng.random() < 0.72:
                nm = rng.choice(names)
                if nm.startswith("bb") and rng.random() < 0.65:
                    continue
                img, wf, solid = assets[nm]
                off = side * (1.40 + rng.random() * 1.0)
                segs[i].sprites.append((img, off, wf, solid))
            if rng.random() < 0.55:
                nm = rng.choice([n for n in names if not n.startswith("bb")])
                img, wf, solid = assets[nm]
                off = side * (3.0 + rng.random() * 2.6)
                segs[i].sprites.append((img, off, wf, solid))
    img, wf, solid = assets["arch"]
    segs[LINE_I].sprites.append((img, 0.0, wf, False))
    return segs


class Renderer:
    def __init__(self, segs, theme):
        self.segs = segs
        self.n = len(segs)
        self.L = self.n * SEG_LEN
        self.theme = theme
        haze = theme["haze"]
        self.pal = []
        for n in range(DRAW_DIST):
            f = min(0.85, (n / float(DRAW_DIST)) ** 2 * 0.95)
            row = []
            for d in (0, 1):
                row.append((mix(theme["grass"][d], haze, f), mix(theme["rumble"][d], haze, f),
                            mix(theme["road"][d], haze, f), mix(theme["lane"], haze, f)))
            self.pal.append(row)
        self.occupied = []
        self.player_rect = (W // 2, H - 10, 60)
        self._make_bg()

    # ---------- الخلفية ----------
    def _make_bg(self):
        t = self.theme
        rng = random.Random(11)
        sky = pygame.Surface((W, H))
        for y in range(HZ):
            sky.fill(mix(t["sky_top"], t["sky_bot"], y / float(HZ)), (0, y, W, 1))
        sky.fill(mix(t["grass"][0], t["haze"], 0.8), (0, HZ, W, H - HZ))
        sx, sy = 236, int(HZ * 0.5)
        base = mix(t["sky_top"], t["sky_bot"], sy / float(HZ))
        for r, a in ((22, 0.25), (17, 0.45), (12, 1.0)):
            pygame.draw.circle(sky, mix(base, t["sun"], a), (sx, sy), r)
        self.sky = sky
        clouds = pygame.Surface((BGW, HZ), pygame.SRCALPHA)
        cc = t["cloud"] + (210,)
        for _ in range(8):
            cx = rng.randrange(10, BGW - 70)
            cy = rng.randrange(6, max(8, HZ - 36))
            for k in range(rng.randint(3, 5)):
                bw = rng.randint(18, 34)
                pygame.draw.ellipse(clouds, cc, (cx + k * 12, cy + rng.randint(-3, 3), bw, rng.randint(7, 11)))
        r1 = make_ridge(BGW, 46, t["m1"], light(t["m1"], 0.35), [(3, 0.22), (7, 0.12), (13, 0.06)], 3)
        r2 = make_ridge(BGW, 28, t["m2"], light(t["m2"], 0.3), [(5, 0.2), (11, 0.12), (19, 0.07)], 5)
        self.layers = [(clouds, 0.10, 0), (r1, 0.28, HZ - 46 + 2), (r2, 0.50, HZ - 28 + 2)]

    def draw_bg(self, surf, scroll):
        surf.blit(self.sky, (0, 0))
        for layer, f, y in self.layers:
            off = int(scroll * f) % BGW
            surf.blit(layer, (-off, y))
            surf.blit(layer, (BGW - off, y))

    def find(self, z):
        return self.segs[int(z // SEG_LEN) % self.n]

    # ---------- رسم السبرايت ----------
    def blit_sprite(self, surf, img, world_w, scale, sx, sy, clip, shadow=False):
        dw = int(scale * world_w * ROAD_W * (W / 2.0))
        if dw < 2 or dw > 900:
            return
        iw, ih = img.get_size()
        dh = int(dw * ih / float(iw))
        if dh < 1:
            return
        dx = int(sx - dw / 2.0)
        dy = int(sy - dh)
        if dx >= W or dx + dw <= 0 or dy >= clip:
            return
        scaled = pygame.transform.scale(img, (dw, dh))
        need_clip = (dy + dh) > clip
        if need_clip:
            surf.set_clip((0, 0, W, max(0, int(clip))))
        if shadow:
            sh = max(2, int(dh * 0.20))
            pygame.draw.ellipse(surf, (34, 34, 42), (dx + int(dw * 0.03), dy + dh - sh // 2 - 1, int(dw * 0.94), sh))
        surf.blit(scaled, (dx, dy))
        if need_clip:
            surf.set_clip(None)

    # ---------- الرسم الرئيسي ----------
    def draw(self, surf, cam_z, cam_x, cam_h, cam_depth, player_z, ais, pinfo, bg_scroll):
        segs = self.segs
        N = self.n
        L = self.L
        half_w = W / 2.0
        half_h = H / 2.0
        cam_z %= L
        base = segs[int(cam_z // SEG_LEN) % N]
        base_pct = (cam_z % SEG_LEN) / float(SEG_LEN)
        pz = (cam_z + player_z) % L
        pseg = segs[int(pz // SEG_LEN) % N]
        ppct = (pz % SEG_LEN) / float(SEG_LEN)
        py = pseg.y1 + (pseg.y2 - pseg.y1) * ppct
        cam_y = py + cam_h
        cam_px = cam_x * ROAD_W

        self.draw_bg(surf, bg_scroll)

        for s in self.occupied:
            del s.cars[:]
        self.occupied = []
        for c in ais:
            sg = segs[int(c.z // SEG_LEN) % N]
            sg.cars.append((c, (c.z % SEG_LEN) / float(SEG_LEN)))
            self.occupied.append(sg)

        maxy = H
        x = 0.0
        dx = -(base.curve * base_pct)
        info = []
        pal = self.pal
        for n in range(DRAW_DIST):
            s = segs[(base.i + n) % N]
            cz = cam_z - (L if s.i < base.i else 0)
            z1 = s.z1 - cz
            z2 = s.z2 - cz
            sc1 = cam_depth / (z1 if z1 > 1 else 1.0)
            sc2 = cam_depth / (z2 if z2 > 1 else 1.0)
            x1 = int(half_w + sc1 * (x - cam_px) * half_w)
            x2 = int(half_w + sc2 * (x + dx - cam_px) * half_w)
            y1 = int(HZ - sc1 * (s.y1 - cam_y) * half_h)
            y2 = int(HZ - sc2 * (s.y2 - cam_y) * half_h)
            w1 = int(sc1 * ROAD_W * half_w)
            w2 = int(sc2 * ROAD_W * half_w)
            x += dx
            dx += s.curve
            clip = maxy
            info.append((s, x1, y1, w1, sc1, x2, y2, w2, sc2, clip))
            if z1 <= cam_depth or y2 >= y1 or y2 >= maxy:
                continue
            gr, ru, ro, la = pal[n][s.dark]
            clipped = y1 > maxy
            if clipped:
                surf.set_clip((0, 0, W, maxy))
            pygame.draw.rect(surf, gr, (0, y2, W, y1 - y2 + 1))
            r1 = w1 / 6.0
            r2 = w2 / 6.0
            pygame.draw.polygon(surf, ru, [(x1 - w1 - r1, y1), (x1 - w1, y1), (x2 - w2, y2), (x2 - w2 - r2, y2)])
            pygame.draw.polygon(surf, ru, [(x1 + w1 + r1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 + w2 + r2, y2)])
            pygame.draw.polygon(surf, ro, [(x1 - w1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 - w2, y2)])
            if s.start:
                cells = 14
                for k in range(cells):
                    f0 = k / float(cells)
                    f1 = (k + 1) / float(cells)
                    col = (240, 240, 240) if (k + s.i) % 2 == 0 else (30, 30, 36)
                    pygame.draw.polygon(surf, col, [
                        (x1 - w1 + 2 * w1 * f0, y1), (x1 - w1 + 2 * w1 * f1, y1),
                        (x2 - w2 + 2 * w2 * f1, y2), (x2 - w2 + 2 * w2 * f0, y2)])
            elif not s.dark:
                lw1 = max(1.0, w1 / 36.0)
                lw2 = max(1.0, w2 / 36.0)
                for k in range(1, LANES):
                    lx1 = x1 - w1 + (2.0 * w1 * k / LANES)
                    lx2 = x2 - w2 + (2.0 * w2 * k / LANES)
                    pygame.draw.polygon(surf, la, [(lx1 - lw1, y1), (lx1 + lw1, y1), (lx2 + lw2, y2), (lx2 - lw2, y2)])
            if clipped:
                surf.set_clip(None)
            maxy = y1
            if maxy <= 0:
                break

        # ---- السبرايتات والسيارات (من الأبعد للأقرب) ----
        for n in range(len(info) - 1, -1, -1):
            s, x1, y1, w1, sc1, x2, y2, w2, sc2, clip = info[n]
            for (img, off, wf, solid) in s.sprites:
                sx = x1 + sc1 * off * ROAD_W * half_w
                self.blit_sprite(surf, img, wf, sc1, sx, y1, clip)
            for (c, pct) in s.cars:
                sc = lerp(sc1, sc2, pct)
                sx = lerp(x1, x2, pct) + sc * c.x * ROAD_W * half_w
                sy = lerp(y1, y2, pct)
                self.blit_sprite(surf, c.img, CAR_W, sc, sx, sy, clip, shadow=True)
            if pinfo is not None and s is pseg:
                sc = cam_depth / player_z
                gy = HZ - sc * (py - cam_y) * half_h + pinfo.get("dy", 0)
                gx = half_w + pinfo.get("dx", 0)
                dw = int(sc * CAR_W * ROAD_W * half_w)
                self.player_rect = (int(gx), int(gy), dw)
                self.blit_sprite(surf, pinfo["img"], CAR_W, sc, gx, gy, H + 50, shadow=True)


# ======================================================================
#  السيارات (لاعب + ذكاء اصطناعي)
# ======================================================================
class Car:
    L = 1.0

    def __init__(self, mi, name_pair, is_player=False):
        self.mi = mi
        self.m = CARS[mi]
        self.name_pair = name_pair      # (EN, AR)
        self.is_player = is_player
        self.dist = 0.0                 # المسافة المقطوعة من خط البداية
        self.x = 0.0
        self.speed = 0.0
        self.top = REF_MAX * self.m["top"]
        self.acc = self.m["acc"]
        self.hnd = self.m["hnd"]
        self.finish_t = None
        self.skill = 0.93
        self.mood = 1.0
        self.mood_t = 0.0
        self.lane_pref = 0.0
        self.tx = 0.0
        self.honk_cd = random.uniform(2, 6)
        self.img = None

    @property
    def z(self):
        return (LINE_Z + self.dist) % Car.L


def circ(dz, L):
    return ((dz + L / 2.0) % L) - L / 2.0


# ======================================================================
#  الواجهة (نصوص)
# ======================================================================
_shape_cache = {}


def shape_ar(s):
    r = _shape_cache.get(s)
    if r is None:
        try:
            r = get_display(arabic_reshaper.reshape(s))
        except Exception:
            r = s
        _shape_cache[s] = r
    return r


class UI:
    def __init__(self):
        self.fonts = {}
        self.cache = {}
        self.path = self._find_font()
        self.arabic_ok = HAS_BIDI and self.path is not None

    def _find_font(self):
        local = os.path.join(BASE_DIR, "font.ttf")
        if os.path.exists(local):
            return local
        for name in ("tahoma", "segoeui", "arial", "dejavusans", "notosansarabic", "notonaskharabic",
                     "geezapro", "almarai", "cairo", "amiri", "freesans", "liberationsans"):
            try:
                p = pygame.font.match_font(name)
            except Exception:
                p = None
            if p:
                return p
        return None

    def font(self, size):
        f = self.fonts.get(size)
        if f is None:
            f = pygame.font.Font(self.path, size) if self.path else pygame.font.Font(None, size + 6)
            self.fonts[size] = f
        return f

    def text(self, surf, s, size, x, y, color=(255, 255, 255), align="left", shadow=True):
        key = (s, size, color)
        pair = self.cache.get(key)
        if pair is None:
            if len(self.cache) > 600:
                self.cache.clear()
            f = self.font(size)
            pair = (f.render(s, True, color), f.render(s, True, (0, 0, 0)))
            self.cache[key] = pair
        img, sh = pair
        w, h = img.get_size()
        if align == "center":
            x -= w // 2
        elif align == "right":
            x -= w
        if shadow:
            surf.blit(sh, (x + 2, y + 2))
        surf.blit(img, (x, y))
        return pygame.Rect(x, y, w, h)


def panel(surf, rect, color=(0, 0, 0, 150), border=None):
    p = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    p.fill(color)
    surf.blit(p, (rect[0], rect[1]))
    if border:
        pygame.draw.rect(surf, border, rect, 2)


# ======================================================================
#  حفظ التقدم
# ======================================================================
def load_save():
    d = dict(money=START_MONEY, owned=[0], selected=0, wins=0, races=0, lang=None, sound=True)
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    if 0 not in d["owned"]:
        d["owned"].append(0)
    if d["selected"] not in d["owned"]:
        d["selected"] = 0
    return d


def write_save(d):
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# ======================================================================
#  اللعبة
# ======================================================================
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("TURBO RUSH 10")
        flags = (pygame.RESIZABLE | pygame.SCALED) if hasattr(pygame, "SCALED") else 0
        try:
            self.screen = pygame.display.set_mode((SW, SH), flags)
        except Exception:
            self.screen = pygame.display.set_mode((SW, SH))
        self.low = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.save = load_save()
        self.audio = Audio()
        self.audio.muted = not self.save.get("sound", True)
        self.ui = UI()
        lang = self.save.get("lang") or ("ar" if self.ui.arabic_ok else "en")
        if lang == "ar" and not self.ui.arabic_ok:
            lang = "en"
        self.lang = lang
        self.assets = build_assets()
        self.car_imgs = [[make_car(m, False), make_car(m, True)] for m in CARS]
        self.state = "menu"
        self.menu_i = 0
        self.shop_i = self.save["selected"]
        self.shop_msg = ""
        self.shop_msg_t = 0.0
        self.demo_z = 0.0
        self.zoom_t = 1.0
        self.zoom = 1.0
        self.bg_scroll = 0.0
        self.shake = 0.0
        self.hit_cd = 0.0
        self.parts = []
        self.honking = False
        self.cars = []
        self.player = None
        self.order = []
        self.finish_order = []
        self.race_time = 0.0
        self.hint_t = 12.0
        self.new_world()

    # ---------- النصوص ----------
    def T(self, key, **kw):
        s = STR[self.lang][key]
        if kw:
            s = s.format(**kw)
        return shape_ar(s) if self.lang == "ar" else s

    def car_name(self, mi):
        s = CARS[mi]["ar" if self.lang == "ar" else "en"]
        return shape_ar(s) if self.lang == "ar" else s

    def pname(self, c):
        if c.is_player:
            return self.T("you")
        s = c.name_pair[1 if self.lang == "ar" else 0]
        return shape_ar(s) if self.lang == "ar" else s

    # ---------- العالم ----------
    def new_world(self):
        theme = random.choice(THEMES)
        rng = random.Random(random.randint(0, 10 ** 6))
        segs = build_track(self.assets, theme, rng)
        self.R = Renderer(segs, theme)
        Car.L = float(self.R.L)
        self.L = float(self.R.L)

    def start_race(self):
        self.new_world()
        pm = self.save["selected"]
        others = [i for i in range(len(CARS)) if i != pm]
        random.shuffle(others)
        names = random.sample(AI_NAMES, N_CARS - 1)
        player = Car(pm, ("YOU", "أنت"), True)
        self.player = player
        ais = []
        for k in range(N_CARS - 1):
            c = Car(others[k], names[k])
            c.skill = random.uniform(0.92, 1.01)
            c.top = REF_MAX * c.skill
            c.acc = random.uniform(0.95, 1.1)
            c.hnd = 1.0
            c.lane_pref = random.choice((-0.55, -0.25, 0.0, 0.25, 0.55))
            ais.append(c)
        pslot = random.randint(5, 9)
        slots = [s for s in range(N_CARS) if s != pslot]
        random.shuffle(slots)
        grid = {pslot: player}
        for s, c in zip(slots, ais):
            grid[s] = c
        for s, c in grid.items():
            row, col = s // 2, s % 2
            c.dist = -(300.0 + row * 650.0)
            c.x = -0.38 if col == 0 else 0.38
            c.tx = c.x
            c.speed = 0.0
            c.finish_t = None
            c.img = self.car_imgs[c.mi][0]
        self.ais = ais
        self.cars = [player] + ais
        self.finish_order = []
        self.race_time = 0.0
        self.cd = 3.0
        self.cd_last = 4
        self.go_flash = 0.0
        self.fin_timer = 0.0
        self.prize_won = 0
        self.final_place = 0
        self.final_order = []
        self.hit_cd = 0.0
        self.shake = 0.0
        self.parts = []
        self.hint_t = 12.0
        self.zoom = self.zoom_t
        self.bg_scroll = 0.0
        self.honking = False
        self.state = "countdown"

    # ---------- الترتيب ----------
    def standings(self):
        fin = list(self.finish_order)
        rest = sorted([c for c in self.cars if c not in fin], key=lambda c: -c.dist)
        return fin + rest

    # ---------- الإدخال ----------
    def read_keys(self):
        k = pygame.key.get_pressed()
        return dict(up=k[pygame.K_UP] or k[pygame.K_w],
                    down=k[pygame.K_DOWN] or k[pygame.K_s],
                    left=k[pygame.K_LEFT] or k[pygame.K_a],
                    right=k[pygame.K_RIGHT] or k[pygame.K_d])

    def quit(self):
        self.save["sound"] = not self.audio.muted
        self.save["lang"] = self.lang
        write_save(self.save)
        pygame.quit()
        sys.exit(0)

    def set_zoom(self, v):
        self.zoom_t = clamp(v, 0.55, 1.9)

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.quit()
        if e.type == getattr(pygame, "MOUSEWHEEL", -1) and self.state in ("race", "countdown", "finish"):
            self.set_zoom(self.zoom_t - e.y * 0.08)
        if e.type == pygame.KEYUP:
            if e.key in (pygame.K_SPACE, pygame.K_h):
                k = pygame.key.get_pressed()
                if not (k[pygame.K_SPACE] or k[pygame.K_h]):
                    self.honking = False
                    self.audio.horn(False)
        if e.type != pygame.KEYDOWN:
            return
        key = e.key
        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        if key == pygame.K_m:
            self.audio.toggle_mute()
        st = self.state
        if st == "menu":
            items = self.menu_items()
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_i = (self.menu_i - 1) % len(items)
                self.audio.ui("click")
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_i = (self.menu_i + 1) % len(items)
                self.audio.ui("click")
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.audio.ui("click")
                self.menu_select(items[self.menu_i])
            elif key == pygame.K_ESCAPE:
                self.quit()
        elif st == "shop":
            if key in (pygame.K_LEFT, pygame.K_a):
                self.shop_i = (self.shop_i - 1) % len(CARS)
                self.audio.ui("click")
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.shop_i = (self.shop_i + 1) % len(CARS)
                self.audio.ui("click")
            elif key in (pygame.K_UP, pygame.K_w):
                self.shop_i = (self.shop_i - 5) % len(CARS)
                self.audio.ui("click")
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.shop_i = (self.shop_i + 5) % len(CARS)
                self.audio.ui("click")
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.shop_action()
            elif key == pygame.K_ESCAPE:
                self.state = "menu"
                self.audio.ui("click")
        elif st in ("race", "countdown", "finish"):
            if key in (pygame.K_SPACE, pygame.K_h):
                self.honking = True
                self.audio.horn(True)
            elif key in (pygame.K_q, pygame.K_MINUS, pygame.K_KP_MINUS):
                self.set_zoom(self.zoom_t - 0.12)         # تقريب
            elif key in (pygame.K_e, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.set_zoom(self.zoom_t + 0.12)         # إبعاد
            elif key == pygame.K_c:
                presets = [0.7, 1.0, 1.45]
                nxt = min([p for p in presets if p > self.zoom_t + 0.05] or [presets[0]])
                self.set_zoom(nxt)
            elif key in (pygame.K_p, pygame.K_ESCAPE) and st != "finish":
                self.prev_state = st
                self.state = "paused"
                self.audio.stop_engine()
        elif st == "paused":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_p, pygame.K_ESCAPE):
                self.state = self.prev_state
            elif key == pygame.K_BACKSPACE:
                self.audio.stop_engine()
                self.state = "menu"
        elif st == "results":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.state = "menu"
                self.audio.ui("click")
            elif key == pygame.K_r:
                self.start_race()

    def menu_items(self):
        items = ["start", "shop"]
        if self.ui.arabic_ok:
            items.append("lang")
        items += ["sound", "quit"]
        return items

    def menu_select(self, it):
        if it == "start":
            self.start_race()
        elif it == "shop":
            self.shop_i = self.save["selected"]
            self.shop_msg = ""
            self.state = "shop"
        elif it == "lang":
            self.lang = "en" if self.lang == "ar" else "ar"
            self.save["lang"] = self.lang
            write_save(self.save)
        elif it == "sound":
            self.audio.toggle_mute()
            self.save["sound"] = not self.audio.muted
            write_save(self.save)
        elif it == "quit":
            self.quit()

    def shop_action(self):
        i = self.shop_i
        m = CARS[i]
        s = self.save
        if i in s["owned"]:
            s["selected"] = i
            self.shop_msg = self.T("selected")
            self.audio.ui("click")
        elif s["money"] >= m["price"]:
            s["money"] -= m["price"]
            s["owned"].append(i)
            s["selected"] = i
            self.shop_msg = self.T("bought")
            self.audio.ui("buy")
        else:
            self.shop_msg = self.T("not_enough")
            self.audio.ui("err")
        self.shop_msg_t = 2.0
        write_save(s)

    # ==================================================================
    #  التحديث
    # ==================================================================
    def update(self, dt):
        self.zoom += (self.zoom_t - self.zoom) * min(1.0, dt * 6.0)
        self.shop_msg_t = max(0.0, self.shop_msg_t - dt)
        st = self.state
        if st == "menu" or st == "shop":
            self.demo_z = (self.demo_z + dt * 7000.0) % self.L
            self.bg_scroll += dt * 12.0
        elif st == "countdown":
            self.update_countdown(dt)
        elif st in ("race", "finish"):
            self.update_race(dt)
        if st == "results":
            self.demo_z = (self.demo_z + dt * 3000.0) % self.L

    def update_countdown(self, dt):
        self.cd -= dt
        n = int(math.ceil(self.cd))
        if n != self.cd_last and n >= 1:
            self.audio.ui("beep")
        self.cd_last = n
        k = self.read_keys()
        self.order = self.standings()
        self.audio.engine(0.25 + (0.45 if k["up"] else 0.0), 1.0 if k["up"] else 0.2)
        self.hint_t -= dt
        if self.cd <= 0:
            self.state = "race"
            self.go_flash = 1.2
            self.audio.ui("go")

    def update_race(self, dt):
        p = self.player
        L = self.L
        k = self.read_keys()
        racing = self.state == "race"
        self.race_time += dt
        self.hint_t -= dt
        self.go_flash = max(0.0, self.go_flash - dt)
        self.shake = max(0.0, self.shake - dt)
        self.hit_cd = max(0.0, self.hit_cd - dt)

        # ----- فيزياء اللاعب -----
        seg = self.R.find(p.z)
        sp = p.speed / REF_MAX
        up = k["up"] and racing
        dn = k["down"] and racing
        lf = k["left"] and racing
        rt = k["right"] and racing
        if up:
            p.speed += REF_MAX / 4.5 * p.acc * dt
        elif dn:
            p.speed -= REF_MAX * 0.95 * dt
        else:
            p.speed -= REF_MAX / 6.0 * dt
        if not racing:                       # بعد خط النهاية: تباطؤ تلقائي وتوسيط
            if p.speed > REF_MAX * 0.30:
                p.speed -= REF_MAX * 0.10 * dt
            p.x -= p.x * dt * 1.5
        steer = (1 if rt else 0) - (1 if lf else 0)
        self.steer_vis = steer
        if p.speed > 60:
            p.x += steer * dt * 2.6 * p.hnd * (0.30 + 0.70 * min(1.0, sp * 1.25))
        p.x -= dt * 2.0 * sp * sp * seg.curve * CENTRIF
        off = abs(p.x) > 1.0
        if off and p.speed > REF_MAX * 0.25:
            p.speed -= REF_MAX / 2.2 * dt
        # اصطدام بعناصر جانب الطريق
        if abs(p.x) > 1.12 and self.hit_cd <= 0:
            for (_img, o, wf, solid) in seg.sprites:
                if solid and abs(p.x - o) < wf * 0.42 + CAR_W * 0.35:
                    p.speed = min(p.speed, REF_MAX * 0.10)
                    p.x -= (1 if p.x > 0 else -1) * 0.30
                    self.hit_cd = 0.8
                    self.shake = 0.35
                    self.audio.crash_snd(0.9)
                    break
        p.x = clamp(p.x, -2.4, 2.4)
        p.speed = clamp(p.speed, 0.0, p.top)
        p.dist += p.speed * dt

        # ----- الذكاء الاصطناعي -----
        for c in self.ais:
            self.update_ai(c, dt)
        self.collide()

        # ----- النهاية -----
        total = LAPS * L
        for c in self.cars:
            if c.finish_t is None and c.dist >= total:
                c.finish_t = self.race_time
                self.finish_order.append(c)
                if c is p:
                    self.on_player_finish()
        self.order = self.standings()
        if self.state == "finish":
            self.fin_timer += dt
            for c in self.ais:
                if c.finish_t is not None:
                    c.speed = max(c.speed - REF_MAX * 0.08 * dt, REF_MAX * 0.35)
            if self.fin_timer > 4.0:
                self.final_order = self.standings()
                self.state = "results"
                self.audio.stop_engine()
                self.audio.ui("win" if self.final_place == 1 else "lose")

        # ----- الصوت والمؤثرات -----
        sp = p.speed / max(1.0, p.top)
        g = min(4, int(sp * 5))
        frac = min(1.0, sp * 5 - g)
        rpm = 0.22 + 0.70 * frac + 0.04 * g
        thr = 1.0 if up else 0.0
        if not up:
            rpm *= 0.88
        self.audio.engine(rpm, thr)
        self.audio.set_wind(sp * sp)
        self.audio.set_offroad(off and p.speed > 300, p.speed / REF_MAX)
        if off and p.speed > REF_MAX * 0.1:
            rx, ry, rw = self.R.player_rect
            for _ in range(2):
                self.parts.append([rx + random.randint(-rw // 3, rw // 3), ry - 1,
                                   random.uniform(-25, 25), random.uniform(-60, -15), 0.5,
                                   mix(self.R.theme["grass"][0], (160, 130, 90), 0.5)])
        # الخلفية تتحرك مع المنعطف
        self.bg_scroll += seg.curve * (p.speed / REF_MAX) * dt * 45.0

    def on_player_finish(self):
        place = len(self.finish_order)
        self.final_place = place
        self.save["races"] = self.save.get("races", 0) + 1
        if place == 1:
            self.save["money"] += PRIZE
            self.save["wins"] = self.save.get("wins", 0) + 1
            self.prize_won = PRIZE
        write_save(self.save)
        self.state = "finish"
        self.fin_timer = 0.0
        self.honking = False
        self.audio.horn(False)

    def update_ai(self, c, dt):
        L = self.L
        p = self.player
        seg = self.R.find(c.z)
        finished = c.finish_t is not None
        if finished:
            c.dist += c.speed * dt
            return
        # مزاج متغير لإعطاء سلوك طبيعي
        c.mood_t -= dt
        if c.mood_t <= 0:
            c.mood = random.uniform(0.965, 1.02)
            c.mood_t = random.uniform(3.0, 6.0)
        diff = (c.dist - p.dist) / L
        rb = 1.0 + clamp(-diff * 0.35, -0.03, 0.06)          # توازن السباق (Rubber banding)
        curve_pen = 1.0 - min(0.22, abs(seg.curve) * 0.022)
        target = c.top * curve_pen * rb * c.mood
        # البحث عن عائق أمامي
        block = None
        best = 1e9
        for o in self.cars:
            if o is c:
                continue
            dz = circ(o.z - c.z, L)
            if 0 < dz < 1500 and abs(o.x - c.x) < 0.5 and dz < best:
                best = dz
                block = o
        if block is not None:
            side = 1 if c.x < block.x else -1
            tx = block.x + side * 0.62
            if abs(tx) > 0.85:
                side = -side
                tx = block.x + side * 0.62
            c.tx = clamp(tx, -0.85, 0.85)
            if best < 450 and abs(block.x - c.x) < 0.38:
                target = min(target, block.speed * 0.97)
        else:
            c.tx = c.lane_pref
        step = dt * 1.1
        c.x += clamp(c.tx - c.x, -step, step)
        c.x = clamp(c.x, -0.9, 0.9)
        if c.speed < target:
            c.speed = min(target, c.speed + REF_MAX / 4.5 * c.acc * dt)
        else:
            c.speed = max(target, c.speed - REF_MAX / 3.0 * dt)
        c.dist += c.speed * dt
        # كلاكس السيارات الخلفية
        c.honk_cd -= dt
        if c.honk_cd <= 0:
            dz = circ(p.z - c.z, L)
            if 0 < dz < 900 and abs(p.x - c.x) < 0.45 and self.state == "race":
                self.audio.honk_ai(1.0 - dz / 1000.0)
                c.honk_cd = random.uniform(3, 7)
            else:
                c.honk_cd = random.uniform(0.5, 1.5)

    def collide(self):
        L = self.L
        cars = self.cars
        p = self.player
        n = len(cars)
        for i in range(n):
            a = cars[i]
            for j in range(i + 1, n):
                b = cars[j]
                dz = circ(b.z - a.z, L)
                if abs(dz) >= CAR_LEN:
                    continue
                dx = b.x - a.x
                if abs(dx) >= CAR_HIT_X:
                    continue
                rear, front = (a, b) if dz > 0 else (b, a)
                rel = abs(rear.speed - front.speed)
                rear.speed = min(rear.speed, front.speed * 0.92)
                rear.dist -= (CAR_LEN - abs(dz)) * 0.5
                sgn = 1 if dx >= 0 else -1
                push = (CAR_HIT_X - abs(dx)) * 0.5 + 0.01
                lim = 1.2 if (a.is_player or b.is_player) else 0.9
                a.x = clamp(a.x - sgn * push, -lim, lim)
                b.x = clamp(b.x + sgn * push, -lim, lim)
                if (a is p or b is p) and self.hit_cd <= 0:
                    self.hit_cd = 0.5
                    self.shake = 0.25
                    self.audio.crash_snd(0.35 + rel / REF_MAX)

    # ==================================================================
    #  الرسم
    # ==================================================================
    def draw(self):
        st = self.state
        if st in ("menu", "shop", "results"):
            self.draw_demo()
        else:
            self.draw_world()
        # تكبير الصورة الصغيرة لشكل البكسل آرت
        ox = oy = 0
        if self.shake > 0 and st in ("race", "finish", "paused"):
            ox = random.randint(-4, 4)
            oy = random.randint(-4, 4)
        self.screen.fill((0, 0, 0))
        if ox or oy:
            tmp = pygame.transform.scale(self.low, (SW, SH))
            self.screen.blit(tmp, (ox, oy))
        else:
            pygame.transform.scale(self.low, (SW, SH), self.screen)
        if st == "menu":
            self.draw_menu()
        elif st == "shop":
            self.draw_shop()
        elif st in ("countdown", "race", "finish", "paused"):
            self.draw_hud()
            if st == "paused":
                self.draw_pause()
        elif st == "results":
            self.draw_results()

    def draw_demo(self):
        z = self.demo_z
        cam_h = 1000.0
        pz = cam_h * BASE_DEPTH
        cx = 0.35 * math.sin(z / 2600.0)
        img = self.car_imgs[self.save["selected"]][0]
        pinfo = dict(img=img, dx=int(cx * 6), dy=0)
        self.R.draw(self.low, z, cx, cam_h, BASE_DEPTH, pz, [], pinfo, self.bg_scroll)

    def draw_world(self):
        p = self.player
        sp = clamp(p.speed / REF_MAX, 0.0, 1.3)
        cam_h = 1000.0 * self.zoom
        fov = BASE_FOV + 7.0 * min(1.0, sp) ** 2          # المنظور يتسع مع السرعة
        depth = 1.0 / math.tan(math.radians(fov / 2.0))
        pz = cam_h * BASE_DEPTH
        self.cur_fov = fov
        braking = self.read_keys()["down"] and self.state == "race" and p.speed > 200
        img = self.car_imgs[p.mi][1 if braking else 0]
        bounce = 0
        if p.speed > 300 and random.random() < 0.5:
            bounce = 1
        steer = getattr(self, "steer_vis", 0)
        pinfo = dict(img=img, dx=int(steer * 3 * min(1.0, sp * 2)), dy=bounce)
        p.img = img
        self.R.draw(self.low, p.z - pz, p.x, cam_h, depth, pz, self.ais, pinfo, self.bg_scroll)
        # غبار خارج الطريق
        dt = 1.0 / FPS
        alive = []
        for pt in self.parts:
            pt[0] += pt[2] * dt
            pt[1] += pt[3] * dt
            pt[3] += 120 * dt
            pt[4] -= dt
            if pt[4] > 0:
                self.low.fill(pt[5], (int(pt[0]), int(pt[1]), 2, 2))
                alive.append(pt)
        self.parts = alive[-80:]
        # خطوط السرعة
        if sp > 0.82:
            for _ in range(int((sp - 0.8) * 22)):
                xx = random.choice((random.randint(0, 55), random.randint(W - 55, W - 1)))
                yy = random.randint(HZ + 8, H - 10)
                ln = random.randint(5, 12)
                d = 1 if xx > W // 2 else -1
                pygame.draw.line(self.low, (225, 235, 255), (xx, yy), (xx + d * ln // 2, yy + ln))

    # ---------- القائمة ----------
    def draw_menu(self):
        scr = self.screen
        ui = self.ui
        panel(scr, (0, 0, SW, 150), (0, 0, 0, 110))
        ui.text(scr, "TURBO RUSH 10", 64, SW // 2, 22, (255, 220, 60), "center")
        ui.text(scr, self.T("subtitle"), 22, SW // 2, 96, (255, 255, 255), "center")
        items = self.menu_items()
        y0 = 190
        for i, it in enumerate(items):
            if it == "sound":
                key = "sound_off" if self.audio.muted else "sound_on"
            else:
                key = it
            sel = i == self.menu_i
            col = (255, 230, 80) if sel else (235, 235, 235)
            if sel:
                panel(scr, (SW // 2 - 190, y0 + i * 48 - 4, 380, 44), (0, 0, 0, 150), (255, 220, 60))
            ui.text(scr, self.T(key), 28, SW // 2, y0 + i * 48, col, "center")
        money = "{:,} {}".format(self.save["money"], self.T("cur"))
        ui.text(scr, money if self.lang == "en" else shape_ar(money), 22, SW - 16, 12, (255, 220, 60), "right")
        ui.text(scr, self.T("ctrl1"), 15, SW // 2, SH - 52, (255, 255, 255), "center")
        ui.text(scr, self.T("ctrl2"), 15, SW // 2, SH - 30, (255, 255, 255), "center")

    # ---------- المتجر ----------
    def draw_shop(self):
        scr = self.screen
        ui = self.ui
        scr.fill((20, 22, 38))
        for i in range(0, SH, 6):
            pygame.draw.line(scr, (24, 27, 46), (0, i), (SW, i))
        ui.text(scr, self.T("shop_title"), 40, SW // 2, 14, (255, 220, 60), "center")
        money = "{:,} {}".format(self.save["money"], self.T("cur"))
        panel(scr, (SW - 250, 14, 236, 40), (0, 0, 0, 160), (255, 220, 60))
        ui.text(scr, money if self.lang == "en" else shape_ar(money), 24, SW - 26, 20, (255, 220, 60), "right")
        i = self.shop_i
        m = CARS[i]
        owned = i in self.save["owned"]
        img = self.car_imgs[i][0]
        bw, bh = img.get_width() * 7, img.get_height() * 7
        big = pygame.transform.scale(img, (bw, bh))
        cx = 300
        pygame.draw.rect(scr, (34, 38, 64), (cx - 180, 100, 360, 210), 0)
        pygame.draw.rect(scr, (60, 66, 100), (cx - 180, 100, 360, 210), 3)
        pygame.draw.ellipse(scr, (14, 14, 24), (cx - bw // 2 - 6, 100 + 105 + bh // 2 - 24, bw + 12, 30))
        scr.blit(big, (cx - bw // 2, 100 + 105 - bh // 2 - 6))
        ui.text(scr, self.car_name(i), 32, cx, 62, (255, 255, 255), "center")
        # حالة السيارة
        if self.save["selected"] == i:
            status, col = self.T("equipped"), (110, 255, 130)
        elif owned:
            status, col = self.T("owned"), (140, 220, 255)
        else:
            pr = "{:,} {}".format(m["price"], self.T("cur"))
            status = (pr if self.lang == "en" else shape_ar(pr))
            col = (255, 220, 60) if self.save["money"] >= m["price"] else (255, 110, 110)
        ui.text(scr, status, 26, cx, 314, col, "center")
        # الإحصائيات
        sx, sy = 600, 110
        panel(scr, (sx - 20, sy - 14, 360, 190), (0, 0, 0, 150), (60, 66, 100))
        stats = [("top", m["top"], 0.90, 1.25, (255, 120, 90)),
                 ("accel", m["acc"], 0.85, 1.30, (255, 210, 80)),
                 ("handling", m["hnd"], 0.95, 1.20, (110, 220, 255))]
        for k, (key, v, lo, hi, col2) in enumerate(stats):
            yy = sy + k * 56
            ui.text(scr, self.T(key), 20, sx, yy, (255, 255, 255))
            pygame.draw.rect(scr, (50, 54, 80), (sx, yy + 28, 320, 14))
            pygame.draw.rect(scr, col2, (sx, yy + 28, int(320 * clamp((v - lo) / (hi - lo), 0.05, 1.0)), 14))
        kmh = int(m["top"] * 240)
        ui.text(scr, "{} {}".format(kmh, self.T("kmh")), 18, sx + 320, sy - 4, (200, 200, 220), "right")
        # الشبكة السفلية
        cw, ch, gap = 170, 78, 8
        gx0 = (SW - (5 * cw + 4 * gap)) // 2
        for k in range(len(CARS)):
            r, c = k // 5, k % 5
            rx = gx0 + c * (cw + gap)
            ry = 372 + r * (ch + gap)
            sel = k == i
            panel(scr, (rx, ry, cw, ch), (0, 0, 0, 150), (255, 220, 60) if sel else (60, 66, 100))
            im = self.car_imgs[k][0]
            sm = pygame.transform.scale(im, (im.get_width() * 2, im.get_height() * 2))
            if k not in self.save["owned"]:
                dark = pygame.Surface(sm.get_size(), pygame.SRCALPHA)
                dark.fill((0, 0, 0, 120))
                sm.blit(dark, (0, 0))
            scr.blit(sm, (rx + 8, ry + ch // 2 - sm.get_height() // 2))
            if self.save["selected"] == k:
                tag, tcol = "OK", (110, 255, 130)
            elif k in self.save["owned"]:
                tag, tcol = "*", (140, 220, 255)
            else:
                tag, tcol = "${:,}".format(CARS[k]["price"]), (255, 220, 60)
            ui.text(scr, tag, 17, rx + cw - 8, ry + 8, tcol, "right")
            ui.text(scr, str(k + 1), 15, rx + cw - 8, ry + ch - 24, (180, 180, 200), "right")
        # الرسائل والتلميحات
        if self.save["selected"] == i:
            action = self.T("equipped")
        else:
            action = self.T("equip") if owned else self.T("buy")
        ui.text(scr, action + "  [Enter]" if self.lang == "en" else "[Enter]  " + action,
                18, cx, 346, (255, 255, 255), "center")
        if self.shop_msg_t > 0:
            ui.text(scr, self.shop_msg, 26, SW // 2, SH - 60, (255, 255, 120), "center")
        ui.text(scr, self.T("shop_hint"), 16, SW // 2, SH - 24, (200, 200, 220), "center")

    # ---------- الواجهة أثناء السباق ----------
    def draw_hud(self):
        scr = self.screen
        ui = self.ui
        p = self.player
        order = self.order if self.order else self.cars
        # لوحة الترتيب (1 → 10)
        panel(scr, (10, 10, 214, 248), (0, 0, 0, 150), (255, 255, 255))
        ui.text(scr, self.T("standings"), 17, 117, 14, (255, 220, 60), "center")
        for r, c in enumerate(order):
            yy = 40 + r * 21
            if c is p:
                pygame.draw.rect(scr, (255, 214, 60), (14, yy - 1, 206, 20))
            tc = (20, 20, 20) if c is p else (255, 255, 255)
            ui.text(scr, str(r + 1), 16, 24, yy, tc, shadow=False)
            pygame.draw.rect(scr, c.m["body"], (46, yy + 3, 14, 12))
            pygame.draw.rect(scr, (0, 0, 0), (46, yy + 3, 14, 12), 1)
            ui.text(scr, self.pname(c), 16, 68, yy, tc, shadow=False)
            if c.finish_t is not None:
                ui.text(scr, "F", 15, 212, yy, (30, 140, 40) if c is p else (110, 255, 130), "right", shadow=False)
        # اللفة والمركز
        place = (order.index(p) + 1) if p in order else 1
        lap = clamp(int(max(p.dist, 0) // self.L) + 1, 1, LAPS)
        if p.finish_t is not None:
            lap = LAPS
        ui.text(scr, self.T("lap", a=lap, b=LAPS), 22, SW // 2, 10, (255, 255, 255), "center")
        ui.text(scr, "{}/{}".format(place, N_CARS), 52, SW // 2, 32, (255, 220, 60), "center")
        # شريط تقدم السباق
        bx, by, bw = SW // 2 - 150, 100, 300
        pygame.draw.rect(scr, (0, 0, 0), (bx - 2, by - 2, bw + 4, 12))
        pygame.draw.rect(scr, (60, 64, 80), (bx, by, bw, 8))
        total = LAPS * self.L
        for c in self.cars:
            if c is p:
                continue
            fx = bx + int(bw * clamp(c.dist, 0, total) / total)
            pygame.draw.rect(scr, c.m["body"], (fx - 3, by - 1, 6, 10))
        fx = bx + int(bw * clamp(p.dist, 0, total) / total)
        pygame.draw.rect(scr, (255, 255, 255), (fx - 5, by - 3, 10, 14))
        pygame.draw.rect(scr, (255, 214, 60), (fx - 4, by - 2, 8, 12))
        # المال
        money = "{:,} {}".format(self.save["money"], self.T("cur"))
        panel(scr, (SW - 220, 10, 210, 58), (0, 0, 0, 150), (255, 214, 60))
        ui.text(scr, self.T("money"), 14, SW - 210, 14, (200, 200, 200))
        ui.text(scr, money if self.lang == "en" else shape_ar(money), 28, SW - 20, 30, (255, 220, 60), "right")
        # السرعة
        kmh = int(p.speed / REF_MAX * 240)
        panel(scr, (SW - 250, SH - 96, 240, 86), (0, 0, 0, 150), (255, 255, 255))
        ui.text(scr, str(kmh), 52, SW - 150, SH - 94, (255, 255, 255), "right")
        ui.text(scr, self.T("kmh"), 20, SW - 144, SH - 62, (200, 200, 220))
        ui.text(scr, self.T("speed"), 14, SW - 240, SH - 92, (200, 200, 200))
        cells = 24
        frac = clamp(p.speed / max(1.0, p.top), 0, 1)
        for k in range(cells):
            on = (k + 1) / float(cells) <= frac + 0.001
            col = mix((60, 220, 90), (255, 60, 40), k / float(cells - 1)) if on else (50, 54, 70)
            pygame.draw.rect(scr, col, (SW - 240 + k * 9, SH - 28, 7, 12))
        # حالة الكاميرا / المنظور
        zl = self.zoom
        cam_key = "cam_0" if zl < 0.85 else ("cam_1" if zl < 1.25 else "cam_2")
        fov = getattr(self, "cur_fov", BASE_FOV)
        line = "{}: {}   x{:.2f}   {} {:.0f}".format(self.T("camera"), self.T(cam_key), zl, self.T("fov"), fov)
        if self.lang == "ar":
            line = shape_ar("{}: {}   x{:.2f}   {} {:.0f}".format(STR["ar"]["camera"], STR["ar"][cam_key], zl, STR["ar"]["fov"], fov))
        panel(scr, (10, SH - 34, 400, 26), (0, 0, 0, 150))
        ui.text(scr, line, 16, 18, SH - 31, (200, 235, 255))
        if self.hint_t > 0:
            ui.text(scr, self.T("ctrl1"), 15, 18, SH - 82, (255, 255, 255))
            ui.text(scr, self.T("ctrl2"), 15, 18, SH - 60, (255, 255, 255))
        if self.honking:
            ui.text(scr, self.T("honk"), 30, SW // 2, SH - 150, (255, 230, 60), "center")
        # رسائل المنتصف
        if self.state == "countdown":
            n = int(math.ceil(self.cd))
            if n >= 1:
                ui.text(scr, str(n), 150, SW // 2, 130, (255, 230, 60), "center")
        elif self.state == "race" and self.go_flash > 0:
            ui.text(scr, self.T("go"), 130, SW // 2, 140, (110, 255, 130), "center")
        elif self.state == "finish":
            ui.text(scr, self.T("finish"), 90, SW // 2, 150, (255, 255, 255), "center")
            ui.text(scr, "{}/{}".format(self.final_place, N_CARS), 70, SW // 2, 250, (255, 220, 60), "center")
            if self.prize_won:
                ui.text(scr, self.T("prize", n="{:,}".format(self.prize_won)), 40, SW // 2, 340, (110, 255, 130), "center")

    def draw_pause(self):
        panel(self.screen, (0, 0, SW, SH), (0, 0, 0, 150))
        self.ui.text(self.screen, self.T("paused"), 72, SW // 2, 190, (255, 220, 60), "center")
        self.ui.text(self.screen, self.T("paused_hint"), 24, SW // 2, 290, (255, 255, 255), "center")

    def draw_results(self):
        scr = self.screen
        ui = self.ui
        panel(scr, (0, 0, SW, SH), (0, 0, 0, 170))
        ui.text(scr, self.T("results"), 44, SW // 2, 14, (255, 220, 60), "center")
        order = self.final_order or self.cars
        for r, c in enumerate(order):
            yy = 74 + r * 28
            col = (255, 214, 60) if c.is_player else (255, 255, 255)
            if c.is_player:
                pygame.draw.rect(scr, (90, 74, 10), (SW // 2 - 230, yy - 2, 460, 26))
            ui.text(scr, str(r + 1), 20, SW // 2 - 210, yy, col)
            pygame.draw.rect(scr, c.m["body"], (SW // 2 - 160, yy + 4, 18, 14))
            pygame.draw.rect(scr, (0, 0, 0), (SW // 2 - 160, yy + 4, 18, 14), 1)
            ui.text(scr, self.pname(c), 20, SW // 2 - 128, yy, col)
            ui.text(scr, self.car_name(c.mi), 16, SW // 2 + 220, yy + 3, (190, 190, 210), "right")
        if self.final_place == 1:
            ui.text(scr, self.T("win"), 34, SW // 2, 366, (110, 255, 130), "center")
            ui.text(scr, self.T("prize", n="{:,}".format(self.prize_won)), 34, SW // 2, 408, (255, 220, 60), "center")
        else:
            ui.text(scr, self.T("lose", n=self.final_place), 28, SW // 2, 380, (255, 150, 120), "center")
        money = "{:,} {}".format(self.save["money"], self.T("cur"))
        ui.text(scr, "{}: {}".format(self.T("money"), money) if self.lang == "en" else shape_ar("{}: {}".format(STR["ar"]["money"], money)),
                22, SW // 2, 452, (255, 255, 255), "center")
        ui.text(scr, self.T("enter_menu"), 22, SW // 2, SH - 40, (200, 220, 255), "center")

    # ==================================================================
    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main():
    Game().run()


if __name__ == "__main__":
    main()