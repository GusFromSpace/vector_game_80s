import pygame
import math
import random
import array
import numpy as np

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors (1990 Neon Overload)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 20, 147) # Deep Pink
GREEN = (57, 255, 20) # Neon Green
CYAN = (0, 255, 255) # Electric Cyan
YELLOW = (255, 255, 0) # Laser Yellow
ORANGE = (255, 69, 0) # Neon Orange
PURPLE = (191, 0, 255) # Electric Purple
DARK_GREY = (20, 20, 25)
NEON_BLUE = (30, 144, 255)
MAGENTA = (255, 0, 255)

# Game Balance Constants
SHIP_THRUST_ACCELERATION = 0.18
SHIP_ROTATION_SPEED = 0.08
SHIP_INERTIA_FACTOR = 0.98
SHIELD_MAX_ENERGY = 100
SHIELD_DRAIN_RATE = 1.5
SHIELD_REGEN_RATE = 0.3
TRAIL_MIN_DIST = 10
ASTEROID_SPEED_MIN = 0.4
ASTEROID_SPEED_MAX = 1.5
NUM_INITIAL_ASTEROIDS = 4
MAX_ASTEROIDS = 10
PROJECTILE_SPEED = 12
PROJECTILE_LIFESPAN = 50
INITIAL_LIVES = 3
BASE_SCROLL_SPEED = 1.5
FORCED_SCROLL_INC = 0.0001
STAR_FRAGMENT_SPAWN_CHANCE = 0.015
ENEMY_SPAWN_CHANCE = 0.006
GLITCH_SEEKER_CHANCE = 0.003
WEAPON_SPAWN_CHANCE = 0.0008
WEAPON_LABELS = ["OMEGA", "REAR", "TRIPLE"]
BOSS_SCORE_MILESTONE = 20000
BOSS_SCORE_CENTIPEDE = 40000
SALVAGE_POD_LIFESPAN = 480 # 8 seconds

# 1985 Power-Up Options
POWERUP_LABELS = ["SPEED UP", "DOUBLE", "OPTION", "SHIELD"]

# 1984 Story Milestones
STORY_MILESTONES = {
    2000: "LOG 01: THE MEAT-POCKET IS ROTATING AT A HARMONIC FREQUENCY. THE OFFICE SMELLS LIKE OZONE AND PEPPERONI.",
    5000: "LOG 04: THE EPA TRUCK HAS BEEN PARKED OUTSIDE FOR THREE DAYS. THEY DONT REALIZE THE GEOMETRY IS IN THE MICROWAVE.",
    10000: "LOG 09: IVE MODIFIED THE CALCULATOR. I CAN SEE THE VOID NOW. ITS NOT EMPTY. ITS... JAGGED.",
    20000: "LOG 15: THE VOID IS COLLAPSING. SOMETHING IS COMING THROUGH THE SUB-HARMONIC RIFT. IT LOOKS LIKE... A CORE.",
    30000: "LOG 22: THE PATTERNS ARE BEAUTIFUL. LETHAL GEOMETRY. THE MICROWAVE IS SMOKING, BUT THE RIFT IS AT 100% SYNCHRONIZATION.",
    40000: "LOG 30: THE SWARM IS HERE. SEGMENTED GEOMETRY. IT DOESNT FIRE. IT JUST... PERSISTS."
}

def rotate_point(point, angle):
    x, y = point
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)

def get_distance_sq(p1, p2):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def get_distance(p1, p2):
    return math.sqrt(get_distance_sq(p1, p2))

class BGMGenerator:
    def __init__(self):
        self.sample_rate = 44100
        self.bpm = 140
        self.ms_per_16th = (60000 / self.bpm) / 4
        self.total_samples = int((60 / self.bpm) * 16 * self.sample_rate)

    def _generate_tone(self, freq, duration_samples, volume=0.3, slide_to=None, richness=0.7):
        t = np.linspace(0, duration_samples / self.sample_rate, int(duration_samples), False)
        if slide_to:
            freqs = np.linspace(freq, slide_to, len(t))
        else:
            freqs = freq

        # Core wave + Harmonics
        wave = np.sin(2 * np.pi * freqs * t)
        wave += richness * 0.6 * np.sin(4 * np.pi * freqs * t)
        wave += richness * 0.4 * np.sin(6 * np.pi * freqs * t)

        # Envelope
        env = np.exp(-2.0 * np.linspace(0, 1, len(t)))
        return (np.clip(wave, -1, 1) * env * volume * 32767).astype(np.int16)

    def _generate_noise(self, duration_samples, volume=0.1):
        num_samples = int(duration_samples)
        noise = np.random.uniform(-1, 1, num_samples)
        env = np.exp(-6.0 * np.linspace(0, 1, num_samples))
        return (noise * env * volume * 32767).astype(np.int16)

    def generate_bgm(self, tension=0.0):
        master_buffer = np.zeros(self.total_samples, dtype=np.int16)
        beat_s = 60 / self.bpm
        beat_samples = int(beat_s * self.sample_rate)

        for bar in range(4):
            base_idx = int((bar * 4 * beat_s) * self.sample_rate)
            base_freq = 35 + tension * 15

            # Bass
            if bar % 2 == 0:
                tone = self._generate_tone(base_freq, beat_samples * 3, volume=0.8, slide_to=22)
                master_buffer[base_idx:base_idx+len(tone)] += tone
            else:
                tone1 = self._generate_tone(base_freq + 3, beat_samples * 1.5, volume=0.8, slide_to=25)
                master_buffer[base_idx:base_idx+len(tone1)] += tone1
                tone2 = self._generate_tone(base_freq - 3, beat_samples, volume=0.8, slide_to=20)
                start2 = int(base_idx + 2 * beat_samples)
                master_buffer[start2:start2+len(tone2)] += tone2

            # Percussion
            noise_idx = int(base_idx + 2 * beat_samples)
            noise = self._generate_noise(5000 + tension * 10000, volume=0.4 + tension * 0.3)
            master_buffer[noise_idx:noise_idx+len(noise)] += noise

            for h_idx in range(4):
                h_start = int(base_idx + h_idx * beat_samples)
                hihat = self._generate_noise(1200, volume=0.1 + tension * 0.2)
                master_buffer[h_start:h_start+len(hihat)] += hihat

        return pygame.mixer.Sound(buffer=master_buffer)

    def generate_sfx(self):
        fire = self._generate_tone(800, 4000, volume=0.2, slide_to=200)
        exp = self._generate_noise(8000, volume=0.2)
        hit = self._generate_tone(100, 6000, volume=0.3, slide_to=20)
        weapon = np.concatenate([
            self._generate_tone(1200, 4000, volume=0.4, slide_to=800),
            self._generate_tone(1000, 4000, volume=0.4, slide_to=600)
        ])
        return {
            'fire': pygame.mixer.Sound(buffer=fire),
            'exp': pygame.mixer.Sound(buffer=exp),
            'hit': pygame.mixer.Sound(buffer=hit),
            'weapon': pygame.mixer.Sound(buffer=weapon)
        }

