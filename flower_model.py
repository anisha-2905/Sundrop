"""Sunpetal - the particle model of the golden lily plant.

The plant is ONE connected organism made of ~20k particles:
    * a gently S-curved stem (dotted strands that flow with light pulses)
    * a rosette of broad leaves at the base + narrow leaves up the stem
    * 3 lilies that can bloom (top, right, left)  <- right hand
    * 1 elongated bud that always stays closed
    * curled glowing stamens inside each lily
    * pollen motes that float up from open flowers

Growth (left hand, 0..1): particles stream up from the ground and assemble.
Bloom (right hand, 0..1): petals unfold, recurve, and the purple centre lights up.
"""
from types import SimpleNamespace

import numpy as np

import config as cfg

# ------------------------------------------------------------------ helpers


def _c(rgb):
    return np.array(rgb, dtype=np.float64) / 255.0


ORANGE, GOLD, PURPLE, LILAC = _c(cfg.ORANGE), _c(cfg.GOLD), _c(cfg.PURPLE), _c(cfg.LILAC)
AMBER, GREEN_GOLD = _c(cfg.AMBER), _c(cfg.GREEN_GOLD)
GREEN_DEEP = _c((58, 104, 52))
WARM_WHITE = _c((255, 238, 180))

STEM_H = 1.75


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def _unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


def stem_point(s):
    """Centre line of the stem, s in 0..1 (an S-curve, leaning right at the top)."""
    s = np.asarray(s, dtype=np.float64)
    x = -0.10 * np.sin(s * 2.8)
    y = s * STEM_H
    z = 0.04 * np.sin(s * 4.0 + 0.7)
    return np.stack([x, y, z], axis=-1)


def blade_width(u, base_frac=0.12):
    """Shape of a petal/leaf: narrow base, widest ~40% up, pointed tip (0..1)."""
    u = np.clip(u, 0.0, 1.0)
    return base_frac * (1 - u) + (1 - base_frac) * np.sin(np.pi * u ** 0.75) ** 0.85


