# common/travel_data.py
"""
Modulo per la gestione avanzata di Viaggio, Esplorazione Hex-Crawl, Biomi,
Incontri Casuali e Turni di Guardia Notturna (D&D 5e RAW).
"""

import random
from typing import Dict, Any, List, Optional
from common.i18n import get_language
from common.dice import roll_dice

# 1. BIOMI D&D 5e E PARAMETRI DI NAVIGAZIONE
BIOMES: Dict[str, Dict[str, Any]] = {
    "foresta": {
        "key": "foresta",
        "name_it": "Foresta / Boschi",
        "name_en": "Forest / Woods",
        "icon": "🌲",
        "dc_nav": 15,
        "forage_dc": 15,
        "description_it": "Vegetazione fitta, sentieri tortuosi, tronchi caduti e baldacchino che oscura il cielo.",
        "description_en": "Dense vegetation, winding trails, fallen trunks, and a canopy obscuring the sky."
    },
    "pianura": {
        "key": "pianura",
        "name_it": "Pianura / Strade",
        "name_en": "Plains / Roads",
        "icon": "🌾",
        "dc_nav": 10,
        "forage_dc": 15,
        "description_it": "Grandi distese erbose aperte, colline dolci e strade maestre battute da viandanti.",
        "description_en": "Open grasslands, gentle hills, and highroads traveled by wanderers."
    },
    "palude": {
        "key": "palude",
        "name_it": "Palude / Acquitrino",
        "name_en": "Swamp / Marsh",
        "icon": "🐊",
        "dc_nav": 18,
        "forage_dc": 18,
        "description_it": "Acque stagnanti mefitiche, fango profondo, banchi di nebbia e insetti ronzanti.",
        "description_en": "Mundane foul waters, deep mud, fog banks, and biting insects."
    },
    "montagna": {
        "key": "montagna",
        "name_it": "Montagna / Rupi",
        "name_en": "Mountain / Peaks",
        "icon": "⛰️",
        "dc_nav": 18,
        "forage_dc": 20,
        "description_it": "Sentieri scoscesi a strapiombo, roccia friabile, aria rarefatta e venti gelidi.",
        "description_en": "Steep clifftop paths, loose scree, thin air, and freezing winds."
    },
    "deserto": {
        "key": "deserto",
        "name_it": "Deserto / Lande Desolate",
        "name_en": "Desert / Badlands",
        "icon": "🏜️",
        "dc_nav": 20,
        "forage_dc": 20,
        "description_it": "Dune di sabbia roventi, sole implacabile di giorno e gelo improvviso di notte.",
        "description_en": "Scorching sand dunes, blistering day sun, and sudden freezing nights."
    },
    "sottosuolo": {
        "key": "sottosuolo",
        "name_it": "Sottosuolo (Underdark)",
        "name_en": "Underdark / Caverns",
        "icon": "🦇",
        "dc_nav": 20,
        "forage_dc": 20,
        "description_it": "Labirinti di caverne prive di luce solare, stalattiti taglienti e silenzi echeggianti.",
        "description_en": "Sunless cavern labyrinths, sharp stalactites, and echoing silences."
    },
    "costiero": {
        "key": "costiero",
        "name_it": "Costiero / Litorale",
        "name_en": "Coast / Shores",
        "icon": "🌊",
        "dc_nav": 12,
        "forage_dc": 15,
        "description_it": "Rupi a picco sul mare, scogliere battute dalle onde, spiagge sabbiose e relitti.",
        "description_en": "Seaside bluffs, wave-battered cliffs, sandy beaches, and driftwood flotsam."
    },
    "tundra": {
        "key": "tundra",
        "name_it": "Tundra / Ghiacciaio",
        "name_en": "Tundra / Arctic",
        "icon": "❄️",
        "dc_nav": 18,
        "forage_dc": 20,
        "description_it": "Distese di permafrost, lastre di ghiaccio crepitanti e tormente di neve accecanti.",
        "description_en": "Permafrost wastes, creaking pack ice, and blinding snow blizzards."
    }
}

# 2. LIVELLI DI PERICOLO
DANGER_LEVELS: Dict[str, Dict[str, Any]] = {
    "safe": {
        "key": "safe",
        "name_it": "Basso / Terre Civilizzate",
        "name_en": "Low / Safe Patrols",
        "encounter_threshold": 18, # d20 >= 18 (15%)
        "icon": "🛡️"
    },
    "moderate": {
        "key": "moderate",
        "name_it": "Medio / Terre Selvagge",
        "name_en": "Moderate / Wilderness",
        "encounter_threshold": 15, # d20 >= 15 (30%)
        "icon": "🌲"
    },
    "dangerous": {
        "key": "dangerous",
        "name_it": "Alto / Terre Ostili",
        "name_en": "High / Dangerous",
        "encounter_threshold": 12, # d20 >= 12 (45%)
        "icon": "⚔️"
    },
    "deadly": {
        "key": "deadly",
        "name_it": "Estremo / Letale",
        "name_en": "Extreme / Deadly",
        "encounter_threshold": 9,  # d20 >= 9 (60%)
        "icon": "💀"
    }
}