class SalvagePod:
    def __init__(self, pos, weapon, option_count):
        self.pos, self.weapon, self.option_count, self.lifespan, self.size, self.timer, self.being_siphoned = list(pos), weapon, option_count, SALVAGE_POD_LIFESPAN, 20, 0, False
    def update(self): self.timer += 1; self.lifespan -= 1; self.being_siphoned = False
    def draw(self, screen, camera_x, shake_offset):
        if self.lifespan > 120 or (self.timer % 10 < 5):
            cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
            pygame.draw.circle(screen, NEON_BLUE, (int(cx), int(cy)), self.size, 2); draw_text(screen, "SALVAGE", 12, cx, cy - 25, NEON_BLUE, center=True)
            color = [RED, NEON_BLUE, GREEN][self.weapon] if self.weapon is not None else WHITE
            pygame.draw.rect(screen, color, (cx - 6, cy - 6, 12, 12), 1)

class WeaponPickup:
    def __init__(self, x_pos): self.pos, self.type, self.size, self.timer = [x_pos, random.randrange(100, SCREEN_HEIGHT - 100)], random.randint(0, 2), 15, 0
    def update(self): self.timer += 1
    def draw(self, screen, camera_x, shake_offset):
        color = [RED, NEON_BLUE, GREEN][self.type]; cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        if self.timer % 10 < 5: pygame.draw.rect(screen, color, (int(cx-8), int(cy-8), 16, 16), 2); draw_text(screen, "W", 12, cx, cy, color, center=True)

class SFXQueue:
    def __init__(self, sfx_dict, ms_per_16th): self.sfx, self.ms_per_16th, self.queue, self.last_triggered_tick = sfx_dict, ms_per_16th, [], 0
    def add(self, name, callback=None): self.queue.append({'name': name, 'callback': callback})
    def update(self):
        curr_tick = pygame.time.get_ticks()
        if curr_tick // self.ms_per_16th > self.last_triggered_tick // self.ms_per_16th:
            for item in self.queue:
                self.sfx[item['name']].play()
                if item['callback']: item['callback']()
            self.queue = []
        self.last_triggered_tick = curr_tick

class Particle:
    def __init__(self, pos, color, is_bloom=False):
        self.pos, self.velocity = list(pos), [math.cos(random.uniform(0, 2*math.pi)) * random.uniform(1, 8), math.sin(random.uniform(0, 2*math.pi)) * random.uniform(1, 8)]
        self.lifespan, self.color, self.is_bloom, self.size = random.randint(25, 60), color, is_bloom, random.randint(1, 3)
    def update(self): self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]; self.velocity[0] *= 0.95; self.velocity[1] *= 0.95; self.lifespan -= 1
    def draw(self, screen, camera_x, shake_offset=(0,0)):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        if self.is_bloom:
            s = random.randint(3, 8); pygame.draw.line(screen, self.color, (int(cx - s), int(cy)), (int(cx + s), int(cy)), 1); pygame.draw.line(screen, self.color, (int(cx), int(cy - s)), (int(cx), int(cy + s)), 1)
        else: pygame.draw.circle(screen, self.color, (int(cx), int(cy)), self.size)

class Projectile:
    def __init__(self, pos, angle, is_enemy=False, speed=PROJECTILE_SPEED): self.pos, self.velocity, self.lifespan, self.is_enemy, self.grazed = list(pos), [math.cos(angle) * speed, math.sin(angle) * speed], PROJECTILE_LIFESPAN, is_enemy, False
    def update(self): self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]; self.lifespan -= 1
    def draw(self, screen, camera_x, shake_offset=(0,0)):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]; color = RED if self.is_enemy else CYAN
        pygame.draw.circle(screen, color, (int(cx), int(cy)), 2)
        if random.random() > 0.5: pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 4, 1)

class Option:
    def __init__(self, player): self.player, self.history, self.pos, self.delay = player, [], list(player.pos), 15
    def update(self):
        self.history.append(list(self.player.pos))
        if len(self.history) > self.delay: self.pos = self.history.pop(0)
    def draw(self, screen, camera_x, shake_offset=(0,0)):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]; r = 5 + math.sin(pygame.time.get_ticks() * 0.01) * 2
        pygame.draw.circle(screen, ORANGE, (int(cx), int(cy)), int(r), 1); pygame.draw.circle(screen, YELLOW, (int(cx), int(cy)), 2)

class StarFragment:
    def __init__(self, x_pos): self.pos, self.speed, self.size, self.flicker_timer, self.being_siphoned = [x_pos, -20], random.uniform(2, 5), 10, 0, False
    def update(self):
        if not self.being_siphoned: self.pos[1] += self.speed
        self.flicker_timer += 1; self.being_siphoned = False
    def draw(self, screen, camera_x, shake_offset=(0,0)):
        if self.flicker_timer % 2 == 0:
            cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]; s = self.size
            points = [(cx, cy - s), (cx + s//2, cy), (cx, cy + s), (cx - s//2, cy)]
            pygame.draw.polygon(screen, PURPLE, points, 1)
            if self.flicker_timer % 4 == 0:
                pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 2)

class GlitchSeeker:
    def __init__(self, x_pos): self.pos, self.velocity, self.size, self.flicker = [x_pos, random.randrange(100, SCREEN_HEIGHT - 100)], [-6, random.uniform(-2, 2)], 12, 0
    def update(self, player):
        self.flicker += 1
        if player.pos[1] > self.pos[1]: self.velocity[1] += 0.3
        else: self.velocity[1] -= 0.3
        self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]
    def draw(self, screen, camera_x, shake_offset):
        if self.flicker % 3 != 0:
            cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
            pygame.draw.line(screen, GREEN, (cx - 12, cy), (cx + 12, cy), 2); pygame.draw.line(screen, WHITE, (cx, cy - 12), (cx, cy + 12), 1)

