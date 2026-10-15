"""
Modulo Internazionalizzazione (i18n) per DndOmniCompanion.
Fornisce supporto completo per la scelta della lingua tra Italiano ('it') ed Inglese ('en').
Include persistenza della preferenza in client_data/settings.json, traduzioni per UI,
menu, dialoghi, schede, combattimento, condizioni 5e e abilità.
"""

import os
import json
import threading

# Directory base del progetto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(BASE_DIR, "client_data", "settings.json")

SUPPORTED_LANGUAGES = {
    "it": "Italiano 🇮🇹",
    "en": "English 🇬🇧"
}

DEFAULT_LANGUAGE = "it"
_current_language = DEFAULT_LANGUAGE
_listeners = []
_lock = threading.RLock()


# Dizionario Condizioni 5e (bidirezionale)
CONDITIONS_IT_TO_EN = {
    "Accecato": "Blinded",
    "Affascinato": "Charmed",
    "Assordato": "Deafened",
    "Spaventato": "Frightened",
    "Avvelenato": "Poisoned",
    "Incapacitato": "Incapacitated",
    "Invisibile": "Invisible",
    "Paralizzato": "Paralyzed",
    "Pietrificato": "Petrified",
    "Prono": "Prone",
    "Trattenuto": "Restrained",
    "Stordito": "Stunned",
    "Incosciente": "Unconscious",
    "Sfinimento": "Exhaustion",
    "Concentrazione": "Concentration",
    "Morto": "Dead",
    "Scatto": "Dash",
    "Disimpegno": "Disengage",
    "Schivata": "Dodge",
    "Aiuto": "Help",
    "Afferrato": "Grappled",
    "Privo di Sensi": "Incapacitated",
    "Nascosto": "Hidden",
}

CONDITIONS_EN_TO_IT = {v: k for k, v in CONDITIONS_IT_TO_EN.items()}

# Dizionario Caratteristiche / Abilità 5e
ABILITIES_IT_TO_EN = {
    "FOR": "STR",
    "DES": "DEX",
    "COS": "CON",
    "INT": "INT",
    "SAG": "WIS",
    "CAR": "CHA",
}

ABILITIES_EN_TO_IT = {v: k for k, v in ABILITIES_IT_TO_EN.items()}

ABILITY_NAMES = {
    "it": {
        "FOR": "Forza", "DES": "Destrezza", "COS": "Costituzione",
        "INT": "Intelligenza", "SAG": "Saggezza", "CAR": "Carisma"
    },
    "en": {
        "STR": "Strength", "DEX": "Dexterity", "CON": "Constitution",
        "INT": "Intelligence", "WIS": "Wisdom", "CHA": "Charisma"
    }
}


