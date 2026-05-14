import pygame
import math
import random
import array
import numpy as np
import json
import os

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
WEAPON_LABELS = ["PULSE", "REAR", "SPREAD", "WAVE", "LANCE", "SEEKER"]
WEAPON_COLORS = {0: (0, 255, 255), 1: (80, 120, 255), 2: (0, 255, 100), 3: (255, 0, 255), 4: (255, 255, 0), 5: (255, 140, 0)}
WEAPON_LETTERS = {0: "P", 1: "R", 2: "S", 3: "W", 4: "L", 5: "K"}
BOSS_SCORE_MILESTONE = 20000
BOSS_SCORE_CENTIPEDE = 40000
SALVAGE_POD_LIFESPAN = 480 # 8 seconds

# CRT / Visual Effect Defaults
CRT_SCANLINE_ALPHA = 22
CRT_SCANLINE_SPACING = 3
CRT_VIGNETTE_STRENGTH = 90
CRT_CHROMA_OFFSET = 2
CRT_BLOOM_THRESHOLD = 180
CRT_BLOOM_INTENSITY = 0.35
PHOSPHOR_DECAY_ALPHA = 30  # Lower = longer trails (alpha subtracted per frame)

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

class CRTPostProcessor:
    """Retro-futuristic CRT post-processing pipeline.
    Applies scanlines, vignette, chromatic aberration, and bloom."""
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.enabled = True
        self._build_scanline_surface()
        self._build_vignette_surface()

    def _build_scanline_surface(self):
        self.scanline_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for y in range(0, self.h, CRT_SCANLINE_SPACING):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, CRT_SCANLINE_ALPHA), (0, y), (self.w, y), 1)

    def _build_vignette_surface(self):
        self.vignette_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        cx, cy = self.w // 2, self.h // 2
        max_r = math.sqrt(cx * cx + cy * cy)
        # Build vignette in rings from outside in
        for r in range(int(max_r), 0, -4):
            alpha = int((1.0 - (r / max_r) ** 1.5) * CRT_VIGNETTE_STRENGTH)
            alpha = max(0, min(255, alpha))
            if alpha > 0:
                pygame.draw.circle(self.vignette_surf, (0, 0, 0, alpha), (cx, cy), r)

    def apply(self, screen):
        if not self.enabled:
            return
        # Chromatic aberration: offset red channel left, blue channel right
        offset = CRT_CHROMA_OFFSET
        if offset > 0:
            # Extract and offset channels
            px_arr = pygame.surfarray.pixels3d(screen)
            # Shift red channel left (negative x)
            red_shifted = np.roll(px_arr[:, :, 0], -offset, axis=0)
            # Shift blue channel right (positive x)
            blue_shifted = np.roll(px_arr[:, :, 2], offset, axis=0)
            px_arr[:, :, 0] = red_shifted
            px_arr[:, :, 2] = blue_shifted
            del px_arr  # Release surface lock

        # Bloom: extract bright pixels, blur, overlay
        self._apply_bloom(screen)

        # Scanlines overlay
        screen.blit(self.scanline_surf, (0, 0))

        # Vignette overlay
        screen.blit(self.vignette_surf, (0, 0))

    def _apply_bloom(self, screen):
        # Downscale for cheap blur
        small_w, small_h = self.w // 4, self.h // 4
        small = pygame.transform.smoothscale(screen, (small_w, small_h))
        # Threshold: darken non-bright pixels
        px = pygame.surfarray.pixels3d(small)
        brightness = px.max(axis=2)
        mask = brightness < CRT_BLOOM_THRESHOLD
        px[mask] = 0
        del px
        # Scale back up (creates natural blur)
        bloom = pygame.transform.smoothscale(small, (self.w, self.h))
        bloom.set_alpha(int(CRT_BLOOM_INTENSITY * 255))
        screen.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


