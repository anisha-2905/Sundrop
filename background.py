"""Sunpetal - the lantern night background (pointillism), painted for ANY window size.

How it stays responsive
* The scene is designed on a "logical" canvas whose SHORT side is always 540 units, so a
  tall phone-shaped window, a wide monitor and a square window all get the same dot size
  and the same look; only the layout changes (lanterns re-arrange for portrait / landscape).
* Painting takes a second or two, so it runs in a background thread. While it works you
  see the previous picture (cover-scaled) or plain purple; the new one swaps in when ready.
* While you drag the window edge, painting waits until you stop (no wasted work).

Only pygame + the standard library are needed here.
"""
import math
import random
import threading
import time

import pygame

import config as cfg

BASE = 540                      # logical length of the short side
BG = (24, 20, 60)
ACCENTS = [(255, 170, 60), (120, 90, 200), (70, 100, 200), (240, 150, 170)]

# Landscape layers, back to front. Points are (x fraction, y fraction of the height).
BACK_HILLS = [(0, .640), (.12, .605), (.28, .640), (.45, .622), (.62, .655), (.80, .632), (1, .660)]
VALLEY = [(0, .668), (.2, .662), (.5, .682), (.8, .668), (1, .690)]
MID_HILLS = [(0, .800), (.2, .822), (.45, .808), (.7, .832), (1, .810)]
FRONT_HILLS = [(0, .868), (.25, .895), (.55, .880), (.8, .902), (1, .875)]
BOTTOM = [(0, .945), (.3, .962), (.6, .950), (1, .958)]

# portrait lantern layout: x fraction, y fraction, width as a fraction of the width
PORTRAIT_LANTERNS = [(.820, .107, .169), (.616, .249, .165), (.814, .391, .152), (.620, .510, .117),
                     (.766, .608, .082), (.877, .667, .063), (.936, .715, .042)]
# landscape layout: x fraction of width, y fraction of height, width in logical units
LANDSCAPE_LANTERNS = [(.885, .13, 66), (.805, .31, 62), (.920, .47, 56), (.845, .62, 42),
                      (.940, .72, 30), (.885, .80, 22), (.965, .86, 15),            # right stream
                      (.075, .20, 36), (.165, .38, 28), (.095, .54, 21), (.200, .64, 15)]  # left stream


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def logical_size(w, h):
    """Logical canvas whose short side is BASE, same aspect ratio as the window."""
    if w >= h:
        return int(round(BASE * w / h)), BASE
    return BASE, int(round(BASE * h / w))


def curve(points, x, W, H):
    t = x / W
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if t <= x1:
            k = (t - x0) / (x1 - x0)
            k = (1 - math.cos(k * math.pi)) / 2
            return (y0 + (y1 - y0) * k) * H
    return points[-1][1] * H


def draw_layer(surf, points, colour, rim, W, H):
    top = [(x, curve(points, x, W, H)) for x in range(-4, W + 8, 4)]
    bottom = [(W + 4, H), (-4, H)]
    pygame.draw.polygon(surf, rim, [(x, y - 3) for x, y in top] + bottom)
    pygame.draw.polygon(surf, colour, top + bottom)


def draw_pine(surf, x, y, h, colour):
    w = h * 0.42
    for k in range(3):
        top = y - h + k * h * 0.27
        half = w * (0.5 + k * 0.2)
        pygame.draw.polygon(surf, colour, [(x, top), (x - half, top + h * 0.5), (x + half, top + h * 0.5)])
    pygame.draw.rect(surf, colour, (x - 1, y - h * 0.12, 2, h * 0.14))


def draw_trees(surf, points, colour, hmin, hmax, gap, density, rng, W, H):
    x = 0.0
    while x < W:
        if rng.random() < density:
            draw_pine(surf, x, curve(points, x, W, H) + 3, rng.uniform(hmin, hmax), colour)
        x += rng.uniform(*gap)


# ----------------------------------------------------------------------------
# the smooth source picture
# ----------------------------------------------------------------------------
def paint_sky(surf, W, H):
    stops = [(0.0, (20, 16, 62)), (0.5, (52, 42, 112)), (1.0, (44, 36, 98))]
    for y in range(H):
        t = y / max(1, H - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t <= t1:
                k = (t - t0) / (t1 - t0)
                pygame.draw.line(surf, tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3)), (0, y), (W, y))
                break