# Dizionario completo traduzioni UI
STRINGS = {
    "it": {
        # --- Generiche ---
        "app_title": "D&D OmniCompanion",
        "ok": "OK",
        "cancel": "Annulla",
        "save": "Salva",
        "delete": "Elimina",
        "close": "Chiudi",
        "search": "Cerca",
        "filter": "Filtra",
        "edit": "Modifica",
        "add": "Aggiungi",
        "remove": "Rimuovi",
        "clear": "Pulisci",
        "yes": "Sì",
        "no": "No",
        "confirm": "Conferma",
        "error": "Errore",
        "warning": "Attenzione",
        "info": "Informazione",
        "success": "Successo",
        "language": "Lingua",
        "language_name": "Italiano",
        "select_language": "Seleziona Lingua",
        "language_changed_toast": "Lingua impostata su {lang}. I nuovi testi sono attivi!",

        # --- Launcher (main.py) ---
        "launcher_tagline": "Virtual Tabletop & Campaign Manager • 5e",
        "launcher_dm_title": "Dungeon Master",
        "launcher_dm_desc": "Ospita la sessione con campagne preparate, mappe, incontri SRD, nebbia di guerra, audio e musica.",
        "launcher_dm_btn_camp": "⚔️ Avvia con Campagna",
        "launcher_dm_btn_edit": "📜 Prepara / Modifica Campagna",
        "launcher_dm_btn_quick": "⚡ Sessione Rapida (Vuota)",
        "launcher_player_title": "Giocatore",
        "launcher_player_desc": "Unisciti al gruppo, controlla il tuo eroe, lancia incantesimi AoE, tira dadi e parla in voce.",
        "launcher_player_btn_join": "🛡️ Unisciti a Partita",
        "launcher_footer": "DndOmniCompanion • Audio Streaming, Voice UDP & Hex Grid Engine",
        "launcher_lang_btn": "🌐 Lingua: Italiano 🇮🇹",

        # --- Menù Globale ---
        "menu_file": "File",
        "menu_new_campaign": "Nuova Campagna...",
        "menu_load_campaign": "Carica Campagna...",
        "menu_edit_active_campaign": "Editor Campagna Attiva...",
        "menu_load_map": "Carica Mappa...",
        "menu_save_session": "Salva Sessione...",
        "menu_load_session": "Carica Sessione...",
        "menu_exit": "Esci",
        "menu_tools": "Strumenti",
        "menu_loot_gen": "💰 Generatore di Bottino (Loot 5e)",
        "menu_npc_gen": "🎭 Generatore Rapido PNG",
        "menu_map_editor": "Editor Mappe",
        "menu_share_image": "Condividi Immagine (Handout)",
        "menu_share_text": "Condividi Documento testuale",
        "menu_download_maps": "Scarica Mappe Famose",
        "menu_srd_compendium": "Compendio & SRD",
        "menu_encounter_builder": "Preparazione Combattimenti",
        "menu_manuals": "📖 Consulta Manuali di Gioco (PHB, DMG, MM)",
        "menu_travel_panel": "Pannello Viaggio",
        "menu_starter_pack": "Starter Pack Campagna",
        "menu_server": "Server",
        "menu_connect": "Connetti al Server...",
        "menu_reconnect": "Riconnetti Ultimo Server",
        "menu_disconnect": "Disconnetti",
        "menu_library": "Libreria",
        "menu_language": "🌐 Lingua / Language",

        # --- Toolbar Mappa e Tooltips ---
        "tool_center_map": "Centra Mappa",
        "tool_zoom_in": "Ingrandisci Mappa (+)",
        "tool_zoom_out": "Rimpicciolisci Mappa (-)",
        "tool_aoe": "Area di Effetto",
        "tool_measure": "Misura Distanza",
        "tool_manuals": "Consulta Manuali di Gioco (PHB, DMG, MM)",
        "tool_fog": "Nebbia di Guerra (FoW)",
        "tool_door_teleport": "Porta / Teletrasporto",
        "tool_ping": "Invia Ping sulla Mappa",
        "tool_fow_reveal_all": "Rivela Tutta la Mappa",
        "tool_fow_hide_all": "Nascondi Tutta la Mappa",
        "tool_fow_reset": "Ripristina Nebbia Iniziale",

        # --- Pannelli DM ---
        "tab_chat_log": "Chat & Log",
        "tab_party_initiative": "Iniziativa & PG",
        "tab_bestiary": "Bestiario",
        "tab_audio_sfx": "Audio / SFX",
        "btn_start_combat": "Inizia Combattimento",
        "btn_end_combat": "Termina Combattimento",
        "lbl_round": "Round: {round}",
        "btn_next_turn": "Prossimo Turno ⏩",
        "btn_prev_turn": "⏪ Turno Precedente",
        "btn_roll_monster_init": "🎲 Tira Iniziativa Mostri",
        "btn_spawn_npc": "➕ Aggiungi NPC",
        "btn_split_gold": "💰 Dividi Denaro",
        "btn_hide_reveal_npc": "👁️ Nascondi/Rivela PNG",
        "dm_party_header": "--- MEMBRI DEL PARTY ---",
        "dm_npc_header": "--- PNG & MOSTRI ---",

        # --- Pannelli Client / Giocatore ---
        "tab_chat": "Chat",
        "tab_player_controls": "Controlli PG",
        "btn_sheet": "Scheda PG",
        "btn_roll_dice": "Tira Dadi",
        "btn_action": "Azione",
        "btn_travel_actions": "Azioni di Viaggio",
        "btn_request_combat": "Richiedi Combattimento",
        "lbl_voice_status": "Voice Channel: {status}",
        "voice_status_connected": "Connesso",
        "voice_status_disconnected": "Disconnesso",
        "btn_mute": "Muta",
        "btn_unmute": "Smuta",
        "btn_deafen": "Sordo",
        "btn_undeafen": "Ascolta",
        "btn_send": "Invia",
        "chat_input_placeholder": "Scrivi un messaggio o /roll 1d20+5...",
        "hotbar_label": "Macro Rapide (Click Dx: Imposta, Click Sx: Esegui):",

        # --- Scheda Personaggio (Character Sheet) ---
        "sheet_title": "Scheda Personaggio",
        "sheet_tab_stats": "Statistiche & Vita",
        "sheet_tab_skills_saves": "Abilità & Tiri Salvezza",
        "sheet_tab_features": "Privilegi & Tratti",
        "sheet_tab_inventory": "Inventario & Peso",
        "sheet_tab_spellbook": "Grimorio & Slot",
        "sheet_tab_actions": "Azioni Combattimento",
        "sheet_char_name": "Nome:",
        "sheet_char_class": "Classe:",
        "sheet_char_race": "Razza / Specie:",
        "sheet_char_level": "Livello:",
        "sheet_hp": "Punti Ferita (PF)",
        "sheet_temp_hp": "PF Temporanei",
        "sheet_ac": "Classe Armatura (CA)",
        "sheet_initiative": "Iniziativa",
        "sheet_speed": "Velocità",
        "sheet_proficiency": "Bonus Competenza",
        "sheet_death_saves": "Tiri Salvezza Morte",
        "sheet_successes": "Successi",
        "sheet_failures": "Fallimenti",
        "sheet_short_rest": "Riposo Breve",
        "sheet_long_rest": "Riposo Lungo",
        "sheet_level_up": "Aumenta Livello (+)",
        "sheet_tab_weapons": "⚔️ Armi & Attacchi",
        "sheet_tab_inventory": "🎒 Inventario",
        "sheet_tab_features": "🌟 Tratti & Privilegi",
        "sheet_tab_spellbook": "📖 Grimorio",
        "sheet_tab_journal": "📜 Diario & Note",
        "sheet_tab_quick_notes": "📝 Note Rapide",
        "adv_normal": "Normale",
        "adv_advantage": "Vantaggio",
        "adv_disadvantage": "Svantaggio",
        "insp_none": "☆ Nessuna Ispirazione",
        "insp_active": "★ Ispirazione Attiva!",
        "sheet_total_weight": "Peso Totale: {current} / {max} lbs",
        "sheet_encumbered": "(INGOMBRATO!)",
        "sheet_you_are_dead": "☠ SEI MORTO ☠",
        "sheet_active_conditions": "Condizioni Attive:",

        # --- Viaggio & Esplorazione ---
        "travel_title": "Gestione Viaggio ed Esplorazione 5e",
        "travel_order": "Ordine di Marcia",
        "travel_vanguard": "Avanguardia (Fronte)",
        "travel_center": "Centro (Corpo)",
        "travel_rearguard": "Retroguardia (Retro)",
        "travel_pace": "Ritmo di Marcia",
        "travel_pace_slow": "Lento (18 mi/giorno, Furtività + Foraggiamento)",
        "travel_pace_normal": "Normale (24 mi/giorno, Standard)",
        "travel_pace_fast": "Rapido (30 mi/giorno, -5 Percezione)",
        "travel_forced_march": "Marcia Forzata",
        "travel_sustenance": "Sostentamento & Risorse",
        "travel_rations": "Razioni",
        "travel_water": "Acqua",
        "travel_advance_1h": "Avanza 1 Ora",
        "travel_advance_day": "Avanza 1 Giorno (8h Viaggio)",
        "travel_activity": "Attività di Viaggio",

        # --- Manuali di Gioco ---
        "manuals_title": "Compendio & Manuali Ufficiali D&D 5e",
        "manuals_search_placeholder": "Digita per cercare mostro, incantesimo, regola, oggetto...",
        "manuals_all": "Tutte le Categorie",
        "manuals_monsters": "Mostri & Bestiario",
        "manuals_spells": "Incantesimi",
        "manuals_rules": "Regole di Gioco",
        "manuals_items": "Oggetti & Equipaggiamento",
        "manuals_features": "Privilegi di Classe",
        "manuals_source": "Fonte / Manuale:",
        "manuals_count": "Trovate {count} voci corrispondenti",
        "manuals_empty": "Nessuna voce trovata per la ricerca corrente.",

        # --- Combattimento & Azioni 5e ---
        "action_dash": "Scatto (Dash)",
        "action_disengage": "Disimpegno (Disengage)",
        "action_dodge": "Schivata (Dodge)",
        "action_help": "Aiuto (Help)",
        "action_hide": "Nascondersi (Hide)",
        "action_ready": "Preparare Azione (Ready)",
        "action_search": "Cercare (Search)",
        "action_use_object": "Usa Oggetto (Use Object)",
        "action_attack": "Attacco (Attack)",
        "action_cast": "Lancia Incantesimo (Cast Spell)",
    },
    "en": {
        # --- Common ---
        "app_title": "D&D OmniCompanion",
        "ok": "OK",
        "cancel": "Cancel",
        "save": "Save",
        "delete": "Delete",
        "close": "Close",
        "search": "Search",
        "filter": "Filter",
        "edit": "Edit",
        "add": "Add",
        "remove": "Remove",
        "clear": "Clear",
        "yes": "Yes",
        "no": "No",
        "confirm": "Confirm",
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
        "success": "Success",
        "language": "Language",
        "language_name": "English",
        "select_language": "Select Language",
        "language_changed_toast": "Language set to {lang}. New texts are active!",

        # --- Launcher (main.py) ---
        "launcher_tagline": "Virtual Tabletop & Campaign Manager • 5e",
        "launcher_dm_title": "Dungeon Master",
        "launcher_dm_desc": "Host the session with prepared campaigns, maps, SRD encounters, fog of war, audio and music.",
        "launcher_dm_btn_camp": "⚔️ Launch with Campaign",
        "launcher_dm_btn_edit": "📜 Prepare / Edit Campaign",
        "launcher_dm_btn_quick": "⚡ Quick Session (Empty)",
        "launcher_player_title": "Player",
        "launcher_player_desc": "Join the party, control your hero, cast AoE spells, roll dice and voice chat.",
        "launcher_player_btn_join": "🛡️ Join Game",
        "launcher_footer": "DndOmniCompanion • Audio Streaming, Voice UDP & Hex Grid Engine",
        "launcher_lang_btn": "🌐 Language: English 🇬🇧",

        # --- Global Menu ---
        "menu_file": "File",
        "menu_new_campaign": "New Campaign...",
        "menu_load_campaign": "Load Campaign...",
        "menu_edit_active_campaign": "Active Campaign Editor...",
        "menu_load_map": "Load Map...",
        "menu_save_session": "Save Session...",
        "menu_load_session": "Load Session...",
        "menu_exit": "Exit",
        "menu_tools": "Tools",
        "menu_loot_gen": "💰 Loot Generator (5e)",
        "menu_npc_gen": "🎭 Quick NPC Generator",
        "menu_map_editor": "Map Editor",
        "menu_share_image": "Share Image (Handout)",
        "menu_share_text": "Share Text Handout",
        "menu_download_maps": "Download Famous Maps",
        "menu_srd_compendium": "Compendium & SRD",
        "menu_encounter_builder": "Encounter Builder",
        "menu_manuals": "📖 Browse Rulebooks (PHB, DMG, MM)",
        "menu_travel_panel": "Travel Panel",
        "menu_starter_pack": "Campaign Starter Pack",
        "menu_server": "Server",
        "menu_connect": "Connect to Server...",
        "menu_reconnect": "Reconnect to Last Server",
        "menu_disconnect": "Disconnect",
        "menu_library": "Library",
        "menu_language": "🌐 Language / Lingua",

        # --- Map Toolbar and Tooltips ---
        "tool_center_map": "Center Map",
        "tool_zoom_in": "Zoom In (+)",
        "tool_zoom_out": "Zoom Out (-)",
        "tool_aoe": "Area of Effect",
        "tool_measure": "Measure Distance",
        "tool_manuals": "Browse Rulebooks (PHB, DMG, MM)",
        "tool_fog": "Fog of War (FoW)",
        "tool_door_teleport": "Door / Teleport",
        "tool_ping": "Send Ping on Map",
        "tool_fow_reveal_all": "Reveal Full Map",
        "tool_fow_hide_all": "Hide Full Map",
        "tool_fow_reset": "Reset Fog of War",

        # --- DM Panels ---
        "tab_chat_log": "Chat & Log",
        "tab_party_initiative": "Initiative & Characters",
        "tab_bestiary": "Bestiary",
        "tab_audio_sfx": "Audio / SFX",
        "btn_start_combat": "Start Combat",
        "btn_end_combat": "End Combat",
        "lbl_round": "Round: {round}",
        "btn_next_turn": "Next Turn ⏩",
        "btn_prev_turn": "⏪ Previous Turn",
        "btn_roll_monster_init": "🎲 Roll Monster Initiative",
        "btn_spawn_npc": "➕ Add NPC",
        "btn_split_gold": "💰 Split Gold",
        "btn_hide_reveal_npc": "👁️ Hide/Reveal NPC",
        "dm_party_header": "--- PARTY MEMBERS ---",
        "dm_npc_header": "--- NPCS & MONSTERS ---",

        # --- Client / Player Panels ---
        "tab_chat": "Chat",
        "tab_player_controls": "Character Controls",
        "btn_sheet": "Character Sheet",
        "btn_roll_dice": "Roll Dice",
        "btn_action": "Action",
        "btn_travel_actions": "Travel Actions",
        "btn_request_combat": "Request Combat",
        "lbl_voice_status": "Voice Channel: {status}",
        "voice_status_connected": "Connected",
        "voice_status_disconnected": "Disconnected",
        "btn_mute": "Mute",
        "btn_unmute": "Unmute",
        "btn_deafen": "Deafen",
        "btn_undeafen": "Undeafen",
        "btn_send": "Send",
        "chat_input_placeholder": "Type a message or /roll 1d20+5...",
        "hotbar_label": "Macro Hotbar (Right-Click: Edit, Left-Click: Execute):",

        # --- Character Sheet ---
        "sheet_title": "Character Sheet",
        "sheet_tab_stats": "Stats & Hit Points",
        "sheet_tab_skills_saves": "Skills & Saving Throws",
        "sheet_tab_features": "Features & Traits",
        "sheet_tab_inventory": "Inventory & Weight",
        "sheet_tab_spellbook": "Spellbook & Slots",
        "sheet_tab_actions": "Combat Actions",
        "sheet_char_name": "Name:",
        "sheet_char_class": "Class:",
        "sheet_char_race": "Race / Species:",
        "sheet_char_level": "Level:",
        "sheet_hp": "Hit Points (HP)",
        "sheet_temp_hp": "Temp HP",
        "sheet_ac": "Armor Class (AC)",
        "sheet_initiative": "Initiative",
        "sheet_speed": "Speed",
        "sheet_proficiency": "Proficiency Bonus",
        "sheet_death_saves": "Death Saving Throws",
        "sheet_successes": "Successes",
        "sheet_failures": "Failures",
        "sheet_short_rest": "Short Rest",
        "sheet_long_rest": "Long Rest",
        "sheet_level_up": "Level Up (+)",
        "sheet_tab_weapons": "⚔️ Weapons & Attacks",
        "sheet_tab_inventory": "🎒 Inventory",
        "sheet_tab_features": "🌟 Features & Traits",
        "sheet_tab_spellbook": "📖 Spellbook",
        "sheet_tab_journal": "📜 Journal & Notes",
        "sheet_tab_quick_notes": "📝 Quick Notes",
        "adv_normal": "Normal",
        "adv_advantage": "Advantage",
        "adv_disadvantage": "Disadvantage",
        "insp_none": "☆ No Inspiration",
        "insp_active": "★ Inspiration Active!",
        "sheet_total_weight": "Total Weight: {current} / {max} lbs",
        "sheet_encumbered": "(ENCUMBERED!)",
        "sheet_you_are_dead": "☠ YOU ARE DEAD ☠",
        "sheet_active_conditions": "Active Conditions:",

        # --- Travel & Exploration ---
        "travel_title": "5e Travel & Exploration Management",
        "travel_order": "Marching Order",
        "travel_vanguard": "Vanguard (Front)",
        "travel_center": "Center (Main Body)",
        "travel_rearguard": "Rearguard (Back)",
        "travel_pace": "Travel Pace",
        "travel_pace_slow": "Slow (18 mi/day, Stealth + Foraging)",
        "travel_pace_normal": "Normal (24 mi/day, Standard)",
        "travel_pace_fast": "Fast (30 mi/day, -5 Perception)",
        "travel_forced_march": "Forced March",
        "travel_sustenance": "Sustenance & Resources",
        "travel_rations": "Rations",
        "travel_water": "Water",
        "travel_advance_1h": "Advance 1 Hour",
        "travel_advance_day": "Advance 1 Day (8h Travel)",
        "travel_activity": "Travel Activity",

        # --- Rulebooks & Compendium ---
        "manuals_title": "D&D 5e Official Rulebooks & Compendium",
        "manuals_search_placeholder": "Type to search monster, spell, rule, item...",
        "manuals_all": "All Categories",
        "manuals_monsters": "Monsters & Bestiary",
        "manuals_spells": "Spells",
        "manuals_rules": "Game Rules",
        "manuals_items": "Items & Equipment",
        "manuals_features": "Class Features",
        "manuals_source": "Source / Book:",
        "manuals_count": "Found {count} matching entries",
        "manuals_empty": "No entries match the current search.",

        # --- Combat & 5e Actions ---
        "action_dash": "Dash",
        "action_disengage": "Disengage",
        "action_dodge": "Dodge",
        "action_help": "Help",
        "action_hide": "Hide",
        "action_ready": "Ready Action",
        "action_search": "Search",
        "action_use_object": "Use Object",
        "action_attack": "Attack",
        "action_cast": "Cast Spell",
    }
}