class Enemy:
    def __init__(self, x_pos):
        self.pos, self.velocity, self.size, self.rage, self.siphon_target = [x_pos, random.randrange(100, SCREEN_HEIGHT - 100)], [-2, random.uniform(-1, 1)], 18, False, None
        self.fragments_collected, self.fling_cooldown, self.vertices, self.current_weapon, self.weapon_cooldown, self.supercharged = 0, 0, [], None, 0, False
        for i in range(8): a = (i / 8) * 2 * math.pi; self.vertices.append((math.cos(a) * self.size, math.sin(a) * self.size))
    def update(self, player, fragments, asteroids, pickups, salvage_pods, sfx_q):
        self.siphon_target = None; min_dist_sq = 160000; pod_target = None
        for pod in salvage_pods:
            if get_distance_sq(self.pos, pod.pos) < 250000: pod_target = pod; break
        if pod_target:
            if pod_target.pos[1] > self.pos[1]: self.velocity[1] += 0.25
            else: self.velocity[1] -= 0.25
            if get_distance_sq(self.pos, pod_target.pos) < 22500:
                pod_target.being_siphoned = True; angle = math.atan2(self.pos[1] - pod_target.pos[1], self.pos[0] - pod_target.pos[0])
                pod_target.pos[0] += math.cos(angle) * 4; pod_target.pos[1] += math.sin(angle) * 4
                if get_distance_sq(self.pos, pod_target.pos) < 625:
                    if pod_target in salvage_pods: salvage_pods.remove(pod_target)
                    self.supercharged = True; sfx_q.add('weapon')
        else:
            p_target = None
            for p in pickups:
                if get_distance_sq(self.pos, p.pos) < 250000: p_target = p; break
            if p_target:
                if p_target.pos[1] > self.pos[1]: self.velocity[1] += 0.2
                else: self.velocity[1] -= 0.2
            elif fragments:
                for f in fragments:
                    d_sq = get_distance_sq(self.pos, f.pos)
                    if d_sq < min_dist_sq: min_dist_sq, self.siphon_target = d_sq, f
                if self.siphon_target:
                    if self.siphon_target.pos[1] > self.pos[1]: self.velocity[1] += 0.15
                    else: self.velocity[1] -= 0.15
                    if min_dist_sq < 40000:
                        self.siphon_target.being_siphoned = True; angle = math.atan2(self.pos[1] - self.siphon_target.pos[1], self.pos[0] - self.siphon_target.pos[0])
                        self.siphon_target.pos[0] += math.cos(angle) * 5; self.siphon_target.pos[1] += math.sin(angle) * 5
                        if min_dist_sq < 625:
                            if self.siphon_target in fragments: fragments.remove(self.siphon_target)
                            self.rage, self.fragments_collected, self.siphon_target = True, self.fragments_collected + 1, None
            else:
                if player.pos[1] > self.pos[1]: self.velocity[1] += 0.08
                else: self.velocity[1] -= 0.08
        if self.fragments_collected >= 2 and self.fling_cooldown <= 0:
            for a in asteroids:
                if get_distance_sq(self.pos, a.pos) < 14400:
                    angle = math.atan2(player.pos[1] - a.pos[1], player.pos[0] - a.pos[0])
                    a.velocity[0], a.velocity[1], self.fling_cooldown = math.cos(angle) * 4, math.sin(angle) * 4, 120; break
        if self.fling_cooldown > 0: self.fling_cooldown -= 1
        if self.weapon_cooldown > 0: self.weapon_cooldown -= 1
        speed_cap = 6 if self.rage else 3.5; curr_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
        if curr_speed > speed_cap: scale = speed_cap / curr_speed; self.velocity[0] *= scale; self.velocity[1] *= scale
        self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]
    def fire(self):
        if self.current_weapon is not None and self.weapon_cooldown <= 0:
            self.weapon_cooldown, shots = 45 if self.supercharged else 90, []
            if self.current_weapon == 0: shots.append(Projectile(list(self.pos), math.pi, is_enemy=True))
            elif self.current_weapon == 1: shots.append(Projectile(list(self.pos), 0, is_enemy=True))
            elif self.current_weapon == 2: shots.append(Projectile(list(self.pos), math.pi - 0.2, is_enemy=True)); shots.append(Projectile(list(self.pos), math.pi + 0.2, is_enemy=True))
            return shots
        return []
    def draw(self, screen, camera_x, shake_offset):
        color = RED if self.rage else PURPLE; cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        points = [(x + cx, y + cy) for x, y in self.vertices]; pygame.draw.polygon(screen, color, points, 2); pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 4)
        if self.fling_cooldown > 100: pygame.draw.circle(screen, ORANGE, (int(cx), int(cy)), 50, 1)
        if self.siphon_target: pygame.draw.line(screen, CYAN, (cx, cy), (self.siphon_target.pos[0] - camera_x, self.siphon_target.pos[1]), 1)
        if self.supercharged: pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 25, 1)

class Boss:
    def __init__(self, x_pos):
        self.pos, self.health, self.timer, self.current_weapon, self.weapon_cooldown, self.shields = [x_pos, SCREEN_HEIGHT // 2], 80, 0, None, 0, []
        for i in range(6): self.shields.append({'angle': i * (math.pi/3), 'health': 15, 'size': 25})
    def update(self, player, pickups):
        self.timer += 1; self.pos[1] = SCREEN_HEIGHT // 2 + math.sin(self.timer * 0.05) * 120
        for s in self.shields: s['angle'] += 0.04
        if self.current_weapon is None:
            for p in pickups:
                if get_distance_sq(self.pos, p.pos) < 160000:
                    if p.pos[1] > self.pos[1]: self.pos[1] += 3
                    else: self.pos[1] -= 3
                    break
        if self.weapon_cooldown > 0: self.weapon_cooldown -= 1
    def fire(self):
        if self.weapon_cooldown <= 0:
            self.weapon_cooldown, shots = 45, []
            if self.health > 40:
                for i in range(8): shots.append(Projectile(list(self.pos), (i / 8) * 2 * math.pi + (self.timer * 0.1), is_enemy=True, speed=5))
            else:
                for i in range(12): shots.append(Projectile(list(self.pos), math.pi + (i - 6) * 0.15, is_enemy=True, speed=6))
            if self.current_weapon == 2:
                 for i in range(3): shots.append(Projectile(list(self.pos), math.pi + (i-1)*0.3, is_enemy=True, speed=10))
            return shots
        return []
    def draw(self, screen, camera_x, shake_offset):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]; scale = 1.0 + math.sin(self.timer * 0.15) * 0.3
        core_pts = [(cx + math.cos(a)*35*scale, cy + math.sin(a)*35*scale) for a in [i*(math.pi/4) for i in range(8)]]
        pygame.draw.polygon(screen, CYAN if self.health > 40 else RED, core_pts, 3)
        for s in self.shields:
            if s['health'] > 0:
                sx, sy = cx + math.cos(s['angle']) * 100, cy + math.sin(s['angle']) * 100
                pygame.draw.circle(screen, YELLOW, (int(sx), int(sy)), int(s['size']), 1); pygame.draw.circle(screen, WHITE, (int(sx), int(sy)), 5)

class CentipedeSegment:
    def __init__(self, pos): self.pos, self.size = list(pos), 15
    def draw(self, screen, camera_x, shake_offset):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        pygame.draw.circle(screen, GREEN, (int(cx), int(cy)), self.size, 1); pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 3)