def sample_blade(rng, n, edge_frac=0.2, vein_frac=0.16, vein_vs=(-0.55, 0.0, 0.55)):
    """Sample (u along length, v across width, kind) for a petal or leaf.
    kind: 0 = fill, 1 = edge, 2 = vein. Edges and veins are evenly spaced -> dotted lines."""
    half = max(int(n * edge_frac) // 2, 1)
    per = max(int(n * vein_frac) // len(vein_vs), 1)
    n_f = max(n - 2 * half - per * len(vein_vs), 1)
    strat = lambda m: (np.arange(m) + rng.random(m)) / m
    u = np.concatenate([rng.random(n_f), strat(half), strat(half)] + [strat(per) for _ in vein_vs])
    v = np.concatenate([rng.uniform(-1, 1, n_f), -np.ones(half), np.ones(half),
                        np.repeat(np.array(vein_vs, dtype=float), per)])
    kind = np.concatenate([np.zeros(n_f, int), np.ones(2 * half, int), np.full(per * len(vein_vs), 2)])
    return u, v, kind


# ------------------------------------------------------------------ particle blocks


class Block:
    """A group of particles. Subclasses provide pose(ctx) -> (pos, col, inten)
    plus per-particle arrays: thr, spawn, flow, flow_amp, tw_amp and a band width."""

    n = 0
    band = 0.10


class StaticBlock(Block):
    def __init__(self, home, col, inten, thr, spawn, flow, flow_amp, tw_amp, band=0.10):
        self.home, self.col, self.inten = home, col, inten
        self.n = len(home)
        self.thr, self.spawn, self.flow = thr, spawn, flow
        self.flow_amp, self.tw_amp, self.band = flow_amp, tw_amp, band

    def pose(self, ctx):
        return self.home, self.col, self.inten


def _jitter(rng, base, n, spread):
    return np.asarray(base)[None, :] + rng.normal(size=(n, 3)) * np.array([spread, spread * 0.2, spread])


def make_stem(rng, density):
    strands, n = 9, int(150 * density)
    s = (np.arange(n)[None, :] + rng.random((strands, n))) / n
    phi = rng.random(strands)[:, None] * 2 * np.pi + s * 6.0
    rad = 0.032 * (1 - 0.55 * s)
    centre = stem_point(s)
    pos = centre + np.stack([np.cos(phi) * rad, np.zeros_like(rad), np.sin(phi) * rad], axis=-1)
    pos, s = pos.reshape(-1, 3), s.reshape(-1)
    m = len(s)
    base = lerp(GOLD, AMBER, rng.random(m)[:, None])
    col = lerp(base, GREEN_GOLD, (rng.random(m) * 0.55)[:, None])
    return StaticBlock(pos, col, np.full(m, 0.8), 0.5 * s, _jitter(rng, [0, -0.02, 0], m, 0.18),
                       s, np.ones(m), np.full(m, 0.1), band=0.1)


def make_pedicel(rng, p0, p2, thr, density):
    """A short branch from the stem to a flower/bud."""
    p0, p2 = np.asarray(p0), np.asarray(p2)
    d = p2 - p0
    p1 = p0 + d * np.array([0.8, 0.1, 0.8])
    pts = []
    flow = []
    for _ in range(3):
        u = (np.arange(int(45 * density)) + rng.random(int(45 * density))) / int(45 * density)
        b = ((1 - u) ** 2)[:, None] * p0 + (2 * (1 - u) * u)[:, None] * p1 + (u * u)[:, None] * p2
        pts.append(b + rng.normal(size=b.shape) * 0.008)
        flow.append(u)
    pos, u = np.concatenate(pts), np.concatenate(flow)
    m = len(u)
    col = lerp(GOLD, GREEN_GOLD, (rng.random(m) * 0.5)[:, None])
    return StaticBlock(pos, col, np.full(m, 0.8), thr - 0.10 + 0.10 * u,
                       _jitter(rng, p0, m, 0.03), u, np.ones(m), np.full(m, 0.1), band=0.06)


def make_leaf(rng, base, az, elev, L, W, droop, thr, density, ripple=0.02):
    """One leaf: a bent, pointed blade. Particles unfurl from the base outward."""
    n = int(450 * density * (L / 0.8) * (0.6 + W / 0.25 * 0.4))
    u, v, kind = sample_blade(rng, max(n, 120), edge_frac=0.2, vein_frac=0.22, vein_vs=(-0.6, -0.3, 0.0, 0.3, 0.6))
    m = len(u)
    # Bezier centre line in (r = outward, h = up)
    p1r, p1h = 0.55 * L * np.cos(elev), 0.55 * L * np.sin(elev)
    p2r, p2h = p1r + 0.55 * L * np.cos(elev - droop), p1h + 0.55 * L * np.sin(elev - droop)
    a, b, c = (1 - u) ** 2, 2 * (1 - u) * u, u * u
    r, h = b * p1r + c * p2r, b * p1h + c * p2h
    w = W * blade_width(u)
    off = v * w
    h = h + np.abs(v) * w * 0.35 + ripple * np.sin(u * 14 + v * 3)  # V-fold + small ripple
    d = np.array([np.cos(az), 0, np.sin(az)])
    t = np.array([-np.sin(az), 0, np.cos(az)])
    pos = np.asarray(base)[None, :] + r[:, None] * d + h[:, None] * np.array([0, 1, 0]) + off[:, None] * t
    rr = rng.random(m)[:, None]
    col = lerp(GREEN_DEEP, GREEN_GOLD, rr)
    col = np.where((kind == 1)[:, None], lerp(GOLD, GREEN_GOLD, 0.35), col)
    col = np.where((kind == 2)[:, None], lerp(GOLD, GREEN_GOLD, 0.55), col)
    amber = rng.random(m) < 0.06
    col[amber] = AMBER
    inten = np.where(kind == 0, 0.5, np.where(kind == 1, 1.0, 0.85))
    return StaticBlock(pos, col, inten, thr + 0.18 * u, _jitter(rng, base, m, 0.03), u,
                       np.where(kind == 0, 0.0, 1.0), np.full(m, 0.1), band=0.12)


class PetalBlock(Block):
    """One lily (6 tepals). Bloomable lilies open with the right hand; the bud never does."""

    def __init__(self, rng, anchor, axis, size, thr, stagger, bloomable=True, aspect=1.0,
                 n_per=520, roll=0.0):
        self.bloomable, self.thr_f, self.size = bloomable, thr, size
        a = _unit(axis)
        helper = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = _unit(np.cross(a, helper))
        e2 = np.cross(a, e1)
        self.anchor, self.a = np.asarray(anchor, float)[None, :], a[None, :]
        keys = ["u", "v", "kind", "az", "L", "Wd", "th_o", "de_o", "th_c", "pst"]
        acc = {k: [] for k in keys}
        for k in range(6):
            outer = k % 2 == 0
            u, v, kind = sample_blade(rng, n_per)
            m = len(u)
            full = lambda x: np.full(m, x)
            acc["u"].append(u)
            acc["v"].append(v)
            acc["kind"].append(kind)
            acc["az"].append(full(roll + k * np.pi / 3 + rng.normal(0, 0.04)))
            acc["L"].append(full(size * aspect * (1.0 if outer else 0.9) * rng.uniform(0.95, 1.05)))
            acc["Wd"].append(full(size * (0.30 if outer else 0.34) / aspect ** 0.5))
            acc["th_o"].append(full(rng.uniform(1.05, 1.25) if outer else rng.uniform(0.9, 1.1)))
            acc["de_o"].append(full(rng.uniform(0.6, 1.0)))
            acc["th_c"].append(full((0.42 if outer else 0.38) * (1.3 if aspect > 1 else 1.0)))
            acc["pst"].append(full((0.0 if outer else 0.5) + 0.15 * rng.random()))
        for k in keys:
            setattr(self, k, np.concatenate(acc[k]))
        n = self.n = len(self.u)
        self.r0 = 0.04 * size
        # closed pose: the tip bends back exactly twice the base tilt, so all 6 tips meet on the axis
        self.de_c = -2.0 * self.th_c
        # closed petals are narrower on blooming lilies, but full width on the bud so it has no gaps
        self.wc = 1.0 if aspect > 1 else 0.6
        self.st = stagger * 0.25 + self.pst * 0.2
        cA, sA = np.cos(self.az)[:, None], np.sin(self.az)[:, None]
        self.d = cA * e1[None, :] + sA * e2[None, :]
        self.t = -sA * e1[None, :] + cA * e2[None, :]

        # ---- colours: closed (golden) -> open (purple/lilac centre)
        u, v, kind = self.u, self.v, self.kind
        r = rng.random(n)
        col0 = lerp(ORANGE, GOLD, (0.25 + 0.5 * r)[:, None])
        col0 = np.where((kind == 1)[:, None], lerp(GOLD, ORANGE, 0.15), col0)
        col0 = np.where((kind == 2)[:, None], lerp(ORANGE, GOLD, 0.5), col0)
        fleck = (kind == 0) & (rng.random(n) < 0.08)
        col0[fleck] = WARM_WHITE
        pw = np.clip(1 - u / 0.5, 0, 1) * np.clip(1 - 0.7 * np.abs(v), 0, 1)
        pw = pw ** 0.8 if bloomable else pw * 0
        col1 = lerp(col0, PURPLE, (pw * 0.9)[:, None])
        lil = (pw > 0.35) & (r > 0.72)
        col1[lil] = lerp(col1[lil], LILAC, 0.8)
        self.col0, self.col1 = col0, col1
        self.inten0 = np.where(kind == 0, 0.75, np.where(kind == 1, 1.25, 1.0))
        self.inten0[fleck] = 1.8

        self.thr = thr + 0.08 * u
        self.spawn = _jitter(rng, anchor, n, 0.06)
        self.flow = u + (self.az / (2 * np.pi))
        self.flow_amp = np.where(kind == 0, 0.15, 1.0)
        self.tw_amp = np.where(fleck, 0.6, 0.08)
        self.band = 0.10

    def pose(self, ctx):
        bi = ctx.bloom * float(smoothstep((ctx.grow - self.thr_f - 0.05) / 0.15)) if self.bloomable else 0.0
        b = smoothstep((bi - self.st) / 0.55)
        theta = lerp(self.th_c, self.th_o, b)
        delta = lerp(self.de_c, self.de_o, b)
        L, u, r0 = self.L, self.u, self.r0
        p1r, p1h = r0 + 0.55 * L * np.sin(theta), 0.55 * L * np.cos(theta)
        p2r, p2h = p1r + 0.55 * L * np.sin(theta + delta), p1h + 0.55 * L * np.cos(theta + delta)
        ua, ub, uc = (1 - u) ** 2, 2 * (1 - u) * u, u * u
        r = ua * r0 + ub * p1r + uc * p2r
        h = ub * p1h + uc * p2h
        w = self.Wd * (self.wc + (1 - self.wc) * b) * blade_width(u)
        vw = self.v * w
        rr = np.maximum(r, 0.06 * self.size)
        ang = np.clip(vw / rr, -1.25, 1.25)
        cw = 1 - b                                        # closed petals wrap around the axis
        off_t = vw * b + cw * rr * np.sin(ang)
        off_r = cw * rr * (np.cos(ang) - 1)
        lift = b * 0.8 * vw * vw / L                      # open petals cup upward
        ripple = b * 0.04 * L * np.sin(u * 10 + self.az * 2) * self.v ** 2
        pos = (self.anchor + (h + lift + ripple)[:, None] * self.a
               + (r + off_r)[:, None] * self.d + off_t[:, None] * self.t)
        col = self.col0 + (self.col1 - self.col0) * b[:, None]
        return pos, col, self.inten0 * (0.45 + 0.55 * b) * (1 + 0.3 * b)


class StamenBlock(Block):
    """Curled glowing filaments in the centre of a lily (like the sundrop flower)."""

    def __init__(self, rng, anchor, axis, size, thr, stagger, density, roll=0.0):
        a = _unit(axis)
        helper = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = _unit(np.cross(a, helper))
        e2 = np.cross(a, e1)
        self.anchor, self.a, self.thr_f, self.size, self.stagger = np.asarray(anchor, float)[None, :], a[None, :], thr, size, stagger
        n_per = int(80 * density)
        w, d, Ls = [], [], []
        for k, (az, length) in enumerate([(0.3, 1.15), (2.4, 0.85), (4.4, 0.7)]):
            w.append((np.arange(n_per) + rng.random(n_per)) / n_per)
            dv = np.cos(roll + az) * e1 + np.sin(roll + az) * e2
            d.append(np.tile(dv, (n_per, 1)))
            Ls.append(np.full(n_per, size * length))
        self.w, self.d, self.Ls = np.concatenate(w), np.concatenate(d), np.concatenate(Ls)
        n = self.n = len(self.w)
        self.thr = np.full(n, thr + 0.05)
        self.spawn = _jitter(rng, anchor, n, 0.03)
        self.flow, self.flow_amp, self.tw_amp = self.w, np.ones(n), np.full(n, 0.3)
        self.band = 0.10
        self.col = lerp(GOLD, WARM_WHITE, (rng.random(n) * 0.5)[:, None])

    def pose(self, ctx):
        bi = ctx.bloom * float(smoothstep((ctx.grow - self.thr_f - 0.05) / 0.15))
        gl = float(smoothstep((bi - self.stagger * 0.2 - 0.15) / 0.6))
        w, Ls, size = self.w, self.Ls, self.size
        line = np.minimum(w / 0.62, 1.0)
        h = Ls * 0.78 * line
        r = Ls * 0.12 * line ** 1.6
        rho = np.clip((w - 0.62) / 0.38, 0, 1)
        psi = rho * 2 * np.pi * 1.15
        rc = 0.09 * size * (1 - 0.55 * rho)
        r = r + rc * (1 - np.cos(psi))
        h = h + rc * np.sin(psi)
        pos = self.anchor + (h * gl)[:, None] * self.a + (r * gl)[:, None] * self.d
        return pos, self.col, np.full(self.n, 1.5 * gl)


class PollenBlock(Block):
    """Tiny motes that drift up out of open flowers."""

    def __init__(self, rng, flowers, density):
        n = self.n = int(260 * density)
        idx = rng.integers(0, len(flowers), n)
        self.anchor = np.array([flowers[i]["anchor"] for i in idx])
        self.axis = np.array([_unit(flowers[i]["axis"]) for i in idx])
        self.fthr = np.array([flowers[i]["thr"] for i in idx])
        self.phase, self.speed = rng.random(n), rng.uniform(0.05, 0.12, n)
        self.wander = rng.normal(size=(n, 3)) * 0.18
        self.col = lerp(GOLD, LILAC, (rng.random(n) * 0.4)[:, None])
        self.thr, self.spawn = np.full(n, 0.6), self.anchor.copy()
        self.flow, self.flow_amp, self.tw_amp = np.zeros(n), np.zeros(n), np.full(n, 0.5)

    def pose(self, ctx):
        frac = (self.phase + ctx.t * self.speed) % 1.0
        bi = ctx.bloom * smoothstep((ctx.grow - self.fthr - 0.05) / 0.15)
        sway = np.sin(ctx.t * 0.7 + self.phase * 20)[:, None]
        pos = (self.anchor + self.axis * (0.2 + frac * 0.9)[:, None]
               + self.wander * (0.3 + frac)[:, None] * (0.7 + 0.3 * sway))
        return pos, self.col, 0.9 * bi * np.sin(np.pi * frac) ** 1.5


class SeedBlock(Block):
    """A faint ring of light at the root - the 'seed' that waits for your left hand."""

    def __init__(self, rng, density):
        n = self.n = int(150 * density)
        self.ang, self.rad = rng.random(n) * 2 * np.pi, 0.12 + 0.2 * np.sqrt(rng.random(n))
        self.spd, self.ph = rng.uniform(0.3, 0.8, n), rng.random(n) * 6.28
        self.col = lerp(GOLD, LILAC, (rng.random(n) * 0.5)[:, None])
        self.thr, self.spawn = np.full(n, -1.0), np.zeros((n, 3))
        self.flow, self.flow_amp, self.tw_amp = np.zeros(n), np.zeros(n), np.full(n, 0.3)

    def pose(self, ctx):
        a = self.ang + ctx.t * 0.5 * self.spd
        pos = np.stack([np.cos(a) * self.rad, 0.01 + 0.04 * np.sin(ctx.t + self.ph), np.sin(a) * self.rad * 0.8], -1)
        return pos, self.col, (0.55 + 0.45 * np.sin(ctx.t * 1.6 + self.ph)) * (1.0 - 0.6 * ctx.grow)


# ------------------------------------------------------------------ the whole plant


class PlantModel:
    FLOWERS = [
        # big middle flower: faces left (and a little toward the viewer)
        dict(name="left", s=0.68, off=(-0.30, 0.05, 0.0),
             axis=(-0.9, 0.2, -0.5), size=0.50,
             bloom=True, thr=0.46, stag=0.55, roll=0.0),

        # upper flower: faces right and slightly up  (grows right after the middle one)
        dict(name="top", s=0.78, off=(0.25, 0.06, 0.0),
             axis=(0.40, 0.15, -0.8), size=0.50,
             bloom=True, thr=0.54, stag=0.0, roll=0.0),

        # closed bud at the very top, pointing up and a little left
        dict(name="bud", s=0.97, off=(0.0, 0.08, 0.0),
             axis=(-0.35, 1.0, -0.05), size=0.27,
             bloom=False, thr=0.56, stag=0.0, roll=0.0, aspect=1.9),
    ]

    def __init__(self, density=1.0, seed=7):
        rng = np.random.default_rng(seed)
        self.blocks = []
        self._build(rng, density)
        self.n = sum(b.n for b in self.blocks)
        cat = lambda name: np.concatenate([np.asarray(getattr(b, name)) for b in self.blocks])
        self.thr, self.spawn = cat("thr"), cat("spawn")
        self.flow, self.flow_amp, self.tw_amp = cat("flow"), cat("flow_amp"), cat("tw_amp")
        self.band = np.concatenate([np.full(b.n, b.band) for b in self.blocks])
        self.noise = rng.normal(size=(self.n, 3)) * 0.30
        self.phase = rng.random(self.n) * 6.28
        self.tw_spd = rng.uniform(1.5, 4.0, self.n)
        self.pos = np.empty((self.n, 3))
        self.col = np.empty((self.n, 3))
        self.inten = np.empty(self.n)
        self.slices, i = [], 0
        for b in self.blocks:
            self.slices.append(slice(i, i + b.n))
            i += b.n

    # -- construction
    def _build(self, rng, density):
        add = self.blocks.append
        add(make_stem(rng, density))

        flowers = []
        for f in self.FLOWERS:
            anchor = stem_point(f["s"]) + np.array(f["off"])
            f = dict(f, anchor=anchor)
            flowers.append(f)
            if f["s"] < 1.0:
                add(make_pedicel(rng, stem_point(f["s"]), anchor, f["thr"], density))
            n_per = int(520 * density * (f["size"] / 0.5)) if f["bloom"] else int(330 * density)
            add(PetalBlock(rng, anchor, f["axis"], f["size"], f["thr"], f["stag"], bloomable=f["bloom"],
                           aspect=f.get("aspect", 1.0), n_per=n_per, roll=f["roll"]))
            if f["bloom"]:
                add(StamenBlock(rng, anchor, f["axis"], f["size"], f["thr"], f["stag"], density, roll=f["roll"]))
        self.flowers = flowers

        # broad rosette leaves at the base (hosta-like, as in the reference)
        for k in range(7):
            az = 0.3 + k * 2.4
            add(make_leaf(rng, [0, 0.03 + 0.01 * k, 0], az, rng.uniform(0.65, 1.0), rng.uniform(0.6, 0.85),
                          rng.uniform(0.22, 0.27), rng.uniform(1.0, 1.4), 0.00 + k * 0.035, density, ripple=0.02))
        # narrow pointed leaves climbing the stem
        for s, az, L in [(0.20, np.pi, 0.62), (0.30, 0.2, 0.55), (0.50, np.pi + 0.5, 0.55),
                         (0.70, -0.3, 0.48), (0.86, np.pi - 0.3, 0.40)]:
            add(make_leaf(rng, stem_point(s), az, 0.55, L, 0.13, 0.6, 0.5 * s + 0.02, density, ripple=0.01))

        add(PollenBlock(rng, flowers, density))
        add(SeedBlock(rng, density))

    # -- per frame
    def frame(self, t, grow, bloom):
        """Returns (positions Nx3, colours Nx3 in 0..1, intensities N) for this moment."""
        ctx = SimpleNamespace(t=t, grow=grow, bloom=bloom)
        for b, sl in zip(self.blocks, self.slices):
            p, c, i = b.pose(ctx)
            self.pos[sl], self.col[sl], self.inten[sl] = p, c, i

        # assembly: particles stream from their spawn point to their place on the plant
        a = np.clip((grow - self.thr) / self.band, 0, 1)
        e = a * a * (3 - 2 * a)
        vis = np.clip(a * 4, 0, 1)
        mid = 4 * e * (1 - e)
        swirl = (mid * (0.5 + 0.5 * np.sin(t * 2.0 + self.phase)))[:, None]
        pos = self.spawn + (self.pos - self.spawn) * e[:, None] + self.noise * swirl
        inten = self.inten * vis * (1 + 1.2 * mid)

        # light pulses flowing along stem, leaf veins and petal edges
        pulse = np.maximum(0, np.sin(2 * np.pi * (self.flow * 2.0 - t * 0.35 + self.phase * 0.05))) ** 8
        inten = inten * (1 + self.flow_amp * 1.8 * pulse)
        # twinkle
        inten = inten * (1 + self.tw_amp * np.sin(t * self.tw_spd + self.phase))

        # gentle breeze: more sway higher up
        hgt = np.clip(pos[:, 1] / 2.2, 0, 1.2) ** 2
        pos[:, 0] += 0.035 * hgt * np.sin(t * 0.8 + pos[:, 1] * 1.5)
        pos[:, 2] += 0.020 * hgt * np.sin(t * 0.6 + 1.0 + pos[:, 1] * 1.2)
        return pos, self.col, inten