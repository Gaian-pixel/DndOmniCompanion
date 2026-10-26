# common/companions_data.py
"""
Modulo per la gestione di Famigli (Find Familiar), Compagni Animali (Ranger Beast Master)
e Creature Evocate (Conjuration/Necromancy) conformi alle regole D&D 5e RAW.
"""

from typing import Dict, Any, List, Optional
from common.i18n import get_language

# 1. FORME FAMIGLIO (PHB p. 240 & Warlock Pact of the Chain)
FAMILIAR_FORMS: Dict[str, Dict[str, Any]] = {
    "owl": {
        "key": "owl",
        "name_it": "Gufo",
        "name_en": "Owl",
        "icon": "🦉",
        "size": 1, # Tiny / Small
        "hp": 1,
        "max_hp": 1,
        "ac": 11,
        "speed": 60,
        "speed_unit": "ft",
        "vision_radius": 24, # Scurovisione 120 ft (24 esagoni)
        "has_darkvision": True,
        "traits": [
            "Picchiata (Flyby): Il gufo non provoca attacchi di opportunità quando vola via dalla portata di un nemico.",
            "Vista e Udito Acuti: Vantaggio alle prove di Saggezza (Percezione) basate su vista o udito."
        ],
        "can_attack": False,
        "description_it": "Famiglio aereo eccellente per esplorazione notturna e azione Aiuto senza subire AdO.",
        "description_en": "Excellent aerial familiar for night reconnaissance and Help action without provoking AoO."
    },
    "bat": {
        "key": "bat",
        "name_it": "Pipistrello",
        "name_en": "Bat",
        "icon": "🦇",
        "size": 1,
        "hp": 1,
        "max_hp": 1,
        "ac": 12,
        "speed": 30,
        "speed_unit": "ft",
        "vision_radius": 12, # Vista Cieca 60 ft (12 esagoni)
        "has_darkvision": True,
        "blindsight": 12,
        "traits": [
            "Vista Cieca (Blindsight) 18m (12 esagoni): Percepisce l'ambiente anche in oscurità magica.",
            "Udito Acuto: Vantaggio alle prove di Saggezza (Percezione) basate sull'udito."
        ],
        "can_attack": False,
        "description_it": "Famiglio dotato di Vista Cieca: immune alla cecità e perfetto in oscurità magica.",
        "description_en": "Familiar with Blindsight: immune to blindness and excels in magical darkness."
    },
    "cat": {
        "key": "cat",
        "name_it": "Gatto",
        "name_en": "Cat",
        "icon": "🐈",
        "size": 1,
        "hp": 2,
        "max_hp": 2,
        "ac": 12,
        "speed": 40,
        "speed_unit": "ft",
        "vision_radius": 8,
        "has_darkvision": True,
        "traits": [
            "Furtivo: Vantaggio alle prove di Furtività.",
            "Olfatto Acuto: Vantaggio alle prove di Percezione basate sull'olfatto.",
            "Arrampicarsi: Velocità di scalata 9m (30 ft)."
        ],
        "can_attack": False,
        "description_it": "Famiglio furtivo e agile, ideale per infiltrazioni urbane e spazi angusti.",
        "description_en": "Stealthy and agile familiar, ideal for urban infiltration and tight spaces."
    },
    "hawk": {
        "key": "hawk",
        "name_it": "Falco",
        "name_en": "Hawk",
        "icon": "🦅",
        "size": 1,
        "hp": 1,
        "max_hp": 1,
        "ac": 13,
        "speed": 60,
        "speed_unit": "ft",
        "vision_radius": 12,
        "traits": [
            "Vista Acuta: Vantaggio alle prove di Saggezza (Percezione) basate sulla vista."
        ],
        "can_attack": False,
        "description_it": "Famiglio veloce per ricognizioni diurne a lungo raggio.",
        "description_en": "Fast familiar for daylight long-range reconnaissance."
    },
    "raven": {
        "key": "raven",
        "name_it": "Corvo",
        "name_en": "Raven",
        "icon": "🐦",
        "size": 1,
        "hp": 1,
        "max_hp": 1,
        "ac": 12,
        "speed": 50,
        "speed_unit": "ft",
        "vision_radius": 8,
        "traits": [
            "Mimetismo Vocale: Può imitare suoni semplici o parole sentite superando una prova con intuizione."
        ],
        "can_attack": False,
        "description_it": "Famiglio intelligente in grado di imitare voci e trasportare messaggi.",
        "description_en": "Clever familiar capable of mimicking sounds and carrying messages."
    },
    "snake": {
        "key": "snake",
        "name_it": "Serpente Velenoso",
        "name_en": "Poisonous Snake",
        "icon": "🐍",
        "size": 1,
        "hp": 2,
        "max_hp": 2,
        "ac": 13,
        "speed": 30,
        "speed_unit": "ft",
        "vision_radius": 6,
        "blindsight": 2,
        "traits": [
            "Vista Cieca 3m (2 esagoni).",
            "Nuoto: Velocità di nuoto 9m (30 ft)."
        ],
        "can_attack": False,
        "description_it": "Famiglio acquatico e terrestre silenzioso.",
        "description_en": "Silent amphibious familiar."
    },
    "toad": {
        "key": "toad",
        "name_it": "Rospo / Rana",
        "name_en": "Toad / Frog",
        "icon": "🐸",
        "size": 1,
        "hp": 1,
        "max_hp": 1,
        "ac": 11,
        "speed": 20,
        "speed_unit": "ft",
        "vision_radius": 6,
        "has_darkvision": True,
        "traits": [
            "Anfibio: Può respirare sia in aria che in acqua.",
            "Salto Balzante: Salto in lungo fino a 3m."
        ],
        "can_attack": False,
        "description_it": "Famiglio anfibio discreto per canali e paludi.",
        "description_en": "Discreet amphibious familiar for sewers and swamps."
    },
    "spider": {
        "key": "spider",
        "name_it": "Ragno",
        "name_en": "Spider",
        "icon": "🕷️",
        "size": 1,
        "hp": 1,
        "max_hp": 1,
        "ac": 12,
        "speed": 20,
        "speed_unit": "ft",
        "vision_radius": 6,
        "has_darkvision": True,
        "traits": [
            "Scalare Ragnatele (Spider Climb): Scala pareti verticali e soffitti.",
            "Senso della Ragnatela: Rileva vibrazioni e creature a contatto con la ragnatela."
        ],
        "can_attack": False,
        "description_it": "Famiglio minuscolo che può arrampicarsi su pareti e soffitti.",
        "description_en": "Tiny familiar able to climb walls and ceilings."
    },
    "imp": {
        "key": "imp",
        "name_it": "Diavoletto (Imp)",
        "name_en": "Imp (Chain Pact)",
        "icon": "😈",
        "size": 1,
        "hp": 10,
        "max_hp": 10,
        "ac": 13,
        "speed": 40,
        "speed_unit": "ft",
        "vision_radius": 24,
        "has_darkvision": True,
        "traits": [
            "Patto della Catena (Warlock): Questo famiglio PUÒ compiere attacchi.",
            "Resistenza Magica: Vantaggio ai TS contro incantesimi ed effetti magici.",
            "Vista del Diavolo: Vede normalmente anche nell'oscurità magica.",
            "Invisibilità a Volontà: Può rendersi invisibile come azione magica."
        ],
        "can_attack": True,
        "attack": {
            "name": "Pungiglione",
            "hit": "+5",
            "damage": "1d4+3",
            "type": "Perforante",
            "extra_damage": "3d6",
            "extra_type": "Veleno"
        },
        "description_it": "Famiglio del Patto della Catena (Warlock) con invisibilità, parola e attacco velenoso.",
        "description_en": "Warlock Pact of the Chain familiar with invisibility, speech, and poisonous sting."
    },
    "pseudodragon": {
        "key": "pseudodragon",
        "name_it": "Pseudodrago",
        "name_en": "Pseudodragon (Chain Pact)",
        "icon": "🐲",
        "size": 1,
        "hp": 7,
        "max_hp": 7,
        "ac": 13,
        "speed": 60,
        "speed_unit": "ft",
        "vision_radius": 12,
        "has_darkvision": True,
        "blindsight": 2,
        "traits": [
            "Patto della Catena (Warlock): Questo famiglio PUÒ attaccare.",
            "Resistenza Magica Condivisa: Condivide vantaggio ai TS con il padrone entro 3m.",
            "Telepatia Limitata: Comunica telepaticamente immagini e sensazioni entro 30m.",
            "Pungiglione Sopore: TS Costituzione CD 11 o Avvelenato; se fallisce di 5+, cade Incosciente."
        ],
        "can_attack": True,
        "attack": {
            "name": "Pungiglione",
            "hit": "+4",
            "damage": "1d4+2",
            "type": "Perforante"
        },
        "description_it": "Famiglio draghesco che conferisce Resistenza Magica al padrone e pungiglione soporifero.",
        "description_en": "Draconic familiar conferring Magic Resistance to master and sleeping sting."
    }
}

