# VECTOR ASTEROIDS: THE NULL-VOID INCIDENT (1981)

## ATTRIBUTION

The legacy version of this game was designed and implemented by **Gemini CLI**, an interactive AI agent, based on direct requests from [GusFromSpace](https://github.com/GusFromSpace).

The current version has been extended and evolved by **GusFromSpace** with contributions from **Gemini CLI** and **Claude Code**.

## THE LORE: A SPECIFIC HISTORICAL ANOMALY
The year is 1981. In a small, windowless office in Schenectady, New York, a regional logistics manager named Gary 'The Geb' Gebhart discovered that the corporate microwave was leaking a specific frequency (approx. 434.2 MHz) every time someone heated a 'Meat-Lovers' pocket sandwich. Gary noticed that his nearby oscilloscope didn't just show waves; it showed *geometry*. He began to suspect that the meat-pockets were opening a sub-harmonic rift into what he called the 'Null-Void.' This game is a reconstructed simulation of Gary's frantic attempts to navigate that rift using a modified pocket calculator and a stolen radar array before the breakroom was eventually decommissioned by the EPA in early 1982.

## HOW TO PLAY
Navigate the Null-Void and destroy the Geometric Echoes (Asteroids).

### CONTROLS
*   **UP ARROW**: Forward Thrust (Inertia-based)
*   **LEFT/RIGHT ARROW**: Rotate ship
*   **SPACEBAR**: Pulse-Fire Projectiles
*   **DOWN ARROW (HOLD)**: Energy Shield (1980 Phoenix Tech)
    *   *Note: Inoperable while firing or claiming. Blocks collisions and repels echoes.*
*   **LEFT SHIFT (HOLD)**: Territory Claim (1981 Qix Protocol)
    *   *Strategy: Loop back to your start point to vaporize everything inside the zone.*
    *   *Danger: If an echo touches your unfinished trail, Gary loses a life.*
*   **C**: Activate queued power-up (Gradius Protocol)
*   **P / ESC**: Pause simulation
*   **F2**: Toggle CRT visual effects
*   **F3**: Toggle FPS diagnostic overlay
*   **F11**: Fullscreen mode
*   **R**: Restart the simulation (Game Over state)

### POWER-UP BAR (Gradius Protocol)
Collect purple Star-Fragments to advance the selection cursor. Press **C** to activate:

`SPEED UP → DOUBLE → OPTION → SHIELD`

### WEAPON PICKUPS
Collect **W** pickups to equip special weapons: `OMEGA`, `REAR`, `TRIPLE`.
Warning: hostile signals can siphon your weapon if they get close.

### COMBO SYSTEM
Chain kills within a 2-second window to build a score multiplier (up to 16x).
Multiplier resets on taking damage.

### SCORE MILESTONES
| Score | Event |
|-------|-------|
| 20,000 | First resonance event (boss) |
| 40,000 | Deep rift cascade (second boss) |

### REQUIREMENTS
*   Python 3.x
*   Pygame (`pip install pygame`)
*   NumPy (`pip install numpy`)

## RUN THE SIMULATION
```bash
python vector_game.py
```

---

## SIMULATION PROTOCOL INTERFACE

The original oscilloscope recordings from Gary's rig were partially recovered during the EPA cleanup. The telemetry data has been reconstructed into a programmatic interface, allowing automated signal analysis and navigation of archived rift sessions.

### Oscilloscope Tap

The simulation exposes module-level slots for external signal processors. Set these before calling `main()`:

```python
import vector_game

# Attach a signal processor for automated navigation
# Must implement: .step(telemetry) -> list[float x5]
vector_game._AUTOPILOT_CONTROLLER = your_processor

# Attach a session recorder to capture telemetry
# Signature: callable(telemetry, controls, signal_strength, terminated, session_data)
vector_game._SESSION_OBSERVER = your_recorder

# Override simulation calibration (all fields optional)
vector_game._SIMULATION_CONFIG = {
    'rift_density': 1.0,        # Geometric echo density multiplier
    'echo_aggression': 1.0,     # Hostile signal aggression multiplier
    'void_velocity': 1.0,       # Rift drift speed multiplier
    'harmonic_stability': 3,    # Initial harmonic integrity (lives)
    'resonance_threshold': 1.0, # Resonance event threshold multiplier
    'calibration_seed': 42,     # Void coordinates for deterministic sessions
}

vector_game.main()
```

### Null-Void Session API

For programmatic session management without the display interface:

```python
from null_void_sim import NullVoidSession

session = NullVoidSession(
    calibration={'rift_density': 1.5, 'echo_aggression': 2.0},
    render=False,       # Set True to display the simulation
    max_drift=18000     # Max ticks before session truncation (~5 min at 60fps)
)

# Initialize session with void coordinates
telemetry = session.reset(seed=42)
print(f"Telemetry channels: {session.observation_channels}")  # 75
print(f"Control channels: {session.control_channels}")        # 5

# Run session
while session.session_active:
    controls = [1.0, 0.0, 0.0, 0.5, 0.0]  # thrust, left, right, fire, shield
    telemetry, signal, terminated, truncated, data = session.step(controls)

print(f"Final score: {data['score']}")
session.close()
```

### Session Data Fields
```python
{
    'score': int,             # Current score
    'lives': int,             # Remaining lives
    'distance': float,        # Distance drifted through the rift
    'ticks': int,             # Elapsed simulation ticks
    'combo_chain': int,       # Current kill chain count
    'combo_multiplier': int,  # Active score multiplier (1-16)
    'boss_phase': str,        # 'drift' | 'resonance' | 'centipede'
    'entity_count': int,      # Total active entities
    'scroll_velocity': float, # Current rift drift speed
    'player_pos': list,       # [x, y] world coordinates
    'shield_energy': float,   # Remaining shield charge (0-100)
}
```

### Telemetry Format

The telemetry readout contains 75 normalized float channels:

| Channels | Description |
|----------|-------------|
| 0-6 | Ship state (position, velocity, angle, shield, reserved) |
| 7-31 | 5 nearest geometric echoes (distance, angle, relative velocity, size) |
| 32-46 | 3 nearest hostile signals (distance, angle, relative velocity, size) |
| 47-58 | 3 nearest enemy projectiles (distance, angle, relative velocity) |
| 59-60 | Reserved (legacy padding) |
| 61-74 | Extended harmonic analysis (combo, distance, boss phase, loadout, opportunities) |

*Note: Channels 0-60 maintain backward compatibility with the original 61-channel oscilloscope format.*

---

## LICENSE
GNU General Public License v3.0 — free to use, modify, and distribute. Any derivative works must remain open source under the same license.