class PhosphorTrail:
    """Persistent phosphor decay surface — objects leave fading afterimages like a CRT."""
    def __init__(self, width, height):
        self.w, self.h = width, height
        # RGB surface (no alpha needed for the trail itself)
        self.trail_surf = pygame.Surface((width, height))
        self.trail_surf.fill(BLACK)
        # Decay multiplier surface — dims the trail each frame
        self.decay_surf = pygame.Surface((width, height))
        decay_val = 255 - PHOSPHOR_DECAY_ALPHA  # e.g., 225 means each pixel retains ~88% brightness
        self.decay_surf.fill((decay_val, decay_val, decay_val))
        self.enabled = True

    def capture(self, source_screen):
        """Imprint the current frame onto the trail (bright pixels dominate)."""
        if not self.enabled:
            return
        # Decay existing trail first (multiplicative darkening toward black)
        self.trail_surf.blit(self.decay_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        # Stamp the new frame — brighter pixels overwrite dimmer trail pixels
        self.trail_surf.blit(source_screen, (0, 0), special_flags=pygame.BLEND_RGB_MAX)

    def apply(self, screen):
        """Overlay the phosphor trail at reduced opacity."""
        if not self.enabled:
            return
        self.trail_surf.set_alpha(60)  # Subtle ghost overlay
        screen.blit(self.trail_surf, (0, 0))

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

    def _generate_808(self, freq, duration_samples, volume=0.8, slide_to=None):
        """808-style sub bass: sine wave with pitch slide and long sustain."""
        t = np.linspace(0, duration_samples / self.sample_rate, int(duration_samples), False)
        if slide_to:
            # Quick exponential pitch slide (like a real 808)
            slide_curve = np.exp(-8.0 * np.linspace(0, 1, len(t)))
            freqs = slide_to + (freq - slide_to) * slide_curve
        else:
            freqs = freq
        # Pure sine for sub, slight saturation for presence
        wave = np.sin(2 * np.pi * freqs * t)
        wave = np.tanh(wave * 1.5)  # Soft clipping for warmth
        # Long sustain envelope with gentle decay
        env = np.exp(-0.8 * np.linspace(0, 1, len(t)))
        return (np.clip(wave, -1, 1) * env * volume * 32767).astype(np.int16)

    def _generate_pad(self, freq, duration_samples, volume=0.15):
        """Dark atmospheric pad: layered detuned sines with slow attack."""
        t = np.linspace(0, duration_samples / self.sample_rate, int(duration_samples), False)
        # Layer multiple slightly detuned oscillators for width
        wave = np.sin(2 * np.pi * freq * t)
        wave += 0.7 * np.sin(2 * np.pi * (freq * 1.003) * t)  # Slight detune
        wave += 0.7 * np.sin(2 * np.pi * (freq * 0.997) * t)  # Other direction
        wave += 0.4 * np.sin(2 * np.pi * (freq * 2.01) * t)   # Octave harmonic
        # Slow attack, long sustain, gentle release
        attack = np.minimum(np.linspace(0, 1, len(t) // 4), 1.0)
        attack = np.pad(attack, (0, len(t) - len(attack)), constant_values=1.0)
        release = np.exp(-0.3 * np.linspace(0, 1, len(t)))
        env = attack * release
        return (np.clip(wave / 3, -1, 1) * env * volume * 32767).astype(np.int16)

    def generate_bgm(self, tension=0.0):
        # 8-bar loop, 140 BPM (UK drill / type beat range)
        bar_count = 8
        total = int((60 / self.bpm) * bar_count * 4 * self.sample_rate)
        master_buffer = np.zeros(total, dtype=np.float64)
        beat_s = 60 / self.bpm
        beat_samples = int(beat_s * self.sample_rate)

        # --- Minor key base frequencies (generative: slight randomization each regen) ---
        root = 32 + tension * 8  # Deep sub root
        minor_third = root * 1.2
        fifth = root * 1.5
        minor_seventh = root * 1.8
        bass_pattern = [root, root, minor_third, fifth, root, minor_seventh, root, fifth]

        # --- 808 Bass (sliding, long sustain) ---
        for bar in range(bar_count):
            base_idx = int((bar * 4 * beat_s) * self.sample_rate)
            bass_freq = bass_pattern[bar % len(bass_pattern)]

            # Main 808 hit on beat 1
            slide_target = bass_freq * random.uniform(0.4, 0.6)
            bass = self._generate_808(bass_freq, beat_samples * 3.5, volume=0.7 + tension * 0.15, slide_to=slide_target)
            master_buffer[base_idx:base_idx+len(bass)] += bass

            # Occasional short 808 bounce on beat 3 (generative)
            if random.random() < 0.4 + tension * 0.3:
                bounce_idx = int(base_idx + 2 * beat_samples)
                bounce_freq = bass_freq * random.choice([1.0, 1.5, 0.75])
                bounce = self._generate_808(bounce_freq, beat_samples * 1.2, volume=0.45, slide_to=bounce_freq * 0.5)
                master_buffer[bounce_idx:bounce_idx+len(bounce)] += bounce

        # --- Trap hi-hat pattern (with rolls and ghost notes) ---
        sixteenth = beat_samples // 4
        for bar in range(bar_count):
            base_idx = int((bar * 4 * beat_s) * self.sample_rate)
            for step in range(16):  # 16 sixteenth notes per bar
                h_start = int(base_idx + step * sixteenth)

                # Base pattern: hits on every other sixteenth with some variation
                if step % 2 == 0:
                    vel = random.uniform(0.06, 0.14) + tension * 0.08
                    hat_len = random.randint(800, 1400)
                    hihat = self._generate_noise(hat_len, volume=vel)
                    master_buffer[h_start:h_start+len(hihat)] += hihat
                # Ghost notes (quiet, random)
                elif random.random() < 0.3 + tension * 0.2:
                    vel = random.uniform(0.02, 0.06)
                    hihat = self._generate_noise(600, volume=vel)
                    master_buffer[h_start:h_start+len(hihat)] += hihat

                # Hi-hat rolls (32nd note bursts — signature UK drill pattern)
                if step in (6, 7, 14, 15) and random.random() < 0.5 + tension * 0.3:
                    thirty_second = sixteenth // 2
                    for r in range(2):
                        roll_start = h_start + r * thirty_second
                        roll_vel = random.uniform(0.04, 0.1) * (1.0 + r * 0.3)
                        roll = self._generate_noise(500, volume=roll_vel)
                        if roll_start + len(roll) < total:
                            master_buffer[roll_start:roll_start+len(roll)] += roll

        # --- Snare / clap on beats 2 and 4 ---
        for bar in range(bar_count):
            base_idx = int((bar * 4 * beat_s) * self.sample_rate)
            for beat in [1, 3]:  # Beats 2 and 4 (0-indexed)
                snare_idx = int(base_idx + beat * beat_samples)
                # Layered snare: noise burst + pitched transient
                snare_body = self._generate_noise(4000 + int(tension * 3000), volume=0.25 + tension * 0.15)
                snare_click = self._generate_tone(200, 1500, volume=0.15, slide_to=80, richness=0.2)
                master_buffer[snare_idx:snare_idx+len(snare_body)] += snare_body
                master_buffer[snare_idx:snare_idx+len(snare_click)] += snare_click

        # --- Dark atmospheric pad (replaces arpeggiator) ---
        pad_notes = [root * 4, minor_third * 4, fifth * 2, minor_seventh * 2]
        pad_duration = beat_samples * 8  # 2 bars per pad
        pad_volume = 0.08 + tension * 0.06
        for i, note in enumerate(pad_notes):
            pad_start = int(i * 2 * 4 * beat_s * self.sample_rate)
            if pad_start + pad_duration > total:
                pad_duration = total - pad_start
            if pad_duration > 0:
                pad = self._generate_pad(note, pad_duration, volume=pad_volume)
                master_buffer[pad_start:pad_start+len(pad)] += pad

        # --- Sparse melodic stabs (generative — different each time) ---
        if tension > 0.2:
            pentatonic = [root * 8, minor_third * 8, fifth * 4, minor_seventh * 4, root * 16]
            stab_volume = 0.06 + (tension - 0.2) * 0.12
            num_stabs = random.randint(3, 7)
            for _ in range(num_stabs):
                stab_bar = random.randint(0, bar_count - 1)
                stab_beat = random.choice([0, 0.5, 1, 2, 2.5, 3])
                stab_start = int((stab_bar * 4 + stab_beat) * beat_s * self.sample_rate)
                stab_freq = random.choice(pentatonic)
                stab = self._generate_tone(stab_freq, beat_samples * random.uniform(0.3, 0.8),
                                          volume=stab_volume, richness=0.15)
                if stab_start + len(stab) < total:
                    master_buffer[stab_start:stab_start+len(stab)] += stab

        # Clip and convert to int16
        master_buffer = np.clip(master_buffer, -32767, 32767).astype(np.int16)
        return pygame.mixer.Sound(buffer=master_buffer)

    def generate_sfx(self):
        fire = self._generate_tone(800, 4000, volume=0.2, slide_to=200)
        exp = self._generate_noise(8000, volume=0.2)
        hit = self._generate_tone(100, 6000, volume=0.3, slide_to=20)
        weapon = np.concatenate([
            self._generate_tone(1200, 4000, volume=0.4, slide_to=800),
            self._generate_tone(1000, 4000, volume=0.4, slide_to=600)
        ])
        # New SFX
        graze = self._generate_tone(1500, 2000, volume=0.15, slide_to=2000, richness=0.2)
        claim = np.concatenate([
            self._generate_tone(400, 3000, volume=0.3, slide_to=800),
            self._generate_tone(800, 4000, volume=0.35, slide_to=1200)
        ])
        powerup = np.concatenate([
            self._generate_tone(600, 2000, volume=0.25, slide_to=900),
            self._generate_tone(900, 2000, volume=0.25, slide_to=1200),
            self._generate_tone(1200, 3000, volume=0.3, slide_to=1600)
        ])
        boss_hit = np.concatenate([
            self._generate_tone(60, 4000, volume=0.4, slide_to=30),
            self._generate_noise(6000, volume=0.25)
        ])
        return {
            'fire': pygame.mixer.Sound(buffer=fire),
            'exp': pygame.mixer.Sound(buffer=exp),
            'hit': pygame.mixer.Sound(buffer=hit),
            'weapon': pygame.mixer.Sound(buffer=weapon),
            'graze': pygame.mixer.Sound(buffer=graze),
            'claim': pygame.mixer.Sound(buffer=claim),
            'powerup': pygame.mixer.Sound(buffer=powerup),
            'boss_hit': pygame.mixer.Sound(buffer=boss_hit)
        }

class SalvagePod:
    def __init__(self, pos, weapon_stack, option_count):
        if isinstance(weapon_stack, list):
            self.weapon_stack = list(weapon_stack)
        elif weapon_stack is not None:
            self.weapon_stack = [weapon_stack]
        else:
            self.weapon_stack = []
        self.pos, self.option_count, self.lifespan, self.size, self.timer, self.being_siphoned = list(pos), option_count, SALVAGE_POD_LIFESPAN, 20, 0, False
    @property
    def weapon(self):
        return self.weapon_stack[0] if self.weapon_stack else None
    def update(self): self.timer += 1; self.lifespan -= 1; self.being_siphoned = False
    def draw(self, screen, camera_x, shake_offset):
        if self.lifespan > 120 or (self.timer % 10 < 5):
            cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
            pygame.draw.circle(screen, NEON_BLUE, (int(cx), int(cy)), self.size, 2); draw_text(screen, "SALVAGE", 12, cx, cy - 25, NEON_BLUE, center=True)
            for i, wid in enumerate(self.weapon_stack):
                color = WEAPON_COLORS.get(wid, WHITE)
                pygame.draw.rect(screen, color, (cx - 8 + i * 10, cy - 6, 8, 12), 1)
            if not self.weapon_stack:
                pygame.draw.rect(screen, WHITE, (cx - 6, cy - 6, 12, 12), 1)

class WeaponPickup:
    def __init__(self, x_pos): self.pos, self.type, self.size, self.timer = [x_pos, random.randrange(100, SCREEN_HEIGHT - 100)], random.randint(0, 5), 15, 0
    # Allow forced weapon type for testing/curriculum
    weapon_type = property(lambda self: self.type)
    def update(self): self.timer += 1
    def draw(self, screen, camera_x, shake_offset):
        color = WEAPON_COLORS.get(self.type, CYAN); letter = WEAPON_LETTERS.get(self.type, "?")
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        if self.timer % 10 < 5:
            pygame.draw.rect(screen, color, (int(cx-10), int(cy-10), 20, 20), 2)
            draw_text(screen, letter, 14, cx, cy, color, center=True)
        # Subtle glow pulse
        pulse = abs(math.sin(self.timer * 0.08))
        pygame.draw.circle(screen, tuple(int(c * pulse * 0.3) for c in color), (int(cx), int(cy)), 14, 1)

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
    def __init__(self, pos, angle, is_enemy=False, speed=PROJECTILE_SPEED, weapon_type=None):
        self.pos, self.velocity, self.lifespan, self.is_enemy, self.grazed = list(pos), [math.cos(angle) * speed, math.sin(angle) * speed], PROJECTILE_LIFESPAN, is_enemy, False
        self.weapon_type = weapon_type
        self.piercing = (weapon_type == 4)  # LANCE passes through
        self.age = 0
        self.base_angle = angle
        # SEEKER moves slower to compensate for homing
        if weapon_type == 5 and not is_enemy:
            self.velocity = [math.cos(angle) * speed * 0.6, math.sin(angle) * speed * 0.6]
            self.lifespan = int(PROJECTILE_LIFESPAN * 1.5)
        # LANCE gets extended range
        if weapon_type == 4 and not is_enemy:
            self.lifespan = int(PROJECTILE_LIFESPAN * 1.4)
    def update(self, enemies=None):
        self.age += 1
        # WAVE: sinusoidal perpendicular offset
        if self.weapon_type == 3 and not self.is_enemy:
            perp_x = -self.velocity[1]; perp_y = self.velocity[0]
            mag = math.sqrt(perp_x**2 + perp_y**2) or 1
            wave = math.sin(self.age * 0.3) * 3
            self.pos[0] += self.velocity[0] + (perp_x / mag) * wave
            self.pos[1] += self.velocity[1] + (perp_y / mag) * wave
        # SEEKER: gentle homing toward nearest enemy
        elif self.weapon_type == 5 and not self.is_enemy and enemies:
            nearest, min_d = None, float('inf')
            for e in enemies:
                d = get_distance_sq(self.pos, e.pos)
                if d < min_d: nearest, min_d = e, d
            if nearest and min_d < 400000:  # ~630px range
                desired = math.atan2(nearest.pos[1] - self.pos[1], nearest.pos[0] - self.pos[0])
                current = math.atan2(self.velocity[1], self.velocity[0])
                diff = desired - current
                while diff > math.pi: diff -= 2 * math.pi
                while diff < -math.pi: diff += 2 * math.pi
                turn = max(-0.05, min(0.05, diff))
                speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                new_angle = current + turn
                self.velocity = [math.cos(new_angle) * speed, math.sin(new_angle) * speed]
            self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]
        else:
            self.pos[0] += self.velocity[0]; self.pos[1] += self.velocity[1]
        self.lifespan -= 1
    def draw(self, screen, camera_x, shake_offset=(0,0)):
        cx, cy = self.pos[0] - camera_x + shake_offset[0], self.pos[1] + shake_offset[1]
        if self.is_enemy:
            pygame.draw.circle(screen, RED, (int(cx), int(cy)), 2)
            if random.random() > 0.5: pygame.draw.circle(screen, WHITE, (int(cx), int(cy)), 4, 1)
            return
        wt = self.weapon_type
        if wt == 3:  # WAVE — flickering magenta dot
            flicker = 2 + int(abs(math.sin(self.age * 0.4)) * 3)
            pygame.draw.circle(screen, (255, 0, 255), (int(cx), int(cy)), flicker)
            if self.age % 3 == 0: pygame.draw.circle(screen, (255, 100, 255), (int(cx), int(cy)), flicker + 2, 1)
        elif wt == 4:  # LANCE — long thin line in velocity direction
            angle = math.atan2(self.velocity[1], self.velocity[0])
            ex, ey = cx + math.cos(angle) * 12, cy + math.sin(angle) * 12
            pygame.draw.line(screen, YELLOW, (int(cx - math.cos(angle) * 4), int(cy - math.sin(angle) * 4)), (int(ex), int(ey)), 2)
            pygame.draw.circle(screen, WHITE, (int(ex), int(ey)), 1)
        elif wt == 5:  # SEEKER — rotating diamond
            angle = self.age * 0.15
            sz = 4
            pts = [(cx + math.cos(angle + i * math.pi/2) * sz, cy + math.sin(angle + i * math.pi/2) * sz) for i in range(4)]
            pygame.draw.polygon(screen, (255, 140, 0), pts, 0)
            pygame.draw.polygon(screen, WHITE, pts, 1)
        elif wt == 2:  # SPREAD — small triangle
            angle = math.atan2(self.velocity[1], self.velocity[0])
            pts = [(cx + math.cos(angle) * 5, cy + math.sin(angle) * 5),
                   (cx + math.cos(angle + 2.5) * 3, cy + math.sin(angle + 2.5) * 3),
                   (cx + math.cos(angle - 2.5) * 3, cy + math.sin(angle - 2.5) * 3)]
            pygame.draw.polygon(screen, (0, 255, 100), pts, 0)
        elif wt == 1:  # REAR — cyan with trail line
            pygame.draw.circle(screen, (80, 120, 255), (int(cx), int(cy)), 3)
            angle = math.atan2(self.velocity[1], self.velocity[0])
            pygame.draw.line(screen, (40, 60, 180), (int(cx), int(cy)), (int(cx - math.cos(angle) * 8), int(cy - math.sin(angle) * 8)), 1)
        else:  # PULSE (0) or default — standard cyan dot
            pygame.draw.circle(screen, CYAN, (int(cx), int(cy)), 2)
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
        self.trail, self.claiming, self.speed_boost, self.has_double, self.options, self.powerup_index = [], False, 0, False, [], -1
        self.weapon_stack = []  # list of weapon IDs, max 2 (fusion)
    @property
    def current_weapon(self):
        """Backward compat: returns first weapon in stack or None."""
        return self.weapon_stack[0] if self.weapon_stack else None
    @current_weapon.setter
    def current_weapon(self, value):
        """Backward compat: setting replaces the entire stack."""
        if value is None:
            self.weapon_stack = []
        else:
            self.weapon_stack = [value]
    def add_weapon(self, weapon_id):
        """Add a weapon to the stack with fusion logic."""
        if len(self.weapon_stack) == 0:
            self.weapon_stack = [weapon_id]
        elif len(self.weapon_stack) == 1:
            self.weapon_stack.append(weapon_id)  # fuse!
        else:
            # FIFO: drop oldest, add new
            self.weapon_stack = [self.weapon_stack[1], weapon_id]
    def rotate(self, direction):
        if not self.shield_active: self.angle += direction * (SHIP_ROTATION_SPEED + self.speed_boost * 0.02)
    def thrust(self):
        if not self.shield_active: accel = SHIP_THRUST_ACCELERATION + self.speed_boost * 0.05; self.velocity[0] += math.cos(self.angle) * accel; self.velocity[1] += math.sin(self.angle) * accel
    def _emit_weapon_shots(self, weapon_id, tip_x, tip_y):
        """Generate projectiles for a single weapon type."""
        shots = []
        fwd_pos = [self.pos[0] + tip_x, self.pos[1] + tip_y]
        rear_pos = [self.pos[0] - tip_x, self.pos[1] - tip_y]
        if weapon_id == 0:  # PULSE — single fast shot
            shots.append(Projectile(list(fwd_pos), self.angle, weapon_type=0))
        elif weapon_id == 1:  # REAR — front + back
            shots.append(Projectile(list(fwd_pos), self.angle, weapon_type=1))
            shots.append(Projectile(list(rear_pos), self.angle + math.pi, weapon_type=1))
        elif weapon_id == 2:  # SPREAD — 3-way fan
            for offset in [-0.2, 0, 0.2]:
                shots.append(Projectile(list(fwd_pos), self.angle + offset, weapon_type=2))
        elif weapon_id == 3:  # WAVE — sinusoidal path
            shots.append(Projectile(list(fwd_pos), self.angle, weapon_type=3))
        elif weapon_id == 4:  # LANCE — piercing line
            shots.append(Projectile(list(fwd_pos), self.angle, weapon_type=4))
        elif weapon_id == 5:  # SEEKER — homing
            shots.append(Projectile(list(fwd_pos), self.angle, weapon_type=5))
        return shots
    def fire(self):
        if not self.shield_active and not self.claiming:
            shots = []
            tip_x, tip_y = rotate_point((self.size, 0), self.angle)
            if self.weapon_stack:
                for wid in self.weapon_stack:
                    shots.extend(self._emit_weapon_shots(wid, tip_x, tip_y))
            else:
                # Default: single forward shot (no weapon equipped)
                shots.append(Projectile([self.pos[0] + tip_x, self.pos[1] + tip_y], self.angle, weapon_type=0))
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

class FloatingText:
    """Score popup that drifts upward and fades out."""
    def __init__(self, pos, text, color=WHITE, size=18):
        self.pos = list(pos)
        self.text, self.color, self.size = text, color, size
        self.lifespan = 45
        self.max_life = 45
    def update(self):
        self.pos[1] -= 1.2; self.lifespan -= 1
    def draw(self, screen, camera_x, shake_offset=(0, 0)):
        if self.lifespan > 0:
            alpha_ratio = self.lifespan / self.max_life
            # Fade the color toward black
            c = tuple(int(ch * alpha_ratio) for ch in self.color)
            cx = self.pos[0] - camera_x + shake_offset[0]
            cy = self.pos[1] + shake_offset[1]
            draw_text(screen, self.text, self.size, int(cx), int(cy), c, center=True)

COMBO_WINDOW = 120  # frames (~2 seconds at 60fps)
COMBO_TIERS = [1, 2, 4, 8, 16]  # multiplier tiers at 0, 1, 2, 3, 4+ kills in window

class ComboTracker:
    """Tracks chain kills and provides a score multiplier."""
    def __init__(self):
        self.chain = 0          # kills in current window
        self.timer = 0          # frames since last kill
        self.multiplier = 1
        self.display_timer = 0  # for pulsing the multiplier display
    def register_kill(self):
        self.chain += 1; self.timer = COMBO_WINDOW; self.display_timer = 20
        tier = min(self.chain, len(COMBO_TIERS) - 1)
        self.multiplier = COMBO_TIERS[tier]
    def reset(self):
        """Call on player damage."""
        self.chain, self.multiplier, self.timer = 0, 1, 0
    def update(self):
        if self.timer > 0:
            self.timer -= 1
            if self.timer == 0: self.chain, self.multiplier = 0, 1
        if self.display_timer > 0: self.display_timer -= 1
    def apply(self, base_score):
        """Returns the multiplied score."""
        return base_score * self.multiplier


def get_state(player, asteroids, enemies, projectiles, cam_x,
              combo=None, star_fragments=None, salvage_pods=None,
              score=0, lives=3, scroll_speed=1.5, boss_active=False):
    """Returns normalized telemetry readout as a list of 75 floats.

    Channels 0-60: Legacy oscilloscope format (backward compatible).
    Channels 61-74: Extended harmonic analysis data.
    """
    # --- Legacy channels (0-60) ---
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

    # --- Extended harmonic channels (61-74) ---
    combo_mult = combo.multiplier / 16.0 if combo else 0.0
    combo_decay = combo.timer / 120.0 if combo else 0.0
    dist_traveled = cam_x / 10000.0
    boss_flag = 1.0 if boss_active else 0.0
    claim_flag = 1.0 if player.claiming else 0.0
    weapon_ch = (player.weapon_stack[0] + 1) / 7.0 if player.weapon_stack else 0.0
    weapon_ch2 = (player.weapon_stack[1] + 1) / 7.0 if len(player.weapon_stack) > 1 else 0.0
    option_ch = len(player.options) / 2.0
    lives_ch = lives / 3.0
    scroll_ch = scroll_speed / 5.0
    shield_flag = 1.0 if player.shield_active else 0.0

    # Nearest star fragment (opportunity signal)
    sf_dist, sf_angle = 0.0, 0.0
    if star_fragments:
        nearest_sf = min(star_fragments, key=lambda s: get_distance_sq(player.pos, s.pos))
        sf_dist = min(get_distance(player.pos, nearest_sf.pos) / 800.0, 1.0)
        sf_angle = math.atan2(nearest_sf.pos[1]-player.pos[1], nearest_sf.pos[0]-player.pos[0]) / 3.14

    # Nearest salvage pod (recovery opportunity)
    sp_dist, sp_angle = 0.0, 0.0
    if salvage_pods:
        nearest_sp = min(salvage_pods, key=lambda s: get_distance_sq(player.pos, s.pos))
        sp_dist = min(get_distance(player.pos, nearest_sp.pos) / 800.0, 1.0)
        sp_angle = math.atan2(nearest_sp.pos[1]-player.pos[1], nearest_sp.pos[0]-player.pos[0]) / 3.14

    obs.extend([combo_mult, combo_decay, dist_traveled, boss_flag, claim_flag,
                weapon_ch, option_ch, lives_ch, scroll_ch, shield_flag,
                sf_dist, sf_angle, sp_dist, sp_angle, weapon_ch2])

    return obs

# === OSCILLOSCOPE TAP INTERFACE ===
# These module-level slots allow external signal processors to interface with
# the simulation. Set them before calling main() to enable automated analysis.

# External signal processor. Set to an object with .step(telemetry) -> list[float x5 or x6]
# to enable automated navigation. Channel 5 (claim) is optional for backward compat.
# Optional: .telemetry property -> dict.
_AUTOPILOT_CONTROLLER = None

# Session recorder. Set to a callable to capture simulation telemetry.
# Signature: callable(telemetry, controls, signal_strength, terminated, session_data)
_SESSION_OBSERVER = None

# Simulation calibration parameters. Set to a dict to override defaults.
# Recognized fields (all optional):
#   rift_density       -> NUM_INITIAL_ASTEROIDS, MAX_ASTEROIDS
#   echo_aggression    -> ENEMY_SPAWN_CHANCE, GLITCH_SEEKER_CHANCE
#   void_velocity      -> BASE_SCROLL_SPEED, FORCED_SCROLL_INC
#   harmonic_stability -> INITIAL_LIVES
#   resonance_threshold -> BOSS_SCORE_MILESTONE, BOSS_SCORE_CENTIPEDE
#   calibration_seed   -> RNG seed for deterministic sessions
#   star_frequency     -> STAR_FRAGMENT_SPAWN_CHANCE
_SIMULATION_CONFIG = None

# Simulation rendering mode. Set to 'protocol' to run without display output.
# Default None = normal rendered mode.
_SIMULATION_MODE = None

def _apply_calibration():
    """Apply simulation calibration parameters to session constants."""
    global NUM_INITIAL_ASTEROIDS, MAX_ASTEROIDS, ENEMY_SPAWN_CHANCE, GLITCH_SEEKER_CHANCE
    global BASE_SCROLL_SPEED, FORCED_SCROLL_INC, INITIAL_LIVES
    global BOSS_SCORE_MILESTONE, BOSS_SCORE_CENTIPEDE, STAR_FRAGMENT_SPAWN_CHANCE
    if _SIMULATION_CONFIG is None:
        return
    cfg = _SIMULATION_CONFIG
    if 'rift_density' in cfg:
        NUM_INITIAL_ASTEROIDS = int(cfg['rift_density'] * 4)
        MAX_ASTEROIDS = int(cfg['rift_density'] * 10)
    if 'echo_aggression' in cfg:
        ENEMY_SPAWN_CHANCE = 0.006 * cfg['echo_aggression']
        GLITCH_SEEKER_CHANCE = 0.003 * cfg['echo_aggression']
    if 'void_velocity' in cfg:
        BASE_SCROLL_SPEED = 1.5 * cfg['void_velocity']
        FORCED_SCROLL_INC = 0.0001 * cfg['void_velocity']
    if 'harmonic_stability' in cfg:
        INITIAL_LIVES = int(cfg['harmonic_stability'])
    if 'resonance_threshold' in cfg:
        rt = cfg['resonance_threshold']
        BOSS_SCORE_MILESTONE = int(20000 * rt)
        BOSS_SCORE_CENTIPEDE = int(40000 * rt)
    if 'star_frequency' in cfg:
        STAR_FRAGMENT_SPAWN_CHANCE = cfg['star_frequency']
    if 'calibration_seed' in cfg:
        seed = cfg['calibration_seed']
        random.seed(seed)
        np.random.seed(seed)


HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")

class HighScoreManager:
    """Persists top 10 high scores with 3-character initials."""
    def __init__(self):
        self.scores = self._load()

    def _load(self):
        try:
            with open(HIGHSCORE_FILE, 'r') as f:
                data = json.load(f)
                return data[:10]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save(self):
        with open(HIGHSCORE_FILE, 'w') as f:
            json.dump(self.scores[:10], f, indent=2)

    def qualifies(self, score):
        return len(self.scores) < 10 or score > self.scores[-1]['score']

    def add(self, name, score):
        self.scores.append({'name': name[:3].upper(), 'score': score})
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        self.scores = self.scores[:10]
        self._save()


def title_screen(screen, clock, crt, phosphor):
    """Animated title screen with scrolling lore. Returns when player presses start."""
    # Decorative background asteroids
    bg_asteroids = []
    for _ in range(12):
        a = Asteroid(random.randint(0, SCREEN_WIDTH), random.randint(10, 35))
        a.velocity = [random.uniform(-1, 1), random.uniform(-0.5, 0.5)]
        bg_asteroids.append(a)

    hsm = HighScoreManager()
    timer = 0
    lore_lines = [
        "THE YEAR IS 1981.",
        "IN SCHENECTADY, NEW YORK, A LOGISTICS MANAGER",
        "NAMED GARY 'THE GEB' GEBHART DISCOVERED THAT",
        "THE CORPORATE MICROWAVE WAS LEAKING A SPECIFIC",
        "FREQUENCY EVERY TIME SOMEONE HEATED A",
        "'MEAT-LOVERS' POCKET SANDWICH.",
        "",
        "THE OSCILLOSCOPE SHOWED GEOMETRY.",
        "THE MEAT-POCKETS WERE OPENING A",
        "SUB-HARMONIC RIFT INTO THE NULL-VOID.",
    ]
    lore_scroll_y = SCREEN_HEIGHT + 20

    while True:
        timer += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    return True
                if event.key == pygame.K_F2:
                    crt.enabled = not crt.enabled; phosphor.enabled = not phosphor.enabled
                if event.key == pygame.K_F11:
                    return True  # Just start the game on F11

        # Update background
        for a in bg_asteroids:
            a.update()
            a.pos[0] %= SCREEN_WIDTH
            a.pos[1] %= SCREEN_HEIGHT
        lore_scroll_y -= 0.4
        if lore_scroll_y < -len(lore_lines) * 22:
            lore_scroll_y = SCREEN_HEIGHT + 20

        # Draw
        screen.fill(BLACK)

        # Lore crawl (dim, in the background)
        for i, line in enumerate(lore_lines):
            y = lore_scroll_y + i * 22
            if 80 < y < SCREEN_HEIGHT - 80:
                alpha = 1.0 - abs(y - SCREEN_HEIGHT // 2) / (SCREEN_HEIGHT // 2)
                c = int(alpha * 80)
                draw_text(screen, line, 14, SCREEN_WIDTH // 2, int(y), (c, c, c + 20), center=True)

        # Asteroids
        for a in bg_asteroids:
            a.draw(screen, 0, (0, 0))

        # Title — large pulsing text
        title_pulse = 0.7 + 0.3 * abs(math.sin(timer * 0.02))
        title_r = int(255 * title_pulse)
        title_g = int(20 * title_pulse)
        title_b = int(147 * title_pulse)
        draw_text(screen, "VECTOR ASTEROIDS", 52, SCREEN_WIDTH // 2, 140, (title_r, title_g, title_b), center=True)

        # Subtitle
        sub_pulse = 0.5 + 0.5 * abs(math.sin(timer * 0.015 + 1))
        draw_text(screen, "THE NULL-VOID INCIDENT", 22, SCREEN_WIDTH // 2, 190, (int(sub_pulse * 0), int(sub_pulse * 255), int(sub_pulse * 255)), center=True)

        # Year badge
        draw_text(screen, "[ 1981 ]", 16, SCREEN_WIDTH // 2, 220, (100, 100, 120), center=True)

        # Start prompt (blinks)
        if timer % 80 < 60:
            draw_text(screen, "PRESS ENTER TO BEGIN", 20, SCREEN_WIDTH // 2, 320, YELLOW, center=True)

        # Controls hint
        draw_text(screen, "ARROWS: MOVE   SPACE: FIRE   SHIFT: CLAIM   DOWN: SHIELD", 12, SCREEN_WIDTH // 2, 380, (80, 80, 100), center=True)
        draw_text(screen, "P: PAUSE   F2: CRT FX   F3: FPS   F11: FULLSCREEN", 12, SCREEN_WIDTH // 2, 400, (60, 60, 80), center=True)

        # High scores
        if hsm.scores:
            draw_text(screen, "HIGH SCORES", 18, SCREEN_WIDTH // 2, 440, CYAN, center=True)
            for i, entry in enumerate(hsm.scores[:5]):
                rank_color = YELLOW if i == 0 else WHITE
                draw_text(screen, f"{i+1}. {entry['name']}  {entry['score']:,}", 16, SCREEN_WIDTH // 2, 465 + i * 22, rank_color, center=True)

        # Border
        pygame.draw.rect(screen, NEON_BLUE, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 4)

        # Apply effects
        phosphor.capture(screen)
        phosphor.apply(screen)
        crt.apply(screen)

        pygame.display.flip()
        clock.tick(FPS)

    return True


def score_entry_screen(screen, clock, crt, phosphor, final_score):
    """3-character initial entry for high scores. Returns the initials string."""
    chars = ['A', 'A', 'A']
    cursor = 0
    timer = 0

    while True:
        timer += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    c = ord(chars[cursor])
                    chars[cursor] = chr(c + 1) if c < ord('Z') else 'A'
                elif event.key == pygame.K_DOWN:
                    c = ord(chars[cursor])
                    chars[cursor] = chr(c - 1) if c > ord('A') else 'Z'
                elif event.key == pygame.K_RIGHT:
                    cursor = min(2, cursor + 1)
                elif event.key == pygame.K_LEFT:
                    cursor = max(0, cursor - 1)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return ''.join(chars)

        screen.fill(BLACK)

        draw_text(screen, "NEW HIGH SCORE!", 36, SCREEN_WIDTH // 2, 150, YELLOW, center=True)
        draw_text(screen, f"{final_score:,}", 48, SCREEN_WIDTH // 2, 210, CYAN, center=True)
        draw_text(screen, "ENTER YOUR INITIALS", 20, SCREEN_WIDTH // 2, 280, WHITE, center=True)

        # Draw character slots
        for i, ch in enumerate(chars):
            x = SCREEN_WIDTH // 2 - 60 + i * 60
            y = 340
            color = YELLOW if i == cursor else WHITE
            draw_text(screen, ch, 48, x, y, color, center=True)
            if i == cursor and timer % 40 < 25:
                pygame.draw.line(screen, color, (x - 15, y + 25), (x + 15, y + 25), 3)

        draw_text(screen, "UP/DOWN: CHANGE   LEFT/RIGHT: MOVE   ENTER: CONFIRM", 12, SCREEN_WIDTH // 2, 420, (80, 80, 100), center=True)

        pygame.draw.rect(screen, NEON_BLUE, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 4)

        phosphor.capture(screen)
        phosphor.apply(screen)
        crt.apply(screen)

        pygame.display.flip()
        clock.tick(FPS)


def main():
    _apply_calibration()
    pygame.init(); pygame.mixer.init(); bgm_gen = BGMGenerator(); bgm_sound = bgm_gen.generate_bgm(); sfx_queue = SFXQueue(bgm_gen.generate_sfx(), bgm_gen.ms_per_16th)
    bgm_sound.play(loops=-1); screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)); pygame.display.set_caption("Vector Asteroids: Harmonic Void")
    clock, player = pygame.time.Clock(), Player(); asteroids = [Asteroid() for _ in range(NUM_INITIAL_ASTEROIDS)]
    projectiles, star_fragments, enemies, glitch_seekers, particles, pickups, salvage_pods = [], [], [], [], [], [], []
    floating_texts = []
    combo = ComboTracker()
    shake_amount, score, lives, game_over, camera_x = 0, 0, INITIAL_LIVES, False, 0
    current_scroll_speed, current_transmission, seen_milestones = BASE_SCROLL_SPEED, None, set()
    layers = [ParallaxLayer(0.2, (60, 60, 80), 40, is_lattice=True), ParallaxLayer(0.5, (100, 80, 150), 30), ParallaxLayer(0.8, (80, 150, 200), 20)]
    current_boss = None; centipede_boss = None

    # Visual effect systems
    crt = CRTPostProcessor(SCREEN_WIDTH, SCREEN_HEIGHT)
    phosphor = PhosphorTrail(SCREEN_WIDTH, SCREEN_HEIGHT)
    hsm = HighScoreManager()

    # Show title screen on launch
    if not title_screen(screen, clock, crt, phosphor):
        return

    # UI state
    paused = False
    show_fps = False
    is_fullscreen = False

    autopilot = False
    autopilot_telemetry = {"probs": [0.0]*5, "risk": 0.0, "opp": 0.0, "var": 0.0}
    last_score, last_lives = 0, INITIAL_LIVES

    running = True
    while running:
        curr_enemy_spawn_chance = ENEMY_SPAWN_CHANCE

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                # Pause toggle (works in any state except game over)
                if event.key in (pygame.K_p, pygame.K_ESCAPE) and not game_over:
                    paused = not paused; continue
                # Fullscreen toggle
                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                    continue
                # FPS counter toggle
                if event.key == pygame.K_F3: show_fps = not show_fps; continue
                # CRT effects toggle
                if event.key == pygame.K_F2: crt.enabled = not crt.enabled; phosphor.enabled = not phosphor.enabled; continue
                # Skip if paused
                if paused: continue
                if current_transmission: current_transmission = None; continue
                if event.key == pygame.K_a: autopilot = not autopilot
                if event.key == pygame.K_SPACE and not game_over:
                    for s in player.fire(): projectiles.append(s)
                if event.key == pygame.K_c and not game_over: player.activate_powerup()
                if event.key == pygame.K_r and game_over:
                    # High score entry if qualified
                    if hsm.qualifies(score):
                        initials = score_entry_screen(screen, clock, crt, phosphor, score)
                        if initials: hsm.add(initials, score)
                    # Show title screen before restarting
                    if not title_screen(screen, clock, crt, phosphor): running = False; continue
                    player.reset(); asteroids = [Asteroid() for _ in range(NUM_INITIAL_ASTEROIDS)]; projectiles, star_fragments, enemies, glitch_seekers, particles, pickups, salvage_pods = [], [], [], [], [], [], []
                    floating_texts = []; combo = ComboTracker()
                    score, lives, game_over, camera_x, shake_amount, current_scroll_speed, seen_milestones = 0, INITIAL_LIVES, False, 0, 0, BASE_SCROLL_SPEED, set(); current_boss = None; centipede_boss = None
                    last_score, last_lives = 0, INITIAL_LIVES; paused = False

        if not game_over and not current_transmission and not paused:
            state = get_state(player, asteroids, enemies, projectiles, camera_x,
                              combo=combo, star_fragments=star_fragments, salvage_pods=salvage_pods,
                              score=score, lives=lives, scroll_speed=current_scroll_speed,
                              boss_active=(current_boss is not None or centipede_boss is not None))
            keys = pygame.key.get_pressed()

            if autopilot and _AUTOPILOT_CONTROLLER is not None:
                ai_act = list(_AUTOPILOT_CONTROLLER.step(state))
                # Backward compat: 5-channel controllers get claim=0.0
                if len(ai_act) < 6: ai_act.append(0.0)
                if hasattr(_AUTOPILOT_CONTROLLER, 'telemetry'):
                    autopilot_telemetry.update(_AUTOPILOT_CONTROLLER.telemetry)
                autopilot_telemetry["probs"] = [float(a) for a in ai_act]
            elif autopilot:
                # Built-in demo pilot: simple rule-based fallback
                ai_act = [1, 0, 0, random.random() > 0.92, player.shield_energy < 15, 0]
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
                    1.0 if keys[pygame.K_DOWN] else 0.0,
                    1.0 if keys[pygame.K_LSHIFT] else 0.0
                ]

            reward = 0.01
            reward += (score - last_score) * 0.1
            if lives < last_lives: reward -= 50.0
            if player.pos[0] - camera_x < 200: reward -= 0.1
            elif player.pos[0] - camera_x > 400: reward += 0.05
            last_score, last_lives = score, lives

            if _SESSION_OBSERVER is not None:
                session_data = {
                    'score': score, 'lives': lives, 'distance': camera_x,
                    'combo_chain': combo.chain, 'combo_multiplier': combo.multiplier,
                    'boss_phase': 'resonance' if current_boss else 'centipede' if centipede_boss else 'drift',
                    'entity_count': len(asteroids) + len(enemies) + len(glitch_seekers),
                    'scroll_velocity': current_scroll_speed
                }
                _SESSION_OBSERVER(state, action, reward, game_over, session_data)

            current_scroll_speed += FORCED_SCROLL_INC; camera_x += current_scroll_speed; sfx_queue.update()
            combo.update()
            # Reset combo on damage (detected via lives change)
            if lives < last_lives: combo.reset()
            for ft in floating_texts[:]: ft.update()
            floating_texts = [ft for ft in floating_texts if ft.lifespan > 0]
            if score >= BOSS_SCORE_MILESTONE and current_boss is None and score < BOSS_SCORE_CENTIPEDE: current_boss = Boss(camera_x + SCREEN_WIDTH + 200)
            if score >= BOSS_SCORE_CENTIPEDE and centipede_boss is None: centipede_boss = CentipedeBoss(camera_x + SCREEN_WIDTH + 200)
            if random.random() < WEAPON_SPAWN_CHANCE: pickups.append(WeaponPickup(camera_x + SCREEN_WIDTH + 100))
            for p_up in pickups[:]:
                p_up.update()
                if p_up.pos[0] < camera_x - 100: pickups.remove(p_up)
                elif get_distance_sq(p_up.pos, player.pos) < (player.size + p_up.size)**2: player.add_weapon(p_up.type); sfx_queue.add('weapon'); pickups.remove(p_up)
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
                    player.weapon_stack = list(pod.weapon_stack); [player.options.append(Option(player)) for _ in range(pod.option_count)]; sfx_queue.add('weapon'); salvage_pods.remove(pod)
            if centipede_boss:
                centipede_boss.update(player)
                if not player.shield_active and player.invulnerable_frames == 0:
                    if get_distance_sq(centipede_boss.pos, player.pos) < 900:
                        sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 30, lives - 1
                        if lives <= 0 and not autopilot: game_over = True
                        else:
                            if player.weapon_stack or player.options: salvage_pods.append(SalvagePod(player.pos, player.weapon_stack, len(player.options)))
                            player.reset(); player.pos[0] = camera_x + 100
                for s in centipede_boss.segments[:]:
                    if not player.shield_active and player.invulnerable_frames == 0:
                        if get_distance_sq(s.pos, player.pos) < 400:
                             sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 30, lives - 1
                             if lives <= 0 and not autopilot: game_over = True
                             else:
                                 if player.weapon_stack or player.options: salvage_pods.append(SalvagePod(player.pos, player.weapon_stack, len(player.options)))
                                 player.reset(); player.pos[0] = camera_x + 100
            # Claim logic — driven by action channel 5 in autopilot, LSHIFT in manual
            claim_active = ai_act[5] > 0.5 if autopilot else keys[pygame.K_LSHIFT]
            if claim_active and not player.shield_active: player.claiming = True
            else:
                if player.claiming and len(player.trail) > 5:
                    if get_distance_sq(player.pos, player.trail[0]) < 2500:
                        score += 500; sfx_queue.add('claim'); create_explosion(particles, player.pos, YELLOW, 20)
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
                    if player.weapon_stack or player.options: salvage_pods.append(SalvagePod(player.pos, player.weapon_stack, len(player.options)))
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
                            if player.weapon_stack or player.options: salvage_pods.append(SalvagePod(player.pos, player.weapon_stack, len(player.options)))
                            player.reset(); player.pos[0] = camera_x + 100; glitch_seekers.remove(g)
            p_size_sq = player.size**2
            for p in projectiles[:]:
                p.update(enemies=enemies + glitch_seekers)
                if p.lifespan <= 0 or p.pos[0] < camera_x or p.pos[0] > camera_x + SCREEN_WIDTH:
                    if p in projectiles: projectiles.remove(p)
                else:
                    if p.is_enemy and not p.grazed and not player.shield_active:
                         if get_distance_sq(p.pos, player.pos) < 2500: score += 100; p.grazed = True; sfx_queue.add('graze')
                    if p.is_enemy and not player.shield_active and player.invulnerable_frames == 0:
                        if get_distance_sq(p.pos, player.pos) < p_size_sq:
                            sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 30, lives - 1
                            if lives <= 0 and not autopilot: game_over = True
                            else:
                                if player.weapon_stack or player.options: salvage_pods.append(SalvagePod(player.pos, player.weapon_stack, len(player.options)))
                                player.reset(); player.pos[0] = camera_x + 100
                            if p in projectiles: projectiles.remove(p); continue
                    for g in glitch_seekers[:]:
                        if not p.is_enemy and get_distance_sq(p.pos, g.pos) < g.size**2:
                            def kg(t=g): nonlocal score; combo.register_kill(); pts = combo.apply(1500); score += pts; floating_texts.append(FloatingText(t.pos, f"+{pts}", GREEN)); create_explosion(particles, t.pos, GREEN, 20); [glitch_seekers.remove(t) if t in glitch_seekers else None]
                            sfx_queue.add('exp', kg)
                            if not p.piercing: projectiles.remove(p)
                            break
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
                                 current_boss.health -= 1; sfx_queue.add('boss_hit'); projectiles.remove(p)
                                 if current_boss.health <= 0: score += 10000; create_explosion(particles, current_boss.pos, CYAN, 100); current_boss = None; shake_amount = 50
                                 continue
            for s in star_fragments[:]:
                s.update()
                if get_distance_sq(player.pos, s.pos) < (player.size + s.size)**2:
                    score += 1000; sfx_queue.add('powerup'); create_explosion(particles, s.pos, PURPLE, 10); star_fragments.remove(s); player.powerup_index = (player.powerup_index + 1) % len(POWERUP_LABELS)
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
                            def ke(t=e): nonlocal score; combo.register_kill(); pts = combo.apply(500); score += pts; floating_texts.append(FloatingText(t.pos, f"+{pts}", CYAN)); create_explosion(particles, t.pos, WHITE, 25); [enemies.remove(t) if t in enemies else None]
                            sfx_queue.add('exp', ke); shake_amount = 15; projectiles.remove(p); break
                    if e not in enemies: continue
                    if not player.shield_active and player.invulnerable_frames == 0:
                        if get_distance_sq(e.pos, player.pos) < (e.size + player.size)**2:
                            sfx_queue.add('hit'); create_explosion(particles, player.pos, RED, 40); shake_amount, lives = 25, lives - 1
                            if lives <= 0 and not autopilot: game_over = True
                            else:
                                if player.weapon_stack or player.options: salvage_pods.append(SalvagePod(player.pos, player.weapon_stack, len(player.options)))
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
                        if player.weapon_stack or player.options: salvage_pods.append(SalvagePod(player.pos, player.weapon_stack, len(player.options)))
                        player.reset(); player.pos[0] = camera_x + 100
                for p in projectiles[:]:
                    if get_distance_sq(p.pos, a.pos) < a.size**2:
                        def ka(t=a):
                            nonlocal score; combo.register_kill(); base = 100 if t.size > 20 else 200; pts = combo.apply(base); score += pts; floating_texts.append(FloatingText(t.pos, f"+{pts}", WHITE)); create_explosion(particles, t.pos, WHITE, 15)
                            if t.size > 15 and len(asteroids) < MAX_ASTEROIDS: asteroids.append(Asteroid(t.pos[0], t.size // 2))
                            if t in asteroids: asteroids.remove(t)
                            if len(asteroids) < MAX_ASTEROIDS: asteroids.append(Asteroid(camera_x + SCREEN_WIDTH + random.randint(400, 800)))
                        sfx_queue.add('exp', ka); shake_amount = 10
                        if not p.piercing: projectiles.remove(p)
                        break

        # === RENDERING PIPELINE ===
        shake_offset = (random.randint(-int(shake_amount), int(shake_amount)), random.randint(-int(shake_amount), int(shake_amount))) if shake_amount > 0 else (0,0)
        shake_amount *= 0.9; screen.fill(BLACK); tilt = (player.pos[1] - SCREEN_HEIGHT//2) * 0.1

        # --- Layer 1: Background ---
        for layer in layers: layer.draw(screen, camera_x, tilt_offset=tilt, shake_offset=shake_offset)
        if pygame.time.get_ticks() % 500 < 250:
            pygame.draw.line(screen, RED, (0, 0), (0, SCREEN_HEIGHT), 3); draw_text(screen, "RIFT COLLAPSE", 14, 15, SCREEN_HEIGHT // 2, RED)

        # --- Layer 2: Game world entities ---
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
        for ft in floating_texts: ft.draw(screen, camera_x, shake_offset)

        # --- Layer 3: Phosphor trail (capture before CRT, apply as underlay) ---
        phosphor.capture(screen)
        phosphor.apply(screen)

        # --- Layer 4: CRT post-processing (scanlines, bloom, vignette, chroma) ---
        crt.apply(screen)

        # --- Layer 5: HUD (rendered AFTER CRT so text stays crisp) ---
        draw_text(screen, f"SCORE: {score}", 24, 10, 10); draw_text(screen, f"LIVES: {lives}", 24, 10, 40); draw_text(screen, "SHIELD", 18, 10, 75, GREEN)
        pygame.draw.rect(screen, WHITE, (85, 80, 104, 14), 1); pygame.draw.rect(screen, GREEN, (87, 82, int(player.shield_energy), 10))

        bar_x = SCREEN_WIDTH // 2 - 200
        for i, label in enumerate(POWERUP_LABELS):
            rect = pygame.Rect(bar_x + i * 105, SCREEN_HEIGHT - 40, 100, 30); color = YELLOW if player.powerup_index == i else (50, 50, 50)
            pygame.draw.rect(screen, color, rect, 2); draw_text(screen, label, 14, rect.centerx, rect.centery, color, center=True)
        if player.weapon_stack:
            if len(player.weapon_stack) == 2:
                loadout = f"LOADOUT: {WEAPON_LABELS[player.weapon_stack[0]]} + {WEAPON_LABELS[player.weapon_stack[1]]}"
                c1, c2 = WEAPON_COLORS[player.weapon_stack[0]], WEAPON_COLORS[player.weapon_stack[1]]
                fused_color = (min(255, (c1[0]+c2[0])//2+50), min(255, (c1[1]+c2[1])//2+50), min(255, (c1[2]+c2[2])//2+50))
                draw_text(screen, loadout, 18, 10, 125, fused_color)
            else:
                draw_text(screen, f"LOADOUT: {WEAPON_LABELS[player.weapon_stack[0]]}", 18, 10, 125, WEAPON_COLORS.get(player.weapon_stack[0], CYAN))
        if player.claiming: draw_text(screen, "CLAIMING TERRITORY", 18, 10, 100, YELLOW)

        # Combo multiplier display
        if combo.multiplier > 1:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            combo_size = int(28 + combo.display_timer * 1.5)
            combo_color = (255, int(200 * pulse), int(50 * pulse))
            draw_text(screen, f"x{combo.multiplier}", combo_size, SCREEN_WIDTH // 2, 20, combo_color, center=True)
            # Chain counter
            draw_text(screen, f"CHAIN: {combo.chain}", 14, SCREEN_WIDTH // 2, 45, YELLOW, center=True)

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

        # --- Dynamic BGM regeneration ---
        if pygame.time.get_ticks() % 6857 < 20:
            # Compute tension from game state (works for all players, not just autopilot)
            entity_pressure = min(1.0, (len(enemies) + len(glitch_seekers)) / 8.0)
            scroll_pressure = min(1.0, (current_scroll_speed - BASE_SCROLL_SPEED) / 3.0)
            boss_pressure = 0.5 if current_boss else (0.7 if centipede_boss else 0.0)
            combo_energy = min(1.0, combo.chain / 6.0)
            tension = max(entity_pressure, scroll_pressure, boss_pressure, combo_energy)
            if autopilot:
                tension = max(tension, autopilot_telemetry.get("risk", 0.0))
            bgm_sound.stop()
            bgm_sound = bgm_gen.generate_bgm(tension=tension)
            bgm_sound.play(loops=-1)

        # --- Layer 6: Transmission / Game Over overlays ---
        if current_transmission:
            box_rect = pygame.Rect(100, 200, 600, 200); pygame.draw.rect(screen, BLACK, box_rect); pygame.draw.rect(screen, CYAN, box_rect, 2)
            draw_text(screen, "INCOMING TRANSMISSION...", 18, 120, 215, CYAN); draw_text(screen, current_transmission, 20, 120, 260, WHITE, wrap_width=560)
            draw_text(screen, "PRESS ANY KEY TO CONTINUE", 16, 400, 370, YELLOW, center=True)

        # Border frame
        pygame.draw.rect(screen, NEON_BLUE, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 4)

        if game_over:
            draw_text(screen, "GAME OVER", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, YELLOW, True)
            draw_text(screen, f"FINAL SCORE: {score}", 32, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, WHITE, True)
            draw_text(screen, "PRESS 'R' TO RESTART", 24, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70, WHITE, True)

        # --- Layer 7: Pause overlay ---
        if paused:
            pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 120))
            screen.blit(pause_overlay, (0, 0))
            # Pulsing pause text
            pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.003)) * 255)
            pause_color = (pulse, 255, pulse)
            draw_text(screen, "PAUSED", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30, pause_color, True)
            draw_text(screen, "P / ESC TO RESUME", 20, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30, WHITE, True)
            draw_text(screen, "F2: CRT EFFECTS   F3: FPS   F11: FULLSCREEN", 14, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 65, (120, 120, 140), True)

        # --- Layer 8: FPS counter (always on top) ---
        if show_fps:
            fps_val = clock.get_fps()
            fps_color = GREEN if fps_val >= 55 else YELLOW if fps_val >= 30 else RED
            draw_text(screen, f"FPS: {fps_val:.0f}", 16, SCREEN_WIDTH - 90, 5, fps_color)

        pygame.display.flip(); clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
