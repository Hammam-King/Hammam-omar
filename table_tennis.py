import pygame
import sys
import math
import random
import array

# ── Init ──────────────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

WIDTH, HEIGHT = 1000, 620
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Table Tennis")
clock = pygame.time.Clock()

# ── Colours ───────────────────────────────────────────────────────────────────
BG_TOP      = (8,  18, 38)
BG_BOT      = (3,  10, 22)
CYAN        = (0,  230, 255)
CYAN_BRIGHT = (140, 245, 255)
CYAN_DIM    = (0,  140, 180)
RED         = (255,  55, 100)
RED_BRIGHT  = (255, 140, 165)
RED_DIM     = (180,  35,  65)
WHITE       = (255, 255, 255)
GREY        = (100, 125, 160)
DARK_PANEL  = (8,  18,  42)
TABLE_LINE  = (40,  65, 110)
ACCENT_LINE = (255, 255, 255)

# ── Sound synthesis ───────────────────────────────────────────────────────────
SAMPLE_RATE = 44100

def _make_tone(freq, duration, volume=0.5, wave="sine", decay=True):
    n = int(SAMPLE_RATE * duration)
    buf = array.array("h")
    for i in range(n):
        t = i / SAMPLE_RATE
        if wave == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        else:
            v = 2 * (t * freq - math.floor(t * freq + 0.5))
        env = (1 - i / n) if decay else 1.0
        buf.append(int(v * env * volume * 32767))
    return pygame.mixer.Sound(buffer=buf)

def _make_chord(freqs, duration, volume=0.35):
    n = int(SAMPLE_RATE * duration)
    buf = array.array("h")
    for i in range(n):
        t = i / SAMPLE_RATE
        v = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
        env = 1 - i / n
        buf.append(int(v * env * volume * 32767))
    return pygame.mixer.Sound(buffer=buf)

SND_PADDLE  = _make_tone(480, 0.08, 0.55, "sine")
SND_PADDLE2 = _make_tone(600, 0.08, 0.55, "sine")
SND_WALL    = _make_tone(240, 0.06, 0.35, "sine")
SND_SCORE   = _make_chord([523, 659, 784], 0.4, 0.45)
SND_LOSE    = _make_chord([300, 240, 180], 0.5, 0.35)
SND_WIN     = _make_chord([523, 659, 784, 1047], 0.6, 0.4)
SND_COUNT   = _make_tone(700, 0.12, 0.4, "sine")

sfx_on  = True
music_on = True
volume   = 0.8

def play(snd):
    if sfx_on:
        snd.set_volume(volume)
        snd.play()

# ── Fonts ─────────────────────────────────────────────────────────────────────
def load_font(size, bold=False):
    for name in ["Inter", "Segoe UI", "Arial", None]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except:
            pass
    return pygame.font.Font(None, size)

F_HUGE  = load_font(80, bold=True)
F_BIG   = load_font(48, bold=True)
F_MED   = load_font(30, bold=True)
F_SM    = load_font(20)
F_XS    = load_font(15)

# ── Drawing helpers ────────────────────────────────────────────────────────────
def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def draw_text(surf, text, font, color, cx, cy, glow_color=None, glow_r=3):
    if glow_color:
        g = font.render(text, True, glow_color)
        gr = g.get_rect(center=(cx, cy))
        for dx in range(-glow_r, glow_r + 1):
            for dy in range(-glow_r, glow_r + 1):
                if dx*dx + dy*dy <= glow_r*glow_r:
                    surf.blit(g, (gr.x + dx, gr.y + dy))
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(cx, cy))
    surf.blit(rendered, rect)
    return rect

def rounded_rect(surf, color, rect, r=10, alpha=255, border=0, border_col=None):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=r)
    if border and border_col:
        pygame.draw.rect(s, (*border_col, alpha), s.get_rect(), border, border_radius=r)
    surf.blit(s, (rect[0], rect[1]))

COURT_THEMES = {
    "Easy": {
        "bg_top":    (5,  20,  8),
        "bg_bot":    (2,  10,  4),
        "line":      (40, 120, 55),
        "line_dim":  (25,  75, 35),
        "edge_glow": (30, 160, 60),
        "circle":    (35, 110, 50),
        "accent":    (80, 220, 100),
        "name_col":  (80, 220, 100),
    },
    "Medium": {
        "bg_top":    (8,  18, 38),
        "bg_bot":    (3,  10, 22),
        "line":      (40,  65, 130),
        "line_dim":  (30,  50, 100),
        "edge_glow": (0,  120, 200),
        "circle":    (35,  65, 140),
        "accent":    (0,  200, 255),
        "name_col":  (0,  200, 255),
    },
    "Hard": {
        "bg_top":    (24,  5,   5),
        "bg_bot":    (12,  2,   2),
        "line":      (160, 35,  35),
        "line_dim":  (100, 20,  20),
        "edge_glow": (220, 50,  30),
        "circle":    (150, 30,  30),
        "accent":    (255, 80,  40),
        "name_col":  (255, 80,  40),
    },
}

def bg_gradient(diff="Medium"):
    th = COURT_THEMES.get(diff, COURT_THEMES["Medium"])
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = lerp_color(th["bg_top"], th["bg_bot"], t)
        pygame.draw.line(screen, c, (0, y), (WIDTH, y))

# Pre-render glow surfaces for performance
_glow_cache = {}
def get_glow(color, radius):
    key = (color, radius)
    if key not in _glow_cache:
        size = radius * 2 + 2
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        for r in range(radius, 0, -1):
            alpha = int(80 * (r / radius) ** 0.5)
            pygame.draw.circle(s, (*color, alpha), (radius + 1, radius + 1), r)
        _glow_cache[key] = s
    return _glow_cache[key]