def draw_clouds(surf, rng, W, H):
    # y, wave size, thickness, body colour, rim colour, start x, end x (fractions)
    bands = [
        (0.05, 0.02, 0.10, (22, 18, 62), (46, 40, 108), 0.0, 0.55),
        (0.11, 0.02, 0.10, (36, 30, 84), (66, 58, 128), 0.35, 1.0),
        (0.17, 0.025, 0.12, (20, 16, 56), (44, 38, 100), 0.0, 0.7),
        (0.24, 0.02, 0.10, (62, 54, 128), (96, 86, 164), 0.5, 1.0),
        (0.30, 0.03, 0.12, (24, 20, 64), (50, 44, 112), 0.0, 0.6),
        (0.36, 0.02, 0.10, (50, 44, 108), (84, 76, 150), 0.4, 1.0),
        (0.42, 0.03, 0.12, (22, 18, 60), (46, 40, 104), 0.0, 0.5),
        (0.46, 0.025, 0.10, (64, 56, 130), (98, 88, 168), 0.45, 1.0),
        (0.52, 0.03, 0.12, (34, 30, 82), (62, 54, 122), 0.0, 1.0),
        (0.57, 0.03, 0.08, (46, 40, 100), (76, 68, 140), 0.0, 1.0),
    ]
    for yf, af, tf, base, rim, x0, x1 in bands:
        phase = rng.uniform(0, 6.28)
        circles = []
        x = W * x0 - 30
        while x < W * x1 + 30:
            r = rng.uniform(16, 34)
            circles.append((x, H * yf + math.sin(x * 0.012 + phase) * H * af, r))
            x += r * rng.uniform(0.9, 1.4)
        for x, cy, r in circles:
            pygame.draw.circle(surf, rim, (int(x), int(cy - 2)), int(r + 2))
        for x, cy, r in circles:
            pygame.draw.circle(surf, base, (int(x), int(cy)), int(r))
            pygame.draw.rect(surf, base, (int(x - r), int(cy), int(2 * r), int(H * tf)))


def draw_swirl(surf, W, H):
    cx, cy = W * 0.2, H * 0.185
    pts = [(cx + t * 1.6 * math.cos(t), cy + t * 1.6 * math.sin(t))
           for t in [0.5 + (4 * math.pi - 0.5) * i / 90 for i in range(91)]]
    pygame.draw.lines(surf, (70, 72, 176), False, pts, 3)


