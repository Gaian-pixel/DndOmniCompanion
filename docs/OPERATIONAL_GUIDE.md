# D&D OmniCompanion — Operational Guide & System Manual

> 🌐 **Language / Lingua**: 🇬🇧 **[English (OPERATIONAL_GUIDE.md)](OPERATIONAL_GUIDE.md)** | 🇮🇹 **[Italiano (GUIDA_OPERATIVA.md)](GUIDA_OPERATIVA.md)**
> 📖 **Step-by-Step User Guide**: See also the **[Complete User Guide (USER_GUIDE.md)](USER_GUIDE.md)**.

Welcome to the comprehensive operational manual for **D&D OmniCompanion**, a complete Virtual Tabletop (VTT) and campaign companion engine built in Python for Dungeons & Dragons 5th Edition.

---

## Table of Contents
1. [Architecture & Network Model](#1-architecture--network-model)
2. [Prerequisites & Quick Start](#2-prerequisites--quick-start)
3. [User Interface & Layout Overview](#3-user-interface--layout-overview)
4. [Dungeon Master (DM) Operations](#4-dungeon-master-dm-operations)
   - [Map Management & Hex Grid](#map-management--hex-grid)
   - [Fog of War, Dynamic Lighting & Line of Sight](#fog-of-war-dynamic-lighting--line-of-sight)
   - [Traps, Hazards & Portals (Teleports)](#traps-hazards--portals-teleports)
   - [Combat Management & Live Encounter Balancer](#combat-management--live-encounter-balancer)
   - [Monster Bestiary & Offline PDF Indexer](#monster-bestiary--offline-pdf-indexer)
   - [Handouts & Clue Sharing](#handouts--clue-sharing)
   - [Campaigns, Scenes, Shops & Quests](#campaigns-scenes-shops--quests)
   - [Party Management & Loot Splitting](#party-management--loot-splitting)
   - [Audio Soundboard](#audio-soundboard)
5. [Player Operations](#5-player-operations)
   - [Character Creation & Progression Wizard](#character-creation--progression-wizard)
   - [Interactive Character Sheet](#interactive-character-sheet)
   - [Combat Actions & 5e Turn Flow](#combat-actions--5e-turn-flow)
   - [Death Saving Throws Automation](#death-saving-throws-automation)
   - [Inventory & Encumbrance Grid](#inventory--encumbrance-grid)
   - [Spellbook & Spell Slot Management](#spellbook--spell-slot-management)
   - [Peer-to-Peer Player Trading](#peer-to-peer-player-trading)
   - [Hotbar Quick Macros](#hotbar-quick-macros)
   - [Travel System & Marching Order](#travel-system--marching-order)
6. [5e Mechanics & Automation Engine](#6-5e-mechanics--automation-engine)
   - [Advantage & Disadvantage Computation](#advantage--disadvantage-computation)
   - [Dynamic Cover System](#dynamic-cover-system)
   - [Opportunity Attacks](#opportunity-attacks)
   - [Concentration Checks](#concentration-checks)
   - [Damage Absorption, Resistances & Rage](#damage-absorption-resistances--rage)
   - [Resting & Hit Dice](#resting--hit-dice)
7. [Communication & Voice Chat](#7-communication--voice-chat)
   - [Discord-Styled Rich Chat](#discord-styled-rich-chat)
   - [Private Whispers](#private-whispers)
   - [Integrated UDP Voice Chat](#integrated-udp-voice-chat)
8. [Chat Commands & Hotkeys Reference](#8-chat-commands--hotkeys-reference)
9. [Bilingual Internationalization (IT / EN) & Distance Units (ft / m)](#9-bilingual-internationalization-it--en--distance-units-ft--m)
10. [Testing Suite & Quality Assurance](#10-testing-suite--quality-assurance)

> 🇮🇹 **Guida in Italiano**: Consulta anche la **[Guida Completa all'Utilizzo (Italiano)](GUIDA_ALL_UTILIZZO.md)**.

---

## 1. Architecture & Network Model

D&D OmniCompanion is structured around an asynchronous Client-Server architecture combining reliable TCP state management with low-latency UDP voice streaming.

```mermaid
flowchart TD
    subgraph Server["Server (DM Host)"]
        DM_GUI["DM GUI (dm_gui.py)"]
        S_Core["Game Server (server.py)"]
        S_Rules["Rules Engine (server/rules/*.py)"]
        S_Voice["Voice Server (voice_server.py: UDP 53912)"]
        S_State["GameState (common/game_state.py)"]
        S_PDF["PDF Manual Indexer (common/pdf_manuals_indexer.py)"]
    end

    subgraph Client1["Player Client 1"]
        C1_GUI["Player GUI (client.py)"]
        C1_Char["Character Manager & Sheet"]
        C1_Voice["Voice Client (voice_client.py)"]
    end

    subgraph Client2["Player Client 2"]
        C2_GUI["Player GUI (client.py)"]
        C2_Char["Character Manager & Sheet"]
        C2_Voice["Voice Client (voice_client.py)"]
    end

    S_Core <-->|TCP: Length-Prefixed JSON Packets| C1_GUI
    S_Core <-->|TCP: Length-Prefixed JSON Packets| C2_GUI
    S_Voice <-->|UDP: Raw PCM Audio Packets| C1_Voice
    S_Voice <-->|UDP: Raw PCM Audio Packets| C2_Voice
    DM_GUI --> S_Core
    S_Core --> S_Rules
    S_Rules --> S_State
```

### Core Subsystems
* **`common/network_utils.py` & `common/protocol.py`**: Custom binary-length-prefixed framing over TCP socket streams, ensuring zero JSON chunk fragmentation regardless of network latency or payload size. Includes **GM Layer Protocol Filtering** (the server automatically excludes tokens with `layer == "gm"` when broadcasting `GAME_STATE`, `PLAYER_JOINED`, and `PLAYER_MOVE` to regular player sockets) and whiteboard protocol messages (`CLEAR_DRAWINGS_REQUEST`, `CLEAR_DRAWINGS_BROADCAST`).
* **`common/hex_utils.py`**: Mathematical engine for geometric grids:
  * Cubic coordinate system ($q, r, s$ where $q + r + s = 0$) with `HexLayout` for hexagonal maps, line of sight (LoS) raycasting, cone projections ($60^\circ / 90^\circ$), spheres, and straight-line AoEs.
  * `SquareLayout` for chess/square dungeon battlemaps and pixel $\leftrightarrow$ cell conversion.
  * Polymorphic `grid_distance(a, b, grid_type)` function supporting Chebyshev distance (standard 5e rule where diagonals cost 5 ft / 1 cell), cubic hex distance, and Euclidean distance for gridless maps (`none`/`gridless`).
* **`server/rules/`**: Decoupled 5e rule modules isolating combat (`combat.py`), movement (`movement.py`), character damage/death (`character.py`), chat commands (`chat.py`), inventory/trading (`inventory.py`), map & whiteboard interactions (`map_interaction.py`), and audio (`audio.py`).
* **`common/i18n.py`**: Real-time bilingual translation dictionary (`IT`/`EN`), Imperial/Metric unit conversion (`ft`/`mi` $\leftrightarrow$ `m`/`km`), localization of token sizes, GM layer, whiteboard tools, and multi-scale map distance/travel-time calculation.

---

## 2. Prerequisites & Quick Start

### Requirements
* **Python 3.9+** (tested and verified up to Python 3.14).
* Core dependencies:
  ```bash
  pip install pillow ttkbootstrap requests sounddevice numpy
  ```
  *(Note: `sounddevice` and `numpy` are used for real-time voice streaming. In headless test environments or systems without PortAudio, the environment variable `DND_MOCK_AUDIO=1` is automatically honored).*

### Launching the Application
Execute the unified launcher from the project root:
```bash
python main.py
```
A role selector modal appears:
1. **Dungeon Master**: Launches the DM Host server on default port `53911` (TCP) and `53912` (UDP) and opens the DM workspace (with Campaign, Campaign Editor, or Quick Session).
2. **Player**: Launches the Player VTT client, allowing character selection/creation and server connection via IP/hostname.

---

## 3. User Interface & Layout Overview

Both the DM and Player interfaces are built with **ttkbootstrap** in modern dark fantasy styling, organized into a 3-column layout inspired by modern VTTs and Discord:

| Column | Component | Purpose |
|---|---|---|
| **Left Toolbar** | Compact Icon Strip | Context-sensitive map tools (`👆` Select/Center, `📏` Scale-Aware Ruler, `💥` Area of Effect, `📍` Ping, `📖` Rulebooks, `🚪` Teleport, `☁️` Fog of War) with tooltips. |
| **Center Viewport** | `HexMapCanvas` | Infinite zoom & pan interactive hex canvas with top-center **Initiative Ribbon HUD** during combat, bottom-left **Glassmorphism Zoom/Center HUD**, dynamic Fog of War, lighting halos, auras, tokens, condition badges, walls, and ruler vectors. |
| **Right Sidebar** | Tabbed Notebook | Tabs for Chat / Dice Log, Voice Controls, Hero Summary Card & Action Economy, Party & NPC Tracker, World & Calendar, Bestiary, and Audio/SFX. |

* **Quick Command Palette (`Ctrl+K`)**: Press `Ctrl+K` at any time to search 5e rules, monsters, spells, map tokens, or execute instant `/roll` commands.

---

## 4. Dungeon Master (DM) Operations

### Map Management, Multi-Grid & Scale-Aware Ruler
* **Loading Maps**: Navigate to `File -> Load Map`. Supported formats: `.png`, `.jpg`, `.jpeg`, `.json`.
* **Multi-Grid Geometry Engine (Hex, Square, Gridless)**:
  * **Hexagonal Grid (`hex`)**: cubic coordinate math with flat-topped and pointy-topped layouts.
  * **Square Grid (`square`)**: matrix layout using official D&D 5e **Chebyshev distance** (diagonal steps cost a standard 5 ft / 1 cell).
  * **Gridless Mode (`none` / `gridless`)**: suppresses on-screen grid lines for pictorial artwork; tokens move freely calculating true Euclidean distance.
  * **Live Grid Switcher (`📐 Grid: ...`)**: top status bar button allowing the DM to switch the active map's grid type live during session.
* **Multi-Scale Map Engine (DMG p. 14)**:
  * **Combat Scale** (`hex_size=30` or `60`): $1\text{ hex} = 5\text{ ft}$ ($1.5\text{ m}$).
  * **Exploration / Province Scale** (`hex_size=35`): $1\text{ hex} = 1\text{ mi}$ ($1.5\text{ km}$, $\sim 20\text{ min}$ marching/hex).
  * **World / Kingdom Scale** (`hex_size=15`): $1\text{ hex} = 6\text{ mi}$ ($9\text{ km}$, $2\text{ hours}$ marching/hex; $4\text{ hexes} = 1\text{ day}$).
  * **Custom Scale**: Any custom distance value and unit (`ft`, `m`, `mi`, `km`) per hex.
  * **Quick Scale Switcher (`📏 Scale`)**: Click the scale pill in the DM top bar to switch the active map's scale on the fly and broadcast it live to all connected players.
* **Map Editor**: Choose `Tools -> Map Editor` to configure grid radius, grid geometry type (`grid_type`), offset, scale, static walls, traps, portals, and lights.

### Fog of War, Manual Brush, Dynamic Lighting & Line of Sight
* **Dynamic Fog of War (FoW)**: The canvas automatically conceals unexplored cells for players.
* **Manual FoW Brush (`Radius: 0, 1, 2, 3`)**: In the FoW control bar (`[ ☁️ ]`), the DM can select a brush radius and left-click (reveal) or right-click (hide) to paint or restore fog across contiguous circular areas.
* **Shared Party Vision**: As any party token moves, cells within its vision radius are revealed.
* **Dynamic Lighting**: Tokens carrying light sources (e.g., Torches: 20 ft bright / 20 ft dim; Lanterns: 30 ft bright / 30 ft dim) illuminate dynamically in real time.
* **Darkness Filter (`[ 🌑 ]`) & Magical Darkness**:
  * 1-Click toolbar toggle (`[ 🌑 ]`) or `/darkness` / `/oscurita` chat command: immerses the entire map in total pitch-black darkness (`#000000`).
  * Dynamic visibility rules: cells not lit by active torches/lanterns or uncovered by Darkvision appear pitch black.
  * Magical Darkness Spheres: placeable via right-click $\rightarrow$ `🌑 Piazza Sfera di Oscurità Magica (R=3)`. Non-magical Darkvision cannot see through magical darkness (PHB p. 194-195).
* **True Line of Sight (LoS)**: Geometric raycasting evaluates line-of-sight against walls (`wall_hexes`). Tokens behind impenetrable walls cannot be seen through FoW.

### Creature Token Sizes & DM Hidden Layer (GM Layer)
* **Official 5e Creature Token Sizes**: Full support for the 6 standard categories (**Tiny**, **Small**, **Medium**, **Large**, **Huge**, **Gargantuan**), with visual canvas radius scaling from $0.5\times$ to $3.5\times$. Configurable via right-click $\rightarrow$ `Creature Size`.
* **DM Hidden Layer (GM Layer)**:
  * Conceals monster or trap tokens from player clients.
  * DM Rendering: token renders semi-transparently with a dashed purple ring and a `[GM]` badge.
  * Network Security Filter: at the TCP protocol layer (`network_utils.py` and `game_state.py`), `GAME_STATE`, `PLAYER_JOINED`, and `PLAYER_MOVE` packets systematically filter out `layer == "gm"` tokens for non-DM sockets, eliminating metagame data leaks.
  * Toggle via right-click on token $\rightarrow$ `👁️ GM Layer`.

### Traps, Difficult Terrain, Hazards & Portals (Teleports)
* **Traps**: When a token enters a trap hex, the server:
  1. Checks Passive Perception against the trap's Detection DC.
  2. If triggered, rolls damage and prompts the player for a Dexterity Saving Throw.
  3. Reveals the trap visually on the map with an alert in chat.
* **Difficult Terrain & Hazardous Surfaces**:
  * 5 distinct terrain types with unique textures and color schemes: **Mud** (`mud`), **Slippery Ice** (`ice`), **Briars** (`briars`), **Rubble** (`rubble`), **Deep Swamp** (`swamp`).
  * **Movement Penalties**: Pathfinding (`hex_linedraw`) applies double movement cost ($\times 2$, stacks with the `Prono` / Prone condition).
  * **Entry Hazards**: Stepping onto Ice requires a DC 10 Dexterity saving throw or fall Prone; stepping into Briars deals $1d4$ piercing damage automatically with an alert in chat.
  * **On-the-Fly Painting & DM Tools**: DM can apply terrain via right-click on hex $\rightarrow$ `🌾 Terreno Difficile...` or using the `[ 🪨 ]` brush popup on the left toolbar (radius 0, 1, 2 with terrain type selector).
* **Portals & Teleports**: Clicking `[ 🚪 ]` on the DM toolbar allows binding an hex coordinate (e.g., `5,5`) to a destination map file (e.g., `dungeon_level2.json`). When a token steps on the hex, the server automatically transitions the party to the new map.

### Combat Management & Live Encounter Balancer
1. **Starting Combat**: Select targets or click **Inizia Combattimento** (Start Combat) in the `Iniziativa & PG` tab.
2. **Mass NPC Initiative**: The DM can click **Tira Iniziativa Mostri** to instantly roll initiative for all monsters in the encounter simultaneously with Dexterity modifiers applied.
3. **Turn Cycling**: Use **Prossimo Turno** (Next Turn) or **Precedente** to advance the initiative order. The active token is highlighted with a gold ring on the map, and a non-blocking toast notification announces their turn.
4. **Live Encounter Difficulty Calculator (DMG p. 82)**:
   * The DM panel dynamically tallies total player levels and monster challenge ratings (CR).
   * Calculates adjusted encounter XP using 5e monster count multipliers (from $1.5\times$ to $4\times$).
   * Displays real-time difficulty: **Banale (Trivial)**, **Facile (Easy)**, **Medio (Medium)**, **Difficile (Hard)**, or **Mortale (Deadly)**.
5. **Boss Mechanics & Legendary Actions**:
   * **Legendary Resistances**: Monsters with legendary resistance (e.g., 3/day) can turn a failed saving throw into a success with 1 click.
   * **Legendary Actions**: Spend legendary action points outside the boss's turn, resetting automatically at the start of each round.

### Monster Bestiary & Offline PDF Indexer
* **Online SRD Bestiary**: Search monsters by name via Open5e/D&D 5e API.
* **Offline PDF Indexer**: Click **Cerca in PDF** to search offline directly inside official rulebook PDFs (Monster Manual, Player's Handbook, Dungeon Master's Guide) cached in `manuals/pdf_index_cache.json`.
* **One-Click Spawn**: Click **Spawna sulla Mappa** to instantly place the monster token at the last clicked hex with complete HP, AC, speed, actions, and initiative stats.

### Handouts & Clue Sharing
* Open `Strumenti -> Condividi Documento (Handout)`.
* Enter a title and text (e.g., ancient letter, cipher, map fragment).
* Broadcasts immediately to all connected clients, popping up an authentic dark fantasy parchment modal dialog.

### Campaigns, Scenes, Shops & Quests
* **Campaign & Scene Manager**: Prepare encounters in advance as "Scenes" linked to specific maps and tokens. Switch scenes seamlessly during live play without manual re-placement.
* **Shop & Economy System**: Open merchant stores where players can browse goods, check inventory weight, and purchase gear deducted directly from their gold pieces.
* **Quest Log**: Track Active, Completed, and Failed quests with milestone rewards.

### Party Management & Loot Splitting
* **Party vs NPC Separation**: In out-of-combat mode, the DM listbox separates players into `--- PARTY ---` and `--- NPC ---`. Right-click any entity to toggle party status.
* **Loot Splitter**: Click **Dividi Denaro** and enter an amount of Gold Pieces (GP). The server divides the gold evenly among all active party members and updates their character sheets automatically.

### Audio Soundboard
* The `Audio/Sfx` tab provides instant atmospheric soundscape broadcast buttons (e.g., Tavern, Battle, Dungeon Ambience) played synchronously on client browsers/media players.

### Shared Tactical Whiteboard & Session Log Export
* **Tactical Whiteboard (`[ ✏️ ]` / `[ 🗑️ ]`)**: real-time freehand sketching broadcast live to all clients. Instant clear button with TCP broadcast.
* **Session Log Export (`File -> 📜 Export Session Log...`)**: export the entire session transcript (dice rolls, combat events, chat, whispers) into formatted Markdown (`.md`) or HTML.

---

## 5. Player Operations

### Character Creation & Progression Wizard
* Accessible via `Libreria -> Creazione Personaggio` or the Level-Up button.
* **Baldur's Gate Styled UI**: Step-by-step guidance for class, race, ability scores (Standard Array, Point Buy, or Custom Rolls), starting gear, and background features.
* **Level-Up Wizard**:
  * Calculates HP gain (Hit Die roll or fixed average).
  * Automatically fetches class features from the 5e SRD for the new level.
  * Handles Ability Score Improvements (ASI) or Feats.
  * Unlocks new spell slots.

### Interactive Character Sheet
Organized in clean tabs:
* **Combat Tab**: Current/Max HP, Temp HP, Armor Class, Speed, Initiative bonus, Active Conditions with visual status badges, Death Saves, Hit Dice tracker.
* **Stats & Skills Tab**: Six core ability scores, saving throw proficiencies, passive perception, and all 18 skill proficiencies with automatic modifier computation.
* **Inventory Tab**: Grid-based inventory with item weights, quantity, attuned items, and total weight vs carrying capacity ($\text{STR} \times 15\text{ lbs}$).
* **Spellbook Tab**: Level 1 to 9 spell slots with current/max counters, spell search, modal **Spell Upcasting**, and 1-click casting with automatic slot deduction.
* **Features & Traits**: Racial traits, class privileges, **Special Class Resources** tracker, feats, and custom notes.

### Special Class Resources System
* **Class Automation**: When creating a character or leveling up, standard 5e class resources are automatically populated (e.g., *Ki Points*, *Rage*, *Bardic Inspiration*, *Wild Shape*, *Channel Divinity*, *Action Surge*, *Second Wind*, *Sorcery Points*, *Lay on Hands*).
* **Interactive Adjusters**: Quick `[-]` / `[+]` counter buttons to expend or replenish charges live during play.
* **Custom Resources**: Add custom resource pools with Name, Max Value, and Recovery Rule (*Short Rest* vs *Long Rest*).
* **Automated Rest Recovery**: Triggering a Short Rest or Long Rest automatically resets only the resources configured for that rest duration.

### Combat Actions & Context-Aware 5e Turn Economy
The Player Action Economy panel automatically adapts to whether combat is active:
* **Out of Combat (`🧭 Exploration Mode - Free Movement`)**:
  * Action badges (`⚡ Action`, `✨ Bonus`, `🛡️ Reaction`) remain in `Free (Exploration)` mode and are never locked when moving, attacking, or casting spells outside combat.
  * The movement bar displays the character's per-move speed (`👟 Speed: 30 ft / 9 m (Free)`).
* **During Combat (`Turn Economy`)**:
  1. **Turn Notification**: Visual banner, **Initiative Ribbon HUD** arrow `▼`, and toast appear ("È IL TUO TURNO!"). All turn economy resources reset automatically via `TURN_ECONOMY_UPDATE`.
  2. **Move**: Click on the destination hex (movement path is validated against remaining speed; Prone condition doubles movement cost).
  3. **Action Menu**: Click `Azione` to choose standard 5e actions:
     * **Attacco (Attack)**: Select weapon, pick target on map with 1 click (consumes `⚡ Action`).
     * **Lancia Incantesimo (Cast Spell / AoE)**: Open AoE tool, select template (Sphere, Cone, Line), choose radius/length, and place on hex grid.
     * **Scatto (Dash)**: Doubles current speed for the turn (consumes `⚡ Action`).
     * **Disimpegno (Disengage)**: Prevents triggering opportunity attacks during movement.
     * **Schivata (Dodge)**: Gives attackers disadvantage until the start of your next turn.
     * **Aiuto (Help)**: Gives an ally advantage on their next attack roll against a nearby enemy.
  4. **End Turn**: Click `Termina Turno` to pass initiative to the next combatant.

### Death Saving Throws Automation
* If you start your turn at **0 HP**:
  * A Death Save prompt opens automatically. You can also roll with `/tsmorte`, `/deathsave`, or `/ds`.
  * **Natural 20**: Regain 1 HP immediately, stand up, and clear the `Incosciente` (Unconscious) condition.
  * **Roll $\ge 10$**: +1 Success (at 3 successes, you gain the `Stabilizzato` condition).
  * **Roll $< 10$**: +1 Failure.
  * **Natural 1**: Counts as **2 Failures** (at 3 failures, you gain the `Morto` condition).
* **Taking Damage at 0 HP**: Automatically marks a failure (or 2 if a critical hit). Excessive damage exceeding your Max HP causes instant death.

### Inventory & Encumbrance Grid
* Real-time weight tracking:
  $$\text{Carrying Capacity} = \text{Strength} \times 15\text{ lbs}$$
* If total inventory weight exceeds carrying capacity, the weight counter turns red with an **Ingombrato (Encumbered)** warning.
* **Online DM Approval**: During live connected sessions, adding custom items or requesting gold (`🤝 Request Currency from DM`) sends an approval prompt to the DM (`CURRENCY_REQUEST` / `ITEM_APPROVAL_REQUEST`).

### Spellbook, Slot Management & Spell Upcasting
* Add spells using the built-in SRD browser.
* **Automatic Upcasting**: Clicking **Cast** on a 1st+ level spell opens a modal selector displaying all available slots up to 9th level. Choosing a higher-level slot consumes that slot and broadcasts the cast announcement with both base and upcast levels.
* **Long Rest** restores all spell slots to maximum.

### Character Sheet Export (Official PDF & JSON)
* Click **`📥 Esporta Scheda...`** at the bottom of the character sheet:
  * **Official PDF**: Prompts you to select your blank PDF template (e.g., `dnd_blankcharactersheet_it.pdf`) and compiles the official 3-page sheet with complete stats, skill proficiency dots, hit dice, weapons, currency, inventory, notes, and full spellbook. Ready for printing and archival.
  * **JSON**: Raw structured data for backup, editing, and campaign migration.

### Peer-to-Peer Player Trading
* Open player trade via the context menu or inventory tab.
* Select items and gold to offer to an ally.

### Hotbar Quick Macros
* 10 customizable quick slots at the bottom of the player panel.
* **Right-Click Slot**: Configure macro command (e.g., `/roll 1d20+5 Spada Lunga`, `/ds`, `/tsmorte`).
* **Left-Click Slot**: Instantly executes the macro in chat.

### Travel System & Marching Order
* Set party marching order: **Avanguardia (Front)**, **Centro (Middle)**, **Retroguardia (Rear)**.
* Assign travel roles: Navigator, Scout, Forager.
* Ration and water tracking with automated starvation/exhaustion penalties.
* Forced March calculation with progressive Constitution saving throw DCs ($10 + 1\text{ per hour past 8}$).

---

## 6. 5e Mechanics & Automation Engine

### Critical Successes (Natural 20) & Critical Failures (Natural 1)
The dice engine (`roll_dice_detailed`) inspects all `d20` rolls (including Advantage `2d20kh1` and Disadvantage `2d20kl1`):
* **Attack Rolls**:
  * **Natural 20 (`🌟 CRITICO NATURALE 20!`)**: Automatic hit regardless of target AC, automatically doubling all damage dice while adding flat modifiers once.
  * **Natural 1 (`💀 FALLIMENTO CRITICO!`)**: Automatic miss regardless of attack bonus.
* **Saving Throws, Skill Checks & Generic `1d20` Rolls**:
  * Highlights `🌟 20 NATURALE!` (gold) and `💀 1 NATURALE!` (crimson) in the chat log and dispatches a `CRITICAL_ROLL_BROADCAST` toast notification to all connected clients.

### Advantage & Disadvantage Computation
The combat engine calculates advantage and disadvantage dynamically based on token states, environmental hazards, and lighting:
* **Attacker gains Advantage if**:
  * Attacker is `Invisibile`.
  * Target is `Trattenuto`, `Paralizzato`, `Incosciente`, `Accecato`, or `Pietrificato`.
  * Target is `Prono` AND attack is melee (distance $\le 1$ hex).
  * Target is trapped in hazardous or restrictive terrain (**Briars** or **Deep Mud**).
  * Attacker is concealed in darkness and can see the target (via **Darkvision** or target carrying an **active light source** such as a Torch/Lantern), while target cannot see attacker.
* **Attacker suffers Disadvantage if**:
  * Attacker is `Accecato`, `Avvelenato`, `Trattenuto`, or `Prono`.
  * Target is `Prono` AND attack is ranged (distance $> 1$ hex).
  * Target is `Invisibile`.
  * Target took the `Schivata` (Dodge) action.
  * Attacker is standing on an unstable or slippery surface (**Ice**, **Swamp**, **Rubble**).
  * **Pitch-Black Darkness**: Attacker cannot see the target in darkness.
  * **Dynamic Weather Modifiers**:
    * **Storm** or **Dense Fog**: Disadvantage on all ranged attacks beyond 1 hex due to heavy rain, howling winds, and zero visibility.
    * **Heavy Rain**: Disadvantage on long-range attacks at distance $\ge 4$ hexes.
    * **Blizzard / Snow**: Disadvantage on long-range attacks at distance $\ge 3$ hexes.
* **Magical Darkness**: Standard Darkvision cannot penetrate magical darkness; anyone inside or attacking into magical darkness is blinded (PHB p. 194-195).
* **Mutual Cancellation**: Having both advantage and disadvantage (including mutual blindness in pitch-black darkness between creatures without darkvision) cancels out to a normal roll as per 5e rules, with full transparent reasoning recorded in the combat log.

### Dynamic Cover System
* If another creature or obstacle lies directly on the hex ray between the attacker and target, the target gains **Mezza Copertura (+2 CA)** automatically.

### Opportunity Attacks
* When a token moves out of an adjacent enemy's melee reach (1 hex) without having used the **Disengage** action, the server detects an opportunity attack opening and alerts the DM/attacker.

### Concentration Checks
* When a creature with the `Concentrazione` condition takes damage, the server automatically prompts a Constitution Saving Throw:
  $$\text{DC} = \max(10, \lfloor\text{Damage} / 2\rfloor)$$
* On failure, `Concentrazione` is automatically removed and announced in chat.

### Damage Absorption, Resistances & Rage
* **Temporary Hit Points (Temp HP)**: Absorbs damage first before real HP is decreased.
* **Damage Types & Resistances**: Damage reduction (half) or immunity (zero) is automatically calculated if resistance or immunity tags match the damage type.
* **Barbarian Rage**: Resistance to bludgeoning, piercing, and slashing damage is applied when in Rage.

### Resting & Hit Dice
* **Short Rest**: Spend available Hit Dice to regain HP ($\text{Die Roll} + \text{CON mod}$ per die); resets short-rest class features (e.g., Action Surge, Ki points, Warlock slots).
* **Long Rest**: Restores full HP, regains half of total Hit Dice, clears 1 level of exhaustion, and restores all spell slots.

---

## 7. Communication & Voice Chat

### Discord-Styled Rich Chat
* Formatted message view with timestamps, distinct color tags for DM announcements, combat logs, damage rolls, critical rolls, and player messages.
* Native rich markdown rendering with collapsible dice results.

### Private Whispers
* Use `/w <CharacterName> <Message>` (or `/whisper`, `/sussurra`).
* Whispers are routed strictly between the sender and the recipient with a `[🔒 Sussurro]` prefix.

### Integrated UDP Voice Chat
* High-performance, low-latency audio transmission directly inside the VTT without external third-party software.
* Microphone mute (`[ 🎤 ]`) and audio deafen (`[ 🎧 ]`) controls directly on the chat bar.
* Safe fallback in environments without physical audio hardware.

---

## 8. Chat Commands & Hotkeys Reference

### Chat Commands

| Command | Description | Example |
|---|---|---|
| `/roll <expr>` or `/r <expr>` | Rolls dice with arithmetic | `/roll 2d6+4`, `/r 1d20+7` |
| `/w <name> <msg>` | Sends private whisper | `/w Gildor Guarda dietro di te` |
| `/whisper <name> <msg>` | Alias for private whisper | `/whisper DM Ho trovato la chiave` |
| `/sussurra <name> <msg>` | Italian alias for whisper | `/sussurra Elidor Ho 3 slot rimasti` |
| `/manuale <termine>` | Quick lookup in indexed 5e rulebooks | `/manuale fireball`, `/manuale stealth` |
| `/rule <termine>` | Alias for manual lookup | `/rule grappling` |
| `/tsmorte`, `/deathsave`, `/ds` | Roll 5e Death Saving Throw | `/ds` |
| `/vision <name> <radius>` | DM only: sets character darkvision radius | `/vision Gildor 12` |
| `/darkness`, `/oscurita` | DM only: toggles global map darkness filter | `/darkness`, `/oscurita` |
| `/weather <cond>`, `/meteo <cond>` | DM only: sets dynamic weather (`clear`, `rain`, `storm`, `snow`, `fog`, `darkness`) | `/weather storm`, `/meteo nebbia` |

### Canvas & Hotkey Controls

| Action | Control | Description |
|---|---|---|
| **Command Palette** | `Ctrl + K` | Opens universal search for rules, monsters, spells, tokens, and rolls. |
| **Pan Map** | Right-Click + Drag or Middle-Click + Drag | Smooth canvas viewport navigation. |
| **Zoom Map** | Mouse Wheel Up / Down | Zooms in/out centered on cursor. |
| **Move Token** | Left-Click + Drag on Token | Moves active token along valid hex paths. |
| **Ping Map** | Middle-Click on Hex (or `[ 📍 ]`) | Sends animated ping marker to all players. |
| **Measure Distance** | Click `[ 📏 ]` then Drag | Scale-aware distance in hexes, `ft`/`m` or `mi`/`km` + travel time. |
| **Target Select** | Click `[ 👆 ]` then Click Target | Centers view / targets token. |
| **Place AoE** | Click `[ 💥 ]` then Click Origin Hex | Previews and drops spell template. |
| **Difficult Terrain** | Click `[ 🪨 ]` on left toolbar | Opens brush popup to paint Mud, Ice, Briars, Rubble, Swamp. |
| **Darkness Toggle** | Click `[ 🌑 ]` on left toolbar | 1-click toggle for global pitch-black darkness with 5e vision rules. |

---

## 9. Bilingual Internationalization (IT / EN) & Distance Units (ft / m)

D&D OmniCompanion features full live bilingual localization and dual measurement systems:
* **Language (`🌐 Lingua / Language`)**: Switch at runtime between **Italiano 🇮🇹** and **English 🇬🇧** without restarting the server or client.
* **Distance Units (`📏 Unità di Misura` / `📏 Distance Units`)**: Switch at runtime between **Imperial (`Feet / Miles - ft / mi`)** and **Metric (`Meters / Kilometers - m / km`)**. Automatically converts character speeds, movement bars, map scales, and ruler readouts ($5\text{ ft} = 1.5\text{ m}$).

---

## 10. Testing Suite & Quality Assurance

The codebase includes automated test suites covering headless unit tests, GUI smoke tests, and full multiplayer simulation:

```powershell
# 1. Run unit tests for recent features (multi-scale ruler, criticals, turn economy, units, whispers, death saves)
$env:DND_MOCK_AUDIO="1"; python test_new_features.py

# 2. Run UI smoke tests across all 19 server and client windows
$env:DND_MOCK_AUDIO="1"; python test_ui_smoke.py --no-screens

# 3. Run the complete 53-phase multiplayer game simulation
$env:DND_MOCK_AUDIO="1"; python simulate_game_session.py

# 4. Run campaign system tests
$env:DND_MOCK_AUDIO="1"; python -m unittest test_campaign_system.py
```

All test suites pass with **0 failures**, validating end-to-end reliability across network sockets, combat mechanics, and graphical rendering.
