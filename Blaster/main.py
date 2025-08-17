# Blaster - Controls
# Move: WASD
# Aim: Mouse
# Shoot: Hold Left Mouse Button
# Dash: Space
# Pause: P
# Start: Click "Play" or press Enter
# Restart: R (on Game Over)
# Quit: Esc

import os
import json
import math
import random
from dataclasses import dataclass
from typing import List, Tuple
import pygame as pg

# basic setup
WIDTH, HEIGHT = 960, 540
FPS = 60
TITLE = "Byte Blaster"
FONT_NAME = "freesansbold.ttf"
SAVE_FILE = "byte_blaster_save.json"  # keeps best score
MUSIC_PATH = "music.mp3"              
MUSIC_VOLUME = 0.35
MAX_LIVES = 3

# colors
WHITE  = (235, 235, 235)
BLACK  = (18, 18, 22)
GRAY   = (90, 92, 98)
RED    = (230, 85, 80)
GREEN  = (90, 220, 120)
YELLOW = (240, 220, 120)
CYAN   = (120, 220, 230)
PURPLE = (175, 120, 245)
ORANGE = (255, 170, 70)
PINK   = (255, 120, 200)
BLUE   = (80, 160, 255)

# palettes for fun colors
ENEMY_COLORS  = [ORANGE, PURPLE, PINK, RED, BLUE, YELLOW, GREEN, CYAN]
BULLET_COLORS = [YELLOW, CYAN, PINK, WHITE, BLUE, ORANGE]
PARTICLE_COLS = [YELLOW, ORANGE, PINK, PURPLE, CYAN, BLUE, GREEN, WHITE]

vec2 = pg.math.Vector2

# keep numbers inside a range
def clamp(v, a, b):
    if v < a: return a
    if v > b: return b
    return v

# load the best score from a file
def load_best():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
        except:
            return {"high_score": 0}
    return {"high_score": 0}

# save the best score to a file
def save_best(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

# background star (moves down)
class Star:
    def __init__(self):
        self.pos = vec2(random.randint(0, WIDTH), random.randint(0, HEIGHT))
        self.speed = random.uniform(30, 120)
        self.size = random.randint(1, 3)
        self.color = (random.randint(180, 255), random.randint(180, 255), random.randint(180, 255))

    def update(self, dt):
        self.pos.y += self.speed * dt
        if self.pos.y > HEIGHT:
            self.pos.y = 0
            self.pos.x = random.randint(0, WIDTH)

    def draw(self, surf):
        pg.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), self.size)

# bullets the player fires
@dataclass
class Bullet:
    pos: vec2
    vel: vec2
    life: float
    radius: float
    color: Tuple[int, int, int]

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt

    def alive(self):
        return self.life > 0

    def draw(self, surf):
        pg.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), int(self.radius))

# small dots for effects
@dataclass
class Particle:
    pos: vec2
    vel: vec2
    life: float
    radius: float
    color: Tuple[int, int, int]

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
        self.radius = max(0, self.radius - dt * 25)

    def alive(self):
        return self.life > 0 and self.radius > 0.5

    def draw(self, surf):
        if self.radius > 0:
            pg.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), int(self.radius))

# bad guys that chase the player
class Enemy:
    def __init__(self, pos, speed, hp, size):
        self.pos = vec2(pos)
        self.speed = speed
        self.hp = hp
        self.size = size
        self.color = random.choice(ENEMY_COLORS)
        self.knock = vec2()

    def update(self, dt, target):
        move_dir = target - self.pos
        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalize()
        move = move_dir * self.speed + self.knock
        self.pos += move * dt
        self.knock *= 0.9
        self.pos.x = clamp(self.pos.x, 10, WIDTH - 10)
        self.pos.y = clamp(self.pos.y, 10, HEIGHT - 10)

    def hit(self, power, impulse):
        self.hp -= int(power)
        self.knock += impulse

    def dead(self):
        return self.hp <= 0

    def draw(self, surf):
        pg.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), int(self.size))

