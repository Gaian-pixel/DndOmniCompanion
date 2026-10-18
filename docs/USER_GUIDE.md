# 🐉 D&D OmniCompanion — Complete User Guide

> 🌐 **Language / Lingua**: 🇬🇧 **[English (USER_GUIDE.md)](USER_GUIDE.md)** | 🇮🇹 **[Italiano (GUIDA_ALL_UTILIZZO.md)](GUIDA_ALL_UTILIZZO.md)**

Welcome to the official user guide for **D&D OmniCompanion**, the Virtual Tabletop (VTT) and Campaign Manager for **Dungeons & Dragons 5th Edition**.
This manual walks you step by step through starting a session, configuring the interface, managing characters, maps, combat, exploration, measurement units, and Dungeon Master tools.

---

## 📑 Table of Contents

1. [Quick Start & Connection](#1-quick-start--connection)
2. [Interface Overview & Global Settings](#2-interface-overview--global-settings)
   - [Top Menu Bar: Language, Distance Units & Session Log Export](#top-menu-bar-language-distance-units--session-log-export)
   - [3-Column Layout, Canvas HUDs & Whiteboard Tools (`[ ✏️ ]`)](#3-column-layout-canvas-huds--whiteboard-tools---)
   - [Quick Command Palette (`Ctrl+K`)](#quick-command-palette-ctrlk)
3. [Distance Units, Map Scales, Multi-Grid & Dynamic Ruler](#3-distance-units-map-scales-multi-grid--dynamic-ruler)
   - [Choosing Between Feet/Miles (`ft/mi`) and Meters/Kilometers (`m/km`)](#choosing-between-feetmiles-ftmi-and-meterskilometers-mkm)
   - [The 4 Map Scales (DMG p. 14)](#the-4-map-scales-dmg-p-14)
   - [Multi-Grid Support: Hexagonal, Square & Gridless](#multi-grid-support-hexagonal-square--gridless)
   - [Using the Dynamic Ruler (`[ 📏 ]`)](#using-the-dynamic-ruler---)
4. [Player Guide](#4-player-guide)
   - [Standalone Offline Character Manager](#standalone-offline-character-manager)
   - [Character Creation Wizard & Level-Up](#character-creation-wizard--level-up)
   - [Hero Summary Card & Interactive Character Sheet](#hero-summary-card--interactive-character-sheet)
   - [Special Class Resources (Ki, Rage, Bardic Inspiration, etc.)](#special-class-resources-ki-rage-bardic-inspiration-etc)
   - [Magic Item Attunement (Attunement `🔮`) & DM Inspiration](#magic-item-attunement-attunement--dm-inspiration)
   - [Turn Economy: Exploration vs. Combat](#turn-economy-exploration-vs-combat)
   - [Combat Actions, AoE Spells & Upcasting](#combat-actions-aoe-spells--upcasting)
   - [RAW Reactions & Shield Spell Prompt](#raw-reactions--shield-spell-prompt)
   - [Special Traits: Evasion (Rogue/Monk) & Sneak Attack](#special-traits-evasion-roguemonk--sneak-attack)
   - [Hit Points, Rests & Death Saving Throws](#hit-points-rests--death-saving-throws)
   - [Inventory, Encumbrance, Trading & DM Approval](#inventory-encumbrance-trading--dm-approval)
   - [Character Sheet Export (Official D&D 5e PDF & JSON)](#character-sheet-export-official-dd-5e-pdf--json)
   - [Macro Hotbar (Quick Slots 1–10)](#macro-hotbar-quick-slots-110)
5. [Dungeon Master (DM) Guide](#5-dungeon-master-dm-guide)
   - [Campaign Management Styles (DM Agency vs. Full Automation) & Pending Actions Dock](#campaign-management-styles-dm-agency-vs-full-automation--pending-actions-dock)
   - [Campaigns, Acts, Scenes & Starter Pack](#campaigns-acts-scenes--starter-pack)
   - [Map Management, Map Editor, Walls, Traps & Portals](#map-management-map-editor-walls-traps--portals)
   - [Doors, Locks & RAW 5e Lockpicking Mechanics](#doors-locks--raw-5e-lockpicking-mechanics)
   - [Dungeon Room Pins & Narration Boxed Text](#dungeon-room-pins--narration-boxed-text)
   - [Blind Rolls to the DM (`/broll`, `/gmroll`)](#blind-rolls-to-the-dm-broll-gmroll)
   - [Fog of War (FoW), Manual Brush, Line of Sight & Lighting](#fog-of-war-fow-manual-brush-line-of-sight--lighting)
   - [Creature Token Sizes & DM Hidden Layer (GM Layer)](#creature-token-sizes--dm-hidden-layer-gm-layer)
   - [Combat Management & Live Encounter Balancer (DMG p. 82)](#combat-management--live-encounter-balancer-dmg-p-82)
   - [SRD Bestiary, Offline PDF Rulebooks & Procedural Generators](#srd-bestiary-offline-pdf-rulebooks--procedural-generators)
   - [World, Calendar, Weather, Travel, Shops & Quests](#world-calendar-weather-travel-shops--quests)
   - [Handouts (Documents/Images) & Audio Soundboard](#handouts-documentsimages--audio-soundboard)
   - [Shared Tactical Whiteboard & Session Log Export](#shared-tactical-whiteboard--session-log-export)
6. [Critical Successes (`Natural 20`) & Critical Failures (`Natural 1`)](#6-critical-successes-natural-20--critical-failures-natural-1)
7. [Discord-Styled Chat, Whispers & UDP Voice Chat](#7-discord-styled-chat-whispers--udp-voice-chat)
8. [Quick Reference: Chat Commands & Shortcuts](#8-quick-reference-chat-commands--shortcuts)

---

## 1. Quick Start & Connection

1. Open a terminal in the project root folder and run:
   ```bash
   python main.py
   ```
2. The **Main Launcher** will appear with two role cards:
   * **Dungeon Master (Host)**:
     * **⚔️ Launch with Campaign**: load an existing campaign (with acts, scenes, prepared encounters, and maps).
     * **📜 Prepare / Edit Campaign**: open the Campaign Editor to author your adventure before the session.
     * **⚡ Quick Session (Empty)**: immediately start the server on TCP port `53911` (and UDP Voice port `53912`) for an ad-hoc game.
   * **Player**:
     * **👤 Character Manager (Offline)**: opens a dedicated window to view, create, edit, duplicate, delete, and export character sheets (Official PDF or JSON backup) completely offline without needing a server connection.
     * **✨ Create Character (Wizard)**: immediately starts the step-by-step Baldur's Gate 3 inspired character creation wizard for a Level 1 hero.
     * **🛡️ Join Game**: opens the Player VTT client. From `Server -> Connect to Server...` (or `Reconnect to Last Server`), choose your character, enter the DM's IP address (`127.0.0.1` or LAN/VPN IP), and click **Connect**.

---

## 2. Interface Overview & Global Settings

### Top Menu Bar: Language, Distance Units & Session Log Export
At the top menu bar (on both DM and Player clients) you will find instant configuration menus and session management utilities:
* **`🌐 Language / Lingua`**: switches the entire UI, conditions, skills, abilities, and system messages in real time between **Italiano 🇮🇹** and **English 🇬🇧** without restarting.
* **`📏 Distance Units` (`📏 Unità di Misura`)**: lets you choose at any time between:
  * **Feet / Miles (`ft / mi`)** — Standard US Imperial system (1 tactical hex = `5 ft`).
  * **Meters / Kilometers (`m / km`)** — European/Italian Metric system (1 tactical hex = `1.5 m`).
* **`File -> 📜 Export Session Log...`**: allows both the DM and Players to export the entire session history (chat messages, dice rolls, tactical actions, damage dealt, and spawns) into a clean, formatted **Markdown (`.md`)** file or an **interactive HTML** file.

### 3-Column Layout, Canvas HUDs & Whiteboard Tools (`[ ✏️ ]`)
The workspace is divided into three ergonomic columns:
1. **Left Toolbar (Map & Whiteboard Tools)**: compact icon bar for interacting with the map:
   * `👆` Select / Center token and map.
   * `💥` Area of Effect (AoE) spell templates and Magical Darkness Spheres.
   * `📏` Dynamic measurement ruler with travel time estimations.
   * `📍` Shared animated broadcast ping.
   * `📖` Offline PDF rulebooks browser.
   * `[ ✏️ ]` **Tactical Whiteboard / Pen**: lets both DM and Players sketch freehand tactical lines, arrows, and routes directly on the shared canvas in real time.
   * `[ 🧹 ]` / `[ 🗑️ ]` **Clear Whiteboard**: immediately clears all drawings from the map locally and across all connected clients.
   * `🚪` Doors and Teleport Transitions between maps (DM only).
   * `[ 🪨 ]` **Difficult Terrain Brush (DM only)**: select a terrain brush (Mud, Ice, Briars, Rubble, Swamp, Eraser) and paint or clear surfaces directly on the live session battlemap.
   * `[ 🌑 ]` **1-Click Darkness Filter (DM only)**: instantly toggles map-wide Darkness with automated D&D 5e visibility, torchlight, and Darkvision rules.
   * `☁️` Fog of War (with multi-radius brush from 0 to 3, DM only).
2. **Center Viewport (`HexMapCanvas`)**: the interactive map (hexagonal, square, or gridless), enhanced by two floating HUD overlays:
   * **Initiative Ribbon HUD (top-center)**: automatically appears during combat, displaying cards for all combatants in turn order (`#1`, `#2`...), an active turn arrow `▼`, and a mini HP bar for each combatant. Clicking any card centers the camera on that token.
   * **Glassmorphism Map Controls (bottom-left)**: floating `[ - ]`, `[ 100% ]`, `[ + ]`, and `[ ⌖ ]` buttons to zoom or recenter the viewport with 1 click.
3. **Right Sidebar (Tabbed Notebook)**: houses Chat & Voice Controls, Player Controls / Initiative Tracker, World & Calendar, Bestiary, and Audio/SFX Soundboard.

### Quick Command Palette (`Ctrl+K`)
Press **`Ctrl+K`** at any time (or select `Tools/Library -> Quick Command Palette`) to open the universal search modal:
* Type a **monster**, **spell**, or **5e rule** name to inspect its statblock or description.
* Type a **map token** name to immediately center the camera on that token.
* Type a dice expression such as `/roll 2d6+4` or `1d20+5` and press `Enter` to roll immediately in chat.

---

## 3. Distance Units, Map Scales, Multi-Grid & Dynamic Ruler

### Choosing Between Feet/Miles (`ft/mi`) and Meters/Kilometers (`m/km`)
Whenever you switch units from the **`📏 Distance Units`** menu, the entire application automatically converts:
* Your character's **Speed** in the Hero Summary Card, Character Sheet, and Creation Wizard (`30 ft` $\leftrightarrow$ `9 m`).
* The **Movement Bar** in the Turn Economy panel.
* The **Dynamic Ruler** (`[ 📏 ]`) and map scale badges.

### The 4 Map Scales (DMG p. 14)
Every map has a geographic scale. The DM can view and change it with 1 click via the **`📏 Scale: ...`** pill in the top bar above the map (or in the Map Editor):

| Map Scale | 1 Hex Value (Imperial) | 1 Hex Value (Metric) | Estimated Marching Time | Typical Use Case |
|---|---|---|---|---|
| **⚔️ Combat** | `5 ft` | `1.5 m` | Real-time (6 sec/round) | Tactical encounters, dungeons, taverns |
| **🌲 Exploration (POI)** | `1 mi` | `1.5 km` | `~20 min` per hex | Local valleys, forests, city districts |
| **🌍 World / Region** | `6 mi` | `9 km` | `2 hours` per hex (`4 hexes = 1 day`) | Continental/kingdom maps (e.g., Sword Coast, Faerûn) |
| **⚙️ Custom** | Configurable (`ft`/`mi`) | Configurable (`m`/`km`) | Automatically calculated | Non-standard grid maps |

> [!TIP]
> When the DM changes the scale from the `📏 Scale` top-bar selector, the change is saved and broadcast live to all connected players!

### Multi-Grid Support: Hexagonal, Square & Gridless
OmniCompanion supports three distinct grid geometries to match any map type:
* **Hexagonal Grid (`hex`)**: the signature tactical grid ideal for overland exploration and AoE geometric projections (cones and spheres).
* **Square Grid (`square`)**: standard 5e dungeon battlemap grid. Utilizes official **Chebyshev distance** for movement (each diagonal step counts as $5\text{ ft} / 1.5\text{ m}$, matching standard 5e rules).
* **Gridless Mode (`none` / `gridless`)**: suppresses all grid lines for pictorial artwork; the ruler and token movement calculate exact Euclidean pixel distance.
* **Instant Grid Switching**: the DM can switch the active map's grid type live at any time by clicking the **`📐 Grid: ...`** pill in the top status bar.

### Using the Dynamic Ruler (`[ 📏 ]`)
1. Click the **`[ 📏 ]`** button on the left toolbar to activate Ruler mode (the button highlights in gold).
2. **Left-click and drag** from a starting hex to a destination hex on the map.
3. A dashed gold vector appears with a high-contrast badge displaying:
   * On **Combat** maps: `6 hex (30 ft)` or `6 hex (9 m)`.
   * On **Exploration** maps: `3 hex (3 mi [~1h])` or `3 hex (4.5 km [~1h])`.
   * On **World / Region** maps: `8 hex (48 mi [~2 d])` or `8 hex (72 km [~2 d])`.

---

## 4. Player Guide

### Offline Character Creation & Management (No Server Needed)
You do not need to start a session or connect to a DM server to create, view, edit, or export characters:
* **From the Main Launcher (`main.py`)**:
  * **👤 Character Manager (Offline)**: opens a comprehensive offline management panel with the full list of saved heroes, search/filtering by name/class/race, instant preview of core stats (HP, AC, Speed, Ability Scores with modifiers), and buttons to **open the complete character sheet**, **duplicate**, **delete**, or **export to Official 5e PDF or JSON**. If you want to jump straight into a game, click "Select as Active" to select the character and launch the client immediately.
  * **✨ Create Character (Wizard)**: launches the Baldur's Gate 3 inspired step-by-step character creator to create and save a new Level 1 hero locally.
* **From the Player VTT Client (`client/client.py`)**:
  * In the top menu bar: navigate to **`Character -> Character Manager (Offline)...`** or **`Create New Character (Wizard)...`** / **`Create Manual Character...`**.
  * On the right sidebar (`Player Controls` tab): use the quick tool buttons `[ ✨ ]` (New Hero) and `[ 👤 ]` (Manager) placed right beside the active character dropdown.
  * The **`📜 Character Sheet`** button is **always active even when disconnected**: click it at any time to inspect your character, test offline dice rolls, edit equipment, level up, manage spells, and export the official PDF.

### Character Creation Wizard & Level-Up
* **New Character (Level 1)**: From the Character Manager, the client menu, or the sheet, launch the **Creation Wizard**. It guides you through Race, Class, Background, Ability Scores (Standard Array, Point Buy, or Dice Roll), and starting equipment.
* **Leveling Up (`Level Up (+)`)**: Inside the Character Sheet, click `Level Up (+)`:
  * Choose between the **fixed average** Hit Die value or **rolling**.
  * The wizard automatically fetches **new class features** and updates **spell slots** for your new level from the 5e SRD.
  * At ASI levels (e.g., 4, 8, 12, 16, 19), assign your **Ability Score Improvement (+2 / +1+1)** or Feat.

In the **`Player Controls`** tab on the right sidebar, the **Hero Summary Card** is always visible at the top:
* Displays Name, Class/Race/Level, Current/Max HP (plus Temporary HP, Exhaustion level, and active Conditions).
* **Dynamic Health Bar**: smoothly fills from `0%` to `100%` of the card width, shifting color from green (`> 50%`) to amber (`25%–50%`) and red (`< 25%`).
* Quick badges for **🛡️ AC**, **👟 Speed** (converted to `ft` or `m`), and **⚡ Initiative**.
* **Light Source Button `[ 🕯️ ]` (PHB p. 183)**:
  * **Left-Click**: instantly turns the character's active light source on or off.
  * **Right-Click**: opens a context menu to select from 4 official presets:
    * **Torch**: $20\text{ ft}$ bright, $20\text{ ft}$ dim (8-hex radius), warm amber glow `#FFD700`.
    * **Hooded Lantern**: $30\text{ ft}$ bright, $30\text{ ft}$ dim (12-hex radius), orange glow `#FFA500`.
    * **Hooded Lantern (Dim / 5 ft)**: $5\text{ ft}$ dim (1-hex radius), narrow `#FF8C00` beam.
    * **Light Spell**: $20\text{ ft}$ bright, $20\text{ ft}$ dim (8-hex radius), magical cyan glow `#66D9E8`.
  * **Dynamic FoW Integration**: toggling lights automatically reveals Fog of War based on $\max(\text{vision\_radius}, \text{light\_radius})$.

Click **`📋 Character Sheet`** to open the full multi-tabbed sheet:
1. **Stats & Combat**: Ability Scores, Saving Throws, all 18 Skills with Proficiency selector (`0 = None`, `1 = Proficient +PB`, `2 = Expertise +2×PB`) and `🎲` 1-click roll buttons, quick HP adjusters (`-5`, `-1`, `+1`, `+5`), Short/Long Rest buttons, Hit Dice, and Death Saves.
2. **⚔️ Weapons & Attacks**: weapon list with automatic attack bonus and damage roll buttons.
3. **🎒 Inventory**: item management with weight, magic item attunement (max 3 `🔮`), Coin Pouch (`cp`, `sp`, `ep`, `gp`, `pp`), and automatic **Encumbrance** tracking ($\text{Strength} \times 15\text{ lbs}$).
4. **📖 Spellbook**: Spell Slot counters for levels 1–9, SRD spell search, and **Cast** button that automatically deducts a slot and announces the spell in chat.
5. **🌟 Features & Traits / 📜 Journal**: racial traits, class features, special class resource tracker, and session notes.

### Special Class Resources (Ki, Rage, Bardic Inspiration, etc.)
Under the **`🌟 Features`** tab of the Character Sheet you will find the **`⚡ Special Class Resources`** interactive card:
* **Automatic Population**: during character creation or level-up, official class resources are automatically added (e.g., *Ki Points* for Monks, *Rage Uses* for Barbarians, *Bardic Inspiration* for Bards, *Wild Shape* for Druids, *Channel Divinity* for Clerics/Paladins, *Action Surge* and *Second Wind* for Fighters, *Sorcery Points* for Sorcerers, *Lay on Hands* for Paladins).
* **Quick Adjusters `[-]` / `[+]`**: spend or restore charges with 1 click during gameplay.
* **Custom Resources**: create custom tracking pools with **`+ Add Resource`** by specifying Name, Maximum Value, and Recovery Rule (*Short Rest* or *Long Rest*), or delete with `🗑️`.
* **Smart Rest Recovery**: taking a *Short Rest* or *Long Rest* automatically replenishes only the resources appropriate for that rest type.

### Magic Item Attunement (Attunement `🔮`) & DM Inspiration
* **Magic Item Attunement (Attunement `🔮`)**:
  * As per official RAW 5e rules (DMG p. 136), a character can be attuned to a maximum of **3 magic items simultaneously**.
  * Under the **🎒 Inventory** tab of the Character Sheet, each item features an attunement toggle indicator `🔮 Attuned`.
  * The system dynamically counts occupied attunement slots (`🔮 Active Attunement: X / 3`) and prevents exceeding the limit without ending an existing attunement during a short rest.
  * Passive stat bonuses (e.g., bonuses to AC, attack rolls, ability scores, or saving throws) are automatically calculated and applied directly to your character sheet.
* **Dungeon Master's Inspiration (`✨ Inspiration`)**:
  * Displayed prominently at the top of the Character Sheet and in the Hero Summary Card as an **`✨ Inspiration`** badge.
  * Can be granted by the DM with 1 click to reward exceptional roleplaying, clever ideas, or heroic sacrifices.
  * The player can spend Inspiration at any time before making an attack roll, saving throw, or ability check to gain immediate **Advantage** (2d20kh1).

### 5e Backpacks, Containers & Variant Encumbrance (RAW PHB p. 143, 176, 190)
OmniCompanion authentically simulates item storage locations, extradimensional capacity, and bodily weight burdens:

1. **Inventory Containers & Compartments**:
   * Each item has a designated location (`container`):
     * `🎒 Backpack` (`backpack`): default storage for adventuring gear, rations, and tools.
     * `⚔️ Equipped / On Person` (`equipped`): weapons held in hand, armor worn, shields strapped, and accessories carried on your belt.
     * `🔮 Bag of Holding` (`bag_of_holding`): extradimensional space (max capacity 500 lbs / 64 cubic feet). Contained items do not burden the character.
     * `✨ Heward's Handy Haversack` (`haversack`): extradimensional pockets (max capacity 120 lbs, empty haversack weight 5 lbs).
     * `🐴 Saddlebag / Mount` (`mount`): gear stowed on horses, mules, or pack beasts (does not burden the character).
   * Container locations can be selected and updated with 1 click in both the custom item creation dialog and item details.

2. **Tactical "Drop Backpack" Action (*Drop Backpack*, PHB p. 190)**:
   * Under 5e rules, slipping off a backpack and letting it drop to the floor is a free **Object Interaction** performed as part of a move or action.
   * Both in the Character Sheet (Inventory tab) and on the sidebar **Hero Summary Card**, players have the 1-click toggle button `[ 🎒 Drop Backpack ]` $\leftrightarrow$ `[ 🎒 Pick Up Backpack ]`.
   * When the backpack is dropped:
     * Status updates to `⚠️ Backpack: On Ground`.
     * All items stored in the backpack are visually flagged with `[On Ground]`.
     * The weight of all items inside the backpack is **instantly excluded from the carried weight**, allowing the adventurer to shed encumbrance penalties and move at full combat speed.
     * The action is announced to table chat citing PHB p. 190.

3. **5e Variant: Encumbrance Rule (PHB p. 176)**:
   * **Real Coin Weight**: 50 coins of any metal type weigh exactly 1 pound (e.g., 500 gp = 10 lbs carried on belt).
   * **Strength-Based Thresholds**:
     * **🟢 Normal** ($\le \text{STR} \times 5\text{ lbs}$): no penalty.
     * **🟡 Encumbered** ($> \text{STR} \times 5\text{ lbs}$ up to $\text{STR} \times 10\text{ lbs}$): movement speed reduced by **10 ft (3 m)**.
     * **🔴 Heavily Encumbered** ($> \text{STR} \times 10\text{ lbs}$ up to $\text{STR} \times 15\text{ lbs}$): movement speed reduced by **20 ft (6 m)** and **Disadvantage** on ability checks, attack rolls, and saving throws that use Strength, Dexterity, or Constitution.
     * **⛔ Overloaded** ($> \text{STR} \times 15\text{ lbs}$): weight exceeds maximum carrying capacity; speed drops to **0**.
   * Speed penalties are automatically applied to the Hero Summary Card speed badge and turn movement tracker.

### Turn Economy: Exploration vs. Combat
The **Turn Economy** section in the `Player Controls` tab automatically adapts to the current game phase:

* **Out of Combat (`🧭 Exploration Mode - Free Movement`)**:
  * The header displays **`🧭 Exploration Mode (Free Movement)`**.
  * All three badges (**`⚡ Action`**, **`✨ Bonus`**, **`🛡️ Reaction`**) remain active in `Free (Exploration)` mode: you can move across the map, attack, or cast spells freely without badges turning red or locking you out.
  * The bottom bar displays **`👟 Speed: 30 ft (Free)`** (or `9 m (Free)`), showing your per-move speed without deducting from a combat turn pool.
* **During Combat (`Turn Economy`)**:
  * When the DM starts combat, the panel switches to strict server-synchronized D&D 5e turn tracking.
  * Performing an attack or standard action consumes **`⚡ Action`**; using a bonus action consumes **`✨ Bonus`**; moving across hexes deducts feet/meters from the **`👟 Movement`** bar.
  * You can also click individual badges manually to toggle them (e.g., spending your `🛡️ Reaction` for *Shield* or an *Opportunity Attack*), or click **`↺ Reset`**.
  * All turn resources **reset automatically** at the start of your turn and whenever combat begins or ends.

### Combat Actions, AoE Spells, Tactical Cover & Upcasting
* **`⚔️ Action` Button**: opens the 5e Standard Actions dialog:
  * **Weapon / Spell Attack**: choose target, weapon, optional Advantage/Disadvantage, and **5e RAW Tactical Cover**:
    * `Automatic Cover`: geometric raycasting (`hex_linedraw`) calculating intervening walls, half-cover obstacles, and interposing creatures.
    * `No Cover`: target's normal AC.
    * `Half Cover (+2 AC / +2 DEX Save)`: target behind low walls, trees, or creatures.
    * `Three-Quarters Cover (+5 AC / +5 DEX Save)`: target behind arrow slits or substantial fortifications.
    * `Total Cover`: target is completely obscured; attack is blocked.
  * **5e Tactical Actions**: **Dash** (doubles turn movement), **Disengage** (prevents opportunity attacks), **Dodge** (imposes disadvantage on enemy attacks and grants advantage on DEX saves), **Help** (grants an ally advantage).
* **`[ 💥 ]` Button (Area of Effect)**:
  * Choose the geometric template (**Sphere**, **Cone**, **Line**), size in hexes, color, and optional Saving Throw (e.g., `DEX DC 15` with `8d6` fire damage).
  * Click on the map to place the template: the server automatically identifies affected targets, prompts Saving Throws (applying Half or 3/4 Cover save bonuses if applicable), and applies full or half damage.
* **Spellcasting, Upcasting & Strict Concentration (PHB p. 201-204)**:
  * When clicking **`Cast`** on a 1st+ level spell in your Spellbook, a modal dialog presents all available spell slots from the spell's base level up to level 9.
  * Select a higher-level slot to **Upcast** the spell (e.g., casting 1st-level *Magic Missile* using a 3rd-level slot).
  * The designated slot is deducted automatically, and chat broadcasts an announcement noting both the spell's base level and the effective upcast level.
  * **Strict Concentration**:
    * Concentration spells are automatically tracked.
    * Casting a new concentration spell automatically drops any existing concentration with a chat broadcast, preventing unauthorized dual-concentration.
    * Taking damage while concentrating triggers an automatic Constitution save ($\text{DC} \ge 10$); failure instantly removes the condition and linked persistent AoE zones.
* **`⏭️ End Turn` Button**: active during your combat turn; immediately advances initiative to the next combatant.

### RAW Reactions & Shield Spell Prompt
* **RAW Reaction Economy (PHB p. 190)**:
  * Each creature has exactly one `🛡️ Reaction` per round, which refreshes at the start of its turn.
  * The engine continuously monitors triggers occurring on other combatants' turns.
* **Interactive Shield Spell Prompt**:
  * When an incoming enemy attack roll hits a character's Armor Class (or when targeted by *Magic Missile*), if the character knows or has prepared the *Shield* spell, holds an unspent `🛡️ Reaction`, and has at least one 1st+ level spell slot available, a countdown reaction prompt pops up:
    * If accepted: spends the round's `🛡️ Reaction`, expends a 1st-level spell slot, and adds **+5 to Armor Class (AC)** until the start of the caster's next turn.
    * **Retroactive Attack Recalculation**: If the improved AC ($AC + 5$) now equals or exceeds the enemy's attack roll, the attack is retroactively converted from a Hit into a Miss, completely sparing the character from damage!
* **Dynamic Opportunity Attacks**:
  * When an adjacent enemy (within 1 hex / $5\text{ ft}$) attempts to move away from melee range without taking the *Disengage* action, the server triggers an Opportunity Attack alert, allowing the defending player to spend their `🛡️ Reaction` to make an immediate melee attack.

### Special Traits: Evasion (Rogue/Monk) & Sneak Attack
* **Evasion (*PHB p. 79/96*)**:
  * For 7th-level Rogues and Monks, instinctive agility alters Dexterity saving throws against area effects (such as a *Fireball* spell or dragon breath):
    * **Successful Save**: takes **0 damage** (instead of half damage).
    * **Failed Save**: takes only **half damage** (instead of full damage).
  * The engine automatically checks the character's class and level to adjust damage without requiring manual calculations.
* **Sneak Attack (*PHB p. 96*)**:
  * When a Rogue lands an attack, the rules engine automatically validates official 5e conditions:
    * The attack must use a **Finesse** or **Ranged** weapon.
    * The Rogue has **Advantage** on the attack roll, OR another enemy of the target is within 1 hex ($5\text{ ft}$), that enemy is not incapacitated, and the Rogue **does not have Disadvantage**.
    * Sneak Attack damage applies **once per turn**.
  * When criteria are satisfied, the extra sneak attack dice appropriate for the Rogue's level (from $+1d6$ at 1st level up to $+10d6$ at 19th level) are automatically rolled and combined into the damage report.

### Hit Points, Rests & Death Saving Throws
* **Dropping to 0 HP**: your character automatically loses `Concentration` and gains the `Unconscious` and `Prone` conditions. If remaining excess damage is $\ge \text{Max HP}$, **Instant Death** occurs.
* **Death Saving Throws**:
  * At the start of your turn at 0 HP (or via `/ds` / `/deathsave` in chat, or from the Character Sheet), roll a Death Save:
    * **`Natural 20`**: immediately regain **1 HP** and clear `Unconscious`!
    * **`10–19`**: +1 Success (at 3 successes you become `Stabilized`).
    * **`2–9`**: +1 Failure.
    * **`Natural 1`**: **+2 Failures** (at 3 failures the character dies).
* **Short Rest & Long Rest (RAW PHB p. 186)**:
  * **Short Rest Hit Dice Spending (`ShortRestDialog`)**:
    * Clicking **`Short Rest`** in the Character Sheet opens an interactive modal dialog:
      * Displays current and maximum HP with an **interactive health progress bar** and exact **Hit Dice remaining** (e.g. `3 / 5 (d8)`).
      * **`🎲 Spend 1 Hit Die` Button**: rolls one die of your class ($1\text{dY} + \text{CON mod}$, minimum 1 HP healed even with negative CON), adds the HP, and logs rolls step-by-step.
      * **`⚡ Spend All Hit Dice` Button**: rolls remaining hit dice consecutively until HP is full or dice are exhausted.
      * **`✅ Finish Rest` Button**: closes the dialog, broadcasts total recovered HP and dice spent to chat, and restores short-rest resources (e.g., *Second Wind*, *Action Surge*, and *Warlock Pact Magic slots*).
  * **Long Rest**: fully restores HP, all Spell Slots, reduces Exhaustion by 1, recharges all class resources, and **regains up to half of the character's total Hit Dice** ($\max(1, \lfloor\text{Total}/2\rfloor)$ as per official 5e RAW).

### Inventory, Encumbrance, Trading & DM Approval
* **Online Security (DM Approval)**: while connected to a live session, ability scores and Max HP are locked. To add currency or custom items, click **`🤝 Request Currency from DM`** or add an item: the DM receives an instant approval prompt.
* **Trading with Allies (`Give` / `🤝 Give Gold to Ally`)**: transfer items or gold pieces directly to another connected party member.

### Character Sheet Export (Official D&D 5e PDF & JSON)
At the bottom of the Character Sheet window, click **`📥 Esporta Scheda...`**: a dedicated modal selection window opens, allowing you to choose between two formats:
* **📄 Official D&D 5e Character Sheet (PDF)**: prompts you to select your blank 3-page D&D 5e PDF template (e.g., `dnd_blankcharactersheet_it.pdf`, not bundled in Git for size and licensing reasons) and compiles the sheet directly. Includes:
  - **Page 1**: Full header, ability scores and modifiers centered in their boxes, Inspiration check, Proficiency Bonus, Saving Throws with proficiency dots, all 18 Skills (with single dot for proficiency and double circle for expertise), Passive Perception, Armor Class in shield, Initiative, Speed, HP (Max, Current, Temp), Hit Dice total & current, Death Saves tracked, Weapons Table with bonuses and damage/types, Coins in their respective hexagons (CP, SP, EP, GP, PP), Equipment & Inventory, Personality Traits, Ideals, Bonds, Flaws, and Class Features (with tracking for Rage, Second Wind, Ki, etc.).
  - **Page 2**: Character details, age, height, weight, eyes, skin, hair, physical appearance, allies and organizations, full backstory notes, and treasure.
  - **Page 3 (Spellbook)**: Spellcasting class, primary ability, Save DC, Spell Attack Bonus, total and expended slots for each level from 1 to 9, and full spell list with prepared indicators.
* **💾 Raw Character Data (JSON)**: exports structured `.json` data with clean formatting, ideal for backups, external manual editing, or importing into other campaigns.

### Macro Hotbar (Quick Slots 1–10)
At the bottom of the Player window is a bar with **10 numbered macro buttons (`1`–`10`)**:
* **Right-Click a slot**: assign a label and a chat/roll command (e.g., `Longsword` $\rightarrow$ `/roll 1d20+6`, or `/ds`).
* **Left-Click a slot**: immediately executes the macro. Macros are persisted per character.

---

## 5. Dungeon Master (DM) Guide

### Campaign Management Styles (DM Agency vs. Full Automation) & Pending Actions Dock
D&D OmniCompanion empowers the Dungeon Master with total control over the balance between **computational automation** and **human adjudication (DM Agency)**, ensuring that software never overrides the Dungeon Master's narrative voice and pacing:

* **The 3 Core Management Profiles**:
  * **🎲 Traditional Tabletop (Pen & Paper / RAW DM Agency)**:
    * Authentic tabletop pen-and-paper experience. Critical character sheet changes are never committed automatically.
    * When weapon attacks or AoE spells hit, damage is not deducted automatically: the system displays the calculated math in the **Floating DM Pending Actions Dock** for instant approval, halving, modification, or rejection.
    * Locked doors prompt narrative interaction (rusty hinges, trapped keyholes) rather than automatically unlocking upon a click.
    * Character concentration checks, 0 HP knockouts, and death saves are handled with narrative pacing.
  * **⚖️ Assisted Hybrid (Recommended for Fluid Sessions)**:
    * The ideal balance for modern gaming groups. The engine computes complex bookkeeping (resistances, dynamic cover, darkness visibility, difficult terrain penalties, and conditions), while the DM receives ergonomic 1-click decision cards (`[Full]`, `[Half]`, `[Edit]`, `[Reject]`) to validate results effortlessly.
  * **⚡ Full Automation (CRPG / Fast Tactical)**:
    * Video game tactical mode. Damage is directly subtracted from HP, doors unlock instantly upon passing DC, out-of-turn actions are locked, and saving throw/reaction prompts trigger automatically.
* **Switching Profiles on the Fly**:
  * Click the colored badge **`🎲 Table`**, **`⚖️ Hybrid`**, or **`⚡ Full Auto`** on the map's top ribbon.
  * Or navigate to **`Tools -> ⚙️ Campaign Management Style (Automations)...`**.
* **11 Independent Granular Switches**:
  * From the automation settings dialog, the DM can toggle each system independently:
    1. `auto_attack_damage`: automatic HP deduction from weapon attacks.
    2. `auto_aoe_damage`: automatic damage resolution from AoE spells and saving throws.
    3. `auto_concentration`: automatic Constitution saving throw prompts on damage.
    4. `auto_advantage_disadvantage`: automatic 2d20 Advantage/Disadvantage resolution.
    5. `auto_critical_damage`: automatic dice doubling on Natural 20 criticals.
    6. `auto_traps`: automatic trap triggering and damage application.
    7. `auto_turn_economy`: strict combat turn locking for inactive players.
    8. `auto_spell_slots`: automatic deduction of spell slots upon casting.
    9. `auto_encumbrance`: movement restriction when carrying capacity is exceeded.
    10. `auto_death_saves`: automatic turn-start Death Saving Throw prompts.
    11. `auto_weather_effects`: automatic ranged attack penalties in storms, fog, and rain.
* **Floating DM Pending Actions Dock**:
  * When running in Traditional or Hybrid mode, whenever an event requires DM oversight (e.g., incoming damage, rest request, lockpicking attempt, or trap trigger), a non-intrusive floating dock appears at the bottom-center of the DM screen:
  * Shows event details (e.g., `Attack on Gildor: 14 Slashing Damage`) with 1-click action buttons:
    * `[ ✅ Apply ]` — confirm and execute the action immediately.
    * `[ ✂️ Half (Resistance) ]` — halving the numeric value before applying.
    * `[ ✏️ Edit ]` — manually input a custom numeric value.
    * `[ ❌ Reject ]` — discard the action without altering the game state.

### Campaigns, Acts, Scenes & Starter Pack
From the DM **`File`** and **`Tools`** menus:
* **New Campaign / Active Campaign Editor**: structure your adventure into **Acts**, **Scenes** (each linked to a map file and audio tracks), **NPCs**, and **Prepared Encounters**.
* **`🗺️ Switch Scene` Button** (in the `Initiative & Characters` tab): loads the selected scene's map and broadcasts it to all players with 1 click.
* **`⚔️ Deploy Encounter` Button**: spawns all monsters of a prepared encounter onto the active map with 1 click.
* **Campaign Starter Pack (`Tools -> Campaign Starter Pack`)**: configure starting equipment (e.g., Rations, Torch, Potion of Healing) automatically granted to new PCs upon their first login to the campaign.

### Map Management, Map Editor, Walls, Traps & Portals
* **Map Editor (`Tools -> Map Editor`)**:
  * Load a background image, adjust hex size (`hex_size`), and set the **Map Scale** (Combat, Exploration, World, or Custom).
  * Paint **Walls / Obstacles** (blocks movement and Line of Sight).
  * Place **Traps** (with Passive Perception DC, Saving Throw DC, and damage formula, e.g., `2d6`).
  * Place ambient **Lights** and pickable **Loot** items.
  * **Paint Difficult Terrain**: click **`🌾 Difficult Terrain`**, select a terrain category (Mud, Ice, Briars, Rubble, Swamp) from the dropdown, and paint cells directly on the grid with distinct textures and colors. Maps save terrain in JSON format (`"difficult_terrain"`).
* **Live Session Difficult Terrain (`[ 🪨 ]` & Right-Click)**:
  * **Left Toolbar Brush `[ 🪨 ]`**: click the toolbar button to open the quick brush selector (**💩 Mud**, **🧊 Ice**, **🌿 Briars**, **🪨 Rubble**, **🌊 Swamp**, **🗑️ Eraser**). Click map hexes to instantly paint or erase terrain during live play.
  * **Right-Click Context Menu**: right-click any map cell $\rightarrow$ **`🌾 Difficult Terrain...`** to apply or remove terrain on the fly.
  * **Integrated 5e Rules**:
    * **Movement**: movement costs are doubled for each difficult hex along the path (`hex_linedraw`); if a creature is **Prone**, movement cost increases to 3 hexes per cell.
    * **Hazards on Entry**: stepping onto Ice triggers a **DC 10 Dex saving throw** or falls Prone; entering Briars inflicts **1d4 piercing damage**.
    * **Combat Modifiers**: attacking from unstable footing (Ice, Rubble, Swamp, Mud) imposes **Disadvantage**; striking targets entangled in Briars or stuck in Mud grants **Advantage**.
    * **Coordinate HUD**: hovering over any hex displays its terrain type and movement cost (e.g., `⬡ q:2, r:1 [Ice x2 Mov]`).
* **Portals & Teleports (`[ 🚪 ]`)**: click the `[ 🚪 ]` tool on the left toolbar and click a hex to link it to another map file (e.g., `crypt_level2.json`). Stepping on that hex automatically transitions the party to the destination map.

### Doors, Locks & RAW 5e Lockpicking Mechanics
OmniCompanion manages doors, gates, and passageways through an interactive system fully compliant with official 5e rules:

* **Door States**:
  * **Open (`open`)**: clear passage; Line of Sight freely pierces the threshold.
  * **Closed (`closed`)**: blocks vision and movement, but opens freely with a simple object interaction.
  * **Locked (`locked`)**: engaged lock mechanism with an assigned Difficulty Class (e.g., DC 15 or DC 20).
  * **Secret (`secret`)**: completely hidden on player screens until discovered via Passive Perception or active Investigation; clearly highlighted with a dashed boundary for the DM.
  * **Barred (`barred`)**: fortified from the inside with heavy timber beams or chains, requiring brute force to breach or unbarring from the opposite side.
* **Player Door Interactions**:
  * Clicking or right-clicking an adjacent door presents official RAW options:
  * **🗝️ Open with Key**: if the character carries the designated key in their inventory, the door unlocks instantly without rolls.
  * **🛠️ Pick Lock with Thieves' Tools**:
    * Requires *Thieves' Tools* in the character's inventory (PHB p. 154).
    * Rolls a **Dexterity (Thieves' Tools)** check adding proficiency bonus (or double proficiency for expertise).
    * Meeting or exceeding the door's lock DC clicks the mechanism open and transitions the door to unlocked.
    * In *Traditional* or *Hybrid* mode, the roll triggers a DM notification card to narrate complications (e.g., broken lockpicks on a Natural 1 or tripping a needle trap).
  * **💥 Force / Bash Open**:
    * Rolls a **Strength (Athletics)** check against the door's break DC.
    * A success splinters or forces the door open, but produces a loud crash alerting nearby monsters.
  * **✨ Knock Spell**:
    * Instantly unlocks up to two locks or bars, but emanates an echoing knock audible up to 300 feet (90 meters).
* **DM Door Configuration**:
  * **Right-Click** any door $\rightarrow$ **`Edit Door...`** to customize initial state, lockpicking DC, break DC, secret status, and destination map file.

### Dungeon Room Pins & Narration Boxed Text
**Room Pins (`[ 📌 ]`)** turn OmniCompanion into an interactive adventure module:

* **Placing Room Pins**:
  * The DM selects the **`[ 📌 ]`** tool from the left toolbar or right-clicks any map hex $\rightarrow$ **`Place Room Pin`**.
  * A numbered/labeled pin appears on the map (e.g., `[ 📌 1: Crypt Entrance ]`), visible only to the DM.
* **Room Narrative Window**:
  * Clicking a pin opens a dual-pane narrative inspector:
    1. **📜 Boxed Narration Text**: evocative environmental descriptions written to be read aloud to players (in official Wizards of the Coast style).
       * Click **`📢 Read to Table (Broadcast)`** to push formatted parchment prose to every player's chat log with 1 click!
    2. **🔒 Secret DM Notes**: visible **exclusively to the Master**. Includes hidden traps, monster ambush triggers, concealed loot caches, and investigation clues.

### Blind Rolls to the DM (`/broll`, `/gmroll`)
To preserve true suspense and prevent player metagaming, OmniCompanion provides built-in blind rolling:

* **Chat Command**: type `/broll <dice> [reason]` or `/gmroll <dice> [reason]`:
  * Examples: `/broll 1d20+5 Stealth`, `/broll 1d20+3 Passive Perception`, `/gmroll 1d20+7 Disarm Trap`.
* **Anti-Metagame Behavior**:
  * The server computes the roll using the full mathematical dice engine (including modifiers, criticals, and arithmetic).
  * The **numeric roll, individual dice, and total are dispatched EXCLUSIVELY to the Dungeon Master**.
  * The player receives a discreet confirmation toast in chat:
    > `🎲 You sent a blind roll to the DM (1d20+5: Stealth). The Master knows the outcome!`
  * This prevents metagaming when rolling a low number on perception or stealth, keeping players guessing whether the hallway is truly clear or whether their check was simply disastrous!

### Fog of War (FoW), Manual Brush, Line of Sight & Lighting
* Click **`[ ☁️ ]`** on the DM's left toolbar to open the **Fog of War** toolbar:
  * **Toggle Fog of War On / Off**.
  * **Reveal Full Map** / **Hide Full Map** / **Reset Fog of War**.
  * **Manual FoW Brush (`Radius: 0, 1, 2, 3`)**: select a brush radius from the dropdown. Left-click (reveal) or right-click (hide) anywhere on the map to paint or erase fog across entire circular areas, allowing the DM to uncover or re-shroud rooms in seconds.
* When FoW is enabled, players only see hexes within their vision radius that are not obstructed by walls (dynamic Line of Sight).
* Use the chat command `/vision <CharacterName> <Radius>` (e.g., `/vision Gildor 12` for $60\text{ ft} / 18\text{ m}$ Darkvision) to customize a token's vision radius.

### Creature Token Sizes & DM Hidden Layer (GM Layer)
* **Official 5e Creature Token Sizes**:
  * OmniCompanion supports all 6 official 5e size categories: **Tiny** ($0.5\times$), **Small** ($0.8\times$), **Medium** ($1.0\times$), **Large** ($1.8\times$), **Huge** ($2.6\times$), and **Gargantuan** ($3.5\times$).
  * Tokens proportionally scale on the canvas, occupying their exact tactical footprint.
  * To change token size: **Right-Click** the token or its entry in the player list $\rightarrow$ **`Creature Size`** $\rightarrow$ select the desired category.
* **DM Hidden Layer (GM Layer)**:
  * Allows the DM to prepare monsters, traps, and secrets completely invisible to the players.
  * **DM Canvas View**: tokens on the GM layer render semi-transparently with a dashed purple ring (`#A855F7`) and a prominent `[GM]` badge.
  * **Player Privacy & Zero Data Leaks**: GM layer tokens are never rendered on player screens and are systematically filtered out at the network protocol layer (`GAME_STATE`, `PLAYER_JOINED`, `PLAYER_MOVE`), completely eliminating any possibility of client-side metagaming.
  * To toggle the GM layer on any token: **Right-Click** $\rightarrow$ **`👁️ GM Layer`**.

### Combat Management & Live Encounter Balancer (DMG p. 82)
In the DM **`Initiative & Characters`** tab:
1. **Party vs. NPC Separation**: outside combat, the list cleanly separates `--- PARTY MEMBERS ---` and `--- NPCs & MONSTERS ---`. **Right-Click** any entity to inspect its full sheet, edit HP, apply conditions, set a **Magical Aura**, or toggle Party membership.
2. **Live Encounter Difficulty Calculator**: a badge evaluates encounter difficulty in real time (**Trivial**, **Easy**, **Medium**, **Hard**, **Deadly**) using *Dungeon Master's Guide (p. 82)* XP thresholds and monster count multipliers.
3. **Starting & Advancing Combat**:
   * Click **`🎲 Roll Monster Initiative`** to automatically roll initiative for all NPCs/Monsters.
   * Click **`Start Combat`** to sort combatants, activate the **Initiative Ribbon HUD** on the map, and reset turn economy.
   * Use **`Next Turn ⏩`** and **`⏪ Previous Turn`** to cycle turns and rounds.
4. **Boss Legendary Actions & Lair Actions (MM p. 11)**:
   * **Legendary Actions**:
     * Legendary Bosses can take up to 3 Legendary Actions per round, usable only at the end of another creature's turn.
     * When another character finishes their turn, the engine logs a **DM reminder** noting available legendary charges.
     * The DM can spend actions selecting the cost (1, 2, or 3) and action name (e.g. *Wing Attack*, *Tail Attack*, *Frightful Presence*).
     * At the start of the Boss's turn, legendary action charges **automatically reset to their maximum**.
   * **Lair Actions (Initiative 20)**:
     * For bosses with an active lair (`has_lair_actions = True`), at the top of each combat round at **Initiative count 20**, an automated Lair Action alert broadcasts to chat and DM logs, allowing the DM to trigger environmental lair effects.
   * **Legendary Resistances (3/day)**: when the boss fails a saving throw, the DM can immediately turn the failure into a success.

### SRD Bestiary, Compendium Split View & Procedural Generators
* **Compendium & SRD Split View (`Tools -> Compendium & SRD` or `Library -> Compendium & Rules`)**:
  * **Interactive Master-Detail Interface**: The unified compendium features a responsive two-pane split layout; the left column displays searchable results with live filtering and item counters, while the right panel instantly renders the full 5e statblock card of the selected entry.
  * **Authentic 5e Statblock Component (`StatblockCardView`)**:
    * **Monsters & NPCs**: Faithful to the official *Monster Manual* format with high-contrast badges for **Armor Class** (including armor/shield type notes), **Hit Points** (with hit dice formula), and **Speed** (walking, flying, swimming, burrowing, climbing). Displays a 6-stat ability score grid with real-time calculated modifiers ($(\text{stat}-10)//2$), saving throws with proficiency, skills, damage/condition immunities and resistances, senses (darkvision, passive perception), languages, and Challenge Rating (CR with awarded XP). Dedicated sections for Special Traits, Actions with highlighted attack bonuses and damage formulas, Reactions, and Legendary Actions with action point costs.
    * **Magic Items**: Scroll-themed card displaying item rarity badges (*Common*, *Uncommon*, *Rare*, *Very Rare*, *Legendary*), item category, attunement prerequisites (`Requires Attunement`), magical properties, and lore text.
    * **Spells**: Full spell header with level and school, casting time, range, components (V, S, M), duration, concentration/ritual tags, full description, and higher-level scaling (*At Higher Levels*).
  * **Multi-Criteria Fast Filters**:
    * **Monsters**: Fast-toggle buttons for Challenge Rating tiers (*All*, *CR 0–1/2*, *CR 1–4*, *CR 5–9*, *CR 10–14*, *CR 15–19*, *CR 20+*) and Creature Types (*All*, *Dragon*, *Undead*, *Humanoid*, *Beast*, *Aberration*, *Construct*, *Fey*, *Monstrosity*, *Giant*, *Celestial*, *Fiend*...).
    * **Magic Items**: Fast filters for Rarity and Equipment Type (*Weapon*, *Armor*, *Wand*, *Ring*, *Potion*, *Wondrous*...).
    * **Spells**: Filters by Spell Level (Cantrip, 1–9) and Magic School.
  * **Contextual Primary Action Button**: The bottom right of the statblock features the primary action for the active context:
    * *Monsters*: **`Spawn on Map 🐉`** places the creature at the last clicked hex or map center with initiative, HP, AC, speed, and complete sheet.
    * *Spells*: **`Add to Spellbook ✨`** copies the spell directly into the active character's spell list.
    * *Items*: **`Add to Inventory 🎒`** assigns the item to the active character.
* **`Bestiary` Tab in DM Right Sidebar**:
  * Integrated search bar with instant filter pills for Challenge Rating (CR) and Creature Type.
  * **Visual Mini-Statblock**: Compact card rendering with AC, HP, normalized speed badges, and essential ability score table.
  * **Instant 2-Click Spawning**: Double-click any entry in the bestiary list or click **Spawn on Map** to deploy monsters in seconds.
* **Deterministic AC & Speed Normalization (No raw `[{}]`)**:
  * The engine automatically sanitizes all SRD and PDF-extracted monster entries, removing raw nested JSON formatting (such as `[{'value': 18, ...}]`).
  * Reliably extracts base and complex movement speeds (e.g., *Walk 30 ft, Fly 80 ft, Swim 40 ft*) and armor notes (e.g., *18 (Plate Armor)*).
* **Browse Rulebooks (`📖` or `Tools -> Browse Rulebooks`)**: instant offline search inside official PDF manuals stored in `manuals_pdf/` (*Player's Handbook*, *Dungeon Master's Guide*, *Monster Manual*, *Tasha's*, *Xanathar's*).
* **5e Loot Generator (`Tools -> 💰 Loot Generator`)**: generate balanced treasure hoards by Challenge Rating (CR 0–4, 5–10, 11–16, 17+) and split gold with 1 click.
* **Quick NPC Generator (`Tools -> 🎭 Quick NPC Generator`)**: generate complete NPCs with name, race, personality trait, secret, stats, and 1-click map spawning.

### World, Calendar, Weather, Travel, Shops & Quest Log
* **`World` Tab & `Tools -> Travel Panel`**:
  * Manage the **Calendar of Harptos (Forgotten Realms)** or standard calendar, time of day (with day, sunrise, sunset, and night tint), and **Dynamic Weather** with 6 animated atmospheric environments:
    * **☀️ Clear**: standard unobstructed vision.
    * **🌧️ Rain**: rainfall streaks and water ripples; Disadvantage at long range ($\ge 4$ hexes).
    * **⛈️ Storm**: heavy rain, gale-force winds, and branching animated lightning bolts; **Disadvantage on all ranged attacks** ($> 1$ hex).
    * **❄️ Snow**: swirling snowflakes and frost crystals; Disadvantage at long range ($\ge 3$ hexes).
    * **🌫️ Fog**: dense volumetric mist banks; **Disadvantage on all ranged attacks** ($> 1$ hex).
    * **🌑 Darkness**: deep stippled pitch black, dark edge vignette, and floating shadowy tendrils.
  * **1-Click Darkness Filter & Darkvision (`[ 🌑 ]`)**:
    * Click the **`[ 🌑 ]`** button on the DM's left toolbar, or type `/darkness` or `/weather Darkness`, to cloak the map in complete darkness.
    * **Dynamic Torchlight & Lanterns**: tokens with `light_radius > 0` project a warm golden halo that pierces through the darkness.
    * **Magical Darkness Sphere**: right-click any hex $\rightarrow$ **`🌑 Place Magical Darkness Sphere (R=3)`** to create a zone of magical darkness impenetrable to normal Darkvision (requires *Devil's Sight* or *Truesight*).
    * **D&D 5e Combat Rules (Unseen Attackers & Targets)**: attacking from darkness while seeing the target grants **Advantage**; attacking a target you cannot see imposes **Disadvantage**; mutual darkness cancels out to a normal roll.
  * Manage party **Marching Order** (Front, Middle, Rear), travel roles (Scout, Navigator, Forager), ration/water consumption, and **Forced March** Constitution saving throws.
  * Open and broadcast **Merchant Shops** (`shop_ui.py`).
  * **Shared Quest Log**: accessible from `Library -> 📜 Quest Log` or the DM tools menu:
    * Track main and secondary quest objectives with titles, descriptions, quest givers, and gold/item rewards.
    * All operations (adding quests, completing via `[✅ Complete]`, or deleting) are broadcast in real time to all connected players with chat announcements.

### Shared Document Handouts & Audio Soundboard
* **Document & Image Handouts (`Tools -> Share Text Handout / Share Image`)**:
  * Broadcast parchment scrolls, letters, puzzles, and illustrations directly to all connected players.
  * Clients automatically receive the broadcast and open a themed parchment modal viewer.
* **`Audio / SFX` Tab**: broadcast ambient music (Tavern, Battle, Dungeon) and sound effects synchronously to all connected clients.

### Shared Tactical Whiteboard & Session Log Export
* **Tactical Whiteboard (`[ ✏️ ]` / `[ 🗑️ ]`)**: sketch lines and battle tactics directly on the map; click `[ 🗑️ ]` to clear the whiteboard for all participants with 1 click.
* **Session Log Export (`File -> 📜 Export Session Log...`)**: export and archive the full session chronicle in formatted **Markdown (`.md`)** or **interactive HTML**, perfect for campaign campaign journals and post-session recaps.

---

## 6. Critical Successes (`Natural 20`) & Critical Failures (`Natural 1`)

The rules engine automatically detects every `Natural 20` and `Natural 1` rolled on a 20-sided die (`1d20`, including Advantage `2d20kh1` and Disadvantage `2d20kl1`):

1. **Attack Rolls**:
   * **`🌟 NATURAL 20 CRITICAL HIT!`**: the attack **automatically hits** regardless of the target's AC and **automatically doubles all damage dice** (flat modifiers are added once, per 5e rules).
   * **`💀 CRITICAL FAILURE (Natural 1)!`**: the attack **automatically misses** regardless of bonuses.
2. **Saving Throws (`SAVE_RESULT`)**:
   * Displays **`🌟 NATURAL 20!`** or **`💀 NATURAL 1!`** banners in the result log and broadcasts a Toast notification to the entire table.
3. **Death Saving Throws**:
   * **`Natural 20`**: the character immediately regains **1 HP** and regains consciousness.
   * **`Natural 1`**: inflicts **2 failures** instead of 1.
4. **Skill Checks, Ability Checks & Generic `1d20` Chat Rolls**:
   * Every `1d20` roll triggered from the Character Sheet, Command Palette, or `/roll 1d20+...` is highlighted in chat with gold (`🌟 NATURAL 20!`) or crimson (`💀 NATURAL 1!`) formatting and triggers a visual/audio **Broadcast Toast** across all connected clients.

---

## 7. Discord-Styled Chat, Whispers & UDP Voice Chat

* **Rich Chat**: supports timestamps, distinct role colors for DM and Players, and highlighted blocks for dice rolls and criticals.
* **Private Whispers**: type `/w <Name> <Message>` (or `/whisper`, `/sussurra`) to send a private message visible only to you and the recipient (`[🔒 Whisper]`). Multi-word names can be quoted (e.g., `/w "Goblin Scout" Hello`).
* **Integrated UDP Voice Chat**: at the bottom of the Chat tab are real-time voice controls:
  * **`[ 🎤 ]`**: Mute / Unmute your microphone.
  * **`[ 🎧 ]`**: Deafen / Undeafen incoming voice audio.

---

## 8. Quick Reference: Chat Commands & Shortcuts

| Command / Shortcut | Who Can Use It | Effect | Example |
|---|---|---|---|
| `Ctrl + K` | Everyone | Opens the Quick Command Palette | `Ctrl+K` $\rightarrow$ `fireball` |
| `/roll <dice>` or `/r <dice>` | Everyone | Rolls dice (supports `kh1`/`kl1` for advantage/disadvantage) | `/roll 2d20kh1+5`, `/r 4d6` |
| `/w <name> <text>` | Everyone | Sends a private whisper | `/w DM I check for secret doors` |
| `/whisper <name> <text>` | Everyone | English alias for private whisper | `/whisper Gildor Follow me` |
| `/sussurra <name> <text>` | Everyone | Italian alias for private whisper | `/sussurra Elidor Heal me!` |
| `/manuale <term>` | Everyone | Searches a rule, spell, or monster in indexed PDFs | `/manuale grapple` |
| `/rule <term>` | Everyone | Alias for PDF rulebook search | `/rule concentration` |
| `/broll <dice> [reason]` | Everyone | Makes a secret roll visible **only to the DM** | `/broll 1d20+5 Stealth` |
| `/gmroll <dice> [reason]` | Everyone | Alias for secret DM roll | `/gmroll 1d20+3 Perception` |
| `/tsmorte` / `/deathsave` / `/ds` | Players (at 0 HP) | Rolls a 5e Death Saving Throw | `/ds` |
| `/vision <name> <radius_hex>` | DM Only | Sets a token's vision radius (in hexes) | `/vision Gildor 12` |
| `/darkness` / `/oscurita` | DM Only | Toggles environmental darkness on/off on the map | `/darkness` |
| `/weather <condition>` / `/meteo <condition>` | DM Only | Sets active weather condition | `/weather Storm` |