# 2. COMPAGNI ANIMALI DEL RANGER (PHB p. 93 / TCoE Primal Companion)
BEAST_COMPANIONS: Dict[str, Dict[str, Any]] = {
    "wolf": {
        "key": "wolf",
        "name_it": "Lupo",
        "name_en": "Wolf",
        "icon": "🐺",
        "size": 1, # Medium
        "hp": 11,
        "max_hp": 11,
        "ac": 13,
        "speed": 40,
        "speed_unit": "ft",
        "vision_radius": 8,
        "has_darkvision": True,
        "attack": {
            "name": "Morso",
            "hit": "+4",
            "damage": "2d4+2",
            "type": "Perforante",
            "note": "TS Forza CD 11 o cade Prono"
        },
        "traits": [
            "Tattiche di Branco (Pack Tactics): Vantaggio all'attacco se un alleato è adiacente al bersaglio.",
            "Udito e Olfatto Acuti: Vantaggio a Percezione basata su udito o olfatto."
        ],
        "can_attack": True,
        "description_it": "Compagno da mischia formidabile che atterra i nemici e sfrutta il branco.",
        "description_en": "Formidable melee companion that trips enemies and uses pack tactics."
    },
    "panther": {
        "key": "panther",
        "name_it": "Pantera",
        "name_en": "Panther",
        "icon": "🐆",
        "size": 1,
        "hp": 13,
        "max_hp": 13,
        "ac": 12,
        "speed": 50,
        "speed_unit": "ft",
        "vision_radius": 8,
        "has_darkvision": True,
        "attack": {
            "name": "Artigli",
            "hit": "+4",
            "damage": "1d4+2",
            "type": "Tagliente"
        },
        "traits": [
            "Balzo (Pounce): Se carica di almeno 6m e colpisce, TS FOR CD 12 o Prono + morso come bonus.",
            "Furtivo: Vantaggio a prove di Furtività."
        ],
        "can_attack": True,
        "description_it": "Cacciatore furtivo ad altissima velocità e capacità di balzo.",
        "description_en": "Stealthy high-speed hunter with pounce ability."
    },
    "boar": {
        "key": "boar",
        "name_it": "Cinghiale",
        "name_en": "Boar",
        "icon": "🐗",
        "size": 1,
        "hp": 11,
        "max_hp": 11,
        "ac": 11,
        "speed": 40,
        "speed_unit": "ft",
        "vision_radius": 6,
        "attack": {
            "name": "Zanne",
            "hit": "+3",
            "damage": "1d6+1",
            "type": "Tagliente",
            "note": "Se carica +1d6 danno e TS FOR CD 11 o Prono"
        },
        "traits": [
            "Carica (Charge): +1d6 danni da carica e atterramento.",
            "Tenacia (Relentless): Se subisce 7 o meno danni a 0 PV, rimane a 1 PV (1/riposo breve)."
        ],
        "can_attack": True,
        "description_it": "Compagno robusto che non cade a 0 PV al primo colpo mortale.",
        "description_en": "Sturdy companion that resists dying to lethal blows."
    },
    "giant_snake": {
        "key": "giant_snake",
        "name_it": "Serpente Gigante",
        "name_en": "Giant Poisonous Snake",
        "icon": "🐍",
        "size": 1,
        "hp": 11,
        "max_hp": 11,
        "ac": 14,
        "speed": 30,
        "speed_unit": "ft",
        "vision_radius": 6,
        "blindsight": 2,
        "attack": {
            "name": "Morso Velenoso",
            "hit": "+6",
            "damage": "1d4+4",
            "type": "Perforante",
            "extra_damage": "3d6",
            "extra_type": "Veleno"
        },
        "traits": [
            "Portata 3m (10 ft / 2 esagoni): Può colpire nemici a distanza di 2 caselle.",
            "Nuoto: Velocità di nuoto 9m."
        ],
        "can_attack": True,
        "description_it": "Alta CA e attacco con portata 3m ad altissimo danno da veleno.",
        "description_en": "High AC and 10 ft reach with high poison damage."
    },
    "mastiff": {
        "key": "mastiff",
        "name_it": "Mastino",
        "name_en": "Mastiff",
        "icon": "🐕",
        "size": 1,
        "hp": 11,
        "max_hp": 11,
        "ac": 12,
        "speed": 40,
        "speed_unit": "ft",
        "vision_radius": 6,
        "attack": {
            "name": "Morso",
            "hit": "+3",
            "damage": "1d6+1",
            "type": "Perforante",
            "note": "TS FOR CD 11 o Prono"
        },
        "traits": [
            "Udito e Olfatto Acuti: Vantaggio a Percezione.",
            "Cavalcatura: Può servire da cavalcatura per creature di Taglia Piccola (Halfling, Gnomo)."
        ],
        "can_attack": True,
        "description_it": "Fedele segugio da guardia, utilizzabile come cavalcatura per Halfling e Gnomi.",
        "description_en": "Loyal guard dog, mountable by Halflings and Gnomes."
    }
}