# ── Particles ─────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ("x","y","vx","vy","life","decay","size","color")
    def __init__(self, x, y, is_player, strong=False):
        angle = random.uniform(0, math.pi * 2)
        spd = random.uniform(2.5, 6.0) * (1.5 if strong else 1.0)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd
        self.life  = 1.0
        self.decay = random.uniform(0.035, 0.065)
        self.size  = random.uniform(2.5, 5.0) * (1.3 if strong else 1.0)
        self.color = CYAN if is_player else RED

    def update(self):
        self.x  += self.vx;  self.y  += self.vy
        self.vx *= 0.87;     self.vy *= 0.87
        self.life -= self.decay
        return self.life > 0

    def draw(self, surf):
        r = max(1, int(self.size * self.life))
        a = max(0, min(255, int(self.life * 240)))
        s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (r+1, r+1), r)
        surf.blit(s, (int(self.x)-r-1, int(self.y)-r-1))

class Ring:
    __slots__ = ("x","y","r","max_r","life","color")
    def __init__(self, x, y, is_player, max_r=50, is_wall=False):
        self.x, self.y = x, y
        self.r   = 4.0
        self.max_r = float(max_r)
        self.life  = 1.0
        self.color = (180,230,255) if is_wall else (CYAN if is_player else RED)

    def update(self):
        self.life -= 0.055
        progress   = max(0.0, min(1.0, 1.0 - self.life))
        self.r     = max(0.0, 4 + (self.max_r - 4) * progress)
        return self.life > 0

    def draw(self, surf):
        ri = int(self.r)
        if ri < 1: return
        a  = max(0, min(255, int(self.life * 200)))
        s  = pygame.Surface((ri*2+4, ri*2+4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (ri+2, ri+2), ri, 3)
        surf.blit(s, (int(self.x)-ri-2, int(self.y)-ri-2))

particles: list = []
rings:     list = []

def spawn_paddle_hit(x, y, is_player, strong=False):
    count = 16 if strong else 10
    for _ in range(count):
        particles.append(Particle(x, y, is_player, strong))
    rings.append(Ring(x, y, is_player, max_r=60 if strong else 42))
    if strong:
        rings.append(Ring(x, y, is_player, max_r=32))

def spawn_wall_hit(x, y):
    for _ in range(5):
        particles.append(Particle(x, y, True))
        particles[-1].decay *= 1.6
    rings.append(Ring(x, y, True, max_r=28, is_wall=True))

def update_effects():
    global particles, rings
    particles = [p for p in particles if p.update()]
    rings     = [r for r in rings     if r.update()]

def draw_effects(surf):
    for r in rings:    r.draw(surf)
    for p in particles: p.draw(surf)

# ── Difficulty ─────────────────────────────────────────────────────────────────
DIFFICULTIES = {
    "Easy":   {"ball_speed":  10.0, "ai_speed":  5.5, "mistake": 0.30, "zone": 0.45},
    "Medium": {"ball_speed": 12.0, "ai_speed":  9.0, "mistake": 0.12, "zone": 0.65},
    "Hard":   {"ball_speed": 15.0, "ai_speed": 14.0, "mistake": 0.03, "zone": 0.85},
}

# ── Game objects ───────────────────────────────────────────────────────────────
PAD_W, PAD_H = 14, 96
PAD_MARGIN   = 42
BALL_R       = 11
WIN_SCORE    = 7
WIN_MARGIN   = 2
TOTAL_ROUNDS = 3

class Paddle:
    def __init__(self, is_left):
        self.w = PAD_W; self.h = PAD_H
        self.x = PAD_MARGIN if is_left else WIDTH - PAD_MARGIN - PAD_W
        self.y = HEIGHT // 2 - PAD_H // 2
        self.is_left  = is_left
        self.leg_phase = 0.0
        self.hit_anim  = 0.0
        self.move_vel  = 0.0
        self.prev_y    = float(self.y)

    def move(self, dy, speed=8.5):
        self.y = max(0, min(HEIGHT - self.h, self.y + dy * speed))

    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)

    def update_anim(self, dy):
        if abs(dy) > 0.3:
            self.leg_phase += 0.22
        else:
            target = round(self.leg_phase / math.pi) * math.pi
            self.leg_phase += (target - self.leg_phase) * 0.12
        self.hit_anim = max(0.0, self.hit_anim - 0.07)
        dy_norm = max(-1.0, min(1.0, dy))
        self.move_vel += (dy_norm - self.move_vel) * 0.25
        self.prev_y   = self.y

    def trigger_hit(self):
        self.hit_anim = 1.0

    def draw(self, surf):
        color  = CYAN if self.is_left else RED
        bright = CYAN_BRIGHT if self.is_left else RED_BRIGHT
        dim    = CYAN_DIM if self.is_left else RED_DIM
        gc     = (0, 180, 230) if self.is_left else (220, 40, 85)
        skin   = (238, 185, 138)
        hair_c = (28, 18, 12)

        py = self.y
        ph = self.h   # 96

        # Body centre x — behind the paddle (away from ball)
        if self.is_left:
            cx = self.x - 15
        else:
            cx = self.x + self.w + 15

        racket_cx = self.x + self.w // 2

        # Animation state
        swing = math.sin(self.leg_phase) * 7.0
        bob   = int(math.sin(self.leg_phase * 2) * 1.5)
        hit_e = math.sin(self.hit_anim * math.pi)

        # Racket swing rotation & lunge
        swing_phase = (1.0 - math.cos(self.hit_anim * math.pi)) / 2.0
        r_dir       = -1 if self.is_left else 1
        racket_rot  = swing_phase * 28.0 * r_dir + self.move_vel * 5.0 * r_dir
        lunge       = int(swing_phase * 5)
        draw_rx     = racket_cx - lunge * r_dir
        draw_ry     = py + (ph - 24) // 2 + 2

        # ── Soft body glow ──
        gw, gh = 52, ph + 22
        gs = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*gc, 30), gs.get_rect(), border_radius=18)
        surf.blit(gs, (cx - gw // 2, py - 11))

        # ── Head ──
        head_r  = 9
        head_cy = py + 10 + bob
        pygame.draw.circle(surf, skin, (cx, head_cy), head_r)
        # Hair dome (top half ellipse)
        hs = pygame.Surface((head_r * 2 + 2, head_r + 5), pygame.SRCALPHA)
        pygame.draw.ellipse(hs, (*hair_c, 240), hs.get_rect())
        surf.blit(hs, (cx - head_r - 1, head_cy - head_r - 1))
        # Eye facing toward ball / centre
        ex = cx + (3 if self.is_left else -3)
        pygame.draw.circle(surf, (20, 12, 30), (ex, head_cy + 2), 2)

        # ── Neck ──
        pygame.draw.rect(surf, skin, (cx - 3, head_cy + head_r, 6, 5))

        # ── Jersey / Shirt ──
        torso_top = head_cy + head_r + 5
        torso_h   = 26
        torso_w   = 16
        torso_bot = torso_top + torso_h
        rounded_rect(surf, color,
                     (cx - torso_w // 2, torso_top, torso_w, torso_h), r=5)
        # Chest stripe highlight
        rounded_rect(surf, bright,
                     (cx - torso_w // 2 + 2, torso_top + 4, torso_w - 4, 8),
                     r=3, alpha=70)

        # ── Shorts ──
        shorts_top = torso_bot
        shorts_h   = 13
        shorts_w   = 18
        rounded_rect(surf, dim,
                     (cx - shorts_w // 2, shorts_top, shorts_w, shorts_h), r=4)

        # ── Legs (animated running cycle) ──
        legs_top = shorts_top + shorts_h
        leg_h    = 22

        l_kn_x = cx - 3 + int(swing * 0.45)
        l_kn_y = legs_top + leg_h // 2
        r_kn_x = cx + 3 - int(swing * 0.45)
        r_kn_y = legs_top + leg_h // 2
        l_ft_x = cx - 3 + int(swing * 0.9)
        l_ft_y = legs_top + leg_h
        r_ft_x = cx + 3 - int(swing * 0.9)
        r_ft_y = legs_top + leg_h

        pygame.draw.line(surf, skin, (cx - 3, legs_top), (l_kn_x, l_kn_y), 5)
        pygame.draw.line(surf, skin, (l_kn_x, l_kn_y),   (l_ft_x, l_ft_y), 4)
        pygame.draw.line(surf, skin, (cx + 3, legs_top), (r_kn_x, r_kn_y), 5)
        pygame.draw.line(surf, skin, (r_kn_x, r_kn_y),   (r_ft_x, r_ft_y), 4)

        # ── Shoes ──
        shoe_c = (38, 38, 62)
        pygame.draw.ellipse(surf, shoe_c, (l_ft_x - 6, l_ft_y - 3, 10, 6))
        pygame.draw.ellipse(surf, shoe_c, (r_ft_x - 3, r_ft_y - 3, 10, 6))

        # ── Racket arm (upper arm + forearm to paddle) ──
        shoulder_y = torso_top + 4
        if self.is_left:
            shoulder_x = cx + torso_w // 2 - 1
            free_shl_x = cx - torso_w // 2 + 1
        else:
            shoulder_x = cx - torso_w // 2 + 1
            free_shl_x = cx + torso_w // 2 - 1

        elbow_x = shoulder_x + int((draw_rx - shoulder_x) * (0.50 + hit_e * 0.28))
        elbow_y = shoulder_y + int(8 * (1.0 - hit_e * 0.65))
        pygame.draw.line(surf, skin, (shoulder_x, shoulder_y), (elbow_x, elbow_y), 4)
        pygame.draw.line(surf, skin, (elbow_x, elbow_y), (draw_rx, draw_ry), 4)

        # ── Free arm (hanging at side) ──
        free_ex = free_shl_x + (-3 if self.is_left else 3)
        pygame.draw.line(surf, skin,
                         (free_shl_x, shoulder_y), (free_ex, shoulder_y + 10), 4)
        pygame.draw.line(surf, skin,
                         (free_ex, shoulder_y + 10),
                         (free_ex + (-2 if self.is_left else 2), torso_bot), 4)

        # ── Racket (rotation applied) ──
        rh_h     = ph - 24
        rh_w     = self.w + 12
        handle_h = ph - rh_h - 4
        rad      = math.radians(racket_rot)
        hdx      = -math.sin(rad)          # visual "down" x after rotation
        hdy      =  math.cos(rad)          # visual "down" y after rotation
        g_rw, g_rh = rh_w + 20, rh_h + 20

        # Glow (rotated)
        grs = pygame.Surface((g_rw, g_rh), pygame.SRCALPHA)
        pygame.draw.ellipse(grs, (*gc, int(50 + swing_phase * 35)), grs.get_rect())
        grs_rot = pygame.transform.rotate(grs, racket_rot)
        surf.blit(grs_rot, grs_rot.get_rect(center=(draw_rx, draw_ry)))

        # Handle (rotated line from bottom of head toward grip)
        hs_x = int(draw_rx + hdx * (rh_h // 2))
        hs_y = int(draw_ry + hdy * (rh_h // 2))
        he_x = int(hs_x   + hdx * handle_h)
        he_y = int(hs_y   + hdy * handle_h)
        pygame.draw.line(surf, (130, 80, 35), (hs_x, hs_y), (he_x, he_y), 5)

        # Racket head (rotated oval)
        rs = pygame.Surface((rh_w, rh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(rs, (*color, 235), rs.get_rect())
        pygame.draw.ellipse(rs, (*bright, 100), (4, 5, rh_w - 8, rh_h // 3))
        pygame.draw.ellipse(rs, (*bright, 195), rs.get_rect(), 2)
        rs_rot = pygame.transform.rotate(rs, racket_rot)
        surf.blit(rs_rot, rs_rot.get_rect(center=(draw_rx, draw_ry)))

class Ball:
    def __init__(self, speed):
        self.speed = speed
        self.x = float(WIDTH // 2); self.y = float(HEIGHT // 2)
        self.vx = 0.0; self.vy = 0.0
        self.r  = BALL_R
        self.trail: list = []

    def launch(self, direction=1):
        angle = math.radians(random.uniform(-22, 22))
        self.vx = math.cos(angle) * self.speed * direction
        self.vy = math.sin(angle) * self.speed

    def reset(self, direction=1):
        self.x = WIDTH // 2; self.y = HEIGHT // 2
        self.trail.clear()
        self.launch(direction)

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 14: self.trail.pop(0)
        self.x += self.vx; self.y += self.vy

    def draw(self, surf):
        bx, by = int(self.x), int(self.y)

        # ── trail ──
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            t = (i + 1) / (n + 1)
            a = int(t * 100)
            r = max(1, int(self.r * t * 0.75))
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 200, 230, a), (r+1, r+1), r)
            surf.blit(s, (int(tx)-r-1, int(ty)-r-1))

        # ── soft outer glow ──
        for rad, alpha in [(self.r*5, 18), (self.r*3, 38), (self.r*2, 60)]:
            gs = pygame.Surface((rad*2+2, rad*2+2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (0, 220, 245, alpha), (rad+1, rad+1), rad)
            surf.blit(gs, (bx-rad-1, by-rad-1))

        # ── main ball body ──
        pygame.draw.circle(surf, (0, 215, 240), (bx, by), self.r)

        # ── inner bright centre ──
        inner = max(2, self.r - 4)
        cs = pygame.Surface((inner*2+2, inner*2+2), pygame.SRCALPHA)
        pygame.draw.circle(cs, (180, 248, 255, 200), (inner+1, inner+1), inner)
        surf.blit(cs, (bx-inner-1, by-inner-1))

        # ── tiny white rim highlight ──
        pygame.draw.circle(surf, (255, 255, 255), (bx, by), self.r, 1)

# ── AI ─────────────────────────────────────────────────────────────────────────
class AI:
    def __init__(self, cfg):
        self.cfg = cfg
        self.target_y = HEIGHT / 2
        self.mistake_offset = 0
        self.mistake_timer  = 0

    def update(self, paddle, ball):
        cfg = self.cfg
        if self.mistake_timer > 0:
            self.mistake_timer -= 1
        elif random.random() < cfg["mistake"] / FPS * 60:
            self.mistake_offset = random.uniform(-1, 1) * paddle.h * 0.8
            self.mistake_timer  = random.randint(40, 80)

        if ball.vx > 0 and ball.x > WIDTH/2 * (1 - cfg["zone"]):
            self.target_y = ball.y + self.mistake_offset - paddle.h / 2
        else:
            self.target_y += (HEIGHT/2 - paddle.h/2 - self.target_y) * 0.04

        diff  = self.target_y - paddle.y
        move  = min(abs(diff), cfg["ai_speed"])
        paddle.y = max(0, min(HEIGHT-paddle.h, paddle.y + math.copysign(move, diff)))

# ── Table drawing ──────────────────────────────────────────────────────────────
def draw_table(diff="Medium"):
    th  = COURT_THEMES.get(diff, COURT_THEMES["Medium"])
    cx  = WIDTH // 2
    cy  = HEIGHT // 2
    lc  = th["line"]
    acc = th["accent"]
    eg  = th["edge_glow"]

    # ── border ──
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(s, (*acc, 22), (2,2,WIDTH-4,HEIGHT-4), 2, border_radius=4)
    screen.blit(s, (0,0))

    # ── edge glow strips (top & bottom) ──
    for yy in [0, HEIGHT-1]:
        for w in range(6, 0, -1):
            a = max(0, 70 - w*10)
            ps = pygame.Surface((WIDTH, 1), pygame.SRCALPHA)
            ps.fill((*eg, a))
            screen.blit(ps, (0, yy + (w if yy==0 else -w)))

    if diff == "Easy":
        # ── Green court: solid feel with corner markers ──
        dash, gap, y = 22, 10, 0
        while y < HEIGHT:
            pygame.draw.line(screen, lc, (cx,y), (cx, min(y+dash,HEIGHT)), 2)
            y += dash + gap
        pygame.draw.circle(screen, lc, (cx, cy), 62, 2)
        pygame.draw.circle(screen, acc, (cx, cy), 7)
        # friendly corner markers
        for (mx, my) in [(80,40),(WIDTH-80,40),(80,HEIGHT-40),(WIDTH-80,HEIGHT-40)]:
            pygame.draw.line(screen, lc, (mx-16, my), (mx+16, my), 2)
            pygame.draw.line(screen, lc, (mx, my-16), (mx, my+16), 2)
        # subtle half-field zones
        for xx in [cx-180, cx+180]:
            ys = pygame.Surface((2, HEIGHT), pygame.SRCALPHA)
            ys.fill((*lc, 35))
            screen.blit(ys, (xx, 0))

    elif diff == "Medium":
        # ── Blue court: clean professional look ──
        dash, gap, y = 20, 12, 0
        while y < HEIGHT:
            pygame.draw.line(screen, lc, (cx,y), (cx, min(y+dash,HEIGHT)), 2)
            y += dash + gap
        pygame.draw.circle(screen, lc, (cx, cy), 62, 2)
        pygame.draw.circle(screen, acc, (cx, cy), 6)
        # penalty arcs at each end
        pygame.draw.arc(screen, lc,
                        pygame.Rect(PAD_MARGIN+PAD_W, cy-55, 80, 110),
                        -math.pi/2, math.pi/2, 1)
        pygame.draw.arc(screen, lc,
                        pygame.Rect(WIDTH-PAD_MARGIN-PAD_W-80, cy-55, 80, 110),
                        math.pi/2, 3*math.pi/2, 1)

    elif diff == "Hard":
        # ── Red/fire court: aggressive diagonal accents ──
        dash, gap, y = 16, 8, 0
        while y < HEIGHT:
            pygame.draw.line(screen, lc, (cx,y), (cx, min(y+dash,HEIGHT)), 3)
            y += dash + gap
        pygame.draw.circle(screen, lc, (cx, cy), 62, 2)
        pygame.draw.circle(screen, acc, (cx, cy), 8)
        # danger zone diagonals in corners
        for (x1,y1,x2,y2) in [
            (0,0,  60,60),  (WIDTH,0,  WIDTH-60,60),
            (0,HEIGHT,60,HEIGHT-60),(WIDTH,HEIGHT,WIDTH-60,HEIGHT-60)
        ]:
            pygame.draw.line(screen, (*lc,100), (x1,y1), (x2,y2), 2)
        # aggressive double line at net
        pygame.draw.line(screen, lc, (cx-3, 0), (cx-3, HEIGHT), 1)
        pygame.draw.line(screen, lc, (cx+3, 0), (cx+3, HEIGHT), 1)
        # side warning stripes near walls
        for yy in range(0, HEIGHT, 40):
            pygame.draw.line(screen, (*acc, 40), (0,yy), (20,yy+20), 1)
            pygame.draw.line(screen, (*acc, 40), (WIDTH,yy), (WIDTH-20,yy+20), 1)

# ── Score / HUD ────────────────────────────────────────────────────────────────
def draw_score(sl, sr, rl, rr, rnd, flash=None, is_2p=False):
    cx = WIDTH // 2
    lc = CYAN_BRIGHT if flash == "player" else WHITE
    rc = RED_BRIGHT  if flash == "ai"     else WHITE
    lg = CYAN if flash == "player" else None
    rg = RED  if flash == "ai"     else None
    draw_text(screen, str(sl), F_HUGE, lc, cx//2,        50, glow_color=lg, glow_r=2)
    draw_text(screen, str(sr), F_HUGE, rc, cx+cx//2,     50, glow_color=rg, glow_r=2)
    info = f"Round {rnd}  •  Best of {TOTAL_ROUNDS}{'  •  2P' if is_2p else ''}"
    draw_text(screen, info, F_XS, GREY, cx, 96)
    # round pips
    needed = math.ceil(TOTAL_ROUNDS/2)
    gap = 20
    for i in range(needed):
        px = cx//2 - (needed-1)*gap//2 + i*gap
        pygame.draw.circle(screen, CYAN if i < rl else (35,50,80), (px,87), 5)
    for i in range(needed):
        px = cx+cx//2 - (needed-1)*gap//2 + i*gap
        pygame.draw.circle(screen, RED  if i < rr else (35,50,80), (px,87), 5)

def draw_player_labels(is_2p):
    cx = WIDTH // 2
    def label(text, color, x, y):
        s = F_XS.render(text, True, color)
        screen.blit(s, s.get_rect(center=(x,y)))
    label("P1  W/S" if is_2p else "YOU  W/S", (*CYAN,160),  cx//2,        HEIGHT-22)
    label("P2  ↑↓"  if is_2p else "AI",        (*RED, 160),  cx+cx//2,     HEIGHT-22)

def draw_hud(diff_name, is_2p):
    lbl = F_XS.render(
        f"{diff_name}  •  SFX:{'ON' if sfx_on else 'OFF'}  •  Vol:{int(volume*100)}%",
        True, (70,95,130))
    screen.blit(lbl, (10, HEIGHT-16))
    rbl = F_XS.render(
        "ESC Pause  •  P1:W/S  •  P2:↑↓" if is_2p else "ESC Pause  •  W/S Move",
        True, (70,95,130))
    screen.blit(rbl, rbl.get_rect(right=WIDTH-10, bottom=HEIGHT-2))

def draw_overlay_panel(title, title_color, lines):
    cx, cy = WIDTH//2, HEIGHT//2
    pw = 540; ph = 90 + len(lines)*40 + 48
    rounded_rect(screen, DARK_PANEL, (cx-pw//2, cy-ph//2, pw, ph),
                 r=18, alpha=240, border=2, border_col=(50,80,130))
    draw_text(screen, title, F_BIG, title_color, cx, cy-ph//2+44,
              glow_color=title_color, glow_r=2)
    for i, line in enumerate(lines):
        t = F_SM.render(line, True, (180,205,235))
        screen.blit(t, t.get_rect(center=(cx, cy-ph//2+90+i*40)))

# ── Menu ───────────────────────────────────────────────────────────────────────
class Menu:
    def __init__(self):
        self.mode = "1P"
        self.difficulty = "Medium"

    def run(self):
        global sfx_on, music_on, volume
        while True:
            clock.tick(FPS)
            bg_gradient()
            draw_table()
            cx, cy = WIDTH//2, HEIGHT//2

            # ── Title ──
            t1 = F_BIG.render("TABLE", True, CYAN)
            t2 = F_BIG.render("TENNIS", True, WHITE)
            tw = t1.get_width() + 14 + t2.get_width()
            # glow behind title
            for dx in range(-2,3):
                for dyd in range(-2,3):
                    g = F_BIG.render("TABLE", True, CYAN_DIM)
                    screen.blit(g, (cx-tw//2+dx, cy-205+dyd))
            screen.blit(t1, (cx-tw//2, cy-205))
            screen.blit(t2, (cx-tw//2+t1.get_width()+14, cy-205))

            # ── Mode tabs ──
            tab_w, tab_h = 188, 42
            tab_gap = 10
            total_w = tab_w*2 + tab_gap
            t1r = pygame.Rect(cx-total_w//2,            cy-150, tab_w, tab_h)
            t2r = pygame.Rect(cx-total_w//2+tab_w+tab_gap, cy-150, tab_w, tab_h)
            for rect, label, mode_id in [(t1r,"1 Player vs AI","1P"),(t2r,"2 Players","2P")]:
                active = self.mode == mode_id
                rounded_rect(screen,
                             (15,45,80) if active else (12,22,42),
                             rect, r=10, alpha=220,
                             border=2, border_col=(CYAN if active else (45,65,100)))
                col = CYAN_BRIGHT if active else GREY
                draw_text(screen, label, F_SM, col, rect.centerx, rect.centery)

            if self.mode == "1P":
                # Sub-label
                sub = F_XS.render("SELECT DIFFICULTY", True, GREY)
                screen.blit(sub, sub.get_rect(center=(cx, cy-95)))
                diff_list   = ["Easy",       "Medium",             "Hard"]
                diff_colors = [(54,215,153), (251,195, 35),  (255,90,90)]
                diff_hints  = ["Slow AI · Forgiving",
                               "Balanced Challenge",
                               "Fast AI · No Mercy"]
                btn_rects = []
                for i,(d,col,hint) in enumerate(zip(diff_list,diff_colors,diff_hints)):
                    r = pygame.Rect(cx-175, cy-66+i*65, 350, 56)
                    btn_rects.append((r, d))
                    sel = self.difficulty == d
                    rounded_rect(screen, (15,28,52), r, r=12, alpha=210,
                                 border=2, border_col=(col if sel else (35,55,85)))
                    # accent bar
                    pygame.draw.rect(screen, col, (r.x, r.y+5, 4, r.h-10), border_radius=2)
                    dl = F_SM.render(d, True, WHITE)
                    hl = F_XS.render(hint, True, GREY)
                    screen.blit(dl, (r.x+18, r.y+9))
                    screen.blit(hl, (r.x+18, r.y+33))

            else:
                sub = F_XS.render("LOCAL MULTIPLAYER", True, GREY)
                screen.blit(sub, sub.get_rect(center=(cx, cy-95)))
                cw, ch = 158, 110
                c1r = pygame.Rect(cx-cw-16, cy-80, cw, ch)
                c2r = pygame.Rect(cx+16,    cy-80, cw, ch)
                rounded_rect(screen,(0,38,68), c1r, r=14, alpha=220,
                             border=2, border_col=CYAN_DIM)
                rounded_rect(screen,(68,14,28), c2r, r=14, alpha=220,
                             border=2, border_col=RED_DIM)
                vs = F_SM.render("VS", True, GREY)
                screen.blit(vs, vs.get_rect(center=(cx, cy-80+ch//2)))
                for rect,(label,key,col) in zip([c1r,c2r],[
                        ("Player 1","W / S",CYAN),
                        ("Player 2","↑ / ↓",RED)]):
                    draw_text(screen, label, F_XS, col,            rect.centerx, rect.y+20)
                    draw_text(screen, "Left Paddle" if col==CYAN else "Right Paddle",
                              F_XS, GREY,                          rect.centerx, rect.y+38)
                    draw_text(screen, key,   F_MED, col,           rect.centerx, rect.y+75)
                # Start
                sr = pygame.Rect(cx-155, cy+45, 310, 52)
                rounded_rect(screen,(0,50,85), sr, r=13, alpha=220,
                             border=2, border_col=CYAN_DIM)
                draw_text(screen, "START MATCH", F_SM, CYAN_BRIGHT, sr.centerx, sr.centery)

            # ── Audio controls ──
            ctrl_y = cy+130
            sfx_r = pygame.Rect(cx-205, ctrl_y, 125, 34)
            mus_r = pygame.Rect(cx-65,  ctrl_y, 110, 34)
            rounded_rect(screen,(12,28,50), sfx_r, r=8, alpha=210,
                         border=1, border_col=(CYAN_DIM if sfx_on else (40,60,90)))
            rounded_rect(screen,(12,28,50), mus_r, r=8, alpha=210,
                         border=1, border_col=(CYAN_DIM if music_on else (40,60,90)))
            draw_text(screen,f"SFX: {'ON' if sfx_on else 'OFF'}", F_XS,
                      CYAN if sfx_on else GREY, sfx_r.centerx, sfx_r.centery)
            draw_text(screen,f"Music: {'ON' if music_on else 'OFF'}", F_XS,
                      CYAN if music_on else GREY, mus_r.centerx, mus_r.centery)
            # volume slider
            vx, vy, vw = cx+55, ctrl_y+10, 150
            vl = F_XS.render(f"Vol: {int(volume*100)}%", True, GREY)
            screen.blit(vl,(vx, vy-12))
            pygame.draw.rect(screen,(25,45,75),(vx,vy,vw,8), border_radius=4)
            pygame.draw.rect(screen,CYAN_DIM,   (vx,vy,int(vw*volume),8), border_radius=4)

            hint = F_XS.render("← → adjust volume    ESC quit", True, (50,70,100))
            screen.blit(hint, hint.get_rect(center=(cx, HEIGHT-18)))

            pygame.display.flip()

            mouse = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                    if event.key == pygame.K_LEFT:
                        volume = max(0.0, volume-0.05)
                    if event.key == pygame.K_RIGHT:
                        volume = min(1.0, volume+0.05)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if t1r.collidepoint(mouse): self.mode = "1P"
                    if t2r.collidepoint(mouse): self.mode = "2P"
                    if sfx_r.collidepoint(mouse): sfx_on = not sfx_on
                    if mus_r.collidepoint(mouse): music_on = not music_on
                    if self.mode == "1P":
                        for rect, d in btn_rects:
                            if rect.collidepoint(mouse):
                                self.difficulty = d
                                return self.mode, self.difficulty
                    else:
                        if 'sr' in dir() and sr.collidepoint(mouse):
                            return self.mode, self.difficulty

# ── Game ───────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self, mode, diff_name):
        cfg = DIFFICULTIES[diff_name]
        self.mode      = mode
        self.diff_key  = diff_name          # raw key: "Easy"/"Medium"/"Hard"
        self.diff_name = diff_name if mode == "1P" else "2 Players"
        self.cfg       = cfg
        self.ball      = Ball(cfg["ball_speed"])
        self.pl        = Paddle(True)
        self.pr        = Paddle(False)
        self.ai        = AI(cfg) if mode == "1P" else None
        self.sl = self.sr = self.rl = self.rr = 0
        self.rnd       = 1
        self.state     = "COUNTDOWN"
        self.countdown = 3
        self.cd_timer  = 0.0
        self.flash     = None
        self.flash_t   = 0
        self.winner_l  = False
        self.ball.reset(1)
        particles.clear(); rings.clear()

    def reset_round(self):
        self.sl = self.sr = 0
        self.pl.y = self.pr.y = HEIGHT//2 - PAD_H//2
        self.state = "COUNTDOWN"; self.countdown = 3; self.cd_timer = 0.0
        self.ball.reset(1 if random.random()>0.5 else -1)
        particles.clear(); rings.clear()

    def _check_round(self):
        lw = self.sl >= WIN_SCORE and self.sl - self.sr >= WIN_MARGIN
        rw = self.sr >= WIN_SCORE and self.sr - self.sl >= WIN_MARGIN
        if lw or rw:
            self.winner_l = lw
            if lw: self.rl += 1
            else:  self.rr += 1
            needed = math.ceil(TOTAL_ROUNDS/2)
            if self.rl >= needed or self.rr >= needed:
                self.state = "GAME_OVER"
            else:
                self.rnd += 1; self.state = "ROUND_OVER"
            play(SND_WIN if lw else SND_LOSE)
            return True
        return False

    def update(self, dt):
        if self.state == "COUNTDOWN":
            self.cd_timer += dt
            if self.cd_timer >= 1.0:
                self.cd_timer = 0.0; self.countdown -= 1
                if self.countdown >= 0: play(SND_COUNT)
                if self.countdown < 0: self.state = "PLAYING"
            return

        if self.state != "PLAYING": return

        keys = pygame.key.get_pressed()
        dy_l = (-1 if keys[pygame.K_w] else 0) + (1 if keys[pygame.K_s] else 0)
        self.pl.move(dy_l)
        self.pl.update_anim(dy_l)
        if self.mode == "2P":
            dy_r = (-1 if keys[pygame.K_UP] else 0) + (1 if keys[pygame.K_DOWN] else 0)
            self.pr.move(dy_r)
            self.pr.update_anim(dy_r)
        else:
            self.ai.update(self.pr, self.ball)
            self.pr.update_anim(self.pr.y - self.pr.prev_y)

        update_effects()
        self.ball.update()

        bx, by, r = self.ball.x, self.ball.y, self.ball.r

        # Wall
        if by - r <= 0:
            self.ball.y = r; self.ball.vy = abs(self.ball.vy)
            play(SND_WALL); spawn_wall_hit(bx, r)
        elif by + r >= HEIGHT:
            self.ball.y = HEIGHT - r; self.ball.vy = -abs(self.ball.vy)
            play(SND_WALL); spawn_wall_hit(bx, HEIGHT - r)

        # Paddles
        for pad, is_left in [(self.pl, True), (self.pr, False)]:
            pr = pad.rect()
            if (pr.left-r < bx < pr.right+r and pr.top-r < by < pr.bottom+r):
                going_right = self.ball.vx > 0
                if (is_left and not going_right) or (not is_left and going_right):
                    hit_pos = (by - pr.centery) / (pr.height/2)
                    angle   = hit_pos * math.radians(58)
                    spd     = math.hypot(self.ball.vx, self.ball.vy)
                    new_spd = min(spd*1.06, self.cfg["ball_speed"]*2.3)
                    self.ball.vx = math.cos(angle)*new_spd*(1 if is_left else -1)
                    self.ball.vy = math.sin(angle)*new_spd
                    self.ball.x  = (pr.right+r+1) if is_left else (pr.left-r-1)
                    strong = new_spd > self.cfg["ball_speed"] * 1.4
                    play(SND_PADDLE2 if strong else SND_PADDLE)
                    spawn_paddle_hit(self.ball.x, self.ball.y, is_left, strong)
                    pad.trigger_hit()

        # Scoring
        if bx + r < 0:
            self.sr += 1; self.flash = "ai"
            self.flash_t = int(FPS*0.65)
            play(SND_SCORE)
            if not self._check_round():
                self.ball.reset(1)
        elif bx - r > WIDTH:
            self.sl += 1; self.flash = "player"
            self.flash_t = int(FPS*0.65)
            play(SND_SCORE)
            if not self._check_round():
                self.ball.reset(-1)

        if self.flash_t > 0: self.flash_t -= 1
        else: self.flash = None

    def draw(self):
        dk = self.diff_key if self.mode == "1P" else "Medium"
        bg_gradient(dk)
        draw_table(dk)
        draw_score(self.sl, self.sr, self.rl, self.rr, self.rnd,
                   self.flash, is_2p=(self.mode=="2P"))
        draw_player_labels(self.mode=="2P")
        draw_hud(self.diff_name, self.mode=="2P")
        self.pl.draw(screen)
        self.pr.draw(screen)
        self.ball.draw(screen)
        draw_effects(screen)

        if self.state == "COUNTDOWN":
            label = "GO!" if self.countdown==0 else str(self.countdown)
            col   = CYAN_BRIGHT if self.countdown==0 else WHITE
            draw_text(screen, label, F_HUGE, col,
                      WIDTH//2, HEIGHT//2, glow_color=CYAN, glow_r=3)

        elif self.state == "PAUSED":
            ov = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
            ov.fill((0,0,0,145)); screen.blit(ov,(0,0))
            draw_overlay_panel("PAUSED", WHITE, [
                "ESC — Resume",
                "Q — Quit to Menu",
                "M — Toggle Music",
                "S — Toggle SFX",
                "P1:W/S  •  P2:↑↓" if self.mode=="2P" else "W/S or ↑↓ to move",
            ])

        elif self.state == "ROUND_OVER":
            ov = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
            ov.fill((0,0,0,155)); screen.blit(ov,(0,0))
            is2p = self.mode=="2P"
            title = ("P1 Wins Round!" if self.winner_l else "P2 Wins Round!") if is2p \
                    else ("Round Won!" if self.winner_l else "Round Lost")
            col = CYAN if self.winner_l else RED
            draw_overlay_panel(title, col,
                [f"{self.rl} — {self.rr} Rounds", "SPACE to continue"])

        elif self.state == "GAME_OVER":
            ov = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
            ov.fill((0,0,0,165)); screen.blit(ov,(0,0))
            is2p = self.mode=="2P"
            title = ("P1 Wins!" if self.winner_l else "P2 Wins!") if is2p \
                    else ("Victory!" if self.winner_l else "Defeat")
            col  = CYAN if self.winner_l else RED
            who  = ("P1" if is2p else "You") if self.winner_l else ("P2" if is2p else "AI")
            wr   = self.rl if self.winner_l else self.rr
            lr   = self.rr if self.winner_l else self.rl
            draw_overlay_panel(title, col,
                [f"{who} won {wr}–{lr} rounds",
                 "SPACE — Play Again  •  Q — Menu"])

        pygame.display.flip()

    def handle(self, event):
        global sfx_on, music_on, volume
        if event.type != pygame.KEYDOWN: return None
        k = event.key
        if self.state == "PLAYING":
            if k == pygame.K_ESCAPE: self.state = "PAUSED"
            if k == pygame.K_m: music_on = not music_on
            if k == pygame.K_s and self.mode=="1P": sfx_on = not sfx_on
            if self.mode == "1P":
                if k == pygame.K_UP:   volume = min(1.0, volume+0.05)
                if k == pygame.K_DOWN: volume = max(0.0, volume-0.05)
        elif self.state == "PAUSED":
            if k == pygame.K_ESCAPE: self.state = "PLAYING"
            if k == pygame.K_q:      return "MENU"
            if k == pygame.K_m:      music_on = not music_on
            if k == pygame.K_s:      sfx_on   = not sfx_on
            if k == pygame.K_UP:     volume = min(1.0, volume+0.05)
            if k == pygame.K_DOWN:   volume = max(0.0, volume-0.05)
        elif self.state == "ROUND_OVER":
            if k == pygame.K_SPACE: self.reset_round()
        elif self.state == "GAME_OVER":
            if k == pygame.K_SPACE: return "RESTART"
            if k == pygame.K_q:     return "MENU"
        return None

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    menu = Menu()
    while True:
        mode, diff = menu.run()
        game = Game(mode, diff)
        while True:
            dt = clock.tick(FPS) / 1000.0
            game.update(dt)
            game.draw()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                result = game.handle(event)
                if result == "MENU":  game = None; break
                if result == "RESTART": game = Game(mode, diff)
            if game is None: break

if __name__ == "__main__":
    main()
