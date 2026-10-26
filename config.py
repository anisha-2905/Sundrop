"""Sunpetal - every tweakable setting lives here."""

# ---------------------------------------------------------------- window
WIN_W, WIN_H = 1280, 720
FPS = 60
TITLE = "Sunpetal"
TAGLINE = "A little magic, at your fingertips."

# Particle layer resolution relative to the window.
# 0.5 = fast and soft/glowy, 0.75 = crisper but heavier.
RENDER_SCALE = 1.0
# Particle count multiplier. Lower (0.6) if your PC struggles, raise (1.5) for a denser plant.
DENSITY = 1.0
# Soft halo around the light. 0 = crisp, no halo | 0.25 = subtle | 1.0 = very dreamy/blurry.
GLOW = 0.6
# Overall brightness of the particle glow.
GAIN = 1.5

# ---------------------------------------------------------------- palette (RGB)
NAVY = (7, 19, 41)          # #071329  background
ORANGE = (255, 157, 50)     # #FF9D32  petals
GOLD = (255, 215, 106)      # #FFD76A  edges, fireflies, stamens
PURPLE = (133, 57, 213)     # #8539D5  flower centre
LILAC = (198, 160, 255)     # #C6A0FF  centre highlights
AMBER = (214, 140, 40)      # stem accent
GREEN_GOLD = (150, 172, 64) # leaf / stem accent

# ---------------------------------------------------------------- background
BACKGROUND_COLOR = NAVY     # plain solid navy; try (4, 10, 28) for darker
SHOW_FIREFLIES = True       # the drifting golden lights; set False for a perfectly clean background

# ---------------------------------------------------------------- hand tracking
CAMERA_INDEX = 0
SWAP_HANDS = False          # set True if your left/right hands feel reversed
# Hand openness = fingertip-to-wrist distance / palm length.
# A fist is roughly 1.0-1.2, a fully open hand roughly 1.8-2.1.
OPEN_MIN = 1.20             # at or below this -> closed / resting (0.0)
OPEN_MAX = 1.85             # at or above this -> fully open (1.0)
OPENNESS_SMOOTHING = 0.5    # 0 = raw, closer to 1 = smoother but laggier
DEADZONE = 0.10             # tiny hand wobbles below this count as closed

# If tracking disappears briefly, keep the last pose for this long
# before gently returning to rest.
HOLD_SECONDS = 0.8

# ---------------------------------------------------------------- motion (units per second, exponential)
GROW_RISE, GROW_FALL = 0.35, 0.25
BLOOM_RISE, BLOOM_FALL = 0.37, 0.39

# ---------------------------------------------------------------- fireflies
FIREFLY_COUNT = 10