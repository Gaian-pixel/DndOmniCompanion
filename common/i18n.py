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
    "Nebbia": "Fog",
    "Oscurità": "Darkness"
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
    "Notte": "Night",
    "Alba": "Dawn",
    "Giorno": "Day",
    "Tramonto": "Dusk",
    "Al Chiuso": "Indoor",
    "Dungeon": "Dungeon",
    "Manuale": "Manual"
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



RACES_IT_TO_EN = {
    "Umano": "Human",
    "Elfo": "Elf",
    "Nano": "Dwarf",
    "Halfling": "Halfling",
    "Draconide": "Dragonborn",
    "Dragonide": "Dragonborn",
    "Gnomo": "Gnome",
    "Mezzelfo": "Half-Elf",
    "Mezzorco": "Half-Orc",
    "Tiefling": "Tiefling"
}
RACES_EN_TO_IT = {
    "Human": "Umano",
    "Elf": "Elfo",
    "Dwarf": "Nano",
    "Halfling": "Halfling",
    "Dragonborn": "Draconide",
    "Gnome": "Gnomo",
    "Half-Elf": "Mezzelfo",
    "Half-Orc": "Mezzorco",
    "Tiefling": "Tiefling"
}

def translate_race(race_name: str, target_lang: str = None) -> str:
    """Traduce la razza 5e tra IT ed EN."""
    if not target_lang:
        target_lang = get_language()
    clean = (race_name or "").strip()
    if target_lang == "en":
        return RACES_IT_TO_EN.get(clean, clean)
    else:
        return RACES_EN_TO_IT.get(clean, clean)


CLASSES_IT_TO_EN = {
    "Barbaro": "Barbarian",
    "Bardo": "Bard",
    "Chierico": "Cleric",
    "Druido": "Druid",
    "Guerriero": "Fighter",
    "Monaco": "Monk",
    "Paladino": "Paladin",
    "Ranger": "Ranger",
    "Ladro": "Rogue",
    "Stregone": "Sorcerer",
    "Warlock": "Warlock",
    "Mago": "Wizard"
}
CLASSES_EN_TO_IT = {v: k for k, v in CLASSES_IT_TO_EN.items()}

def translate_class(class_name: str, target_lang: str = None) -> str:
    """Traduce la classe 5e tra IT ed EN."""
    if not target_lang:
        target_lang = get_language()
    clean = (class_name or "").strip()
    if target_lang == "en":
        return CLASSES_IT_TO_EN.get(clean, clean)
    else:
        return CLASSES_EN_TO_IT.get(clean, clean)


ALIGNMENTS_IT_TO_EN = {
    "Nessuno (Non specificato)": "None (Unspecified)",
    "Legale Buono": "Lawful Good",
    "Neutrale Buono": "Neutral Good",
    "Caotico Buono": "Chaotic Good",
    "Legale Neutrale": "Lawful Neutral",
    "Neutrale Puro": "True Neutral",
    "Neutrale": "Neutral",
    "Caotico Neutrale": "Chaotic Neutral",
    "Legale Malvagio": "Lawful Evil",
    "Neutrale Malvagio": "Neutral Evil",
    "Caotico Malvagio": "Chaotic Evil"
}
ALIGNMENTS_EN_TO_IT = {v: k for k, v in ALIGNMENTS_IT_TO_EN.items()}

def translate_alignment(align_name: str, target_lang: str = None) -> str:
    """Traduce l'allineamento morale 5e tra IT ed EN."""
    if not target_lang:
        target_lang = get_language()
    clean = (align_name or "").strip()
    if target_lang == "en":
        return ALIGNMENTS_IT_TO_EN.get(clean, clean)
    else:
        return ALIGNMENTS_EN_TO_IT.get(clean, clean)


BACKGROUNDS_IT_TO_EN = {
    "Accolito": "Acolyte",
    "Ciarlatano": "Charlatan",
    "Criminale": "Criminal",
    "Intrattenitore": "Entertainer",
    "Eroe Popolare": "Folk Hero",
    "Artigiano di Gilda": "Guild Artisan",
    "Eremita": "Hermit",
    "Nobile": "Noble",
    "Forestiero": "Outlander",
    "Sapiente": "Sage",
    "Marinaio": "Sailor",
    "Soldato": "Soldier",
    "Monello": "Urchin",
    "Personalizzato": "Custom"
}
BACKGROUNDS_EN_TO_IT = {v: k for k, v in BACKGROUNDS_IT_TO_EN.items()}