# 3. ANDATURE DI VIAGGIO (PHB p. 182)
TRAVEL_PACES: Dict[str, Dict[str, Any]] = {
    "Lenta": {
        "key": "Lenta",
        "speed_mph": 2,
        "miles_per_day": 18,
        "pp_modifier": 5, # Vantaggio (+5 alla Percezione Passiva)
        "stealth_allowed": True,
        "forage_allowed": True,
        "name_it": "Lenta (2 mi/h, Furtivo, +5 PP)",
        "name_en": "Slow (2 mph, Stealth, +5 PP)",
        "description_it": "Muoversi con circospezione permette di avanzare furtivamente e scorgere pericoli.",
        "description_en": "Careful pace allows stealth exploration and increases passive perception."
    },
    "Normale": {
        "key": "Normale",
        "speed_mph": 3,
        "miles_per_day": 24,
        "pp_modifier": 0,
        "stealth_allowed": False,
        "forage_allowed": True,
        "name_it": "Normale (3 mi/h, 24 mi/g)",
        "name_en": "Normal (3 mph, 24 mi/d)",
        "description_it": "Andatura standard a passo costante.",
        "description_en": "Standard travel pace at constant speed."
    },
    "Veloce": {
        "key": "Veloce",
        "speed_mph": 4,
        "miles_per_day": 30,
        "pp_modifier": -5, # Svantaggio (-5 alla Percezione Passiva)
        "stealth_allowed": False,
        "forage_allowed": False,
        "nav_penalty": -5,
        "name_it": "Veloce (4 mi/h, -5 PP, no caccia)",
        "name_en": "Fast (4 mph, -5 PP, no forage)",
        "description_it": "Marcia a passo svelto: riduce l'attenzione all'ambiente e impedisce la raccolta di cibo.",
        "description_en": "Brisk march: reduces situational awareness and prevents food gathering."
    }
}

