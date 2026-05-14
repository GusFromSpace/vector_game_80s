"""
NULL-VOID SIMULATION PROTOCOL
=============================
Reconstructed telemetry interface for Gary Gebhart's oscilloscope rig.

Provides a programmatic session interface for signal analysis and automated
navigation of the Null-Void rift. Supports deterministic calibration,
headless protocol execution, and real-time telemetry capture.

Originally reverse-engineered from oscilloscope recordings found in
the Schenectady EPA cleanup archives (1982, Case #NY-434-VOID).

Usage:
    from null_void_sim import NullVoidSession

    session = NullVoidSession()
    telemetry = session.reset()

    while True:
        controls = [1.0, 0.0, 0.0, 0.5, 0.0]  # thrust, left, right, fire, shield
        telemetry, signal, terminated, truncated, data = session.step(controls)
        if terminated or truncated:
            break
"""

import pygame
import math
import random
import numpy as np

# Import the simulation core
import vector_game as _core


class _NoOpSFX:
    """Silent sound queue for headless sessions."""
    def add(self, *args, **kwargs):
        # Execute callbacks if provided (they handle game logic)
        if len(args) >= 2 and callable(args[1]):
            args[1]()
    def update(self): pass


class NullVoidSession:
    """Programmatic interface to the Null-Void rift simulation.

    Provides session management, deterministic calibration, and
    telemetry capture without requiring display output.

    Args:
        calibration: Optional dict of simulation parameters.
            See _SIMULATION_CONFIG documentation for recognized fields.
        render: If True, display the simulation visually. Default False.
        max_drift: Maximum simulation ticks before session truncation.
            Default 18000 (5 minutes at 60 ticks/sec).
    """

    # Channel dimensions for signal processors
    observation_channels = 75
    control_channels = 5

    def __init__(self, calibration=None, render=False, max_drift=18000):
        self._calibration = calibration or {}
        self._render = render
        self._max_drift = max_drift
        self._tick = 0
        self._initialized = False
        self._sfx = _NoOpSFX()

        # Session objects (created on reset)
        self._player = None
        self._asteroids = None
        self._projectiles = None
        self._star_fragments = None
        self._enemies = None
        self._glitch_seekers = None
        self._particles = None
        self._pickups = None
        self._salvage_pods = None
        self._combo = None
        self._score = 0
        self._lives = _core.INITIAL_LIVES
        self._camera_x = 0
        self._scroll_speed = _core.BASE_SCROLL_SPEED
        self._current_boss = None
        self._centipede_boss = None
        self._game_over = False
        self._shake_amount = 0
        self._seen_milestones = set()
        self._current_transmission = None

        # Display objects (only if rendering)
        self._screen = None
        self._clock = None
        self._crt = None
        self._phosphor = None
        self._layers = None
        self._sfx_queue = None
        self._bgm_gen = None
        self._bgm_sound = None

    def _init_pygame(self):
        """Initialize display subsystem if rendering."""
        if self._render:
            pygame.init()
            pygame.mixer.init()
            self._screen = pygame.display.set_mode((_core.SCREEN_WIDTH, _core.SCREEN_HEIGHT))
            pygame.display.set_caption("Null-Void Protocol Session")
            self._clock = pygame.time.Clock()
            self._crt = _core.CRTPostProcessor(_core.SCREEN_WIDTH, _core.SCREEN_HEIGHT)
            self._phosphor = _core.PhosphorTrail(_core.SCREEN_WIDTH, _core.SCREEN_HEIGHT)
            self._layers = [
                _core.ParallaxLayer(0.2, (60, 60, 80), 40, is_lattice=True),
                _core.ParallaxLayer(0.5, (100, 80, 150), 30),
                _core.ParallaxLayer(0.8, (80, 150, 200), 20)
            ]
            self._bgm_gen = _core.BGMGenerator()
            self._sfx_queue = _core.SFXQueue(self._bgm_gen.generate_sfx(), self._bgm_gen.ms_per_16th)
        else:
            # Headless — minimal init for mixer (needed by SFXQueue internals)
            pygame.init()
            pygame.mixer.init()
            self._clock = pygame.time.Clock()

    def reset(self, seed=None):
        """Initialize a new simulation session.

        Args:
            seed: Optional void coordinates (int) for deterministic sessions.

        Returns:
            Initial telemetry readout (list of 75 floats).
        """
        # Apply calibration
        if seed is not None:
            self._calibration['calibration_seed'] = seed
        _core._SIMULATION_CONFIG = self._calibration
        _core._apply_calibration()

        if not self._initialized:
            self._init_pygame()
            self._initialized = True

        # Apply seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # Reset session state
        self._player = _core.Player()
        self._asteroids = [_core.Asteroid() for _ in range(_core.NUM_INITIAL_ASTEROIDS)]
        self._projectiles = []
        self._star_fragments = []
        self._enemies = []
        self._glitch_seekers = []
        self._particles = []
        self._pickups = []
        self._salvage_pods = []
        self._combo = _core.ComboTracker()
        self._score = 0
        self._lives = _core.INITIAL_LIVES
        self._camera_x = 0
        self._scroll_speed = _core.BASE_SCROLL_SPEED
        self._current_boss = None
        self._centipede_boss = None
        self._game_over = False
        self._shake_amount = 0
        self._seen_milestones = set()
        self._current_transmission = None
        self._tick = 0
        self._last_score = 0
        self._last_lives = _core.INITIAL_LIVES

        return _core.get_state(
            self._player, self._asteroids, self._enemies,
            self._projectiles, self._camera_x,
            combo=self._combo, star_fragments=self._star_fragments,
            salvage_pods=self._salvage_pods, score=self._score,
            lives=self._lives, scroll_speed=self._scroll_speed,
            boss_active=False
        )

    def step(self, controls):
        """Advance the simulation by one tick.

        Args:
            controls: List of 5 floats [thrust, left, right, fire, shield].
                Values > 0.5 are treated as active.

        Returns:
            Tuple of (telemetry, signal_strength, terminated, truncated, session_data):
                telemetry: List of 75 normalized floats.
                signal_strength: Float — composite signal quality metric.
                terminated: Bool — True if the session ended (all lives lost).
                truncated: Bool — True if max_drift exceeded.
                session_data: Dict of decoded session metrics.
        """
        if self._game_over:
            obs = _core.get_state(
                self._player, self._asteroids, self._enemies,
                self._projectiles, self._camera_x,
                combo=self._combo, star_fragments=self._star_fragments,
                salvage_pods=self._salvage_pods, score=self._score,
                lives=self._lives, scroll_speed=self._scroll_speed,
                boss_active=(self._current_boss is not None or self._centipede_boss is not None)
            )
            return obs, 0.0, True, False, self._build_session_data()

        self._tick += 1

        # Apply controls to player
        player = self._player
        if controls[1] > 0.5: player.rotate(-1)
        if controls[2] > 0.5: player.rotate(1)
        if controls[0] > 0.5: player.thrust()
        player.shield_active = controls[4] > 0.5 and player.shield_energy > 0
        if controls[3] > 0.5 and self._tick % 8 == 0:
            for s in player.fire():
                self._projectiles.append(s)

        # === Physics tick ===
        player.update(self._camera_x)
        self._scroll_speed += _core.FORCED_SCROLL_INC
        self._camera_x += self._scroll_speed
        self._combo.update()

        # Update all entities
        for a in self._asteroids: a.update()
        for p in self._projectiles[:]:
            p.update()
            if p.lifespan <= 0 or p.pos[0] < self._camera_x - 100 or p.pos[0] > self._camera_x + _core.SCREEN_WIDTH + 100:
                if p in self._projectiles: self._projectiles.remove(p)
        for e in self._enemies[:]:
            e.update(player, self._star_fragments, self._asteroids,
                    self._pickups, self._salvage_pods, self._sfx)
            if e.pos[0] < self._camera_x - 200:
                if e in self._enemies: self._enemies.remove(e)
        for g in self._glitch_seekers[:]:
            g.update(player)
        for s in self._star_fragments[:]:
            s.update()
        for p in self._particles[:]:
            p.update()
            if p.life <= 0: self._particles.remove(p)
        for pu in self._pickups[:]:
            pu.update()
        for sp in self._salvage_pods[:]:
            sp.update()

        # Spawn logic
        if random.random() < _core.STAR_FRAGMENT_SPAWN_CHANCE:
            self._star_fragments.append(_core.StarFragment(self._camera_x + _core.SCREEN_WIDTH + 100))
        if random.random() < _core.ENEMY_SPAWN_CHANCE:
            self._enemies.append(_core.Enemy(self._camera_x + _core.SCREEN_WIDTH + 100))
        if random.random() < _core.GLITCH_SEEKER_CHANCE:
            self._glitch_seekers.append(_core.GlitchSeeker(self._camera_x + _core.SCREEN_WIDTH + 200))
        if random.random() < _core.WEAPON_SPAWN_CHANCE:
            self._pickups.append(_core.WeaponPickup(self._camera_x + _core.SCREEN_WIDTH + 100))

        # Boss spawning
        if self._score >= _core.BOSS_SCORE_MILESTONE and self._current_boss is None and self._score < _core.BOSS_SCORE_CENTIPEDE:
            self._current_boss = _core.Boss(self._camera_x + _core.SCREEN_WIDTH + 200)
        if self._score >= _core.BOSS_SCORE_CENTIPEDE and self._centipede_boss is None:
            self._centipede_boss = _core.CentipedeBoss(self._camera_x + _core.SCREEN_WIDTH + 200)

        # === Collision detection (simplified for headless) ===
        # Player vs asteroids
        for a in self._asteroids[:]:
            if not player.shield_active and player.invulnerable_frames == 0:
                if _core.get_distance_sq(player.pos, a.pos) < (player.size + a.size) ** 2:
                    self._lives -= 1
                    self._shake_amount = 30
                    self._combo.reset()
                    _core.create_explosion(self._particles, player.pos, _core.RED, 40)
                    player.reset()
                    player.pos[0] = self._camera_x + 100
                    if self._lives <= 0:
                        self._game_over = True

        # Projectiles vs asteroids
        for p in self._projectiles[:]:
            if p.is_enemy: continue
            for a in self._asteroids[:]:
                if _core.get_distance_sq(p.pos, a.pos) < a.size ** 2:
                    self._combo.register_kill()
                    base = 100 if a.size > 20 else 200
                    pts = self._combo.apply(base)
                    self._score += pts
                    if a.size > 15 and len(self._asteroids) < _core.MAX_ASTEROIDS:
                        self._asteroids.append(_core.Asteroid(a.pos[0], a.size // 2))
                    if a in self._asteroids: self._asteroids.remove(a)
                    if len(self._asteroids) < _core.MAX_ASTEROIDS:
                        self._asteroids.append(_core.Asteroid(self._camera_x + _core.SCREEN_WIDTH + random.randint(400, 800)))
                    if p in self._projectiles: self._projectiles.remove(p)
                    break

        # Projectiles vs enemies
        for e in self._enemies[:]:
            for p in self._projectiles[:]:
                if not p.is_enemy and _core.get_distance_sq(e.pos, p.pos) < e.size ** 2:
                    self._combo.register_kill()
                    pts = self._combo.apply(500)
                    self._score += pts
                    if e in self._enemies: self._enemies.remove(e)
                    if p in self._projectiles: self._projectiles.remove(p)
                    break

        # Player vs enemies
        for e in self._enemies[:]:
            if not player.shield_active and player.invulnerable_frames == 0:
                if _core.get_distance_sq(player.pos, e.pos) < (player.size + e.size) ** 2:
                    self._lives -= 1
                    self._combo.reset()
                    player.reset()
                    player.pos[0] = self._camera_x + 100
                    if self._lives <= 0:
                        self._game_over = True

        # Star fragment pickup
        for s in self._star_fragments[:]:
            if _core.get_distance_sq(player.pos, s.pos) < (player.size + s.size) ** 2:
                self._score += self._combo.apply(1000)
                self._star_fragments.remove(s)
                player.powerup_index = (player.powerup_index + 1) % len(_core.POWERUP_LABELS)

        # Weapon pickup
        for pu in self._pickups[:]:
            if _core.get_distance_sq(player.pos, pu.pos) < (player.size + pu.size) ** 2:
                player.current_weapon = pu.weapon_type
                self._pickups.remove(pu)

        # Scroll death (fell behind camera)
        if player.pos[0] < self._camera_x - 50 and player.invulnerable_frames == 0:
            self._lives -= 1
            self._combo.reset()
            player.reset()
            player.pos[0] = self._camera_x + 100
            if self._lives <= 0:
                self._game_over = True

        # Damage detection for combo reset
        if self._lives < self._last_lives:
            self._combo.reset()

        # === Signal calculation (reward) ===
        signal = 0.01
        signal += (self._score - self._last_score) * 0.1
        if self._lives < self._last_lives:
            signal -= 50.0
        if player.pos[0] - self._camera_x < 200:
            signal -= 0.1
        elif player.pos[0] - self._camera_x > 400:
            signal += 0.05

        self._last_score = self._score
        self._last_lives = self._lives

        # Build telemetry
        obs = _core.get_state(
            player, self._asteroids, self._enemies,
            self._projectiles, self._camera_x,
            combo=self._combo, star_fragments=self._star_fragments,
            salvage_pods=self._salvage_pods, score=self._score,
            lives=self._lives, scroll_speed=self._scroll_speed,
            boss_active=(self._current_boss is not None or self._centipede_boss is not None)
        )

        terminated = self._game_over
        truncated = self._tick >= self._max_drift

        # Handle pygame events to prevent OS hang (even in headless)
        if self._render or self._tick % 60 == 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminated = True

        return obs, signal, terminated, truncated, self._build_session_data()

    def _build_session_data(self):
        """Compile decoded session metrics."""
        return {
            'score': self._score,
            'lives': self._lives,
            'distance': self._camera_x,
            'ticks': self._tick,
            'combo_chain': self._combo.chain,
            'combo_multiplier': self._combo.multiplier,
            'boss_phase': ('resonance' if self._current_boss else
                          'centipede' if self._centipede_boss else 'drift'),
            'entity_count': (len(self._asteroids) + len(self._enemies) +
                           len(self._glitch_seekers)),
            'scroll_velocity': self._scroll_speed,
            'player_pos': list(self._player.pos),
            'shield_energy': self._player.shield_energy
        }

    def configure(self, params):
        """Update calibration parameters for the next session.

        Takes effect on the next reset() call.

        Args:
            params: Dict of calibration fields to update.
        """
        self._calibration.update(params)

    def close(self):
        """Terminate the simulation session and release resources."""
        pygame.quit()
        self._initialized = False

    @property
    def session_active(self):
        """Whether the current session is still running."""
        return not self._game_over and self._tick < self._max_drift


# Convenience: allow running this file directly to verify the interface
if __name__ == "__main__":
    print("NULL-VOID SIMULATION PROTOCOL — Interface Verification")
    print("=" * 55)

    session = NullVoidSession(calibration={'calibration_seed': 42})
    telemetry = session.reset(seed=42)
    print(f"Telemetry channels: {len(telemetry)}")
    print(f"Control channels:   {session.control_channels}")

    total_signal = 0.0
    steps = 0

    while session.session_active and steps < 1000:
        # Random navigation for verification
        controls = [
            random.random(),   # thrust
            random.random(),   # left
            random.random(),   # right
            random.random(),   # fire
            0.0                # shield
        ]
        telemetry, signal, terminated, truncated, data = session.step(controls)
        total_signal += signal
        steps += 1

        if terminated:
            break

    print(f"Session completed: {steps} ticks")
    print(f"Final score:       {data['score']}")
    print(f"Distance drifted:  {data['distance']:.1f}")
    print(f"Total signal:      {total_signal:.2f}")
    print(f"Telemetry shape:   {len(telemetry)} channels")
    print(f"Boss phase:        {data['boss_phase']}")
    print("Protocol verification: PASS")

    session.close()
