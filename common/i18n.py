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

# Dizionario Abilità / Skills 5e
SKILLS_IT_TO_EN = {
    "Acrobazia": "Acrobatics",
    "Addestrare Animali": "Animal Handling",
    "Arcano": "Arcana",
    "Atletica": "Athletics",
    "Furtività": "Stealth",
    "Indagare": "Investigation",
    "Inganno": "Deception",
    "Intimidire": "Intimidation",
    "Intrattenere": "Performance",
    "Intuizione": "Insight",
    "Medicina": "Medicine",
    "Natura": "Nature",
    "Percezione": "Perception",
    "Persuasione": "Persuasion",
    "Prestidigitazione": "Sleight of Hand",
    "Religione": "Religion",
    "Sopravvivenza": "Survival",
    "Storia": "History"
}

SKILLS_EN_TO_IT = {v: k for k, v in SKILLS_IT_TO_EN.items()}


def translate_skill(skill_name: str, target_lang: str = None) -> str:
    """Traduce il nome di un'abilità 5e tra Italiano ed Inglese."""
    if not target_lang:
        target_lang = get_language()
    clean = skill_name.strip()
    if target_lang == "en":
        return SKILLS_IT_TO_EN.get(clean, clean)
    else:
        return SKILLS_EN_TO_IT.get(clean, clean)


WEATHER_IT_TO_EN = {
    "Sereno": "Clear",
    "Pioggia": "Rain",
    "Tempesta": "Storm",
    "Neve": "Snow",
    "Nebbia": "Fog"
}
WEATHER_EN_TO_IT = {v: k for k, v in WEATHER_IT_TO_EN.items()}

def translate_weather(weather_name: str, target_lang: str = None) -> str:
    """Traduce la condizione meteorologica tra IT ed EN."""
    if not target_lang:
        target_lang = get_language()
    clean = weather_name.strip()
    if target_lang == "en":
        return WEATHER_IT_TO_EN.get(clean, clean)
    else:
        return WEATHER_EN_TO_IT.get(clean, clean)


PERIODS_IT_TO_EN = {
    "Mattina": "Morning",
    "Pomeriggio": "Afternoon",
    "Sera": "Evening",
    "Notte": "Night"
}
PERIODS_EN_TO_IT = {v: k for k, v in PERIODS_IT_TO_EN.items()}