# 4. TABELLE DI INCONTRI CASUALI STRUTTURATE PER BIOMA
BIOME_ENCOUNTERS: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "foresta": {
        "combat": [
            {
                "title_it": "Branco di Lupi Affamati",
                "title_en": "Hungry Wolf Pack",
                "desc_it": "Ululati tagliano l'aria mentre un branco di lupi accerchia il sentiero tra gli alberi.",
                "desc_en": "Howls cut through the air as a pack of wolves encircles the path between the trees.",
                "monsters": [{"name": "Wolf", "count": "1d4+1", "cr": "1/4"}],
                "stealth_dc": 13,
                "dist_hexes": 6
            },
            {
                "title_it": "Incursione di Goblin Silvani",
                "title_en": "Forest Goblin Ambush",
                "desc_it": "Frecce fischianti piovono dalle cime degli alberi: piccoli guerrieri goblin tendono un agguato!",
                "desc_en": "Whistling arrows rain from treetops: goblin skirmishers set up an ambush!",
                "monsters": [{"name": "Goblin", "count": "1d6+2", "cr": "1/4"}],
                "stealth_dc": 15,
                "dist_hexes": 5
            },
            {
                "title_it": "Ragno Gigante della Canopia",
                "title_en": "Giant Spider from the Canopy",
                "desc_it": "Un enorme aracnide si cala silenzioso da ragnatele sospese sopra la carovana.",
                "desc_en": "A massive arachnid silently drops from thick webs suspended above the caravan.",
                "monsters": [{"name": "Giant Spider", "count": "1d2", "cr": "1"}],
                "stealth_dc": 14,
                "dist_hexes": 3
            },
            {
                "title_it": "Orso Bruno Furente",
                "title_en": "Enraged Brown Bear",
                "desc_it": "Un possente orso bruno esce da un cespuglio di rovi, difendendo il proprio territorio.",
                "desc_en": "A massive brown bear emerges from a bramble thicket, defending its territory.",
                "monsters": [{"name": "Brown Bear", "count": "1", "cr": "1"}],
                "stealth_dc": 10,
                "dist_hexes": 4
            }
        ],
        "social": [
            {
                "title_it": "Eremita Druidico del Bosco",
                "title_en": "Druidic Forest Hermit",
                "desc_it": "Un vecchio eremita in abiti di foglie accoglie il party offrendo infusi caldi e previsioni sul meteo.",
                "desc_en": "An elderly hermit in leafy robes greets the party offering warm herbal tea and weather forecasts.",
                "reward": "Consiglio saggio: +2 alla prossima prova di Orientamento o Sopravvivenza."
            },
            {
                "title_it": "Pattuglia di Guardie Forestali Elfiche",
                "title_en": "Elven Ranger Patrol",
                "desc_it": "Due arcieri elfici emergono dalle ombre con archi abbassati, chiedendo le intenzioni del gruppo.",
                "desc_en": "Two elven scouts emerge from the shadows with bows lowered, inquiring about the party's journey.",
                "reward": "Informazioni sul territorio: rivelano la presenza di pericoli vicini."
            }
        ],
        "discovery": [
            {
                "title_it": "Circolo Druidico Antico",
                "title_en": "Ancient Druidic Stone Ring",
                "desc_it": "Menhir ricoperti di muschio irradiano un'aura rigenerante. Riposare qui ricarica le energie.",
                "desc_en": "Moss-covered standing stones radiate restorative energy. Resting here restores vigor.",
                "reward": "Benedizione Silvana: ciascun membro del gruppo recupera immediatamente 1 Dado Vita speso."
            },
            {
                "title_it": "Albero Monumentale con Forziere Cavo",
                "title_en": "Monumental Hollow Tree Cache",
                "desc_it": "All'interno del tronco cavo di un'antica quercia è nascosto un piccolo scrigno da viaggio.",
                "desc_en": "Hidden inside the hollow trunk of an ancient oak lies a small traveling lockbox.",
                "reward": "Bottino trovato: 2d10 MO, 3 razioni sigillate e 1 Pozione di Guarigione."
            }
        ],
        "hazard": [
            {
                "title_it": "Banchi di Nebbia Inebriante",
                "title_en": "Intoxicating Spore Fog",
                "desc_it": "Spore luminescenti saturate nell'aria provocano capogiri e sonnolenza improvvisa.",
                "desc_en": "Glowing spores lingering in the air cause sudden dizziness and lethargy.",
                "save_stat": "COS",
                "save_dc": 12,
                "fail_effect": "Condizione Avvelenato o Sfinimento per 4 ore se fallito."
            },
            {
                "title_it": "Trappola da Caccia Dimenticata",
                "title_en": "Forgotten Snare Trap",
                "desc_it": "Una tagliola arrugginita o fune a cappio è celata sotto le foglie secche.",
                "desc_en": "A rusted bear trap or loop snare is concealed beneath the dead foliage.",
                "save_stat": "DES",
                "save_dc": 13,
                "fail_effect": "Chi apre la fila subisce 1d8 danni perforanti e cade Prono."
            }
        ]
    },
    "pianura": {
        "combat": [
            {
                "title_it": "Banda di Tagliagole della Strada",
                "title_en": "Highway Bandit Gang",
                "desc_it": "Uomini armati di balestre e sciabole bloccano il passaggio esigendo un dazio sul sangue.",
                "desc_en": "Outlaws armed with crossbows and cutlasses block the road demanding a blood toll.",
                "monsters": [{"name": "Bandit", "count": "1d6+1", "cr": "1/8"}],
                "stealth_dc": 12,
                "dist_hexes": 8
            },
            {
                "title_it": "Muta di Mastini Randagi",
                "title_en": "Feral Mastiff Pack",
                "desc_it": "Cani da caccia inselvatichiti caricano abbaiando minacciosi tra l'erba alta.",
                "desc_en": "Feral hunting hounds charge barking aggressively through the tall grass.",
                "monsters": [{"name": "Mastiff", "count": "1d4+2", "cr": "1/8"}],
                "stealth_dc": 11,
                "dist_hexes": 6
            }
        ],
        "social": [
            {
                "title_it": "Carovana di Mercanti Nanici",
                "title_en": "Dwarven Merchant Caravan",
                "desc_it": "Robusti carri trainati da buoi si fermano a lato strada; i mercanti offrono razioni e mercanzie.",
                "desc_en": "Sturdy ox-drawn wagons pull to the side; traders offer rations, smithing goods, and gossip.",
                "reward": "Accesso a merci fresche, razioni di ferro e notizie delle città vicine."
            },
            {
                "title_it": "Pellegrini Erranti",
                "title_en": "Wandering Pilgrims",
                "desc_it": "Fedeli in viaggio verso un santuario remoto cantano inni e condividono pane e formaggio.",
                "desc_en": "Devout travelers on pilgrimage share bread, cheese, and sacred blessings.",
                "reward": "Pasto caldo condiviso: rimuove la necessità di consumare 1 razione oggi."
            }
        ],
        "discovery": [
            {
                "title_it": "Torre di Guardia in Rovina",
                "title_en": "Ruined Watchtower",
                "desc_it": "I resti di una torre offrono mura solide e una posizione sopraelevata per un accampamento sicuro.",
                "desc_en": "The remains of a stone watchtower provide solid walls and high vantage for a safe camp.",
                "reward": "Rifugio ideale: +3 alla Percezione Passiva delle sentinelle durante i turni di guardia notturna."
            }
        ],
        "hazard": [
            {
                "title_it": "Ponte di Legno Pericolante",
                "title_en": "Crumbling Wooden Bridge",
                "desc_it": "Il torrente sottostante ha eroso le travi del ponte; attraversare richiede cautela.",
                "desc_en": "The rushing creek has weakened the timber bridge; crossing requires utmost care.",
                "save_stat": "DES",
                "save_dc": 12,
                "fail_effect": "Un asse cede: ritardo di 1 ora o perdita di un piccolo carico."
            }
        ]
    },
    "palude": {
        "combat": [
            {
                "title_it": "Guerrieri Lucertola delle Acque",
                "title_en": "Lizardfolk Marsh Hunters",
                "desc_it": "Guerrieri squamati emergono silenziosi dall'acqua melmosa con giavellotti e scudi d'ossa.",
                "desc_en": "Scaly warriors rise silently from the murky waters with bone shields and crude spears.",
                "monsters": [{"name": "Lizardfolk", "count": "1d4+1", "cr": "1/2"}],
                "stealth_dc": 14,
                "dist_hexes": 4
            },
            {
                "title_it": "Coccodrillo delle Rupi Fangose",
                "title_en": "Giant Mud Crocodile",
                "desc_it": "Quello che sembrava un tronco d'albero galleggiante spalanca fauci mostruose!",
                "desc_en": "What looked like a floating log suddenly opens massive, armored jaws!",
                "monsters": [{"name": "Crocodile", "count": "1d2", "cr": "1/2"}],
                "stealth_dc": 15,
                "dist_hexes": 3
            },
            {
                "title_it": "Zombi Riemersi dalle Torbiere",
                "title_en": "Bog Zombies Risen",
                "desc_it": "Cadaveri mummificati dalla torba e alghe marcescenti si alzano zoppicanti verso il party.",
                "desc_en": "Peat-mummified corpses tangled in rotting algae stumble forward hungrily.",
                "monsters": [{"name": "Zombie", "count": "1d4+2", "cr": "1/4"}],
                "stealth_dc": 10,
                "dist_hexes": 4
            }
        ],
        "social": [
            {
                "title_it": "Pescatore di Rane delle Paludi",
                "title_en": "Swamp Frogger & Guide",
                "desc_it": "Un vecchio indigeno su una chiatta a palo offre di indicare i sentieri sicuri per poche monete.",
                "desc_en": "An eccentric native on a punt pole boat offers to point out firm paths for a few coins.",
                "reward": "Guida locale: riduce la CD di navigazione della palude a 12 per oggi."
            }
        ],
        "discovery": [
            {
                "title_it": "Sorgente di Fanghi Termali Curativi",
                "title_en": "Thermal Mineral Mud Spring",
                "desc_it": "Acqua sulfurea calda gorgoglia in una conca; i suoi minerali leniscono ferite e veleni.",
                "desc_en": "Warm mineral-rich waters bubble up; the therapeutic mud soothes cuts, aches, and toxins.",
                "reward": "Bagno terapeutico: cura qualsiasi condizione Avvelenato attiva e ripristina 2d4+2 PV."
            }
        ],
        "hazard": [
            {
                "title_it": "Sabbie Mobili Improvvise",
                "title_en": "Treacherous Quicksand Pit",
                "desc_it": "La terra solida cede all'improvviso, risucchiando chi apre la marcia nella melma.",
                "desc_en": "Firm ground turns to liquid slurry, pulling whoever leads the file into a deep sinkhole.",
                "save_stat": "FOR",
                "save_dc": 14,
                "fail_effect": "Trattenuto e risucchiato: richiede una prova di FOR (Atletica) CD 14 per liberarsi."
            },
            {
                "title_it": "Miasma Fetido Paludoso",
                "title_en": "Rotting Swamp Miasma",
                "desc_it": "Una sacca di gas sulfureo erompe da una bolla putrescente nell'acqua.",
                "desc_en": "A pocket of stagnant marsh gas bursts from beneath rotting vegetation.",
                "save_stat": "COS",
                "save_dc": 13,
                "fail_effect": "TS Fallito: Avvelenato e Svantaggio alle prove di caratteristica per 4 ore."
            }
        ]
    },
    "montagna": {
        "combat": [
            {
                "title_it": "Ogre delle Caverne Rocciose",
                "title_en": "Mountain Cave Ogre",
                "desc_it": "Un gigante brutale con una clava d'albero scende dal costone sbraitando minacce.",
                "desc_en": "A brute with a crude tree-trunk club lumbers down the stony incline bellowing.",
                "monsters": [{"name": "Ogre", "count": "1", "cr": "2"}],
                "stealth_dc": 9,
                "dist_hexes": 6
            },
            {
                "title_it": "Arpie dei Dirupi",
                "title_en": "Cliff Harpy Roost",
                "desc_it": "Canti suadenti e ipnotici echeggiano tra le gole rocciose prima dell'attacco alato.",
                "desc_en": "Luring song echoes between the stone chasms before winged terrors dive.",
                "monsters": [{"name": "Harpy", "count": "1d3", "cr": "1"}],
                "stealth_dc": 13,
                "dist_hexes": 8
            }
        ],
        "social": [
            {
                "title_it": "Eremita delle Vette Innevate",
                "title_en": "Hermit of the High Peaks",
                "desc_it": "Un asceta meditante su uno spuntone di roccia avvisa il gruppo sui venti e sui passi chiusi.",
                "desc_en": "An ascetic monk meditating on a high ledge warns the party of pass blockages.",
                "reward": "Benedizione delle alture: Vantaggio al prossimo TS su Costituzione."
            }
        ],
        "discovery": [
            {
                "title_it": "Grotta Riparata con Sorgente Pura",
                "title_en": "Sheltered Cavern with Fresh Spring",
                "desc_it": "Un anfratto naturale profondo offre riparo perfetto dai venti d'alta quota e acqua fresca.",
                "desc_en": "A deep natural alcove provides pristine mountain water and complete shelter from gales.",
                "reward": "Campo d'eccellenza: Ricarica tutti gli otri e garantisce Riposo Lungo senza penalità climatiche."
            }
        ],
        "hazard": [
            {
                "title_it": "Frana di Rocce e Ghiaione",
                "title_en": "Rockslide on the Scree",
                "desc_it": "Pietre cadono dal crinale provocando una pioggia violenta di massi lungo il sentiero.",
                "desc_en": "Boulders break loose from the ridge above, hurtling down the narrow mountain trail.",
                "save_stat": "DES",
                "save_dc": 14,
                "fail_effect": "3d6 danni contundenti e caduta Prono (danni dimezzati con successo)."
            }
        ]
    },
    "deserto": {
        "combat": [
            {
                "title_it": "Scorpione Gigante delle Sabbie",
                "title_en": "Giant Sand Scorpion",
                "desc_it": "Un enorme carapace corazzato e un pungiglione gocciolante veleno affiorano dalle dune.",
                "desc_en": "Armored chitin and a dripping venomous stinger burst through the shifting sands.",
                "monsters": [{"name": "Giant Scorpion", "count": "1", "cr": "3"}],
                "stealth_dc": 13,
                "dist_hexes": 4
            },
            {
                "title_it": "Predoni Nomadi delle Loro",
                "title_en": "Desert Raider Patrol",
                "desc_it": "Predoni a cavallo di cammelli con scimitarre lucenti circondano la linea di marcia.",
                "desc_en": "Mounted raiders brandishing scimitars gallop across the dunes flanking the line.",
                "monsters": [{"name": "Bandit", "count": "1d6", "cr": "1/8"}],
                "stealth_dc": 12,
                "dist_hexes": 8
            }
        ],
        "social": [
            {
                "title_it": "Carovana di Beduini Pacifici",
                "title_en": "Bedouin Nomad Caravan",
                "desc_it": "Una carovana accogliente offre datteri, riparo all'ombra e scambi commerciali.",
                "desc_en": "A welcoming desert clan offers sweet dates, tent shade, and trade goods.",
                "reward": "Ristoro e idratazione: ripristina acqua senza spendere risorse."
            }
        ],
        "discovery": [
            {
                "title_it": "Oasi delle Palme Smeraldine",
                "title_en": "Emerald Palm Oasis",
                "desc_it": "Un lago di acqua cristallina circondato da palme da dattero e vegetazione rigogliosa.",
                "desc_en": "A pool of sparkling fresh water nestled among lush date palms.",
                "reward": "Rifornimento completo di provviste per l'intero gruppo."
            }
        ],
        "hazard": [
            {
                "title_it": "Tempesta di Sabbia Soffocante",
                "title_en": "Blinding Dust Storm",
                "desc_it": "Un muro di sabbia rossa avanza rapido coprendo il cielo e azzerando la visibilità.",
                "desc_en": "A towering wall of red dust rolls forward, blinding eyes and swallowing paths.",
                "save_stat": "COS",
                "save_dc": 13,
                "fail_effect": "Accecato temporaneamente e Sfinimento per marcia forzata nella sabbia."
            }
        ]
    },
    "sottosuolo": {
        "combat": [
            {
                "title_it": "Pattuglia di Trogloditi Sotterranei",
                "title_en": "Troglodyte Ambush",
                "desc_it": "Un tanfo nauseabondo precede l'assalto di creature sotterranee feroci e artigliate.",
                "desc_en": "A repulsive stench heralds the rush of subterranean clawed stalkers.",
                "monsters": [{"name": "Troglodyte", "count": "1d4+2", "cr": "1/4"}],
                "stealth_dc": 14,
                "dist_hexes": 4
            },
            {
                "title_it": "Ghoul Famelici delle Caverne",
                "title_en": "Underdark Ghoul Pack",
                "desc_it": "Non morti scheletrici strisciano fuori da anfratti bui cercando carne fresca.",
                "desc_en": "Flesh-craving undead scuttle from dark crevices hissing with paralytic hunger.",
                "monsters": [{"name": "Ghoul", "count": "1d3", "cr": "1"}],
                "stealth_dc": 13,
                "dist_hexes": 4
            }
        ],
        "social": [
            {
                "title_it": "Mercante Gnomo delle Profondità (Svirfneblin)",
                "title_en": "Deep Gnome (Svirfneblin) Miner",
                "desc_it": "Uno gnomo diffidente ma onesto offre gemme preziose e mappe delle gallerie.",
                "desc_en": "A cautious deep gnome miner offers gemstones and notes on cavern paths.",
                "reward": "Mappa delle gallerie: evita trappole naturali nel sottosuolo per 1 giorno."
            }
        ],
        "discovery": [
            {
                "title_it": "Grotta dei Cristalli Fosforescenti",
                "title_en": "Phosphorescent Crystal Cavern",
                "desc_it": "Migliaia di formazioni cristalline emettono una quieta luce bluastra rischiarando il buio.",
                "desc_en": "Thousands of crystal formations emit a soft blue glow illuminating the deep.",
                "reward": "Luce naturale: nessun bisogno di torce; +1 morale ai tiri salvezza."
            }
        ],
        "hazard": [
            {
                "title_it": "Crollo di Stalattiti dal Soffitto",
                "title_en": "Collapsing Stalactites",
                "desc_it": "Vibrazioni sismiche spezzano punte rocciose che precipitano verso il pavimento.",
                "desc_en": "Tremors crack the ceiling, dropping sharp mineral spikes toward the cavern floor.",
                "save_stat": "DES",
                "save_dc": 14,
                "fail_effect": "2d8 danni perforanti (dimezzati con successo)."
            }
        ]
    },
    "costiero": {
        "combat": [
            {
                "title_it": "Assalitori Sahuagin delle Maree",
                "title_en": "Sahuagin Tide Raider Pack",
                "desc_it": "Guerrieri marini dalle scaglie iridescenti emergono dalla risacca brandendo tridenti.",
                "desc_en": "Fish-like scaled warriors surge from the surf wielding coral tridents.",
                "monsters": [{"name": "Sahuagin", "count": "1d4+1", "cr": "1/2"}],
                "stealth_dc": 13,
                "dist_hexes": 5
            }
        ],
        "social": [
            {
                "title_it": "Guardiani del Faro Solitario",
                "title_en": "Lonely Lighthouse Keepers",
                "desc_it": "Due vecchi marinai offrono zuppa di pesce e racconti sui mostri marini.",
                "desc_en": "Veteran mariners offer seafood chowder, a hearth, and local legends.",
                "reward": "Pasto caldo e riposo sicuro al coperto."
            }
        ],
        "discovery": [
            {
                "title_it": "Relitto di Nave Arenata",
                "title_en": "Beached Shipwreck Hull",
                "desc_it": "La carcassa di una goletta spezzata tra gli scogli conserva una cassa sigillata.",
                "desc_en": "The wooden ribs of a schooner beached among shoals hold an intact sealed chest.",
                "reward": "Bottino del relitto: 3d10 MO, cannocchiale e strumenti da navigatore."
            }
        ],
        "hazard": [
            {
                "title_it": "Onda di Marea Improvvisa",
                "title_en": "Rogue Tidal Surge",
                "desc_it": "Una serie di onde giganti si infrange sulla spiaggia spazzando via il sentiero costiero.",
                "desc_en": "A rogue surge breaks violently across the strand, threatening to wash gear into the sea.",
                "save_stat": "FOR",
                "save_dc": 13,
                "fail_effect": "Caduta Prono e trascinamento per 3 esagoni; 1d6 danni contundenti."
            }
        ]
    },
    "tundra": {
        "combat": [
            {
                "title_it": "Lupi delle Nevi Famelici",
                "title_en": "Arctic Winter Wolves",
                "desc_it": "Sagome bianche quasi invisibili nella bufera scattano con zanne congelate.",
                "desc_en": "White silhouettes nearly invisible in the flurry pounce with frost-coated fangs.",
                "monsters": [{"name": "Wolf", "count": "1d4", "cr": "1/4"}],
                "stealth_dc": 15,
                "dist_hexes": 5
            }
        ],
        "social": [
            {
                "title_it": "Cacciatori della Tundra con Slitte",
                "title_en": "Tundra Sled Hunters",
                "desc_it": "Un gruppo di cacciatori in pelli di renna scambia carne affumicata con manufatti.",
                "desc_en": "Caribou-cloaked hunters with sled dogs trade cured meat and warm furs.",
                "reward": "Scambio pelli e carne affumicata."
            }
        ],
        "discovery": [
            {
                "title_it": "Rifugio di Ghiaccio Protetto (Iglu)",
                "title_en": "Insulated Ice Shelter",
                "desc_it": "Un iglu scavato con cura isola completamente dal gelo esterno.",
                "desc_en": "A carefully sculpted snow shelter provides absolute isolation from sub-zero winds.",
                "reward": "Riposo caldo: immunità da danni da freddo durante il riposo lungo."
            }
        ],
        "hazard": [
            {
                "title_it": "Lastra di Ghiaccio Cedevole",
                "title_en": "Thin Ice Sheet",
                "desc_it": "Il ghiaccio sotto la neve fresca crepita e cede sotto il peso del gruppo.",
                "desc_en": "Thin ice beneath fresh powder splinters and gives way into frigid deeps.",
                "save_stat": "DES",
                "save_dc": 14,
                "fail_effect": "Immersione in acqua gelida: 2d6 danni da freddo e rischio ipotermia."
            }
        ]
    }
}