def translate_background(bg_name: str, target_lang: str = None) -> str:
    """Traduce il background 5e tra IT ed EN."""
    if not target_lang:
        target_lang = get_language()
    clean = (bg_name or "").strip()
    if target_lang == "en":
        return BACKGROUNDS_IT_TO_EN.get(clean, clean)
    else:
        return BACKGROUNDS_EN_TO_IT.get(clean, clean)


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
        "launcher_player_btn_manage_chars": "👤 Gestione Personaggi (Offline)",
        "launcher_player_btn_create_char": "✨ Crea Personaggio (Guidato)",
        "launcher_player_btn_join": "🛡️ Unisciti a Partita",
        "launcher_footer": "DndOmniCompanion • Audio Streaming, Voice UDP & Hex Grid Engine",
        "launcher_lang_btn": "🌐 Lingua: Italiano 🇮🇹",

        # --- Menù Globale ---
        "menu_file": "File",
        "menu_view": "Visualizza",
        "menu_fullscreen": "Schermo Intero (F11)",
        "menu_exit_fullscreen": "Esci da Schermo Intero",
        "toast_fullscreen_on": "Schermo Intero attivato (Premi F11 o Esc per uscire)",
        "toast_fullscreen_off": "Schermo Intero disattivato",
        "menu_new_campaign": "Nuova Campagna...",
        "menu_load_campaign": "Carica Campagna...",
        "menu_edit_active_campaign": "Editor Campagna Attiva...",
        "menu_close_campaign": "Chiudi Campagna Attiva",
        "menu_load_map": "Carica Mappa...",
        "menu_save_session": "Salva Sessione...",
        "menu_load_session": "Carica Sessione...",
        "menu_exit": "Esci",
        "confirm_exit_server": "Vuoi chiudere il server?",
        "confirm_exit_client": "Vuoi chiudere il client e uscire?",
        "confirm_exit_connected": "Sei attualmente connesso al server.\nVuoi davvero disconnetterti e chiudere il client?",
        "menu_tools": "Strumenti",
        "menu_encounter_builder": "⚔️ Preparazione Combattimenti (Encounter Builder)...",
        "btn_encounter_builder": "⚔️ Encounter Builder",
        "menu_loot_gen": "💰 Generatore di Bottino (Loot 5e)",
        "menu_npc_gen": "🎭 Generatore Rapido PNG",
        "menu_map_editor": "Editor Mappe",
        "menu_share_image": "Condividi Immagine (Handout)",
        "menu_share_text": "Condividi Documento testuale",
        "menu_download_maps": "Scarica Mappe Famose",
        "menu_srd_compendium": "Compendio & SRD",
        "menu_quest_log": "📜 Registro Missioni & Handouts...",
        "menu_manuals": "📖 Consulta Manuali di Gioco (PHB, DMG, MM)",
        "menu_travel_panel": "Pannello Viaggio",
        "menu_starter_pack": "Starter Pack Campagna",
        "menu_automation_settings": "⚙️ Stile Gestione Campagna (Automazioni)...",
        "campaign_none_title": "Nessuna Campagna Attiva",
        "campaign_none_prompt": "Non c'è una campagna attualmente caricata.\n\nVuoi caricare una campagna esistente?\n(Scegli 'No' per creare una Nuova Campagna)",
        "menu_server": "Server",
        "menu_connect": "Connetti al Server...",
        "menu_reconnect": "Riconnetti Ultimo Server",
        "menu_disconnect": "Disconnetti",
        "menu_character": "Personaggio",
        "menu_manage_characters": "Gestione Personaggi (Offline)...",
        "menu_create_character": "Crea Nuovo Personaggio (Guidato)...",
        "menu_create_manual_character": "Crea Personaggio Manuale...",
        "menu_active_sheet": "Scheda PG Attivo...",
        "char_manager_title": "D&D OmniCompanion • Gestione Personaggi",
        "char_manager_header": "Gestione Personaggi (Offline)",
        "char_manager_desc": "Crea, personalizza ed esporta i tuoi eroi senza bisogno di collegarti a un server.",
        "char_manager_btn_wizard": "✨ Nuovo (Guidato)",
        "char_manager_btn_manual": "➕ Manuale",
        "char_manager_btn_duplicate": "📋 Duplica",
        "char_manager_btn_delete": "🗑️ Elimina",
        "char_manager_btn_open_sheet": "📜 Apri Scheda Completa",
        "char_manager_btn_export": "📄 Esporta PDF / JSON",
        "char_manager_btn_select": "🎮 Seleziona come Attivo",
        "char_manager_filter_placeholder": "Cerca per nome, classe o razza...",
        "char_manager_no_selection": "Seleziona un personaggio dall'elenco a sinistra per visualizzarne i dettagli o apportare modifiche.",
        "char_manager_delete_confirm": "Sei sicuro di voler eliminare definitivamente il personaggio '{name}'?",
        "char_manager_count": "{count} personaggio/i salvato/i in locale",
        "menu_library": "Libreria",
        "menu_language": "🌐 Lingua / Language",
        "menu_units": "📏 Unità di Misura",
        "unit_feet": "Piedi / Miglia (ft / mi)",
        "unit_meters": "Metri / Chilometri (m / km)",
        "unit_changed_toast": "Unità di misura impostata su: {unit}",

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
        "lbl_round": "Round: {round}",
        "btn_roll_monster_init": "🎲 Tira Iniziativa Mostri",
        "btn_spawn_npc": "➕ Aggiungi NPC",
        "btn_split_gold": "💰 Dividi Denaro",
        "btn_hide_reveal_npc": "👁️ Nascondi/Rivela PNG",
        "dm_party_header": "--- MEMBRI DEL PARTY ---",
        "dm_npc_header": "--- PNG & MOSTRI ---",

        # --- Pannelli Client / Giocatore ---
        "tab_chat": "Chat",
        "tab_player_controls": "Controlli PG",
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
        "sheet_tab_journal": "📖 Biografia & Diario",
        "sheet_tab_quick_notes": "📝 Appunti di Sessione",
        "adv_normal": "Normale",
        "adv_advantage": "Vantaggio",
        "adv_disadvantage": "Svantaggio",
        "insp_none": "☆ Nessuna Ispirazione",
        "insp_active": "★ Ispirazione Attiva!",
        "sheet_total_weight": "Peso Totale: {current} / {max} lbs",
        "sheet_encumbered": "(INGOMBRATO!)",
        "container_backpack": "🎒 Zaino",
        "container_equipped": "⚔️ Equipaggiato / Addosso",
        "container_bag_of_holding": "🔮 Borsa Conservante",
        "container_haversack": "✨ Zaino Pratico di Heward",
        "container_mount": "🐴 Sacca da Sella / Animale",
        "btn_drop_backpack": "🎒 Sfila Zaino a Terra",
        "btn_pickup_backpack": "🎒 Raccogli Zaino",
        "status_backpack_worn": "🎒 Zaino: In Spalla",
        "status_backpack_ground": "⚠️ Zaino: A Terra (Carico escluso)",
        "msg_backpack_dropped": "🎒 {name} si sfila lo zaino e lo lascia a terra per muoversi più agilmente! (Interazione con Oggetto, PHB p. 190)",
        "msg_backpack_picked_up": "🎒 {name} raccoglie lo zaino da terra e lo rimette in spalla.",
        "enc_normal": "🟢 Normale",
        "enc_encumbered": "🟡 Ingombrato (-10 ft / -3 m vel.)",
        "enc_heavily_encumbered": "🔴 Gravemente Ingombrato (-20 ft / -6 m vel., Svantaggio)",
        "enc_overloaded": "⛔ Sovraccarico (Movimento 0)",
        "lbl_container": "Collocazione / Contenitore:",
        "lbl_coins_weight": "Monete: {weight} lbs",
        "lbl_boh_capacity": "🔮 Borsa Conservante: {cur} / 500 lbs",
        "lbl_haversack_capacity": "✨ Zaino Pratico: {cur} / 120 lbs",
        "lbl_mount_capacity": "🐴 Sacca da Sella: {cur} lbs",
        "lbl_backpack_ground_weight": "🎒 A Terra: {weight} lbs",
        "sheet_you_are_dead": "☠ SEI MORTO ☠",
        "sheet_active_conditions": "Condizioni Attive:",
        "sheet_currency": "Borsa delle Monete",
        "sheet_currency_total": "Valore Stimato Totale",
        "sheet_item": "Oggetto",
        "sheet_weight_col": "Peso (lbs)",
        "sheet_attunement": "Sintonia",
        "sheet_empty_slot": "Vuoto",
        "sheet_empty_slot_desc": "Slot Vuoto (Clicca per aggiungere)",
        "sheet_search_compendium": "📚 Cerca nel Compendio",
        "sheet_add_custom_item": "✏️ Nuovo Oggetto",
        "sheet_give_gold_btn": "🤝 Dona Oro a Compagno",
        "sheet_spell_slots_header": "Slot Incantesimo (Max / Correnti)",
        "sheet_attunement_count": "Sintonia: {count}/3 🔮",
        "sheet_item_actions": "Azioni",
        "sheet_item_edit": "Dettagli",
        "sheet_item_discard": "Scarta",
        "sheet_item_trade": "Dona",
        "sheet_discard_confirm": "Vuoi scartare questo oggetto? Andrà perso irrevocabilmente.",
        "coin_cp_title": "Rame (MR)",
        "coin_sp_title": "Argento (MA)",
        "coin_ep_title": "Electrum (ME)",
        "coin_gp_title": "Oro (MO)",
        "coin_pp_title": "Platino (MP)",
        "coin_cp_sub": "1/100 MO",
        "coin_sp_sub": "1/10 MO",
        "coin_ep_sub": "1/2 MO",
        "coin_gp_sub": "Base 1.0 MO",
        "coin_pp_sub": "10.0 MO",
        "tooltip_coin_cp": "Monete di Rame (MR / cp):\n100 MR = 1 MO",
        "tooltip_coin_sp": "Monete d'Argento (MA / sp):\n10 MA = 1 MO",
        "tooltip_coin_ep": "Monete d'Electrum (ME / ep):\n2 ME = 1 MO",
        "tooltip_coin_gp": "Monete d'Oro (MO / gp):\nValuta standard di riferimento 5e",
        "tooltip_coin_pp": "Monete di Platino (MP / pp):\n1 MP = 10 MO",
        "btn_request_currency": "🤝 Richiedi Valuta al Master",
        "title_request_currency": "Richiedi Valuta al Dungeon Master",
        "lbl_request_coin": "Tipo di Moneta:",
        "lbl_request_amount": "Quantità da Richiedere:",
        "lbl_request_reason": "Motivazione (es. ricompensa missione, bottino, vendita):",
        "msg_request_currency_sent": "Richiesta di {amount} {coin} inviata al Master. Attendi l'approvazione.",
        "msg_currency_locked_online": "In sessione non puoi aumentarti il denaro da solo. Usa 'Richiedi Valuta al Master' per ottenere monete dal DM.",
        "msg_item_approval_sent": "La richiesta per '{item}' è stata inviata al Master. Verrà aggiunto appena approvato.",
        "msg_attr_locked_online": "Caratteristica bloccata durante la sessione. Aumenta solo tramite Level Up o concessione del Master.",
        "msg_hp_max_locked_online": "I Punti Ferita Massimi sono bloccati durante la sessione.",
        "msg_hp_cur_locked_online": "I Punti Ferita in partita sono gestiti da combattimento, riposi e dal Dungeon Master.",

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
        "turn_economy_exploration": "⚡ Economia Turno • 🧭 Esplorazione",
        "turn_economy_my_turn": "⚡ Economia Turno • 🟢 TUO TURNO",
        "turn_economy_other_turn": "⚡ Economia Turno • ⏳ Turno Altrui",
        "turn_economy_reset": "↺ Reset",
        "tooltip_reset_economy": "Ripristina le risorse del turno",
        "btn_act": "⚔️ Azione",
        "tooltip_act": "Azione Standard: clicca per contrassegnare come spesa/disponibile",
        "btn_bonus": "✨ Bonus",
        "tooltip_bonus": "Azione Bonus: clicca per contrassegnare come spesa/disponibile",
        "btn_react": "🛡️ Reaz",
        "tooltip_react": "Reazione: clicca per contrassegnare come spesa/disponibile",
        "lbl_movement": "👟 Movimento: {used} / {total} ft (Rim: {rem} ft)",
        "lbl_movement_exploration": "🧭 Esplorazione: Movimento libero (Base: {base})",
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
        "weather_clear": "Sereno",
        "weather_rain": "Pioggia",
        "weather_storm": "Tempesta",
        "weather_snow": "Neve",
        "weather_fog": "Nebbia",
        "weather_darkness": "Oscurità",
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

        # --- Generatore Rapido PNG & Bottino (dm_generators.py) ---
        "npc_gen_title": "D&D OmniCompanion • Generatore Rapido PNG",
        "npc_gen_header": "🎭 Generatore Rapido di PNG",
        "npc_gen_subtitle": "Crea al volo personaggi non giocanti con personalità, segreti e statistiche",
        "npc_gen_name": "Nome:",
        "npc_gen_hp": "HP:",
        "npc_gen_ac": "CA:",
        "npc_gen_race_role": "Razza & Ruolo:",
        "npc_gen_alignment": "Allineamento:",
        "npc_gen_personality_traits": "Personalità, Tratti e Segreti del PNG:",
        "npc_gen_role_prefix": "Ruolo:",
        "npc_gen_trait_prefix": "Tratto Distintivo:",
        "npc_gen_secret_prefix": "Segreto / Motivazione:",
        "btn_generate_another_npc": "🔄 Genera Altro PNG",
        "btn_spawn_token_map": "⚡ Spawna Token sulla Mappa",
        "btn_save_to_campaign": "💾 Salva nella Campagna",
        "msg_npc_spawned_title": "PNG Schierato",
        "msg_npc_spawned_desc": "Token per '{name}' creato con successo sulla mappa!",
        "msg_npc_saved_title": "Salvato",
        "msg_npc_saved_desc": "PNG '{name}' salvato nella campagna '{campaign}'!",
        "msg_no_campaign_title": "Nessuna Campagna",
        "msg_no_campaign_desc": "Nessuna campagna attiva caricata. Carica o crea una campagna dal menu File.",
        "loot_gen_title": "D&D OmniCompanion • Generatore di Bottino 5e",
        "loot_gen_header": "💰 Generatore di Tesoro & Bottino",
        "loot_gen_subtitle": "Genera ricompense secondo le tabelle della Guida del Dungeon Master (DMG 5e)",
        "loot_gen_cr": "Grado Sfida (CR):",
        "loot_gen_type": "Tipo Bottino:",
        "loot_gen_hoard": "Tesoro della Tana",
        "loot_gen_individual": "Bottino Individuale",
        "btn_generate_loot": "🎲 Genera Nuovo Bottino",
        "loot_coins_summary": "🪙 Monete: {coins}",
        "loot_no_coins": "Nessuna moneta",
        "loot_value_est": "Valore Totale Stimato: ~{val} Monete d'Oro",
        "col_type": "Tipo",
        "col_name_desc": "Nome / Descrizione",
        "col_properties": "Proprietà",
        "btn_distribute_gold_party": "💰 Distribuisci Monete d'Oro al Party",
        "btn_grant_selected_item": "🎒 Assegna Oggetto Selezionato a Giocatore",
        "msg_no_gold_title": "Nessun Oro",
        "msg_no_gold_desc": "Non ci sono monete d'oro in questo bottino.",
        "msg_no_party_players_title": "Nessun Giocatore",
        "msg_no_party_players_desc": "Non ci sono giocatori nel party a cui distribuire l'oro.",
        "msg_gold_distributed_title": "Oro Distribuito",
        "msg_gold_distributed_desc": "{total} MO distribuiti con successo ({share} MO a testa).",
        "msg_select_item_warning": "Seleziona un oggetto o gemma dalla lista.",
        "msg_no_online_players": "Nessun giocatore online a cui assegnare l'oggetto.",
        "prompt_assign_item": "A chi vuoi assegnare '{item}'?\nGiocatori disponibili: {players}",
        "msg_item_assigned_title": "Assegnato",
        "msg_item_assigned_desc": "'{item}' inviato all'inventario di {player}.",

        # --- Finestre Dialoghi Master & Client ---
        "custom_npc_title": "Crea Nuovo NPC / Mostro Custom",
        "custom_npc_name": "Nome del PNG/Mostro:",
        "custom_npc_hp": "HP Massimi:",
        "custom_npc_init": "Iniziativa:",
        "custom_npc_ac": "Classe Armatura (CA):",
        "custom_npc_speed": "Velocità (ft):",
        "custom_npc_notes": "Note/Descrizione (opzionale):",
        "btn_create_npc_map": "Crea NPC e Aggiungi alla Mappa",
        "handout_dialog_title": "Condividi Documento / Nota Testuale",
        "handout_doc_title": "Titolo del Documento:",
        "handout_doc_text": "Testo da mostrare ai giocatori:",
        "btn_send_to_players": "Invia ai Giocatori",
        "msg_handout_shared": "Documento condiviso con tutti i giocatori connessi!",
        "aoe_dialog_title": "Piazza Area d'Effetto (AoE)",
        "aoe_shape": "Forma Area:",
        "aoe_sphere_cube": "Sfera / Cubo",
        "aoe_cone": "Cono",
        "aoe_line": "Linea",
        "aoe_size_hexes": "Raggio / Lunghezza (esagoni):",
        "aoe_color": "Colore:",
        "color_red": "Rosso",
        "color_blue": "Blu",
        "color_green": "Verde",
        "color_yellow": "Giallo",
        "color_purple": "Viola",
        "aoe_requires_save": "Richiede Tiro Salvezza (Auto-roll per bersagli)",
        "aoe_dc": "CD:",
        "aoe_damage": "Danni:",
        "aoe_half_damage": "Dimezza Danni (Successo TS)",
        "aoe_consume_slot": "Consuma Slot Incantesimo:",
        "aoe_no_slot": "0 - Nessuno / Trucchetto",
        "aoe_slot_lvl": "{lvl} - Slot Livello {lvl} ({cur}/{mx} disp)",
        "btn_confirm_aoe": "Conferma Area d'Effetto",
        "aoe_click_map_prompt": "Clicca sulla mappa per confermare il bersaglio / centro dell'area d'effetto.",
        "combat_config_title": "Configurazione Combattimento",
        "combat_filter_distance": "Filtro per Distanza (Auto-selezione)",
        "combat_origin": "Origine:",
        "combat_radius_hex": "Raggio (esagoni):",
        "btn_select_nearby": "Seleziona Vicini",
        "combat_participants": "Partecipanti:",
        "npc_init_dialog_title": "Iniziativa NPC",
        "npc_init_dialog_prompt": "Inserisci l'iniziativa per gli NPC:",
        "btn_confirm_initiatives": "Conferma Iniziative",
        "btn_next": "Avanti",
        "btn_prepare_cast": "Prepara Lancio",
        "btn_confirm_select_center": "Conferma & Seleziona Centro",
        "aoe_client_dialog_title": "Lancia Incantesimo / AoE",
        "aoe_save_auto_damage": "Richiede Tiro Salvezza (Danni Automatici)",
        "aoe_save_auto_npc": "Richiede Tiro Salvezza (Auto-roll per NPC)",
        "deploy_encounter_title": "Schiera Incontro della Campagna",
        "deploy_encounter_header": "⚔️ Incontri Preparati della Campagna",
        "deploy_encounter_subtitle": "Seleziona l'incontro da schierare sulla mappa corrente:",
        "col_encounter_name": "Nome Incontro",
        "col_act": "Atto",
        "col_monsters": "Mostri",
        "col_notes": "Note",
        "btn_deploy_on_map": "⚡ Schiera sulla Mappa",
        "msg_no_encounter_title": "Nessun Incontro",
        "msg_no_encounter_desc": "Nessuna campagna attiva con incontri preparati. Vuoi aprire l'Editor Campagna?",
        "switch_scene_title": "Passa a Scena della Campagna",
        "switch_scene_header": "🗺️ Scene della Campagna",
        "msg_no_scene_title": "Nessuna Scena",
        "msg_no_scene_desc": "Nessuna campagna attiva con scene collegate.",
        "starter_kit_title": "Configura Starter Pack Campagna (Equipaggiamento Iniziale)",
        "starter_kit_header": "Equipaggiamento Iniziale della Campagna",
        "starter_kit_desc": "I nuovi PG riceveranno automaticamente questi oggetti al loro primo login in questa campagna:",
        "btn_add_item": "➕ Aggiungi Oggetto",
        "btn_edit_selected": "✏️ Modifica Selezionato",
        "btn_remove_selected": "🗑️ Rimuovi Selezionato",
        "btn_reset_defaults": "Ripristina Predefiniti",
        "btn_save_config": "Salva Configurazione",
        "msg_confirm_reset_starter_kit": "Vuoi ripristinare il kit iniziale predefinito della campagna?",
        "msg_starter_kit_saved": "Equipaggiamento iniziale della campagna salvato con successo!",
        "sheet_viewer_title": "Scheda Personaggio: {name}",
        "general_info": "Informazioni Generali",
        "lbl_class": "Classe:",
        "lbl_race": "Razza:",
        "lbl_alignment": "Allineamento:",
        "lbl_background": "Background:",
        "tab_stats_attributes": "📊 Statistiche & Attributi",
        "combat": "Combattimento",
        "hit_points": "Punti Ferita (HP)",
        "armor_class": "Classe Armatura (CA)",
        "initiative": "Iniziativa",
        "speed": "Velocità",
        "ability_scores": "Punteggi di Caratteristica",
        "col_ability": "Caratteristica",
        "col_base_score": "Punteggio Base",
        "col_modifier": "Modificatore",
        "tab_inventory": "🎒 Inventario",
        "col_item_name": "Nome Oggetto",
        "col_quantity": "Quantità",
        "col_weight": "Peso (lbs)",
        "col_desc_effect": "Descrizione / Effetto",
        "coin_pouch": "Borsa delle Monete",
        "tab_spellbook": "✨ Grimorio",
        "spell_slots": "Slot Incantesimo",
        "col_level": "Livello",
        "col_spell_name": "Nome Incantesimo",
        "col_casting_time": "Lancio",
        "col_range": "Raggio / Gittata",
        "tab_features_notes": "📜 Privilegi & Note",
        "features_traits": "Tratti e Privilegi:",
        "notes_background": "Note e Background:",
        "btn_close_sheet": "Chiudi Scheda",
        "msg_select_at_least_one_participant": "Seleziona almeno un partecipante.",
        "msg_combat_already_running": "Un combattimento è già in corso.",
        "msg_no_players_combat": "Nessun personaggio/NPC per iniziare il combattimento.",
        "msg_combat_end_title": "Fine Combattimento",
        "msg_combat_end_confirm": "Vuoi terminare il combattimento?",
        "col_skill_prof": "Comp.",
        "col_skill_name": "Abilità (Stat)",
        "col_skill_bonus": "Bonus",
        "col_skill_roll": "Tira",
        "tooltip_skill_prof": "Livello di Competenza:\n0 = Nessuna\n1 = Competente (+Bonus Comp)\n2 = Maestria (+Doppio Bonus)",
        "tooltip_skill_bonus": "Modificatore totale calcolato (Caratteristica + Competenza) sommato al d20",
        "tooltip_skill_combo": "0 = Nessuna Competenza\n1 = Competente (+PB)\n2 = Maestria (+2×PB)",
        "btn_close": "Chiudi",
        "cantrip": "Trucchetto",
        "col_description": "Descrizione",
        "msg_content_cannot_empty": "Il contenuto non può essere vuoto.",
        "msg_entity_exists": "Un'entità con questo nome esiste già.",
        "msg_name_required": "Il nome è obbligatorio.",
        "msg_stat_integer": "I valori statistici devono essere numeri validi.",
        "msg_title_required": "Il titolo è obbligatorio.",
        "no_features_registered": "Nessun tratto speciale registrato.",
        "no_notes_present": "Nessuna nota presente.",
        "prompt_item_desc": "Descrizione o effetto dell'oggetto:",
        "prompt_item_type": "Tipo (Arma, Armatura, Consumabile, Documento, Valuta, Equipaggiamento):",
        "text_inventory": "Inventario Testuale",
        "text_spells": "Incantesimi Testuali",
        "token_size_menu": "Dimensioni Token",
        "size_tiny": "Minuscola (Tiny)",
        "size_small": "Piccola (Small)",
        "size_medium": "Media (Medium)",
        "size_large": "Grande (Large)",
        "size_huge": "Enorme (Huge)",
        "size_gargantuan": "Mastodontica (Gargantuan)",
        "ctx_toggle_gm_layer": "Livello GM (Invisibile ai Giocatori)",
        "ctx_move_to_gm_layer": "Sposta nel Livello GM",
        "ctx_move_to_token_layer": "Sposta nel Livello Token",
        "grid_type_menu": "Tipo Griglia",
        "grid_hex": "Esagonale (Hex)",
        "grid_square": "Quadrata (Square)",
        "grid_none": "Senza Griglia (Gridless)",
        "grid_type_pill": "🌐 Griglia: {type}",
        "map_env_outdoor": "🌲 All'Aperto",
        "map_env_indoor": "🏰 Al Chiuso / Dungeon",
        "map_env_tooltip": "Tipo Ambiente Mappa (Clicca per alternare tra All'Aperto e Al Chiuso / Dungeon)",
        "map_env_switched": "[AMBIENTE] Tipo mappa impostato su: {env}.",
        "period_dawn": "Alba",
        "period_day": "Giorno",
        "period_dusk": "Tramonto",
        "period_night": "Notte",
        "period_indoor": "Al Chiuso",
        "period_manual": "Manuale",
        "fow_brush_radius": "Pennello:",
        "tool_pen": "Disegno a Mano Libera",
        "tool_clear_drawings": "Cancella Disegni Mappa",
        "menu_export_session_log": "Esporta Diario di Sessione...",
        "export_log_title": "Diario di Sessione D&D",
        "export_log_saved": "Diario di sessione esportato con successo in:\n{path}",
        "export_log_empty": "La cronologia della chat è vuota, nessun messaggio da esportare.",
        # --- Nuove Feature 5e RAW (Luce, Copertura, Dadi Vita e Missioni) ---
        "light_torch": "Torcia",
        "light_hooded_lantern": "Lanterna a Cappuccio",
        "light_dim_hooded": "Lanterna Schermata (Luce Fioca)",
        "light_spell": "Incantesimo Luce",
        "btn_toggle_light": "Accendi/Spegni Luce",
        "cover_none": "Nessuna Copertura (0 CA)",
        "cover_half": "Mezza Copertura (+2 CA, +2 TS DES)",
        "cover_three_quarters": "Tre Quarti di Copertura (+5 CA, +5 TS DES)",
        "cover_total": "Copertura Totale (Bloccato)",
        "short_rest_title": "Riposo Breve (D&D 5e)",
        "short_rest_roll_die": "Tira 1 Dado Vita",
        "short_rest_spend_all": "Spendi Tutti i Dadi",
        "short_rest_finish": "Concludi Riposo",
        "quest_log_title": "Registro Missioni & Obiettivi",
        "quest_status_in_progress": "In Corso",
        "quest_status_completed": "Completata",
        "quest_status_failed": "Fallita",
        # --- Nuove Traduzioni UI Avanzate ---
        "launcher_dm_sub": "MASTER & REGIA CAMPAGNA",
        "launcher_player_sub": "EROI, SCHEDE 5E & TAVOLO VIRTUALE",
        "campaign_lib_title": "Libreria Campagne Preparate",
        "campaign_editor_title": "Editor Campagna: {title}",
        "wizard_window_title": "Creazione Guidata Personaggio",
        "btn_back_to_menu": "← Menu",

        # --- Creazione Guidata Personaggio (Wizard) ---
        "wizard_step1_title": "Passo 1: Scegli la Razza",
        "wizard_step2_title": "Passo 2: Scegli la Classe",
        "wizard_step3_title": "Passo 3: Caratteristiche (Standard Array)",
        "wizard_step4_title": "Passo 4: Scegli il Background & le Competenze",
        "wizard_step5_title": "Passo 5: Narrativa, Obiettivi & Dettagli Finali",
        "wizard_btn_prev": "← Passo Precedente",
        "wizard_btn_next": "Passo Successivo →",
        "wizard_btn_finish": "Fine e Crea Personaggio",
        "wizard_step1_desc": "La razza definisce la tua discendenza biologica e culturale, i bonus alle caratteristiche, la taglia, la velocità e i talenti innati.",
        "wizard_step1_filter_hint": "Filtra e confronta le 9 razze canoniche: bonus, resistenze e sinergie. Clicca su una riga per l'anteprima dettagliata.",
        "wizard_step2_desc": "La classe definisce la vocazione, le abilità marziali o magiche, i privilegi speciali e il ruolo tattico del tuo avventuriero.",
        "wizard_step2_filter_hint": "Confronta Dadi Vita, Ruolo Tattico, Caratteristiche Primarie e Complessità per scegliere la tua vocazione.",
        "wizard_step3_desc": "Distribuisci l'array standard (15, 14, 13, 12, 10, 8) alle 6 caratteristiche. I bonus razziali sono applicati automaticamente.",
        "wizard_step4_desc": "Il tuo passato plasma le tue competenze nelle abilità, i privilegi sociali e l'equipaggiamento iniziale.",
        "wizard_step5_desc": "Definisci nome, allineamento, ideali, legami, difetti e aspetto visivo del tuo eroe.",
        "wizard_lbl_race": "🧬 Razza:",
        "wizard_lbl_subrace": "🌿 Sottorazza:",
        "wizard_lbl_class": "⚔️ Classe:",
        "wizard_lbl_speed_size": "🏃 Velocità & Taglia:",
        "wizard_lbl_traits": "🧬 Tratti Razziali Innati",
        "wizard_lbl_hit_die": "🎲 Dado Vita:",
        "wizard_lbl_saving_throws": "🛡️ Tiri Salvezza:",
        "wizard_lbl_proficiencies": "⚔️ Competenze:",
        "wizard_lbl_skills": "🎯 Competenze Abilità:",
        "wizard_lbl_features": "⚔️ Privilegi Chiave di Livello 1",
        "wizard_lbl_equipment": "🎒 Dotazione Iniziale di Classe",
        "wizard_lbl_spells": "✨ Magia & Incantesimi Iniziali (Livello 1):",
        "wizard_lbl_token": "🖼️ Ritratto Personaggio & Token Mappa",
        "wizard_lbl_alignment": "⚖️ Allineamento:",
        "wizard_btn_choose_race": "✓ Scegli Questa Razza",
        "wizard_btn_choose_class": "✓ Scegli Questa Classe",
        "wizard_btn_roll_random": "🎲 Tira Tutti i Tratti Casuali",
        "wizard_msg_name_required": "Il nome del personaggio è obbligatorio.",
        "wizard_traits_key": "Tratti Razziali Chiave",
        "wizard_stat_bonus": "Bonus Caratteristiche",
        "wizard_half_elf_bonus": "✨ Bonus +1 Mezzelfo (2 Caratteristiche):",
        "wizard_class_synergies": "⭐ Sinergie di Classe Consigliate:",
        "wizard_filter_label": "Filtra:",
        "wizard_search_label": "🔍 Cerca:",
        "wizard_token_no_image": "Nessuna immagine (token con iniziali)",
        "wizard_quick_advice": "💡 Consiglio di Creazione Rapida (per il Passo 3):",
        "wizard_aspect_token": "Aspetto del Personaggio & Token di Gioco:",
        "btn_prev": "◀ Prec.",
        "btn_next_arrow": "Succ. ▶",
        "btn_remove": "❌ Rimuovi",
        "lbl_size": "Taglia",
        "lbl_category": "Categoria",
        "wizard_btn_comparison_table": "📊 Tabella Comparativa",
        "wizard_senses": "👁️ Sensi:",
        "wizard_languages": "🗣️ Linguaggi:",
        "wizard_resistances_defenses": "🛡️ Resistenze & Difese:",
        "wizard_overview_lore": "📖 Panoramica & Lore Narrativa",
        "wizard_subraces_variants": "🌿 Sottorazze e Varianti Famose",
        "wizard_lifespan": "⏳ Longevità & Maturità:",
        "wizard_optimal_for": "Ottimale per",
        "wizard_step3_instruction": "Assegna i valori: 15, 14, 13, 12, 10, 8\nI valori si scambieranno automaticamente per non avere duplicati.",
        "wizard_err_standard_array": "Devi assegnare ogni valore della Array Standard (15,14,13,12,10,8) esattamente una volta.",
        "wizard_cat_all": "Tutte",
        "wizard_cat_martial": "Combattenti",
        "wizard_cat_magical": "Magiche",
        "wizard_cat_hybrid": "Ibride",
        "wizard_primary_stat": "⭐ Primaria:",
        "wizard_quick_build_tip": "💡 Consiglio di Creazione Rapida (per il Passo 3):",
        "wizard_starter_gear": "🎒 Dotazione Iniziale di Classe (fornita all'inizio):",
        "wizard_starter_spells": "✨ Magia & Incantesimi Iniziali (Livello 1):",
        "wizard_class_overview": "📖 Panoramica & Identità Narrativa",
        "wizard_lvl1_features": "⚔️ Privilegi Chiave di Livello 1",
        "wizard_playstyle_role": "🎯 Stile di Gioco & Ruolo nel Gruppo",
        "wizard_subclasses_archetypes": "🔮 Archetipi e Sottoclassi Future",
        "wizard_hp_at_lvl1": "PF al 1°",
        "wizard_lbl_bg": "Background 5e:",
        "wizard_choose_2_skills": "Scegli 2 Abilità:",
        "wizard_rp_pillars": "🎭 Le 4 Colonne Ruolistiche (D&D 5e)",
        "wizard_rp_trait": "Tratto Caratteriale (Abitudini & Modi di fare):",
        "wizard_rp_ideal": "Ideale (Principio etico o morale):",
        "wizard_rp_bond": "Legame (La persona, luogo o memoria per cui moriresti):",
        "wizard_rp_flaw": "Difetto (Vizio segreto, debolezza o fobia):",
        "wizard_feat_label": "Privilegio",
        "wizard_equip_gold_label": "Equipaggiamento & Oro Iniziale",
        "wizard_origin_place": "Origine / Città:",
        "wizard_origin_default": "Terre d'origine",
        "wizard_token_card_title": "🖼️ Ritratto Personaggio & Token Mappa",
        "wizard_token_desc": "L'immagine scelta verrà ritagliata in forma circolare e utilizzata come token interattivo sulla mappa.",
        "wizard_token_none_set": "Nessuna immagine impostata",
        "wizard_token_none_initials": "Nessuna immagine (token con iniziali)",
        "wizard_token_loaded": "Immagine caricata",
        "wizard_choose_image": "📁 Scegli Immagine...",
        "wizard_alignment_tip": "💡 Allineamento Opzionale: In D&D 5e l'allineamento è solo una possibile bussola etica e una linea guida. Non definisce per forza il giocatore o il personaggio che sarai al tavolo: le tue scelte avranno sempre la precedenza.",
        "wizard_personal_quest": "🎯 Obiettivo Personale / Gancio d'Avventura:",
        "wizard_character_secret": "🔒 Segreto del Personaggio (per il Master):",
        "wizard_dm_only": "[Visibile solo a te e al DM]",
        "wizard_party_tie": "🤝 Legame con il Gruppo (Party Tie):",
        "wizard_trinket": "🗝️ Cimelio Personale (Trinket con significato affettivo):",
        "wizard_bio_story": "📖 Biografia & Storia dell'Eroe:",
        "wizard_btn_compose": "✨ Componi Storia",
        "wizard_btn_variation": "🎲 Variazione",
        "wizard_lbl_style": "🎨 Stile Narrativo:",
        "wizard_style_heroic": "Eroico & Epico",
        "wizard_style_dark": "Dark Fantasy & Tormentato",
        "wizard_style_mysterious": "Misterioso & Arcano",
        "wizard_style_picaresque": "Picaresco & Avventuroso",
        "wizard_msg_char_created": "Personaggio '{name}' creato con successo!",
        "wizard_dlg_classes_title": "Tabella Comparativa delle 12 Classi (D&D 5e)",
        "wizard_dlg_classes_header": "📊 Confronto Rapido delle Classi",
        "wizard_dlg_classes_desc": "Confronta Dadi Vita, Ruolo Tattico, Caratteristiche Primarie e Complessità per scegliere l'eroe perfetto. Fai doppio clic su una riga per selezionarla.",
        "wizard_party_role": "Ruolo nel Party",
        "wizard_complexity": "Complessità",
        "wizard_dlg_races_title": "Compendio & Confronto Comparativo Razze (D&D 5e)",
        "wizard_dlg_races_header": "📊 Compendio e Confronto Comparativo delle Razze (D&D 5e)",
        "wizard_chip_all": "Tutte (9)",
        "wizard_chip_res": "🛡️ Resistenze",
        "wizard_chip_darkvision": "👁️ Scurovisione",
        "wizard_chip_small": "🏃 Taglia Piccola",
        "wizard_chip_melee": "⚔️ Mischia / Forza",
        "wizard_chip_magic": "✨ Magiche / Carisma",
        "wizard_dlg_choose_race": "✓ Scegli Questa Razza",
        "wizard_dlg_race_tip": "💡 Suggerimento: Seleziona una razza per visualizzarne i dettagli o premi 'Scegli Questa Razza'.",
        "wizard_dlg_races_taglia_vel": "Taglia / Vel.",
        "wizard_dlg_races_classi": "Classi Consigliate",
        "wizard_dlg_res_box": "🛡️ Resistenze, Immunità & Difese",
        "wizard_dlg_syn_box": "⭐ Sinergie & Classi Ideali",
        "wizard_dlg_traits_box": "🧬 Tratti Razziali",
        "wizard_dlg_subraces_box": "🌿 Sottorazze & Varianti",
        "wizard_vision_normal": "Normale",
        "wizard_languages_common": "Comune",
        "wizard_resistances_none": "Nessuna",
        "wizard_size": "Taglia",

        # --- Progressione Livello ---
        "prog_title": "Avanzamento di Livello (Level Up)",
        "prog_tab_hp": "Incremento Punti Ferita (HP)",
        "prog_tab_features": "⚔️ Nuovi Privilegi",
        "prog_tab_subclass": "🌟 Sottoclasse",
        "prog_tab_asi": "💪 Caratteristiche (ASI)",
        "prog_tab_spells": "✨ Incantesimi",
        "prog_hp_mode_avg": "Media (Consigliata)",
        "prog_hp_mode_roll": "Tira Dado Vita",
        "prog_btn_roll": "🎲 Tira Dado",
        "prog_btn_apply": "✅ Applica e Sali di Livello",
        "prog_subclass_header": "Sottoclasse Ufficiale D&D 5e",
        "prog_asi_header": "Aumento Punteggi di Caratteristica o Talento",
        "prog_asi_dual_error": "In modalità duale (+1 a due caratteristiche), devi selezionare due caratteristiche differenti!",
        "prog_spells_header": "Incantesimi Selezionati: {count}",
        "prog_btn_add_spell": "➕ Aggiungi al Grimorio",
        "prog_btn_remove_spell": "➖ Rimuovi Selezione",
        "prog_total_hit_dice": "Dadi Vita Totali",
        "prog_die_result": "Risultato Dado (senza Costituzione):",
        "prog_choose_feat": "Scegli un Talento Ufficiale D&D 5e (Feat):",
        "prog_no_spell_slots": "Questa classe non utilizza slot incantesimo per lanciare magie.",
        "prog_compendium_hint": "Puoi consultare il compendio incantesimi in qualunque momento con il pulsante sottostante.",
        "prog_loading": "Caricamento progressione D&D 5e...",
        "prog_loaded_srd": "Dati di progressione caricati (SRD 5e Ufficiale)",

        # --- Scheda Personaggio UI ---
        "sheet_header_subclass": "Sottoclasse:",
        "sheet_header_background": "Background:",
        "sheet_header_alignment": "Allineamento:",
        "sheet_btn_detach": "◱ Stacca Finestra",
        "sheet_btn_dock": "◰ Riaggancia alla Mappa",
        "sheet_btn_quick_save": "💾 Salva (Ctrl+S)",
        "sheet_btn_close_esc": "✕ Chiudi (Esc)",
        "sheet_btn_token": "📷 Token",
        "sheet_saves_header": "Tiri Salvezza",
        "sheet_weapons_header": "⚔️ Armi & Attacchi Rapidi 5e",
        "sheet_weapons_empty": "Nessuna arma equipaggiata.\nClicca '+ Aggiungi Arma' per registrare un'arma o attacco!",
        "sheet_weapons_add": "➕ Aggiungi Arma",
        "sheet_weapons_to_hit": "TxC",
        "sheet_weapons_dmg": "Danno",
        "sheet_weapons_target": "🎯 Bersaglio ({txc})",
        "sheet_weapons_attack": "🎲 Tira TxC",
        "sheet_weapons_hit": "🎯 Colpisci ({txc})",
        "sheet_weapons_damage_btn": "💥 Danno",
        "sheet_features_resources": "⚡ Risorse di Classe Speciali (Ki, Furore, Ispirazione, ecc.)",
        "sheet_features_new_resource": "+ Nuova Risorsa",
        "sheet_features_header": "📜 Privilegi di Classe, Tratti Razziali e Talenti",
        "sheet_features_propose": "📤 Proponi al Master",
        "sheet_features_view_text": "👁️ Vista Testo",
        "sheet_features_view_cats": "👁️ Vista Categorie",
        "sheet_features_delete": "🗑️ Elimina",
        "sheet_features_edit": "✏️ Modifica",
        "sheet_features_add": "➕ Aggiungi Tratto",
        "sheet_features_placeholder": "Seleziona un tratto o privilegio",
        "sheet_features_no_resources": "Nessuna risorsa speciale registrata. Clicca '+ Nuova Risorsa' per tracciare Ki, Furore, Ispirazione Bardica, ecc.",
        "sheet_journal_title": "📖 Biografia & Diario del Personaggio",
        "sheet_journal_sub": "Storia, legami, ideali, segreti e cronaca di viaggio (supporta Markdown #, ##, **, *, •)",
        "sheet_notes_title": "📝 Appunti di Sessione & Note Rapide",
        "sheet_notes_sub": "Indizi, promesse, PNG incontrati, mappe e appunti tattici (supporta Markdown #, ##, **, *)",
        "sheet_btn_generate_story": "✨ Genera Storia",
        "sheet_btn_save_changes": "💾 Salva Modifiche",
        "sheet_btn_edit_text": "✏️ Modifica Testo",
        "sheet_btn_view_markdown": "👁️ Vista Formattata (Markdown)",
        "sheet_badge_dm_approval": "🔒 Approvazione DM Attiva",
        "sheet_spellbook_add_btn": "➕ Nuovo Incantesimo",
        "sheet_spellbook_srd_btn": "📚 Cerca nel Compendio (SRD)",
        "sheet_spellbook_cast_btn": "Dettagli / Lancia",
        "sheet_spellbook_upcast": "⚡ Lancia a Livello (Upcasting):",
        "sheet_spellbook_cast_chat": "Lancia in Chat",
        "sheet_spellbook_attack_target": "Attacca Bersaglio",
        "sheet_short_rest_subtitle": "Spendi Dadi Vita per recuperare PF e ripristinare i privilegi di classe.",
        "sheet_short_rest_log": "Registro Tiri del Riposo:",
        "sheet_short_rest_roll_hd": "🎲 Tira 1 Dado Vita",
        "sheet_short_rest_spend_all": "⚡ Spendi Tutti",
        "sheet_short_rest_finish": "✅ Concludi Riposo",
        "sheet_export_dialog_title": "Esportazione Personaggio",
        "sheet_export_dialog_sub": "Scegli il formato desiderato per l'esportazione:",
        "sheet_export_pdf_card": "📄 Scheda Ufficiale D&D 5e (PDF)",
        "sheet_export_pdf_desc": "Seleziona il modello PDF vuoto (es. dnd_blankcharactersheet_it.pdf) per compilare automaticamente la scheda a 3 pagine.",
        "sheet_export_pdf_btn": "Esporta PDF",
        "sheet_export_json_card": "💾 File Dati Personaggio (JSON)",
        "sheet_export_json_desc": "Salva i dati grezzi del personaggio per backup, modifiche manuali o re-importazione.",
        "sheet_export_json_btn": "Esporta JSON",
        "sheet_btn_export_dialog": "📥 Esporta PDF / JSON...",
        "sheet_toast_saved": "Modifiche salvate con successo nella scheda del personaggio!",
        "sheet_toast_long_rest": "Hai effettuato un riposo lungo! HP, Dadi Vita, Tiri contro la Morte e Slot Incantesimo sono stati recuperati.",
        "sheet_crit_success_title": "COLPO CRITICO!",
        "sheet_crit_fail_title": "FALLIMENTO CRITICO!",
        "container_filter_label": "Contenitore:",
        "container_filter_all": "📦 Tutti gli Oggetti",
        "item_action_spend_one": "🏹 Spendi 1",
        "item_action_spend_custom": "🔢 Spendi...",
        "item_action_unpack": "📦 Spacchetta",
        "item_action_save": "💾 Salva",
        "item_action_trade": "🤝 Dona",
        "item_action_discard": "🗑️ Scarta",
        "item_action_details": "✏️ Modifica Dettagli...",
        "item_action_remove_request": "🗑️ Richiedi Rimozione...",
        "item_requires_attunement": "Richiede Sintonia Magica 🔮",
        "item_attuned": "Oggetto Sintonizzato 🔮",
        "empty_slot_number": "Slot #{num} Vuoto",
        "add_item_title": "✨ Nuovo Oggetto (Slot #{num})",
        "weapon_sheet_title": "⚔️ Scheda Arma 5e",
        "weapon_name": "Nome Arma:",
        "weapon_type_props": "Tipo / Proprietà:",
        "weapon_attr_txc": "Attributo (TxC & Danni):",
        "weapon_damage_die": "Dado Danno:",
        "weapon_damage_type": "Tipo di Danno:",
        "weapon_magic_bonus": "Bonus Magico (+X):",
        "weapon_proficient": "Competente nell'Arma (+ Competenza al TxC)",
        "weapon_btn_save": "Salva Arma",
        "login_select_char": "Seleziona Personaggio:",
        "login_btn_create": "Crea Nuovo",
        "login_btn_edit": "Modifica",
        "login_btn_delete": "Elimina",
        "login_btn_connect": "Connetti",
        "login_no_char_selected": "Seleziona o crea un personaggio per connetterti.",
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
        "launcher_player_btn_manage_chars": "👤 Character Manager (Offline)",
        "launcher_player_btn_create_char": "✨ Create Character (Wizard)",
        "launcher_player_btn_join": "🛡️ Join Game",
        "launcher_footer": "DndOmniCompanion • Audio Streaming, Voice UDP & Hex Grid Engine",
        "launcher_lang_btn": "🌐 Language: English 🇬🇧",

        # --- Global Menu ---
        "menu_file": "File",
        "menu_view": "View",
        "menu_fullscreen": "Fullscreen (F11)",
        "menu_exit_fullscreen": "Exit Fullscreen",
        "toast_fullscreen_on": "Fullscreen enabled (Press F11 or Esc to exit)",
        "toast_fullscreen_off": "Fullscreen disabled",
        "menu_new_campaign": "New Campaign...",
        "menu_load_campaign": "Load Campaign...",
        "menu_edit_active_campaign": "Active Campaign Editor...",
        "menu_close_campaign": "Close Active Campaign",
        "menu_load_map": "Load Map...",
        "menu_save_session": "Save Session...",
        "menu_load_session": "Load Session...",
        "menu_exit": "Exit",
        "confirm_exit_server": "Do you want to close the server?",
        "confirm_exit_client": "Do you want to close the client and exit?",
        "confirm_exit_connected": "You are currently connected to the server.\nDo you really want to disconnect and close the client?",
        "menu_tools": "Tools",
        "menu_encounter_builder": "⚔️ Combat Encounter Builder...",
        "btn_encounter_builder": "⚔️ Encounter Builder",
        "menu_loot_gen": "💰 Loot Generator (5e)",
        "menu_npc_gen": "🎭 Quick NPC Generator",
        "menu_map_editor": "Map Editor",
        "menu_share_image": "Share Image (Handout)",
        "menu_share_text": "Share Text Handout",
        "menu_download_maps": "Download Famous Maps",
        "menu_srd_compendium": "Compendium & SRD",
        "menu_quest_log": "📜 Quest Log & Handouts...",
        "menu_manuals": "📖 Browse Rulebooks (PHB, DMG, MM)",
        "menu_travel_panel": "Travel Panel",
        "menu_starter_pack": "Campaign Starter Pack",
        "menu_automation_settings": "⚙️ Campaign Automation Settings...",
        "campaign_none_title": "No Active Campaign",
        "campaign_none_prompt": "There is currently no active campaign loaded.\n\nDo you want to load an existing campaign?\n(Choose 'No' to create a New Campaign)",
        "menu_server": "Server",
        "menu_connect": "Connect to Server...",
        "menu_reconnect": "Reconnect to Last Server",
        "menu_disconnect": "Disconnect",
        "menu_character": "Character",
        "menu_manage_characters": "Character Manager (Offline)...",
        "menu_create_character": "Create New Character (Wizard)...",
        "menu_create_manual_character": "Create Manual Character...",
        "menu_active_sheet": "Active Character Sheet...",
        "char_manager_title": "D&D OmniCompanion • Character Manager",
        "char_manager_header": "Character Manager (Offline)",
        "char_manager_desc": "Create, customize and export your heroes without needing to connect to a server.",
        "char_manager_btn_wizard": "✨ New (Wizard)",
        "char_manager_btn_manual": "➕ Manual",
        "char_manager_btn_duplicate": "📋 Duplicate",
        "char_manager_btn_delete": "🗑️ Delete",
        "char_manager_btn_open_sheet": "📜 Open Full Sheet",
        "char_manager_btn_export": "📄 Export PDF / JSON",
        "char_manager_btn_select": "🎮 Select as Active",
        "char_manager_filter_placeholder": "Search by name, class or race...",
        "char_manager_no_selection": "Select a character from the list on the left to view details or make changes.",
        "char_manager_delete_confirm": "Are you sure you want to permanently delete character '{name}'?",
        "char_manager_count": "{count} character(s) saved locally",
        "menu_library": "Library",
        "menu_language": "🌐 Language / Lingua",
        "menu_units": "📏 Distance Units",
        "unit_feet": "Feet / Miles (ft / mi)",
        "unit_meters": "Meters / Kilometers (m / km)",
        "unit_changed_toast": "Distance unit set to: {unit}",

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
        "lbl_round": "Round: {round}",
        "btn_roll_monster_init": "🎲 Roll Monster Initiative",
        "btn_spawn_npc": "➕ Add NPC",
        "btn_split_gold": "💰 Split Gold",
        "btn_hide_reveal_npc": "👁️ Hide/Reveal NPC",
        "dm_party_header": "--- PARTY MEMBERS ---",
        "dm_npc_header": "--- NPCS & MONSTERS ---",

        # --- Client / Player Panels ---
        "tab_chat": "Chat",
        "tab_player_controls": "Character Controls",
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
        "sheet_tab_journal": "📖 Biography & Journal",
        "sheet_tab_quick_notes": "📝 Session Notes",
        "adv_normal": "Normal",
        "adv_advantage": "Advantage",
        "adv_disadvantage": "Disadvantage",
        "insp_none": "☆ No Inspiration",
        "insp_active": "★ Inspiration Active!",
        "sheet_total_weight": "Total Weight: {current} / {max} lbs",
        "sheet_encumbered": "(ENCUMBERED!)",
        "container_backpack": "🎒 Backpack",
        "container_equipped": "⚔️ Equipped / On Person",
        "container_bag_of_holding": "🔮 Bag of Holding",
        "container_haversack": "✨ Heward's Handy Haversack",
        "container_mount": "🐴 Saddlebag / Mount",
        "btn_drop_backpack": "🎒 Drop Backpack to Ground",
        "btn_pickup_backpack": "🎒 Pick Up Backpack",
        "status_backpack_worn": "🎒 Backpack: Worn",
        "status_backpack_ground": "⚠️ Backpack: On Ground (Weight excluded)",
        "msg_backpack_dropped": "🎒 {name} drops their backpack to the ground to move freely! (Object Interaction, PHB p. 190)",
        "msg_backpack_picked_up": "🎒 {name} picks up their backpack and shoulders it.",
        "enc_normal": "🟢 Normal",
        "enc_encumbered": "🟡 Encumbered (-10 ft / -3 m spd)",
        "enc_heavily_encumbered": "🔴 Heavily Encumbered (-20 ft / -6 m spd, Disadvantage)",
        "enc_overloaded": "⛔ Overloaded (Movement 0)",
        "lbl_container": "Location / Container:",
        "lbl_coins_weight": "Coins: {weight} lbs",
        "lbl_boh_capacity": "🔮 Bag of Holding: {cur} / 500 lbs",
        "lbl_haversack_capacity": "✨ Handy Haversack: {cur} / 120 lbs",
        "lbl_mount_capacity": "🐴 Saddlebag: {cur} lbs",
        "lbl_backpack_ground_weight": "🎒 On Ground: {weight} lbs",
        "sheet_you_are_dead": "☠ YOU ARE DEAD ☠",
        "sheet_active_conditions": "Active Conditions:",
        "sheet_currency": "Coin Pouch",
        "sheet_currency_total": "Total Estimated Value",
        "sheet_item": "Item",
        "sheet_weight_col": "Weight (lbs)",
        "sheet_attunement": "Attunement",
        "sheet_empty_slot": "Empty",
        "sheet_empty_slot_desc": "Empty Slot (Click to add)",
        "sheet_search_compendium": "📚 Search Compendium",
        "sheet_add_custom_item": "✏️ New Item",
        "sheet_give_gold_btn": "🤝 Give Gold to Ally",
        "sheet_spell_slots_header": "Spell Slots (Max / Current)",
        "sheet_attunement_count": "Attunement: {count}/3 🔮",
        "sheet_item_actions": "Actions",
        "sheet_item_edit": "Details",
        "sheet_item_discard": "Discard",
        "sheet_item_trade": "Give",
        "sheet_discard_confirm": "Do you want to discard this item? It will be permanently lost.",
        "coin_cp_title": "Copper (cp)",
        "coin_sp_title": "Silver (sp)",
        "coin_ep_title": "Electrum (ep)",
        "coin_gp_title": "Gold (gp)",
        "coin_pp_title": "Platinum (pp)",
        "coin_cp_sub": "1/100 gp",
        "coin_sp_sub": "1/10 gp",
        "coin_ep_sub": "1/2 gp",
        "coin_gp_sub": "Base 1.0 gp",
        "coin_pp_sub": "10.0 gp",
        "tooltip_coin_cp": "Copper pieces (cp):\n100 cp = 1 gp",
        "tooltip_coin_sp": "Silver pieces (sp):\n10 sp = 1 gp",
        "tooltip_coin_ep": "Electrum pieces (ep):\n2 ep = 1 gp",
        "tooltip_coin_gp": "Gold pieces (gp):\nStandard 5e currency reference",
        "tooltip_coin_pp": "Platinum pieces (pp):\n1 pp = 10 gp",
        "btn_request_currency": "🤝 Request Currency from DM",
        "title_request_currency": "Request Currency from Dungeon Master",
        "lbl_request_coin": "Coin Type:",
        "lbl_request_amount": "Amount to Request:",
        "lbl_request_reason": "Reason (e.g. quest reward, loot, trade):",
        "msg_request_currency_sent": "Request for {amount} {coin} sent to the DM. Waiting for approval.",
        "msg_currency_locked_online": "During a live session you cannot unilaterally increase currency. Use 'Request Currency from DM' to ask the DM.",
        "msg_item_approval_sent": "Request for '{item}' sent to the DM. It will be added once approved.",
        "msg_attr_locked_online": "Attribute score locked during session. Increases occur via Level Up or DM grant.",
        "msg_hp_max_locked_online": "Max Hit Points are locked during session.",
        "msg_hp_cur_locked_online": "Hit Points during session are managed by combat events, rests, and the Dungeon Master.",

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
        "turn_economy_exploration": "⚡ Turn Economy • 🧭 Exploration",
        "turn_economy_my_turn": "⚡ Turn Economy • 🟢 YOUR TURN",
        "turn_economy_other_turn": "⚡ Turn Economy • ⏳ Other's Turn",
        "turn_economy_reset": "↺ Reset",
        "tooltip_reset_economy": "Reset turn resources",
        "btn_act": "⚔️ Action",
        "tooltip_act": "Standard Action: click to toggle spent/available",
        "btn_bonus": "✨ Bonus",
        "tooltip_bonus": "Bonus Action: click to toggle spent/available",
        "btn_react": "🛡️ React",
        "tooltip_react": "Reaction: click to toggle spent/available",
        "lbl_movement": "👟 Movement: {used} / {total} ft (Left: {rem} ft)",
        "lbl_movement_exploration": "🧭 Exploration: Free movement (Base: {base})",
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
        "weather_clear": "Clear",
        "weather_rain": "Rain",
        "weather_storm": "Storm",
        "weather_snow": "Snow",
        "weather_fog": "Fog",
        "weather_darkness": "Darkness",
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

        # --- Quick NPC Generator & Loot (dm_generators.py) ---
        "npc_gen_title": "D&D OmniCompanion • Quick NPC Generator",
        "npc_gen_header": "🎭 Quick NPC Generator",
        "npc_gen_subtitle": "Quickly create non-player characters with personality, secrets, and stats",
        "npc_gen_name": "Name:",
        "npc_gen_hp": "HP:",
        "npc_gen_ac": "AC:",
        "npc_gen_race_role": "Race & Role:",
        "npc_gen_alignment": "Alignment:",
        "npc_gen_personality_traits": "NPC Personality, Traits & Secrets:",
        "npc_gen_role_prefix": "Role:",
        "npc_gen_trait_prefix": "Distinctive Trait:",
        "npc_gen_secret_prefix": "Secret / Motivation:",
        "btn_generate_another_npc": "🔄 Generate Another NPC",
        "btn_spawn_token_map": "⚡ Spawn Token on Map",
        "btn_save_to_campaign": "💾 Save to Campaign",
        "msg_npc_spawned_title": "NPC Spawned",
        "msg_npc_spawned_desc": "Token for '{name}' successfully created on map!",
        "msg_npc_saved_title": "Saved",
        "msg_npc_saved_desc": "NPC '{name}' saved into campaign '{campaign}'!",
        "msg_no_campaign_title": "No Campaign",
        "msg_no_campaign_desc": "No active campaign loaded. Load or create a campaign from File menu.",
        "loot_gen_title": "D&D OmniCompanion • 5e Loot Generator",
        "loot_gen_header": "💰 Treasure & Loot Generator",
        "loot_gen_subtitle": "Generate rewards based on Dungeon Master's Guide (DMG 5e) tables",
        "loot_gen_cr": "Challenge Rating (CR):",
        "loot_gen_type": "Loot Type:",
        "loot_gen_hoard": "Hoard Treasure",
        "loot_gen_individual": "Individual Loot",
        "btn_generate_loot": "🎲 Generate New Loot",
        "loot_coins_summary": "🪙 Coins: {coins}",
        "loot_no_coins": "No coins",
        "loot_value_est": "Estimated Total Value: ~{val} Gold Pieces",
        "col_type": "Type",
        "col_name_desc": "Name / Description",
        "col_properties": "Properties",
        "btn_distribute_gold_party": "💰 Distribute Gold to Party",
        "btn_grant_selected_item": "🎒 Assign Selected Item to Player",
        "msg_no_gold_title": "No Gold",
        "msg_no_gold_desc": "There are no gold coins in this loot.",
        "msg_no_party_players_title": "No Players",
        "msg_no_party_players_desc": "There are no players in the party to distribute gold to.",
        "msg_gold_distributed_title": "Gold Distributed",
        "msg_gold_distributed_desc": "{total} GP successfully distributed ({share} GP each).",
        "msg_select_item_warning": "Select an item or gem from the list.",
        "msg_no_online_players": "No online players to assign the item to.",
        "prompt_assign_item": "Who do you want to assign '{item}' to?\nAvailable players: {players}",
        "msg_item_assigned_title": "Assigned",
        "msg_item_assigned_desc": "'{item}' sent to {player}'s inventory.",

        # --- Dialog Windows DM & Client ---
        "custom_npc_title": "Create New Custom NPC / Monster",
        "custom_npc_name": "NPC / Monster Name:",
        "custom_npc_hp": "Max HP:",
        "custom_npc_init": "Initiative:",
        "custom_npc_ac": "Armor Class (AC):",
        "custom_npc_speed": "Speed (ft):",
        "custom_npc_notes": "Notes / Description (optional):",
        "btn_create_npc_map": "Create NPC & Add to Map",
        "handout_dialog_title": "Share Document / Text Handout",
        "handout_doc_title": "Document Title:",
        "handout_doc_text": "Text to show players:",
        "btn_send_to_players": "Send to Players",
        "msg_handout_shared": "Document shared with all connected players!",
        "aoe_dialog_title": "Place Area of Effect (AoE)",
        "aoe_shape": "Area Shape:",
        "aoe_sphere_cube": "Sphere / Cube",
        "aoe_cone": "Cone",
        "aoe_line": "Line",
        "aoe_size_hexes": "Radius / Length (hexes):",
        "aoe_color": "Color:",
        "color_red": "Red",
        "color_blue": "Blue",
        "color_green": "Green",
        "color_yellow": "Yellow",
        "color_purple": "Purple",
        "aoe_requires_save": "Requires Saving Throw (Auto-roll for targets)",
        "aoe_dc": "DC:",
        "aoe_damage": "Damage:",
        "aoe_half_damage": "Half Damage on Save",
        "aoe_consume_slot": "Consume Spell Slot:",
        "aoe_no_slot": "0 - None / Cantrip",
        "aoe_slot_lvl": "{lvl} - Level {lvl} Slot ({cur}/{mx} avail)",
        "btn_confirm_aoe": "Confirm Area of Effect",
        "aoe_click_map_prompt": "Click on the map to confirm the target / center of the area of effect.",
        "combat_config_title": "Combat Configuration",
        "combat_filter_distance": "Distance Filter (Auto-selection)",
        "combat_origin": "Origin:",
        "combat_radius_hex": "Radius (hexes):",
        "btn_select_nearby": "Select Nearby",
        "combat_participants": "Participants:",
        "npc_init_dialog_title": "NPC Initiative",
        "npc_init_dialog_prompt": "Enter initiative for NPCs:",
        "btn_confirm_initiatives": "Confirm Initiatives",
        "btn_next": "Next",
        "btn_prepare_cast": "Prepare Cast",
        "btn_confirm_select_center": "Confirm & Select Center",
        "aoe_client_dialog_title": "Cast Spell / AoE",
        "aoe_save_auto_damage": "Requires Saving Throw (Automatic Damage)",
        "aoe_save_auto_npc": "Requires Saving Throw (Auto-roll for NPCs)",
        "deploy_encounter_title": "Deploy Campaign Encounter",
        "deploy_encounter_header": "⚔️ Campaign Prepared Encounters",
        "deploy_encounter_subtitle": "Select the encounter to deploy on current map:",
        "col_encounter_name": "Encounter Name",
        "col_act": "Act",
        "col_monsters": "Monsters",
        "col_notes": "Notes",
        "btn_deploy_on_map": "⚡ Deploy on Map",
        "msg_no_encounter_title": "No Encounter",
        "msg_no_encounter_desc": "No active campaign with prepared encounters. Would you like to open the Campaign Editor?",
        "switch_scene_title": "Switch to Campaign Scene",
        "switch_scene_header": "🗺️ Campaign Scenes",
        "msg_no_scene_title": "No Scene",
        "msg_no_scene_desc": "No active campaign with linked scenes.",
        "starter_kit_title": "Configure Campaign Starter Pack (Starting Equipment)",
        "starter_kit_header": "Campaign Starting Equipment",
        "starter_kit_desc": "New PCs will automatically receive these items upon their first login to this campaign:",
        "btn_add_item": "➕ Add Item",
        "btn_edit_selected": "✏️ Edit Selected",
        "btn_remove_selected": "🗑️ Remove Selected",
        "btn_reset_defaults": "Reset Defaults",
        "btn_save_config": "Save Configuration",
        "msg_confirm_reset_starter_kit": "Do you want to reset to the default campaign starter kit?",
        "msg_starter_kit_saved": "Campaign starting equipment successfully saved!",
        "sheet_viewer_title": "Character Sheet: {name}",
        "general_info": "General Information",
        "lbl_class": "Class:",
        "lbl_race": "Race:",
        "lbl_alignment": "Alignment:",
        "lbl_background": "Background:",
        "tab_stats_attributes": "📊 Stats & Attributes",
        "combat": "Combat",
        "hit_points": "Hit Points (HP)",
        "armor_class": "Armor Class (AC)",
        "initiative": "Initiative",
        "speed": "Speed",
        "ability_scores": "Ability Scores",
        "col_ability": "Ability",
        "col_base_score": "Base Score",
        "col_modifier": "Modifier",
        "tab_inventory": "🎒 Inventory",
        "col_item_name": "Item Name",
        "col_quantity": "Quantity",
        "col_weight": "Weight (lbs)",
        "col_desc_effect": "Description / Effect",
        "coin_pouch": "Coin Pouch",
        "tab_spellbook": "✨ Spellbook",
        "spell_slots": "Spell Slots",
        "col_level": "Level",
        "col_spell_name": "Spell Name",
        "col_casting_time": "Cast Time",
        "col_range": "Range",
        "tab_features_notes": "📜 Features & Notes",
        "features_traits": "Features & Traits:",
        "notes_background": "Notes & Background:",
        "btn_close_sheet": "Close Sheet",
        "msg_select_at_least_one_participant": "Select at least one participant.",
        "msg_combat_already_running": "A combat is already running.",
        "msg_no_players_combat": "No character/NPC to start combat.",
        "msg_combat_end_title": "End Combat",
        "msg_combat_end_confirm": "Do you want to end combat?",
        "col_skill_prof": "Prof.",
        "col_skill_name": "Skill (Stat)",
        "col_skill_bonus": "Bonus",
        "col_skill_roll": "Roll",
        "tooltip_skill_prof": "Proficiency Level:\n0 = None\n1 = Proficient (+PB)\n2 = Expertise (+2×PB)",
        "tooltip_skill_bonus": "Total calculated modifier (Ability + Proficiency) added to d20",
        "tooltip_skill_combo": "0 = None\n1 = Proficient (+PB)\n2 = Expertise (+2×PB)",
        "btn_close": "Close",
        "cantrip": "Cantrip",
        "col_description": "Description",
        "msg_content_cannot_empty": "Content cannot be empty.",
        "msg_entity_exists": "An entity with this name already exists.",
        "msg_name_required": "Name is required.",
        "msg_stat_integer": "Stat values must be valid numbers.",
        "msg_title_required": "Title is required.",
        "no_features_registered": "No special features registered.",
        "no_notes_present": "No notes present.",
        "prompt_item_desc": "Item description or effect:",
        "prompt_item_type": "Type (Weapon, Armor, Consumable, Document, Currency, Equipment):",
        "text_inventory": "Text Inventory",
        "text_spells": "Text Spells",
        "token_size_menu": "Token Size",
        "size_tiny": "Tiny",
        "size_small": "Small",
        "size_medium": "Medium",
        "size_large": "Large",
        "size_huge": "Huge",
        "size_gargantuan": "Gargantuan",
        "ctx_toggle_gm_layer": "GM Layer (Hidden from Players)",
        "ctx_move_to_gm_layer": "Move to GM Layer",
        "ctx_move_to_token_layer": "Move to Token Layer",
        "grid_type_menu": "Grid Type",
        "grid_hex": "Hexagonal (Hex)",
        "grid_square": "Square Grid",
        "grid_none": "Gridless",
        "grid_type_pill": "🌐 Grid: {type}",
        "map_env_outdoor": "🌲 Outdoor",
        "map_env_indoor": "🏰 Indoor / Dungeon",
        "map_env_tooltip": "Map Environment Type (Click to toggle between Outdoor and Indoor / Dungeon)",
        "map_env_switched": "[ENVIRONMENT] Map type set to: {env}.",
        "period_dawn": "Dawn",
        "period_day": "Day",
        "period_dusk": "Dusk",
        "period_night": "Night",
        "period_indoor": "Indoor",
        "period_manual": "Manual",
        "fow_brush_radius": "Brush:",
        "tool_pen": "Freehand Pen",
        "tool_clear_drawings": "Clear Map Drawings",
        "menu_export_session_log": "Export Session Log...",
        "export_log_title": "D&D Session Journal",
        "export_log_saved": "Session journal successfully exported to:\n{path}",
        "export_log_empty": "Chat history is empty, no messages to export.",
        # --- New 5e RAW Features (Light, Cover, Hit Dice, and Quests) ---
        "light_torch": "Torch",
        "light_hooded_lantern": "Hooded Lantern",
        "light_dim_hooded": "Hooded Lantern (Dim)",
        "light_spell": "Light Spell",
        "btn_toggle_light": "Toggle Light Source",
        "cover_none": "No Cover (0 AC)",
        "cover_half": "Half Cover (+2 AC, +2 DEX saves)",
        "cover_three_quarters": "Three-Quarters Cover (+5 AC, +5 DEX saves)",
        "cover_total": "Total Cover (Blocked)",
        "short_rest_title": "Short Rest (D&D 5e)",
        "short_rest_roll_die": "Roll 1 Hit Die",
        "short_rest_spend_all": "Spend All Hit Dice",
        "short_rest_finish": "Finish Rest",
        "quest_log_title": "Quest & Objectives Log",
        "quest_status_in_progress": "In Progress",
        "quest_status_completed": "Completed",
        "quest_status_failed": "Failed",
        # --- Advanced UI Translations ---
        "launcher_dm_sub": "MASTER & CAMPAIGN MANAGEMENT",
        "launcher_player_sub": "HEROES, 5E SHEETS & VTT",
        "campaign_lib_title": "Prepared Campaign Library",
        "campaign_editor_title": "Campaign Editor: {title}",
        "wizard_window_title": "Character Creation Wizard",
        "btn_back_to_menu": "← Menu",

        # --- Character Creation Wizard ---
        "wizard_step1_title": "Step 1: Choose Race",
        "wizard_step2_title": "Step 2: Choose Class",
        "wizard_step3_title": "Step 3: Ability Scores (Standard Array)",
        "wizard_step4_title": "Step 4: Choose Background & Skills",
        "wizard_step5_title": "Step 5: Backstory, Goals & Final Details",
        "wizard_btn_prev": "← Previous Step",
        "wizard_btn_next": "Next Step →",
        "wizard_btn_finish": "Finish & Create Character",
        "wizard_step1_desc": "Race defines your biological and cultural heritage, ability score bonuses, size, speed, and innate traits.",
        "wizard_step1_filter_hint": "Filter and compare the 9 core races: bonuses, resistances, and synergies. Click a row for detailed preview.",
        "wizard_step2_desc": "Class defines your vocation, martial or magical skills, special features, and tactical party role.",
        "wizard_step2_filter_hint": "Compare Hit Dice, Tactical Role, Primary Abilities, and Complexity to choose your path.",
        "wizard_step3_desc": "Assign the standard array (15, 14, 13, 12, 10, 8) to the 6 abilities. Racial bonuses are applied automatically.",
        "wizard_step4_desc": "Your background shapes your skill proficiencies, social features, and starting equipment.",
        "wizard_step5_desc": "Define your name, alignment, ideals, bonds, flaws, and visual token appearance.",
        "wizard_lbl_race": "🧬 Race:",
        "wizard_lbl_subrace": "🌿 Subrace:",
        "wizard_lbl_class": "⚔️ Class:",
        "wizard_lbl_speed_size": "🏃 Speed & Size:",
        "wizard_lbl_traits": "🧬 Innate Racial Traits",
        "wizard_lbl_hit_die": "🎲 Hit Die:",
        "wizard_lbl_saving_throws": "🛡️ Saving Throws:",
        "wizard_lbl_proficiencies": "⚔️ Proficiencies:",
        "wizard_lbl_skills": "🎯 Skill Proficiencies:",
        "wizard_lbl_features": "⚔️ Key Level 1 Features",
        "wizard_lbl_equipment": "🎒 Class Starting Equipment",
        "wizard_lbl_spells": "✨ Magic & Starting Spells (Level 1):",
        "wizard_lbl_token": "🖼️ Character Portrait & Map Token",
        "wizard_lbl_alignment": "⚖️ Alignment:",
        "wizard_btn_choose_race": "✓ Choose This Race",
        "wizard_btn_choose_class": "✓ Choose This Class",
        "wizard_btn_roll_random": "🎲 Roll All Random Traits",
        "wizard_msg_name_required": "Character name is required.",
        "wizard_traits_key": "Key Racial Traits",
        "wizard_stat_bonus": "Ability Score Bonuses",
        "wizard_half_elf_bonus": "✨ Half-Elf +1 Bonus (2 Abilities):",
        "wizard_class_synergies": "⭐ Recommended Class Synergies:",
        "wizard_filter_label": "Filter:",
        "wizard_search_label": "🔍 Search:",
        "wizard_token_no_image": "No image (token with initials)",
        "wizard_quick_advice": "💡 Quick Creation Tip (for Step 3):",
        "wizard_aspect_token": "Character Appearance & Game Token:",
        "btn_prev": "◀ Prev",
        "btn_next_arrow": "Next ▶",
        "btn_remove": "❌ Remove",
        "lbl_size": "Size",
        "lbl_category": "Category",
        "wizard_btn_comparison_table": "📊 Comparison Table",
        "wizard_senses": "👁️ Senses:",
        "wizard_languages": "🗣️ Languages:",
        "wizard_resistances_defenses": "🛡️ Resistances & Defenses:",
        "wizard_overview_lore": "📖 Overview & Narrative Lore",
        "wizard_subraces_variants": "🌿 Subraces & Famous Variants",
        "wizard_lifespan": "⏳ Lifespan & Maturity:",
        "wizard_optimal_for": "Optimal for",
        "wizard_step3_instruction": "Assign values: 15, 14, 13, 12, 10, 8\nValues will swap automatically to avoid duplicates.",
        "wizard_err_standard_array": "You must assign each Standard Array value (15,14,13,12,10,8) exactly once.",
        "wizard_cat_all": "All",
        "wizard_cat_martial": "Martial",
        "wizard_cat_magical": "Spellcasters",
        "wizard_cat_hybrid": "Hybrid",
        "wizard_primary_stat": "⭐ Primary Ability:",
        "wizard_quick_build_tip": "💡 Quick Build Recommendation (for Step 3):",
        "wizard_starter_gear": "🎒 Starting Equipment (provided at start):",
        "wizard_starter_spells": "✨ Starting Magic & Spells (Level 1):",
        "wizard_class_overview": "📖 Narrative Identity & Overview",
        "wizard_lvl1_features": "⚔️ Key Level 1 Features",
        "wizard_playstyle_role": "🎯 Playstyle & Party Role",
        "wizard_subclasses_archetypes": "🔮 Future Archetypes & Subclasses",
        "wizard_hp_at_lvl1": "HP at 1st",
        "wizard_lbl_bg": "5e Background:",
        "wizard_choose_2_skills": "Choose 2 Skills:",
        "wizard_rp_pillars": "🎭 The 4 Roleplaying Pillars (D&D 5e)",
        "wizard_rp_trait": "Personality Trait (Habits & Mannerisms):",
        "wizard_rp_ideal": "Ideal (Ethical or moral principle):",
        "wizard_rp_bond": "Bond (Person, place or memory you'd die for):",
        "wizard_rp_flaw": "Flaw (Secret vice, weakness or phobia):",
        "wizard_feat_label": "Feature",
        "wizard_equip_gold_label": "Starting Equipment & Gold",
        "wizard_origin_place": "Origin / City:",
        "wizard_origin_default": "Homeland",
        "wizard_token_card_title": "🖼️ Character Portrait & Map Token",
        "wizard_token_desc": "The selected image will be cropped to a circle and used as an interactive token on the map.",
        "wizard_token_none_set": "No image set",
        "wizard_token_none_initials": "No image (initials token)",
        "wizard_token_loaded": "Image loaded",
        "wizard_choose_image": "📁 Choose Image...",
        "wizard_alignment_tip": "💡 Optional Alignment: In D&D 5e, alignment is merely an ethical compass and roleplay guideline. It never forces your decisions: player choices always take precedence.",
        "wizard_personal_quest": "🎯 Personal Quest / Adventure Hook:",
        "wizard_character_secret": "🔒 Character Secret (for the DM):",
        "wizard_dm_only": "[Visible only to you and the DM]",
        "wizard_party_tie": "🤝 Party Tie (Bond with Party):",
        "wizard_trinket": "🗝️ Personal Trinket (Sentimental Kept Item):",
        "wizard_bio_story": "📖 Hero Biography & Backstory:",
        "wizard_btn_compose": "✨ Compose Backstory",
        "wizard_btn_variation": "🎲 Variation",
        "wizard_lbl_style": "🎨 Narrative Style:",
        "wizard_style_heroic": "Heroic & Epic",
        "wizard_style_dark": "Dark Fantasy & Gritty",
        "wizard_style_mysterious": "Mysterious & Arcane",
        "wizard_style_picaresque": "Picaresque & Adventurous",
        "wizard_msg_char_created": "Character '{name}' successfully created!",
        "wizard_dlg_classes_title": "Comparison Table of 12 Classes (D&D 5e)",
        "wizard_dlg_classes_header": "📊 Quick Classes Comparison",
        "wizard_dlg_classes_desc": "Compare Hit Dice, Tactical Role, Primary Abilities, and Complexity to choose your ideal hero. Double-click a row to select.",
        "wizard_party_role": "Party Role",
        "wizard_complexity": "Complexity",
        "wizard_dlg_races_title": "Races Compendium & Comparison (D&D 5e)",
        "wizard_dlg_races_header": "📊 Races Compendium & Comparison (D&D 5e)",
        "wizard_chip_all": "All (9)",
        "wizard_chip_res": "🛡️ Resistances",
        "wizard_chip_darkvision": "👁️ Darkvision",
        "wizard_chip_small": "🏃 Small Size",
        "wizard_chip_melee": "⚔️ Melee / Strength",
        "wizard_chip_magic": "✨ Magic / Charisma",
        "wizard_dlg_choose_race": "✓ Choose This Race",
        "wizard_dlg_race_tip": "💡 Tip: Select a race to view details or click 'Choose This Race'.",
        "wizard_dlg_races_taglia_vel": "Size / Spd",
        "wizard_dlg_races_classi": "Recommended Classes",
        "wizard_dlg_res_box": "🛡️ Resistances, Immunities & Defenses",
        "wizard_dlg_syn_box": "⭐ Synergies & Ideal Classes",
        "wizard_dlg_traits_box": "🧬 Racial Traits",
        "wizard_dlg_subraces_box": "🌿 Subraces & Variants",
        "wizard_vision_normal": "Normal",
        "wizard_languages_common": "Common",
        "wizard_resistances_none": "None",
        "wizard_size": "Size",

        # --- Level Up Progression ---
        "prog_title": "Level Up Progression",
        "prog_tab_hp": "Hit Point Increase (HP)",
        "prog_tab_features": "⚔️ New Features",
        "prog_tab_subclass": "🌟 Subclass",
        "prog_tab_asi": "💪 Ability Score (ASI)",
        "prog_tab_spells": "✨ Spells",
        "prog_hp_mode_avg": "Average (Recommended)",
        "prog_hp_mode_roll": "Roll Hit Die",
        "prog_btn_roll": "🎲 Roll Die",
        "prog_btn_apply": "✅ Apply & Level Up",
        "prog_subclass_header": "Official 5e Subclass",
        "prog_asi_header": "Ability Score Improvement or Feat",
        "prog_asi_dual_error": "In dual mode (+1 to two abilities), you must select two different abilities!",
        "prog_spells_header": "Selected Spells: {count}",
        "prog_btn_add_spell": "➕ Add to Spellbook",
        "prog_btn_remove_spell": "➖ Remove Selection",
        "prog_total_hit_dice": "Total Hit Dice",
        "prog_die_result": "Die Result (without Constitution):",
        "prog_choose_feat": "Choose an Official 5e Feat:",
        "prog_no_spell_slots": "This class does not use spell slots to cast spells.",
        "prog_compendium_hint": "You can consult the spell compendium at any time using the button below.",
        "prog_loading": "Loading 5e progression...",
        "prog_loaded_srd": "Progression data loaded (Official 5e SRD)",

        # --- Character Sheet UI ---
        "sheet_header_subclass": "Subclass:",
        "sheet_header_background": "Background:",
        "sheet_header_alignment": "Alignment:",
        "sheet_btn_detach": "◱ Detach Window",
        "sheet_btn_dock": "◰ Dock to Map",
        "sheet_btn_quick_save": "💾 Save (Ctrl+S)",
        "sheet_btn_close_esc": "✕ Close (Esc)",
        "sheet_btn_token": "📷 Token",
        "sheet_saves_header": "Saving Throws",
        "sheet_weapons_header": "⚔️ 5e Quick Attacks & Weapons",
        "sheet_weapons_empty": "No weapon equipped.\nClick '+ Add Weapon' to record a weapon or attack!",
        "sheet_weapons_add": "➕ Add Weapon",
        "sheet_weapons_to_hit": "To Hit",
        "sheet_weapons_dmg": "Damage",
        "sheet_weapons_target": "🎯 Target ({txc})",
        "sheet_weapons_attack": "🎲 Roll To Hit",
        "sheet_weapons_hit": "🎯 Strike ({txc})",
        "sheet_weapons_damage_btn": "💥 Damage",
        "sheet_features_resources": "⚡ Special Class Resources (Ki, Rage, Inspiration, etc.)",
        "sheet_features_new_resource": "+ New Resource",
        "sheet_features_header": "📜 Class Features, Racial Traits & Feats",
        "sheet_features_propose": "📤 Propose to DM",
        "sheet_features_view_text": "👁️ Text View",
        "sheet_features_view_cats": "👁️ Category View",
        "sheet_features_delete": "🗑️ Delete",
        "sheet_features_edit": "✏️ Edit",
        "sheet_features_add": "➕ Add Feature",
        "sheet_features_placeholder": "Select a trait or feature",
        "sheet_features_no_resources": "No special resources recorded. Click '+ New Resource' to track Ki, Rage, Bardic Inspiration, etc.",
        "sheet_journal_title": "📖 Character Biography & Journal",
        "sheet_journal_sub": "Backstory, bonds, ideals, secrets, and adventure journal (supports Markdown #, ##, **, *, •)",
        "sheet_notes_title": "📝 Session Notes & Quick Logs",
        "sheet_notes_sub": "Clues, promises, met NPCs, maps, and tactical notes (supports Markdown #, ##, **, *)",
        "sheet_btn_generate_story": "✨ Generate Backstory",
        "sheet_btn_save_changes": "💾 Save Changes",
        "sheet_btn_edit_text": "✏️ Edit Text",
        "sheet_btn_view_markdown": "👁️ Formatted View (Markdown)",
        "sheet_badge_dm_approval": "🔒 DM Approval Active",
        "sheet_spellbook_add_btn": "➕ New Spell",
        "sheet_spellbook_srd_btn": "📚 Search Compendium (SRD)",
        "sheet_spellbook_cast_btn": "Details / Cast",
        "sheet_spellbook_upcast": "⚡ Upcast at Level:",
        "sheet_spellbook_cast_chat": "Cast in Chat",
        "sheet_spellbook_attack_target": "Attack Target",
        "sheet_short_rest_subtitle": "Spend Hit Dice to recover HP and regain class features.",
        "sheet_short_rest_log": "Rest Roll Log:",
        "sheet_short_rest_roll_hd": "🎲 Roll 1 Hit Die",
        "sheet_short_rest_spend_all": "⚡ Spend All",
        "sheet_short_rest_finish": "✅ Finish Rest",
        "sheet_export_dialog_title": "Character Export",
        "sheet_export_dialog_sub": "Choose the desired format for export:",
        "sheet_export_pdf_card": "📄 Official 5e Character Sheet (PDF)",
        "sheet_export_pdf_desc": "Select the blank PDF template to automatically fill out the 3-page official sheet.",
        "sheet_export_pdf_btn": "Export PDF",
        "sheet_export_json_card": "💾 Character Data File (JSON)",
        "sheet_export_json_desc": "Save raw character data for backup, manual editing, or re-import.",
        "sheet_export_json_btn": "Export JSON",
        "sheet_btn_export_dialog": "📥 Export PDF / JSON...",
        "sheet_toast_saved": "Changes successfully saved to character sheet!",
        "sheet_toast_long_rest": "You finished a long rest! HP, Hit Dice, Death Saves, and Spell Slots have been restored.",
        "sheet_crit_success_title": "CRITICAL HIT!",
        "sheet_crit_fail_title": "CRITICAL MISS!",
        "container_filter_label": "Container:",
        "container_filter_all": "📦 All Items",
        "item_action_spend_one": "🏹 Use 1",
        "item_action_spend_custom": "🔢 Use...",
        "item_action_unpack": "📦 Unpack",
        "item_action_save": "💾 Save",
        "item_action_trade": "🤝 Give",
        "item_action_discard": "🗑️ Discard",
        "item_action_details": "✏️ Edit Details...",
        "item_action_remove_request": "🗑️ Request Removal...",
        "item_requires_attunement": "Requires Attunement 🔮",
        "item_attuned": "Attuned Item 🔮",
        "empty_slot_number": "Slot #{num} Empty",
        "add_item_title": "✨ New Item (Slot #{num})",
        "weapon_sheet_title": "⚔️ 5e Weapon Sheet",
        "weapon_name": "Weapon Name:",
        "weapon_type_props": "Type / Properties:",
        "weapon_attr_txc": "Attribute (To Hit & Damage):",
        "weapon_damage_die": "Damage Die:",
        "weapon_damage_type": "Damage Type:",
        "weapon_magic_bonus": "Magic Bonus (+X):",
        "weapon_proficient": "Proficient with Weapon (+ Proficiency to Attack)",
        "weapon_btn_save": "Save Weapon",
        "login_select_char": "Select Character:",
        "login_btn_create": "Create New",
        "login_btn_edit": "Edit",
        "login_btn_delete": "Delete",
        "login_btn_connect": "Connect",
        "login_no_char_selected": "Select or create a character to connect.",
    }
}