# 3. CREATURE EVOCATE (Conjuration & Necromancy)
SUMMON_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "skeleton": {
        "key": "skeleton",
        "name_it": "Scheletro",
        "name_en": "Skeleton",
        "icon": "💀",
        "size": 1,
        "hp": 13,
        "max_hp": 13,
        "ac": 13,
        "speed": 30,
        "speed_unit": "ft",
        "vision_radius": 12,
        "has_darkvision": True,
        "attack": {
            "name": "Spada Corta",
            "hit": "+4",
            "damage": "1d6+2",
            "type": "Perforante"
        },
        "traits": ["Immunità: Veleno ed Esaustione. Vulnerabilità: Danni Contundenti."],
        "concentration": False,
        "can_attack": True,
        "description_it": "Non Morto animato tramite Animare Morti.",
        "description_en": "Undead minion animated via Animate Dead."
    },
    "zombie": {
        "key": "zombie",
        "name_it": "Zombi",
        "name_en": "Zombie",
        "icon": "🧟",
        "size": 1,
        "hp": 22,
        "max_hp": 22,
        "ac": 8,
        "speed": 20,
        "speed_unit": "ft",
        "vision_radius": 12,
        "has_darkvision": True,
        "attack": {
            "name": "Schianto",
            "hit": "+3",
            "damage": "1d6+1",
            "type": "Contundente"
        },
        "traits": ["Tenacia Non Morta: TS COS CD 5+danno per non scendere a 0 PV."],
        "concentration": False,
        "can_attack": True,
        "description_it": "Resistente non morto rianimato tramite Animare Morti.",
        "description_en": "Durable undead minion from Animate Dead."
    },
    "conjured_wolf": {
        "key": "conjured_wolf",
        "name_it": "Lupo Fatato",
        "name_en": "Conjured Wolf",
        "icon": "🐺",
        "size": 1,
        "hp": 11,
        "max_hp": 11,
        "ac": 13,
        "speed": 40,
        "speed_unit": "ft",
        "vision_radius": 8,
        "has_darkvision": True,
        "attack": {
            "name": "Morso",
            "hit": "+4",
            "damage": "2d4+2",
            "type": "Perforante"
        },
        "traits": ["Tattiche di Branco: Vantaggio se alleato adiacente.", "Spirito Evocato: Svanisce se cade la concentrazione."],
        "concentration": True,
        "can_attack": True,
        "description_it": "Spirito bestiale evocato tramite Evoca Animali (Conjure Animals).",
        "description_en": "Bestial spirit summoned via Conjure Animals."
    },
    "fey_spirit": {
        "key": "fey_spirit",
        "name_it": "Spirito Fatato",
        "name_en": "Fey Spirit",
        "icon": "🧚",
        "size": 1,
        "hp": 30,
        "max_hp": 30,
        "ac": 15,
        "speed": 30,
        "speed_unit": "ft",
        "vision_radius": 12,
        "has_darkvision": True,
        "attack": {
            "name": "Lama Fatata",
            "hit": "+7",
            "damage": "1d6+6",
            "type": "Forza"
        },
        "traits": ["Passo Fatato (Fey Step): Si teletrasporta fino a 9m come Azione Bonus."],
        "concentration": True,
        "can_attack": True,
        "description_it": "Spirito fatato combattente con teletrasporto e danni da forza.",
        "description_en": "Fey combatant with bonus action teleportation."
    }
}

