"""Sunpetal - draws the particle plant as soft additive light on a midnight sky."""
import numpy as np
import pygame

import config as cfg


def _lerp(a, b, t):
    return a + (b - a) * t


class Fireflies:
    """Tiny warm lights drifting around the plant (world space, so they get parallax)."""

    def __init__(self, n, seed=11):
        rng = np.random.default_rng(seed)
        self.n = n
        self.home = np.stack([rng.uniform(-2.3, 2.3, n), rng.uniform(-0.1, 2.9, n), rng.uniform(-1.6, 1.6, n)], -1)
        self.amp = rng.uniform(0.15, 0.5, (n, 3))
        self.spd = rng.uniform(0.15, 0.5, (n, 3))
        self.ph = rng.random((n, 3)) * 6.28
        self.tw_spd = rng.uniform(0.8, 2.2, n)
        self.tw_ph = rng.random(n) * 6.28

    def positions(self, t):
        return self.home + self.amp * np.sin(t * self.spd + self.ph)

    def brightness(self, t):
        return (0.5 + 0.5 * np.sin(t * self.tw_spd + self.tw_ph)) ** 2


def _glow_sprite(size, level):
    r = size / 2.0
    y, x = np.mgrid[0:size, 0:size]
    d = np.hypot(x - r + 0.5, y - r + 0.5) / r
    f = np.clip(1 - d, 0, 1) ** 2.2 * level
    col = np.array([255, 205, 110], dtype=float)
    arr = (f[:, :, None] * col[None, None, :]).clip(0, 255).astype(np.uint8)
    return pygame.surfarray.make_surface(arr.swapaxes(0, 1))


