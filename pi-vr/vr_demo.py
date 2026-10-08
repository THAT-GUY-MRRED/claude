"""Stereo VR demo for a Raspberry Pi headset.

Draws a 3D wireframe world twice (one view per eye, side by side) and turns
the view with your head using the MPU-6050.

    python3 vr_demo.py          # with the gyro connected
    python3 vr_demo.py --fake   # test on any computer: mouse / arrow keys look around

Keys:  C = recenter   +/- = adjust eye spacing (IPD)   Esc = quit
"""

import argparse
import math
import random

import pygame

from head_tracker import FakeTracker, HeadTracker

FOV_DEG = 90          # field of view per eye; tweak until objects look the right size
EYE_SEPARATION = 0.064  # metres between the two virtual cameras (average IPD)
NEAR = 0.05


def build_world():
    """Return a list of 3D line segments ((x,y,z),(x,y,z)) and their colours."""
    lines = []
    floor_y = -1.6
    # Floor grid
    for i in range(-10, 11):
        lines.append((((i, floor_y, -10), (i, floor_y, 10)), (40, 120, 40)))
        lines.append((((-10, floor_y, i), (10, floor_y, i)), (40, 120, 40)))
    # Cubes scattered around you
    random.seed(3)
    for _ in range(12):
        ang = random.uniform(0, 2 * math.pi)
        dist = random.uniform(3, 8)
        cx, cz = math.sin(ang) * dist, math.cos(ang) * dist
        s = random.uniform(0.3, 0.8)
        cy = floor_y + s
        colour = random.choice([(255, 80, 80), (80, 160, 255), (255, 220, 60), (200, 100, 255)])
        corners = [(cx + dx * s, cy + dy * s, cz + dz * s)
                   for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
        for a in range(8):
            for b in range(a + 1, 8):
                # corners that differ in exactly one axis are cube edges
                if bin(a ^ b).count("1") == 1:
                    lines.append(((corners[a], corners[b]), colour))
    # A big ring in the sky so you can tell when you look up
    for k in range(32):
        a1, a2 = k * 2 * math.pi / 32, (k + 1) * 2 * math.pi / 32
        lines.append((((math.cos(a1) * 6, 5, math.sin(a1) * 6),
                       (math.cos(a2) * 6, 5, math.sin(a2) * 6)), (255, 255, 255)))
    return lines


def rotation(yaw, pitch, roll):
    """3x3 matrix turning camera-space directions into world-space ones."""
    y, p, r = math.radians(yaw), math.radians(-pitch), math.radians(-roll)
    cy, sy = math.cos(y), math.sin(y)
    cp, sp = math.cos(p), math.sin(p)
    cr, sr = math.cos(r), math.sin(r)
    ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rx = ((1, 0, 0), (0, cp, -sp), (0, sp, cp))
    rz = ((cr, -sr, 0), (sr, cr, 0), (0, 0, 1))

    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))

    return mul(mul(ry, rx), rz)


def to_camera(p, eye, m):
    """World point -> camera space (x right, y up, z forward), i.e. m^T (p - eye)."""
    d = (p[0] - eye[0], p[1] - eye[1], p[2] - eye[2])
    return tuple(m[0][j] * d[0] + m[1][j] * d[1] + m[2][j] * d[2] for j in range(3))


def draw_eye(surface, rect, lines, eye, m, focal):
    cx, cy = rect.centerx, rect.centery
    for (a, b), colour in lines:
        pa, pb = to_camera(a, eye, m), to_camera(b, eye, m)
        if pa[2] < NEAR and pb[2] < NEAR:
            continue
        # Clip the segment so it doesn't pass behind the eye
        if pa[2] < NEAR or pb[2] < NEAR:
            t = (NEAR - pa[2]) / (pb[2] - pa[2])
            mid = tuple(pa[i] + (pb[i] - pa[i]) * t for i in range(3))
            if pa[2] < NEAR:
                pa = mid
            else:
                pb = mid
        sa = (cx + focal * pa[0] / pa[2], cy - focal * pa[1] / pa[2])
        sb = (cx + focal * pb[0] / pb[2], cy - focal * pb[1] / pb[2])
        if max(abs(sa[0]), abs(sa[1]), abs(sb[0]), abs(sb[1])) > 1e5:
            continue
        pygame.draw.line(surface, colour, sa, sb, 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake", action="store_true", help="no sensor; use mouse/arrow keys")
    parser.add_argument("--windowed", action="store_true", help="run in a window instead of fullscreen")
    parser.add_argument("--frames", type=int, default=0, help="quit after N frames (for testing)")
    args = parser.parse_args()

    tracker = FakeTracker() if args.fake else HeadTracker()
    if not args.fake:
        print("Calibrating - keep the headset still for 2 seconds...")
    tracker.calibrate()
    tracker.start()

    pygame.init()
    if args.windowed:
        screen = pygame.display.set_mode((1280, 720))
    else:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(not args.fake or args.windowed)
    w, h = screen.get_size()
    left_rect = pygame.Rect(0, 0, w // 2, h)
    right_rect = pygame.Rect(w // 2, 0, w // 2, h)
    focal = (w / 4) / math.tan(math.radians(FOV_DEG) / 2)

    lines = build_world()
    eye_sep = EYE_SEPARATION
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)
    frame = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_c:
                    tracker.recenter()
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    eye_sep += 0.002
                elif event.key == pygame.K_MINUS:
                    eye_sep = max(0.0, eye_sep - 0.002)
            elif event.type == pygame.MOUSEMOTION and args.fake and event.buttons[0]:
                tracker.yaw += event.rel[0] * 0.3
                tracker.pitch = max(-89, min(89, tracker.pitch - event.rel[1] * 0.3))

        if args.fake:
            keys = pygame.key.get_pressed()
            tracker.yaw += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 2
            tracker.pitch += (keys[pygame.K_UP] - keys[pygame.K_DOWN]) * 2

        yaw, pitch, roll = tracker.get()
        m = rotation(yaw, pitch, roll)
        right_dir = (m[0][0], m[1][0], m[2][0])
        half = eye_sep / 2
        left_eye = (-right_dir[0] * half, -right_dir[1] * half, -right_dir[2] * half)
        right_eye = (right_dir[0] * half, right_dir[1] * half, right_dir[2] * half)

        screen.fill((0, 0, 0))
        screen.set_clip(left_rect)
        draw_eye(screen, left_rect, lines, left_eye, m, focal)
        screen.set_clip(right_rect)
        draw_eye(screen, right_rect, lines, right_eye, m, focal)
        screen.set_clip(None)
        pygame.draw.line(screen, (60, 60, 60), (w // 2, 0), (w // 2, h), 2)

        if args.fake or args.windowed:
            info = f"yaw {yaw:.0f}  pitch {pitch:.0f}  roll {roll:.0f}  IPD {eye_sep * 1000:.0f}mm  {clock.get_fps():.0f}fps"
            screen.blit(font.render(info, True, (200, 200, 200)), (10, 10))

        pygame.display.flip()
        clock.tick(60)
        frame += 1
        if args.frames and frame >= args.frames:
            running = False

    tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