def get_companion_presets(companion_type: str = "familiar", lang: Optional[str] = None) -> List[Dict[str, Any]]:
    """Restituisce l'elenco dei preset disponibili per il tipo specificato (familiar, beast, summon)."""
    cur_lang = (lang or get_language() or "it").lower()
    is_en = cur_lang.startswith("en")
    
    source_map = FAMILIAR_FORMS
    if companion_type in ("beast", "beast_companion"):
        source_map = BEAST_COMPANIONS
    elif companion_type in ("summon", "summons"):
        source_map = SUMMON_TEMPLATES
        
    presets = []
    for key, data in source_map.items():
        name = data["name_en"] if is_en else data["name_it"]
        desc = data["description_en"] if is_en else data["description_it"]
        p = dict(data)
        p["display_name"] = name
        p["description"] = desc
        presets.append(p)
    return presets

def scale_beast_companion_stats(base_data: Dict[str, Any], ranger_level: int = 1, ranger_pb: int = 2) -> Dict[str, Any]:
    """
    Scala le statistiche del compagno animale secondo le regole D&D 5e:
    - CA: base + bonus di competenza del ranger
    - PV Massimi: max(base_hp, 4 * ranger_level)
    - Tiri per colpire e danni: aggiungono PB del ranger
    - Tiri Salvezza e Abilità: aggiungono PB del ranger
    """
    scaled = dict(base_data)
    level = max(1, int(ranger_level))
    pb = max(2, int(ranger_pb))
    
    scaled["ac"] = base_data.get("ac", 12) + pb
    scaled["max_hp"] = max(base_data.get("hp", 11), 4 * level)
    scaled["hp"] = scaled["max_hp"]
    
    if "attack" in base_data and isinstance(base_data["attack"], dict):
        atk = dict(base_data["attack"])
        raw_hit = str(atk.get("hit", "+4")).replace("+", "").strip()
        try: hit_val = int(raw_hit) + pb
        except ValueError: hit_val = 4 + pb
        atk["hit"] = f"+{hit_val}"
        
        # Aggiungi nota bonus danni
        raw_dmg = str(atk.get("damage", "1d6+2"))
        atk["damage_display"] = f"{raw_dmg} (+{pb} Ranger PB)"
        scaled["attack"] = atk
        
    scaled["ranger_pb"] = pb
    scaled["ranger_level"] = level
    return scaled