# the player
class Player:
    def __init__(self, pos):
        self.pos = vec2(pos)
        self.speed = 260
        self.radius = 14
        self.color = CYAN
        self.reload_time = 0.12
        self.cooldown = 0.0
        self.bullet_speed = 600
        self.damage = 1
        self.lives = MAX_LIVES
        self.invincible = 0.0
        self.dash_cd = 0.0
        self._bullet_i = 0  # picks bullet color

    def update(self, dt, keys):
        move = vec2(0, 0)
        if keys[pg.K_w]: move.y -= 1
        if keys[pg.K_s]: move.y += 1
        if keys[pg.K_a]: move.x -= 1
        if keys[pg.K_d]: move.x += 1
        if move.length_squared() > 0:
            move = move.normalize()
        self.pos += move * self.speed * dt
        self.pos.x = clamp(self.pos.x, 16, WIDTH - 16)
        self.pos.y = clamp(self.pos.y, 16, HEIGHT - 16)
        self.cooldown = max(0, self.cooldown - dt)
        self.invincible = max(0, self.invincible - dt)
        self.dash_cd = max(0, self.dash_cd - dt)

    def can_shoot(self):
        return self.cooldown <= 0

    def shoot(self, mouse_pos):
        self.cooldown = self.reload_time
        direction = mouse_pos - self.pos
        if direction.length_squared() == 0:
            direction = vec2(1, 0)
        direction = direction.normalize()
        start = self.pos + direction * (self.radius + 6)
        color = BULLET_COLORS[self._bullet_i % len(BULLET_COLORS)]
        self._bullet_i += 1
        return Bullet(start, direction * self.bullet_speed, 0.6, 4, color)

    def dash(self):
        if self.dash_cd > 0:
            return
        mouse = vec2(pg.mouse.get_pos())
        d = mouse - self.pos
        if d.length_squared() == 0:
            return
        d = d.normalize() * 240
        self.pos += d
        self.invincible = 0.25
        self.dash_cd = 1.2

    def take_hit(self):
        if self.invincible > 0:
            return False
        self.lives -= 1
        self.invincible = 0.6
        return True

    def dead(self):
        return self.lives <= 0

    def draw(self, surf):
        col = GREEN if self.invincible > 0 else self.color
        pg.draw.circle(surf, col, (int(self.pos.x), int(self.pos.y)), int(self.radius))
        mpos = vec2(pg.mouse.get_pos())
        d = mpos - self.pos
        if d.length_squared() > 0:
            d = d.normalize() * (self.radius + 6)
            pg.draw.line(surf, WHITE, self.pos, self.pos + d, 2)

# spawns enemies over time
class Spawner:
    def __init__(self):
        self.wave = 1
        self.reset_wave()

    def reset_wave(self):
        self.to_spawn = 5 + self.wave * 2
        self.spawn_gap = max(0.5, 1.7 - self.wave * 0.06)
        self.timer = self.spawn_gap

    def update(self, dt, enemies):
        self.timer -= dt
        if self.timer <= 0 and self.to_spawn > 0:
            self.timer = self.spawn_gap
            self.spawn_enemy(enemies)
            self.to_spawn -= 1
        if self.to_spawn == 0 and not enemies:
            self.wave += 1
            self.reset_wave()

    def spawn_enemy(self, enemies):
        margin = 28
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            pos = vec2(random.randint(margin, WIDTH - margin), -margin)
        elif side == "bottom":
            pos = vec2(random.randint(margin, WIDTH - margin), HEIGHT + margin)
        elif side == "left":
            pos = vec2(-margin, random.randint(margin, HEIGHT - margin))
        else:
            pos = vec2(WIDTH + margin, random.randint(margin, HEIGHT - margin))
        speed = 90 + self.wave * 6 + random.randint(-10, 20)
        hp = 2 + self.wave // 3
        size = max(12, min(22, 12 + self.wave * 0.3))
        enemies.append(Enemy(pos, speed, hp, size))