class CentipedeBoss:
    def __init__(self, x_pos):
        self.pos, self.velocity, self.timer, self.segments = [x_pos, SCREEN_HEIGHT // 2], [-3, 0], 0, []
        for i in range(15): self.segments.append(CentipedeSegment([x_pos + (i+1)*25, SCREEN_HEIGHT // 2]))
    def update(self, player):
        self.timer += 1; self.pos[1] = SCREEN_HEIGHT // 2 + math.sin(self.timer * 0.04) * 200; self.pos[0] += self.velocity[0]; prev_pos = list(self.pos)
        for s in self.segments:
            dx, dy = prev_pos[0] - s.pos[0], prev_pos[1] - s.pos[1]; dist = math.sqrt(dx*dx + dy*dy)
            if dist > 20: angle = math.atan2(dy, dx); s.pos[0] += math.cos(angle) * (dist - 20); s.pos[1] += math.sin(angle) * (dist - 20)
            prev_pos = list(s.pos)
    def draw(self, screen, camera_x, shake_offset):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        pygame.draw.circle(screen, RED, (int(cx), int(cy)), 20, 2); pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 6)
        for s in self.segments: s.draw(screen, camera_x, shake_offset)

class Player:
    def __init__(self): self.size = 15; self.vertices = [(self.size, 0), (-self.size // 2, self.size // 2), (-self.size // 2, -self.size // 2)]; self.reset()
    def reset(self):
        self.pos, self.angle, self.velocity, self.visible = [100, SCREEN_HEIGHT // 2], 0, [BASE_SCROLL_SPEED, 0], True
        self.invulnerable_frames, self.shield_active, self.shield_energy = 90, False, SHIELD_MAX_ENERGY
        self.trail, self.claiming, self.speed_boost, self.has_double, self.options, self.powerup_index, self.current_weapon = [], False, 0, False, [], -1, None
    def rotate(self, direction):
        if not self.shield_active: self.angle += direction * (SHIP_ROTATION_SPEED + self.speed_boost * 0.02)
    def thrust(self):
        if not self.shield_active: accel = SHIP_THRUST_ACCELERATION + self.speed_boost * 0.05; self.velocity[0] += math.cos(self.angle) * accel; self.velocity[1] += math.sin(self.angle) * accel
    def fire(self):
        if not self.shield_active and not self.claiming:
            shots, tip_x, tip_y = [], *rotate_point((self.size, 0), self.angle)
            if self.current_weapon == 1: shots.extend([Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle), Projectile([self.pos[0] - tip_x, self.pos[1] - tip_y], self.angle + math.pi)])
            elif self.current_weapon == 2: shots.extend([Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle), Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle - 0.2), Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle + 0.2)])
            else: shots.append(Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle))
            if self.has_double: shots.append(Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle - 0.4))
            for opt in self.options:
                shots.append(Projectile(list(opt.pos), self.angle))
                if self.has_double: shots.append(Projectile(list(opt.pos), self.angle - 0.4))
            return shots
        return []
    def activate_powerup(self):
        if self.powerup_index == 0: self.speed_boost = min(3, self.speed_boost + 1)
        elif self.powerup_index == 1: self.has_double = True
        elif self.powerup_index == 2 and len(self.options) < 2: self.options.append(Option(self))
        elif self.powerup_index == 3: self.shield_energy = SHIELD_MAX_ENERGY
        if self.powerup_index != -1: self.powerup_index = -1
    def update(self, camera_x):
        self.velocity[0] *= SHIP_INERTIA_FACTOR; self.velocity[1] *= SHIP_INERTIA_FACTOR; self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]
        if self.pos[1] < 0: self.pos[1] = 0
        if self.pos[1] > SCREEN_HEIGHT: self.pos[1] = SCREEN_HEIGHT
        if self.pos[0] - camera_x > SCREEN_WIDTH - 50: self.pos[0] = camera_x + SCREEN_WIDTH - 50
        if self.invulnerable_frames > 0: self.invulnerable_frames -= 1
        if self.shield_active:
            self.shield_energy -= SHIELD_DRAIN_RATE
            if self.shield_energy <= 0: self.shield_energy, self.shield_active = 0, False
            self.claiming, self.trail = False, []
        else: self.shield_energy = min(SHIELD_MAX_ENERGY, self.shield_energy + SHIELD_REGEN_RATE)
        if self.claiming:
            if not self.trail or get_distance_sq(self.pos, self.trail[-1]) > 100: self.trail.append(list(self.pos))
        else: self.trail = []
        for opt in self.options: opt.update()
    def draw(self, screen, camera_x, shake_offset):
        for opt in self.options: opt.draw(screen, camera_x, shake_offset)
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        if self.invulnerable_frames % 10 < 5:
            transformed_vertices = []
            for x, y in self.vertices: rx, ry = rotate_point((x, y), self.angle); transformed_vertices.append((rx + cx, ry + cy))
            pygame.draw.polygon(screen, RED, transformed_vertices, 2); pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 2)
        if self.shield_active: pygame.draw.circle(screen, GREEN, (int(cx), int(cy)), self.size + 10, 1)
        if len(self.trail) > 1:
            screen_trail = [(p[0] - camera_x + shake_offset[0], p[1] + shake_offset[1]) for p in self.trail]; pygame.draw.lines(screen, YELLOW, False, screen_trail, 2)

class Asteroid:
    def __init__(self, x_spawn=None, size=40):
        self.pos, self.size = [x_spawn or random.randrange(SCREEN_WIDTH * 2), random.randrange(SCREEN_HEIGHT)], size
        angle, speed = random.uniform(0, 2 * math.pi), random.uniform(ASTEROID_SPEED_MIN, ASTEROID_SPEED_MAX)
        self.velocity, self.vertices = [math.cos(angle) * speed, math.sin(angle) * speed], []
        num_vertices = random.randint(8, 12)
        for i in range(num_vertices): a, r = (i / num_vertices) * 2 * math.pi, self.size * random.uniform(0.8, 1.2); self.vertices.append((math.cos(a) * r, math.sin(a) * r))
    def update(self): self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]; self.pos[1] %= SCREEN_HEIGHT
    def draw(self, screen, camera_x, shake_offset):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        points = [(x + cx, y + cy) for x, y in self.vertices]; pygame.draw.polygon(screen, WHITE, points, 2)
        if self.size > 20: pygame.draw.line(screen, DARK_GREY, points[0], points[4], 1); pygame.draw.line(screen, DARK_GREY, points[2], points[6], 1)

class ParallaxLayer:
    def __init__(self, speed_factor, color, count, is_lattice=False):
        self.speed_factor, self.color, self.is_lattice = speed_factor, color, is_lattice
        self.surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for _ in range(count):
            x, y = random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)
            if self.is_lattice:
                pygame.draw.line(self.surface, self.color, (x, y), (x+20, y+20), 1)
                pygame.draw.circle(self.surface, self.color, (x, y), 2, 1)
            else:
                pygame.draw.circle(self.surface, self.color, (x, y), 1)

    def draw(self, screen, camera_x, tilt_offset=0, shake_offset=(0,0)):
        offset = (camera_x * self.speed_factor) % SCREEN_WIDTH
        y_off = tilt_offset * self.speed_factor + shake_offset[1]
        screen.blit(self.surface, (shake_offset[0] - offset, y_off))
        screen.blit(self.surface, (shake_offset[0] - offset + SCREEN_WIDTH, y_off))

