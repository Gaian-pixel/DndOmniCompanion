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
   - [Character Creation Wizard & Level-Up](#character-creation-wizard--level-up)
   - [Hero Summary Card & Interactive Character Sheet](#hero-summary-card--interactive-character-sheet)
   - [Special Class Resources (Ki, Rage, Bardic Inspiration, etc.)](#special-class-resources-ki-rage-bardic-inspiration-etc)
   - [Turn Economy: Exploration vs. Combat](#turn-economy-exploration-vs-combat)
   - [Combat Actions, AoE Spells & Upcasting](#combat-actions-aoe-spells--upcasting)
   - [Hit Points, Rests & Death Saving Throws](#hit-points-rests--death-saving-throws)
   - [Inventory, Encumbrance, Trading & DM Approval](#inventory-encumbrance-trading--dm-approval)
   - [Character Sheet Export (Official D&D 5e PDF & JSON)](#character-sheet-export-official-dd-5e-pdf--json)
   - [Macro Hotbar (Quick Slots 1–10)](#macro-hotbar-quick-slots-110)
5. [Dungeon Master (DM) Guide](#5-dungeon-master-dm-guide)
   - [Campaigns, Acts, Scenes & Starter Pack](#campaigns-acts-scenes--starter-pack)
   - [Map Management, Map Editor, Walls, Traps & Portals](#map-management-map-editor-walls-traps--portals)
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
     * Click **🛡️ Join Game** to open the Player VTT client.
     * From `Server -> Connect to Server...` (or `Reconnect to Last Server`), select or create your character, enter the DM's IP address (`127.0.0.1` for local play on the same PC, or the DM's LAN/VPN IP), and click **Connect**.

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
   * `💥` Area of Effect (AoE) spell templates.
   * `📏` Dynamic measurement ruler with travel time estimations.
   * `📍` Shared animated broadcast ping.
   * `📖` Offline PDF rulebooks browser.
   * `[ ✏️ ]` **Tactical Whiteboard / Pen**: lets both DM and Players sketch freehand tactical lines, arrows, and routes directly on the shared canvas in real time.
   * `[ 🧹 ]` / `[ 🗑️ ]` **Clear Whiteboard**: immediately clears all drawings from the map locally and across all connected clients.
   * `☁️` Fog of War (with multi-radius brush) and `🚪` Portals/Teleports (DM only).
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

### Character Creation Wizard & Level-Up
* **New Character (Level 1)**: From the character selection window or character sheet, launch the **Creation Wizard**. It guides you through Race, Class, Background, Ability Scores (Standard Array, Point Buy, or Dice Roll), and starting equipment.
* **Leveling Up (`Level Up (+)`)**: Inside the Character Sheet, click `Level Up (+)`:
  * Choose between the **fixed average** Hit Die value or **rolling**.
  * The wizard automatically fetches **new class features** and updates **spell slots** for your new level from the 5e SRD.
  * At ASI levels (e.g., 4, 8, 12, 16, 19), assign your **Ability Score Improvement (+2 / +1+1)** or Feat.

#### Hero Summary Card & Interactive Character Sheet
In the **`Player Controls`** tab on the right sidebar, the **Hero Summary Card** is always visible at the top:
* Displays Name, Class/Race/Level, Current/Max HP (plus Temporary HP, Exhaustion level, and active Conditions).
* **Dynamic Health Bar**: smoothly fills from `0%` to `100%` of the card width, shifting color from green (`> 50%`) to amber (`25%–50%`) and red (`< 25%`).
* Quick badges for **🛡️ AC**, **👟 Speed** (converted to `ft` or `m`), and **⚡ Initiative**.

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

### Combat Actions, AoE Spells & Upcasting
* **`⚔️ Action` Button**: opens the 5e Standard Actions dialog:
  * **Weapon / Spell Attack**: choose target, weapon, optional Advantage/Disadvantage, and execute the attack.
  * **5e Tactical Actions**: **Dash** (doubles turn movement), **Disengage** (prevents opportunity attacks), **Dodge** (grants attackers disadvantage), **Help** (grants an ally advantage).
* **`[ 💥 ]` Button (Area of Effect)**:
  * Choose the geometric template (**Sphere**, **Cone**, **Line**), size in hexes, color, and optional Saving Throw (e.g., `DEX DC 15` with `8d6` fire damage).
  * Click on the map to place the template: the server automatically identifies affected targets, prompts Saving Throws, and applies full or half damage.
* **Spellcasting & Upcasting (Higher-Level Spell Slots)**:
  * When clicking **`Cast`** on a 1st+ level spell in your Spellbook, a modal dialog presents all available spell slots from the spell's base level up to level 9.
  * Select a higher-level slot to **Upcast** the spell (e.g., casting 1st-level *Magic Missile* using a 3rd-level slot).
  * The designated slot is deducted automatically, and chat broadcasts an announcement noting both the spell's base level and the effective upcast level.
* **`⏭️ End Turn` Button**: active during your combat turn; immediately advances initiative to the next combatant.

### Hit Points, Rests & Death Saving Throws
* **Dropping to 0 HP**: your character automatically loses `Concentration` and gains the `Unconscious` and `Prone` conditions. If remaining excess damage is $\ge \text{Max HP}$, **Instant Death** occurs.
* **Death Saving Throws**:
  * At the start of your turn at 0 HP (or via `/ds` / `/deathsave` in chat, or from the Character Sheet), roll a Death Save:
    * **`Natural 20`**: immediately regain **1 HP** and clear `Unconscious`!
    * **`10–19`**: +1 Success (at 3 successes you become `Stabilized`).
    * **`2–9`**: +1 Failure.
    * **`Natural 1`**: **+2 Failures** (at 3 failures the character dies).
* **Short Rest & Long Rest**:
  * **Short Rest**: spend available Hit Dice to heal ($\text{Hit Die} + \text{CON mod}$) and recharge short-rest features and resources.
  * **Long Rest**: restores full HP, all Spell Slots, half of total Hit Dice, clears exhaustion, and recharges all class resources.

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
* **Doors & Teleports (`[ 🚪 ]`)**: click the `[ 🚪 ]` tool on the left toolbar and click a hex to link it to another map file (e.g., `crypt_level2.json`). Stepping on that hex automatically transitions the party to the destination map.

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
4. **Legendary Actions & Resistances**: for Boss monsters, dedicated controls let the DM spend Legendary Actions or Legendary Resistances with automatic round resets.

### SRD Bestiary, Offline PDF Rulebooks & Procedural Generators
* **`Bestiary` Tab & `Tools -> Compendium & SRD`**: search monsters from the 5e SRD or indexed PDF rulebooks and click **Spawn on Map** to place them with full stats, AC, HP, and actions.
* **Browse Rulebooks (`📖` or `Tools -> Browse Rulebooks`)**: instant offline search inside official PDF manuals stored in `manuals_pdf/` (*Player's Handbook*, *Dungeon Master's Guide*, *Monster Manual*, *Tasha's*, *Xanathar's*).
* **5e Loot Generator (`Tools -> 💰 Loot Generator`)**: generate balanced treasure hoards by Challenge Rating (CR 0–4, 5–10, 11–16, 17+) and split gold with 1 click.
* **Quick NPC Generator (`Tools -> 🎭 Quick NPC Generator`)**: generate complete NPCs with name, race, personality trait, secret, stats, and 1-click map spawning.

### World, Calendar, Weather, Travel, Shops & Quests
* **`World` Tab & `Tools -> Travel Panel`**:
  * Manage the **Calendar of Harptos (Forgotten Realms)** or standard calendar, time of day (with day/night map lighting tint), and **Dynamic Weather** (Clear, Rain, Fog, Storm, Snow).
  * Manage party **Marching Order** (Front, Middle, Rear), travel roles (Scout, Navigator, Forager), ration/water consumption, and **Forced March** Constitution saving throws.
  * Open and broadcast **Merchant Shops** (`shop_ui.py`) and the **Quest Log** (`quest_ui.py`).

### Handouts (Documents/Images) & Audio Soundboard
* **Share Image / Text Handout (`Tools -> Share Image / Share Text Handout`)**: instantly pop up an illustration (NPC portrait, ancient map) or a readable parchment modal on every player's screen.
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
| `/tsmorte` / `/deathsave` / `/ds` | Players (at 0 HP) | Rolls a 5e Death Saving Throw | `/ds` |
| `/vision <name> <radius_hex>` | DM Only | Sets a token's vision radius (in hexes) | `/vision Gildor 12` |

