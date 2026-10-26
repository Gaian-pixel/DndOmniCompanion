# D&D OmniCompanion 🐉🎲

> 🌐 **Language / Lingua**: 🇬🇧 **[English (README.md)](README.md)** | 🇮🇹 **[Italiano (README_IT.md)](README_IT.md)**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Ruleset: D&D 5e](https://img.shields.io/badge/ruleset-D%26D%205e-red.svg)](https://dnd.wizards.com/)
[![UI: ttkbootstrap](https://img.shields.io/badge/ui-ttkbootstrap-orange.svg)](https://ttkbootstrap.readthedocs.io/)
[![Multiplayer: TCP/UDP](https://img.shields.io/badge/networking-TCP%20%2B%20UDP-green.svg)]()
[![Tests: Passing](https://img.shields.io/badge/tests-273%2F273%20passing-brightgreen.svg)]()
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

### 🖥️ Single-Window Architecture (Mono-Finestra & Center Overlay)
* **Unified In-Place Launcher**: All secondary launcher tools (*Character Manager*, *Creation Wizard*, and *Campaign Editor*) render seamlessly in-place within the primary window, equipped with an intuitive `[ ← Torna al Menu Principale / Back to Main Menu ]` top banner, eliminating floating window clutter.
* **Character Sheet as Center Overlay in VTT**: Within the game client, the Character Sheet opens directly as a sleek floating overlay in the middle of the battlemap canvas (`Center Overlay`), toggled via `📋 Character Sheet` or the **`C`** hotkey.
* **Instant Dismissal via `Esc`**: The overlay closes instantly upon pressing **`Esc`** or clicking the top-right `✖`, returning immediate full focus to map navigation.
* **Flexible Docking & Detaching**:
  * Button **`[ ◱ Stacca Finestra / Detach Window ]`**: Immediately converts the overlay into an independent floating Tkinter window, ideal for dual-monitor battlestations or side-by-side management.
  * Button **`[ ◰ Riaggancia alla Mappa / Dock to Map ]`**: Re-embeds the detached window right back into the main VTT as a central canvas overlay with zero state loss.

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
* **Dynamic Light Sources & Portable Illumination (PHB p. 183)**:
  * **Quick HUD Toggle `[ 🕯️ ]`**: Located in the Hero Summary Card to toggle light sources on/off with 1 click.
  * **Official D&D 5e Presets**: Right-click context menu with **Torch** ($20\text{ ft}$ bright / $20\text{ ft}$ dim, 8-hex radius, warm amber glow), **Hooded Lantern** ($30\text{ ft} / 30\text{ ft}$, 12-hex radius), **Hooded Lantern (Dim)** (narrow 5 ft beam, 1-hex radius), and **Light Spell** ($20\text{ ft} / 20\text{ ft}$, 8-hex radius with cyan aura).
  * **Dynamic FoW Sync**: Turning lights on instantly unveils Fog of War based on $\max(\text{vision\_radius}, \text{light\_radius})$.
* **AoE Spells & Templates (`[ 💥 ]`)**: Spheres, Cones ($60^\circ / 90^\circ$), Lines, and Magical Darkness Spheres with geometric grid previews and 1-click casting.
* **Animated Map Ping**: Middle-click (or `[ 📍 ]` tool) to drop an animated broadcast marker for all connected players.
* **Token Condition Badges**: High-contrast visual status badges rendered directly on map tokens covering all 5e conditions (`💀` Dead, `💤` Unconscious, `🧎` Prone, `🧠` Concentrating, `🛡️` Dodge, `🤝` Help, `🟢` Poisoned, `🙈` Blinded, `⚡` Paralyzed, `🕸️` Restrained, `⛓️` Grappled, `👻` Invisible, `😱` Frightened, `💫` Stunned, `🩹` Stabilized, `🔇` Deafened, `💖` Charmed, `🗿` Petrified, `🔥` Rage).

### ⚔️ D&D 5e Combat Engine & Context-Aware Turn Economy
* **Context-Aware Turn Economy (Exploration vs. Combat)**:
  * **Out of Combat (`🧭 Exploration Mode - Free Movement`)**: Players move, attack, and cast spells freely without consuming or locking turn badges; the movement bar displays per-move speed.
  * **In Combat (`Turn Economy`)**: Strict server-synchronized tracking of **⚡ Action**, **✨ Bonus Action**, **🛡️ Reaction**, and **👟 Movement**, resetting automatically at the start of the combatant's turn and when combat starts or ends.
* **Critical Successes (`🌟 Natural 20`) & Critical Failures (`💀 Natural 1`)**:
  * **Attack Rolls**: `Natural 20` is an automatic hit that automatically doubles all damage dice; `Natural 1` is an automatic miss.
  * **Saving Throws, Ability/Skill Checks & `1d20` Rolls**: Gold/crimson chat banners and broadcast Toast notifications (`CRITICAL_ROLL_BROADCAST`) across all connected clients.
* **Tactical 5e RAW Cover System (PHB p. 196)**:
  * **Quick Selector in Attack & Save Dialogs**: Choose explicit cover for targeted entities:
    * `Automatic Cover`: Geometric LoS raycasting (`hex_linedraw`) detecting intervening walls, closed or locked doors (`get_effective_map_walls`), half cover obstacles, and living creatures (excluding corpses and GM-layer tokens).
    * `No Cover`: Standard AC.
    * `Half Cover`: $+2$ to target AC and $+2$ to Dexterity saving throws.
    * `Three-Quarters Cover`: $+5$ to target AC and $+5$ to Dexterity saving throws.
    * `Total Cover`: Target cannot be targeted directly; attacks are completely blocked.
* **Environmental Combat Modifiers (Weather & Difficult Terrain)**:
  * **Weather (DMG p. 109-110)**: Violent storms and dense fog impose Disadvantage on ranged attacks (> 1 hex); torrential rain and blizzards impose Disadvantage on long-range attacks.
  * **Difficult Terrain**: Attacking from unstable footing (Ice, Rubble, Swamp, Mud) imposes Disadvantage; striking targets entangled in Briars or trapped in Mud grants **Advantage**.
  * **Darkness & Darkvision Rules (PHB p. 194-195)**: Attacking from darkness with Darkvision (or attacking a torch-bearing enemy) grants **Advantage** (*Unseen Attacker*); attacking an unseen target imposes **Disadvantage**; mutual darkness cancels out both to a normal roll. Note: Dragonborn do not possess innate darkvision per 5e RAW.
* **Automated Opportunity Attacks & Out-of-Turn Reactions**: Detects when a combatant leaves hostile melee reach without having taken the *Disengage* action, bypassing strict turn locks with `is_reaction=True` to seamlessly resolve out-of-turn reactions.
* **Auto-Critical Hits on Incapacitated / Paralyzed Targets (PHB p. 291-292)**: Any attack roll that hits a creature with the *Unconscious* or *Paralyzed* condition within 5 feet (1 cell) automatically scores a Critical Hit with doubled damage dice.
* **Bilingual Damage Resistances & Vulnerabilities**: Automated two-way mapping between English and Italian damage types (`fire` $\leftrightarrow$ `fuoco`, `radiant` $\leftrightarrow$ `radioso`, `slashing` $\leftrightarrow$ `tagliente`, etc.) applying exact halving or doubling of damage.
* **Strict Concentration & Upcasting (PHB p. 201-204)**:
  * Casting a new concentration spell from the Spellbook automatically drops and broadcasts the termination of any existing concentration.
  * Taking damage while concentrating automatically triggers a Constitution saving throw ($\text{DC} = \max(10, \lfloor\text{Damage}/2\rfloor)$); failure breaks concentration and cleans up linked persistent AoE zones.
  * **Upcasting**: Select higher-level spell slots to empower spells according to 5e scaling rules.
* **Persistent Death Saves, 0 HP Damage & Instant Death (PHB p. 197)**:
  * Complete 0 HP handling: taking damage at 0 HP adds 1 death save failure (or 2 failures on a critical hit).
  * Accumulating 3 failures marks the character with permanent *Dead* (`💀`) status and spawns an interactive lootable corpse on the map canvas.
  * Receiving healing at 0 HP restores health, completely resets death save successes/failures to 0, and automatically clears the *Unconscious* and *Stabilized* conditions.
  * Instant Death triggers if excess damage equals or exceeds maximum HP.
* **Boss Mechanics RAW (MM p. 11)**:
  * **Legendary Actions**: Up to 3 actions per round spendable at the end of another creature's turn, automatic DM reminders, and full pool reset at the start of the boss's turn.
  * **Lair Actions (Initiative 20)**: Automatic round notification and DM prompt at Initiative count 20 for bosses with an active lair.
  * **Legendary Resistances**: Up to 3/day to turn a failed save into a success.

### 🧙‍♂️ Character Creation, Sheet & Progression
* **Baldur's Gate Styled Wizard with Master-Detail Compendiums**:
  * **Master-Detail Races Compendium (9 Core 5e Races)**: Accessible via the `[ 📊 Tabella Comparativa ]` button in Step 1 of the Creation Wizard:
    * **Live Search & Quick Filter Pills**: Real-time search across any trait, stat, or class plus filter buttons (`[Tutte (9)]`, `[🛡️ Resistenze]`, `[👁️ Scurovisione]`, `[🏃 Taglia Piccola]`, `[⚔️ Mischia / Forza]`, `[✨ Magiche / Carisma]`).
    * **Master-Detail Split-View Layout**: Left comparative table (6 columns: Race with icon, Stat Bonuses, Key Traits, Damage Resistances & Defenses, Size/Speed, Recommended Classes) with bidirectional scrolling, and right reactive preview card.
    * **Authentic 5e Rules & Lore**: Comprehensive defensive traits (Hellish Fire Resistance, Dwarven Resilience vs Poison, Fey Ancestry with Sleep Immunity, Gnome Cunning vs Mental Magic, Relentless Endurance at 1 HP, Lucky), Class Synergies, Lifespan, full mechanical trait descriptions, and subraces with double-click selection.
  * **Classes Comparison Compendium (12 Core 5e Classes)**: Accessible in Step 2 with category filters (`[All]`, `[Martial]`, `[Spellcaster]`, `[Hybrid]`, `[Expert]`), Hit Dice (d6–d12), Primary Abilities, Saving Throws, Party Role, Quick Build recommendations, starting equipment preview, and subclasses.
  * **Assisted Level-Up**: Automatic retrieval of class features, hit dice, and spell slot progressions from the 5e SRD compendium, including Artificer (slots from 1st level) and 3rd-Casters (Eldritch Knight / Arcane Trickster starting at 3rd level). Enforces strict ASI ability score capping at 20, duplicate ability prevention, and automatic class feature synchronization into `features_list` preserving all traits upon saving.
* **Character Avatar & Automatic Tactical Map Token**:
  * Players (and DMs for NPCs and monsters) can upload a portrait for their character.
  * The uploaded portrait automatically becomes the **tactical circular token on the map canvas** with high-definition antialiased rendering, faction/class color ring, and dynamic scale based on Creature Size (Tiny to Gargantuan).
* **Anti-Cheat DM Approval Rules & Sheet Integrity (Online & Offline)**:
  * **Restricted Self-Addition/Removal from SRD**: Players cannot arbitrarily add or remove items or spells from their inventory or spellbook via the SRD browser without DM authorization.
  * This rule strictly applies **both during live multiplayer sessions and offline during character management**, safeguarding sheet integrity.
  * **Markdown Journal & Notes with DM Validation**: Native visual rendering for Markdown-formatted text (`**bold**`, `*italics*`, bullet lists, headers) and DM approval requirement for saving campaign chronicle notes.
  * **Organized Traits & Features View**: Clean separation between innate biological racial traits, active class features, and spendable resources.
* **Inventory, Currencies, Containers & Spendable Consumables**:
  * **Currency Sync & Correct Weight**: Dynamic, true-to-life inventory weight calculation including RAW coin weight ($50\text{ coins} = 1\text{ lb}$) with bidirectional synchronization between item lists and the top currency table (`CP`, `SP`, `EP`, `GP`, `PP`).
  * **Convenient Container Management**: Fast assignment to `🎒 Backpack`, `⚔️ Equipped`, `🔮 Bag of Holding`, `✨ Handy Haversack`, or `🐴 Mount`, with tare vs contents weight tracking.
  * **Spendable Consumables**: Quick `[-1]` / `[+1]` buttons directly on the inventory row for ammunition (arrows, bolts), rations, torches, and potions to spend resources on the fly, with instant HP and server synchronization on healing potion consumption.
* **Short Rest Hit Dice Spending (RAW PHB p. 186)**:
  * Interactive modal `ShortRestDialog` featuring current/max HP, progress health bar, and remaining Hit Dice count.
  * Single-click button to **spend 1 Hit Die at a time** ($1\text{dY} + \text{CON Mod}$, min 1 healed), instantly updating sheet and chat log.
  * "Spend All" button to spend all available dice or finish rest.
  * Long Rest automatically restores full HP and regains half of the character's total Hit Dice ($\max(1, \lfloor\text{Total}/2\rfloor)$).
* **Special Class Resources System**: Automatic population and tracking of Ki Points, Rage, Bardic Inspiration, Wild Shape, Channel Divinity, Action Surge, Second Wind, Sorcery Points, etc., with automated Short/Long Rest recovery.
* **Hero Summary Card & Interactive Character Sheet**:
  * Always-visible sidebar summary card with responsive HP bar, AC, effective Speed (`ft` or `m`), Initiative, light toggle `[ 🕯️ ]`, and quick `[ 🎒 ]` button to drop backpack.
  * Full tabbed sheet: **Combat**, **Stats & Skills** (with Proficiency & Expertise $2\times\text{PB}$), **Weapons & Attacks**, **Inventory & Encumbrance** ($\text{STR} \times 15\text{ lbs}$), **Spellbook & Spell Slots (1–9)** with **Spell Upcasting** modal, **Features & Journal**.
* **5e Backpacks, Containers & Variant Encumbrance (RAW PHB p. 143, 176, 190)**:
  * **Per-Item Location / Compartment**: Assign items to `🎒 Backpack`, `⚔️ Equipped / On Person`, `🔮 Bag of Holding` (500 lbs capacity, internal weight does not burden character), `✨ Heward's Handy Haversack` (120 lbs capacity, 5 lbs bag weight), or `🐴 Saddlebag / Mount`.
  * **Tactical "Drop Backpack" Action**: 1-click quick toggle (`[ 🎒 Drop Backpack ]` $\leftrightarrow$ `[ 🎒 Pick Up Backpack ]`) as a free Object Interaction; instantly excludes backpack gear weight from carried load, announcing the action to table chat and restoring full combat speed.
  * **5e Variant: Encumbrance Rule**: Full Strength-based thresholds ($\text{STR} \times 5$, $\text{STR} \times 10$, $\text{STR} \times 15$), RAW coin weight (50 coins = 1 lb), and dynamic penalties: *Normal*, *Encumbered* (-10 ft / -3 m speed), *Heavily Encumbered* (-20 ft / -6 m speed, Disadvantage on STR/DEX/CON attack rolls, checks, and saves), and *Overloaded* (speed drops to 0).
* **Character Sheet Export (Official D&D 5e PDF & JSON Data)**: Dedicated modal dialog to choose between **Official PDF** (prompts for the blank 3-page D&D 5e PDF template in input, generating a fully filled sheet ready for print or sharing) and **JSON** (full raw backup for campaign import/export).
* **Peer-to-Peer Trading & Macro Hotbar**: Secure direct item/gold transfers between allies with atomic slot clearing preventing item duplication, and a 10-slot customizable quick macro bar supporting `/roll` and `/r` dice formulas.

### 📜 Dungeon Master Operations Suite
* **Live DMG p. 82 Encounter Balancer**: Real-time evaluation of encounter difficulty (**Trivial**, **Easy**, **Medium**, **Hard**, **Deadly**) with monster count XP multipliers.
* **Campaigns, Scenes & Starter Pack Manager**: Prepare acts, scenes linked to maps/monsters for 1-click deployment, and configure starting equipment automatically granted to new PCs.
* **Session Log / Chronicle Export**: Export complete session logs (rolls, tactical actions, chat, whispers) to Markdown (`.md`) or HTML from `File -> Export Session Log`.
* **Shared Quest Log & Document Handouts**:
  * Quest tracking (`Library ➔ Quest Log`) synchronized across all players with objective descriptions, quest givers, rewards, and completion status.
  * Parchment handouts and illustrations broadcast directly to all connected players with a parchment viewer dialog.
* **Procedural Generators**: 5e Loot Generator and Quick NPC Generator.
* **Compendium & SRD Split View and Authentic 5e Statblock**:
  * **Master-Detail Split View Interface**: Interactive two-pane layout (`server/compendium_ui.py`) with a searchable/filterable list on the left and full 5e statblock preview on the right, equipped with contextual primary action buttons (*Spawn Monster on Map*, *Add to Spellbook*, *Equip Item*).
  * **5e Statblock Component (`components/statblock_view.py`)**: High-fidelity Dark Fantasy rendering complete with badges for Armor Class, Hit Points, and Speed, 6 ability score table with real-time calculated modifiers, saving throws, skills, senses, languages, Challenge Rating (CR), traits, highlighted action dice expressions, reactions, and legendary actions.
  * **Multi-Criteria Fast Filters**: Toggle buttons for Challenge Rating tiers (All, CR 0–1/2, 1–4, 5–9, 10–14, 15–19, 20+), Creature Type (All, Dragon, Undead, Humanoid, Beast, Aberration, Construct, Fey, Monstrosity, Giant, Celestial, Fiend...), Magic Item Rarity (Common, Uncommon, Rare, Very Rare, Legendary), and Spell Schools.
  * **Deterministic AC & Speed Normalization (No raw `[{}]`)**: Robust normalization parsing complex armors (e.g., natural armor, shield) and secondary movement speeds (fly, swim, burrow, climb), guaranteeing clean statblocks across both official SRD and PDF-extracted entries.
  * **Mini-Statblock in DM Bestiary Panel (`server/dm_bestiary_panel.py`)**: CR and creature type fast filters with a compact visual statblock card in the DM sidebar and 2-click instant spawning.
* **Offline PDF Rulebooks & Command Palette (`Ctrl+K`)**: Instant search across indexed official 5e PDF rulebooks, rules, monsters, spells, and map tokens.
* **Overland Travel, Calendar, Weather & Shops**: Marching order, travel roles, rations/water, forced march saves, interactive fantasy calendar, and merchant shops.
* **Soundboard & Integrated UDP Voice Chat**: Low-latency voice streaming with Mute/Deafen controls (`[ 🎤 ]` / `[ 🎧 ]`), resilient Windows UDP socket handling (`SIO_UDP_CONNRESET`) preventing ICMP crashes on client disconnects, and synchronized audio soundboard.

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

### 📦 Download Pre-Built Executables (Windows & Linux)
You can download ready-to-run standalone packages directly from the [GitHub Releases](https://github.com/Gaian-pixel/DndOmniCompanion/releases) section:
* **Windows (64-bit)**: Download `DndOmniCompanion-v*-win64.zip`, extract anywhere and launch `DndOmniCompanion.exe`.
* **Linux (x86_64)**: Download `DndOmniCompanion-v*-linux-x64.tar.gz`, extract anywhere and run `./run.sh` (or `./DndOmniCompanion`).

---

### 💻 Running from Source

#### Prerequisites
* **Python 3.9 or higher** (compatible up to Python 3.14)
* On Linux, ensure Tkinter and audio development libraries are installed:
  ```bash
  sudo apt-get install python3-tk libportaudio2 libsndfile1
  ```
* Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```

#### Launching the Application
Run the unified launcher from the project root:
* **Windows**:
  ```bash
  python main.py
  ```
* **Linux**:
  ```bash
  chmod +x run_linux.sh
  ./run_linux.sh
  # or: python3 main.py
  ```
From the startup launcher choose:
1. **Dungeon Master**: Starts the TCP server (`53911`) and UDP Voice server (`53912`) and opens the DM Dashboard (with campaign, campaign editor, or quick session).
2. **Player**:
   * **👤 Character Manager (Offline)**: Create, view, duplicate, delete and export character sheets (Official PDF / JSON backup) completely offline without needing a server connection.
   * **✨ Create Character (Wizard)**: Launch the Baldur's Gate 3 inspired step-by-step Level 1 character creation wizard directly.
   * **🛡️ Join Game**: Launches the Player VTT client to connect to the Dungeon Master's IP address.

---

## 🎮 Quick Controls & Shortcuts

### Map Canvas Controls & Keyboard Shortcuts
| Input / Tool | Action |
|---|---|
| **`C`** | Toggle **Character Sheet** (Center Overlay / Re-dock) |
| **`Esc`** | Close Character Sheet or active Overlay |
| **`F11`** | Toggle **Fullscreen** mode |
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
| `/broll <formula>` or `/gmroll <formula>` | Secret roll visible only to the Dungeon Master | `/broll 1d20+5 stealth` |
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
│   ├── dm_automation_panel.py      # Campaign Conduction Panel (3 styles) & DM Pending Actions Dock
│   ├── dm_travel_dialog.py         # Overland Travel, Marching Order & Rations Dialog
│   ├── dm_entity_dialogs.py        # Token Sizing, Magical Auras & Entity Config Dialogs
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
│   ├── statblock_view.py           # Authentic 5e Statblock card for monsters, spells, and magic items
│   ├── calendar_ui.py              # Fantasy calendar and dynamic weather
│   ├── quest_ui.py                 # Quest Log interface
│   └── shop_ui.py                  # Merchant & Shop interface
├── docs/                           # User and technical documentation (EN + IT)
│   ├── USER_GUIDE.md               # Complete User Guide (English)
│   ├── GUIDA_ALL_UTILIZZO.md       # Manuale completo all'utilizzo (Italiano)
│   ├── OPERATIONAL_GUIDE.md        # System & Operational Manual (English)
│   └── GUIDA_OPERATIVA.md          # Manuale operativo e architettura (Italiano)
├── tests/                          # Automated testing suite (273 passing tests)
│   ├── simulate_4player_campaign.py# Live 4-player + DM campaign simulation (11 phases)
│   ├── simulate_game_session.py    # End-to-end multiplayer simulation (53 phases)
│   ├── test_mono_finestra.py       # Single-window, overlay, and docking architecture tests
│   ├── test_authentic_5e.py        # Authentic 5e RAW rules test suite
│   ├── test_ui_smoke.py            # Smoke tests across all graphical windows
│   └── ... (28 modular unit and integration test suites)
└── main.py                         # Unified launcher (DM Host / Player Client)
```

---

## 🧪 Automated Testing & Verification

All **273 automated tests** pass with 100% success and 0 failures:

```powershell
# 1. Comprehensive Unit Tests (296 tests: ruler, criticals, single-window, turn economy, units, inventory, races/classes)
$env:DND_MOCK_AUDIO="1"; python -m unittest discover tests

# 2. Authentic 5e RAW Rules Test Suite (Doors, Lockpicking, Room Pins, Reactions, Shield, Evasion, Sneak Attack, Blind Rolls)
$env:DND_MOCK_AUDIO="1"; python -m unittest tests/test_authentic_5e.py

# 3. Single-Window Architecture Tests (In-place frames, canvas overlay, docking/detaching, hotkeys C/Esc)
$env:DND_MOCK_AUDIO="1"; python -m unittest tests/test_mono_finestra.py

# 4. Full UI Smoke Tests across all 19 DM Server & Player Client screens
$env:DND_MOCK_AUDIO="1"; python tests/test_ui_smoke.py --no-screens

# 5. Full 53-Phase End-to-End Multiplayer Simulation
$env:DND_MOCK_AUDIO="1"; python tests/simulate_game_session.py

# 6. Campaign & Scene System Tests
$env:DND_MOCK_AUDIO="1"; python -m unittest tests/test_campaign_system.py

# 7. Live 4-Player + DM Campaign Simulation (11 tactical phases: join, traps, turn combat, opportunity attacks, death saves/loot, P2P trading, level-up, short rest)
$env:DND_MOCK_AUDIO="1"; python tests/simulate_4player_campaign.py
```

---

## 📜 License & Acknowledgments

* Designed for the **Dungeons & Dragons 5th Edition (D&D 5e)** ruleset under the Open Game License (OGL) / System Reference Document 5.1 (SRD5).
* Built with [Python](https://www.python.org/), [ttkbootstrap](https://ttkbootstrap.readthedocs.io/), and [Pillow](https://python-pillow.org/).