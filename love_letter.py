"""
For Ella - a vintage animated love letter (Part 1 + Part 2 + mini music player)

Run:   python love_letter.py
Needs: pip install pillow numpy pygame     (tkinter ships with Python on Windows/macOS;
                                      on Linux: sudo apt install python3-tk)
Keep the 'assets' folder next to this file. It needs:
    letter.png, cat1.png ... cat6.png          (from Part 1)
    paper.png, photo.png, flowers.png,
    butterfly.png, candle.png                  (new, cut from your design sheet)

Runs FULLSCREEN.  Click the letter to open it.  Click anywhere else for hearts.
Press Esc (or Q) to quit.

Music: put your MP3 in the 'assets' folder (or next to this file) and set MUSIC_FILE
below. It starts automatically and loops until the app is closed. The little record
player (bottom-left) can pause / resume it.   Needs:  pip install pygame
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

W, H = 1280, 720          # logical canvas (W is adapted to your screen at launch)
FPS = 30

# ---- words you can edit ------------------------------------------------------
TEXT = "HAPPY BIRTHDAY"
SUBTITLE = "~ FOR ELLA ~"
HINT = "~ click the letter to open it ~"

GREETING = "My dearest Ella,"
BODY = ("Happy birthday.\n\n"
        "The best things in life, like the old and beautiful ones we love, "
        "only grow softer and more precious with time. That is how I feel about you.\n\n"
        "Thank you for every quiet moment and every laugh in between.")
SIGN = "Forever yours"

KEEP_CATS = False         # True = cats keep floating in the back after the letter opens

MUSIC_FILE = "music.mp3"  # your MP3 (looked up in 'assets' or next to this file)
MUSIC_VOLUME = 0.5        # 0.0 - 1.0
MUSIC_LABEL = "Paraluman - Adie"  # small text shown on the player

# ---- vintage palette -------------------------------------------------------
INK = (92, 54, 38)
INK_SOFT = (140, 100, 74)
GOLD = (176, 132, 62)
WAX = (160, 40, 40)
PARCHMENT = (240, 215, 168)
WALNUT = (84, 55, 40)

SCRIPT_FONTS = [
    "Monotype Corsiva", "Apple Chancery", "Segoe Script", "Lucida Handwriting",
    "Edwardian Script ITC", "Palace Script MT", "Brush Script MT",
    "Snell Roundhand", "URW Chancery L", "Z003", "Georgia", "Palatino Linotype",
    "Times New Roman",
]


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out_back(x):
    x = clamp01(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out_cubic(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


# ---- background ------------------------------------------------------------
def make_background(dark=False):
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    d = np.sqrt(((xx - cx) / (W / 2)) ** 2 + ((yy - cy) / (H / 2)) ** 2)

    base = np.zeros((H, W, 3), np.float32)
    base[...] = WALNUT if dark else PARCHMENT          # aged parchment / old walnut
    base *= (1.06 - 0.30 * np.clip(d - 0.35, 0, 1.2) ** 1.6)[..., None]  # vignette

    # mottled stains + fine grain
    blotch = Image.fromarray((rng.random((H // 40 + 1, W // 40 + 1)) * 255).astype("uint8"))
    blotch = np.asarray(blotch.resize((W, H), Image.BICUBIC), np.float32) / 255
    base *= (0.93 + 0.12 * blotch)[..., None]
    base += rng.normal(0, 4.5, (H, W, 1))
    # faint fibres
    fib = Image.new("L", (W, H), 0)
    fd = ImageDraw.Draw(fib)
    for _ in range(int(260 * W / 1100)):
        x, y = rng.integers(0, W), rng.integers(0, H)
        a = rng.random() * math.pi
        l = rng.integers(8, 30)
        fd.line([x, y, x + math.cos(a) * l, y + math.sin(a) * l], fill=int(rng.integers(20, 60)))
    fibv = np.asarray(fib.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 6
    base += (fibv if dark else -fibv)[..., None]

    img = Image.fromarray(np.clip(base, 0, 255).astype("uint8"), "RGB")

    # double-line border with corner ornaments
    dr = ImageDraw.Draw(img)
    m1, m2 = 22, 32
    line2 = (190, 150, 92) if dark else INK_SOFT
    dr.rectangle([m1, m1, W - m1, H - m1], outline=GOLD, width=3)
    dr.rectangle([m2, m2, W - m2, H - m2], outline=line2, width=1)
    for (x, y, sx, sy) in [(m2, m2, 1, 1), (W - m2, m2, -1, 1),
                           (m2, H - m2, 1, -1), (W - m2, H - m2, -1, -1)]:
        for r in (16, 10, 4):
            dr.arc([x + (r if sx > 0 else -r) - r,
                    y + (r if sy > 0 else -r) - r,
                    x + (r if sx > 0 else -r) + r,
                    y + (r if sy > 0 else -r) + r],
                   0, 360, fill=GOLD, width=1)
        dr.ellipse([x + sx * 16 - 3, y + sy * 16 - 3, x + sx * 16 + 3, y + sy * 16 + 3], fill=GOLD)
    return img


# ---- small drawn hearts / sparkles ----------------------------------------
def heart_sprite(size, color):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(120):
        t = i / 120 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((s / 2 + x * s / 38, s / 2 + y * s / 38 - s * 0.03))
    d.polygon(pts, fill=color + (255,))
    d.line(pts + [pts[0]], fill=(255, 245, 225, 120), width=max(2, s // 30))
    return im.resize((size, size), Image.LANCZOS)


def sparkle_sprite(size, color):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    d.polygon([(c, 0), (c + s * 0.09, c - s * 0.09), (s, c), (c + s * 0.09, c + s * 0.09),
               (c, s), (c - s * 0.09, c + s * 0.09), (0, c), (c - s * 0.09, c - s * 0.09)],
              fill=color + (255,))
    return im.resize((size, size), Image.LANCZOS)


def warm_glow(size, color=(255, 196, 112)):
    """Soft radial candle light."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt(((xx - size / 2) / (size / 2)) ** 2 + ((yy - size / 2) / (size / 2)) ** 2)
    a = np.clip(1 - r, 0, 1) ** 2.2
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = color
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def shadow_of(sprite, blur=8, opacity=95, color=(60, 35, 20)):
    pad = blur * 3
    a = Image.new("L", (sprite.width + pad * 2, sprite.height + pad * 2), 0)
    a.paste(sprite.getchannel("A"), (pad, pad))
    a = a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * opacity // 255)
    sh = Image.new("RGBA", a.size, color + (0,))
    sh.putalpha(a)
    return sh, pad