def draw_moon(surf, W, H):
    cx, cy = int(W * (0.575 if H > W else 0.64)), int(H * 0.08)
    size = 140
    halo = pygame.Surface((size, size), pygame.SRCALPHA)
    for r, a, col in ((66, 14, (130, 105, 200)), (50, 22, (140, 115, 210)), (36, 34, (170, 140, 220)),
                      (24, 50, (215, 190, 225))):
        pygame.draw.circle(halo, (*col, a), (size // 2, size // 2), r)
    surf.blit(halo, (cx - size // 2, cy - size // 2))
    moon = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.circle(moon, (255, 238, 192, 255), (20, 20), 15)
    pygame.draw.circle(moon, (0, 0, 0, 0), (26, 15), 13)          # bite -> crescent
    surf.blit(moon, (cx - 20, cy - 20))


def draw_houses(surf, rng, W, H):
    """A quiet, dark hillside village (silhouettes only, no lights)."""
    houses = []
    for _ in range(int(330 * W / BASE)):
        x = rng.uniform(20, W - 10)
        y_min = curve(VALLEY, x, W, H) + 4
        y_max = curve(MID_HILLS, x, W, H) - 4
        if y_max <= y_min + 8:
            continue
        houses.append((x, rng.uniform(y_min + 8, y_max)))
    for x, base in sorted(houses, key=lambda h: h[1]):                # far ones first
        t = (base - H * 0.67) / (H * 0.14)
        w, h = rng.uniform(7, 11) * (0.8 + 0.5 * t), rng.uniform(6, 9) * (0.8 + 0.5 * t)
        shade = rng.randint(-6, 8)
        pygame.draw.rect(surf, (40 + shade, 35 + shade, 96 + shade), (x, base - h, w, h))
        pygame.draw.polygon(surf, (24, 20, 66), [(x - 1.5, base - h), (x + w / 2, base - h - h * 0.6),
                                                 (x + w + 1.5, base - h)])


def draw_lantern(surf, cx, cy, w):
    h = int(w * 1.5)
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    ell = max(6, int(w * 0.22))

    halo = pygame.Surface((int(w * 3), int(h * 2)), pygame.SRCALPHA)         # warm glow around it
    for i in range(14, 0, -1):
        pygame.draw.ellipse(halo, (255, 165, 70, 6 + (14 - i) * 3),
                            (halo.get_width() / 2 - w * (0.5 + i * 0.07), halo.get_height() / 2 - h * (0.5 + i * 0.06),
                             w * (1 + i * 0.14), h * (1 + i * 0.12)))
    surf.blit(halo, (cx - halo.get_width() / 2, cy - halo.get_height() / 2))

    for yy in range(y0 + ell // 2, y0 + h - ell // 2):                      # body, shaded per pixel
        v = (yy - y0) / h
        for xx in range(x0, x0 + int(w)):
            if not (0 <= xx < surf.get_width() and 0 <= yy < surf.get_height()):
                continue
            u = (xx - x0) / w
            shade = (0.74 + 0.36 * math.sin(u * math.pi)) * (0.95 + 0.15 * v)
            mix = max(0, v - 0.55) / 0.45 * 0.5
            col = tuple(min(255, int((c * (1 - mix) + y * mix) * shade)) for c, y in zip((190, 138, 54), (245, 215, 130)))
            surf.set_at((xx, yy), col)
    pygame.draw.ellipse(surf, (172, 122, 48), (x0, y0, w, ell))
    pygame.draw.ellipse(surf, (150, 104, 42), (x0, y0 + h - ell, w, ell))
    pygame.draw.ellipse(surf, (240, 222, 158), (x0 + w * 0.07, y0 + h - ell * 0.92, w * 0.86, ell * 0.72))

    sun = (116, 62, 22)
    sx, sy, sr = x0 + w * 0.5, y0 + h * 0.40, w * 0.15
    for k in range(12):
        a = k * math.pi / 6
        tip = sr + (w * 0.17 if k % 2 == 0 else w * 0.10)
        da = 0.16
        pygame.draw.polygon(surf, sun, [
            (sx + math.cos(a - da) * sr * 1.05, sy + math.sin(a - da) * sr * 1.05),
            (sx + math.cos(a) * tip, sy + math.sin(a) * tip),
            (sx + math.cos(a + da) * sr * 1.05, sy + math.sin(a + da) * sr * 1.05)])
    pygame.draw.circle(surf, sun, (int(sx), int(sy)), max(1, int(sr)))
    if w >= 40:
        for fx, fy in [(.14, .10), (.38, .06), (.62, .06), (.86, .10), (.10, .30), (.90, .30),
                       (.14, .62), (.86, .62), (.22, .78), (.5, .74), (.78, .78)]:
            hx, hy, r = x0 + fx * w, y0 + fy * h, max(1, int(w * 0.018))
            pygame.draw.circle(surf, (130, 78, 30), (int(hx - r * 0.9), int(hy)), r)
            pygame.draw.circle(surf, (130, 78, 30), (int(hx + r * 0.9), int(hy)), r)
            pygame.draw.polygon(surf, (130, 78, 30), [(hx - r * 1.8, hy + r * 0.2), (hx + r * 1.8, hy + r * 0.2),
                                                      (hx, hy + r * 2.2)])
    return (x0 - w * 0.7, y0 - h * 0.35, w * 2.4, h * 1.7)                    # area that gets extra-fine dots


def lantern_layout(W, H):
    """Different arrangement for portrait vs landscape so the plant in the middle stays clear."""
    if W / H > 0.85:                    # landscape and square: lanterns stream down both sides
        return [(fx * W, fy * H, w) for fx, fy, w in LANDSCAPE_LANTERNS]
    return [(fx * W, fy * H, fw * W) for fx, fy, fw in PORTRAIT_LANTERNS]


def build_source(rng, W, H):
    surf = pygame.Surface((W, H))
    paint_sky(surf, W, H)
    draw_clouds(surf, rng, W, H)
    draw_swirl(surf, W, H)
    draw_moon(surf, W, H)

    draw_layer(surf, BACK_HILLS, (34, 29, 86), (92, 84, 164), W, H)
    draw_trees(surf, BACK_HILLS, (28, 24, 74), 10, 20, (5, 10), 0.85, rng, W, H)
    draw_layer(surf, VALLEY, (30, 26, 78), (66, 58, 126), W, H)
    draw_houses(surf, rng, W, H)
    draw_layer(surf, MID_HILLS, (24, 20, 66), (62, 54, 122), W, H)
    draw_trees(surf, MID_HILLS, (20, 17, 58), 16, 30, (6, 12), 0.85, rng, W, H)
    draw_layer(surf, FRONT_HILLS, (17, 14, 50), (50, 44, 106), W, H)
    draw_trees(surf, FRONT_HILLS, (14, 11, 42), 26, 48, (7, 15), 0.9, rng, W, H)
    draw_layer(surf, BOTTOM, (10, 8, 32), (30, 26, 72), W, H)
    draw_trees(surf, BOTTOM, (7, 6, 24), 30, 58, (9, 18), 0.85, rng, W, H)

    boxes = []
    for cx, cy, w in sorted(lantern_layout(W, H), key=lambda l: l[2]):    # small (far) ones first
        boxes.append(draw_lantern(surf, cx, cy, int(w)))
    return surf, boxes


# ----------------------------------------------------------------------------
# turning the picture into dots
# ----------------------------------------------------------------------------
def dot_layer(canvas, src, rng, M, W, H, spacing, radius, noise=9, accent=0.08, box=None):
    x0, y0, x1, y1 = (0, 0, W, H) if box is None else (max(0, box[0]), max(0, box[1]),
                                                         min(W, box[0] + box[2]), min(H, box[1] + box[3]))
    dots = []
    gx = x0 + spacing / 2
    while gx < x1:
        gy = y0 + spacing / 2
        while gy < y1:
            px = min(W - 1, max(0, gx + rng.uniform(-0.7, 0.7) * spacing))
            py = min(H - 1, max(0, gy + rng.uniform(-0.7, 0.7) * spacing))
            r, g, b, _ = src.get_at((int(px), int(py)))
            grey = (r + g + b) / 3
            br = rng.uniform(0.9, 1.12)
            col = [(grey + (c - grey) * 1.15) * br + rng.gauss(0, noise) for c in (r, g, b)]
            if rng.random() < accent:
                a = rng.choice(ACCENTS)
                col = [c * 0.78 + ac * 0.22 for c, ac in zip(col, a)]
            dots.append((px, py, radius * rng.uniform(0.75, 1.2), tuple(max(0, min(255, int(c))) for c in col)))
            gy += spacing
        gx += spacing
    rng.shuffle(dots)
    for px, py, r, col in dots:
        pygame.draw.circle(canvas, col, (int(px * M), int(py * M)), max(1, round(r * M)))


def spotlight(w, h, strength):
    """Soft dark pool behind the plant so its golden light keeps its colour (edges stay bright)."""
    ref = min(h, w * 1.1)
    cx, cy = w * 0.5, h * 0.9 - 0.36 * ref
    rx, ry = 0.36 * ref, 0.50 * ref
    n = 64
    small = pygame.Surface((n, n))
    for j in range(n):
        for i in range(n):
            x, y = (i + 0.5) / n * w, (j + 0.5) / n * h
            d2 = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            v = 1.0 - strength * math.exp(-d2 * 1.3)
            small.set_at((i, j), (int(255 * v),) * 3)
    return pygame.transform.smoothscale(small, (w, h))


def paint(size, seed=7):
    """Returns a pygame Surface of exactly `size` with the finished dot painting."""
    w, h = size
    W, H = logical_size(w, h)
    M = max(1.0, min(cfg.BG_QUALITY, w / W))                   # dot canvas pixels per logical unit
    rng = random.Random(seed)
    src, boxes = build_source(rng, W, H)
    canvas = pygame.Surface((int(W * M), int(H * M)))
    canvas.fill(BG)
    dot_layer(canvas, src, rng, M, W, H, 5.0, 3.3)                                     # coarse dots
    dot_layer(canvas, src, rng, M, W, H, 3.0, 2.0)                                     # fine dots
    dot_layer(canvas, src, rng, M, W, H, 2.0, 1.25, 4, 0.03, (0, H * 0.56, W, H * 0.30))  # hillside detail
    for box in boxes:                                                                  # extra fine on lanterns
        dot_layer(canvas, src, rng, M, W, H, 2.0, 1.25, 4, 0.02, box)
    if cfg.BACKGROUND_DIM < 1.0:
        k = int(255 * max(0.0, cfg.BACKGROUND_DIM))
        canvas.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
    if canvas.get_size() != (w, h):
        canvas = pygame.transform.smoothscale(canvas, (w, h))
    if cfg.BACKGROUND_SPOTLIGHT > 0:
        canvas.blit(spotlight(w, h, cfg.BACKGROUND_SPOTLIGHT), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return canvas


# ----------------------------------------------------------------------------
# the manager the renderer talks to
# ----------------------------------------------------------------------------
class Background:
    """Hands the renderer a surface of the right size every frame, repainting in a thread."""

    SETTLE = 0.35                       # seconds the window size must stay put before repainting

    def __init__(self, seed=7):
        self.seed = seed
        self.want = (1, 1)
        self.changed_at = 0.0
        self.built = None               # (size, surface)
        self._job = None                # running thread
        self._result = None
        self._cover = None              # (key, surface): cheap stretched stand-in while repainting
        self._born = None               # when the first painting arrived (for the fade-in)
        self._solid = None

    def set_size(self, size):
        size = (max(int(size[0]), 64), max(int(size[1]), 64))
        if size != self.want:
            self.want = size
            self.changed_at = time.time()

    # -- thread
    def _work(self, size):
        try:
            self._result = (size, paint(size, self.seed))
        except Exception as e:           # never crash the show over a background
            print("[Sunpetal] background failed:", e)
            self._result = (size, None)

    def _navy(self):
        if self._solid is None or self._solid.get_size() != self.want:
            self._solid = pygame.Surface(self.want)
            self._solid.fill(cfg.NAVY)
        return self._solid

    def _stand_in(self):
        """The last painting, cover-scaled (no distortion) to the current size."""
        size, surf = self.built
        key = (self.want, id(surf))
        if self._cover is None or self._cover[0] != key:
            s = max(self.want[0] / size[0], self.want[1] / size[1])
            big = pygame.transform.scale(surf, (int(size[0] * s) + 1, int(size[1] * s) + 1))
            out = pygame.Surface(self.want)
            out.blit(big, ((self.want[0] - big.get_width()) // 2, (self.want[1] - big.get_height()) // 2))
            self._cover = (key, out)
        return self._cover[1]

    def surface(self):
        # pick up a finished painting
        if self._job is not None and not self._job.is_alive() and self._result is not None:
            size, surf = self._result
            self._job, self._result = None, None
            if surf is not None:
                self.built = (size, surf.convert())
                self._cover = None
                if self._born is None:
                    self._born = time.time()
        # start a new painting once the window size has settled
        stale = self.built is None or self.built[0] != self.want
        if (cfg.BACKGROUND_STYLE == "lantern" and stale and self._job is None
                and time.time() - self.changed_at > self.SETTLE):
            self._job = threading.Thread(target=self._work, args=(self.want,), daemon=True)
            self._job.start()

        if cfg.BACKGROUND_STYLE != "lantern" or self.built is None:
            return self._navy()
        img = self.built[1] if self.built[0] == self.want else self._stand_in()
        fade = 1.0 if self._born is None else min(1.0, (time.time() - self._born) / 1.2)
        if fade < 1.0:                   # first painting fades in from navy
            out = self._navy().copy()
            img = img.copy()
            img.set_alpha(int(255 * fade))
            out.blit(img, (0, 0))
            return out
        return img