def translate_period(period_name: str, target_lang: str = None) -> str:
    """Traduce il periodo della giornata tra IT ed EN."""
    if not target_lang:
        target_lang = get_language()
    clean = period_name.strip()
    if target_lang == "en":
        return PERIODS_IT_TO_EN.get(clean, clean)
    else:
        return PERIODS_EN_TO_IT.get(clean, clean)



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
        "tool_command_palette": "Tavolozza Comandi Rapida (Ctrl+K)",
        "cmd_palette_title": "Tavolozza Comandi & Ricerca Rapida",
        "cmd_palette_placeholder": "🔍 Cerca regole, mostri, token, incantesimi o scrivi /roll...",
        "cmd_palette_hint": "↑ / ↓ Naviga  •  ↵ Seleziona / Esegui  •  Esc Chiudi",
        "cmd_type_roll": "🎲 Tiro Dadi",
        "cmd_type_token": "📍 Token Mappa",
        "cmd_type_rule": "📖 Regola 5e",
        "cmd_type_action": "⚡ Azione Rapida",

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
        "sheet_currency": "Valuta",
        "sheet_item": "Oggetto",
        "sheet_weight_col": "Peso (lbs)",
        "sheet_attunement": "Sintonia",
        "sheet_empty_slot": "Vuoto",
        "sheet_search_compendium": "Cerca nel Compendio",
        "sheet_give_gold_btn": "🪙 Dona Oro a Compagno",
        "sheet_spell_slots_header": "Slot Incantesimo (Max / Correnti)",

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

        # --- Controlli Navigazione & Party Giocatore ---
        "party_members_header": "👥 Compagnia di Avventura",
        "chat_tab_global": "Globale",
        "chat_tab_system": "Sistema",
        "status_disconnected": "Stato: Disconnesso",
        "status_connected": "Stato: Connesso",
        "no_character": "Nessun Personaggio",
        "adventurer_lvl": "Avventuriero • Livello {lvl}",
        "select_or_create_char": "Seleziona o crea un PG",
        "class_adventurer": "Avventuriero",
        "char_level_prefix": "Livello",
        "exhaustion_prefix": "Indebolimento",
        "not_in_combat": "Non in Combattimento",

        # --- Economia Turno & Azioni Rapide ---
        "turn_economy": "⚡ Economia Turno",
        "turn_economy_reset": "↺ Reset",
        "tooltip_reset_economy": "Ripristina le risorse del turno",
        "btn_act": "⚔️ Azione",
        "tooltip_act": "Azione Standard: clicca per contrassegnare come spesa/disponibile",
        "btn_bonus": "✨ Bonus",
        "tooltip_bonus": "Azione Bonus: clicca per contrassegnare come spesa/disponibile",
        "btn_react": "🛡️ Reaz",
        "tooltip_react": "Reazione: clicca per contrassegnare come spesa/disponibile",
        "lbl_movement": "👟 Movimento: {used} / {total} ft (Rim: {rem} ft)",
        "btn_dash": "🏃 Scatto",
        "tooltip_dash": "Spende l'Azione per raddoppiare il movimento in questo turno",
        "btn_disengage": "💨 Disimpegno",
        "tooltip_disengage": "Spende l'Azione: non provochi attacchi d'opportunità uscendo dalla portata di un nemico",
        "btn_dodge": "🛡️ Schivata",
        "tooltip_dodge": "Spende l'Azione: gli attacchi contro di te avranno svantaggio e hai vantaggio ai TS su Destrezza",
        "btn_help": "🤝 Aiuto",
        "tooltip_help": "Spende l'Azione: clicca poi un bersaglio per conferire Vantaggio al prossimo attacco alleato",

        # --- Bottoni Azione Scheda Giocatore ---
        "change_active_char": "Cambia Scheda Personaggio:",
        "btn_sheet": "📜 Scheda Personaggio",
        "btn_roll_dice": "🎲 Tira Dadi",
        "btn_action": "⚔️ Azione (Attacco / Cura / Danno)",
        "btn_short_rest": "☕ Riposo Breve (Dadi Vita)",
        "lbl_class_features": "Privilegi di Classe",
        "btn_second_wind": "💨 Secondo Fiato",
        "tooltip_second_wind": "Guerriero (1/Riposo Breve): recupera 1d10 + Livello HP come Azione Bonus",
        "btn_action_surge": "⚡ Azione Furente",
        "tooltip_action_surge": "Guerriero (1/Riposo Breve): ottieni un'Azione aggiuntiva in questo turno",
        "btn_rage": "🩸 Ira Barbarica",
        "tooltip_rage": "Barbaro: entra in Ira (+2 danni mischia, resistenza a contundente, perforante e tagliente)",
        "btn_travel_actions": "🧭 Azioni di Viaggio",
        "btn_manuals": "📖 Consulta Manuali di Gioco",
        "btn_request_combat": "⚔️ Richiedi Combattimento",
        "btn_end_turn": "⏹ Termina Turno",

        # --- Tooltip Audio & Voce ---
        "tooltip_mute_audio": "Muta/Smuta Audio di gioco",
        "tooltip_deafen": "Muta/Smuta Cuffie",
        "tooltip_mute_mic": "Muta/Smuta Microfono",
        "voice_server_active": "🟢 Voice Server: Attivo",

        # --- Tab & Controlli DM ---
        "tab_world": "Mondo",
        "tab_audio_sfx": "Audio / SFX",
        "dm_combatants_header": "⚔️ Avventurieri & Mostri",
        "lbl_round_num": "⚔️ ROUND {round}",
        "btn_prev_turn": "⬅ Turno Prec.",
        "btn_next_turn": "Turno Succ. ➡",
        "btn_hide_reveal": "👁 Nascondi / Rivela PNG",
        "npc_actions_header": "Azioni PNG Selezionato",
        "btn_start_combat": "⚔️ Inizia Combattimento",
        "btn_end_combat": "⏹ Termina Combattimento",
        "btn_deploy_prepared": "⚡ Schiera Incontro Preparato",
        "btn_roll_all_npcs": "🎲 Tira Iniziativa per Tutti i Mostri",
        "lbl_balance_waiting": "⚔️ Bilanciamento 5e: In attesa dati",
        "btn_spawn_png": "Spawna PNG",
        "btn_add_manual_npc": "+ Aggiungi NPC/Mostro Manuale",
        "btn_split_loot": "💰 Dividi Denaro (Party Loot)",
        "lbl_bestiary_header": "📖 Bestiario (Monster Manual 2025 & SRD):",
        "lbl_bestiary_preview_default": "Seleziona un mostro per visualizzare le statistiche.",
        "btn_spawn_on_map": "⚔️ Spawna sulla Mappa",
        "btn_full_sheet": "📖 Scheda Completa",
        "btn_dice": "🎲 Dadi",

        # --- Scheda Personaggio Esecuzione ---
        "sheet_attributes": "ATTRIBUTI",
        "sheet_skills": "ABILITÀ",
        "sheet_saving_throws": "TIRI SALVEZZA",
        "sheet_armor_class": "CA",
        "sheet_initiative_short": "INIZ",
        "sheet_speed_short": "VEL",
        "sheet_dice_roll": "Tiro Dado:",
        "sheet_levelup_btn": "🌟 Sali di Livello!",
        "sheet_short_rest_btn": "☕ Riposo Breve",
        "sheet_long_rest_btn": "🌙 Riposo Lungo",
        "sheet_name": "Nome:",
        "sheet_campaign": "Campagna:",
        "sheet_class": "Classe:",
        "sheet_level": "Livello:",
        "sheet_race": "Razza:",
        "sheet_exp": "EXP:",

        # --- DM Mappa & Barra FoW ---
        "dm_tactical_map": "🗺 Mappa Tattica",
        "fow_tool_label": "Strumento:",
        "fow_mode_move": "Muovi Token",
        "fow_mode_erase": "Cancella Nebbia",
        "fow_mode_draw": "Disegna Nebbia",
        "fow_player_view": "Vista PG",
        "fow_send_btn": "Invia Nebbia",
        "fow_options_btn": "Opzioni FoW",
        "fow_menu_enable": "Abilita Sistema Nebbia",
        "fow_menu_hide_all": "Oscura Tutta la Mappa (Nascondi Tutto)",
        "fow_menu_reveal_all": "Rivela Tutta la Mappa (Rivela Tutto)",

        # --- Pillole di Stato & Meteo ---
        "period_morning": "Mattina",
        "period_afternoon": "Pomeriggio",
        "period_evening": "Sera",
        "period_night": "Notte",
        "weather_clear": "Sereno",
        "weather_rain": "Pioggia",
        "weather_storm": "Tempesta",
        "weather_snow": "Neve",
        "weather_fog": "Nebbia",
        "status_exploration": "🕊️ Esplorazione",
        "status_in_combat": "⚔️ In Combattimento (R{round})",
        "campaign_none": "🏰 Campagna: Nessuna (Sessione Rapida)",
        "campaign_active": "🏰 Campagna: {name}",

        # --- Tooltips Strumenti DM ---
        "tool_fog_of_war": "Nebbia di Guerra",
        "tool_teleport": "Aggiungi/Rimuovi Teletrasporto",
        "tool_clear_aoe": "Pulisci Aree di Effetto",

        # --- Tab Mondo DM ---
        "time_mgmt_header": "Gestione Tempo",
        "time_day_display": "Giorno {day} - {time} ({period})",
        "time_add_1h": "+1 Ora",
        "time_add_8h": "+8 Ore (Riposo)",
        "time_add_1d": "+1 Giorno",
        "btn_switch_scene": "🗺️ Passa a Scena della Campagna",
        "btn_open_calendar": "📅 Apri Calendario Campagna",
        "btn_open_quests": "📜 Diario e Missioni",
        "btn_open_shops": "🛒 Negozi",
        "btn_travel_panel": "🧭 Pannello Gestione Viaggio (Hex Crawl)",
        "weather_header": "Clima",

        # --- Tab Audio DM ---
        "audio_library_header": "Libreria Audio",
        "audio_library_desc": "Carica MP3/OGG/WAV/FLAC. I giocatori li scaricano una sola volta.",
        "audio_upload_btn": "➕ Carica tracce...",
        "audio_col_name": "Nome",
        "audio_col_type": "Tipo",
        "audio_col_duration": "Durata",

        # --- Badge Rapidi Giocatore ---
        "sheet_ac_badge": "CA",
        "sheet_speed_badge": "Vel",
        "sheet_init_badge": "Iniz",

        # --- Menu Contestuale Token ---
        "ctx_view_sheet": "Visualizza Scheda",
        "ctx_assign_item": "Assegna Oggetto",
        "ctx_modify_hp": "Modifica HP",
        "ctx_modify_conditions": "Modifica Stati/Condizioni",
        "ctx_execute_action": "Esegui Azione (Danno/Cura)",
        "ctx_set_aura": "Imposta Aura",
        "ctx_light_source": "🔦 Sorgente di Luce (Torcia/Lanterna)...",
        "ctx_config_boss": "👑 Configura Boss Leggendario...",
        "ctx_spend_legendary": "👑 Spendi Azione Leggendaria...",
        "ctx_set_owner": "Imposta Proprietario",
        "ctx_open_private_chat": "Apri Chat Privata",
        "ctx_toggle_combat": "Aggiungi/Rimuovi da Combattimento",
        "ctx_toggle_party": "Aggiungi/Rimuovi dal Party",
        "ctx_toggle_inspiration": "🌟 Assegna/Rimuovi Ispirazione",
        "ctx_remove_entity": "Rimuovi",
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
        "tool_command_palette": "Quick Command Palette (Ctrl+K)",
        "cmd_palette_title": "Command Palette & Quick Search",
        "cmd_palette_placeholder": "🔍 Search rules, monsters, tokens, spells or type /roll...",
        "cmd_palette_hint": "↑ / ↓ Navigate  •  ↵ Select / Execute  •  Esc Close",
        "cmd_type_roll": "🎲 Dice Roll",
        "cmd_type_token": "📍 Map Token",
        "cmd_type_rule": "📖 5e Rule",
        "cmd_type_action": "⚡ Quick Action",

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
        "sheet_currency": "Currency",
        "sheet_item": "Item",
        "sheet_weight_col": "Weight (lbs)",
        "sheet_attunement": "Attunement",
        "sheet_empty_slot": "Empty",
        "sheet_search_compendium": "Search Compendium",
        "sheet_give_gold_btn": "🪙 Give Gold to Ally",
        "sheet_spell_slots_header": "Spell Slots (Max / Current)",

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

        # --- Player Navigation & Party Controls ---
        "party_members_header": "👥 Adventuring Party",
        "chat_tab_global": "Global",
        "chat_tab_system": "System",
        "status_disconnected": "Status: Disconnected",
        "status_connected": "Status: Connected",
        "no_character": "No Character",
        "adventurer_lvl": "Adventurer • Level {lvl}",
        "select_or_create_char": "Select or create a character",
        "class_adventurer": "Adventurer",
        "char_level_prefix": "Level",
        "exhaustion_prefix": "Exhaustion",
        "not_in_combat": "Not in Combat",

        # --- Turn Economy & Quick Actions ---
        "turn_economy": "⚡ Turn Economy",
        "turn_economy_reset": "↺ Reset",
        "tooltip_reset_economy": "Reset turn resources",
        "btn_act": "⚔️ Action",
        "tooltip_act": "Standard Action: click to toggle spent/available",
        "btn_bonus": "✨ Bonus",
        "tooltip_bonus": "Bonus Action: click to toggle spent/available",
        "btn_react": "🛡️ React",
        "tooltip_react": "Reaction: click to toggle spent/available",
        "lbl_movement": "👟 Movement: {used} / {total} ft (Left: {rem} ft)",
        "btn_dash": "🏃 Dash",
        "tooltip_dash": "Spends Action to double movement this turn",
        "btn_disengage": "💨 Disengage",
        "tooltip_disengage": "Spends Action: movement does not provoke opportunity attacks",
        "btn_dodge": "🛡️ Dodge",
        "tooltip_dodge": "Spends Action: attackers have disadvantage against you and you have advantage on DEX saves",
        "btn_help": "🤝 Help",
        "tooltip_help": "Spends Action: click an enemy to grant advantage to an ally's next attack",

        # --- Player Action Buttons ---
        "change_active_char": "Change Active Character:",
        "btn_sheet": "📜 Character Sheet",
        "btn_roll_dice": "🎲 Roll Dice",
        "btn_action": "⚔️ Action (Attack / Heal / Damage)",
        "btn_short_rest": "☕ Short Rest (Hit Dice)",
        "lbl_class_features": "Class Features",
        "btn_second_wind": "💨 Second Wind",
        "tooltip_second_wind": "Fighter (1/Short Rest): regain 1d10 + Level HP as a Bonus Action",
        "btn_action_surge": "⚡ Action Surge",
        "tooltip_action_surge": "Fighter (1/Short Rest): gain an additional Action this turn",
        "btn_rage": "🩸 Barbarian Rage",
        "tooltip_rage": "Barbarian: enter Rage (+2 melee damage, resistance to bludgeoning, piercing, slashing)",
        "btn_travel_actions": "🧭 Travel Actions",
        "btn_manuals": "📖 Browse Rulebooks",
        "btn_request_combat": "⚔️ Request Combat",
        "btn_end_turn": "⏹ End Turn",

        # --- Audio & Voice Tooltips ---
        "tooltip_mute_audio": "Mute/Unmute Game Audio",
        "tooltip_deafen": "Deafen/Undeafen Voice Audio",
        "tooltip_mute_mic": "Mute/Unmute Microphone",
        "voice_server_active": "🟢 Voice Server: Active",

        # --- DM Tabs & Controls ---
        "tab_world": "World",
        "tab_audio_sfx": "Audio / SFX",
        "dm_combatants_header": "⚔️ Adventurers & Monsters",
        "lbl_round_num": "⚔️ ROUND {round}",
        "btn_prev_turn": "⬅ Prev Turn",
        "btn_next_turn": "Next Turn ➡",
        "btn_hide_reveal": "👁 Hide / Reveal NPC",
        "npc_actions_header": "Selected NPC Actions",
        "btn_start_combat": "⚔️ Start Combat",
        "btn_end_combat": "⏹ End Combat",
        "btn_deploy_prepared": "⚡ Deploy Prepared Encounter",
        "btn_roll_all_npcs": "🎲 Roll Initiative for All Monsters",
        "lbl_balance_waiting": "⚔️ 5e Balance: Awaiting data",
        "btn_spawn_png": "Spawn NPC",
        "btn_add_manual_npc": "+ Add Manual NPC/Monster",
        "btn_split_loot": "💰 Split Gold (Party Loot)",
        "lbl_bestiary_header": "📖 Bestiary (Monster Manual 2025 & SRD):",
        "lbl_bestiary_preview_default": "Select a monster to view stats.",
        "btn_spawn_on_map": "⚔️ Spawn on Map",
        "btn_full_sheet": "📖 Full Stat Block",
        "btn_dice": "🎲 Dice",

        # --- Character Sheet Translation ---
        "sheet_attributes": "ABILITY SCORES",
        "sheet_skills": "SKILLS",
        "sheet_saving_throws": "SAVING THROWS",
        "sheet_armor_class": "AC",
        "sheet_initiative_short": "INIT",
        "sheet_speed_short": "SPEED",
        "sheet_dice_roll": "Dice Roll:",
        "sheet_levelup_btn": "🌟 Level Up!",
        "sheet_short_rest_btn": "☕ Short Rest",
        "sheet_long_rest_btn": "🌙 Long Rest",
        "sheet_name": "Name:",
        "sheet_campaign": "Campaign:",
        "sheet_class": "Class:",
        "sheet_level": "Level:",
        "sheet_race": "Race:",
        "sheet_exp": "EXP:",

        # --- DM Map & FoW Toolbar ---
        "dm_tactical_map": "🗺 Tactical Map",
        "fow_tool_label": "Tool:",
        "fow_mode_move": "Move Token",
        "fow_mode_erase": "Erase Fog",
        "fow_mode_draw": "Draw Fog",
        "fow_player_view": "Player View",
        "fow_send_btn": "Broadcast Fog",
        "fow_options_btn": "FoW Options",
        "fow_menu_enable": "Enable Fog of War",
        "fow_menu_hide_all": "Obscure Entire Map (Hide All)",
        "fow_menu_reveal_all": "Reveal Entire Map (Reveal All)",

        # --- Status Pills & Weather ---
        "period_morning": "Morning",
        "period_afternoon": "Afternoon",
        "period_evening": "Evening",
        "period_night": "Night",
        "weather_clear": "Clear",
        "weather_rain": "Rain",
        "weather_storm": "Storm",
        "weather_snow": "Snow",
        "weather_fog": "Fog",
        "status_exploration": "🕊️ Exploration",
        "status_in_combat": "⚔️ In Combat (R{round})",
        "campaign_none": "🏰 Campaign: None (Quick Session)",
        "campaign_active": "🏰 Campaign: {name}",

        # --- DM Tooltips ---
        "tool_fog_of_war": "Fog of War",
        "tool_teleport": "Add/Remove Teleport",
        "tool_clear_aoe": "Clear Areas of Effect",

        # --- DM World Tab ---
        "time_mgmt_header": "Time Management",
        "time_day_display": "Day {day} - {time} ({period})",
        "time_add_1h": "+1 Hour",
        "time_add_8h": "+8 Hours (Rest)",
        "time_add_1d": "+1 Day",
        "btn_switch_scene": "🗺️ Switch Campaign Scene",
        "btn_open_calendar": "📅 Open Campaign Calendar",
        "btn_open_quests": "📜 Quests & Journal",
        "btn_open_shops": "🛒 Shops & Trading",
        "btn_travel_panel": "🧭 Travel Management Panel (Hex Crawl)",
        "weather_header": "Weather",

        # --- DM Audio Tab ---
        "audio_library_header": "Audio Library",
        "audio_library_desc": "Upload MP3/OGG/WAV/FLAC. Players download them once.",
        "audio_upload_btn": "➕ Upload Tracks...",
        "audio_col_name": "Name",
        "audio_col_type": "Type",
        "audio_col_duration": "Duration",

        # --- Player Badges ---
        "sheet_ac_badge": "AC",
        "sheet_speed_badge": "Spd",
        "sheet_init_badge": "Init",

        # --- Context Menu ---
        "ctx_view_sheet": "View Character Sheet",
        "ctx_assign_item": "Assign Item",
        "ctx_modify_hp": "Modify HP",
        "ctx_modify_conditions": "Modify Conditions/Statuses",
        "ctx_execute_action": "Perform Action (Damage/Heal)",
        "ctx_set_aura": "Set Aura",
        "ctx_light_source": "🔦 Light Source (Torch/Lantern)...",
        "ctx_config_boss": "👑 Configure Legendary Boss...",
        "ctx_spend_legendary": "👑 Spend Legendary Action...",
        "ctx_set_owner": "Set Owner",
        "ctx_open_private_chat": "Open Private Chat",
        "ctx_toggle_combat": "Add/Remove from Combat",
        "ctx_toggle_party": "Add/Remove from Party",
        "ctx_toggle_inspiration": "🌟 Grant/Remove Inspiration",
        "ctx_remove_entity": "Remove",
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