# the game itself
class Game:
    def __init__(self):
        pg.init()
        try:
            pg.mixer.init()
        except:
            pass
        pg.display.set_caption(TITLE)
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        self.clock = pg.time.Clock()
        self.font = pg.font.Font(FONT_NAME, 20)
        self.bigfont = pg.font.Font(FONT_NAME, 48)

        self.mode = "start"  
        self.paused = False
        self.score = 0
        self.save = load_best()

        self.play_button = pg.Rect(0, 0, 220, 60)
        self.play_button.center = (WIDTH // 2, HEIGHT // 2 + 30)

        self.player = Player(vec2(WIDTH / 2, HEIGHT / 2))
        self.bullets: List[Bullet] = []
        self.enemies: List[Enemy] = []
        self.particles: List[Particle] = []
        self.spawner = Spawner()

        self.time = 0.0  # used for background color
        self.stars = [Star() for _ in range(140)]  # lots of little stars

        self.start_music()

    # start background music if possible
    def start_music(self):
        if not pg.mixer.get_init():
            return
        try:
            if os.path.exists(MUSIC_PATH):
                pg.mixer.music.load(MUSIC_PATH)
                pg.mixer.music.set_volume(MUSIC_VOLUME)
                pg.mixer.music.play(-1)
        except:
            pass

    # reset game state for a new run
    def reset(self):
        self.player = Player(vec2(WIDTH / 2, HEIGHT / 2))
        self.bullets = []
        self.enemies = []
        self.particles = []
        self.spawner = Spawner()
        self.score = 0
        self.paused = False
        self.time = 0.0
        self.stars = [Star() for _ in range(140)]

    # main loop
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if self.mode == "play" and not self.paused:
                self.update(dt)
            self.draw()

    # inputs
    def handle_events(self):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.quit_game()
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_ESCAPE:
                    self.quit_game()
                if e.key == pg.K_RETURN and self.mode == "start":
                    self.mode = "play"
                if e.key == pg.K_p and self.mode == "play":
                    self.paused = not self.paused
                if e.key == pg.K_r and self.mode == "gameover":
                    self.mode = "start"
                    self.reset()
                if e.key == pg.K_SPACE and self.mode == "play" and not self.paused:
                    self.player.dash()
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1 and self.mode == "start":
                if self.play_button.collidepoint(e.pos):
                    self.mode = "play"

        # hold left click to shoot
        if self.mode == "play" and not self.paused:
            if pg.mouse.get_pressed()[0] and self.player.can_shoot():
                self.bullets.append(self.player.shoot(vec2(pg.mouse.get_pos())))
                self.spawn_muzzle_particles(self.player.pos)

    # update world
    def update(self, dt):
        self.time += dt

        for s in self.stars:
            s.update(dt)

        keys = pg.key.get_pressed()
        self.player.update(dt, keys)
        self.spawner.update(dt, self.enemies)

        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if b.alive()
                        and 0 <= b.pos.x <= WIDTH and 0 <= b.pos.y <= HEIGHT]

        for en in self.enemies:
            en.update(dt, self.player.pos)

        # bullets hit enemies
        for en in list(self.enemies):
            for b in list(self.bullets):
                if (en.pos - b.pos).length_squared() <= (en.size + b.radius) ** 2:
                    en.hit(self.player.damage, vec2(0, 0))
                    self.bullets.remove(b)
                    self.spawn_hit_particles(b.pos)
                    if en.dead():
                        self.enemies.remove(en)
                        self.score += 10
                        self.spawn_death_particles(en.pos, en.color)
                    break

        # enemies touch player
        for en in list(self.enemies):
            if (en.pos - self.player.pos).length_squared() <= (en.size + self.player.radius) ** 2:
                if self.player.take_hit():
                    self.spawn_damage_particles(self.player.pos)
                # push enemy a bit away so it doesn't stick
                sep = en.pos - self.player.pos
                if sep.length_squared() > 0:
                    sep = sep.normalize() * (en.size + self.player.radius + 1)
                    en.pos = self.player.pos + sep

        # player died?
        if self.player.dead():
            self.mode = "gameover"
            if self.score > self.save.get("high_score", 0):
                self.save["high_score"] = self.score
                save_best(self.save)

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive()]

    # colorful particles when shooting
    def spawn_muzzle_particles(self, pos):
        for _ in range(6):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(40, 140)
            col = random.choice(PARTICLE_COLS)
            self.particles.append(Particle(vec2(pos),
                                           vec2(math.cos(ang), math.sin(ang)) * spd,
                                           0.2, 3, col))

    # colorful particles when a bullet hits
    def spawn_hit_particles(self, pos):
        for _ in range(12):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(60, 180)
            col = random.choice(PARTICLE_COLS)
            self.particles.append(Particle(vec2(pos),
                                           vec2(math.cos(ang), math.sin(ang)) * spd,
                                           0.35, 3, col))

    # colorful explosion when enemy dies
    def spawn_death_particles(self, pos, main_color):
        for _ in range(20):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(50, 240)
            # mix the enemy color with a random one
            rc = random.choice(PARTICLE_COLS)
            mix = 0.5
            col = (int(main_color[0]*mix + rc[0]*(1-mix)),
                   int(main_color[1]*mix + rc[1]*(1-mix)),
                   int(main_color[2]*mix + rc[2]*(1-mix)))
            self.particles.append(Particle(vec2(pos),
                                           vec2(math.cos(ang), math.sin(ang)) * spd,
                                           0.6, 4, col))

    # colorful puff when player gets hit
    def spawn_damage_particles(self, pos):
        for _ in range(16):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(60, 200)
            col = random.choice([RED, ORANGE, PINK, YELLOW])
            self.particles.append(Particle(vec2(pos),
                                           vec2(math.cos(ang), math.sin(ang)) * spd,
                                           0.45, 3, col))

    # smooth background color that changes over time
    def get_bg_color(self):
        t = self.time
        r = int(18 + 40 * (math.sin(t * 0.5 + 0) * 0.5 + 0.5))
        g = int(18 + 40 * (math.sin(t * 0.5 + 2) * 0.5 + 0.5))
        b = int(22 + 40 * (math.sin(t * 0.5 + 4) * 0.5 + 0.5))
        return (r, g, b)

    # draw everything
    def draw(self):
        self.screen.fill(self.get_bg_color())

        # stars first so they sit behind everything
        for s in self.stars:
            s.draw(self.screen)

        if self.mode in ("play", "gameover"):
            for p in self.particles:
                p.draw(self.screen)
            for b in self.bullets:
                b.draw(self.screen)
            for e in self.enemies:
                e.draw(self.screen)
            self.player.draw(self.screen)
            self.draw_hud()

        if self.mode == "start":
            self.draw_start()
        elif self.mode == "gameover":
            self.overlay_text("Game Over", "Press R to restart")

        pg.display.flip()

    # top-left info
    def draw_hud(self):
        # lives
        for i in range(MAX_LIVES):
            col = RED if i >= self.player.lives else GREEN
            pg.draw.rect(self.screen, col, pg.Rect(20 + i * 22, 16, 18, 12), border_radius=3)
        # score and wave
        self.screen.blit(self.font.render(f"Score: {self.score}", True, WHITE), (20, 36))
        self.screen.blit(self.font.render(f"Wave {self.spawner.wave}", True, WHITE), (WIDTH - 140, 16))
        self.screen.blit(self.font.render(f"Best: {self.save.get('high_score', 0)}", True, GRAY), (WIDTH - 140, 36))
        if self.paused:
            self.overlay_text("Paused", "Press P to resume")

    # start screen button and tip
    def draw_start(self):
        title = self.bigfont.render(TITLE, True, WHITE)
        tip = self.font.render("WASD move • Mouse aim • Hold LMB to shoot", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 80)))
        self.screen.blit(tip, tip.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 35)))
        pg.draw.rect(self.screen, CYAN, self.play_button, border_radius=12)
        label = self.font.render("Play", True, BLACK)
        self.screen.blit(label, label.get_rect(center=self.play_button.center))
        hint = self.font.render("Or press Enter", True, GRAY)
        self.screen.blit(hint, hint.get_rect(center=(WIDTH / 2, self.play_button.bottom + 24)))

    # dimmed overlay text
    def overlay_text(self, title, subtitle):
        shade = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        shade.fill((0, 0, 0, 140))
        self.screen.blit(shade, (0, 0))
        t1 = self.bigfont.render(title, True, WHITE)
        t2 = self.font.render(subtitle, True, WHITE)
        self.screen.blit(t1, t1.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 24)))
        self.screen.blit(t2, t2.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 18)))

    # cleanzp
    def quit_game(self):
        try:
            if pg.mixer.get_init():
                pg.mixer.music.stop()
                pg.mixer.quit()
        except:
            pass
        pg.quit()
        raise SystemExit

if __name__ == "__main__":
    Game().run()
