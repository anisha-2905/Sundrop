# ---------------------------------------------------------------- window
WIN_W = 1280
WIN_H = 720

MIN_W = 320
MIN_H = 320

FPS = 60

TITLE = "Sundrop"
TAGLINE = "A little magic, at your fingertips."

TITLE_FONT = "fonts/CinzelDecorative-Bold.ttf"
TITLE_FONT_SIZE = 72
TITLE_COLOR = (255, 205, 90)


# ------------------------------------------------ pointillism flower
PARTICLE_STYLE = "pointillism"

PARTICLE_SIZE_MIN = 1.0
PARTICLE_SIZE_MAX = 2.2

PARTICLE_OPACITY = 0.95
PARTICLE_VARIATION = 0.30

# Brightness without washing colors into white
GAIN = 0.85
GLOW = 0.0

# Render at full resolution
RENDER_SCALE = 1.0
MAX_RENDER_LONG = 1920

# Flower density
DENSITY = 8.0

# ---------------------------------------------------------------- pointillism palette
# ---------------------------------------------------------------- palette (RGB)

NAVY =  (30, 10, 70)

ORANGE = (255, 110, 20)       # Rich orange petals
GOLD = (255, 175, 50)         # Golden petal edges
PURPLE = (215, 55, 175)       # Purple flower centre
LILAC = (255, 140, 215)       # Pink centre highlights
AMBER = (214, 140, 40)        # Amber stem
GREEN_GOLD = (150, 172, 64)  # Green-gold leaves

# ---------------------------------------------------------------- background
BACKGROUND_STYLE = "lantern"
BACKGROUND_DIM = 0.9
BACKGROUND_SPOTLIGHT = 0.55
BG_QUALITY = 2.0
BACKGROUND_COLOR = NAVY
SHOW_FIREFLIES = True

# ---------------------------------------------------------------- hand tracking
CAMERA_INDEX = 0
SWAP_HANDS = False

OPEN_MIN = 1.20
OPEN_MAX = 1.85
OPENNESS_SMOOTHING = 0.5
DEADZONE = 0.10
HOLD_SECONDS = 0.8

# ---------------------------------------------------------------- motion
GROW_RISE, GROW_FALL = 0.35, 0.25
BLOOM_RISE, BLOOM_FALL = 0.37, 0.39

# ---------------------------------------------------------------- fireflies
FIREFLY_COUNT = 10