"""Sunpetal - turns your hands into two numbers: grow (left) and bloom (right).

* HandTracker      - webcam + MediaPipe in a background thread (never blocks the art)
* ManualInput      - mouse / keyboard fallback so you can always play and test
* GestureController- smoothing, "hold on tracking loss", and the rest pose
"""
import math
import sys
import threading
import time

import numpy as np

import config as cfg


def _dist(a, b, w, h):
    return math.hypot((a.x - b.x) * w, (a.y - b.y) * h)


def openness(lm, w, h):
    """0 = closed fist / resting, 1 = fully open hand (scale-independent)."""
    palm = _dist(lm[0], lm[9], w, h) or 1e-6
    ratio = sum(_dist(lm[0], lm[i], w, h) for i in (8, 12, 16, 20)) / 4.0 / palm
    v = float(np.clip((ratio - cfg.OPEN_MIN) / (cfg.OPEN_MAX - cfg.OPEN_MIN), 0.0, 1.0))
    return 0.0 if v < cfg.DEADZONE else v


class HandTracker:
    """status: 'starting' -> 'running' or 'error'. .left / .right are 0..1 or None (hand not seen)."""

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.status, self.error = "starting", ""
        self.left = self.right = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _fail(self, msg):
        self.status, self.error = "error", msg

    def _open_camera(self, cv2):
        """Try the requested camera first, then others, with several Windows backends."""
        if sys.platform == "win32":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]
        indices = [self.camera_index] + [i for i in range(4) if i != self.camera_index]
        for idx in indices:
            for be in backends:
                cap = cv2.VideoCapture(idx, be)
                if cap.isOpened():
                    ok, _ = cap.read()
                    if ok:
                        self.camera_index = idx
                        return cap
                cap.release()
        return None

    def _run(self):
        try:
            import cv2
        except Exception as e:
            self._fail(f"OpenCV missing ({type(e).__name__}) - run: pip install opencv-contrib-python==4.10.0.84")
            return
        try:
            import mediapipe as mp
            hands_api = mp.solutions.hands
        except AttributeError:
            self._fail("This MediaPipe version has no classic hands API - run: pip install mediapipe==0.10.14 (Python 3.10-3.12)")
            return
        except Exception as e:
            self._fail(f"MediaPipe failed to load ({type(e).__name__}: {e}) - use Python 3.10-3.12 and mediapipe==0.10.14")
            return

        cap = self._open_camera(cv2)
        if cap is None:
            self._fail("No camera could be opened - close Zoom/Teams/browser tabs using it, "
                       "and check Windows Settings > Privacy > Camera (allow desktop apps)")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        hands = hands_api.Hands(max_num_hands=2, model_complexity=0,
                                min_detection_confidence=0.6, min_tracking_confidence=0.5)
        self.status = "running"
        ema = {"Left": None, "Right": None}
        k = cfg.OPENNESS_SMOOTHING
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                frame = cv2.flip(frame, 1)                       # selfie view -> labels are YOUR hands
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = hands.process(rgb)
                seen = {}
                if res.multi_hand_landmarks:
                    for hl, hd in zip(res.multi_hand_landmarks, res.multi_handedness):
                        label = hd.classification[0].label
                        if cfg.SWAP_HANDS:
                            label = "Left" if label == "Right" else "Right"
                        seen[label] = openness(hl.landmark, w, h)
                for label in ("Left", "Right"):
                    if label in seen:
                        ema[label] = seen[label] if ema[label] is None else k * ema[label] + (1 - k) * seen[label]
                    else:
                        ema[label] = None
                self.left, self.right = ema["Left"], ema["Right"]
        except Exception as e:
            self._fail(f"Tracking stopped: {type(e).__name__}: {e}")
        finally:
            cap.release()
            hands.close()


class ManualInput:
    """Mouse / keyboard stand-in for the hands.
    Hold LEFT mouse / W / UP = left hand open (grow). Hold RIGHT mouse / SPACE / B = right hand open (bloom)."""

    def read(self):
        import pygame
        keys, mouse = pygame.key.get_pressed(), pygame.mouse.get_pressed()
        grow = mouse[0] or keys[pygame.K_w] or keys[pygame.K_UP]
        bloom = mouse[2] or keys[pygame.K_SPACE] or keys[pygame.K_b]
        return (1.0 if grow else 0.0), (1.0 if bloom else 0.0)


def demo_inputs(t):
    """A scripted 28 s loop (grow -> bloom -> rest) for when you just want to watch it."""
    from flower_model import smoothstep
    c = t % 28.0
    left = smoothstep((c - 1) / 7) - smoothstep((c - 22) / 4)
    right = smoothstep((c - 9) / 4) - smoothstep((c - 16) / 3)
    return float(np.clip(left, 0, 1)), float(np.clip(right, 0, 1))


def _approach(x, target, rise, fall, dt):
    rate = rise if target > x else fall
    return x + (target - x) * (1.0 - math.exp(-rate * dt))


class GestureController:
    """Smooth grow/bloom values (0..1). One scalar each, so the flower can never
    bloom and close at the same time. Brief tracking loss holds the pose, then eases to rest."""

    def __init__(self):
        self.grow = 0.0
        self.bloom = 0.0
        self.idle = 0.0                           # seconds since any hand was open
        self._last = {"left": (0.0, -1e9), "right": (0.0, -1e9)}

    def _target(self, name, raw, now):
        if raw is not None:
            self._last[name] = (raw, now)
            return raw
        value, seen_at = self._last[name]
        return value if now - seen_at < cfg.HOLD_SECONDS else 0.0

    def update(self, dt, left_raw, right_raw, now):
        g = min(1.0, self._target("left", left_raw, now) * 1.05)
        b = self._target("right", right_raw, now)
        # blooming only becomes possible once the plant has grown
        ready = float(np.clip((self.grow - 0.50) / 0.35, 0, 1))
        b *= ready * ready * (3 - 2 * ready)
        self.grow = _approach(self.grow, g, cfg.GROW_RISE, cfg.GROW_FALL, dt)
        self.bloom = _approach(self.bloom, b, cfg.BLOOM_RISE, cfg.BLOOM_FALL, dt)
        active = (left_raw or 0) > 0.15 or (right_raw or 0) > 0.15
        self.idle = 0.0 if active else self.idle + dt