_font_cache = {}
def draw_text(screen, text, size, x, y, color=WHITE, center=False, wrap_width=None):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("monospace", size, bold=True)
    font = _font_cache[size]
    if wrap_width:
        words, lines, current_line = text.split(' '), [], []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] < wrap_width: current_line.append(word)
            else: lines.append(' '.join(current_line)); current_line = [word]
        lines.append(' '.join(current_line))
        for i, line in enumerate(lines):
            img = font.render(line, True, color)
            if center: rect = img.get_rect(center=(x, y + i * size)); screen.blit(img, rect)
            else: screen.blit(img, (x, y + i * size))
    else:
        img = font.render(text, True, color)
        if center: rect = img.get_rect(center=(x, y)); screen.blit(img, rect)
        else: screen.blit(img, (x, y))

def create_explosion(particles, pos, color, count=15):
    for _ in range(count): particles.append(Particle(pos, color, is_bloom=(random.random() > 0.5)))

def get_state(player, asteroids, enemies, projectiles, cam_x):
    """Returns normalized game state as a plain list of 61 floats."""
    obs = [(player.pos[0]-cam_x)/800, player.pos[1]/600, player.velocity[0]/10, player.velocity[1]/10, player.angle/6.28, player.shield_energy/100, 0.0]
    sorted_asts = sorted(asteroids, key=lambda a: get_distance_sq(player.pos, a.pos))[:5]
    for a in sorted_asts:
        dist = get_distance(player.pos, a.pos) / 800.0
        angle = math.atan2(a.pos[1]-player.pos[1], a.pos[0]-player.pos[0]) / 3.14
        obs.extend([dist, angle, (a.velocity[0]-player.velocity[0])/10.0, (a.velocity[1]-player.velocity[1])/10.0, a.size/40.0])
    while len(obs) < 7 + 25: obs.extend([0,0,0,0,0])
    sorted_enemies = sorted(enemies, key=lambda e: get_distance_sq(player.pos, e.pos))[:3]
    for e in sorted_enemies:
        dist = get_distance(player.pos, e.pos) / 800.0
        angle = math.atan2(e.pos[1]-player.pos[1], e.pos[0]-player.pos[0]) / 3.14
        obs.extend([dist, angle, (e.velocity[0]-player.velocity[0])/10.0, (e.velocity[1]-player.velocity[1])/10.0, e.size/40.0])
    while len(obs) < 7 + 25 + 15: obs.extend([0,0,0,0,0])
    enemy_projs = [p for p in projectiles if p.is_enemy]
    sorted_projs = sorted(enemy_projs, key=lambda p: get_distance_sq(player.pos, p.pos))[:3]
    for p in sorted_projs:
        dist = get_distance(player.pos, p.pos) / 800.0
        angle = math.atan2(p.pos[1]-player.pos[1], p.pos[0]-player.pos[0]) / 3.14
        obs.extend([dist, angle, (p.velocity[0]-player.velocity[0])/15.0, (p.velocity[1]-player.velocity[1])/15.0])
    while len(obs) < 61: obs.extend([0])
    return obs

# External controller slot. Set to an object with .step(state) -> list[float x5]
# to enable autopilot mode. Optional: .telemetry property -> dict.
_AUTOPILOT_CONTROLLER = None

# Session observer slot. Set to a callable(state, action, reward) to observe gameplay.
_SESSION_OBSERVER = None