SUPPORTED_DISTANCE_UNITS = {
    "ft": "Piedi / Feet (ft)",
    "m": "Metri / Meters (m)"
}
_current_distance_unit = "ft"
_unit_listeners = []


def _load_settings():
    """Carica le impostazioni da client_data/settings.json se presente."""
    global _current_language, _current_distance_unit
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                lang = data.get("language")
                if lang in SUPPORTED_LANGUAGES:
                    _current_language = lang
                unit = data.get("distance_unit")
                if unit in SUPPORTED_DISTANCE_UNITS:
                    _current_distance_unit = unit
    except Exception as e:
        print(f"[i18n] Errore lettura settings: {e}")


def _save_settings():
    """Salva la lingua corrente e l'unità di misura in client_data/settings.json."""
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
        data["distance_unit"] = _current_distance_unit
        
        # Scrittura atomica
        tmp_path = SETTINGS_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SETTINGS_PATH)
    except Exception as e:
        print(f"[i18n] Errore salvataggio settings: {e}")


# Inizializza impostazioni all'importazione
_load_settings()


def get_distance_unit() -> str:
    """Restituisce l'unità di misura corrente ('ft' o 'm')."""
    with _lock:
        return _current_distance_unit


def set_distance_unit(unit_code: str):
    """Imposta l'unità di misura corrente ('ft' o 'm') e salva le impostazioni."""
    global _current_distance_unit
    if unit_code not in SUPPORTED_DISTANCE_UNITS:
        return
    with _lock:
        if _current_distance_unit == unit_code:
            return
        _current_distance_unit = unit_code
        _save_settings()
        listeners_copy = list(_unit_listeners)
    dead_listeners = []
    for cb in listeners_copy:
        try:
            cb(_current_distance_unit)
        except Exception as e:
            err_msg = str(e)
            if "destroyed" in err_msg or "cannot invoke" in err_msg:
                dead_listeners.append(cb)
            else:
                print(f"[i18n] Errore callback unità: {e}")
    if dead_listeners:
        with _lock:
            for d in dead_listeners:
                if d in _unit_listeners:
                    _unit_listeners.remove(d)