def with_alpha(sprite, k):
    if k >= 0.995:
        return sprite
    s = sprite.copy()
    s.putalpha(s.getchannel("A").point(lambda v: int(v * k)))
    return s


def clip_composite(canvas, sp, x, y):
    """alpha_composite that tolerates sprites hanging off the canvas edge."""
    x, y = int(x), int(y)
    l, t = max(0, x), max(0, y)
    r, b = min(canvas.width, x + sp.width), min(canvas.height, y + sp.height)
    if r <= l or b <= t:
        return
    canvas.alpha_composite(sp.crop((l - x, t - y, r - x, b - y)), (l, t))


def load_asset(name):
    path = os.path.join(ASSETS, name)
    if not os.path.exists(path):
        sys.exit(f"Missing asset: {path}\nKeep the 'assets' folder next to love_letter.py.")
    return Image.open(path).convert("RGBA")


def make_polaroid(photo, height):
    """Photo is only RESIZED - never retouched. A cream frame + tape is added around it."""
    pw = int(photo.width * height / photo.height)
    pic = photo.resize((pw, height), Image.LANCZOS)
    pad, bottom, top = 13, 42, 26
    fw, fh = pw + 2 * pad, height + pad + bottom
    rng = np.random.default_rng(3)
    arr = np.zeros((fh, fw, 4), np.float32)
    arr[..., :3] = (247, 240, 224)
    arr[..., 3] = 255
    arr[..., :3] += rng.normal(0, 3, (fh, fw, 1))
    frame = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"), "RGBA")
    frame.paste(pic, (pad, pad))
    d = ImageDraw.Draw(frame)
    d.rectangle([0, 0, fw - 1, fh - 1], outline=(205, 190, 160, 255), width=2)
    hs = heart_sprite(24, (170, 60, 60))
    frame.alpha_composite(hs, (fw // 2 - 12, height + pad + (bottom - 24) // 2))

    out = Image.new("RGBA", (fw, fh + top), (0, 0, 0, 0))
    out.alpha_composite(frame, (0, top))
    for cx_, ang in ((fw // 2, -4),):
        tape = Image.new("RGBA", (118, 34), (226, 205, 150, 175))
        td = ImageDraw.Draw(tape)
        for i in range(0, 34, 4):
            td.line([0, i, 118, i], fill=(210, 188, 134, 60))
        tape = tape.rotate(ang, expand=True, resample=Image.BICUBIC)
        out.alpha_composite(tape, (cx_ - tape.width // 2, top - tape.height // 2 + 4))
    return out


# ---- scene objects ---------------------------------------------------------
class Floater:
    """A cat sticker drifting around the letter."""

    def __init__(self, img, anchor, height, layer, delay, rng):
        self.base = img
        self.anchor = anchor
        self.layer = layer                    # 0 = behind letter, 1 = in front
        self.delay = delay
        self.h = height
        self.ph = [rng.uniform(0, 6.28) for _ in range(4)]
        self.sp = [rng.uniform(0.5, 1.1), rng.uniform(0.4, 0.9), rng.uniform(0.5, 0.9)]
        self.amp = (rng.uniform(14, 30), rng.uniform(14, 30))
        self.tilt = rng.uniform(7, 14) * rng.choice([-1, 1])
        self.cache = {}

    def _sprite(self, scale, ang):
        key = (round(scale * 40), round(ang / 2))
        if key not in self.cache:
            w = max(8, int(self.base.width * self.h / self.base.height * scale))
            h = max(8, int(self.h * scale))
            sp = self.base.resize((w, h), Image.LANCZOS).rotate(
                key[1] * 2, resample=Image.BICUBIC, expand=True)
            sh, pad = shadow_of(sp, 6, 90)
            self.cache[key] = (sp, sh, pad)
            if len(self.cache) > 400:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[key]

    def draw(self, canvas, t, vis=1.0):
        local = t - self.delay
        if local <= 0 or vis <= 0.02:
            return
        pop = ease_out_back(local / 0.9)
        x = self.anchor[0] + self.amp[0] * math.sin(t * self.sp[0] + self.ph[0])
        y = self.anchor[1] + self.amp[1] * math.sin(t * self.sp[1] + self.ph[1]) \
            + 6 * math.sin(t * 2.1 + self.ph[3])
        ang = self.tilt * math.sin(t * self.sp[2] + self.ph[2])
        scale = max(0.02, pop) * (1 + 0.03 * math.sin(t * 1.7 + self.ph[3])) * vis
        sp, sh, pad = self._sprite(max(0.03, scale), ang)
        clip_composite(canvas, sh, x - sh.width / 2 + 7, y - sh.height / 2 + 10)
        clip_composite(canvas, sp, x - sp.width / 2, y - sp.height / 2)


class Prop:
    """A decoration of the opened letter: enters with a bounce, then drifts gently."""

    def __init__(self, img, height, home, delay, enter=(0, 0), dur=1.1, drift=(0, 0),
                 tilt=0.0, base_ang=0.0, speed=1.0, flap=False, seed=0, ang_q=0.5):
        self.base, self.h, self.home, self.delay = img, height, home, delay
        self.enter, self.dur, self.drift = enter, dur, drift
        self.tilt, self.base_ang, self.speed, self.flap = tilt, base_ang, speed, flap
        self.ang_q = ang_q
        r = random.Random(seed)
        self.ph = [r.uniform(0, 6.28) for _ in range(4)]
        self.cache = {}
        self.rect = None           # (cx, cy, w, h) of last drawn sprite
        self.vis = 0.0

    def _sprite(self, scale, ang, fx):
        key = (round(scale * 40), round(ang / self.ang_q), round(fx * 6))
        if key not in self.cache:
            w = max(8, int(self.base.width * self.h / self.base.height * scale * (key[2] / 6)))
            h = max(8, int(self.h * scale))
            sp = self.base.resize((w, h), Image.LANCZOS).rotate(
                key[1] * self.ang_q, resample=Image.BICUBIC, expand=True)
            sh, pad = shadow_of(sp, 6, 95)
            self.cache[key] = (sp, sh)
            if len(self.cache) > 500:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[key]

    def draw(self, canvas, u):
        local = u - self.delay
        if local <= 0:
            return
        k = local / self.dur
        pop = ease_out_back(k)
        scale = 0.55 + 0.45 * ease_out_cubic(k)
        t = u * self.speed
        x = self.home[0] + self.enter[0] * (1 - pop) \
            + self.drift[0] * (math.sin(0.9 * t + self.ph[0]) + 0.3 * math.sin(2.3 * t + self.ph[1]))
        y = self.home[1] + self.enter[1] * (1 - pop) \
            + self.drift[1] * (math.sin(0.7 * t + self.ph[1]) + 0.3 * math.sin(1.9 * t + self.ph[2]))
        ang = self.base_ang + self.tilt * math.sin(1.1 * t + self.ph[2])
        fx = 1.0
        if self.flap:
            fx = 0.70 + 0.30 * abs(math.sin(u * 7.5 + self.ph[3]))
        sp, sh = self._sprite(scale, ang, fx)
        clip_composite(canvas, sh, x - sh.width / 2 + 7, y - sh.height / 2 + 10)
        clip_composite(canvas, sp, x - sp.width / 2, y - sp.height / 2)
        self.rect = (x, y, sp.width, sp.height)
        self.vis = clamp01(local / 0.4)


class Particle:
    def __init__(self, sprite, x, y, vx, vy, life, sway=0.0, spin=0.0):
        self.sprite, self.x, self.y, self.vx, self.vy = sprite, x, y, vx, vy
        self.life, self.age, self.sway, self.spin = life, 0.0, sway, spin
        self.ph = random.uniform(0, 6.28)


# ---- Spotify mini player -----------------------------------------------------
class MusicControl:
    """Plays a local MP3 on a loop in the background (via pygame.mixer)."""

    def __init__(self, filename, volume=0.5):
        self.playing = False
        self.ok = False
        self.pg = None
        path = filename
        if not os.path.isabs(path):
            for base in (ASSETS, HERE):
                if os.path.exists(os.path.join(base, filename)):
                    path = os.path.join(base, filename)
                    break
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            self.pg, self.ok = pygame, True
        except Exception as e:
            print(f"[music] could not load '{filename}': {e}")

    def start(self):
        if self.ok:
            self.pg.mixer.music.play(loops=-1)          # -1 = loop forever
            self.playing = True

    def press(self, name):
        if not self.ok:
            return
        if self.playing:
            self.pg.mixer.music.pause()
        else:
            self.pg.mixer.music.unpause()
        self.playing = not self.playing

    def stop(self):
        if self.ok:
            try:
                self.pg.mixer.music.stop()
                self.pg.mixer.quit()
            except Exception:
                pass


class PlayerCard:
    """Small brass-and-parchment record player, bottom-left."""
    X0, Y0, CW, CH = 52, H - 52 - 60, 188, 60
    BTN = {"play": (96, 41)}                                          # relative to card
    LABEL_POS = (62, 17)                                              # relative to card

    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.angle = 0.0
        self.last = 0.0
        self.disc_src = self._disc()
        self.disc_cache = {}
        self.base = {}
        for playing in (False, True):
            img = self._build(playing)
            self.base[playing] = (img,) + shadow_of(img, 5, 90)

    def alpha(self, t):
        return smooth((t - 4.6) / 1.0)

    def _build(self, playing):
        S = 4
        w, h = self.CW * S, self.CH * S
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([S, S, w - S, h - S], radius=10 * S,
                            fill=(232, 205, 156, 240), outline=GOLD, width=2 * S)
        d.rounded_rectangle([5 * S, 5 * S, w - 5 * S, h - 5 * S], radius=7 * S,
                            outline=INK_SOFT, width=S // 2)
        d.ellipse([(32 - 24) * S, (30 - 24) * S, (32 + 24) * S, (30 + 24) * S],
                  outline=GOLD, width=S)
        ink = INK + (255,)

        def poly(pts):
            d.polygon([(x * S, y * S) for x, y in pts], fill=ink)

        def rect(x0, y0, x1, y1):
            d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=ink)

        cx, cy = self.BTN["play"]
        d.ellipse([(cx - 11) * S, (cy - 11) * S, (cx + 11) * S, (cy + 11) * S],
                  fill=(244, 224, 184, 255), outline=GOLD, width=int(1.5 * S))
        if playing:
            rect(cx - 4.5, cy - 5, cx - 1.5, cy + 5)
            rect(cx + 1.5, cy - 5, cx + 4.5, cy + 5)
        else:
            poly([(cx - 3, cy - 5.5), (cx + 5.5, cy), (cx - 3, cy + 5.5)])
        return im.resize((self.CW, self.CH), Image.LANCZOS)

    @staticmethod
    def _disc():
        S, size = 4, 44
        n = size * S
        im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([0, 0, n - 1, n - 1], fill=(38, 26, 22, 255))
        for k in range(5):
            r = n / 2 * (0.98 - k * 0.09)
            d.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r],
                      outline=(66, 48, 40, 255), width=S // 2)
        d.arc([n * .1, n * .1, n * .9, n * .9], 200, 250, fill=(135, 108, 90, 255), width=2 * S)
        d.arc([n * .1, n * .1, n * .9, n * .9], 20, 70, fill=(135, 108, 90, 255), width=2 * S)
        r = n * 0.30
        d.ellipse([n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r],
                  fill=WAX + (255,), outline=GOLD + (255,), width=S)
        d.ellipse([n / 2 + n * .17 - n * .035, n / 2 - n * .035,
                   n / 2 + n * .17 + n * .035, n / 2 + n * .035], fill=GOLD + (255,))
        hr = n * 0.04
        d.ellipse([n / 2 - hr, n / 2 - hr, n / 2 + hr, n / 2 + hr], fill=(232, 205, 156, 255))
        return im.resize((size, size), Image.LANCZOS)

    def hit(self, x, y, t):
        if t < 5.0:
            return None
        for name, (bx, by) in self.BTN.items():
            rad = 14 if name == "play" else 12
            if (x - self.X0 - bx) ** 2 + (y - self.Y0 - by) ** 2 <= rad ** 2:
                return name
        return None

    def press(self, name):
        self.ctrl.press(name)

    def draw(self, canvas, t):
        dt = max(0.0, min(0.1, t - self.last))
        self.last = t
        playing = self.ctrl.playing
        if playing:
            self.angle = (self.angle + 130 * dt) % 360
        a = self.alpha(t)
        if a <= 0.01:
            return
        base, sh, pad = self.base[playing]
        card = base.copy()

        k = int(self.angle // 6) % 60
        if k not in self.disc_cache:
            self.disc_cache[k] = self.disc_src.rotate(-k * 6, resample=Image.BICUBIC)
        card.alpha_composite(self.disc_cache[k], (10, 8))

        bars = ImageDraw.Draw(card)                       # tiny equalizer
        for i in range(3):
            hgt = 3 + (7 * (0.5 + 0.5 * math.sin(t * (5.5 + i * 1.7) + i * 2.0)) if playing else 0)
            bx = self.CW - 30 + i * 6
            bars.rectangle([bx, 24 - hgt, bx + 3, 24],
                           fill=(GOLD if playing else INK_SOFT) + (255,))

        clip_composite(canvas, with_alpha(sh, a), self.X0 - pad + 3, self.Y0 - pad + 5)
        clip_composite(canvas, with_alpha(card, a), self.X0, self.Y0)


class Scene:
    def __init__(self):
        rng = random.Random(11)
        self.rng = rng
        self.bg_light = make_background().convert("RGBA")
        self.bg_dark = make_background(dark=True).convert("RGBA")

        # ---------------- Part 1 : closed letter + cats
        letter = load_asset("letter.png")
        lw = 540
        self.letter = letter.resize((lw, int(letter.height * lw / letter.width)), Image.LANCZOS)
        self.letter_center = (W / 2, 418)
        self.seal_frac = (0.523, 0.600)
        self.letter_cache = {}
        self.letter_rect = (0, 0, 0, 0)

        cats = [load_asset(f"cat{i}.png") for i in range(1, 7)]
        dx = (W - 1100) / 2
        # (cat index, anchor x, y, height, layer, delay)
        layout = [
            (1, 70, 330, 120, 0, 0.9), (4, 1035, 345, 125, 0, 1.05),
            (2, 235, 420, 140, 0, 0.7), (5, 870, 430, 140, 0, 0.8),
            (0, 215, 105, 105, 0, 1.2), (3, 900, 100, 105, 0, 1.3),
            (3, 165, 215, 175, 1, 1.1), (0, 935, 235, 175, 1, 1.2),
            (5, 150, 560, 170, 1, 1.35), (1, 955, 565, 170, 1, 1.45),
            (4, 330, 640, 125, 1, 1.55), (2, 790, 645, 125, 1, 1.65),
        ]
        self.floaters = [Floater(cats[c], (x + dx, y), h, lay, d, rng)
                         for c, x, y, h, lay, d in layout]

        # ---------------- Part 2 : the opened letter
        cx = W / 2 - 22                                   # composition centre
        self.paper_h = 660
        paper = load_asset("paper.png")
        self.paper = paper.resize((int(paper.width * self.paper_h / paper.height), self.paper_h),
                                  Image.LANCZOS)
        self.paper_center = (cx - 15, 365)
        self.paper_cache = {}
        self.paper_rect = None
        self.text_cx = self.paper_center[0] - 4           # centre of the writing area
        self.text_top = self.paper_center[1] - self.paper_h / 2

        photo = load_asset("photo.png")
        polaroid = make_polaroid(photo, 310)
        self.props = {
            "flowers": Prop(load_asset("flowers.png"), 335, (cx - 375, 535), 2.7,
                            enter=(-520, 60), dur=1.3, drift=(0, 3), tilt=2.2, speed=0.9, seed=1),
            "photo": Prop(polaroid, polaroid.height, (cx + 290, 215), 3.0,
                          enter=(0, -520), dur=1.3, drift=(2, 4), tilt=1.3, base_ang=5, speed=0.8, seed=2),
            "candle": Prop(load_asset("candle.png"), 345, (cx + 400, 540), 3.3,
                           enter=(0, 420), dur=1.3, drift=(0, 3), tilt=0.0, speed=0.8, seed=3),
            "butterfly": Prop(load_asset("butterfly.png"), 165, (cx - 395, 150), 3.6,
                              enter=(-520, -320), dur=2.4, drift=(42, 26), tilt=11, base_ang=-8,
                              speed=1.0, flap=True, seed=4, ang_q=1.5),
        }
        self.glow_cache = {}
        self.glow_src = {"big": warm_glow(620), "small": warm_glow(210)}

        # ---------------- shared
        self.hearts = [heart_sprite(s, c) for s, c in
                       [(18, (170, 60, 60)), (26, (190, 80, 70)), (34, (150, 40, 45)),
                        (22, (205, 120, 95))]]
        self.sparkle = sparkle_sprite(16, (196, 150, 70))
        self.glow = self._glow(150)
        self.particles = []
        self.ambient_timer = 0.0
        self.last_t = 0.0
        self.t_open = None
        self._settled = False
        self.seal_pos = self.letter_center
        self.sparkles = [(rng.uniform(60, W - 60), rng.uniform(60, H - 60),
                          rng.uniform(0, 6.28), rng.uniform(1, 2.5)) for _ in range(26)]

        # ---------------- music player (bottom-left)
        self.music = MusicControl(MUSIC_FILE, MUSIC_VOLUME)
        self.player = PlayerCard(self.music)

    @staticmethod
    def _glow(size):
        g = Image.new("L", (size, size), 0)
        ImageDraw.Draw(g).ellipse([size * .28, size * .28, size * .72, size * .72], fill=255)
        g = g.filter(ImageFilter.GaussianBlur(size * 0.14))
        im = Image.new("RGBA", (size, size), (200, 50, 45, 0))
        im.putalpha(g)
        return im

    # -- state
    def u(self, t):
        return None if self.t_open is None else t - self.t_open

    def hit_letter(self, x, y):
        l, t, r, b = self.letter_rect
        return self.t_open is None and l <= x <= r and t <= y <= b

    def open(self, t):
        if self.t_open is None:
            self.t_open = t
            self.burst(self.seal_pos[0], self.seal_pos[1], 34)

    # -- helpers
    def letter_sprite(self, scale, ang):
        key = (round(scale * 50), round(ang * 4))
        if key not in self.letter_cache:
            w, h = self.letter.size
            sp = self.letter.resize((max(8, int(w * scale)), max(8, int(h * scale))), Image.LANCZOS)
            sp = sp.rotate(ang, resample=Image.BICUBIC, expand=True)
            sh, pad = shadow_of(sp, 16, 120)
            self.letter_cache[key] = (sp, sh, pad)
            if len(self.letter_cache) > 300:
                self.letter_cache.pop(next(iter(self.letter_cache)))
        return self.letter_cache[key]

    def paper_sprite(self, scale, ang):
        key = (round(scale * 40), round(ang * 2))
        if key not in self.paper_cache:
            w, h = self.paper.size
            sp = self.paper.resize((max(8, int(w * key[0] / 40)), max(8, int(h * key[0] / 40))),
                                   Image.LANCZOS)
            sp = sp.rotate(key[1] / 2, resample=Image.BICUBIC, expand=True)
            sh, pad = shadow_of(sp, 14, 130)
            self.paper_cache[key] = (sp, sh)
            if len(self.paper_cache) > 200:
                self.paper_cache.pop(next(iter(self.paper_cache)))
        return self.paper_cache[key]

    def glow_sprite(self, name, level):
        key = (name, level)
        if key not in self.glow_cache:
            self.glow_cache[key] = with_alpha(self.glow_src[name], level / 12)
        return self.glow_cache[key]

    def burst(self, x, y, n=22):
        for _ in range(n):
            a = random.uniform(0, 6.28)
            v = random.uniform(90, 300)
            self.particles.append(Particle(random.choice(self.hearts), x, y,
                                           math.cos(a) * v, math.sin(a) * v - 120,
                                           random.uniform(1.4, 2.4), random.uniform(0, 14)))

    def spawn_ambient(self):
        self.particles.append(Particle(random.choice(self.hearts), random.uniform(60, W - 60),
                                       H + 20, random.uniform(-12, 12), random.uniform(-70, -40),
                                       random.uniform(9, 14), random.uniform(10, 26)))

    # -- render one frame
    def render(self, t):
        dt = max(0.0, min(0.1, t - self.last_t))
        self.last_t = t
        u = self.u(t)

        # background: parchment -> candle-lit walnut when the letter opens
        if u is None:
            canvas = self.bg_light.copy()
        else:
            k = smooth((u - 0.8) / 1.3)
            canvas = self.bg_dark.copy() if k >= 1 else Image.blend(self.bg_light, self.bg_dark, k)

        # twinkling sparkles
        for x, y, ph, sp in self.sparkles:
            a = 0.5 + 0.5 * math.sin(t * sp + ph)
            if a > 0.2 and t > 0.6:
                clip_composite(canvas, with_alpha(self.sparkle, a * 0.8), x, y)

        # cats
        for f in self.floaters:
            if u is None:
                vis = 1.0
            elif KEEP_CATS and f.layer == 0:
                vis = 1.0
            else:
                vis = 1 - ease_out_cubic(u / 0.9)
            if f.layer == 0:
                f.draw(canvas, t, vis)

        # ---- the letter: drops in, floats / breathes; on click it shakes, then slides away
        intro = ease_out_back(t / 1.1)
        bob = 11 * math.sin(t * 1.25)
        sway = 2.6 * math.sin(t * 0.8 + 0.6)
        scale = max(0.05, intro) * (1 + 0.012 * math.sin(t * 2.0))
        drop = (1 - ease_out_cubic(t / 1.1)) * -260
        fa, dy = 1.0, 0.0
        if u is not None:
            scale *= 1 + 0.10 * ease_out_cubic(u / 0.8)
            sway += 5 * math.sin(u * 38) * clamp01(u / 0.15) * max(0.0, 1 - u / 0.85)
            if u > 0.8:
                q = clamp01((u - 0.8) / 1.0)
                fa = 1 - q
                dy = 170 * ease_out_cubic(q)
                scale *= 1 - 0.12 * q
        cx, cy = self.letter_center[0], self.letter_center[1] + bob + drop + dy
        sp, sh, pad = self.letter_sprite(scale, sway)

        # the parchment slides up out of the envelope (drawn BEHIND the letter)
        if u is not None and u > 0.9:
            p = clamp01((u - 0.9) / 1.5)
            e = ease_out_cubic(p)
            px = self.letter_center[0] + (self.paper_center[0] - self.letter_center[0]) * e
            py = self.letter_center[1] + (self.paper_center[1] - self.letter_center[1]) * e
            psc = 0.25 + 0.75 * ease_out_back(p)
            pang = -7 * (1 - e)
            psp, psh = self.paper_sprite(psc, pang)
            pa = clamp01(p / 0.2)
            clip_composite(canvas, with_alpha(psh, pa), px - psh.width / 2 + 8, py - psh.height / 2 + 14)
            clip_composite(canvas, with_alpha(psp, pa), px - psp.width / 2, py - psp.height / 2)
            if p >= 1.0 and not self._settled:
                self._settled = True
                self.burst(px - 230, py + 140, 14)
                self.burst(px + 230, py + 140, 14)

        if fa > 0.01:
            self.letter_rect = (cx - sp.width / 2, cy - sp.height / 2,
                                cx + sp.width / 2, cy + sp.height / 2)
            clip_composite(canvas, with_alpha(sh, fa), cx - sh.width / 2 + 10, cy - sh.height / 2 + 22)
            clip_composite(canvas, with_alpha(sp, fa), cx - sp.width / 2, cy - sp.height / 2)

            # wax seal heartbeat glow (rotate the seal offset with the letter)
            if t > 1.0:
                ox = (self.seal_frac[0] - 0.5) * self.letter.width * scale
                oy = (self.seal_frac[1] - 0.5) * self.letter.height * scale
                r = math.radians(-sway)
                sx = cx + ox * math.cos(r) - oy * math.sin(r)
                sy = cy + ox * math.sin(r) + oy * math.cos(r)
                beat = max(0.0, math.sin(t * 3.4)) ** 6 + 0.6 * max(0.0, math.sin(t * 3.4 - 0.9)) ** 8
                if u is not None:
                    beat = max(beat, 0.9)
                g = self.glow.copy()
                g.putalpha(g.getchannel("A").point(lambda v: int(v * (0.25 + 0.65 * beat) * fa)))
                gs = int(150 * (0.85 + 0.35 * beat))
                g = g.resize((gs, gs), Image.BICUBIC)
                clip_composite(canvas, g, sx - gs / 2, sy - gs / 2)
                if u is None:
                    self.seal_pos = (sx, sy)
                    # auto heart puff on every few beats
                    if int(t * 3.4 / (2 * math.pi) * 0.5 * 2) != getattr(self, "_last_puff", -1) and beat > 0.9:
                        self._last_puff = int(t * 3.4 / (2 * math.pi) * 0.5 * 2)
                        self.burst(sx, sy - 10, 5)

        for f in self.floaters:
            if f.layer == 1:
                f.draw(canvas, t, 1.0 if u is None else 1 - ease_out_cubic(u / 0.9))

        # ---- the opened letter's decorations
        if u is not None:
            for name in ("flowers", "photo", "candle"):
                self.props[name].draw(canvas, u)

            c = self.props["candle"]
            if c.rect is not None:
                x, y, w, h = c.rect
                fx, fy = x + 0.20 * w, y - 0.38 * h                  # flame position on the sprite
                flick = (0.78 + 0.14 * math.sin(t * 13.0) + 0.08 * math.sin(t * 21 + 1.3)
                         + 0.06 * math.sin(t * 5.1))
                lvl = max(1, min(12, int(round(flick * 12 * 0.60 * c.vis))))
                big, small = self.glow_sprite("big", max(1, lvl // 2)), self.glow_sprite("small", lvl)
                clip_composite(canvas, big, fx - big.width / 2, fy - big.height / 2)
                clip_composite(canvas, small, fx - small.width / 2, fy - small.height / 2)

            self.props["butterfly"].draw(canvas, u)

        # ---- particles (ambient rising hearts + click bursts)
        self.ambient_timer += dt
        if t > 1.5 and self.ambient_timer > 0.55:
            self.ambient_timer = 0
            self.spawn_ambient()
        alive = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.life:
                continue
            p.vy += 120 * dt if p.vy < 0 and abs(p.vx) > 40 else 0     # burst hearts arc back down gently
            p.x += (p.vx + p.sway * math.sin(t * 2 + p.ph)) * dt
            p.y += p.vy * dt
            if abs(p.vx) > 40:
                p.vx *= 0.96
                p.vy *= 0.96
            fade = min(1.0, p.age / 0.3, (p.life - p.age) / 0.6)
            clip_composite(canvas, with_alpha(p.sprite, fade * 0.9), p.x - p.sprite.width / 2,
                           p.y - p.sprite.height / 2)
            alive.append(p)
        self.particles = alive

        # ---- the little record player sits on top of everything
        self.player.draw(canvas, t)

        return canvas.convert("RGB")


# ---- GUI ---------------------------------------------------------------------
def run():
    global W
    import time
    import tkinter as tk
    from tkinter import font as tkfont
    from PIL import ImageTk

    root = tk.Tk()
    root.title("For Ella")
    root.configure(bg="#e9d9ba")
    root.attributes("-fullscreen", True)               # fullscreen by default
    root.update()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()

    W = max(1100, int(round(H * sw / sh)))              # fit the logical canvas to the screen shape
    s = min(sw / W, sh / H)                             # logical -> screen scale
    ox, oy = (sw - W * s) / 2, (sh - H * s) / 2

    def X(x): return ox + x * s
    def Y(y): return oy + y * s

    canvas = tk.Canvas(root, width=sw, height=sh, highlightthickness=0, bg="#e9d9ba")
    canvas.pack(fill="both", expand=True)

    scene = Scene()
    scene.music.start()                                 # begin looping the MP3
    families = set(tkfont.families())
    family = next((f for f in SCRIPT_FONTS if f in families), "TkDefaultFont")
    body_family = family if family != "TkDefaultFont" else "Times"

    def F(px, fam=None):
        return tkfont.Font(family=fam or family, size=-max(8, int(px * s)), slant="italic")

    title_font, sub_font, hint_font = F(72), F(19, body_family), F(18, body_family)
    greet_font, body_font, sign_font = F(40), F(23, body_family), F(30)
    music_font = F(15, body_family)

    hex_ = lambda c: "#%02x%02x%02x" % tuple(c)
    img_id = canvas.create_image(ox, oy, anchor="nw")
    shadow = canvas.create_text(X(W / 2 + 3), Y(95 + 3), text="", font=title_font, fill="#c9b48c")
    title = canvas.create_text(X(W / 2), Y(95), text="", font=title_font, fill=hex_(INK))
    line_l = canvas.create_line(0, 0, 0, 0, fill=hex_(GOLD), width=2)
    line_r = canvas.create_line(0, 0, 0, 0, fill=hex_(GOLD), width=2)
    diamond = canvas.create_polygon(0, 0, 0, 0, 0, 0, 0, 0, fill=hex_(GOLD), outline="")
    sub = canvas.create_text(X(W / 2), Y(150), text="", font=sub_font, fill=hex_(INK_SOFT))
    hint = canvas.create_text(X(W / 2), Y(H - 30), text="", font=hint_font, fill=hex_(INK_SOFT))

    # --- text that is written on the opened parchment
    tcx, ttop = scene.text_cx, scene.text_top
    wrap = int(330 * s)
    greet = canvas.create_text(X(tcx), Y(ttop + 100), text="", font=greet_font, fill=hex_(INK), anchor="n")
    orn_l = canvas.create_line(0, 0, 0, 0, fill=hex_(GOLD), width=2, state="hidden")
    orn_r = canvas.create_line(0, 0, 0, 0, fill=hex_(GOLD), width=2, state="hidden")
    orn_d = canvas.create_polygon(0, 0, 0, 0, 0, 0, 0, 0, fill=hex_(GOLD), outline="", state="hidden")
    body = canvas.create_text(X(tcx), Y(ttop + 188), text="", font=body_font, fill=hex_(INK),
                              anchor="n", justify="center", width=wrap)
    sign = canvas.create_text(X(tcx), Y(ttop + 505), text="", font=sign_font, fill=hex_(INK), anchor="n")

    # --- label on the little record player
    music_label = canvas.create_text(X(PlayerCard.X0 + PlayerCard.LABEL_POS[0]),
                                     Y(PlayerCard.Y0 + PlayerCard.LABEL_POS[1]),
                                     text="", font=music_font, fill=hex_(INK), anchor="w")

    state = {"photo": None, "dark_bg": False}
    start = time.time()

    def lerp_color(c1, c2, k):
        return "#%02x%02x%02x" % tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))

    def tick():
        t0 = time.time()
        t = t0 - start
        u = scene.u(t)
        frame = scene.render(t)
        if abs(s - 1) > 1e-3:
            frame = frame.resize((int(W * s), int(H * s)), Image.BILINEAR)
        state["photo"] = ImageTk.PhotoImage(frame)
        canvas.itemconfig(img_id, image=state["photo"])

        if u is None:
            # typewriter "HAPPY BIRTHDAY" with a slow fade-in of ink
            k = max(0.0, (t - 1.4) / 1.6)
            n = min(len(TEXT), int(k * len(TEXT)) + (1 if k > 0 else 0))
            shown = TEXT[:n]
            fade = min(1.0, max(0.0, (t - 1.4) / 0.9))
            canvas.itemconfig(shadow, text=shown, fill=lerp_color(PARCHMENT, (201, 180, 140), fade))
            canvas.itemconfig(title, text=shown, fill=lerp_color(PARCHMENT, INK, fade))

            # flourish under the title
            ft = min(1.0, max(0.0, (t - 3.0) / 1.0))
            if ft > 0:
                half = 130 * ease_out_cubic(ft)
                canvas.coords(line_l, X(W / 2 - 12), Y(138), X(W / 2 - 12 - half), Y(138))
                canvas.coords(line_r, X(W / 2 + 12), Y(138), X(W / 2 + 12 + half), Y(138))
                canvas.coords(diamond, X(W / 2), Y(131), X(W / 2 + 7), Y(138),
                              X(W / 2), Y(145), X(W / 2 - 7), Y(138))
                canvas.itemconfig(sub, text=SUBTITLE if ft > 0.6 else "")
                canvas.coords(sub, X(W / 2), Y(162 + 2 * math.sin(t * 1.5)))
            # little hint
            if t > 4.5:
                pulse = 0.5 + 0.5 * math.sin(t * 2.2)
                canvas.itemconfig(hint, text=HINT, fill=lerp_color(INK_SOFT, (222, 195, 150), pulse * 0.65))
        else:
            # title fades into the parchment, then everything old hides
            k = clamp01(u / 0.7)
            canvas.itemconfig(title, fill=lerp_color(INK, PARCHMENT, k))
            canvas.itemconfig(shadow, fill=lerp_color((201, 180, 140), PARCHMENT, k))
            canvas.itemconfig(sub, fill=lerp_color(INK_SOFT, PARCHMENT, k))
            canvas.itemconfig(hint, text="")
            if k >= 1.0:
                for it in (title, shadow, sub, line_l, line_r, diamond):
                    canvas.itemconfig(it, state="hidden")
            if u > 1.6 and not state["dark_bg"]:
                state["dark_bg"] = True
                canvas.configure(bg=hex_(WALNUT))
                root.configure(bg=hex_(WALNUT))

            # the love letter is "written" onto the parchment
            n = int(max(0.0, u - 3.4) * 26)
            canvas.itemconfig(greet, text=GREETING[:n])
            n2 = n - len(GREETING)
            if n >= len(GREETING):
                o = clamp01((u - 3.4 - len(GREETING) / 26) / 0.8)
                half = 62 * ease_out_cubic(o)
                for it in (orn_l, orn_r, orn_d):
                    canvas.itemconfig(it, state="normal")
                oy_ = ttop + 168
                canvas.coords(orn_l, X(tcx - 9), Y(oy_), X(tcx - 9 - half), Y(oy_))
                canvas.coords(orn_r, X(tcx + 9), Y(oy_), X(tcx + 9 + half), Y(oy_))
                canvas.coords(orn_d, X(tcx), Y(oy_ - 5), X(tcx + 5), Y(oy_), X(tcx), Y(oy_ + 5), X(tcx - 5), Y(oy_))
            canvas.itemconfig(body, text=BODY[:max(0, n2)])
            n3 = n2 - len(BODY)
            if n3 > 0:
                canvas.itemconfig(sign, text=(SIGN + " \u2665")[:n3])

        # music player label fades in together with the card
        pa = scene.player.alpha(t)
        if pa > 0.01:
            canvas.itemconfig(music_label, text=MUSIC_LABEL,
                              fill=lerp_color((232, 205, 156), INK, pa))
        canvas.tag_raise(music_label)

        elapsed = int((time.time() - t0) * 1000)
        root.after(max(1, int(1000 / FPS) - elapsed), tick)

    def to_logical(e):
        return (e.x - ox) / s, (e.y - oy) / s

    def on_click(e):
        x, y = to_logical(e)
        t = time.time() - start
        btn = scene.player.hit(x, y, t)
        if btn:                                          # record-player buttons
            scene.player.press(btn)
            return
        if scene.hit_letter(x, y) and t > 1.2:
            scene.open(t)
            canvas.config(cursor="")
        else:
            scene.burst(x, y, 26)

    def on_move(e):
        x, y = to_logical(e)
        t = time.time() - start
        over = scene.hit_letter(x, y) or scene.player.hit(x, y, t)
        canvas.config(cursor="hand2" if over else "")

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<Motion>", on_move)
    root.bind("<Escape>", lambda e: root.destroy())
    root.bind("q", lambda e: root.destroy())
    tick()
    root.mainloop()
    scene.music.stop()


if __name__ == "__main__":
    if "--test" in sys.argv:      # headless frame dump (no tkinter needed)
        s = Scene()
        for i, tt in enumerate([0.3, 1.0, 2.5, 5.0]):
            s.render(tt - 0.03)
            s.render(tt).save(f"/tmp/frame{i}.png")
        s.open(5.0)
        for i, tt in enumerate([5.4, 6.3, 7.5, 9.0, 12.0], start=4):
            s.render(tt - 0.03)
            s.render(tt).save(f"/tmp/frame{i}.png")
        print("frames saved")
    else:
        run()