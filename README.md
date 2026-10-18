# D&D OmniCompanion 🐉🎲

> 🌐 **Language / Lingua**: 🇬🇧 **[English (README.md)](README.md)** | 🇮🇹 **[Italiano (README_IT.md)](README_IT.md)**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Ruleset: D&D 5e](https://img.shields.io/badge/ruleset-D%26D%205e-red.svg)](https://dnd.wizards.com/)
[![UI: ttkbootstrap](https://img.shields.io/badge/ui-ttkbootstrap-orange.svg)](https://ttkbootstrap.readthedocs.io/)
[![Multiplayer: TCP/UDP](https://img.shields.io/badge/networking-TCP%20%2B%20UDP-green.svg)]()
[![Tests: Passing](https://img.shields.io/badge/tests-100%25%20passing-brightgreen.svg)]()
[![Localization: EN / IT](https://img.shields.io/badge/i18n-English%20%7C%20Italiano-blueviolet.svg)]()
[![Units: Imperial / Metric](https://img.shields.io/badge/units-ft%2Fmi%20%7C%20m%2Fkm-informational.svg)]()

**D&D OmniCompanion** is an all-in-one Client-Server Virtual Tabletop (VTT) and Campaign Management Engine for **Dungeons & Dragons 5th Edition**, developed in Python. Designed for both in-person table sessions and remote online play, it combines automated D&D 5e rules mechanics, a high-performance multi-scale hex map canvas, real-time UDP voice streaming, and a comprehensive Dungeon Master suite.

---

## 📚 Documentation & Guides

| Document | 🇬🇧 English Version | 🇮🇹 Versione Italiana |
|---|---|---|
| **Main README** | [README.md](README.md) | [README_IT.md](README_IT.md) |
| **User Guide (How-To Manual)** | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | [docs/GUIDA_ALL_UTILIZZO.md](docs/GUIDA_ALL_UTILIZZO.md) |
| **Operational Guide & System Architecture** | [docs/OPERATIONAL_GUIDE.md](docs/OPERATIONAL_GUIDE.md) | [docs/GUIDA_OPERATIVA.md](docs/GUIDA_OPERATIVA.md) |
| **Custom Campaign / Homebrew Rules** | [manuals/Custom_Campaign_Rules.md](manuals/Custom_Campaign_Rules.md) | [manuals/Regole_Personalizzate_Campagna.md](manuals/Regole_Personalizzate_Campagna.md) |

---

## 🌟 Key Highlights

### 🗺️ Multi-Grid & Multi-Scale Virtual Tabletop (VTT)
* **Multi-Grid Geometries (Hexagonal, Square, Gridless)**:
  * **Hex Grid (`hex`)**: Classic tactical hex grid for wilderness and dungeons.
  * **Square Grid (`square`)**: Standard 5e dungeon battlemap grid using official **Chebyshev distance** (diagonal steps count as 5 ft / 1 cell).
  * **Gridless Mode (`none` / `gridless`)**: Freeform placement on illustrative battlemaps with exact Euclidean pixel distance.
  * **Live Grid Switcher (`📐 Grid: ...`)**: DM can switch grid geometry on the fly with 1 click.
* **Smooth Navigation & Modern HUDs**: Infinite canvas with cursor-centered mouse-wheel zoom, right/middle-click panning, a bottom-left **Glassmorphism HUD** for quick zoom/recentering, and a top-center **Initiative Ribbon HUD** during combat.
* **Multi-Scale Map System (DMG p. 14) & Scale-Aware Ruler (`[ 📏 ]`)**:
  * Supports 4 map scales switchable in real time by the DM (`📏 Scale`): **Combat** ($5\text{ ft} / 1.5\text{ m}$), **Exploration** ($1\text{ mi} / 1.5\text{ km}$, $\sim 20\text{ min/hex}$), **World** ($6\text{ mi} / 9\text{ km}$, $2\text{ h/hex}$), and **Custom Scale**.
  * The **Ruler (`[ 📏 ]`)** computes distances according to active scale, grid type, and measurement units with overland travel time estimations.
* **Dual Distance Unit System (`📏 Distance Units`)**: Instant runtime switching between **Imperial (`ft / mi`)** and **Metric (`m / km`)**, automatically converting character speed badges, movement bars, ruler readouts, and ranges.
* **Creature Token Sizes (Tiny to Gargantuan)**: Native visual radius scaling for the 6 official 5e size categories ($0.5\times$ to $3.5\times$) with quick right-click sizing.
* **DM Hidden Layer (GM Layer)**: Place ambushing monsters or secret tokens visible only to the DM (semi-transparent with dashed purple ring and `[GM]` badge). Filtered at the network protocol level (`GAME_STATE`, `PLAYER_JOINED`, `PLAYER_MOVE`) to guarantee zero client-side data leaks.
* **Dynamic Fog of War (FoW) & Manual Brush**: Automated token Line of Sight (LoS) exploration, shared party vision, customizable darkvision (`/vision`), and a **Manual FoW Brush** (radius 0–3) to reveal or shroud rooms in seconds.
* **Difficult Terrain & Hazardous Surfaces (D&D 5e)**: Full support for 5 terrain types (Mud, Ice, Briars, Rubble, Swamp) with step-by-step movement cost doubling along the path (`hex_linedraw`), prone movement penalty (+1), hazard checks on entry (DC 10 Dex save on Ice or fall Prone, 1d4 piercing damage on Briars), DM live brush tool (`[ 🪨 ]`), right-click menu, and Map Editor JSON serialization.
* **Atmospheric Weather Filters & Dynamic Darkness**:
  * 6 animated environmental filters: **Clear**, **Rain**, **Storm** (lightning bolts & rain), **Snow** (frost & snowflakes), **Fog** (volumetric mist banks), and **Darkness** (pitch black & vignette).
  * 24-hour day/night cycle (Day, Sunrise, Sunset, Night) with responsive HUD pill badge.
  * Live dynamic torchlight and lantern glow (`light_radius > 0`) that cuts through the darkness with a warm golden radius.
  * 1-click DM Darkness toggle `[ 🌑 ]` and chat shortcuts (`/darkness`, `/weather Darkness`).
* **Shared Tactical Whiteboard (`[ ✏️ ]` / `[ 🧹 ]`)**: Freehand sketching on the live map canvas broadcast to all players in real time with instant clearing.
* **Dynamic Lighting & Auras**: Live light halos (torches, lanterns) and magical aura rings.
* **AoE Spells & Templates (`[ 💥 ]`)**: Spheres, Cones ($60^\circ / 90^\circ$), Lines, and Magical Darkness Spheres with geometric grid previews and 1-click casting.
* **Animated Map Ping**: Middle-click (or `[ 📍 ]` tool) to drop an animated broadcast marker for all connected players.
* **Token Condition Badges**: Visual status indicators rendered directly on tokens (`💀` Dead, `💤` Unconscious, `🔻` Prono, `⚡` Paralyzed/Concentration, `🛡️` Dodge, `🤝` Help, `🤢` Poisoned, `👁️` Blinded, etc.).

### ⚔️ D&D 5e Combat Engine & Context-Aware Turn Economy
* **Context-Aware Turn Economy (Exploration vs. Combat)**:
  * **Out of Combat (`🧭 Exploration Mode - Free Movement`)**: Players move, attack, and cast spells freely without consuming or locking turn badges; the movement bar displays per-move speed.
  * **In Combat (`Turn Economy`)**: Strict server-synchronized tracking of **⚡ Action**, **✨ Bonus Action**, **🛡️ Reaction**, and **👟 Movement**, resetting automatically at the start of the combatant's turn and when combat starts or ends.
* **Critical Successes (`🌟 Natural 20`) & Critical Failures (`💀 Natural 1`)**:
  * **Attack Rolls**: `Natural 20` is an automatic hit that automatically doubles all damage dice; `Natural 1` is an automatic miss.
  * **Saving Throws, Ability/Skill Checks & `1d20` Rolls**: Gold/crimson chat banners and broadcast Toast notifications (`CRITICAL_ROLL_BROADCAST`) across all connected clients.
* **Dynamic Advantage, Disadvantage & Cover**: Automatically computed from conditions (Invisible, Prone in melee vs. ranged, Blinded, Paralyzed, Dodge, Help) and intervening obstacles (+2 AC for Half Cover).
* **Environmental Combat Modifiers (Weather & Difficult Terrain)**:
  * **Weather (DMG p. 109-110)**: Violent storms and dense fog impose Disadvantage on ranged attacks (> 1 hex); torrential rain and blizzards impose Disadvantage on long-range attacks.
  * **Difficult Terrain**: Attacking from unstable footing (Ice, Rubble, Swamp, Mud) imposes Disadvantage; striking targets entangled in Briars or trapped in Mud grants **Advantage**.
  * **Darkness & Darkvision Rules (PHB p. 194-195)**: Attacking from darkness with Darkvision (or attacking a torch-bearing enemy) grants **Advantage** (*Unseen Attacker*); attacking an unseen target imposes **Disadvantage**; mutual darkness cancels out both to a normal roll.
* **Automated Opportunity Attacks**: Detects when a combatant leaves hostile melee reach without having taken the *Disengage* action.
* **Automated Concentration Checks**: Taking damage while concentrating automatically prompts a Constitution saving throw ($\text{DC} = \max(10, \lfloor\text{Damage}/2\rfloor)$).
* **Death Saves & Instant Death**: Complete 0 HP handling (`Natural 20` = revive at 1 HP, `Natural 1` = 2 failures, 3 successes = Stabilized, 3 failures or excess damage $\ge \text{Max HP}$ = Instant Death).
* **Boss Mechanics**: Legendary Actions and Legendary Resistances with automatic round resets.

### 🧙‍♂️ Character Creation, Sheet & Progression
* **Baldur's Gate Styled Wizard**: Guided Level 1 creation and Level-Up wizard with automatic SRD 5e class features, Hit Dice, and spell slot progression.
* **Special Class Resources System**: Automatic population and tracking of Ki Points, Rage, Bardic Inspiration, Wild Shape, Channel Divinity, Action Surge, Second Wind, Sorcery Points, etc., with automated Short/Long Rest recovery.
* **Hero Summary Card & Interactive Character Sheet**:
  * Always-visible sidebar summary card with responsive HP bar, AC, converted Speed (`ft` or `m`), and Initiative.
  * Full tabbed sheet: **Combat**, **Stats & Skills** (with Proficiency & Expertise $2\times\text{PB}$), **Weapons & Attacks**, **Inventory & Encumbrance** ($\text{STR} \times 15\text{ lbs}$), **Spellbook & Spell Slots (1–9)** with **Spell Upcasting** modal, **Features & Journal**.
* **Character Sheet Export (Official D&D 5e PDF & JSON Data)**: Dedicated modal dialog to choose between **Official PDF** (prompts for the blank 3-page D&D 5e PDF template in input, generating a fully filled sheet ready for print or sharing) and **JSON** (full raw backup for campaign import/export).
* **Online Anti-Cheat & DM Approval**: Requesting currency (`🤝 Request Currency from DM`) or adding custom items requires DM authorization.
* **Peer-to-Peer Trading & Macro Hotbar**: Direct item/gold transfers between allies and a 10-slot customizable quick macro bar.

### 📜 Dungeon Master Operations Suite
* **Live DMG p. 82 Encounter Balancer**: Real-time evaluation of encounter difficulty (**Trivial**, **Easy**, **Medium**, **Hard**, **Deadly**) with monster count XP multipliers.
* **Campaigns, Scenes & Starter Pack Manager**: Prepare acts, scenes linked to maps/monsters for 1-click deployment, and configure starting equipment automatically granted to new PCs.
* **Session Log / Chronicle Export**: Export complete session logs (rolls, tactical actions, chat, whispers) to Markdown (`.md`) or HTML from `File -> Export Session Log`.
* **Procedural Generators & Handouts**: 5e Loot Generator, Quick NPC Generator, and parchment document/image handouts.
* **Offline PDF Rulebooks & Command Palette (`Ctrl+K`)**: Instant search across indexed official 5e PDF rulebooks, rules, monsters, spells, and map tokens.
* **Overland Travel, Calendar, Weather, Shops & Quests**: Marching order, travel roles, rations/water, forced march saves, interactive fantasy calendar, merchant shops, and quest logs.
* **Soundboard & Integrated UDP Voice Chat**: Low-latency voice streaming with Mute/Deafen controls (`[ 🎤 ]` / `[ 🎧 ]`) and synchronized audio soundboard.

### 🎲 Campaign Management Styles: DM Agency vs Automation (5e RAW)
The DM can adjust the automation level in real time from **Tools ➔ ⚙️ Campaign Management Style (Automations)...** or by clicking the status pill on the map header (`🎲 Table`, `⚖️ Hybrid`, `⚡ Full Auto`):
* **🎲 Traditional Tabletop (Pen & Paper / RAW DM Control)**: Authentic tabletop pen-and-paper experience. Critical sheet alterations never occur without DM oversight: direct and AoE damage require DM validation, door lockpicking leaves room for narrative consequences, movement does not enforce artificial walls, and concentration breakage or death/KO are adjudicated by the DM.
* **⚖️ Assisted Hybrid (Recommended for Fluid Sessions)**: The digital assistant handles complex 5e bookkeeping (resistances, covers, visibility, conditions, DCs), while providing the DM with 1-click floating action cards (`[Full]`, `[Half]`, `[Custom]`, `[Cancel]`) to effortlessly confirm or modulate damage.
* **⚡ Full Automation (Fast Tactical / CRPG Style)**: Direct instant HP deductions, doors unlock immediately upon passing DC, strict combat turn locking, and instantaneous reaction/save prompts.
* **Granular Coverage Across All Mechanics**:
  * **⚔️ Combat & Damage**: Direct attack damage, AoE spell/save damage, 2d20 advantage/disadvantage auto-calculation, reaction prompts (Opportunity Attacks, Shield spell), concentration constitution saves, and 0 HP / massive instant death handling.
  * **🗺️ Map & Movement**: Strict combat turn enforcement, speed limit & difficult terrain blocking, automatic door DC resolution, and dynamic Fog of War auto-exploration.
  * **⛺ Rest & Resources**: Instant rest recovery (HP, Hit Dice, Spell Slots) vs DM approval with random encounter checks.

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.9 or higher** (compatible up to Python 3.14)
* Install dependencies:
  ```bash
  pip install pillow ttkbootstrap requests sounddevice numpy
  ```

### Launching the Application
Run the unified launcher from the project root:
```bash
python main.py
```
From the startup launcher choose:
1. **Dungeon Master**: Starts the TCP server (`53911`) and UDP Voice server (`53912`) and opens the DM Dashboard (with campaign, campaign editor, or quick session).
2. **Player**:
   * **👤 Character Manager (Offline)**: Create, view, duplicate, delete and export character sheets (Official PDF / JSON backup) completely offline without needing a server connection.
   * **✨ Create Character (Wizard)**: Launch the Baldur's Gate 3 inspired step-by-step Level 1 character creation wizard directly.
   * **🛡️ Join Game**: Launches the Player VTT client to connect to the Dungeon Master's IP address.

---

## 🎮 Quick Controls & Shortcuts

### Map Canvas Controls
| Input / Tool | Action |
|---|---|
| **Right-Click / Middle-Click + Drag** | Pan the map viewport |
| **Mouse Wheel Up / Down** | Zoom in / out centered on cursor |
| **Left-Click on Hex / Drag Token** | Move active token along valid hex paths |
| **Middle-Click on Hex** (or `[ 📍 ]`) | Send animated **Ping** visible to all players |
| **`[ 📏 ]` Tool + Drag** | Measure distance in hexes, `ft`/`m` or `mi`/`km` + travel time |
| **`[ 💥 ]` Tool + Click** | Place Area of Effect template (Sphere, Cone, Line) |
| **`[ 👆 ]` Tool** | Select / Center camera on active token |
| **`Ctrl + K`** | Open **Quick Command Palette** (universal search & dice roller) |

### Chat Commands
| Command | Description | Example |
|---|---|---|
| `/roll <formula>` or `/r <formula>` | Roll dice with mathematical expressions | `/roll 1d20+5`, `/r 8d6+3` |
| `/w <name> <msg>` | Send private whisper to a player or DM | `/w Gildor Watch out for the trap` |
| `/whisper <name> <msg>` | Alias for private whisper | `/whisper DM I check the chest` |
| `/sussurra <name> <msg>` | Italian alias for private whisper | `/sussurra Elidor I've got you covered` |
| `/manuale <term>` or `/rule <term>` | Search indexed 5e PDF rulebooks | `/manuale fireball`, `/rule stealth` |
| `/tsmorte`, `/deathsave`, `/ds` | Roll a 5e Death Saving Throw | `/ds` |
| `/vision <name> <radius_hex>` | *(DM only)* Set token vision radius | `/vision Gildor 12` |

---

## 📁 Repository Structure

```text
DndOmniCompanion/
├── client/                         # Player VTT Client, Character Sheet UI & Voice Client
│   ├── client.py                   # Main Player GUI, HUDs, and Turn Economy
│   ├── character_manager_ui.py     # Standalone Offline Character Manager
│   ├── character_sheet_ui.py       # Interactive 5e Character Sheet
│   ├── character_manager.py        # Character persistence and serialization
│   ├── character_creation_wizard.py# Level 1 Character Creation Wizard
│   ├── progression_ui.py           # Level-Up Wizard & SRD integration
│   ├── pdf_sheet_generator.py      # Official 3-page 5e PDF character sheet generator
│   ├── login_ui.py                 # Character selection & server connection dialog
│   ├── manuals_ui.py               # Client-side rulebook & compendium browser
│   ├── network.py                  # Client TCP socket networking
│   └── voice_client.py             # UDP real-time voice streamer
├── server/                         # DM Server, 5e Rules Engine, DM GUI & Voice Host
│   ├── server.py                   # Multi-client TCP game server
│   ├── dm_gui.py                   # Main Dungeon Master dashboard
│   ├── commands.py                 # Central network packet dispatcher
│   ├── dm_dialogs.py               # DM dialogs (Handouts, Custom NPC, Sheet Viewer, Starter Kit)
│   ├── dm_generators.py            # Procedural 5e Loot & NPC generators
│   ├── campaign_editor_ui.py       # Campaign, Act, Scene & Encounter editor
│   ├── encounter_builder_ui.py     # Encounter builder & balancer UI
│   ├── map_editor.py               # Map Editor (walls, lights, traps, portals, scale)
│   ├── map_downloader.py           # Preset map downloader
│   ├── compendium_ui.py            # Compendium & SRD interface
│   ├── voice_server.py             # UDP voice broadcast server
│   └── rules/                      # Modular D&D 5e rules engine
│       ├── combat.py               # Initiative, attacks, criticals, cover, advantage, turn economy
│       ├── movement.py             # Hex movement, FoW, traps, teleports
│       ├── character.py            # Damage, temp HP, death saves, concentration, rests
│       ├── chat.py                 # Chat routing, dice rolls, 1d20 criticals, whispers, manual lookup
│       ├── inventory.py            # P2P trading, shops, currency, DM approval
│       ├── map_interaction.py      # Pings, ruler, AoE, doors, map interactions
│       └── audio.py                # Audio broadcast & soundboard management
├── common/                         # Shared protocols, hex math & i18n
│   ├── game_state.py               # Central GameState and Player models
│   ├── protocol.py                 # Network JSON packet builders
│   ├── network_utils.py            # Length-prefixed TCP socket framing
│   ├── hex_utils.py                # Cubic hex geometry, LoS, cones, lines, spheres
│   ├── dice.py                     # Dice roller & Nat 20 / Nat 1 detection
│   ├── i18n.py                     # Live IT/EN translations, Imperial/Metric units & map scales
│   ├── encounter_calc.py           # DMG p. 82 encounter difficulty calculator
│   ├── pdf_manuals_indexer.py      # Offline PDF rulebook indexer & search engine
│   ├── campaign.py                 # Campaign, scene & encounter data models
│   ├── starter_equipment.py        # Configurable campaign starter kit
│   └── theme.py                    # Dark Fantasy color palette and UI styles
├── components/                     # Shared Tkinter/ttkbootstrap custom widgets
│   ├── ui_components.py            # HexMapCanvas, HUDs, Ruler, ToolTip, Toast, Command Palette
│   ├── calendar_ui.py              # Fantasy calendar and dynamic weather
│   ├── quest_ui.py                 # Quest Log interface
│   └── shop_ui.py                  # Merchant & Shop interface
├── docs/                           # User and technical documentation (EN + IT)
│   ├── USER_GUIDE.md               # Complete User Guide (English)
│   ├── GUIDA_ALL_UTILIZZO.md       # Manuale completo all'utilizzo (Italiano)
│   ├── OPERATIONAL_GUIDE.md        # System & Operational Manual (English)
│   └── GUIDA_OPERATIVA.md          # Manuale operativo e architettura (Italiano)
├── main.py                         # Unified launcher (DM Host / Player Client)
└── simulate_game_session.py        # Full 53-phase automated end-to-end simulation
```

---

## 🧪 Automated Testing & Verification

```powershell
# 1. Feature Unit Tests (Multi-scale ruler, Nat20/Nat1 criticals, Turn Economy, ft/m units, Whispers, Death Saves)
$env:DND_MOCK_AUDIO="1"; python test_new_features.py

# 2. Full UI Smoke Tests across all 19 DM Server & Player Client screens
$env:DND_MOCK_AUDIO="1"; python test_ui_smoke.py --no-screens

# 3. Full 53-Phase End-to-End Multiplayer Simulation
$env:DND_MOCK_AUDIO="1"; python simulate_game_session.py

# 4. Campaign & Scene System Tests
$env:DND_MOCK_AUDIO="1"; python -m unittest test_campaign_system.py
```

---

## 📜 License & Acknowledgments

* Designed for the **Dungeons & Dragons 5th Edition (D&D 5e)** ruleset under the Open Game License (OGL) / System Reference Document 5.1 (SRD5).
* Built with [Python](https://www.python.org/), [ttkbootstrap](https://ttkbootstrap.readthedocs.io/), and [Pillow](https://python-pillow.org/).