def toggle_distance_unit() -> str:
    """Inverte l'unità di misura tra 'ft' e 'm' e restituisce la nuova unità."""
    new_u = "m" if get_distance_unit() == "ft" else "ft"
    set_distance_unit(new_u)
    return new_u


def register_unit_listener(callback_fn):
    with _lock:
        if callback_fn not in _unit_listeners:
            _unit_listeners.append(callback_fn)


def unregister_unit_listener(callback_fn):
    """Rimuove un listener di unità registrato."""
    with _lock:
        if callback_fn in _unit_listeners:
            _unit_listeners.remove(callback_fn)


def convert_speed_value(val, from_unit: str, to_unit: str):
    """Converte un valore di velocità tra piedi ('ft') e metri ('m'). 5 ft = 1.5 m."""
    try:
        v = float(val)
    except (ValueError, TypeError):
        return 9 if to_unit == "m" else 30
    if from_unit == to_unit:
        return int(v) if v == int(v) else round(v, 1)
    if from_unit == "ft" and to_unit == "m":
        res = round((v / 5.0) * 1.5, 1)
        return int(res) if res == int(res) else res
    if from_unit == "m" and to_unit == "ft":
        return int(round((v / 1.5) * 5.0))
    return int(v) if v == int(v) else round(v, 1)