def create_companion_player_dict(
    companion_type: str,
    template_key: str,
    master_player: Any,
    custom_name: Optional[str] = None,
    ranger_level: Optional[int] = None,
    ranger_pb: Optional[int] = None
) -> Dict[str, Any]:
    """
    Genera un dizionario completo per istanziare un Player/Token come Famiglio o Compagno Animale
    sulla mappa, coordinato alle statistiche del padrone.
    """
    source_map = FAMILIAR_FORMS
    if companion_type in ("beast", "beast_companion"):
        source_map = BEAST_COMPANIONS
    elif companion_type in ("summon", "summons"):
        source_map = SUMMON_TEMPLATES
        
    template = source_map.get(template_key.lower()) or list(source_map.values())[0]
    
    # Se compagno animale, applica scaling del Ranger
    if companion_type in ("beast", "beast_companion"):
        r_lvl = ranger_level or (getattr(master_player, "level", 1) if hasattr(master_player, "level") else 1)
        r_pb = ranger_pb or (getattr(master_player, "proficiency_bonus", 2) if hasattr(master_player, "proficiency_bonus") else 2)
        final_data = scale_beast_companion_stats(template, r_lvl, r_pb)
    else:
        final_data = dict(template)
        
    master_name = master_player.name if hasattr(master_player, "name") else str(master_player)
    name = custom_name.strip() if custom_name and custom_name.strip() else f"{final_data.get('name_it', 'Compagno')} di {master_name}"
    
    pos = [0, 0]
    if hasattr(master_player, "position") and master_player.position:
        # Posiziona su un esagono adiacente al padrone
        mq, mr = master_player.position[0], master_player.position[1]
        pos = [mq + 1, mr]
        
    full_sheet = {
        "name": name,
        "is_companion": True,
        "companion_type": companion_type,
        "master_name": master_name,
        "race": final_data.get("name_it", "Bestia"),
        "char_class": "Famiglio / Compagno",
        "level": ranger_level or 1,
        "hp_current": final_data.get("hp", 1),
        "hp_max": final_data.get("max_hp", 1),
        "ac": final_data.get("ac", 12),
        "speed": final_data.get("speed", 30),
        "speed_unit": final_data.get("speed_unit", "ft"),
        "attributes": {"FOR": 10, "DES": 14, "COS": 10, "INT": 6, "SAG": 12, "CAR": 6},
        "saving_throws": [],
        "traits": final_data.get("traits", []),
        "features": final_data.get("traits", []),
        "attack": final_data.get("attack")
    }
    
    return {
        "name": name,
        "position": pos,
        "hp": final_data.get("hp", 1),
        "max_hp": final_data.get("max_hp", 1),
        "temp_hp": 0,
        "initiative": 0,
        "owner": master_name,
        "master_name": master_name,
        "companion_type": companion_type,
        "is_companion": True,
        "is_party_member": True,
        "in_pocket_dimension": False,
        "can_attack": final_data.get("can_attack", True),
        "vision_radius": final_data.get("vision_radius", 6),
        "has_darkvision": final_data.get("has_darkvision", False),
        "speed": final_data.get("speed", 30),
        "speed_unit": final_data.get("speed_unit", "ft"),
        "size": final_data.get("size", 1),
        "full_sheet": full_sheet
    }