class Renderer:
    def __init__(self, win_size, scale=0.5):
        self.WW, self.WH = win_size
        self.W, self.H = int(self.WW * scale), int(self.WH * scale)
        self.layer = pygame.Surface((self.W, self.H), depth=32)
        # tone-map lookup: brightness 1 - exp(-x), so overlapping light saturates softly instead of clipping
        steps = 2048
        self._lut = (255.0 * (1.0 - np.exp(-np.arange(steps) / (steps / 6.0 * 1.0)))).astype(np.uint8)
        self._lut_scale = (steps / 6.0) * cfg.GAIN
        self.bg = self._make_background()
        self.fireflies = Fireflies(cfg.FIREFLY_COUNT)
        self.sprites = {s: [_glow_sprite(s, l) for l in np.linspace(0.12, 1.0, 8)] for s in (10, 18, 28)}
        self.font_big = self._font(54)
        self.font = self._font(19)
        self.font_small = self._font(15)
        self._title = None

    # ------------------------------------------------------------ setup
    @staticmethod
    def _font(size):
        return pygame.font.SysFont("segoeui,helveticaneue,avenir,arial", size)

    def _make_background(self):
        """Plain solid navy - no stars, no gradient."""
        bg = pygame.Surface((self.WW, self.WH))
        bg.fill(cfg.BACKGROUND_COLOR)
        return bg

    # ------------------------------------------------------------ camera
    def project(self, pos, t):
        """Slow cinematic camera: a gentle orbit + dolly. Returns screen x, y (render px) and scale."""
        yaw = 0.22 * np.sin(t * 0.17)
        pitch = 0.05 + 0.03 * np.sin(t * 0.11)
        cy, sy_ = np.cos(yaw), np.sin(yaw)
        cp, sp = np.cos(pitch), np.sin(pitch)
        x = pos[:, 0] * cy + pos[:, 2] * sy_
        z = -pos[:, 0] * sy_ + pos[:, 2] * cy
        y = pos[:, 1] - 1.28
        y2, z2 = y * cp - z * sp, y * sp + z * cp
        dist = 5.0 + 0.15 * np.sin(t * 0.11)
        focal = 1.58 * self.H
        k = focal / (dist + z2)
        return self.W / 2 + x * k, self.H * 0.5 - y2 * k, k / (focal / 5.0)

    # ------------------------------------------------------------ drawing
    def draw(self, screen, pos, col, inten, t):
        W, H = self.W, self.H
        sx, sy, ds = self.project(pos, t)
        x0, y0 = np.floor(sx).astype(np.int64), np.floor(sy).astype(np.int64)
        ok = (x0 >= 0) & (x0 < W - 1) & (y0 >= 0) & (y0 < H - 1) & (inten > 0.004)
        x0, y0, fx, fy = x0[ok], y0[ok], (sx - np.floor(sx))[ok], (sy - np.floor(sy))[ok]
        w_ = (inten * np.clip(ds, 0.6, 1.4))[ok]
        c_ = col[ok] * w_[:, None]
        layer = pygame.Surface((W, H))
        layer.fill((0, 0, 0))
        if x0.size:
            # only accumulate inside the box that actually contains particles (much faster)
            xmin, ymin = int(x0.min()), int(y0.min())
            cw, ch = int(x0.max()) - xmin + 2, int(y0.max()) - ymin + 2
            i00 = (y0 - ymin) * cw + (x0 - xmin)
            idx = np.concatenate([i00, i00 + 1, i00 + cw, i00 + cw + 1])
            wt = np.concatenate([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy])
            n_px = cw * ch
            idx3 = np.concatenate([idx, idx + n_px, idx + 2 * n_px])
            w3 = np.concatenate([np.tile(c_[:, c], 4) * wt for c in range(3)])
            acc = np.bincount(idx3, weights=w3, minlength=3 * n_px)
            lut_i = np.minimum((acc * self._lut_scale).astype(np.int32), len(self._lut) - 1)
            img = np.ascontiguousarray(self._lut[lut_i].reshape(3, ch, cw).transpose(1, 2, 0))
            layer.blit(pygame.image.frombuffer(img.tobytes(), (cw, ch), "RGB"), (xmin, ymin))
        self.layer = layer

        screen.blit(self.bg, (0, 0))
        screen.blit(self.layer if (W, H) == (self.WW, self.WH)
                    else pygame.transform.smoothscale(self.layer, (self.WW, self.WH)),
                    (0, 0), special_flags=pygame.BLEND_ADD)
        if cfg.GLOW > 0:                                       # optional soft halo (cheap: done at tiny size)
            for div, strength in ((6, 130), (18, 120)):
                k = int(strength * cfg.GLOW)
                halo = pygame.transform.smoothscale(self.layer, (max(W // div, 2), max(H // div, 2)))
                halo.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
                screen.blit(pygame.transform.smoothscale(halo, (self.WW, self.WH)), (0, 0),
                            special_flags=pygame.BLEND_ADD)
        if cfg.SHOW_FIREFLIES:
            self._draw_fireflies(screen, t)

    def _draw_fireflies(self, screen, t):
        ff = self.fireflies
        sx, sy, ds = self.project(ff.positions(t), t)
        br = ff.brightness(t)
        k = self.WW / self.W
        for i in range(ff.n):
            lvl = min(int(br[i] * 8), 7)
            size = 28 if ds[i] > 1.12 else (18 if ds[i] > 0.9 else 10)
            spr = self.sprites[size][lvl]
            screen.blit(spr, (sx[i] * k - size / 2, sy[i] * k - size / 2), special_flags=pygame.BLEND_ADD)

    # ------------------------------------------------------------ HUD
    def _text(self, font, text, color, alpha):
        s = font.render(text, True, color)
        s.set_alpha(int(255 * alpha))
        return s

    def draw_hud(self, screen, t, ctrl, status, show_help=True, preview=None):
        lilac, gold = cfg.LILAC, cfg.GOLD
        # title + tagline fade away once you start growing
        a = float(np.clip(1.0 - ctrl.grow * 6, 0, 1))
        if a > 0.01:
            s = self._text(self.font_big, cfg.TITLE, gold, a)
            screen.blit(s, ((self.WW - s.get_width()) // 2, int(self.WH * 0.12)))
            s = self._text(self.font, cfg.TAGLINE, lilac, a * 0.85)
            screen.blit(s, ((self.WW - s.get_width()) // 2, int(self.WH * 0.12) + 62))

        if show_help:
            # minimal instructions: visible at the start and whenever you've been idle a while
            vis = np.clip(1.0 - (t - 20) / 4.0, 0, 1) if ctrl.idle < 8 else np.clip((ctrl.idle - 8) / 2.0, 0, 1)
            vis = max(float(vis), 0.0)
            if vis > 0.01:
                items = [("LEFT HAND", "open to grow"), ("RIGHT HAND", "open to bloom"), ("BOTH CLOSED", "rest")]
                gap = self.WW // 4
                for i, (head, tail) in enumerate(items):
                    cx = int(gap * (i + 1))
                    h = self._text(self.font_small, head, gold, vis * 0.9)
                    tl = self._text(self.font_small, tail, lilac, vis * 0.7)
                    screen.blit(h, (cx - h.get_width() // 2, self.WH - 58))
                    screen.blit(tl, (cx - tl.get_width() // 2, self.WH - 36))
        if status:
            s = self._text(self.font_small, status, lilac, 0.75)
            screen.blit(s, (16, 12))
        if preview is not None:
            screen.blit(preview, (self.WW - preview.get_width() - 14, 14))