def _load_settings():
    """Carica le impostazioni da client_data/settings.json se presente."""
    global _current_language
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                lang = data.get("language")
                if lang in SUPPORTED_LANGUAGES:
                    _current_language = lang
    except Exception as e:
        print(f"[i18n] Errore lettura settings: {e}")


def _save_settings():
    """Salva la lingua corrente in client_data/settings.json."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        data = {}
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["language"] = _current_language
        
        # Scrittura atomica
        tmp_path = SETTINGS_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SETTINGS_PATH)
    except Exception as e:
        print(f"[i18n] Errore salvataggio settings: {e}")


# Inizializza impostazioni all'importazione
_load_settings()


def get_language() -> str:
    """Restituisce il codice della lingua corrente ('it' o 'en')."""
    with _lock:
        return _current_language


def set_language(lang_code: str):
    """
    Imposta la lingua corrente ('it' o 'en'), salva le impostazioni
    e notifica tutti i listener registrati.
    """
    global _current_language
    if lang_code not in SUPPORTED_LANGUAGES:
        return
    with _lock:
        if _current_language == lang_code:
            return
        _current_language = lang_code
        _save_settings()
        listeners_copy = list(_listeners)

    for cb in listeners_copy:
        try:
            cb(_current_language)
        except Exception as e:
            print(f"[i18n] Errore callback lingua: {e}")


def toggle_language() -> str:
    """Inverte la lingua tra 'it' ed 'en' e restituisce il nuovo codice."""
    new_lang = "en" if get_language() == "it" else "it"
    set_language(new_lang)
    return new_lang


def register_language_listener(callback_fn):
    """Registra una funzione da chiamare quando la lingua viene modificata: callback_fn(lang_code)."""
    with _lock:
        if callback_fn not in _listeners:
            _listeners.append(callback_fn)


def unregister_language_listener(callback_fn):
    """Rimuove un listener registrato."""
    with _lock:
        if callback_fn in _listeners:
            _listeners.remove(callback_fn)


def _t(key: str, default: str = None, **kwargs) -> str:
    """
    Traduce la chiave data nella lingua corrente.
    Se la chiave non è presente nella lingua corrente, effettua fallback su Italiano o Inglese.
    Supporta formattazione via **kwargs (es. _t('lbl_round', round=3)).
    """
    lang = get_language()
    val = STRINGS.get(lang, {}).get(key)
    if val is None:
        # Fallback sull'altra lingua o default
        fallback_lang = "it" if lang == "en" else "en"
        val = STRINGS.get(fallback_lang, {}).get(key)
    
    if val is None:
        val = default if default is not None else key

    if kwargs and isinstance(val, str):
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val


def translate_condition(condition: str, target_lang: str = None) -> str:
    """
    Traduce il nome di una condizione D&D 5e nella lingua specificata (o in quella corrente).
    Supporta nomi in italiano e inglese.
    """
    if not target_lang:
        target_lang = get_language()
    
    cond_clean = condition.strip()
    if target_lang == "en":
        return CONDITIONS_IT_TO_EN.get(cond_clean, cond_clean)
    else:
        return CONDITIONS_EN_TO_IT.get(cond_clean, cond_clean)


def is_condition_active(conditions_list, condition_name: str) -> bool:
    """
    Verifica se una condizione è presente in una lista, accettando indistintamente
    il nome in italiano o in inglese.
    Esempio: is_condition_active(player.conditions, 'Prono') -> True anche se contiene 'Prone'.
    """
    if not conditions_list or not condition_name:
        return False
    name_it = CONDITIONS_EN_TO_IT.get(condition_name, condition_name)
    name_en = CONDITIONS_IT_TO_EN.get(condition_name, condition_name)
    for c in conditions_list:
        if c in (name_it, name_en, condition_name):
            return True
    return False


def translate_ability(ability_code: str, target_lang: str = None) -> str:
    """
    Converte il codice abilità (es. 'FOR' <-> 'STR') per la lingua di destinazione.
    """
    if not target_lang:
        target_lang = get_language()
    code = ability_code.strip().upper()
    if target_lang == "en":
        return ABILITIES_IT_TO_EN.get(code, code)
    else:
        return ABILITIES_EN_TO_IT.get(code, code)


def get_ability_name(ability_code: str, lang: str = None) -> str:
    """Restituisce il nome completo dell'abilità (es. 'Forza' o 'Strength')."""
    if not lang:
        lang = get_language()
    code = ability_code.strip().upper()
    if lang == "en":
        en_code = ABILITIES_IT_TO_EN.get(code, code)
        return ABILITY_NAMES["en"].get(en_code, en_code)
    else:
        it_code = ABILITIES_EN_TO_IT.get(code, code)
        return ABILITY_NAMES["it"].get(it_code, it_code)
