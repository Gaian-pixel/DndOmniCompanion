# D&D OmniCompanion 🐉🎲

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Ruleset: D&D 5e](https://img.shields.io/badge/ruleset-D%26D%205e-red.svg)](https://dnd.wizards.com/)
[![UI: ttkbootstrap](https://img.shields.io/badge/ui-ttkbootstrap-orange.svg)](https://ttkbootstrap.readthedocs.io/)
[![Multiplayer: TCP/UDP](https://img.shields.io/badge/networking-TCP%20%2B%20UDP-green.svg)]()
[![Tests: 53/53 Passed](https://img.shields.io/badge/tests-53%2F53%20passed-brightgreen.svg)]()
[![Localization: EN / IT](https://img.shields.io/badge/i18n-English%20%7C%20Italiano-blueviolet.svg)]()

**D&D OmniCompanion** is an all-in-one Client-Server Virtual Tabletop (VTT) and Campaign Management Engine developed in Python. Designed for both in-person table sessions and remote online play, it bridges the gap between digital convenience and authentic tabletop roleplaying by providing automated D&D 5th Edition rules mechanics, a high-performance hex map canvas, real-time voice streaming, and an extensive DM suite.

📖 **For in-depth operational walkthroughs and system architecture, check the [Operational Guide & System Manual](docs/OPERATIONAL_GUIDE.md).**

---

## 🌟 Key Highlights

### 🗺️ Interactive Hex Virtual Tabletop (VTT)
* **Smooth Navigation**: Infinite canvas with responsive mouse-wheel zoom and middle/right-click panning.
* **Dynamic Fog of War (FoW) & Vision**: Token-based exploration with shared party vision and customizable darkvision radii (`/vision`).
* **True Line of Sight (LoS)**: Hex-based raycasting prevents X-ray vision through collision walls.
* **Dynamic Lighting**: Torches, lanterns, and magical halos cast live light rings that update in real-time as tokens move.
* **Dynamic Ruler Tool (`[ 📏 ]`)**: Measure ranges in hexes and feet ($5\text{ ft/hex}$) interactively on the canvas.
* **AoE Spells & Templates (`[ 💥 ]`)**: Place 5e spell templates (Spheres, Cones, Lines) with preview outlines and one-click casting.
* **Live Ping Marker**: Middle-click anywhere on the map to drop an animated broadcast ping for the entire party.
* **Token Condition Badges**: Visual status indicators rendered directly on tokens (`💀` Dead, `💤` Unconscious, `🔻` Prone, `⚡` Paralyzed, `🛡️` Dodge, `🤝` Help, `🤢` Poisoned, `👁️` Blinded, `🕯️` Concentration).

### ⚔️ 5e Combat & Rules Automation Engine
* **Initiative Tracker**: Sorts turns seamlessly, highlights active combatants with a gold aura, and posts non-blocking turn notifications.
* **Mass Monster Initiative**: The DM can roll initiative for all combat monsters with 1 click.
* **5e Action Economy**: Dedicated buttons for standard actions: **Attack**, **Cast Spell**, **Dash** (doubles speed), **Disengage** (prevents opportunity attacks), **Dodge** (grants attackers disadvantage), and **Help** (grants ally advantage).
* **Automated Opportunity Attacks**: Senses when a combatant exits hostile melee reach and prompts opportunity strikes.
* **Dynamic Advantage / Disadvantage**: Calculated automatically based on visibility, prone state (melee vs. ranged), paralysis, blindness, and dodge.
* **Cover Calculation**: Intervening obstacles or creatures grant $+2\text{ AC}$ (Half Cover) along the attack trajectory.
* **Concentration Checks**: Taking damage prompts an automated Constitution saving throw ($\text{DC} = \max(10, \lfloor\text{dmg}/2\rfloor)$).
* **Death Saves Automation**: Prompts death saving throws at 0 HP. Handles Natural 20 (revives at 1 HP), Natural 1 (2 failures), 3 successes (Stabilized), and 3 failures (Dead).
* **Boss Mechanics**: Legendary Resistances (3/day) and Legendary Actions with automatic round resets.

### 🧙‍♂️ Character Creation & Progression
* **Baldur's Gate Styled Wizard**: Guided Level 1 character creation and Level-Up progression.
* **SRD & API Integration**: Pulls class features, spell lists, and Hit Dice automatically from the 5e SRD.
* **Interactive Character Sheet**: Full management of ability scores, skills, saving throws, inventory with weight encumbrance ($\text{STR} \times 15\text{ lbs}$), spellbook slots (levels 1–9), and Hit Dice recovery.
* **Hotbar Quick Macros**: 10 customizable quick slots for 1-click rolls, attacks, and chat commands.
* **Peer-to-Peer Trading**: Real-time item and gold exchange between players.

### 📜 Dungeon Master Operations Suite
* **Live DMG p. 82 Encounter Balancer**: Real-time evaluation of encounter difficulty (**Trivial**, **Easy**, **Medium**, **Hard**, **Deadly**) with monster multiplier XP adjustments.
* **Document & Clue Handouts**: Broadcast letters, clues, and map fragments with an immersive parchment modal (`Strumenti -> Condividi Documento`).
* **Campaign & Scene Manager**: Pre-build scenes with linked maps and monsters for instantaneous deployment during sessions.
* **Offline PDF Rulebook & Monster Indexer**: Fast keyword and monster lookup directly from official 5e PDF rulebooks with page citations.
* **Overland Travel & Survival Engine**: Marching orders (Front, Middle, Rear), travel roles (Scout, Navigator, Forager), water/ration tracking, and forced march Constitution saving throws.
* **Party Loot Splitter**: Divides discovered gold pieces evenly across party members with 1 click.
* **Soundboard & Atmosphere**: Broadcast battle music, tavern ambiance, and sound effects to all players.

### 💬 Discord-Styled Chat & Real-Time Voice
* **Rich Markdown Chat**: Colored speaker names, timestamps, formatted dice results, and system broadcasts.
* **Private Whispers**: Encrypted in-character whispers (`/w <name> <message>`, `/whisper`, `/sussurra`).
* **Low-Latency Voice Chat**: UDP-based real-time voice streaming with mute and deafen toggles built right into the interface.

### 🌐 Live Bilingual Localization
* Instant runtime switching between **Italian** and **English** (`Lingua / Language`) without restarting the client or server.

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.9 or higher** (Python 3.9 – 3.14 supported)
* Install dependencies via `pip`:
  ```bash
  pip install pillow ttkbootstrap requests sounddevice numpy
  ```

### Launching the Application
Run the unified main launcher:
```bash
python main.py
```
A startup launcher will appear:
1. **Ospita Partita (Dungeon Master)**: Starts the TCP/UDP server on port `53911`/`53912` and opens the DM Dashboard.
2. **Unisciti alla Partita (Giocatore)**: Launches the Player VTT client to connect to the host's IP address.

---

## 🎮 Controls & Shortcuts

### Canvas Controls
| Input | Action |
|---|---|
| **Right-Click / Middle-Click + Drag** | Pan the map canvas |
| **Mouse Wheel Up / Down** | Zoom in / out centered on cursor |
| **Left-Click + Drag on Token** | Move active token along valid hex paths |
| **Middle-Click on Hex** | Drop visual Ping indicator for all players |
| **`[ 📏 ]` Button + Drag** | Measure distances in hexes and feet |
| **`[ 👆 ]` Button + Click** | Select and center on token / set target |
| **`[ 💥 ]` Button + Click** | Deploy AoE spell template |

### Chat Commands
| Command | Action | Example |
|---|---|---|
| `/roll <dice>` or `/r <dice>` | Roll dice with arithmetic expressions | `/roll 1d20+5`, `/r 8d6` |
| `/w <name> <msg>` | Send private whisper to DM or player | `/w Gildor Controlla la porta` |
| `/whisper <name> <msg>` | Alias for private whisper | `/whisper DM Cerco trappole` |
| `/sussurra <name> <msg>` | Italian alias for private whisper | `/sussurra Elidor Ho preparato Cura Ferite` |
| `/manuale <term>` | Search indexed 5e rulebooks | `/manuale fireball`, `/manuale stealth` |
| `/rule <term>` | Alias for rulebook search | `/rule grapple` |
| `/tsmorte`, `/deathsave`, `/ds` | Roll 5e Death Saving Throw | `/ds` |
| `/vision <name> <radius>` | *(DM only)* Set token vision radius | `/vision Gildor 12` |

---

## 📁 Repository Structure

```
DndOmniCompanion/
├── client/                     # Player VTT client, character sheet UI, voice client
│   ├── client.py               # Main player GUI & network loop
│   ├── character_sheet_ui.py   # Interactive 5e character sheet
│   ├── character_manager.py    # Character serialization and state
│   ├── progression_ui.py       # Baldur's Gate style Level-Up & Creation Wizard
│   ├── voice_client.py         # UDP real-time voice streamer
│   ├── trade_dialog.py         # Peer-to-peer item & gold trading
│   └── quest_dialog.py         # Quest log & shopkeeper interface
├── server/                     # DM Server, combat rules, GUI & voice host
│   ├── server.py               # TCP multi-client server
│   ├── dm_gui.py               # Dungeon Master dashboard
│   ├── voice_server.py         # UDP voice broadcast host
│   └── rules/                  # Modular 5e rules engines
│       ├── combat.py           # Combat flow, attacks, cover, advantage
│       ├── movement.py         # Hex movement, Fog of War, teleports
│       ├── character.py        # Damage, temp HP, death saves, rage
│       ├── chat.py             # Chat routing, dice rolls, whispers
│       ├── conditions.py       # 5e conditions and effects
│       └── hazards.py          # Traps and environmental dangers
├── common/                     # Shared protocols, math & utilities
│   ├── game_state.py           # Central GameState and entity data models
│   ├── protocol.py             # Network packet definitions
│   ├── network_utils.py        # Length-prefixed framing socket utilities
│   ├── hex_utils.py            # Cubic hex coordinates, LoS, AoE geometry
│   ├── encounter_calc.py       # DMG p. 82 encounter difficulty calculator
│   ├── manual_indexer.py       # PDF & rulebook indexer with fast cache
│   └── i18n.py                 # Live bilingual translation dictionary
├── components/                 # Custom Tkinter/ttkbootstrap UI widgets
│   └── ui_components.py        # HexMapCanvas, ToolTips, ToastNotifications
├── docs/                       # Detailed operational and developer guides
│   └── OPERATIONAL_GUIDE.md    # Comprehensive system manual
├── manuals/                    # PDF manuals & custom rule extensions
├── maps/                       # Map images and metadata (walls, lights, portals)
├── main.py                     # Unified launcher (DM Host vs Player Client)
└── simulate_game_session.py    # Full 53-phase automated multiplayer simulation
```

---

## 🧪 Testing & Verification

The project includes rigorous automated verification suites to ensure stability across networking, rules logic, and UI rendering:

```powershell
# 1. Full 53-Phase End-to-End Multiplayer Simulation
$env:DND_MOCK_AUDIO="1"; python simulate_game_session.py

# 2. Targeted Unit Tests (Ruler, Whispers, Death Saves, Handouts, AoE Math)
$env:DND_MOCK_AUDIO="1"; python -m unittest test_new_features.py

# 3. Campaign & Scene System + UI Smoke Tests
$env:DND_MOCK_AUDIO="1"; python -m unittest test_campaign_system.py test_ui_smoke.py
```

All 53 phases pass with **100% success rate (0 failures)**.

---

## 📜 License & Acknowledgments

* Designed for the **Dungeons & Dragons 5th Edition (D&D 5e)** ruleset under the Open Game License (OGL) / System Reference Document 5.1 (SRD5).
* Built with [Python](https://www.python.org/), [ttkbootstrap](https://ttkbootstrap.readthedocs.io/), and [Pillow](https://python-pillow.org/).