def main():
    pygame.init(); pygame.mixer.init(); bgm_gen = BGMGenerator(); bgm_sound = bgm_gen.generate_bgm(); sfx_queue = SFXQueue(bgm_gen.generate_sfx(), bgm_gen.ms_per_16th)
    bgm_sound.play(loops=-1); screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)); pygame.display.set_caption("Vector Asteroids: Harmonic Void")
    clock, player = pygame.time.Clock(), Player(); asteroids = [Asteroid() for _ in range(NUM_INITIAL_ASTEROIDS)]
    projectiles, star_fragments, enemies, glitch_seekers, particles, pickups, salvage_pods = [], [], [], [], [], [], []
    shake_amount, score, lives, game_over, camera_x = 0, 0, INITIAL_LIVES, False, 0
    current_scroll_speed, current_transmission, seen_milestones = BASE_SCROLL_SPEED, None, set()
    layers = [ParallaxLayer(0.2, (60, 60, 80), 40, is_lattice=True), ParallaxLayer(0.5, (100, 80, 150), 30), ParallaxLayer(0.8, (80, 150, 200), 20)]
    current_boss = None; centipede_boss = None

    autopilot = False
    autopilot_telemetry = {"probs": [0.0]*5, "risk": 0.0, "opp": 0.0, "var": 0.0}
    last_score, last_lives = 0, INITIAL_LIVES

    running = True
    while running:
        curr_enemy_spawn_chance = ENEMY_SPAWN_CHANCE

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if current_transmission: current_transmission = None; continue
                if event.key == pygame.K_a: autopilot = not autopilot
                if event.key == pygame.K_SPACE and not game_over:
                    for s in player.fire(): projectiles.append(s)
                if event.key == pygame.K_c and not game_over: player.activate_powerup()
                if event.key == pygame.K_r and game_over:
                    player.reset(); asteroids = [Asteroid() for _ in range(NUM_INITIAL_ASTEROIDS)]; projectiles, star_fragments, enemies, glitch_seekers, particles, pickups, salvage_pods = [], [], [], [], [], [], []
                    score, lives, game_over, camera_x, shake_amount, current_scroll_speed, seen_milestones = 0, INITIAL_LIVES, False, 0, 0, BASE_SCROLL_SPEED, set(); current_boss = None; centipede_boss = None
                    last_score, last_lives = 0, INITIAL_LIVES

        if not game_over and not current_transmission:
            state = get_state(player, asteroids, enemies, projectiles, camera_x)
            keys = pygame.key.get_pressed()

            if autopilot and _AUTOPILOT_CONTROLLER is not None:
                ai_act = _AUTOPILOT_CONTROLLER.step(state)
                if hasattr(_AUTOPILOT_CONTROLLER, 'telemetry'):
                    autopilot_telemetry.update(_AUTOPILOT_CONTROLLER.telemetry)
                autopilot_telemetry["probs"] = [float(a) for a in ai_act]
            elif autopilot:
                # Built-in demo pilot: simple rule-based fallback
                ai_act = [1, 0, 0, random.random() > 0.92, player.shield_energy < 15]
                if player.pos[1] > SCREEN_HEIGHT * 0.7: ai_act[2] = 1
                elif player.pos[1] < SCREEN_HEIGHT * 0.3: ai_act[1] = 1
                autopilot_telemetry["probs"] = [float(a) for a in ai_act]

            if autopilot:
                if ai_act[1]: player.rotate(-1)
                if ai_act[2]: player.rotate(1)
                if ai_act[0]: player.thrust()
                player.shield_active = ai_act[4] > 0.5 and player.shield_energy > 0
                if ai_act[3] > 0.5 and pygame.time.get_ticks() % 8 == 0:
                    for s in player.fire(): projectiles.append(s)
                action = ai_act
            else:
                player.rotate(-1 if keys[pygame.K_LEFT] else 1 if keys[pygame.K_RIGHT] else 0)
                if keys[pygame.K_UP]: player.thrust()
                player.shield_active = (keys[pygame.K_DOWN] and player.shield_energy > 0)
                action = [
                    1.0 if keys[pygame.K_UP] else 0.0,
                    1.0 if keys[pygame.K_LEFT] else 0.0,
                    1.0 if keys[pygame.K_RIGHT] else 0.0,
                    1.0 if keys[pygame.K_SPACE] else 0.0,
                    1.0 if keys[pygame.K_DOWN] else 0.0
                ]

            reward = 0.01
            reward += (score - last_score) * 0.1
            if lives < last_lives: reward -= 50.0
            if player.pos[0] - camera_x < 200: reward -= 0.1
            elif player.pos[0] - camera_x > 400: reward += 0.05
            last_score, last_lives = score, lives

            if _SESSION_OBSERVER is not None:
                _SESSION_OBSERVER(state, action, reward)

            current_scroll_speed += FORCED_SCROLL_INC; camera_x += current_scroll_speed; sfx_queue.update()
            if score >= BOSS_SCORE_MILESTONE and current_boss is None and score < BOSS_SCORE_CENTIPEDE: current_boss = Boss(camera_x + SCREEN_WIDTH + 200)
            if score >= BOSS_SCORE_CENTIPEDE and centipede_boss is None: centipede_boss = CentipedeBoss(camera_x + SCREEN_WIDTH + 200)
            if random.random() < WEAPON_SPAWN_CHANCE: pickups.append(WeaponPickup(camera_x + SCREEN_WIDTH + 100))
            for p_up in pickups[:]:
                p_up.update()
                if p_up.pos[0] < camera_x - 100: pickups.remove(p_up)
                elif get_distance_sq(p_up.pos, player.pos) < (player.size + p_up.size)**2: player.current_weapon, _ = p_up.type, sfx_queue.add('weapon'); pickups.remove(p_up)
                else:
                    target_boss = (current_boss and get_distance_sq(p_up.pos, current_boss.pos) < 2500)
                    if target_boss: current_boss.current_weapon, _ = p_up.type, sfx_queue.add('weapon'); pickups.remove(p_up)
                    else:
                        for e in enemies:
                            if get_distance_sq(p_up.pos, e.pos) < (e.size + p_up.size)**2: e.current_weapon, _ = p_up.type, sfx_queue.add('weapon'); pickups.remove(p_up); break
            for pod in salvage_pods[:]:
                pod.update()
                if pod.pos[0] < camera_x - 100 or pod.lifespan <= 0: salvage_pods.remove(pod)
                elif get_distance_sq(pod.pos, player.pos) < (player.size + pod.size)**2:
                    player.current_weapon = pod.weapon; [player.options.append(Option(player)) for _ in range(pod.option_count)]; sfx_queue.add('weapon'); salvage_pods.remove(pod)
            if centipede_boss:
                centipede_boss.update(player)
                if not player.shield_active and player.invulnerable_frames == 0:
                    if get_distance_sq(centipede_boss.pos, player.pos) < 900:
                        sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 30, lives - 1
                        if lives <= 0 and not autopilot: game_over = True
                        else:
                            if player.current_weapon is not None or player.options: salvage_pods.append(SalvagePod(player.pos, player.current_weapon, len(player.options)))
                            player.reset(); player.pos[0] = camera_x + 100
                for s in centipede_boss.segments[:]:
                    if not player.shield_active and player.invulnerable_frames == 0:
                        if get_distance_sq(s.pos, player.pos) < 400:
                             sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 30, lives - 1
                             if lives <= 0 and not autopilot: game_over = True
                             else:
                                 if player.current_weapon is not None or player.options: salvage_pods.append(SalvagePod(player.pos, player.current_weapon, len(player.options)))
                                 player.reset(); player.pos[0] = camera_x + 100
            if keys[pygame.K_LSHIFT] and not player.shield_active: player.claiming = True
            else:
                if player.claiming and len(player.trail) > 5:
                    if get_distance_sq(player.pos, player.trail[0]) < 2500:
                        score += 500; create_explosion(particles, player.pos, YELLOW, 20)
                        t_min_x = t_max_x = player.trail[0][0]
                        t_min_y = t_max_y = player.trail[0][1]
                        for tx, ty in player.trail:
                            if tx < t_min_x: t_min_x = tx
                            elif tx > t_max_x: t_max_x = tx
                            if ty < t_min_y: t_min_y = ty
                            elif ty > t_max_y: t_max_y = ty
                        for a in asteroids[:]:
                            if t_min_x < a.pos[0] < t_max_x and t_min_y < a.pos[1] < t_max_y: asteroids.remove(a); create_explosion(particles, a.pos, WHITE, 10)
                        if current_boss and t_min_x < current_boss.pos[0] < t_max_x and t_min_y < current_boss.pos[1] < t_max_y: current_boss.health -= 5; create_explosion(particles, current_boss.pos, RED, 20)
                player.claiming = False
            player.update(camera_x)
            if player.pos[0] < camera_x:
                sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 30, lives - 1
                if lives <= 0 and not autopilot: game_over = True
                else:
                    if player.current_weapon is not None or player.options: salvage_pods.append(SalvagePod(player.pos, player.current_weapon, len(player.options)))
                    player.reset(); player.pos[0] = camera_x + 100
            if not autopilot:
                for m, text in STORY_MILESTONES.items():
                    if score >= m and m not in seen_milestones: current_transmission = text; seen_milestones.add(m); break
            if random.random() < STAR_FRAGMENT_SPAWN_CHANCE: star_fragments.append(StarFragment(camera_x + random.randint(100, SCREEN_WIDTH + 100)))
            if current_boss is None:
                if random.random() < curr_enemy_spawn_chance: enemies.append(Enemy(camera_x + SCREEN_WIDTH + 100))
                if random.random() < GLITCH_SEEKER_CHANCE: glitch_seekers.append(GlitchSeeker(camera_x + SCREEN_WIDTH + 100))
            if current_boss:
                current_boss.update(player, pickups); current_boss.pos[0] = camera_x + SCREEN_WIDTH - 200
                if random.random() < 0.05:
                    b_shots = current_boss.fire()
                    if b_shots: sfx_queue.add('fire', lambda shots=b_shots: [projectiles.append(sh) for sh in shots])
            for g in glitch_seekers[:]:
                g.update(player)
                if g.pos[0] < camera_x - 100: glitch_seekers.remove(g)
                elif not player.shield_active and player.invulnerable_frames == 0:
                    if get_distance_sq(g.pos, player.pos) < (g.size + player.size)**2:
                        sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 25, lives - 1
                        if lives <= 0 and not autopilot: game_over = True
                        else:
                            if player.current_weapon is not None or player.options: salvage_pods.append(SalvagePod(player.pos, player.current_weapon, len(player.options)))
                            player.reset(); player.pos[0] = camera_x + 100; glitch_seekers.remove(g)
            p_size_sq = player.size**2
            for p in projectiles[:]:
                p.update()
                if p.lifespan <= 0 or p.pos[0] < camera_x or p.pos[0] > camera_x + SCREEN_WIDTH:
                    if p in projectiles: projectiles.remove(p)
                else:
                    if p.is_enemy and not p.grazed and not player.shield_active:
                         if get_distance_sq(p.pos, player.pos) < 2500: score += 100; p.grazed = True
                    if p.is_enemy and not player.shield_active and player.invulnerable_frames == 0:
                        if get_distance_sq(p.pos, player.pos) < p_size_sq:
                            sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 30, lives - 1
                            if lives <= 0 and not autopilot: game_over = True
                            else:
                                if player.current_weapon is not None or player.options: salvage_pods.append(SalvagePod(player.pos, player.current_weapon, len(player.options)))
                                player.reset(); player.pos[0] = camera_x + 100
                            if p in projectiles: projectiles.remove(p); continue
                    for g in glitch_seekers[:]:
                        if not p.is_enemy and get_distance_sq(p.pos, g.pos) < g.size**2:
                            def kg(t=g): nonlocal score; score += 1500; create_explosion(particles, t.pos, GREEN, 20); [glitch_seekers.remove(t) if t in glitch_seekers else None]
                            sfx_queue.add('exp', kg); projectiles.remove(p); break
                    if p not in projectiles: continue
                    if centipede_boss and not p.is_enemy:
                        if get_distance_sq(p.pos, centipede_boss.pos) < 900: sfx_queue.add('hit'); create_explosion(particles, centipede_boss.pos, RED, 10); projectiles.remove(p); break
                        for s in centipede_boss.segments[:]:
                            if get_distance_sq(p.pos, s.pos) < 400:
                                create_explosion(particles, s.pos, GREEN, 15); score += 1000; sfx_queue.add('exp'); centipede_boss.segments.remove(s); projectiles.remove(p); break
                        if p not in projectiles: continue
                    if current_boss and not p.is_enemy:
                        hit_boss = False
                        for s in current_boss.shields:
                            if s['health'] > 0:
                                sx, sy = current_boss.pos[0] + math.cos(s['angle']) * 80, current_boss.pos[1] + math.sin(s['angle']) * 80
                                if get_distance_sq(p.pos, (sx, sy)) < s['size']**2: s['health'] -= 1; sfx_queue.add('exp'); projectiles.remove(p); hit_boss = True; break
                        if hit_boss: continue
                        if all(sh['health'] <= 0 for sh in current_boss.shields):
                             if get_distance_sq(p.pos, current_boss.pos) < 1600:
                                 current_boss.health -= 1; sfx_queue.add('hit'); projectiles.remove(p)
                                 if current_boss.health <= 0: score += 10000; create_explosion(particles, current_boss.pos, CYAN, 100); current_boss = None; shake_amount = 50
                                 continue
            for s in star_fragments[:]:
                s.update()
                if get_distance_sq(player.pos, s.pos) < (player.size + s.size)**2:
                    score += 1000; create_explosion(particles, s.pos, PURPLE, 10); star_fragments.remove(s); player.powerup_index = (player.powerup_index + 1) % len(POWERUP_LABELS)
                elif s.pos[1] > SCREEN_HEIGHT: star_fragments.remove(s)
                elif player.claiming:
                    for i in range(len(player.trail)):
                        if get_distance_sq(s.pos, player.trail[i]) < s.size**2:
                            sfx_queue.add('hit'); create_explosion(particles, player.pos, PURPLE, 30); lives -= 1; player.reset(); player.pos[0] = camera_x + 100
                            if lives <= 0 and not autopilot: game_over = True
                            star_fragments.remove(s); break
            for e in enemies[:]:
                e.update(player, star_fragments, asteroids, pickups, salvage_pods, sfx_queue)
                if e.pos[0] < camera_x - 100: enemies.remove(e)
                else:
                    if e.current_weapon is not None:
                        e_shots = e.fire()
                        if e_shots: sfx_queue.add('fire', lambda shots=e_shots: [projectiles.append(sh) for sh in shots])
                    for a in asteroids:
                        if get_distance_sq(e.pos, a.pos) < (e.size + a.size)**2:
                            sfx_queue.add('exp'); create_explosion(particles, e.pos, PURPLE, 20); shake_amount = 10; enemies.remove(e); break
                    if e not in enemies: continue
                    for p in projectiles[:]:
                        if not p.is_enemy and get_distance_sq(e.pos, p.pos) < e.size**2:
                            def ke(t=e): nonlocal score; score += 500; create_explosion(particles, t.pos, WHITE, 25); [enemies.remove(t) if t in enemies else None]
                            sfx_queue.add('exp', ke); shake_amount = 15; projectiles.remove(p); break
                    if e not in enemies: continue
                    if not player.shield_active and player.invulnerable_frames == 0:
                        if get_distance_sq(e.pos, player.pos) < (e.size + player.size)**2:
                            sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 25, lives - 1
                            if lives <= 0 and not autopilot: game_over = True
                            else:
                                if player.current_weapon is not None or player.options: salvage_pods.append(SalvagePod(player.pos, player.current_weapon, len(player.options)))
                                player.reset(); player.pos[0] = camera_x + 100; enemies.remove(e)
            for a in asteroids[:]:
                a.update()
                if a.pos[0] < camera_x - 100:
                    asteroids.remove(a)
                    if len(asteroids) < MAX_ASTEROIDS:
                        asteroids.append(Asteroid(camera_x + SCREEN_WIDTH + random.randint(400, 800)))
            for part in particles:
                part.update()
            particles = [p for p in particles if p.lifespan > 0]
            for a in asteroids[:]:
                if player.claiming and len(player.trail) > 2:
                    for i in range(len(player.trail) - 1):
                        if get_distance_sq(a.pos, player.trail[i]) < a.size**2:
                            sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 30); lives -= 1; player.reset(); player.pos[0] = camera_x + 100
                            if lives <= 0 and not autopilot: game_over = True
                            break
                if player.shield_active:
                    if get_distance_sq(player.pos, a.pos) < (a.size + player.size + 10)**2:
                        rp = math.atan2(a.pos[1] - player.pos[1], a.pos[0] - player.pos[0]); a.velocity[0], a.velocity[1] = math.cos(rp) * 3, math.sin(rp) * 3; continue
                if player.invulnerable_frames == 0 and get_distance_sq(player.pos, a.pos) < (a.size + player.size)**2:
                    sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 30); lives -= 1
                    if lives <= 0 and not autopilot: game_over = True
                    else:
                        if player.current_weapon is not None or player.options: salvage_pods.append(SalvagePod(player.pos, player.current_weapon, len(player.options)))
                        player.reset(); player.pos[0] = camera_x + 100
                for p in projectiles[:]:
                    if get_distance_sq(p.pos, a.pos) < a.size**2:
                        def ka(t=a):
                            nonlocal score; score += 100 if t.size > 20 else 200; create_explosion(particles, t.pos, WHITE, 15)
                            if t.size > 15 and len(asteroids) < MAX_ASTEROIDS: asteroids.append(Asteroid(t.pos[0], t.size // 2))
                            if t in asteroids: asteroids.remove(t)
                            if len(asteroids) < MAX_ASTEROIDS: asteroids.append(Asteroid(camera_x + SCREEN_WIDTH + random.randint(400, 800)))
                        sfx_queue.add('exp', ka); shake_amount = 10; projectiles.remove(p); break

        shake_offset = (random.randint(-int(shake_amount), int(shake_amount)), random.randint(-int(shake_amount), int(shake_amount))) if shake_amount > 0 else (0,0)
        shake_amount *= 0.9; screen.fill(BLACK); tilt = (player.pos[1] - SCREEN_HEIGHT//2) * 0.1
        for layer in layers: layer.draw(screen, camera_x, tilt_offset=tilt, shake_offset=shake_offset)
        if pygame.time.get_ticks() % 500 < 250:
            pygame.draw.line(screen, RED, (0, 0), (0, SCREEN_HEIGHT), 3); draw_text(screen, "RIFT COLLAPSE", 14, 15, SCREEN_HEIGHT // 2, RED)
        if not game_over: player.draw(screen, camera_x, shake_offset)
        if current_boss: current_boss.draw(screen, camera_x, shake_offset)
        if centipede_boss: centipede_boss.draw(screen, camera_x, shake_offset)
        for p in projectiles: p.draw(screen, camera_x, shake_offset)
        for s in star_fragments: s.draw(screen, camera_x, shake_offset)
        for e in enemies: e.draw(screen, camera_x, shake_offset)
        for g in glitch_seekers: g.draw(screen, camera_x, shake_offset)
        for pu in pickups: pu.draw(screen, camera_x, shake_offset)
        for sp in salvage_pods: sp.draw(screen, camera_x, shake_offset)
        for a in asteroids: a.draw(screen, camera_x, shake_offset)
        for part in particles: part.draw(screen, camera_x, shake_offset)
        draw_text(screen, f"SCORE: {score}", 24, 10, 10); draw_text(screen, f"LIVES: {lives}", 24, 10, 40); draw_text(screen, "SHIELD", 18, 10, 75, GREEN)

        if autopilot:
            diag_x = SCREEN_WIDTH - 220
            pygame.draw.rect(screen, (20, 20, 40), (diag_x - 10, 40, 210, 160))
            pygame.draw.rect(screen, CYAN, (diag_x - 10, 40, 210, 160), 1)
            draw_text(screen, "PILOT SYSTEMS", 14, diag_x + 95, 50, CYAN, center=True)
            labels = ["THRUST", "LEFT", "RIGHT", "FIRE", "SHIELD"]
            for i, p in enumerate(autopilot_telemetry["probs"]):
                draw_text(screen, labels[i], 12, diag_x, 75 + i * 20, WHITE)
                pygame.draw.rect(screen, (50, 50, 50), (diag_x + 60, 75 + i * 20, 100, 10))
                pygame.draw.rect(screen, NEON_BLUE if p > 0.5 else PURPLE, (diag_x + 60, 75 + i * 20, int(p * 100), 10))
            draw_text(screen, "THREAT", 10, diag_x + 120, 180, RED)
            pygame.draw.rect(screen, (50, 0, 0), (diag_x + 160, 180, 40, 8))
            pygame.draw.rect(screen, RED, (diag_x + 160, 180, int(autopilot_telemetry['risk'] * 40), 8))
            draw_text(screen, "SIGNAL", 10, diag_x + 120, 200, GREEN)
            pygame.draw.rect(screen, (0, 50, 0), (diag_x + 160, 200, 40, 8))
            pygame.draw.rect(screen, GREEN, (diag_x + 160, 200, int(autopilot_telemetry['opp'] * 40), 8))
            draw_text(screen, "AUTOPILOT ACTIVE", 18, SCREEN_WIDTH - 200, 10, RED)

        if pygame.time.get_ticks() % 6857 < 20:
            tension = autopilot_telemetry["risk"] if autopilot else 0.0
            bgm_sound.stop()
            bgm_sound = bgm_gen.generate_bgm(tension=tension)
            bgm_sound.play(loops=-1)

        pygame.draw.rect(screen, WHITE, (85, 80, 104, 14), 1); pygame.draw.rect(screen, GREEN, (87, 82, int(player.shield_energy), 10)); bar_x = SCREEN_WIDTH // 2 - 200
        for i, label in enumerate(POWERUP_LABELS):
            rect = pygame.Rect(bar_x + i * 105, SCREEN_HEIGHT - 40, 100, 30); color = YELLOW if player.powerup_index == i else (50, 50, 50)
            pygame.draw.rect(screen, color, rect, 2); draw_text(screen, label, 14, rect.centerx, rect.centery, color, center=True)
        if player.current_weapon is not None: draw_text(screen, f"WEAPON: {WEAPON_LABELS[player.current_weapon]}", 18, 10, 125, CYAN)
        if player.claiming: draw_text(screen, "CLAIMING TERRITORY", 18, 10, 100, YELLOW)
        if current_transmission:
            box_rect = pygame.Rect(100, 200, 600, 200); pygame.draw.rect(screen, BLACK, box_rect); pygame.draw.rect(screen, CYAN, box_rect, 2)
            draw_text(screen, "INCOMING TRANSMISSION...", 18, 120, 215, CYAN); draw_text(screen, current_transmission, 20, 120, 260, WHITE, wrap_width=560)
            draw_text(screen, "PRESS ANY KEY TO CONTINUE", 16, 400, 370, YELLOW, center=True)
        pygame.draw.rect(screen, NEON_BLUE, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 4)
        if game_over:
            draw_text(screen, "GAME OVER", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, YELLOW, True)
            draw_text(screen, f"FINAL SCORE: {score}", 32, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, WHITE, True)
            draw_text(screen, "PRESS 'R' TO RESTART", 24, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70, WHITE, True)
        pygame.display.flip(); clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