def speed_to_hexes(speed_val, unit: str = None) -> int:
    """
    Converte il valore di velocità in numero di esagoni (1 esagono = 5 ft = 1.5 m).
    Se unit non è specificato o c'è ambiguità legacy (es. speed=9 salvato senza unità),
    gestisce in modo intelligente valori <= 18 come metri e >= 20 come piedi.
    Supporta anche dict, list e stringhe complesse normalizzandoli preventivamente.
    """
    if isinstance(speed_val, (dict, list)) or (isinstance(speed_val, str) and not speed_val.isdigit()):
        try:
            from common.srd_offline import normalize_speed_value
            s_val, _, s_u = normalize_speed_value(speed_val, default_unit=unit)
            v = float(s_val)
            if unit is None:
                unit = s_u
        except Exception:
            try:
                v = float(speed_val)
            except (ValueError, TypeError):
                return 6
    else:
        try:
            v = float(speed_val)
        except (ValueError, TypeError):
            return 6

    if v <= 0:
        return 0
    if unit == "m" or (unit is None and v <= 18):
        return max(1, int(round(v / 1.5)))
    return max(1, int(v // 5))


def get_map_scale_info(map_data: dict = None, unit: str = None) -> dict:
    """
    Determina la scala della mappa attiva (Combattimento, Esplorazione/Provincia, Mondo/Regione o Personalizzata)
    e la distanza rappresentata da 1 singolo esagono nell'unità scelta ('ft'/'mi' oppure 'm'/'km').
    Regole D&D 5e (DMG p. 14):
      - Combattimento (hex_size=60 o default 30): 1 hex = 5 ft (Imperiale) / 1.5 m (Metrico)
      - Esplorazione / Provincia (hex_size=35): 1 hex = 1 mi (Imperiale) / 1.5 km (Metrico)
      - Mondo / Regione (hex_size=15): 1 hex = 6 mi (Imperiale) / 9 km (Metrico)
    """
    u = unit if unit in ("ft", "m") else get_distance_unit()
    is_metric = (u == "m")
    lang = get_language()

    if not isinstance(map_data, dict):
        per_hex = 1.5 if is_metric else 5.0
        u_lbl = "m" if is_metric else "ft"
        return {
            "scale_type": "combat",
            "scale_name": ("Combattimento" if lang == "it" else "Combat"),
            "per_hex": per_hex,
            "unit_label": u_lbl,
            "hex_size": 30,
            "hours_per_hex": 0.0,
        }

    hex_size = map_data.get("hex_size", 30) or 30
    explicit_type = str(map_data.get("map_scale_type", "")).strip().lower()

    # Inferenza automatica da hex_size se map_scale_type non è specificato
    if explicit_type in ("combat", "exploration", "world", "custom"):
        scale_type = explicit_type
    else:
        if hex_size <= 20:
            scale_type = "world"
        elif 20 < hex_size <= 45 and hex_size != 30:
            scale_type = "exploration"
        else:
            scale_type = "combat"

    # Controllo scala personalizzata esplicita (es. hex_scale_ft / hex_scale_value)
    custom_val = map_data.get("hex_scale_value")
    custom_unit = map_data.get("hex_scale_unit")
    if scale_type == "custom" and custom_val is not None:
        try:
            val_f = float(custom_val)
        except (ValueError, TypeError):
            val_f = 1.5 if is_metric else 5.0
        if custom_unit in ("ft", "m", "mi", "km"):
            # Converti automaticamente se l'utente ha cambiato sistema Imperiale <-> Metrico
            if custom_unit == "ft" and is_metric:
                per_hex, u_lbl = round((val_f / 5.0) * 1.5, 2), "m"
            elif custom_unit == "m" and not is_metric:
                per_hex, u_lbl = round((val_f / 1.5) * 5.0, 2), "ft"
            elif custom_unit == "mi" and is_metric:
                per_hex, u_lbl = round(val_f * 1.5, 2), "km"
            elif custom_unit == "km" and not is_metric:
                per_hex, u_lbl = round(val_f / 1.5, 2), "mi"
            else:
                per_hex, u_lbl = val_f, custom_unit
        else:
            per_hex = val_f
            u_lbl = "m" if is_metric else "ft"
        return {
            "scale_type": "custom",
            "scale_name": ("Personalizzata" if lang == "it" else "Custom"),
            "per_hex": per_hex,
            "unit_label": u_lbl,
            "hex_size": hex_size,
            "hours_per_hex": (per_hex / 4.5 if u_lbl == "km" else (per_hex / 3.0 if u_lbl == "mi" else 0.0)),
        }

    if scale_type == "world":
        per_hex = 9.0 if is_metric else 6.0
        u_lbl = "km" if is_metric else "mi"
        s_name = "Mondo / Regione" if lang == "it" else "World / Region"
        hours_per_hex = 2.0  # 6 mi / 3 mph = 2h di marcia per esagono (4 hex = 1 giorno / 24 mi)
    elif scale_type == "exploration":
        per_hex = 1.5 if is_metric else 1.0
        u_lbl = "km" if is_metric else "mi"
        s_name = "Esplorazione (POI)" if lang == "it" else "Exploration (POI)"
        hours_per_hex = 1.0 / 3.0  # 1 mi / 3 mph = 20 min di marcia per esagono
    else:
        per_hex = 1.5 if is_metric else 5.0
        u_lbl = "m" if is_metric else "ft"
        s_name = "Combattimento" if lang == "it" else "Combat"
        hours_per_hex = 0.0

    return {
        "scale_type": scale_type,
        "scale_name": s_name,
        "per_hex": per_hex,
        "unit_label": u_lbl,
        "hex_size": hex_size,
        "hours_per_hex": hours_per_hex,
    }


def format_distance_hexes(hexes: int, unit: str = None, map_data: dict = None, include_travel_time: bool = False) -> str:
    """
    Formatta un numero di esagoni nell'unità di misura scelta tenendo conto della scala della mappa:
      - Combattimento: '30 ft' o '9 m' (1 hex = 5 ft / 1.5 m)
      - Esplorazione: '4 mi' o '6 km' (1 hex = 1 mi / 1.5 km)
      - Mondo/Regione: '24 mi' o '36 km' (1 hex = 6 mi / 9 km)
    Se include_travel_time=True e la mappa è d'esplorazione o regionale, aggiunge la stima del tempo di viaggio (andatura normale).
    """
    scale_info = get_map_scale_info(map_data=map_data, unit=unit)
    per_hex = scale_info["per_hex"]
    u_lbl = scale_info["unit_label"]

    val = round(hexes * per_hex, 1)
    val_str = str(int(val)) if val == int(val) else f"{val:.1f}"
    base_str = f"{val_str} {u_lbl}"

    if include_travel_time and hexes > 0 and scale_info.get("hours_per_hex", 0) > 0:
        total_hours = hexes * scale_info["hours_per_hex"]
        lang = get_language()
        if total_hours < 1.0:
            mins = max(1, int(round(total_hours * 60)))
            time_str = f"~{mins} min"
        elif total_hours <= 8.0:
            h_val = round(total_hours, 1)
            h_str = str(int(h_val)) if h_val == int(h_val) else f"{h_val:.1f}"
            time_str = f"~{h_str}h"
        else:
            # In D&D 5e 1 giornata di viaggio standard = 8 ore di marcia (24 mi / 36 km)
            days = round(total_hours / 8.0, 1)
            d_str = str(int(days)) if days == int(days) else f"{days:.1f}"
            day_lbl = "gg" if lang == "it" else "d"
            time_str = f"~{d_str} {day_lbl}"
        return f"{base_str} [{time_str}]"

    return base_str


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
    dead_listeners = []
    for cb in listeners_copy:
        try:
            cb(_current_language)
        except Exception as e:
            err_msg = str(e)
            if "destroyed" in err_msg or "cannot invoke" in err_msg:
                dead_listeners.append(cb)
            else:
                print(f"[i18n] Errore callback lingua: {e}")
    if dead_listeners:
        with _lock:
            for d in dead_listeners:
                if d in _listeners:
                    _listeners.remove(d)


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


def reset_listeners_for_testing():
    """Resetta tutti i listener registrati per isolare l'ambiente di test."""
    with _lock:
        _listeners.clear()
        _unit_listeners.clear()


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