def get_biome_presets(lang: Optional[str] = None) -> List[Dict[str, Any]]:
    """Restituisce l'elenco dei biomi disponibili formattati nella lingua corrente."""
    cur_lang = (lang or get_language() or "it").lower()
    is_en = cur_lang.startswith("en")
    presets = []
    for key, data in BIOMES.items():
        p = dict(data)
        p["display_name"] = data["name_en"] if is_en else data["name_it"]
        p["description"] = data["description_en"] if is_en else data["description_it"]
        presets.append(p)
    return presets

def get_danger_presets(lang: Optional[str] = None) -> List[Dict[str, Any]]:
    cur_lang = (lang or get_language() or "it").lower()
    is_en = cur_lang.startswith("en")
    presets = []
    for key, data in DANGER_LEVELS.items():
        p = dict(data)
        p["display_name"] = data["name_en"] if is_en else data["name_it"]
        presets.append(p)
    return presets

def generate_biome_encounter(
    biome_key: str = "foresta",
    danger_key: str = "moderate",
    is_night: bool = False,
    force_category: Optional[str] = None,
    lang: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera un incontro casuale (Combattimento, Sociale, Scoperta o Pericolo) in base a
    bioma, grado di pericolo e ora del giorno.
    """
    cur_lang = (lang or get_language() or "it").lower()
    is_en = cur_lang.startswith("en")

    biome_data = BIOME_ENCOUNTERS.get(biome_key.lower()) or BIOME_ENCOUNTERS["foresta"]
    danger_info = DANGER_LEVELS.get(danger_key.lower()) or DANGER_LEVELS["moderate"]
    threshold = danger_info["encounter_threshold"]
    if is_night:
        threshold = max(2, threshold - 2) # Più probabile di notte

    d20_roll = roll_dice("1d20")["total"]
    occurred = (d20_roll >= threshold)

    if not occurred and not force_category:
        return {
            "occurred": False,
            "roll": d20_roll,
            "threshold": threshold,
            "message": "Nessun incontro: il viaggio prosegue indisturbato." if not is_en else "No encounter: the journey proceeds peacefully."
        }

    # Selezione categoria
    cat = force_category
    if not cat:
        if is_night:
            # Di notte prevalgono minacce e pericoli
            weights = [("combat", 60), ("hazard", 25), ("social", 10), ("discovery", 5)]
        else:
            weights = [("combat", 40), ("social", 25), ("discovery", 20), ("hazard", 15)]
        
        # Filtra solo categorie con eventi disponibili nel bioma
        avail_weights = [(c, w) for c, w in weights if c in biome_data and len(biome_data[c]) > 0]
        if not avail_weights:
            cat = "combat"
        else:
            total_w = sum(w for _, w in avail_weights)
            r = random.randint(1, total_w)
            curr = 0
            for c, w in avail_weights:
                curr += w
                if r <= curr:
                    cat = c
                    break

    cat_list = biome_data.get(cat) or biome_data.get("combat", [])
    if not cat_list:
        event = {
            "title_it": "Incontro Generico",
            "title_en": "Generic Encounter",
            "desc_it": "Una minaccia si profila all'orizzonte.",
            "desc_en": "A threat looms on the horizon."
        }
    else:
        event = random.choice(cat_list)

    # Risoluzione conteggio mostri se presente
    monsters_result = []
    if "monsters" in event:
        for m in event["monsters"]:
            cnt_expr = m.get("count", "1")
            cnt_val = roll_dice(cnt_expr)["total"] if any(c in cnt_expr for c in "dD+-") else int(cnt_expr)
            monsters_result.append({
                "name": m["name"],
                "count": max(1, cnt_val),
                "cr": m.get("cr", "1/4")
            })

    title = event.get("title_en") if is_en else event.get("title_it")
    desc = event.get("desc_en") if is_en else event.get("desc_it")

    return {
        "occurred": True,
        "roll": d20_roll,
        "threshold": threshold,
        "category": cat,
        "title": title,
        "description": desc,
        "biome": biome_key,
        "danger": danger_key,
        "is_night": is_night,
        "stealth_dc": event.get("stealth_dc", 12),
        "dist_hexes": event.get("dist_hexes", 6),
        "save_stat": event.get("save_stat"),
        "save_dc": event.get("save_dc"),
        "fail_effect": event.get("fail_effect"),
        "reward": event.get("reward"),
        "monsters": monsters_result
    }

def calculate_effective_sentinel_pp(
    player: Any,
    has_campfire: bool = True,
    is_night: bool = True
) -> Dict[str, Any]:
    """
    Calcola la Percezione Passiva efficace di una sentinella di guardia notturna (5e RAW):
    - Base: 10 + Modificatore Saggezza (Percezione)
    - Al buio senza Scurovisione e senza falò: Svantaggio (-5 PP)
    - Con falò acceso: vede normalmente entro la luce (nessuna penalità)
    - Trance Elfica: richiede solo 4 ore di meditazione invece di 6 di sonno.
    """
    sheet = getattr(player, "full_sheet", {}) or {}
    attrs = sheet.get("attributes", {}) if isinstance(sheet, dict) else {}
    sag_val = attrs.get("SAG", attrs.get("WIS", 10))
    try: sag_mod = (int(sag_val) - 10) // 2
    except (ValueError, TypeError): sag_mod = 0

    skills = sheet.get("skills", {}) if isinstance(sheet, dict) else {}
    perc_bonus = skills.get("Percezione", skills.get("Perception", 0))
    try: perc_val = int(perc_bonus)
    except (ValueError, TypeError): perc_val = 0

    base_pp = 10 + sag_mod + perc_val
    has_dv = bool(getattr(player, "has_darkvision", False))
    if not has_dv and isinstance(sheet, dict):
        race = str(sheet.get("race", "")).lower()
        if any(r in race for r in ("elf", "elfo", "dwarf", "nano", "gnomo", "gnome", "tiefling")):
            has_dv = True

    penalty = 0
    note = "Visione Chiara"
    if is_night and not has_campfire:
        if not has_dv:
            penalty = -5
            note = "Oscurità Totale (-5 PP, Senza Scurovisione)"
        else:
            penalty = -5
            note = "Luce Fioca / Buio (-5 PP, Scurovisione)"

    final_pp = base_pp + penalty

    # Controllo Trance Elfica (4 ore di riposo invece di 6)
    is_elf = False
    if isinstance(sheet, dict):
        r_name = str(sheet.get("race", "")).lower()
        feats = [str(f).lower() for f in sheet.get("features", [])]
        is_elf = ("elf" in r_name or "elfo" in r_name or any("trance" in f for f in feats))

    return {
        "player_name": getattr(player, "name", "Sentinella"),
        "base_pp": base_pp,
        "final_pp": final_pp,
        "has_darkvision": has_dv,
        "is_elf_trance": is_elf,
        "max_watch_hours": 4 if is_elf else 2,
        "note": note
    }

def resolve_night_camp_simulation(
    watch_shifts: Dict[int, str],
    players: List[Any],
    biome_key: str = "foresta",
    danger_key: str = "moderate",
    has_campfire: bool = True
) -> Dict[str, Any]:
    """
    Simula le 8 ore del Riposo Lungo notturno divise in 4 turni da 2 ore.
    Determina se si verifica un incontro notturno, verifica la reazione della sentinella di turno
    e notifica se il gruppo viene sorpreso nel sonno o allertato in tempo.
    """
    shift_hours = {
        1: ("22:00 - 00:00", "Prima Notte"),
        2: ("00:00 - 02:00", "Mezzanotte"),
        3: ("02:00 - 04:00", "Cuore della Notte"),
        4: ("04:00 - 06:00", "Alba")
    }

    players_by_name = {p.name: p for p in players if hasattr(p, "name")}

    # Tira incontro notturno: 1 incontro al massimo per notte
    night_enc = generate_biome_encounter(biome_key, danger_key, is_night=True)
    has_event = night_enc.get("occurred", False)

    target_shift = random.randint(1, 4) if has_event else None
    logs = []
    ambush = False
    alerted = False
    sentinel_name = "Nessuno"
    sentinel_pp = 10

    for s_idx in range(1, 5):
        h_range, period_name = shift_hours[s_idx]
        assigned_name = watch_shifts.get(s_idx) or watch_shifts.get(str(s_idx))
        p_obj = players_by_name.get(assigned_name)
        
        if p_obj:
            s_stats = calculate_effective_sentinel_pp(p_obj, has_campfire, is_night=True)
            sentinel_desc = f"{p_obj.name} (PP {s_stats['final_pp']})"
        else:
            sentinel_desc = "Nessuna sentinella di guardia! ⚠️"

        if has_event and s_idx == target_shift:
            sentinel_name = p_obj.name if p_obj else "Nessuno"
            cat = night_enc.get("category", "combat")
            title = night_enc.get("title", "Pericolo")
            s_dc = night_enc.get("stealth_dc", 13)

            if p_obj:
                s_pp = calculate_effective_sentinel_pp(p_obj, has_campfire, is_night=True)["final_pp"]
                sentinel_pp = s_pp
                if s_pp >= s_dc:
                    alerted = True
                    logs.append(f"⏰ Turno {s_idx} ({h_range} - {period_name}): Guardia: {sentinel_desc} -> 👁️ {p_obj.name} NOTA IL PERICOLO! ({title}, Insidia CD {s_dc} vs PP {s_pp}). Il gruppo viene allertato in tempo!")
                else:
                    ambush = True
                    logs.append(f"⏰ Turno {s_idx} ({h_range} - {period_name}): Guardia: {sentinel_desc} -> ⚠️ IMBOSCATA NOTTURNA! I nemici ({title}, Furtività CD {s_dc}) superano la guardia (PP {s_pp})! Il gruppo è colto nel sonno!")
            else:
                ambush = True
                logs.append(f"⏰ Turno {s_idx} ({h_range} - {period_name}): Nessuna guardia! -> 💀 IMBOSCATA NOTTURNA! Il gruppo viene assalito nel sonno da {title}!")
        else:
            logs.append(f"🌙 Turno {s_idx} ({h_range} - {period_name}): Guardia: {sentinel_desc} -> Notte serena e tranquilla.")

    return {
        "event_occurred": has_event,
        "encounter": night_enc if has_event else None,
        "target_shift": target_shift,
        "ambush": ambush,
        "alerted": alerted,
        "sentinel_name": sentinel_name,
        "sentinel_pp": sentinel_pp,
        "logs": logs,
        "has_campfire": has_campfire
    }
