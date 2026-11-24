"""Sundrop - a little magic, at your fingertips..

Run:   python main.py            (webcam hand tracking)
       python main.py --mouse    (no camera: hold left/right mouse button)
       python main.py --demo     (watch a scripted grow -> bloom -> rest loop)

Keys:  ESC quit | F fullscreen | M switch camera/mouse | H hide hints
The window is resizable - drag its edges or maximise it; everything re-fits.
"""
import argparse
import pygame
import config as cfg
import os, warnings

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"
warnings.filterwarnings("ignore", category=UserWarning)

from flower_model import PlantModel
from hand_input import GestureController, HandTracker, ManualInput, demo_inputs
from renderer import Renderer


def parse_args():
    p = argparse.ArgumentParser(description="Sundrop - gesture-grown particle lily")
    p.add_argument("--mouse", action="store_true", help="use mouse/keyboard instead of the webcam")
    p.add_argument("--demo", action="store_true", help="play a scripted demo loop")
    p.add_argument("--camera", type=int, default=cfg.CAMERA_INDEX, help="webcam index (default 0)")
    p.add_argument("--fullscreen", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    pygame.init()
    windowed = (cfg.WIN_W, cfg.WIN_H)
    fullscreen = args.fullscreen

    def open_display():
        if fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)      # native screen size
        return pygame.display.set_mode(windowed, pygame.RESIZABLE)

    screen = open_display()
    pygame.display.set_caption(cfg.TITLE)
    clock = pygame.time.Clock()

    model = PlantModel(cfg.DENSITY)
    renderer = Renderer(screen.get_size(), cfg.RENDER_SCALE)
    ctrl, manual = GestureController(), ManualInput()

    tracker = None
    if not (args.mouse or args.demo):
        tracker = HandTracker(args.camera)
        tracker.start()
    use_manual, show_help, reported = args.mouse, True, False

    t, running = 0.0, True
    while running:
        dt = min(clock.tick(cfg.FPS) / 1000.0, 0.05)
        t += dt
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type in (pygame.VIDEORESIZE, getattr(pygame, "WINDOWSIZECHANGED", -1)):
                screen = pygame.display.get_surface()
                if not fullscreen:
                    windowed = screen.get_size()
                renderer.resize(screen.get_size())
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.key == pygame.K_f:
                    if not fullscreen:
                        windowed = screen.get_size()
                    fullscreen = not fullscreen
                    screen = open_display()
                    renderer.resize(screen.get_size())
                elif e.key == pygame.K_m:
                    use_manual = not use_manual
                elif e.key == pygame.K_h:
                    show_help = not show_help

        # ---- where do the two numbers come from?
        status = ""
        if args.demo:
            left, right = demo_inputs(t)
            status = "demo"
        elif tracker and tracker.status == "running" and not use_manual:
            left, right = tracker.left, tracker.right
            status = "hands: tracking" if (left is not None or right is not None) else "hands: show me a hand"
        else:
            left, right = manual.read()
            status = "mouse mode: hold LEFT click = grow, RIGHT click = bloom"
            if tracker and tracker.status == "starting" and not use_manual:
                status = "starting camera...  (mouse works meanwhile)"
            if tracker and tracker.status == "error":
                status = f"Camera unavailable: {tracker.error}  |  mouse mode: left click = grow, right click = bloom"
                if not reported:
                    print("[Sundrop]", tracker.error)
                    reported = True

        ctrl.update(dt, left, right, t)
        pos, col, inten = model.frame(t, ctrl.grow, ctrl.bloom)
        screen = pygame.display.get_surface()
        renderer.draw(screen, pos, col, inten, t)

        renderer.draw_hud(screen, t, ctrl, status, show_help)
        pygame.display.flip()

    if tracker:
        tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main()