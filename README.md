# Sundrop

*A little magic, at your fingertips.*

Sundrop is an interactive digital art piece. A glowing golden lily, inspired by the Sundrop flower from *Tangled*, grows and blooms when you move your hands in front of a webcam. The whole plant is built from about 18,000 glowing particles on a midnight-navy background, so it looks like light rather than a solid 3D model.

You don't click a button to make it bloom. Growth and blooming are two separate gestures, one for each hand.

## The plant

One connected plant made of:

- a gently curved stem with light pulses that flow up it
- broad leaves at the base and narrow pointed leaves along the stem
- **3 lilies** that can bloom (golden-orange petals, purple and lilac centre, curled glowing stamens)
- **1 elongated bud** at the top that always stays closed
- pollen that floats up from open flowers and golden fireflies drifting in the background

## Gestures

| Hand | What it does |
|------|--------------|
| **Left hand, open** | **Grow.** Particles stream up from the ground and form the stem, leaves, flowers and bud. |
| **Right hand, open** | **Bloom.** The three lilies unfold, recurve and light up gold and purple. This only works once the plant has grown. |
| **Both hands closed or out of view** | **Rest.** The petals gently close and the plant lowers. The bud stays closed. |

- The flower can never bloom and close at the same time.
- If hand tracking drops for a moment, the last pose is held for 0.8 seconds, then it eases back to rest.
- Open your hand fully for the strongest effect. A relaxed fist counts as closed.

## Setup (Windows)

You need **Python 3.10, 3.11 or 3.12**. The pinned MediaPipe version does not support Python 3.13.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Run modes

```
python main.py              # webcam hand tracking
python main.py --mouse      # no camera: use mouse and keyboard
python main.py --demo       # watch a scripted grow -> bloom -> rest loop
python main.py --camera 1   # use a different webcam
python main.py --fullscreen
```

**Mouse and keyboard mode**

- Grow: hold left mouse button, `W` or Up arrow
- Bloom: hold right mouse button, `Space` or `B`

**Keys while running**

| Key | Action |
|-----|--------|
| `ESC` or `Q` | Quit |
| `F` | Toggle fullscreen |
| `M` | Switch between camera and mouse mode |
| `H` | Hide or show the on-screen hints |

## Project files

| File | Purpose |
|------|---------|
| `main.py` | Window, main loop, switching between camera, mouse and demo input |
| `flower_model.py` | The plant itself: stem, leaves, 3 lilies, bud, stamens, pollen, and the grow and bloom animation |
| `renderer.py` | Camera movement, glowing particle drawing, fireflies, on-screen hints |
| `hand_input.py` | MediaPipe hand tracking, mouse fallback, gesture smoothing |
| `config.py` | All the settings (colours, density, glow, gesture sensitivity, speeds) |
| `check_camera.py` | Diagnostic: shows exactly what is failing if the camera does not work |
| `requirements.txt` | Python packages to install |

## Settings (`config.py`)

**Look**

| Setting | Meaning |
|---------|---------|
| `DENSITY` | Particle count multiplier. Lower it (`0.7`) if your PC is slow. |
| `RENDER_SCALE` | `1.0` is crisp. Use `0.75` for more speed. |
| `GAIN` | Overall brightness of the particles. |
| `GLOW` | Soft halo around the light. `0` is perfectly sharp, `1.0` is very dreamy. |
| `BACKGROUND_COLOR` | Plain background colour. Default is navy `#071329`. |
| `SHOW_FIREFLIES` | Set to `False` for a perfectly clean background. |

**Hand tracking**

| Setting | Meaning |
|---------|---------|
| `CAMERA_INDEX` | Which webcam to use (`0`, `1`, ...). |
| `SWAP_HANDS` | Set `True` if left and right feel reversed. |
| `OPEN_MIN`, `OPEN_MAX` | How open a hand must be to count as closed or fully open. |
| `DEADZONE` | Tiny hand wobbles below this count as closed. |
| `HOLD_SECONDS` | How long the last pose is held if tracking is lost. |
| `GROW_RISE`, `GROW_FALL`, `BLOOM_RISE`, `BLOOM_FALL` | How fast the plant grows, blooms and rests. |

**Flower layout** is in `flower_model.py`, in the `FLOWERS` list:

- `axis` is the direction a flower faces. `x` is left or right, `y` is up, and a negative `z` faces the viewer.
- `s` and `off` set where the flower sits on the stem.
- `size` sets how big it is.
- `thr` sets when it starts to appear while growing. Smaller numbers appear sooner.
- `aspect` makes a flower longer and slimmer, which is how the bud is made.

## Colour palette

| Colour | Hex |
|--------|-----|
| Midnight navy (background) | `#071329` |
| Golden orange (petals) | `#FF9D32` |
| Warm gold (edges, fireflies, stamens) | `#FFD76A` |
| Royal purple (flower centre) | `#8539D5` |
| Soft lilac (centre highlights) | `#C6A0FF` |

## Credits

Inspired by the magical Sundrop flower from Disney's *Tangled*. Built with Python, Pygame, NumPy, OpenCV and MediaPipe.
