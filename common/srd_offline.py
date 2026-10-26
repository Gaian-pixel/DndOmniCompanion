# common/srd_offline.py
"""
Modulo per la consultazione offline e fallback immediato delle risorse D&D 5e SRD.
Carica e indicizza in memoria i file JSON locali in srd_data/ per:
- Incantesimi (319 incantesimi SRD 5.1)
- Mostri e Creature (oltre 1.000 mostri da SRD, Creature Codex e Tome of Beasts)
- Oggetti Magici (237 oggetti magici SRD)
- Progressione e Privilegi di Livello (Classi core 1-20)

Fornisce supporto bilingue IT/EN trasparente.
"""

import os
import json
import re
import ast
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRD_DIR = os.path.join(BASE_DIR, "srd_data")

# Dizionario traduzione incantesimi Italiano -> Inglese (SRD + PHB + XGtE + TCoE)
SPELL_IT_TO_EN = {
    # Trucchetti (Cantrips)
    "luce": "light",
    "mano magica": "mage hand",
    "prestidigitazione": "prestidigitation",
    "raggio di gelo": "ray of frost",
    "dardo di fuoco": "fire bolt",
    "scossa folgorante": "shocking grasp",
    "stretta folgorante": "shocking grasp",
    "spruzzo तलाश": "acid splash",
    "spruzzo acido": "acid splash",
    "fiamma sacra": "sacred flame",
    "taumaturgia": "thaumaturgy",
    "guida": "guidance",
    "resistenza": "resistance",
    "salvare i morenti": "spare the dying",
    "stabilizzare": "spare the dying",
    "artificio druidico": "druidcraft",
    "produrre fiamma": "produce flame",
    "randello incantato": "shillelagh",
    "frusta di spine": "thorn whip",
    "beffa crudele": "vicious mockery",
    "luci danzanti": "dancing lights",
    "illusione minore": "minor illusion",
    "riparare": "mending",
    "messaggio": "message",
    "colpo accurato": "true strike",
    "esplosione mistica": "eldritch blast",
    "deflagrazione occulta": "eldritch blast",
    "tocco gelido": "chill touch",
    "spruzzo velenoso": "poison spray",
    "lama rombante": "booming blade",
    "lama di fiamma verde": "green-flame blade",
    "rintocco dei morti": "toll the dead",
    "scheggia mentale": "mind sliver",
    # 1° Livello
    "dardo incantato": "magic missile",
    "scudo": "shield",
    "armatura magica": "mage armor",
    "sonno": "sleep",
    "mani brucianti": "burning hands",
    "onda tonante": "thunderwave",
    "individuazione del magico": "detect magic",
    "identificare": "identify",
    "caduta morbida": "feather fall",
    "allarme": "alarm",
    "trova famiglio": "find familiar",
    "unto": "grease",
    "spruzzo di colori": "color spray",
    "camuffare se stesso": "disguise self",
    "immagine silenziosa": "silent image",
    "charme su persone": "charm person",
    "comprensione dei linguaggi": "comprehend languages",
    "ritirata rapida": "expeditious retreat",
    "salto": "jump",
    "passo veloce": "longstrider",
    "nube di nebbia": "fog cloud",
    "risata incontenibile": "hideous laughter",
    "risata incontenibile di tasha": "hideous laughter",
    "cura ferite": "cure wounds",
    "parola guaritrice": "healing word",
    "benedizione": "bless",
    "anatema": "bane",
    "scudo della fede": "shield of faith",
    "santuario": "sanctuary",
    "dardo tracciante": "guiding bolt",
    "infliggi ferite": "inflict wounds",
    "comando": "command",
    "creare o distruggere acqua": "create or destroy water",
    "individuazione del bene e del male": "detect evil and good",
    "protezione dal bene e dal male": "protection from evil and good",
    "purificare cibo e bevande": "purify food and drink",
    "bacche benefiche": "goodberry",
    "intralciare": "entangle",
    "luminescenza": "faerie fire",
    "parlare con gli animali": "speak with animals",
    "amicizia con gli animali": "animal friendship",
    "eroismo": "heroism",
    "sussurri dissonanti": "dissonant whispers",
    "sortilegio": "hex",
    "maledizione": "hex",
    "armatura di agathys": "armor of agathys",
    "braccia di hadar": "arms of hadar",
    "intimorire infernale": "hellish rebuke",
    "marchio del cacciatore": "hunter's mark",
    "stoccata argentea": "silvery barbs",
    "globo cromatico": "chromatic orb",
    "dardo del caos": "chaos bolt",
    "dardo stregato": "witch bolt",
    "punizione tonante": "thunderous smite",
    "punizione incandescente": "searing smite",
    "punizione collerica": "wrathful smite",
    "favore divino": "divine favor",
    # 2° Livello
    "passo velato": "misty step",
    "invisibilità": "invisibility",
    "invisibilita": "invisibility",
    "scurovisione": "darkvision",
    "levitazione": "levitate",
    "ragnatela": "web",
    "immagine speculare": "mirror image",
    "sfocatura": "blur",
    "raggio rovente": "scorching ray",
    "frantumare": "shatter",
    "oscurità": "darkness",
    "oscurita": "darkness",
    "fiamma perenne": "continual flame",
    "individuazione dei pensieri": "detect thoughts",
    "suggestione": "suggestion",
    "blocca persone": "hold person",
    "cecità/sordità": "blindness/deafness",
    "cecita/sordita": "blindness/deafness",
    "ingrandire/ridurre": "enlarge/reduce",
    "alterare se stesso": "alter self",
    "scassinare": "knock",
    "serratura arcana": "arcane lock",
    "vedere invisibilità": "see invisibility",
    "arma magica": "magic weapon",
    "arma spirituale": "spiritual weapon",
    "preghiera di guarigione": "prayer of healing",
    "ristorare inferiore": "lesser restoration",
    "silenzio": "silence",
    "zona di verità": "zone of truth",
    "aiuto": "aid",
    "augurio": "augury",
    "calmare emozioni": "calm emotions",
    "fiamma spirituale": "spiritual weapon",
    "lama infuocata": "flame blade",
    "sfera infuocata": "flaming sphere",
    "bagliore lunare": "moonbeam",
    "pelle coriacea": "barkskin",
    "passare senza tracce": "pass without trace",
    "riscaldare il metallo": "heat metal",
    "crescita di spine": "spike growth",
    "nube di pugnali": "cloud of daggers",
    "corona di follia": "crown of madness",
    "frusta mentale di tasha": "tasha's mind whip",
    "lama d'ombra": "shadow blade",
    # 3° Livello
    "palla di fuoco": "fireball",
    "fulmine": "lightning bolt",
    "controincantesimo": "counterspell",
    "dissolvi magie": "dispel magic",
    "volare": "fly",
    "velocità": "haste",
    "velocita": "haste",
    "lentezza": "slow",
    "immagine maggiore": "major image",
    "trama ipnotica": "hypnotic pattern",
    "paura": "fear",
    "intermittenza": "blink",
    "forma gassosa": "gaseous form",
    "respirare sott'acqua": "water breathing",
    "camminare sull'acqua": "water walk",
    "luce diurna": "daylight",
    "capanna di leomund": "tiny hut",
    "circolo magico": "magic circle",
    "protezione dall'energia": "protection from energy",
    "scagliare maledizione": "bestow curse",
    "rimuovi maledizione": "remove curse",
    "toccare del vampiro": "vampiric touch",
    "animare morti": "animate dead",
    "parlare con i morti": "speak with dead",
    "rinascita": "revivify",
    "rivivificare": "revivify",
    "guardiani spirituali": "spirit guardians",
    "parola guaritrice di massa": "mass healing word",
    "faro di speranza": "beacon of hope",
    "invocare il fulmine": "call lightning",
    "crescita vegetale": "plant growth",
    "tempesta di nevischio": "sleet storm",
    "evoca animali": "conjure animals",
    "fame di hadar": "hunger of hadar",
    "sudario spirituale": "spirit shroud",
    # 4° Livello
    "porta dimensionale": "dimension door",
    "invisibilità superiore": "greater invisibility",
    "invisibilita superiore": "greater invisibility",
    "metamorfosi": "polymorph",
    "esilio": "banishment",
    "muro di fuoco": "wall of fire",
    "tempesta di ghiaccio": "ice storm",
    "devastazione": "blight",
    "scudo di fuoco": "fire shield",
    "pelle di pietra": "stoneskin",
    "tentacoli neri": "black tentacles",
    "occhio arcano": "arcane eye",
    "confusione": "confusion",
    "libertà di movimento": "freedom of movement",
    "interdizione alla morte": "death ward",
    "guardiano della fede": "guardian of faith",
    "divinazione": "divination",
    # 5° Livello
    "muro di forza": "wall of force",
    "muro di pietra": "wall of stone",
    "cono di freddo": "cone of cold",
    "telecinesi": "telekinesis",
    "blocca mostri": "hold monster",
    "dominare persone": "dominate person",
    "scrutare": "scrying",
    "nube mortale": "cloudkill",
    "animare oggetti": "animate objects",
    "mano arcana": "arcane hand",
    "mano di bigby": "bigby's hand",
    "cura ferite di massa": "mass cure wounds",
    "ristorare superiore": "greater restoration",
    "rianimare morti": "raise dead",
    "colpo infuocato": "flame strike",
    "comunione": "commune",
    "contagio": "contagion",
    "piaga degli insetti": "insect plague",
    "reincarnazione": "reincarnate",
    "statica sinaptica": "synaptic static",
    "colpo del vento d'acciaio": "steel wind strike",
    "onda distruttiva": "destructive wave",
    # 6° Livello
    "disintegrazione": "disintegrate",
    "catena di fulmini": "chain lightning",
    "globo di invulnerabilità": "globe of invulnerability",
    "muro di ghiaccio": "wall of ice",
    "visione del vero": "true seeing",
    "guarigione": "heal",
    "ferire": "harm",
    "banchetto degli eroi": "heroes' feast",
    "barriera di lame": "blade barrier",
    "raggio solare": "sunbeam",
    "trasporto vegetale": "transport via plants",
    "danza irresistibile": "irresistible dance",
    "sguardo penetrante": "eyebite",
    "cerchio di morte": "circle of death",
    # 7° Livello
    "teletrasporto": "teleport",
    "dito della morte": "finger of death",
    "palla di fuoco ritardata": "delayed blast fireball",
    "spostamento planare": "plane shift",
    "inversione della gravità": "reverse gravity",
    "gabbia di forza": "forcecage",
    "spada arcana": "arcane sword",
    "resurrezione": "resurrection",
    "parola divina": "divine word",
    "rigenerazione": "regenerate",
    "tempesta di fuoco": "fire storm",
    # 8° Livello
    "dominare mostri": "dominate monster",
    "parola del potere stordire": "power word stun",
    "vuoto mentale": "mind blank",
    "labirinto": "maze",
    "nube incendiaria": "incendiary cloud",
    "esplosione solare": "sunburst",
    "terremoto": "earthquake",
    "campo anti-magia": "antimagic field",
    "aura sacra": "holy aura",
    # 9° Livello
    "desiderio": "wish",
    "fermare il tempo": "time stop",
    "sciame di meteore": "meteor swarm",
    "parola del potere uccidere": "power word kill",
    "metamorfosi pura": "true polymorph",
    "previsione": "foresight",
    "resurrezione pura": "true resurrection",
    "guarigione di massa": "mass heal",
    "portale": "gate",
    "proiezione astrale": "astral projection",
    "forma cangiante": "shapechange",
}

# Dizionario traduzione mostri più comuni Italiano -> Inglese (SRD + MM)
MONSTER_IT_TO_EN = {
    "orco": "orc",
    "capoguerra orco": "orc war chief",
    "scheletro": "skeleton",
    "scheletro di cavallo da guerra": "warhorse skeleton",
    "scheletro minotauro": "minotaur skeleton",
    "drago": "dragon",
    "drago rosso": "red dragon",
    "drago nero": "black dragon",
    "drago blu": "blue dragon",
    "drago verde": "green dragon",
    "drago bianco": "white dragon",
    "goblin": "goblin",
    "hobgoblin": "hobgoblin",
    "bugbear": "bugbear",
    "coboldo": "kobold",
    "gnoll": "gnoll",
    "lucertoloide": "lizardfolk",
    "uomo lucertola": "lizardfolk",
    "zombie": "zombie",
    "zombie ogre": "ogre zombie",
    "ghoul": "ghoul",
    "ghast": "ghast",
    "mummia": "mummy",
    "signore delle mummie": "mummy lord",
    "vampiro": "vampire",
    "progenie vampirica": "vampire spawn",
    "spettro": "specter",
    "ombra": "shadow",
    "wight": "wight",
    "wraith": "wraith",
    "apparizione": "wraith",
    "fantasma": "ghost",
    "banshee": "banshee",
    "fuoco fatuo": "will-o'-wisp",
    "cavaliere della morte": "death knight",
    "demilich": "demilich",
    "teschio delle fiamme": "flameskull",
    "licantropo": "werewolf",
    "lupo mannaro": "werewolf",
    "ratto mannaro": "wererat",
    "cinghiale mannaro": "wereboar",
    "tigre mannara": "weretiger",
    "orso mannaro": "werebear",
    "lupo": "wolf",
    "lupo crudele": "dire wolf",
    "lupo invernale": "winter wolf",
    "worg": "worg",
    "mastino": "mastiff",
    "ragno gigante": "giant spider",
    "ragno": "spider",
    "ragno fase": "phase spider",
    "ettercap": "ettercap",
    "scorpione gigante": "giant scorpion",
    "ratto gigante": "giant rat",
    "pipistrello gigante": "giant bat",
    "aquila gigante": "giant eagle",
    "gufo gigante": "giant owl",
    "serpente costrittore gigante": "giant constrictor snake",
    "serpente velenoso gigante": "giant poisonous snake",
    "orso bruno": "brown bear",
    "orso nero": "black bear",
    "orso polare": "polar bear",
    "orso gufo": "owlbear",
    "orsogufo": "owlbear",
    "cinghiale": "boar",
    "tigre": "tiger",
    "leone": "lion",
    "squalo": "reef shark",
    "squalo gigante": "giant shark",
    "cavallo da guerra": "warhorse",
    "cavallo da sella": "riding horse",
    "troll": "troll",
    "ogre": "ogre",
    "oni": "oni",
    "ettin": "ettin",
    "gigante delle colline": "hill giant",
    "gigante di pietra": "stone giant",
    "gigante del fuoco": "fire giant",
    "gigante del gelo": "frost giant",
    "gigante delle nuvole": "cloud giant",
    "gigante delle tempeste": "storm giant",
    "gargolla": "gargoyle",
    "golem di ferro": "iron golem",
    "golem di pietra": "stone golem",
    "golem di argilla": "clay golem",
    "golem di carne": "flesh golem",
    "armatura animata": "animated armor",
    "spada volante": "flying sword",
    "tappeto soffocante": "rug of smothering",
    "scudo guardiano": "shield guardian",
    "idra": "hydra",
    "minotauro": "minotaur",
    "medusa": "medusa",
    "chimera": "chimera",
    "manticora": "manticore",
    "viverna": "wyvern",
    "arpia": "harpy",
    "pegaso": "pegasus",
    "grifone": "griffon",
    "ippogrifo": "hippogriff",
    "basilisco": "basilisk",
    "cockatrice": "cockatrice",
    "bulette": "bulette",
    "ankheg": "ankheg",
    "ruggine": "rust monster",
    "mostro della ruggine": "rust monster",
    "mimic": "mimic",
    "cubo gelatinoso": "gelatinous cube",
    "melma grigia": "gray ooze",
    "budino nero": "black pudding",
    "gelatina ocra": "ochre jelly",
    "beholder": "beholder",
    "osservatore": "beholder",
    "scortica menti": "mind flayer",
    "divoratore di menti": "mind flayer",
    "mind flayer": "mind flayer",
    "illithid": "mind flayer",
    "belva distorcente": "displacer beast",
    "vermeiena": "carrion crawler",
    "umber hulk": "umber hulk",
    "yuan-ti abominio": "yuan-ti abomination",
    "githyanki": "githyanki warrior",
    "githyanki guerriero": "githyanki warrior",
    "slaad rosso": "red slaad",
    "drago fatato": "faerie dragon",
    "kuo-toa": "kuo-toa",
    "kenku": "kenku",
    "aarakocra": "aarakocra",
    "sovrano miconide": "myconid sovereign",
    "demone d'ombra": "shadow demon",
    "yochlol": "yochlol",
    "succube": "succubus",
    "demone": "demon",
    "balor": "balor",
    "marilith": "marilith",
    "glabrezu": "glabrezu",
    "hezrou": "hezrou",
    "vrock": "vrock",
    "dretch": "dretch",
    "quasit": "quasit",
    "diavolo": "devil",
    "diavolo della fossa": "pit fiend",
    "diavolo del ghiaccio": "ice devil",
    "diavolo cornuto": "horned devil",
    "diavolo delle catene": "chain devil",
    "diavolo spinato": "barbed devil",
    "diavolo barbuto": "bearded devil",
    "imp": "imp",
    "rakshasa": "rakshasa",
    "segugio infernale": "hell hound",
    "incubo": "nightmare",
    "elementale del fuoco": "fire elemental",
    "elementale dell'acqua": "water elemental",
    "elementale dell'aria": "air elemental",
    "elementale della terra": "earth elemental",
    "mephit": "magma mephit",
    "salamandra": "salamander",
    "xorn": "xorn",
    "aboleth": "aboleth",
    "chuul": "chuul",
    "otyugh": "otyugh",
    "roper": "roper",
    "cloaker": "cloaker",
    "drider": "drider",
    "remorhaz": "remorhaz",
    "verme purpureo": "purple worm",
    "kraken": "kraken",
    "unicorno": "unicorn",
    "couatl": "couatl",
    "deva": "deva",
    "planetar": "planetar",
    "solar": "solar",
    "strega verde": "green hag",
    "strega notturna": "night hag",
    "strega marina": "sea hag",
    "driade": "dryad",
    "treant": "treant",
    "arbusto risvegliato": "awakened shrub",
    "albero risvegliato": "awakened tree",
    "cumulo strisciante": "shambling mound",
    # Draghi per categoria d'età
    "drago blu antico": "ancient blue dragon",
    "drago rosso antico": "ancient red dragon",
    "drago nero antico": "ancient black dragon",
    "drago verde antico": "ancient green dragon",
    "drago bianco antico": "ancient white dragon",
    "drago d'oro antico": "ancient gold dragon",
    "drago d'argento antico": "ancient silver dragon",
    "drago di bronzo antico": "ancient bronze dragon",
    "drago di rame antico": "ancient copper dragon",
    "drago d'ottone antico": "ancient brass dragon",
    "drago blu adulto": "adult blue dragon",
    "drago rosso adulto": "adult red dragon",
    "drago nero adulto": "adult black dragon",
    "drago verde adulto": "adult green dragon",
    "drago bianco adulto": "adult white dragon",
    "drago d'oro adulto": "adult gold dragon",
    "drago d'argento adulto": "adult silver dragon",
    "drago blu giovane": "young blue dragon",
    "drago rosso giovane": "young red dragon",
    "drago nero giovane": "young black dragon",
    "drago verde giovane": "young green dragon",
    "drago bianco giovane": "young white dragon",
    "cucciolo di drago blu": "blue dragon wyrmling",
    "cucciolo di drago rosso": "red dragon wyrmling",
    "lich": "lich",
    "tarrasque": "tarrasque",
    "tarasque": "tarrasque",
    # PNG / Umanoidi Standard
    "bandito": "bandit",
    "capo bandito": "bandit captain",
    "cultista": "cultist",
    "fanatico del culto": "cult fanatic",
    "guardia": "guard",
    "cavaliere": "knight",
    "assassino": "assassin",
    "arcimago": "archmage",
    "mago": "mage",
    "veterano": "veteran",
    "gladiatore": "gladiator",
    "berserker": "berserker",
    "sacerdote": "priest",
    "druido": "druid",
    "spia": "spy",
    "esploratore": "scout",
    "nobile": "noble",
    "popolano": "commoner",
    "accolito": "acolyte",
    "malvivente": "thug",
    "drow": "drow",
    "duergar": "duergar",
}

# Dizionario traduzione oggetti magici ed equipaggiamento Italiano -> Inglese
ITEM_IT_TO_EN = {
    "pozione di guarigione": "potion of healing",
    "pozione di cura": "potion of healing",
    "pozione di guarigione maggiore": "potion of greater healing",
    "pozione di guarigione superiore": "potion of superior healing",
    "pozione di guarigione suprema": "potion of supreme healing",
    "pozione di volo": "potion of flying",
    "pozione di invisibilità": "potion of invisibility",
    "pozione di invisibilita": "potion of invisibility",
    "pozione di velocità": "potion of speed",
    "pozione di velocita": "potion of speed",
    "pozione di eroismo": "potion of heroism",
    "pozione di forza del gigante": "potion of giant strength",
    "pozione di resistenza": "potion of resistance",
    "pozione di chiaroveggenza": "potion of clairvoyance",
    "pozione di respirare sott'acqua": "potion of water breathing",
    "pozione di forma gassosa": "potion of gaseous form",
    "pozione di crescita": "potion of growth",
    "pozione di rimpicciolimento": "potion of diminution",
    "pozione del veleno": "potion of poison",
    "olio di affilatura": "oil of sharpness",
    "olio di etereità": "oil of etherealness",
    "olio di scivolosità": "oil of slipperiness",
    "borsa conservante": "bag of holding",
    "zaino pratico di heward": "handy haversack",
    "zaino pratico": "handy haversack",
    "buco portatile": "portable hole",
    "mantello della protezione": "cloak of protection",
    "mantello elfico": "cloak of elvenkind",
    "mantello dello spostamento": "cloak of displacement",
    "mantello del pipistrello": "cloak of the bat",
    "mantello dell'aracnide": "cloak of arachnida",
    "mantello della manta": "cloak of the manta ray",
    "stivali elfici": "boots of elvenkind",
    "stivali della velocità": "boots of speed",
    "stivali della levitazione": "boots of levitation",
    "stivali alati": "winged boots",
    "stivali del passo e del balzo": "boots of striding and springing",
    "stivali delle terre invernali": "boots of the winterlands",
    "pantofole della scalata del ragno": "slippers of spider climbing",
    "anello di protezione": "ring of protection",
    "anello dell'invisibilità": "ring of invisibility",
    "anello di accumulo degli incantesimi": "ring of spell storing",
    "anello della rigenerazione": "ring of regeneration",
    "anello dell'evasione": "ring of evasion",
    "anello di azione libera": "ring of free action",
    "anello della resistenza": "ring of resistance",
    "anello del nuoto": "ring of swimming",
    "anello del salto": "ring of jumping",
    "anello del camminare sull'acqua": "ring of water walking",
    "anello della telecinesi": "ring of telekinesis",
    "anello dei tre desideri": "ring of three wishes",
    "anello di deviazione degli incantesimi": "ring of spell turning",
    "amuleto della salute": "amulet of health",
    "amuleto contro localizzazione e individuazione": "amulet of proof against detection and location",
    "periapt della chiusura delle ferite": "periapt of wound closure",
    "amuleto della chiusura delle ferite": "periapt of wound closure",
    "fascia dell'intelletto": "headband of intellect",
    "guanti del potere orchesco": "gauntlets of ogre power",
    "guanti cattura frecce": "gloves of missile snaring",
    "guanti del furto": "gloves of thievery",
    "cintura della forza dei giganti": "belt of giant strength",
    "cintura dei nani": "belt of dwarvenkind",
    "bacchetta dei dardi incantati": "wand of magic missiles",
    "bacchetta delle palle di fuoco": "wand of fireballs",
    "bacchetta dei fulmini": "wand of lightning bolts",
    "bacchetta dell'individuazione del magico": "wand of magic detection",
    "bacchetta dei segreti": "wand of secrets",
    "bacchetta della ragnatela": "wand of web",
    "bacchetta della paura": "wand of fear",
    "bacchetta della paralisi": "wand of paralysis",
    "bacchetta della metamorfosi": "wand of polymorph",
    "bastone del potere": "staff of power",
    "bastone dei maghi": "staff of the magi",
    "bastone della guarigione": "staff of healing",
    "bastone del fuoco": "staff of fire",
    "bastone del gelo": "staff of frost",
    "bastone dei boschi": "staff of the woodlands",
    "bastone del pitone": "staff of the python",
    "verga del patto": "rod of the pact keeper",
    "verga inamovibile": "immovable rod",
    "verga del comando": "rod of rulership",
    "verga dell'assorbimento": "rod of absorption",
    "spada vorpal": "vorpal sword",
    "spada fiammeggiante": "flame tongue",
    "lingua di fuoco": "flame tongue",
    "lama del gelo": "frost brand",
    "vendicatore sacro": "holy avenger",
    "lama del sole": "sun blade",
    "lama della fortuna": "luck blade",
    "spada danzante": "dancing sword",
    "spada del ferimento": "sword of wounding",
    "spada dell'affilatura": "sword of sharpness",
    "ladra delle nove vite": "nine lives stealer",
    "pugnale del veleno": "dagger of venom",
    "giavellotto del fulmine": "javelin of lightning",
    "arco del giuramento": "oathbow",
    "martello dei tuoni": "hammer of thunderbolts",
    "nanico lanciatore": "dwarven thrower",
    "mazza della distruzione": "mace of disruption",
    "mazza del terrore": "mace of terror",
    "mazza della demolizione": "mace of smiting",
    "scudo di mithral": "mithral armor",
    "armatura di mithral": "mithral armor",
    "armatura di adamantio": "adamantine armor",
    "armatura della resistenza": "armor of resistance",
    "armatura dell'invulnerabilità": "armor of invulnerability",
    "corazza dei nani": "dwarven plate",
    "scudo animato": "animated shield",
    "scudo attrai proiettili": "shield of missile attraction",
    "guardia degli incantesimi": "spellguard shield",
    "veste dell'arcimago": "robe of the archmagi",
    "veste degli oggetti utili": "robe of useful items",
    "veste delle stelle": "robe of stars",
    "veste degli occhi": "robe of eyes",
    "pergamena magica": "spell scroll",
    "pergamena di incantesimo": "spell scroll",
    "pergamena di volo": "spell scroll",
    "scopa volante": "broom of flying",
    "tappeto volante": "carpet of flying",
    "sfera di annientamento": "sphere of annihilation",
    "mazzo delle molte cose": "deck of many things",
    "pietra di ioun": "ioun stone",
    "occhiali della notte": "goggles of night",
    "occhi dell'aquila": "eyes of the eagle",
    "occhi di charme": "eyes of charming",
    "corda dell'intreccio": "rope of entanglement",
    "corda della scalata": "rope of climbing",
    "decanter dell'acqua infinita": "decanter of endless water",
    "collana delle palle di fuoco": "necklace of fireballs",
    "perla del potere": "pearl of power",
    "bracciali della difesa": "bracers of defense",
    "bracciali del tiro con l'arco": "bracers of archery",
    "elmo della telepatia": "helm of telepathy",
    "elmo del teletrasporto": "helm of teleportation",
    "elmo della brillantezza": "helm of brilliance",
    "sfera di cristallo": "crystal ball",
    "cubo di forza": "cube of force",
    "lanterna di rivelazione": "lantern of revealing",
    "pietre di invio": "sending stones",
    "tomo del chiaro pensiero": "tome of clear thought",
    "tomo del comando e dell'influenza": "tome of leadership and influence",
    "manuale dell'esercizio fisico": "manual of gainful exercise",
    "manuale della salute": "manual of bodily health",
    "manuale della rapidità d'azione": "manual of quickness of action",
}

# Integrazione dizionari bilingue espansi (100% Spell, Mostri, Oggetti Magici)
try:
    from common.srd_spells_complete import SPELL_IT_TO_EN_EXPANSION
    SPELL_IT_TO_EN.update({k.lower(): v.lower() for k, v in SPELL_IT_TO_EN_EXPANSION.items()})
except ImportError:
    pass

try:
    from common.srd_monsters_complete import MONSTER_IT_TO_EN_EXPANSION
    MONSTER_IT_TO_EN.update({k.lower(): v.lower() for k, v in MONSTER_IT_TO_EN_EXPANSION.items()})
except ImportError:
    pass

try:
    from common.srd_items_complete import ITEM_IT_TO_EN_EXPANSION
    ITEM_IT_TO_EN.update({k.lower(): v.lower() for k, v in ITEM_IT_TO_EN_EXPANSION.items()})
except ImportError:
    pass

# Tabella progressione privilegi, sottoclassi e slot incantesimo per tutte le 13 Classi D&D 5e (Livelli 1-20)
CLASS_PROGRESSION_TABLE = {
    "fighter": {
        "hit_die": 10,
        "subclasses": [
            "Campione (Champion - Critico Migliorato 19-20 / 18-20, Atleta Straordinario, Sopravvissuto)",
            "Maestro di Battaglia (Battle Master - Manovre Tattiche e Dadi di Superiorità d8/d10/d12)",
            "Cavaliere Mistico (Eldritch Knight - Incantesimi Arcani di Abiurazione/Invocazione e Legame con l'Arma)",
            "Samurai (XGtE - Spirito Combattivo con Vantaggio a comando e PF temporanei)",
            "Cavaliere delle Rune / Rune Knight (TCoE - Magia Runica dei Giganti e Potenza del Gigante)",
            "Cavaliere dell'Eco / Echo Knight (Manifestazione d'ombra per attacchi e scambi posizionali)"
        ],
        "features": {
            1: ["Stile di Combattimento (Fighting Style)", "Secondo Fiato (Second Wind)"],
            2: ["Azione Impetuosa (Action Surge - 1 uso)"],
            3: ["Archetipo Marziale (Martial Archetype)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Attacco Extra (Extra Attack)"],
            6: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            7: ["Privilegio Archetipo Marziale"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Indomito (Indomitable - 1 uso)"],
            10: ["Privilegio Archetipo Marziale"],
            11: ["Attacco Extra (2)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Indomito (Indomitable - 2 usi)"],
            14: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            15: ["Privilegio Archetipo Marziale"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Azione Impetuosa (2 usi)", "Indomito (3 usi)"],
            18: ["Privilegio Archetipo Marziale"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Attacco Extra (3)"],
        }
    },
    "barbarian": {
        "hit_die": 12,
        "subclasses": [
            "Cammino del Berserker (Frenesia con attacco bonus ad ogni turno e Presenza Intimidatoria)",
            "Cammino del Combattente Totemico (Spirito dell'Orso: resistenza a tutti i danni tranne psichico; Aquila; Lupo)",
            "Cammino dello Zelota (XGtE - Furia Divina +1d6+ metà livello radioso/necrotico e Ira oltre la Morte)",
            "Cammino del Guardiano Ancestrale (XGtE - Spiriti protettori che danno svantaggio e dimezzano i danni agli alleati)",
            "Cammino della Bestia (TCoE - Zanne, Artigli o Coda naturali mutaforma durante l'Ira)"
        ],
        "features": {
            1: ["Ira (Rage - 2 usi)", "Difesa Senza Armatura (Unarmored Defense)"],
            2: ["Attacco Irruente (Reckless Attack)", "Senso del Pericolo (Danger Sense)"],
            3: ["Cammino Primordiale (Primal Path - Ira 3 usi)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Attacco Extra (Extra Attack)", "Movimento Veloce (Fast Movement +10 ft)"],
            6: ["Privilegio Cammino Primordiale (Ira 4 usi)"],
            7: ["Istinto Ferino (Feral Instinct)"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Critico Brutale (Brutal Critical 1 dado)"],
            10: ["Privilegio Cammino Primordiale"],
            11: ["Ira Implacabile (Relentless Rage)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento - Ira 5 usi)"],
            13: ["Critico Brutale (Brutal Critical 2 dadi)"],
            14: ["Privilegio Cammino Primordiale"],
            15: ["Ira Persistente (Persistent Rage)"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Critico Brutale (Brutal Critical 3 dadi - Ira 6 usi)"],
            18: ["Forza Indomabile (Indomitable Might)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Campione Primordiale (Primal Champion +4 FOR, +4 COS - Ira Illimitata)"],
        }
    },
    "rogue": {
        "hit_die": 8,
        "subclasses": [
            "Furfante (Thief - Mani Rapide, Lavoro al Secondo Piano, Utilizzare Oggetti Magici)",
            "Assassino (Assassin - Assassinio: vantaggio e critico automatico sui nemici sorpresi)",
            "Mistificatore Arcano (Arcane Trickster - Mano Magica Invisibile e Incantesimi di Illusione/Ammaliamento)",
            "Spadaccino / Swashbuckler (XGtE - Audacia Elegante: Attacco Furtivo in 1v1 e +CAR all'Iniziativa)",
            "Lama Spirituale / Soulknife (TCoE - Lame Psichiche evocate a volontà e Telepatia di gruppo)"
        ],
        "features": {
            1: ["Maestria (Expertise)", "Attacco Furtivo (Sneak Attack 1d6)", "Gergo dei Ladri (Thieves' Cant)"],
            2: ["Azione Scaltra (Cunning Action)"],
            3: ["Archetipo Ladresco (Roguish Archetype)", "Attacco Furtivo (2d6)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Schivata Prodigiosa (Uncanny Dodge)", "Attacco Furtivo (3d6)"],
            6: ["Maestria (Expertise aggiuntiva)"],
            7: ["Evasione (Evasion)", "Attacco Furtivo (4d6)"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Privilegio Archetipo Ladresco", "Attacco Furtivo (5d6)"],
            10: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            11: ["Dote Affidabile (Reliable Talent)", "Attacco Furtivo (6d6)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Privilegio Archetipo Ladresco", "Attacco Furtivo (7d6)"],
            14: ["Senso Cieco (Blindsense 10 ft)"],
            15: ["Mente Sfuggente (Slippery Mind)", "Attacco Furtivo (8d6)"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Privilegio Archetipo Ladresco", "Attacco Furtivo (9d6)"],
            18: ["Elusivo (Elusive)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)", "Attacco Furtivo (10d6)"],
            20: ["Colpo di Fortuna (Stroke of Luck)"],
        }
    },
    "wizard": {
        "hit_die": 6,
        "subclasses": [
            "Scuola di Invocazione (Evocation - Plasmare Incantesimi per proteggere gli alleati e Trucchetti Potenziati)",
            "Scuola di Abiurazione (Abjuration - Egidia Arcana che assorbe danni e Controincantesimo potenziato)",
            "Scuola di Divinazione (Divination - Presagio: sostituisci qualsiasi d20 con i 2/3 dadi del destino)",
            "Scuola di Necromanzia (Necromancy - Tristo Mietitore e comando potenziato sui non morti)",
            "Cantore della Lama / Bladesinger (TCoE - Canto della Lama: +INT a CA, Concentrazione e Attacco Extra)",
            "Magia Cronurgica / Chronurgy (Controllo del tempo, +INT all'Iniziativa e ritiro d20 in reazione)"
        ],
        "features": {
            1: ["Incantesimi (Spellcasting)", "Recupero Arcano (Arcane Recovery)"],
            2: ["Tradizione Arcana (Arcane Tradition)"],
            3: ["Slot Incantesimo 2° Livello"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Slot Incantesimo 3° Livello"],
            6: ["Privilegio Tradizione Arcana"],
            7: ["Slot Incantesimo 4° Livello"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Slot Incantesimo 5° Livello"],
            10: ["Privilegio Tradizione Arcana"],
            11: ["Slot Incantesimo 6° Livello"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 7° Livello"],
            14: ["Privilegio Tradizione Arcana"],
            15: ["Slot Incantesimo 8° Livello"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Slot Incantesimo 9° Livello"],
            18: ["Padronanza degli Incantesimi (Spell Mastery)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Incantesimi Personali (Signature Spells)"],
        }
    },
    "cleric": {
        "hit_die": 8,
        "subclasses": [
            "Dominio della Vita (Life - Armature pesanti, Discepolo della Vita +2+liv alle cure, Guaritore Supremo)",
            "Dominio della Luce (Light - Bagliore Protettivo, Palla di Fuoco e Radianza dell'Alba)",
            "Dominio della Tempesta (Tempest - Armature pesanti, Armi marziali, Ira Distruttiva per massimizzare tuono/fulmine)",
            "Dominio della Guerra (War - Sacerdote di Guerra con attacco bonus e Colpo Guidato +10 al tiro per colpire)",
            "Dominio dell'Inganno (Trickery - Benedizione dell'Ingannatore e Incanalare Duplicato Illusorio)",
            "Dominio del Crepuscolo / Twilight (TCoE - Scurovisione 90m condivisa e Santuario del Crepuscolo con PF temporanei)",
            "Dominio della Pace / Peace (TCoE - Legame di Emboldening +1d4 a tiri e TS di gruppo)"
        ],
        "features": {
            1: ["Incantesimi (Spellcasting)", "Dominio Divino (Divine Domain)"],
            2: ["Incanalare Divinità (Channel Divinity 1/riposo)", "Privilegio Dominio Divino"],
            3: ["Slot Incantesimo 2° Livello"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Distruggere Non Morti (CR 1/2)"],
            6: ["Incanalare Divinità (2/riposo)", "Privilegio Dominio Divino"],
            7: ["Slot Incantesimo 4° Livello"],
            8: ["Aumento Punteggi Caratteristica (ASI)", "Distruggere Non Morti (CR 1)", "Colpo Divino / Incantesimi Potenti"],
            9: ["Slot Incantesimo 5° Livello"],
            10: ["Intervento Divino (Divine Intervention)"],
            11: ["Distruggere Non Morti (CR 2)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 7° Livello"],
            14: ["Distruggere Non Morti (CR 3)"],
            15: ["Slot Incantesimo 8° Livello"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Privilegio Dominio Divino", "Distruggere Non Morti (CR 4)"],
            18: ["Incanalare Divinità (3/riposo)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Intervento Divino Migliorato (Successo Automatico)"],
        }
    },
    "paladin": {
        "hit_die": 10,
        "subclasses": [
            "Giuramento di Devozione (Devotion - Arma Sacra +CAR al TxC, Aura di Devozione immune a Charme)",
            "Giuramento degli Antichi (Ancients - Aura di Guardia: resistenza a tutti i danni da incantesimi)",
            "Giuramento di Vendetta (Vengeance - Voto di Inimicizia: vantaggio contro il boss per 1 minuto)",
            "Giuramento di Conquista (XGtE - Aura di Conquista: blocca sul posto e danneggia i nemici spaventati)",
            "Giuramento di Redenzione (XGtE - Emissario di Pace +5 Persuasione e assorbimento danni degli alleati)"
        ],
        "features": {
            1: ["Percezione del Divino (Divine Sense)", "Imposizione delle Mani (Lay on Hands)"],
            2: ["Stile di Combattimento", "Incantesimi", "Punizione Divina (Divine Smite)"],
            3: ["Salute Divina (Divine Health)", "Giuramento Sacro (Sacred Oath)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Attacco Extra (Extra Attack)", "Slot Incantesimo 2° Livello"],
            6: ["Aura di Protezione (Aura of Protection +CAR a tutti i TS)"],
            7: ["Privilegio Giuramento Sacro"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Slot Incantesimo 3° Livello"],
            10: ["Aura di Coraggio (Aura of Courage - Immuni a Spaventato)"],
            11: ["Punizione Divina Migliorata (+1d8 radioso a ogni colpo)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 4° Livello"],
            14: ["Tocco Purificante (Cleansing Touch)"],
            15: ["Privilegio Giuramento Sacro"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Slot Incantesimo 5° Livello"],
            18: ["Miglioramento Auree (Raggio esteso a 9m/30ft)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Campione Sacro (Privilegio Apice del Giuramento)"],
        }
    },
    "bard": {
        "hit_die": 8,
        "subclasses": [
            "Collegio della Sapienza (Lore - 3 abilità extra, Parole Taglienti e Segreti Magici Aggiuntivi al 6° liv)",
            "Collegio del Valore (Valor - Armature medie, scudi, armi marziali e Attacco Extra al 6° liv)",
            "Collegio delle Spade (XGtE - Fioriture di Lama offensive/difensive e Attacco Extra)",
            "Collegio dell'Eloquenza (TCoE - Lingua d'Argento: minimo 10 sul d20 in Persuasione e Inganno)",
            "Collegio del Glamour (XGtE - Manto di Ispirazione con PF temporanei e riposizionamento immediato del party)"
        ],
        "features": {
            1: ["Incantesimi (Spellcasting)", "Ispirazione Bardica (d6)"],
            2: ["Factotum (Jack of All Trades)", "Canto di Riposo (Song of Rest d6)"],
            3: ["Collegio Bardico (Bard College)", "Maestria (Expertise in 2 abilità)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Ispirazione Bardica (d8)", "Fonte di Ispirazione (Ricarica su Riposo Breve)"],
            6: ["Controfascino (Countercharm)", "Privilegio Collegio Bardico"],
            7: ["Slot Incantesimo 4° Livello"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Canto di Riposo (d8)", "Slot Incantesimo 5° Livello"],
            10: ["Ispirazione Bardica (d10)", "Maestria (2 abilità extra)", "Segreti Magici (Magical Secrets)"],
            11: ["Slot Incantesimo 6° Livello"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Canto di Riposo (d10)", "Slot Incantesimo 7° Livello"],
            14: ["Segreti Magici Aggiuntivi", "Privilegio Collegio Bardico"],
            15: ["Ispirazione Bardica (d12)", "Slot Incantesimo 8° Livello"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Canto di Riposo (d12)", "Slot Incantesimo 9° Livello"],
            18: ["Segreti Magici Supremi"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Ispirazione Superiore (Superior Inspiration)"],
        }
    },
    "druid": {
        "hit_die": 8,
        "subclasses": [
            "Circolo della Luna (Moon - Forma Selvatica da Combattimento CR 1 fin dal 2° liv e Forme Elementali al 10°)",
            "Circolo della Terra (Land - Recupero Naturale degli slot e incantesimi sempre preparati del bioma)",
            "Circolo delle Stelle (TCoE - Mappa Stellare e Costellazioni Arcere, Calice o Drago)",
            "Circolo del Pastore / Shepherd (XGtE - Totem Spirituali ad area ed evocazioni bestiali/fatate potenziate)",
            "Circolo delle Spore (TCoE - Entità Simbiotica con PF temporanei, alone di spore necrotiche e rianimazione)"
        ],
        "features": {
            1: ["Druidico (Druidic)", "Incantesimi (Spellcasting)"],
            2: ["Forma Selvatica (Wild Shape 2/riposo)", "Circolo Druidico (Druid Circle)"],
            3: ["Slot Incantesimo 2° Livello"],
            4: ["Forma Selvatica Migliorata (Nuoto)", "Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Slot Incantesimo 3° Livello"],
            6: ["Privilegio Circolo Druidico"],
            7: ["Slot Incantesimo 4° Livello"],
            8: ["Forma Selvatica Migliorata (Volo)", "Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Slot Incantesimo 5° Livello"],
            10: ["Privilegio Circolo Druidico"],
            11: ["Slot Incantesimo 6° Livello"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 7° Livello"],
            14: ["Privilegio Circolo Druidico"],
            15: ["Slot Incantesimo 8° Livello"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Slot Incantesimo 9° Livello"],
            18: ["Corpo Senza Tempo (Timeless Body)", "Incantesimi Bestiali (Beast Spells)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Arcidruido (Archdruid - Forma Selvatica Illimitata)"],
        }
    },
    "monk": {
        "hit_die": 8,
        "subclasses": [
            "Via della Mano Aperta (Open Hand - Tecnica della Mano Aperta per atterrare/spingere e Palmo Tremante)",
            "Via dell'Ombra (Shadow - Arti dell'Ombra, Passo dell'Ombra con teletrasporto 18m e Manto d'Ombra)",
            "Via dei Quattro Elementi (Four Elements - Discipline Elementali alimentate dal Ki)",
            "Via della Misericordia / Mercy (TCoE - Mano di Guarigione e Mano del Dolore con danni necrotici e veleno)",
            "Via del Kensai (XGtE - Maestro delle armi marziali e dell'arco scelte come Armi Kensai)"
        ],
        "features": {
            1: ["Difesa Senza Armatura (10+DES+SAG)", "Arti Marziali (d4)"],
            2: ["Ki (Punti Ki = Livello)", "Raffica di Colpi, Difesa Paziente, Passo del Vento", "Movimento Senza Armatura (+10 ft)"],
            3: ["Tradizione Monastica (Monastic Tradition)", "Deviare Proiettili (Deflect Missiles)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)", "Caduta Lenta (Slow Fall)"],
            5: ["Attacco Extra (Extra Attack)", "Colpo Stordente (Stunning Strike)", "Arti Marziali (d6)"],
            6: ["Colpi Potenziati dal Ki (Magici)", "Privilegio Tradizione Monastica", "Movimento (+15 ft)"],
            7: ["Evasione (Evasion)", "Quiete della Mente (Stillness of Mind)"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Movimento Senza Armatura Migliorato (Camminare su superfici verticali e liquidi)"],
            10: ["Purezza del Corpo (Immune a malattie e veleni)", "Movimento (+20 ft)"],
            11: ["Privilegio Tradizione Monastica", "Arti Marziali (d8)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Lingua del Sole e della Luna (Comprendere e parlare ogni lingua)"],
            14: ["Anima di Diamante (Competenza in TUTTI i Tiri Salvezza + ritiro con 1 Ki)", "Movimento (+25 ft)"],
            15: ["Corpo Senza Tempo (Timeless Body)"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Privilegio Tradizione Monastica", "Arti Marziali (d10)"],
            18: ["Corpo Vuoto (Invisibilità + Resistenza a tutti i danni per 4 Ki)", "Movimento (+30 ft)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Sé Perfetto (Perfect Self - Recupera 4 Ki a inizio scontro se a 0)"],
        }
    },
    "ranger": {
        "hit_die": 10,
        "subclasses": [
            "Cacciatore (Hunter - Preda del Cacciatore: Sterminatore di Colossi +1d8, Ammazzagiganti o Spezzaorde)",
            "Signore delle Bestie (Beast Master - Compagno del Ranger e Bestia Primordiale TCoE)",
            "Cacciatore delle Tenebre / Gloom Stalker (XGtE - Agguato Terrificante al 1° round e Invisibilità alla Scurovisione)",
            "Viandante Fatato / Fey Wanderer (TCoE - +SAG alle prove di Carisma e Colpi Terribili psichici)",
            "Custode degli Sciami / Swarmkeeper (TCoE - Sciame di spiriti naturali che sposta o danneggia i bersagli)"
        ],
        "features": {
            1: ["Nemico Prescelto (Favored Enemy / Favored Foe)", "Esploratore Naturale (Natural Explorer / Deft Explorer)"],
            2: ["Stile di Combattimento (Fighting Style)", "Incantesimi (Spellcasting)"],
            3: ["Archetipo del Ranger (Ranger Archetype)", "Consapevolezza Primordiale (Primeval Awareness)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Attacco Extra (Extra Attack)", "Slot Incantesimo 2° Livello"],
            6: ["Miglioramento Nemico Prescelto ed Esploratore Naturale"],
            7: ["Privilegio Archetipo del Ranger"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)", "Passo della Terra (Land's Stride)"],
            9: ["Slot Incantesimo 3° Livello"],
            10: ["Mimetizzarsi in Piena Vista / Velo della Natura (Nature's Veil)"],
            11: ["Privilegio Archetipo del Ranger"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 4° Livello"],
            14: ["Svanire (Vanish - Nascondersi come Azione Bonus)"],
            15: ["Privilegio Archetipo del Ranger"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Slot Incantesimo 5° Livello"],
            18: ["Sensi Ferini (Feral Senses - Percepire creature invisibili entro 9m)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Sterminatore di Nemici (Foe Slayer +SAG a TxC o Danni)"],
        }
    },
    "sorcerer": {
        "hit_die": 6,
        "subclasses": [
            "Discendenza Draconica (Draconic Bloodline - Resilienza Draconica CA 13+DES e +1 PF/liv, Affinità Elementale)",
            "Magia Selvaggia (Wild Magic - Maree del Caos, Piegare la Fortuna e Tabella Magia Selvaggia)",
            "Anima Divina / Divine Soul (XGtE - Accesso all'intera lista incantesimi del Chierico e Favorito dagli Dei +2d4)",
            "Mente Aberrante / Aberrant Mind (TCoE - Incantesimi Psionici gratuiti con Punti Stregoneria e Telepatia)",
            "Anima Meccanica / Clockwork Soul (TCoE - Ripristinare l'Equilibrio per annullare vantaggio/svantaggio)"
        ],
        "features": {
            1: ["Incantesimi (Spellcasting)", "Origine Stregonesca (Sorcerous Origin)"],
            2: ["Fonte di Magia (Font of Magic - Punti Stregoneria = Livello)"],
            3: ["Metamagia (2 opzioni: Incantesimo Rapido, Raddoppiato, Accurato, Sottile, Potenziato...)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Slot Incantesimo 3° Livello", "Guida Magica (Magical Guidance)"],
            6: ["Privilegio Origine Stregonesca"],
            7: ["Slot Incantesimo 4° Livello"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Slot Incantesimo 5° Livello"],
            10: ["Metamagia Aggiuntiva (3ª opzione)"],
            11: ["Slot Incantesimo 6° Livello"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 7° Livello"],
            14: ["Privilegio Origine Stregonesca"],
            15: ["Slot Incantesimo 8° Livello"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Metamagia Aggiuntiva (4ª opzione)", "Slot Incantesimo 9° Livello"],
            18: ["Privilegio Origine Stregonesca"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Ripristino Stregonesco (Sorcerous Restoration - +4 Punti su Riposo Breve)"],
        }
    },
    "warlock": {
        "hit_die": 8,
        "subclasses": [
            "Il Signore Immondo (The Fiend - Benedizione dell'Oscuro PF temp, Fortuna dell'Oscuro +1d10 e Scagliare all'Inferno)",
            "Il Signore Fatato (The Archfey - Presenza Fatata, Fuga Velata e Difesa Seducente)",
            "Il Grande Antico (The Great Old One - Mente Risvegliata telepatica, Egida Entropica e Creare Servitore)",
            "La Lama del Patto / Hexblade (XGtE - Guerriero Hex, Armature medie/scudi, usa CAR per armi e Maledizione dell'Hexblade)",
            "Il Celestiale (XGtE - Luce Guaritrice con pool di d6 curativi a distanza e Anima Radiosa)",
            "Il Genio / The Genie (TCoE - Vaso del Genio, +Competenza ai danni e Desiderio Limitato)"
        ],
        "features": {
            1: ["Patrono Ultraterreno (Otherworldly Patron)", "Magia del Patto (Pact Magic - 1 slot 1° liv su Riposo Breve)"],
            2: ["Suppliche Occulte (Eldritch Invocations - 2 suppliche, es. Deflagrazione Agonizzante, Vista del Diavolo)"],
            3: ["Dono del Patto (Pact Boon: Patto della Catena, della Lama, del Tomo o del Talismano)", "Slot di 2° Livello"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Suppliche Occulte (3 suppliche)", "Slot di 3° Livello"],
            6: ["Privilegio Patrono Ultraterreno"],
            7: ["Suppliche Occulte (4 suppliche)", "Slot di 4° Livello"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Suppliche Occulte (5 suppliche)", "Slot di 5° Livello"],
            10: ["Privilegio Patrono Ultraterreno"],
            11: ["Arcanum Mistico (Mystic Arcanum - 6° Livello)", "3 Slot Magia del Patto"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)", "Suppliche Occulte (6 suppliche)"],
            13: ["Arcanum Mistico (7° Livello)"],
            14: ["Privilegio Patrono Ultraterreno"],
            15: ["Arcanum Mistico (8° Livello)", "Suppliche Occulte (7 suppliche)"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Arcanum Mistico (9° Livello)", "4 Slot Magia del Patto"],
            18: ["Suppliche Occulte (8 suppliche)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Maestro dell'Occulto (Eldritch Master - Ricarica tutti gli slot in 1 minuto)"],
        }
    },
    "artificer": {
        "hit_die": 8,
        "subclasses": [
            "Armaiolo / Armorer (TCoE - Armatura Arcana pesante: modello Guardiano con Guanti Tonanti o Infiltratore con Lanciatore di Fulmini)",
            "Fabbro da Battaglia / Battle Smith (TCoE - Usa INT per armi magiche, Difensore d'Acciaio fedele e Attacco Extra)",
            "Artigliere / Artillerist (TCoE - Cannone Arcano Lanciafiamme/Balista/Protettore e Arma da Fuoco Arcana +1d8)",
            "Alchimista / Alchemist (TCoE - Elisir Sperimentali giornalieri e Sapienza Alchemica +INT a cure e danni)"
        ],
        "features": {
            1: ["Riparazione Magica (Magical Tinkering)", "Incantesimi (Spellcasting fin dal 1° livello con Strumenti)"],
            2: ["Infondere Oggetti (Infuse Item - 4 infusioni note, 2 oggetti infusi)"],
            3: ["Specializzazione da Artefice (Artificer Specialist)", "Lo Strumento Giusto per il Lavoro"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Privilegio Specializzazione da Artefice (es. Attacco Extra o Arma da Fuoco Arcana)", "Slot 2° Livello"],
            6: ["Maestria negli Strumenti (Tool Expertise)", "Infusioni (6 note, 3 oggetti infusi)"],
            7: ["Lampo di Genio (Flash of Genius: +INT come Reazione a prove o TS di un alleato)"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Privilegio Specializzazione da Artefice", "Slot 3° Livello"],
            10: ["Adepto degli Oggetti Magici (Sintonizzazione con 4 oggetti)", "Infusioni (8 note, 4 oggetti)"],
            11: ["Oggetto Accumula-Incantesimi (Spell-Storing Item: 2x INT usi di un incantesimo di 1°/2° liv)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot 4° Livello"],
            14: [" Esperto degli Oggetti Magici (Sintonizzazione con 5 oggetti, ignora requisiti)", "Infusioni (10 note, 5 oggetti)"],
            15: ["Privilegio Specializzazione da Artefice"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Slot 5° Livello"],
            18: ["Maestro degli Oggetti Magici (Sintonizzazione con 6 oggetti)", "Infusioni (12 note, 6 oggetti)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Anima dell'Artificio (Soul of Artifice: +1 a tutti i TS per ogni oggetto sintonizzato, fino a +6!)"],
        }
    }
}

# Slot incantesimo per incantatori completi (Mago, Chierico, Druido, Bardo, Stregone)
FULL_CASTER_SLOTS = {
    1: {"1": 2},
    2: {"1": 3},
    3: {"1": 4, "2": 2},
    4: {"1": 4, "2": 3},
    5: {"1": 4, "2": 3, "3": 2},
    6: {"1": 4, "2": 3, "3": 3},
    7: {"1": 4, "2": 3, "3": 3, "4": 1},
    8: {"1": 4, "2": 3, "3": 3, "4": 2},
    9: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 1},
    10: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2},
    11: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1},
    12: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1},
    13: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1},
    14: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1},
    15: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1, "8": 1},
    16: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1, "8": 1},
    17: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1, "8": 1, "9": 1},
    18: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 3, "6": 1, "7": 1, "8": 1, "9": 1},
    19: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 3, "6": 2, "7": 1, "8": 1, "9": 1},
    20: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 3, "6": 2, "7": 2, "8": 1, "9": 1},
}

# Slot incantesimo per mezzi-incantatori (Paladino, Ranger, Artefice)
HALF_CASTER_SLOTS = {
    1: {},
    2: {"1": 2},
    3: {"1": 3},
    4: {"1": 3},
    5: {"1": 4, "2": 2},
    6: {"1": 4, "2": 2},
    7: {"1": 4, "2": 3},
    8: {"1": 4, "2": 3},
    9: {"1": 4, "2": 3, "3": 2},
    10: {"1": 4, "2": 3, "3": 2},
    11: {"1": 4, "2": 3, "3": 3},
    12: {"1": 4, "2": 3, "3": 3},
    13: {"1": 4, "2": 3, "3": 3, "4": 1},
    14: {"1": 4, "2": 3, "3": 3, "4": 1},
    15: {"1": 4, "2": 3, "3": 3, "4": 2},
    16: {"1": 4, "2": 3, "3": 3, "4": 2},
    17: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 1},
    18: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 1},
    19: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2},
    20: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2},
}

# Slot Magia del Patto per Warlock (si ricaricano con Riposo Breve)
WARLOCK_PACT_SLOTS = {
    1: {"1": 1},
    2: {"1": 2},
    3: {"2": 2},
    4: {"2": 2},
    5: {"3": 2},
    6: {"3": 2},
    7: {"4": 2},
    8: {"4": 2},
    9: {"5": 2},
    10: {"5": 2},
    11: {"5": 3},
    12: {"5": 3},
    13: {"5": 3},
    14: {"5": 3},
    15: {"5": 3},
    16: {"5": 3},
    17: {"5": 4},
    18: {"5": 4},
    19: {"5": 4},
    20: {"5": 4},
}

# Slot incantesimo per Artefice (arrotonda per eccesso, sblocca al 1° livello)
ARTIFICER_SLOTS = {
    1: {"1": 2},
    2: {"1": 2},
    3: {"1": 3},
    4: {"1": 3},
    5: {"1": 4, "2": 2},
    6: {"1": 4, "2": 2},
    7: {"1": 4, "2": 3},
    8: {"1": 4, "2": 3},
    9: {"1": 4, "2": 3, "3": 2},
    10: {"1": 4, "2": 3, "3": 2},
    11: {"1": 4, "2": 3, "3": 3},
    12: {"1": 4, "2": 3, "3": 3},
    13: {"1": 4, "2": 3, "3": 3, "4": 1},
    14: {"1": 4, "2": 3, "3": 3, "4": 1},
    15: {"1": 4, "2": 3, "3": 3, "4": 2},
    16: {"1": 4, "2": 3, "3": 3, "4": 2},
    17: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 1},
    18: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 1},
    19: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2},
    20: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2},
}

# Slot incantesimo per terzi-incantatori (Eldritch Knight, Arcane Trickster)
THIRD_CASTER_SLOTS = {
    1: {}, 2: {},
    3: {"1": 2}, 4: {"1": 3}, 5: {"1": 3}, 6: {"1": 3},
    7: {"1": 4, "2": 2}, 8: {"1": 4, "2": 2}, 9: {"1": 4, "2": 2},
    10: {"1": 4, "2": 3}, 11: {"1": 4, "2": 3}, 12: {"1": 4, "2": 3},
    13: {"1": 4, "2": 3, "3": 2}, 14: {"1": 4, "2": 3, "3": 2}, 15: {"1": 4, "2": 3, "3": 2},
    16: {"1": 4, "2": 3, "3": 3}, 17: {"1": 4, "2": 3, "3": 3}, 18: {"1": 4, "2": 3, "3": 3},
    19: {"1": 4, "2": 3, "3": 3, "4": 1}, 20: {"1": 4, "2": 3, "3": 3, "4": 1}
}



# Catalogo mostri iconici D&D 5e non inclusi in SRD 5.1 (Monster Manual / Guide ufficiali)
ICONIC_NON_SRD_MONSTERS: List[Dict[str, Any]] = [
    {
        "name": "Beholder",
        "size": "Large",
        "type": "aberration",
        "alignment": "lawful evil",
        "armor_class": 18,
        "hit_points": 180,
        "hit_dice": "19d10 + 76",
        "speed": "0 ft., fly 20 ft. (hover)",
        "strength": 10, "dexterity": 14, "constitution": 18,
        "intelligence": 17, "wisdom": 15, "charisma": 17,
        "challenge_rating": "13", "cr": 13.0,
        "senses": "darkvision 120 ft., passive Perception 22",
        "languages": "Deep Speech, Undercommon",
        "special_abilities": [
            {"name": "Cono Antimagia (Antimagic Cone)", "desc": "L'occhio centrale del beholder crea un cono di 45 metri di antimagia identico all'incantesimo Antimagic Field."},
            {"name": "Resistenza Leggendaria (3/Giorno)", "desc": "Se il beholder fallisce un tiro salvezza, puo scegliere di riuscirvi invece."}
        ],
        "actions": [
            {"name": "Morso (Bite)", "desc": "Attacco con arma da mischia: +5 al tiro per colpire, portata 1.5m, un bersaglio. Colpito: 14 (4d6) danni perforanti."},
            {"name": "Raggi Oculari (Eye Rays)", "desc": "Il beholder spara 3 dei seguenti raggi oculari casuali (d10): 1. Raggio di Fascino, 2. Raggio Paralizzante, 3. Raggio della Paura, 4. Raggio Rallentante, 5. Raggio Fervore/Indebolimento, 6. Raggio Telecinetico, 7. Raggio Sonno, 8. Raggio Pietrificante (CD 16 DES), 9. Raggio Disintegrante (CD 16 DES o 45 danni forza), 10. Raggio della Morte (CD 16 COS o 55 danni necrotici)."}
        ],
        "legendary_actions": [
            {"name": "Raggio Oculare", "desc": "Il beholder usa un raggio oculare a caso contro una creatura visibile entro 36 metri."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Mind Flayer",
        "size": "Medium",
        "type": "aberration",
        "alignment": "lawful evil",
        "armor_class": 15,
        "hit_points": 71,
        "hit_dice": "13d8 + 13",
        "speed": "30 ft.",
        "strength": 11, "dexterity": 12, "constitution": 12,
        "intelligence": 19, "wisdom": 17, "charisma": 17,
        "challenge_rating": "7", "cr": 7.0,
        "senses": "darkvision 120 ft., passive Perception 16",
        "languages": "Deep Speech, Undercommon, telepathy 120 ft.",
        "special_abilities": [
            {"name": "Resistenza alla Magia", "desc": "Il mind flayer ha vantaggio ai tiri salvezza contro incantesimi e altri effetti magici."},
            {"name": "Incanalare Psionico Innato", "desc": "CD incantesimi 15. A volonta: individuazione dei pensieri, levitazione. 1/giorno: dominare mostri, spostamento planare."}
        ],
        "actions": [
            {"name": "Tentacoli (Tentacles)", "desc": "Attacco con arma da mischia: +7 al tiro per colpire, portata 1.5m, una creatura. Colpito: 15 (2d10 + 4) danni psichici. Se il bersaglio e Medium o piu piccolo e afferrato (CD 15) e stordito."},
            {"name": "Estrarre Cervello (Extract Brain)", "desc": "Attacco con arma da mischia: +7 al tiro per colpire, portata 1.5m, un umanoide stordito afferrato dal mind flayer. Colpito: 55 (10d10) danni perforanti. Se riduce i PF a 0, il mind flayer uccide la creatura estraendone e mangiandone il cervello."},
            {"name": "Esplosione Psichica (Mind Blast - Ricarica 5-6)", "desc": "Emette energia psichica in un cono di 18 metri. Ogni creatura nell'area deve superare un TS su Intelligenza CD 15 o subire 22 (4d8 + 4) danni psichici ed essere stordita per 1 minuto."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Displacer Beast",
        "size": "Large",
        "type": "monstrosity",
        "alignment": "lawful evil",
        "armor_class": 13,
        "hit_points": 85,
        "hit_dice": "10d10 + 30",
        "speed": "40 ft.",
        "strength": 18, "dexterity": 15, "constitution": 16,
        "intelligence": 6, "wisdom": 12, "charisma": 8,
        "challenge_rating": "3", "cr": 3.0,
        "senses": "darkvision 60 ft., passive Perception 11",
        "languages": "",
        "special_abilities": [
            {"name": "Spostamento Illusorio (Displacement)", "desc": "La belva proietta un'illusione che la fa apparire a breve distanza dalla sua posizione reale. Gli attacchi contro di essa hanno svantaggio finche non subisce danni."},
            {"name": "Schivata Prodigiosa (Avoidance)", "desc": "Se la belva e soggetta a un effetto che permette un tiro salvezza per dimezzare il danno, non subisce danno con un successo e solo meta con un fallimento."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "La belva distorcente effettua due attacchi con i tentacoli."},
            {"name": "Tentacolo (Tentacle)", "desc": "Attacco con arma da mischia: +6 al tiro per colpire, portata 3m, un bersaglio. Colpito: 7 (1d6 + 4) danni contundenti piu 3 (1d6) danni perforanti."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Carrion Crawler",
        "size": "Large",
        "type": "monstrosity",
        "alignment": "unaligned",
        "armor_class": 13,
        "hit_points": 51,
        "hit_dice": "6d10 + 18",
        "speed": "30 ft., climb 30 ft.",
        "strength": 14, "dexterity": 13, "constitution": 16,
        "intelligence": 2, "wisdom": 13, "charisma": 5,
        "challenge_rating": "2", "cr": 2.0,
        "senses": "darkvision 60 ft., passive Perception 13",
        "languages": "",
        "special_abilities": [
            {"name": "Olfatto Acuto (Keen Smell)", "desc": "Ha vantaggio alle prove di Saggezza (Percezione) basate sull'olfatto."},
            {"name": "Movimento del Ragno (Spider Climb)", "desc": "Puo scalare superfici difficili e soffitti senza compiere prove di caratteristica."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Il vermeiena compie un attacco coi tentacoli e un attacco col morso."},
            {"name": "Tentacoli (Tentacles)", "desc": "Attacco con arma da mischia: +8 al tiro per colpire, portata 3m, una creatura. Colpito: 4 (1d4 + 2) danni da veleno e il bersaglio deve superare un TS su Costituzione CD 13 o essere avvelenato e paralizzato per 1 minuto."},
            {"name": "Morso (Bite)", "desc": "Attacco con arma da mischia: +4 al tiro per colpire, portata 1.5m, un bersaglio. Colpito: 7 (2d4 + 2) danni perforanti."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Umber Hulk",
        "size": "Large",
        "type": "monstrosity",
        "alignment": "chaotic evil",
        "armor_class": 18,
        "hit_points": 93,
        "hit_dice": "11d10 + 33",
        "speed": "30 ft., burrow 20 ft.",
        "strength": 20, "dexterity": 13, "constitution": 16,
        "intelligence": 5, "wisdom": 10, "charisma": 10,
        "challenge_rating": "5", "cr": 5.0,
        "senses": "darkvision 120 ft., tremorsense 60 ft., passive Perception 13",
        "languages": "Umber Hulk",
        "special_abilities": [
            {"name": "Sguardo Confondente (Confusing Gaze)", "desc": "Quando una creatura inizia il suo turno entro 9 metri dall'umber hulk e puo vederne gli occhi, deve superare un TS su Carisma CD 15 o subire confusione per 1 turno."},
            {"name": "Scavatore del Tunnel (Tunneler)", "desc": "Puo scavare attraverso la solida roccia lasciando un tunnel di 1.5 metri di diametro."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie tre attacchi: due con gli artigli e uno con le mandibole."},
            {"name": "Artiglio (Claw)", "desc": "Attacco con arma da mischia: +8 al tiro per colpire, portata 1.5m. Colpito: 9 (1d8 + 5) danni taglienti."},
            {"name": "Mandibole (Mandibles)", "desc": "Attacco con arma da mischia: +8 al tiro per colpire, portata 1.5m. Colpito: 14 (2d8 + 5) danni taglienti."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Yuan-ti Abomination",
        "size": "Large",
        "type": "monstrosity",
        "alignment": "neutral evil",
        "armor_class": 15,
        "hit_points": 127,
        "hit_dice": "15d10 + 45",
        "speed": "40 ft., swim 30 ft.",
        "strength": 19, "dexterity": 14, "constitution": 17,
        "intelligence": 17, "wisdom": 15, "charisma": 18,
        "challenge_rating": "7", "cr": 7.0,
        "senses": "darkvision 60 ft., passive Perception 15",
        "languages": "Abyssal, Common, Draconic",
        "special_abilities": [
            {"name": "Resistenza alla Magia", "desc": "Ha vantaggio ai tiri salvezza contro incantesimi e altri effetti magici."},
            {"name": "Forma di Serpente (Shapechanger)", "desc": "Puo trasformarsi in un serpente velenoso Medium o tornare nella sua forma originale."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie due attacchi con la scimitarra o due con l'arco lungo."},
            {"name": "Scimitarra", "desc": "Attacco con arma da mischia: +7 al tiro per colpire, portata 1.5m. Colpito: 11 (2d6 + 4) danni taglienti piu 7 (2d6) danni da veleno."},
            {"name": "Costrizione (Constrict)", "desc": "Attacco con arma da mischia: +7 al tiro per colpire, portata 3m. Colpito: 11 (2d6 + 4) danni contundenti e il bersaglio e afferrato (CD 15) e trattenuto."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Githyanki Warrior",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "lawful evil",
        "armor_class": 17,
        "hit_points": 49,
        "hit_dice": "9d8 + 9",
        "speed": "30 ft.",
        "strength": 15, "dexterity": 14, "constitution": 12,
        "intelligence": 13, "wisdom": 13, "charisma": 10,
        "challenge_rating": "3", "cr": 3.0,
        "senses": "passive Perception 11",
        "languages": "Gith",
        "special_abilities": [
            {"name": "Incanalare Psionico Innato", "desc": "CD 11. A volonta: mano magica (invisibile). 3/giorno ciascuno: salto, passo velato, colpo non armato."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie due attacchi con lo spadone argentato."},
            {"name": "Spadone d'Argento (Silver Greatsword)", "desc": "Attacco con arma da mischia: +4 al tiro per colpire, portata 1.5m. Colpito: 9 (2d6 + 2) danni taglienti piu 7 (2d6) danni psichici."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Red Slaad",
        "size": "Large",
        "type": "aberration",
        "alignment": "chaotic neutral",
        "armor_class": 14,
        "hit_points": 93,
        "hit_dice": "11d10 + 33",
        "speed": "30 ft.",
        "strength": 16, "dexterity": 12, "constitution": 16,
        "intelligence": 6, "wisdom": 6, "charisma": 7,
        "challenge_rating": "5", "cr": 5.0,
        "senses": "darkvision 60 ft., passive Perception 8",
        "languages": "Slaad, telepathy 60 ft.",
        "special_abilities": [
            {"name": "Rigenerazione", "desc": "Recupera 10 punti ferita all'inizio del suo turno se ha almeno 1 PF."},
            {"name": "Resistenza alla Magia", "desc": "Vantaggio ai TS contro magie ed effetti magici."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie tre attacchi: uno con il morso e due con gli artigli."},
            {"name": "Morso (Bite)", "desc": "Attacco da mischia: +6 al tiro per colpire, portata 1.5m. Colpito: 8 (2d4 + 3) danni perforanti."},
            {"name": "Artigli (Claws)", "desc": "Attacco da mischia: +6 al tiro per colpire, portata 1.5m. Colpito: 7 (1d8 + 3) danni taglienti e inietta un uovo di slaad se il bersaglio e umanoide (CD 14 COS)."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Death Knight",
        "size": "Medium",
        "type": "undead",
        "alignment": "chaotic evil",
        "armor_class": 20,
        "hit_points": 180,
        "hit_dice": "19d8 + 95",
        "speed": "30 ft.",
        "strength": 20, "dexterity": 11, "constitution": 20,
        "intelligence": 12, "wisdom": 16, "charisma": 18,
        "challenge_rating": "17", "cr": 17.0,
        "senses": "darkvision 120 ft., passive Perception 13",
        "languages": "Abyssal, Common",
        "special_abilities": [
            {"name": "Immunità allo Scacciare (Turn Immunity)", "desc": "Il cavaliere della morte e qualsiasi non morto entro 9 metri hanno vantaggio contro gli effetti di scacciare non morti."},
            {"name": "Resistenza Leggendaria (3/Giorno)", "desc": "Se fallisce un tiro salvezza, puo scegliere di riuscirvi invece."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie tre attacchi con la spada lunga."},
            {"name": "Spada Lunga Sacrilega", "desc": "Attacco da mischia: +11 al tiro per colpire, portata 1.5m. Colpito: 9 (1d8 + 5) danni taglienti piu 18 (4d8) danni necrotici."},
            {"name": "Sfera di Fuoco Infernale (1/Giorno)", "desc": "Scaglia una sfera magica infuocata entro 36 metri che esplode in un raggio di 6 metri: 70 (20d6) danni (meta fuoco, meta necrotico), CD 18 DES per dimezzare."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Banshee",
        "size": "Medium",
        "type": "undead",
        "alignment": "chaotic evil",
        "armor_class": 12,
        "hit_points": 58,
        "hit_dice": "13d8",
        "speed": "0 ft., fly 40 ft. (hover)",
        "strength": 1, "dexterity": 14, "constitution": 10,
        "intelligence": 12, "wisdom": 11, "charisma": 17,
        "challenge_rating": "4", "cr": 4.0,
        "senses": "darkvision 60 ft., passive Perception 10",
        "languages": "Common, Elvish",
        "special_abilities": [
            {"name": "Movimento Incorporeo", "desc": "Puo muoversi attraverso altre creature e oggetti come se fossero terreno difficile."}
        ],
        "actions": [
            {"name": "Tocco Corruttore (Corrupting Touch)", "desc": "Attacco con incantesimo da mischia: +4 al tiro per colpire, portata 1.5m. Colpito: 12 (3d6 + 2) danni necrotici."},
            {"name": "Lamento (Wail - 1/Giorno)", "desc": "Emette un lamento straziante. Tutte le creature non non-morte entro 9 metri che possono sentirla devono superare un TS su Costituzione CD 13 o cadere a 0 punti ferita (in caso di successo subiscono 10 danni psichici)."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Demilich",
        "size": "Tiny",
        "type": "undead",
        "alignment": "neutral evil",
        "armor_class": 20,
        "hit_points": 80,
        "hit_dice": "32d4",
        "speed": "0 ft., fly 30 ft. (hover)",
        "strength": 1, "dexterity": 20, "constitution": 10,
        "intelligence": 20, "wisdom": 17, "charisma": 20,
        "challenge_rating": "18", "cr": 18.0,
        "senses": "truesight 120 ft., passive Perception 23",
        "languages": "",
        "special_abilities": [
            {"name": "Resistenza Leggendaria (3/Giorno)", "desc": "Puo scegliere di superare un TS fallito."},
            {"name": "Schivata Incorporea", "desc": "Immune a gran parte dei danni contundenti, perforanti e taglienti non magici."}
        ],
        "actions": [
            {"name": "Ululo della Morte (Howl - Ricarica 5-6)", "desc": "Urla fino a 9 metri: ogni creatura deve superare un TS su Costituzione CD 15 o cadere a 0 punti ferita."},
            {"name": "Risucchio Vitale (Life Drain)", "desc": "Bersaglia fino a 3 creature entro 3m: devono superare un TS su Costituzione CD 19 o subire 21 (6d6) danni necrotici che curano il demilich."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Flameskull",
        "size": "Tiny",
        "type": "undead",
        "alignment": "neutral evil",
        "armor_class": 13,
        "hit_points": 40,
        "hit_dice": "9d4 + 18",
        "speed": "0 ft., fly 40 ft. (hover)",
        "strength": 1, "dexterity": 17, "constitution": 14,
        "intelligence": 16, "wisdom": 10, "charisma": 11,
        "challenge_rating": "4", "cr": 4.0,
        "senses": "darkvision 60 ft., passive Perception 12",
        "languages": "Common",
        "special_abilities": [
            {"name": "Illuminazione", "desc": "Emette luce intensa per 4.5 metri e luce fioca per altri 4.5 metri."},
            {"name": "Rinvigorimento (Rejuvenation)", "desc": "Se distrutto, recupera tutti i punti ferita in 1 ora a meno che i resti non siano aspersi di acqua santa o dissolti con dissolvi magie."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie due raggi di fuoco."},
            {"name": "Raggio di Fuoco (Fire Ray)", "desc": "Attacco con incantesimo a distanza: +5 al tiro per colpire, gittata 9m. Colpito: 10 (3d6) danni da fuoco."},
            {"name": "Incantesimi", "desc": "Lancia incantesimi come mago di 5° livello: Trucchetti: mano magica. 1° liv: dardo incantato, scudo. 2° liv: sfocatura, raggio rovente. 3° liv: palla di fuoco (1/giorno)."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Faerie Dragon",
        "size": "Tiny",
        "type": "dragon",
        "alignment": "chaotic good",
        "armor_class": 15,
        "hit_points": 14,
        "hit_dice": "4d4 + 4",
        "speed": "10 ft., fly 60 ft.",
        "strength": 3, "dexterity": 20, "constitution": 13,
        "intelligence": 14, "wisdom": 12, "charisma": 16,
        "challenge_rating": "2", "cr": 2.0,
        "senses": "darkvision 60 ft., passive Perception 13",
        "languages": "Draconic, Sylvan",
        "special_abilities": [
            {"name": "Invisibilità Superiore (Superior Invisibility)", "desc": "Come azione bonus, il drago puo diventare invisibile fino a quando non attacca o perde la concentrazione."},
            {"name": "Resistenza alla Magia", "desc": "Vantaggio ai TS contro magie ed effetti magici."}
        ],
        "actions": [
            {"name": "Morso (Bite)", "desc": "Attacco da mischia: +7 al tiro per colpire, portata 1.5m. Colpito: 1 danno perforante."},
            {"name": "Soffio di Euforia (Euphoria Breath - Ricarica 5-6)", "desc": "Emana un cono di 1.5 metri di gas euforizzante: CD 11 SAG o il bersaglio non puo compiere reazioni e tira un d6 per determinare il comportamento confusionario."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Kuo-toa",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "neutral evil",
        "armor_class": 13,
        "hit_points": 18,
        "hit_dice": "4d8",
        "speed": "30 ft., swim 30 ft.",
        "strength": 13, "dexterity": 10, "constitution": 11,
        "intelligence": 6, "wisdom": 10, "charisma": 8,
        "challenge_rating": "1/4", "cr": 0.25,
        "senses": "darkvision 120 ft., passive Perception 10",
        "languages": "Undercommon",
        "special_abilities": [
            {"name": "Senso dell'Altrove (Otherworldly Perception)", "desc": "Puo percepire la presenza di qualsiasi creatura invisibile o sul piano etereo entro 9 metri."},
            {"name": "Anfibio", "desc": "Puo respirare sia aria che acqua."}
        ],
        "actions": [
            {"name": "Lancia (Spear)", "desc": "Attacco da mischia o a distanza: +3 al tiro per colpire, portata 1.5m o gittata 6/18m. Colpito: 4 (1d6 + 1) danni perforanti."},
            {"name": "Scudo Appiccicoso (Sticky Shield)", "desc": "Quando un nemico fallisce un attacco da mischia contro il kuo-toa, l'arma puo rimanere incollata allo scudo (CD 11 FOR per liberarla)."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Kenku",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "chaotic neutral",
        "armor_class": 13,
        "hit_points": 13,
        "hit_dice": "3d8",
        "speed": "30 ft.",
        "strength": 10, "dexterity": 16, "constitution": 10,
        "intelligence": 11, "wisdom": 13, "charisma": 10,
        "challenge_rating": "1/4", "cr": 0.25,
        "senses": "passive Perception 13",
        "languages": "comprende Auran e Common ma parla solo tramite Mimica",
        "special_abilities": [
            {"name": "Mimica Vocale Infallibile (Mimicry)", "desc": "Puo imitare qualsiasi suono o voce umana udita con perfezione (CD 14 Saggezza Intuizione per notare l'inganno)."},
            {"name": "Falsario Esperto", "desc": "Ha vantaggio a riprodurre scritti e oggetti artigianali."}
        ],
        "actions": [
            {"name": "Spada Corta (Shortsword)", "desc": "Attacco da mischia: +5 al tiro per colpire, portata 1.5m. Colpito: 6 (1d6 + 3) danni perforanti."},
            {"name": "Arco Corto (Shortbow)", "desc": "Attacco a distanza: +5 al tiro per colpire, gittata 24/96m. Colpito: 6 (1d6 + 3) danni perforanti."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Aarakocra",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "neutral good",
        "armor_class": 12,
        "hit_points": 13,
        "hit_dice": "3d8",
        "speed": "20 ft., fly 50 ft.",
        "strength": 10, "dexterity": 14, "constitution": 10,
        "intelligence": 11, "wisdom": 12, "charisma": 11,
        "challenge_rating": "1/4", "cr": 0.25,
        "senses": "passive Perception 15",
        "languages": "Auran, Aarakocra",
        "special_abilities": [
            {"name": "Picchiata (Dive Attack)", "desc": "Se vola e picchia di almeno 9 metri in linea retta verso un bersaglio prima di colpirlo con un attacco da mischia, infligge 3 (1d6) danni extra."}
        ],
        "actions": [
            {"name": "Artiglio (Talon)", "desc": "Attacco da mischia: +4 al tiro per colpire, portata 1.5m. Colpito: 4 (1d4 + 2) danni taglienti."},
            {"name": "Giavellotto (Javelin)", "desc": "Attacco da mischia o a distanza: +4 al tiro per colpire, portata 1.5m o gittata 9/36m. Colpito: 5 (1d6 + 2) danni perforanti."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Myconid Sovereign",
        "size": "Large",
        "type": "plant",
        "alignment": "lawful neutral",
        "armor_class": 13,
        "hit_points": 60,
        "hit_dice": "8d10 + 16",
        "speed": "30 ft.",
        "strength": 12, "dexterity": 10, "constitution": 14,
        "intelligence": 13, "wisdom": 15, "charisma": 10,
        "challenge_rating": "2", "cr": 2.0,
        "senses": "darkvision 120 ft., passive Perception 12",
        "languages": "telepatia tramite Spore",
        "special_abilities": [
            {"name": "Spore di Rapporto (Rapport Spores)", "desc": "Spore entro 9 metri consentono a tutte le creature senzienti di comunicare telepaticamente per 1 ora."},
            {"name": "Spore di Animazione (Animating Spores)", "desc": "Il sovrano puo rianimare un cadavere di taglia Grande o inferiore trasformandolo in una spora servitrice fungina."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie un attacco con lo schianto o usa una delle sue spore."},
            {"name": "Schianto (Slam)", "desc": "Attacco da mischia: +3 al tiro per colpire, portata 1.5m. Colpito: 8 (3d4 + 1) danni contundenti piu 5 (2d4) danni da veleno."},
            {"name": "Spore di Allucinazione (Hallucination Spores)", "desc": "Emette spore contro una creatura entro 1.5m: CD 12 COS o la creatura e incapacitata da allucinazioni per 1 minuto."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Shadow Demon",
        "size": "Medium",
        "type": "fiend",
        "alignment": "chaotic evil",
        "armor_class": 13,
        "hit_points": 66,
        "hit_dice": "12d8 + 12",
        "speed": "30 ft., fly 30 ft.",
        "strength": 1, "dexterity": 17, "constitution": 12,
        "intelligence": 14, "wisdom": 13, "charisma": 14,
        "challenge_rating": "4", "cr": 4.0,
        "senses": "darkvision 120 ft., passive Perception 11",
        "languages": "Abyssal, telepathy 120 ft.",
        "special_abilities": [
            {"name": "Furtività nell'Ombra (Shadow Stealth)", "desc": "Finché si trova in luce fioca o oscurita, puo nascondersi come azione bonus."},
            {"name": "Sensibilità alla Luce (Light Sensitivity)", "desc": "Ha svantaggio ai tiri per colpire e alle prove di Saggezza (Percezione) in piena luce solare."}
        ],
        "actions": [
            {"name": "Artigli (Claws)", "desc": "Attacco da mischia: +5 al tiro per colpire, portata 1.5m. Colpito: 10 (2d6 + 3) danni psichici, o 17 (4d6 + 3) danni psichici se il demone aveva vantaggio."}
        ],
        "source": "Monster Manual (Offline)"
    },
    {
        "name": "Yochlol",
        "size": "Medium",
        "type": "fiend",
        "alignment": "chaotic evil",
        "armor_class": 15,
        "hit_points": 136,
        "hit_dice": "16d8 + 64",
        "speed": "30 ft., climb 30 ft.",
        "strength": 15, "dexterity": 14, "constitution": 18,
        "intelligence": 13, "wisdom": 15, "charisma": 15,
        "challenge_rating": "10", "cr": 10.0,
        "senses": "darkvision 120 ft., passive Perception 12",
        "languages": "Abyssal, Elvish, Undercommon",
        "special_abilities": [
            {"name": "Mutaforma (Shapechanger)", "desc": "Puo trasformarsi in una donna drow, in un ragno gigante o in una nube di gas velenoso."},
            {"name": "Resistenza alla Magia", "desc": "Vantaggio ai TS contro incantesimi ed effetti magici."}
        ],
        "actions": [
            {"name": "Multiattacco", "desc": "Compie due attacchi di schianto nella forma di melma."},
            {"name": "Schianto (Slam)", "desc": "Attacco da mischia: +6 al tiro per colpire, portata 1.5m. Colpito: 5 (1d6 + 2) danni contundenti piu 21 (6d6) danni da veleno."}
        ],
        "source": "Monster Manual (Offline)"
    }
]

# Catalogo incantesimi iconici D&D 5e non inclusi in SRD 5.1 (PHB / XGtE / TCoE)
ICONIC_NON_SRD_SPELLS: List[Dict[str, Any]] = [
    {
        "name": "Hex",
        "level": "1st-level", "level_int": 1,
        "school": "enchantment", "casting_time": "1 bonus action", "range": "90 feet",
        "duration": "Concentration, up to 1 hour", "concentration": "yes", "components": "V, S, M",
        "dnd_class": "Warlock",
        "desc": "Maledici una creatura che puoi vedere entro gittata. Fino al termine dell'incantesimo infliggi 1d6 danni necrotici extra al bersaglio ogni volta che lo colpisci con un attacco. Inoltre scegli una caratteristica: il bersaglio ha svantaggio alle prove di quella caratteristica.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Armor of Agathys",
        "level": "1st-level", "level_int": 1,
        "school": "abjuration", "casting_time": "1 action", "range": "Self",
        "duration": "1 hour", "concentration": "no", "components": "V, S, M",
        "dnd_class": "Warlock",
        "desc": "Una coltre spettrale di brina ti circonda donandoti 5 punti ferita temporanei. Se una creatura ti colpisce con un attacco da mischia finche hai questi PF temporanei, subisce 5 danni da freddo. A livelli superiori i PF e i danni aumentano di 5 per livello di slot.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Arms of Hadar",
        "level": "1st-level", "level_int": 1,
        "school": "conjuration", "casting_time": "1 action", "range": "Self (10-foot radius)",
        "duration": "Instantaneous", "concentration": "no", "components": "V, S",
        "dnd_class": "Warlock",
        "desc": "Invochi i tentacoli oscuri del vuoto stellare. Ogni creatura entro 3 metri da te deve superare un TS su Forza o subire 2d6 danni necrotici e non puo compiere reazioni fino al suo prossimo turno.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Hunger of Hadar",
        "level": "3rd-level", "level_int": 3,
        "school": "conjuration", "casting_time": "1 action", "range": "150 feet",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S, M",
        "dnd_class": "Warlock",
        "desc": "Apri una porta verso il freddo nero dell'oblio stellare creando una sfera di 6 metri di raggio di oscurita magica. Chi inizia il turno nell'area subisce 2d6 danni da freddo; chi termina il turno deve superare un TS su Destrezza o subire 2d6 danni da acido da tentacoli lattiginosi.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Booming Blade",
        "level": "Cantrip", "level_int": 0,
        "school": "evocation", "casting_time": "1 action", "range": "Self (5-foot radius)",
        "duration": "1 round", "concentration": "no", "components": "S, M (un'arma da mischia)",
        "dnd_class": "Artificer, Sorcerer, Warlock, Wizard",
        "desc": "Brandisci l'arma usata nel lancio ed effettui un attacco da mischia. Se colpisci, il bersaglio subisce i normali effetti dell'attacco ed e circondato da energia tonante: se si muove volontariamente prima del tuo prossimo turno, subisce immediatamente 1d8 danni da tuono (aumenta al 5°, 11° e 17° livello).",
        "source": "Tasha's Cauldron / SCAG (Offline)"
    },
    {
        "name": "Green-Flame Blade",
        "level": "Cantrip", "level_int": 0,
        "school": "evocation", "casting_time": "1 action", "range": "Self (5-foot radius)",
        "duration": "Instantaneous", "concentration": "no", "components": "S, M (un'arma da mischia)",
        "dnd_class": "Artificer, Sorcerer, Warlock, Wizard",
        "desc": "Effettui un attacco con arma da mischia. Se colpisci, fiamme verdi balzano dal bersaglio a un'altra creatura a tua scelta entro 1.5 metri infliggendole danni da fuoco pari al tuo modificatore da incantatore (i danni crescono al 5°, 11° e 17° livello).",
        "source": "Tasha's Cauldron / SCAG (Offline)"
    },
    {
        "name": "Silvery Barbs",
        "level": "1st-level", "level_int": 1,
        "school": "enchantment", "casting_time": "1 reaction", "range": "60 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V",
        "dnd_class": "Bard, Sorcerer, Wizard",
        "desc": "Come reazione a una creatura visibile entro 18 metri che ha appena avuto successo a un tiro per colpire, prova di caratteristica o tiro salvezza, la costringi a ritirare il d20 e usare il risultato piu basso. Puoi poi concedere vantaggio a un tiro a una diversa creatura entro 18 metri.",
        "source": "Strixhaven / 5e Expansion (Offline)"
    },
    {
        "name": "Chaos Bolt",
        "level": "1st-level", "level_int": 1,
        "school": "evocation", "casting_time": "1 action", "range": "120 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V, S",
        "dnd_class": "Sorcerer",
        "desc": "Scagli un dardo di energia caotica cangiante. Attacco con incantesimo a distanza: infligge 2d8 + 1d6 danni. Uno dei dadi d8 determina il tipo di danno (acido, freddo, fuoco, forza, fulmine, veleno, psichico, tuono). Se ottieni lo stesso numero sui due d8, l'energia rimbalza su un secondo bersaglio entro 9 metri!",
        "source": "Xanathar's Guide to Everything (Offline)"
    },
    {
        "name": "Chromatic Orb",
        "level": "1st-level", "level_int": 1,
        "school": "evocation", "casting_time": "1 action", "range": "90 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V, S, M (un diamante da 50 mo)",
        "dnd_class": "Sorcerer, Wizard",
        "desc": "Scagli una sfera di energia elementale di 10 cm. Scegli acido, freddo, fuoco, fulmine, veleno o tuono. Attacco con incantesimo a distanza: se colpisci, il bersaglio subisce 3d8 danni del tipo scelto.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Witch Bolt",
        "level": "1st-level", "level_int": 1,
        "school": "evocation", "casting_time": "1 action", "range": "30 feet",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S, M",
        "dnd_class": "Sorcerer, Warlock, Wizard",
        "desc": "Un raggio di fulmini azzurri crepitanti scatta verso una creatura entro gittata: attacco con incantesimo a distanza per 1d12 danni da fulmine. Nei turni successivi puoi spendere un'azione per infliggere automaticamente 1d12 danni finche mantieni la concentrazione ed entro gittata.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Cloud of Daggers",
        "level": "2nd-level", "level_int": 2,
        "school": "conjuration", "casting_time": "1 action", "range": "60 feet",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S, M",
        "dnd_class": "Bard, Sorcerer, Warlock, Wizard",
        "desc": "Riempi l'aria in un cubo di 1.5 metri con una nube di pugnali volanti magici rotanti. Qualsiasi creatura che entra nell'area o vi inizia il turno subisce 4d4 danni taglienti senza alcun tiro salvezza.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Crown of Madness",
        "level": "2nd-level", "level_int": 2,
        "school": "enchantment", "casting_time": "1 action", "range": "120 feet",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S",
        "dnd_class": "Bard, Sorcerer, Warlock, Wizard",
        "desc": "Un umanoide a tua scelta deve superare un TS su Saggezza o essere affascinato da te. Una corona di ferro contorto e fiamme spettrali appare sulla sua testa, costringendolo a compiere un attacco in mischia contro un alleato a tua scelta prima di muoversi.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Dissonant Whispers",
        "level": "1st-level", "level_int": 1,
        "school": "enchantment", "casting_time": "1 action", "range": "60 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V",
        "dnd_class": "Bard",
        "desc": "Sussurri una melodia discordante udibile solo dal bersaglio: TS su Saggezza o subisce 3d6 danni psichici e deve usare immediatamente la sua reazione per fuggire il piu lontano possibile da te.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Tasha's Mind Whip",
        "level": "2nd-level", "level_int": 2,
        "school": "enchantment", "casting_time": "1 action", "range": "90 feet",
        "duration": "1 round", "concentration": "no", "components": "V",
        "dnd_class": "Sorcerer, Wizard",
        "desc": "Proietti una frusta di energia psichica nella mente di una creatura: TS su Intelligenza o subisce 3d6 danni psichici e nel suo prossimo turno puo compiere solo un'azione, un'azione bonus o il movimento, e non puo compiere reazioni.",
        "source": "Tasha's Cauldron of Everything (Offline)"
    },
    {
        "name": "Toll the Dead",
        "level": "Cantrip", "level_int": 0,
        "school": "necromancy", "casting_time": "1 action", "range": "60 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V, S",
        "dnd_class": "Cleric, Warlock, Wizard",
        "desc": "Punti il dito verso una creatura e risuona il lugubre rintocco di una campana funebre: TS su Saggezza o subisce 1d8 danni necrotici. Se la creatura ha gia subito danni (non e a PF massimi), infligge invece 1d12 danni necrotici (scala al 5°, 11° e 17° liv).",
        "source": "Xanathar's Guide to Everything (Offline)"
    },
    {
        "name": "Mind Sliver",
        "level": "Cantrip", "level_int": 0,
        "school": "enchantment", "casting_time": "1 action", "range": "60 feet",
        "duration": "1 round", "concentration": "no", "components": "V",
        "dnd_class": "Sorcerer, Warlock, Wizard",
        "desc": "Scagli un ago di energia psionica disorientante nella mente di una creatura: TS su Intelligenza o subisce 1d6 danni psichici e sottrae 1d4 al prossimo tiro salvezza effettuato prima della fine del tuo prossimo turno.",
        "source": "Tasha's Cauldron of Everything (Offline)"
    },
    {
        "name": "Shadow Blade",
        "level": "2nd-level", "level_int": 2,
        "school": "illusion", "casting_time": "1 bonus action", "range": "Self",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S",
        "dnd_class": "Sorcerer, Warlock, Wizard",
        "desc": "Tessi fili d'ombra per creare una spada solida nella tua mano. E un'arma da mischia semplice con proprieta accurata, leggera e lancio (6/18m) che infligge 2d8 danni psichici. Ha vantaggio all'attacco se il bersaglio e in luce fioca o buio.",
        "source": "Xanathar's Guide to Everything (Offline)"
    },
    {
        "name": "Spirit Shroud",
        "level": "3rd-level", "level_int": 3,
        "school": "necromancy", "casting_time": "1 bonus action", "range": "Self",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S",
        "dnd_class": "Cleric, Paladin, Warlock, Wizard",
        "desc": "Spiriti dei defunti ti circondano in un raggio di 3 metri. I tuoi attacchi infliggono 1d8 danni extra (radiosi, necrotici o freddo a scelta) e i nemici colpiti non possono recuperare punti ferita fino all'inizio del tuo prossimo turno. La velocita dei nemici vicini e ridotta di 3m.",
        "source": "Tasha's Cauldron of Everything (Offline)"
    },
    {
        "name": "Synaptic Static",
        "level": "5th-level", "level_int": 5,
        "school": "enchantment", "casting_time": "1 action", "range": "120 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V, S",
        "dnd_class": "Bard, Sorcerer, Warlock, Wizard",
        "desc": "Fai esplodere energia psichica in una sfera di 6 metri di raggio. Ogni creatura deve superare un TS su Intelligenza o subire 8d6 danni psichici e sottrarre 1d6 a tutti i tiri per colpire, prove di caratteristica e tiri per la concentrazione per 1 minuto.",
        "source": "Xanathar's Guide to Everything (Offline)"
    },
    {
        "name": "Steel Wind Strike",
        "level": "5th-level", "level_int": 5,
        "school": "conjuration", "casting_time": "1 action", "range": "30 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "S, M (un'arma da mischia da almeno 1 mo)",
        "dnd_class": "Ranger, Wizard",
        "desc": "Svanisci in un lampo d'acciaio compiendo un attacco con incantesimo da mischia contro fino a 5 creature a tua scelta entro 9 metri. Ogni creatura colpita subisce 6d10 danni da forza. Puoi poi teletrasportarti adiacente a uno dei bersagli.",
        "source": "Xanathar's Guide to Everything (Offline)"
    },
    {
        "name": "Bigby's Hand",
        "level": "5th-level", "level_int": 5,
        "school": "evocation", "casting_time": "1 action", "range": "120 feet",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S, M",
        "dnd_class": "Artificer, Wizard",
        "desc": "Crei una mano scintillante di forza pura di taglia Grande che galleggia a tuo comando: puo colpire a pugno per 4d8 danni da forza, spingere i nemici di 5 metri piu mod. INT, afferrare creature stritolandole per 2d6+INT danni o fare da scudo protettivo interponendosi.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Destructive Wave",
        "level": "5th-level", "level_int": 5,
        "school": "evocation", "casting_time": "1 action", "range": "Self (30-foot radius)",
        "duration": "Instantaneous", "concentration": "no", "components": "V",
        "dnd_class": "Paladin",
        "desc": "Percuoti il terreno scatenando un'onda d'urto di potere divino: ogni creatura ostile entro 9 metri deve superare un TS su Costituzione o subire 5d6 danni da tuono piu 5d6 danni radiosi (o necrotici) ed essere atterrata prona.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Goodberry",
        "level": "1st-level", "level_int": 1,
        "school": "transmutation", "casting_time": "1 action", "range": "Touch",
        "duration": "24 hours", "concentration": "no", "components": "V, S, M (un ramoscello di vischio)",
        "dnd_class": "Druid, Ranger",
        "desc": "Fino a 10 bacche fresche compaiono nella tua mano infuse di magia. Una creatura puo mangiare una bacca come azione per recuperare 1 Punto Ferita, e la bacca fornisce abbastanza nutrimento per sostentare una creatura per un giorno intero.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Entangle",
        "level": "1st-level", "level_int": 1,
        "school": "conjuration", "casting_time": "1 action", "range": "90 feet",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V, S",
        "dnd_class": "Druid",
        "desc": "Erba e radici rampicanti germogliano dal suolo in un quadrato di 6 metri rendendolo terreno difficile. Ogni creatura nell'area deve superare un TS su Forza o essere trattenuta (Restrained) dalla vegetazione.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Faerie Fire",
        "level": "1st-level", "level_int": 1,
        "school": "evocation", "casting_time": "1 action", "range": "60 feet",
        "duration": "Concentration, up to 1 minute", "concentration": "yes", "components": "V",
        "dnd_class": "Artificer, Bard, Druid",
        "desc": "Tutti gli oggetti e le creature in un cubo di 6 metri vengono delineati da una luce fatata colorata se falliscono un TS su Destrezza. Non possono beneficiare dell'invisibilita e qualsiasi attacco contro di loro ha Vantaggio!",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Vicious Mockery",
        "level": "Cantrip", "level_int": 0,
        "school": "enchantment", "casting_time": "1 action", "range": "60 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V",
        "dnd_class": "Bard",
        "desc": "Scateni una serie di insulti taglienti intrisi di magia sottile: una creatura che puo sentirti deve superare un TS su Saggezza o subire 1d4 danni psichici e avere Svantaggio al prossimo tiro per colpire che effettua prima della fine del suo prossimo turno.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Eldritch Blast",
        "level": "Cantrip", "level_int": 0,
        "school": "evocation", "casting_time": "1 action", "range": "120 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V, S",
        "dnd_class": "Warlock",
        "desc": "Un raggio crepitante di energia scatta verso una creatura entro gittata. Effettua un attacco con incantesimo a distanza: se colpisci, il bersaglio subisce 1d10 danni da forza. Scaglia raggi addizionali al 5° (2 raggi), 11° (3 raggi) e 17° livello (4 raggi), ciascuno indirizzabile separatamente.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Thorn Whip",
        "level": "Cantrip", "level_int": 0,
        "school": "transmutation", "casting_time": "1 action", "range": "30 feet",
        "duration": "Instantaneous", "concentration": "no", "components": "V, S, M",
        "dnd_class": "Artificer, Druid",
        "desc": "Crei una lunga frusta di rovi spinosi: effettua un attacco con incantesimo da mischia contro una creatura entro 9 metri. Se colpisci, infliggi 1d6 danni perforanti e puoi tirare la creatura fino a 3 metri piu vicina a te se e di taglia Grande o inferiore.",
        "source": "Player's Handbook (Offline)"
    },
    {
        "name": "Shillelagh",
        "level": "Cantrip", "level_int": 0,
        "school": "transmutation", "casting_time": "1 bonus action", "range": "Touch",
        "duration": "1 minute", "concentration": "no", "components": "V, S, M (vischio e un trifoglio)",
        "dnd_class": "Druid",
        "desc": "Il legno di un bastone ferrato o di un randello che impugni viene intriso del potere della natura. Per la durata, puoi usare la tua caratteristica da incantatore (Saggezza) al posto della Forza per i tiri per colpire e per i danni con quell'arma, e il suo dado di danno diventa un d8.",
        "source": "Player's Handbook (Offline)"
    }
]


class OfflineSRD:
    _instance = None
    _spells = None
    _monsters = None
    _magic_items = None

    @classmethod
    def get_instance(cls) -> "OfflineSRD":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_magic_items(self) -> List[Dict[str, Any]]:
        if self._magic_items is None:
            path = os.path.join(SRD_DIR, "open5e_magicitems.json")
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._magic_items = json.load(f)
                except Exception as e:
                    print(f"[SRD_OFFLINE] Errore caricamento open5e_magicitems.json: {e}")
                    self._magic_items = []
            else:
                self._magic_items = []
            # Integrazione catalogo completo Artefatti ed Oggetti Magici DMG
            seen_items = {str(i.get("name", "")).strip().lower() for i in self._magic_items}
            try:
                from common.srd_items_complete import ALL_DMG_MAGIC_ITEMS
                for extra_i in ALL_DMG_MAGIC_ITEMS:
                    if str(extra_i.get("name", "")).strip().lower() not in seen_items:
                        self._magic_items.append(extra_i)
                        seen_items.add(str(extra_i.get("name", "")).strip().lower())
            except ImportError:
                pass
        return self._magic_items

    def get_magic_item(self, name_or_query: str) -> Optional[Dict[str, Any]]:
        """Cerca un oggetto magico nel database SRD offline supportando nomi in italiano o inglese."""
        if not name_or_query or not str(name_or_query).strip():
            return None
        q = str(name_or_query).strip().lower()
        # Rimuovi eventuale bonus finale generico per lookup (es. "Spada Lunga +1" -> "weapon, +1")
        target_en = ITEM_IT_TO_EN.get(q, q)
        if target_en == q:
            for k_it, k_en in ITEM_IT_TO_EN.items():
                if k_it in q:
                    target_en = k_en
                    break
            if re.search(r'\+[123]\b', q):
                num_m = re.search(r'\+([123])\b', q)
                b_num = num_m.group(1) if num_m else "1"
                if any(w in q for w in ["spada", "ascia", "arco", "pugnale", "martello", "mazza", "lancia", "balestra", "arma"]):
                    target_en = f"weapon, +{b_num}"
                elif any(w in q for w in ["armatura", "corazza", "cotta"]):
                    target_en = f"armor, +{b_num}"
                elif "scudo" in q:
                    target_en = f"shield, +{b_num}"

        items = self._load_magic_items()
        for it in items:
            it_name = str(it.get("name", "")).strip().lower()
            if it_name == q or it_name == target_en:
                return it

        best_match = None
        best_len = 999
        for it in items:
            it_name = str(it.get("name", "")).strip().lower()
            if it_name.startswith(target_en) or it_name.startswith(q):
                if len(it_name) < best_len:
                    best_len = len(it_name)
                    best_match = it
            elif (target_en in it_name or q in it_name) and best_match is None:
                best_match = it
        return best_match

    def _load_spells(self) -> List[Dict[str, Any]]:
        if self._spells is None:
            self._spells = []
            path = os.path.join(SRD_DIR, "open5e_spells.json")
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self._spells.extend(data)
                except Exception as e:
                    print(f"[SRD_OFFLINE] Errore caricamento open5e_spells.json: {e}")
            # Integrazione incantesimi iconici non-SRD e di tutte le espansioni (XGtE, TCoE, FTD, EGtW, SCC)
            seen_names = {str(s.get("name", "")).strip().lower() for s in self._spells}
            for extra_s in ICONIC_NON_SRD_SPELLS:
                if str(extra_s.get("name", "")).strip().lower() not in seen_names:
                    self._spells.append(extra_s)
                    seen_names.add(str(extra_s.get("name", "")).strip().lower())
            try:
                from common.srd_spells_complete import ALL_EXPANSION_SPELLS
                for exp_s in ALL_EXPANSION_SPELLS:
                    if str(exp_s.get("name", "")).strip().lower() not in seen_names:
                        self._spells.append(exp_s)
                        seen_names.add(str(exp_s.get("name", "")).strip().lower())
            except ImportError:
                pass
        return self._spells

    def _load_monsters(self) -> List[Dict[str, Any]]:
        if self._monsters is None:
            self._monsters = []
            for fname in ["open5e_monsters.json", "cc_monsters.json", "tob_monsters.json"]:
                path = os.path.join(SRD_DIR, fname)
                if os.path.isfile(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for m in data:
                                    if isinstance(m, dict) and "source" not in m:
                                        m["source"] = fname.replace(".json", "").upper()
                                    self._monsters.append(m)
                    except Exception as e:
                        print(f"[SRD_OFFLINE] Errore caricamento {fname}: {e}")
            # Integrazione mostri iconici e WotC copyright (Monster Manual, Volo, MToF)
            seen_monsters = {str(m.get("name", "")).strip().lower() for m in self._monsters}
            for extra_m in ICONIC_NON_SRD_MONSTERS:
                if str(extra_m.get("name", "")).strip().lower() not in seen_monsters:
                    self._monsters.append(extra_m)
                    seen_monsters.add(str(extra_m.get("name", "")).strip().lower())
            try:
                from common.srd_monsters_complete import ALL_WOTC_MONSTERS
                for wotc_m in ALL_WOTC_MONSTERS:
                    if str(wotc_m.get("name", "")).strip().lower() not in seen_monsters:
                        self._monsters.append(wotc_m)
                        seen_monsters.add(str(wotc_m.get("name", "")).strip().lower())
            except ImportError:
                pass
        return self._monsters

    def search_spells(self, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        """Cerca incantesimi nei dati SRD locali supportando query in italiano o inglese."""
        if not query or not str(query).strip():
            return []
        q = str(query).strip().lower()
        # Risolvi eventuale traduzione nome
        target_en = SPELL_IT_TO_EN.get(q, q)

        spells = self._load_spells()
        candidates = []
        for s in spells:
            name = s.get("name", "")
            name_low = name.lower()
            if target_en in name_low or q in name_low:
                level_val = s.get("level_int")
                if level_val is None:
                    try:
                        level_val = int(s.get("level", 0))
                    except (ValueError, TypeError):
                        level_val = 0
                
                # Punteggio pertinenza (0 = match esatto, 1 = prefisso, 2 = sottostringa)
                score = 0 if name_low == target_en or name_low == q else (1 if name_low.startswith(target_en) or name_low.startswith(q) else 2)

                candidates.append((score, len(name), {
                    "name": name,
                    "level": level_val,
                    "time": s.get("casting_time", "1 Azione"),
                    "range": s.get("range", "9m"),
                    "desc": s.get("desc", ""),
                    "school": s.get("school", ""),
                    "duration": s.get("duration", "Istantanea"),
                    "source": "SRD 5.1 Offline"
                }))

        candidates.sort(key=lambda c: (c[0], c[1]))
        return [c[2] for c in candidates[:max_results]]

    def search_monsters(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Cerca mostri e PNG nei dati SRD locali supportando query in italiano o inglese."""
        if not query or not str(query).strip():
            return []
        q = str(query).strip().lower()
        target_en = MONSTER_IT_TO_EN.get(q, q)

        monsters = self._load_monsters()
        candidates = []
        seen = set()

        for m in monsters:
            name = m.get("name", "")
            name_low = name.lower()
            if target_en in name_low or q in name_low:
                if name_low in seen:
                    continue
                seen.add(name_low)

                hp = m.get("hit_points", 20)
                ac = m.get("armor_class", 10)
                cr = m.get("challenge_rating", m.get("cr", "1"))
                src = m.get("source", "SRD")

                # Punteggio pertinenza (0 = match esatto, 1 = prefisso, 2 = sottostringa)
                score = 0 if name_low == target_en or name_low == q else (1 if name_low.startswith(target_en) or name_low.startswith(q) else 2)

                attrs = self.extract_attributes_from_record(m, name)

                candidates.append((score, len(name), {
                    "name": name,
                    "source": f"{src} (Offline)",
                    "summary": f"CR {cr} • CA {ac} • HP {hp}",
                    "monster_data": {
                        "name": name,
                        "hp": hp,
                        "ac": ac,
                        "dex": attrs["DES"],
                        "cr": str(cr),
                        "speed": m.get("speed", "30 ft"),
                        "attributes": attrs,
                        "actions": m.get("actions", []),
                        "special_abilities": m.get("special_abilities", []),
                        "languages": m.get("languages", ""),
                        "senses": m.get("senses", "")
                    }
                }))

        candidates.sort(key=lambda c: (c[0], c[1]))
        return [c[2] for c in candidates[:max_results]]

    def extract_attributes_from_record(self, m: Dict[str, Any], name: str = "") -> Dict[str, int]:
        return extract_and_normalize_attributes(m, name)

    def get_monster(self, name_or_query: str) -> Optional[Dict[str, Any]]:
        """Restituisce il record completo del mostro (open5e / SRD / CC / TOB) per nome o query."""
        if not name_or_query or not str(name_or_query).strip():
            return None
        raw = str(name_or_query).strip()
        # Rimuove eventuali suffissi numerici di spawning (es. "Ancient Blue Dragon 2" -> "Ancient Blue Dragon")
        clean_name = re.sub(r'\s+\d+$', '', raw).strip().lower()
        target_en = MONSTER_IT_TO_EN.get(clean_name, clean_name)

        monsters = self._load_monsters()
        
        # 1. Match esatto sul nome (o traduzione inglese)
        for m in monsters:
            m_name = m.get("name", "").strip().lower()
            if m_name == clean_name or m_name == target_en:
                return m

        # 2. Match prefisso o sottostringa
        best_match = None
        best_score = 999
        for m in monsters:
            m_name = m.get("name", "").strip().lower()
            if m_name.startswith(target_en) or m_name.startswith(clean_name):
                score = len(m_name)
                if score < best_score:
                    best_score = score
                    best_match = m
            elif (target_en in m_name or clean_name in m_name) and best_match is None:
                best_match = m

        return best_match

    def get_class_level_features(self, char_class: str, level: int, subclass: str = "") -> Dict[str, Any]:
        """Restituisce privilegi, sottoclassi e slot per il livello di qualsiasi delle 13 classi D&D 5e."""
        c_low = str(char_class).strip().lower()
        # Normalizza nome classe italiano/inglese
        for k_it, k_en in [("guerriero", "fighter"), ("barbaro", "barbarian"), ("ladro", "rogue"),
                           ("mago", "wizard"), ("chierico", "cleric"), ("paladino", "paladin"),
                           ("ranger", "ranger"), ("bardo", "bard"), ("druido", "druid"),
                           ("stregone", "sorcerer"), ("warlock", "warlock"), ("monaco", "monk"),
                           ("artefice", "artificer")]:
            if k_it in c_low or k_en in c_low:
                c_low = k_en
                break

        prog = CLASS_PROGRESSION_TABLE.get(c_low, {})
        features = prog.get("features", {}).get(level, [])
        hit_die = prog.get("hit_die", 8)

        slots = {}
        sub_low = str(subclass).lower() if subclass else ""
        if c_low in ["wizard", "cleric", "druid", "bard", "sorcerer"]:
            slots = FULL_CASTER_SLOTS.get(level, {})
        elif c_low == "artificer":
            slots = ARTIFICER_SLOTS.get(level, {})
        elif c_low in ["paladin", "ranger"]:
            slots = HALF_CASTER_SLOTS.get(level, {})
        elif c_low == "warlock":
            slots = WARLOCK_PACT_SLOTS.get(level, {})
        elif any(k in sub_low for k in ["cavaliere mistico", "eldritch knight", "mistificatore arcano", "arcane trickster"]):
            slots = THIRD_CASTER_SLOTS.get(level, {})

        return {
            "class": c_low,
            "level": level,
            "hit_die": hit_die,
            "features": features,
            "subclasses": prog.get("subclasses", []),
            "spell_slots": slots,
            "proficiency_bonus": 2 + (level - 1) // 4
        }


def extract_and_normalize_attributes(source: Any = None, monster_name: str = "") -> Dict[str, int]:
    """
    Estrae e normalizza le caratteristiche di una creatura garantendo che TUTTE le chiavi
    (FOR, DES, COS, INT, SAG, CAR e sinonimi STR, DEX, CON, WIS, CHA) siano popolate
    con i valori corretti da dati esistenti, testo OCR o fallback offline SRD.
    """
    KEY_MAP = {
        "FOR": ["FOR", "STR", "strength", "forza"],
        "DES": ["DES", "DEX", "dexterity", "destrezza"],
        "COS": ["COS", "CON", "constitution", "costituzione"],
        "INT": ["INT", "intelligence", "intelligenza"],
        "SAG": ["SAG", "WIS", "wisdom", "saggezza"],
        "CAR": ["CAR", "CHA", "charisma", "carisma"]
    }

    found_stats = {}

    # 1. Se source è un dizionario (es. monster_data, full_sheet, item_data, api response)
    if isinstance(source, dict):
        attrs_dict = source.get("attributes")
        if isinstance(attrs_dict, dict) and attrs_dict:
            for stat_code, aliases in KEY_MAP.items():
                for alias in aliases:
                    if alias in attrs_dict:
                        try:
                            val = int(attrs_dict[alias])
                            if val > 0:
                                found_stats[stat_code] = val
                                break
                        except (ValueError, TypeError):
                            pass

        for stat_code, aliases in KEY_MAP.items():
            if stat_code not in found_stats:
                for alias in aliases:
                    if alias in source:
                        try:
                            val = int(source[alias])
                            if val > 0:
                                found_stats[stat_code] = val
                                break
                        except (ValueError, TypeError):
                            pass

    # 2. Se source è una stringa (es. testo PDF / OCR del blocco statistiche)
    elif isinstance(source, str) and source.strip():
        txt = source
        patterns = {
            "FOR": r'\b(?:STR|Srn|FOR|Strength)\s*[:\s]?\s*([0-9]{1,2})',
            "DES": r'\b(?:DEX|Dex|Dzx|Drx|DEx|DES|Dexterity)\s*[:\s]?\s*([0-9]{1,2})',
            "COS": r'\b(?:CON|CoH|Cott|Cor\.r|Cor|COS|Constitution)\s*[:\s]?\s*([0-9]{1,2})',
            "INT": r'\b(?:INT|lr\.rr|lrr|lrur|ltlr|lnr|Intelligence)\s*[:\s]?\s*([0-9]{1,2})',
            "SAG": r'\b(?:WIS|Wrs|Wts|SAG|Wisdom)\s*[:\s]?\s*([0-9]{1,2})',
            "CAR": r'\b(?:CHA|Cxl|Cxr|CAR|Charisma)\s*[:\s]?\s*([0-9]{1,2})'
        }
        for stat_code, pat in patterns.items():
            m = re.search(pat, txt, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                    if 1 <= val <= 35:
                        found_stats[stat_code] = val
                except (ValueError, TypeError):
                    pass

    # Se non avevamo monster_name esplicito, prova a leggerlo da source se dizionario
    if not monster_name and isinstance(source, dict):
        monster_name = str(source.get("name") or source.get("title") or "")

    # 3. Fallback intelligente su SRD offline locale:
    # Se mancano statistiche, o sono tutte a 10 (il bug segnalato), consulta il database SRD offline
    stats_all_default_ten = len(found_stats) == 6 and all(v == 10 for v in found_stats.values())
    if (len(found_stats) < 6 or stats_all_default_ten) and monster_name:
        srd_record = OfflineSRD.get_instance().get_monster(monster_name)
        if srd_record:
            srd_stats = {
                "FOR": srd_record.get("strength"),
                "DES": srd_record.get("dexterity"),
                "COS": srd_record.get("constitution"),
                "INT": srd_record.get("intelligence"),
                "SAG": srd_record.get("wisdom"),
                "CAR": srd_record.get("charisma")
            }
            for code, s_val in srd_stats.items():
                if s_val is not None:
                    try:
                        found_stats[code] = int(s_val)
                    except (ValueError, TypeError):
                        pass

    # 4. Imposta default 10 per qualsiasi caratteristica ancora non determinata
    for code in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
        if code not in found_stats or found_stats[code] < 1:
            found_stats[code] = 10

    # 5. Restituisce il dizionario completo con sinonimi bilingue (IT/EN)
    full_attrs = {
        "FOR": found_stats["FOR"],
        "DES": found_stats["DES"],
        "COS": found_stats["COS"],
        "INT": found_stats["INT"],
        "SAG": found_stats["SAG"],
        "CAR": found_stats["CAR"],
        "STR": found_stats["FOR"],
        "DEX": found_stats["DES"],
        "CON": found_stats["COS"],
        "WIS": found_stats["SAG"],
        "CHA": found_stats["CAR"],
        "strength": found_stats["FOR"],
        "dexterity": found_stats["DES"],
        "constitution": found_stats["COS"],
        "intelligence": found_stats["INT"],
        "wisdom": found_stats["SAG"],
        "charisma": found_stats["CAR"],
    }
    return full_attrs


# Funzioni comode di modulo
def search_spells_offline(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    return OfflineSRD.get_instance().search_spells(query, max_results=max_results)

def search_monsters_offline(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    return OfflineSRD.get_instance().search_monsters(query, max_results=max_results)

def get_monster_offline(name: str) -> Optional[Dict[str, Any]]:
    return OfflineSRD.get_instance().get_monster(name)

def get_all_monsters_offline() -> List[Dict[str, Any]]:
    return list(OfflineSRD.get_instance()._load_monsters())

def get_all_spells_offline() -> List[Dict[str, Any]]:
    return list(OfflineSRD.get_instance()._load_spells())

def get_all_magic_items_offline() -> List[Dict[str, Any]]:
    return list(OfflineSRD.get_instance()._load_magic_items())

def get_magic_item_offline(name_or_query: str) -> Optional[Dict[str, Any]]:
    return OfflineSRD.get_instance().get_magic_item(name_or_query)

def get_class_level_features_offline(char_class: str, level: int, subclass: str = "") -> Dict[str, Any]:
    return OfflineSRD.get_instance().get_class_level_features(char_class, level, subclass)


# Mappe inverse Inglese -> Italiano per visualizzazione e ricerca bilingue
SPELL_EN_TO_IT: Dict[str, str] = {}
for _it_k, _en_v in SPELL_IT_TO_EN.items():
    if _en_v not in SPELL_EN_TO_IT:
        SPELL_EN_TO_IT[_en_v] = _it_k.title()

MONSTER_EN_TO_IT: Dict[str, str] = {}
for _it_k, _en_v in MONSTER_IT_TO_EN.items():
    if _en_v not in MONSTER_EN_TO_IT:
        MONSTER_EN_TO_IT[_en_v] = _it_k.title()

ITEM_EN_TO_IT: Dict[str, str] = {}
for _it_k, _en_v in ITEM_IT_TO_EN.items():
    if _en_v not in ITEM_EN_TO_IT:
        ITEM_EN_TO_IT[_en_v] = _it_k.title()


def get_italian_translation(name_en: str, category: str = "") -> Optional[str]:
    """Restituisce la traduzione italiana di un nome inglese SRD se presente nei dizionari."""
    if not name_en:
        return None
    low = str(name_en).strip().lower()
    cat_l = str(category).lower()
    if "incantesim" in cat_l or "spell" in cat_l:
        if low in SPELL_EN_TO_IT:
            return SPELL_EN_TO_IT[low]
    if "mostr" in cat_l or "png" in cat_l or "npc" in cat_l:
        if low in MONSTER_EN_TO_IT:
            return MONSTER_EN_TO_IT[low]
    if any(k in cat_l for k in ("oggett", "equip", "arm", "pozion")):
        if low in ITEM_EN_TO_IT:
            return ITEM_EN_TO_IT[low]
    return SPELL_EN_TO_IT.get(low) or ITEM_EN_TO_IT.get(low) or MONSTER_EN_TO_IT.get(low)


def get_bilingual_label(name: str, category: str = "") -> str:
    """Restituisce l'etichetta bilingue es. 'Fireball (Palla Di Fuoco)' se esiste traduzione."""
    if not name:
        return ""
    it_name = get_italian_translation(name, category)
    if it_name and it_name.lower() != name.strip().lower() and it_name.lower() not in name.strip().lower():
        return f"{name} ({it_name})"
    return name


def match_bilingual_search(item: Dict[str, Any], search_text: str, category: str = "") -> bool:
    """
    Verifica se `item` corrisponde a `search_text` cercando in:
    - nome originale (EN o IT)
    - traduzione italiana/inglese dai dizionari SRD
    - tipo, scuola, rarità, parole chiave, sommario
    """
    if not search_text:
        return True
    q = search_text.strip().lower()
    if not q:
        return True

    name = str(item.get("name") or item.get("title") or "").strip()
    name_l = name.lower()
    if q in name_l:
        return True

    # Traduzione diretta della query IT -> EN
    q_en_candidates = set()
    for d in (SPELL_IT_TO_EN, MONSTER_IT_TO_EN, ITEM_IT_TO_EN):
        if q in d:
            q_en_candidates.add(d[q])
        for k_it, v_en in d.items():
            if q in k_it:
                q_en_candidates.add(v_en)
    for q_en in q_en_candidates:
        if q_en in name_l:
            return True

    # Traduzione del nome dell'elemento EN -> IT
    it_trans = get_italian_translation(name, category)
    if it_trans and q in it_trans.lower():
        return True

    # Campi secondari (keywords, summary, type, school, rarity, category)
    kws = [str(k).lower() for k in item.get("keywords", [])]
    if any(q in k for k in kws):
        return True
    for field in ("summary", "type", "school", "rarity", "category", "manual_name"):
        val = item.get(field)
        if isinstance(val, dict):
            val = val.get("name", "")
        if val and q in str(val).lower():
            return True
    return False


# Catalogo standard 5e SRD Offline per Armi, Armature, Pozioni, Regole e Classi
STANDARD_5E_EQUIPMENT_CATALOG: List[Dict[str, Any]] = [
    # Armi da Mischia e a Distanza
    {"name": "Spada Lunga (Longsword)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "15 mo", "weight": 3.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d8 tagliente (Versatile 1d10). Peso: 3 lbs."},
    {"name": "Spadone (Greatsword)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "50 mo", "weight": 6.0, "damage": {"damage_dice": "2d6", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 2d6 tagliente (Pesante, Due Mani). Peso: 6 lbs."},
    {"name": "Spada Corta (Shortsword)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "10 mo", "weight": 2.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale da mischia. Danno: 1d6 perforante (Accurata, Leggera). Peso: 2 lbs."},
    {"name": "Stocco (Rapier)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "25 mo", "weight": 2.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale da mischia. Danno: 1d8 perforante (Accurata). Peso: 2 lbs."},
    {"name": "Scimitarra (Scimitar)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "25 mo", "weight": 3.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d6 tagliente (Accurata, Leggera). Peso: 3 lbs."},
    {"name": "Ascia Bipenne (Greataxe)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "30 mo", "weight": 7.0, "damage": {"damage_dice": "1d12", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d12 tagliente (Pesante, Due Mani). Peso: 7 lbs."},
    {"name": "Ascia da Battaglia (Battleaxe)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "10 mo", "weight": 4.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d8 tagliente (Versatile 1d10). Peso: 4 lbs."},
    {"name": "Martello da Guerra (Warhammer)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "15 mo", "weight": 2.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Contundente"}}, "desc": "Arma marziale da mischia. Danno: 1d8 contundente (Versatile 1d10). Peso: 2 lbs."},
    {"name": "Maglio (Maul)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "10 mo", "weight": 10.0, "damage": {"damage_dice": "2d6", "damage_type": {"name": "Contundente"}}, "desc": "Arma marziale da mischia. Danno: 2d6 contundente (Pesante, Due Mani). Peso: 10 lbs."},
    {"name": "Alabarda (Halberd)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "20 mo", "weight": 6.0, "damage": {"damage_dice": "1d10", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d10 tagliente (Pesante, Portata, Due Mani). Peso: 6 lbs."},
    {"name": "Pugnale (Dagger)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "2 mo", "weight": 1.0, "damage": {"damage_dice": "1d4", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice da mischia. Danno: 1d4 perforante (Accurata, Leggera, Lancio 6/18m). Peso: 1 lb."},
    {"name": "Mazza (Mace)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "5 mo", "weight": 4.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Contundente"}}, "desc": "Arma semplice da mischia. Danno: 1d6 contundente. Peso: 4 lbs."},
    {"name": "Bastone Ferrato (Quarterstaff)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "2 ma", "weight": 4.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Contundente"}}, "desc": "Arma semplice da mischia. Danno: 1d6 contundente (Versatile 1d8). Peso: 4 lbs."},
    {"name": "Lancia (Spear)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "1 mo", "weight": 3.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice da mischia. Danno: 1d6 perforante (Lancio 6/18m, Versatile 1d8). Peso: 3 lbs."},
    {"name": "Giavellotto (Javelin)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "5 ma", "weight": 2.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice da mischia/lancio. Danno: 1d6 perforante (Lancio 9/36m). Peso: 2 lbs."},
    {"name": "Arco Lungo (Longbow)", "type": "Arma a Distanza Marziale", "rarity": "Comune", "cost": "50 mo", "weight": 2.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale a distanza. Danno: 1d8 perforante (Munizioni 45/180m, Pesante, Due Mani). Peso: 2 lbs."},
    {"name": "Arco Corto (Shortbow)", "type": "Arma a Distanza Semplice", "rarity": "Comune", "cost": "25 mo", "weight": 2.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice a distanza. Danno: 1d6 perforante (Munizioni 24/96m, Due Mani). Peso: 2 lbs."},
    {"name": "Balestra Leggera (Light Crossbow)", "type": "Arma a Distanza Semplice", "rarity": "Comune", "cost": "25 mo", "weight": 5.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice a distanza. Danno: 1d8 perforante (Munizioni 24/96m, Ricarica, Due Mani). Peso: 5 lbs."},
    {"name": "Balestra Pesante (Heavy Crossbow)", "type": "Arma a Distanza Marziale", "rarity": "Comune", "cost": "50 mo", "weight": 18.0, "damage": {"damage_dice": "1d10", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale a distanza. Danno: 1d10 perforante (Munizioni 30/120m, Pesante, Ricarica, Due Mani). Peso: 18 lbs."},
    {"name": "Balestra a Mano (Hand Crossbow)", "type": "Arma a Distanza Marziale", "rarity": "Comune", "cost": "75 mo", "weight": 3.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale a distanza. Danno: 1d6 perforante (Munizioni 9/36m, Leggera, Ricarica). Peso: 3 lbs."},
    # Armature e Scudi
    {"name": "Armatura di Cuoio (Leather Armor)", "type": "Armatura Leggera", "rarity": "Comune", "cost": "10 mo", "weight": 10.0, "desc": "Armatura leggera. CA: 11 + modificatore di Destrezza."},
    {"name": "Armatura di Cuoio Borchiato (Studded Leather)", "type": "Armatura Leggera", "rarity": "Comune", "cost": "45 mo", "weight": 13.0, "desc": "Armatura leggera. CA: 12 + modificatore di Destrezza."},
    {"name": "Giaco di Maglia (Chain Shirt)", "type": "Armatura Media", "rarity": "Comune", "cost": "50 mo", "weight": 20.0, "desc": "Armatura media. CA: 13 + modificatore di Destrezza (max +2)."},
    {"name": "Cotta a Scaglie (Scale Mail)", "type": "Armatura Media", "rarity": "Comune", "cost": "50 mo", "weight": 45.0, "desc": "Armatura media. CA: 14 + modificatore di Destrezza (max +2). Svantaggio a Furtività."},
    {"name": "Mezza Armatura (Half Plate)", "type": "Armatura Media", "rarity": "Comune", "cost": "750 mo", "weight": 40.0, "desc": "Armatura media. CA: 15 + modificatore di Destrezza (max +2). Svantaggio a Furtività."},
    {"name": "Cotta di Maglia (Chain Mail)", "type": "Armatura Pesante", "rarity": "Comune", "cost": "75 mo", "weight": 55.0, "desc": "Armatura pesante. CA: 16 (Richiede FOR 13, Svantaggio a Furtività)."},
    {"name": "Armatura a Piastre (Plate Armor)", "type": "Armatura Pesante", "rarity": "Comune", "cost": "1500 mo", "weight": 65.0, "desc": "Armatura pesante. CA: 18 (Richiede FOR 15, Svantaggio a Furtività)."},
    {"name": "Scudo (Shield)", "type": "Armatura (Scudo)", "rarity": "Comune", "cost": "10 mo", "weight": 6.0, "desc": "Scudo in legno o metallo. Conferisce +2 alla Classe Armatura quando impugnato."},
    # Pozioni
    {"name": "Pozione di Guarigione (Potion of Healing)", "type": "Pozione", "rarity": "Comune", "cost": "50 mo", "weight": 0.5, "desc": "Bevi questa fiala di liquido rosso per recuperare 2d4 + 2 Punti Ferita (1 Azione)."},
    {"name": "Pozione di Guarigione Maggiore (Potion of Greater Healing)", "type": "Pozione", "rarity": "Non Comune", "cost": "150 mo", "weight": 0.5, "desc": "Recuperi 4d4 + 4 Punti Ferita quando bevi questa pozione."},
    {"name": "Pozione di Guarigione Superiore (Potion of Superior Healing)", "type": "Pozione", "rarity": "Raro", "cost": "500 mo", "weight": 0.5, "desc": "Recuperi 8d4 + 8 Punti Ferita quando bevi questa pozione."},
    {"name": "Pozione di Guarigione Suprema (Potion of Supreme Healing)", "type": "Pozione", "rarity": "Molto Raro", "cost": "1350 mo", "weight": 0.5, "desc": "Recuperi 10d4 + 20 Punti Ferita quando bevi questa pozione."},
    {"name": "Antidoto (Antitoxin)", "type": "Pozione", "rarity": "Comune", "cost": "50 mo", "weight": 0.1, "desc": "Chi beve questa fiala ottiene vantaggio ai tiri salvezza contro il veleno per 1 ora."},
    # Attrezzi ed Equipaggiamento d'Avventura
    {"name": "Zaino da Esploratore (Explorer's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "10 mo", "weight": 10.0, "desc": "Contiene sacco a pelo, acciarino, 10 torce, 10 razioni, borraccia e 15m di corda di canapa."},
    {"name": "Zaino da Scassinatore (Burglar's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "16 mo", "weight": 12.0, "desc": "Contiene piede di porco, martello, 10 chiodi, 5 candele, acciarino, 5 razioni, borraccia e 15m di corda."},
    {"name": "Zaino da Studioso (Scholar's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "40 mo", "weight": 10.0, "desc": "Contiene libro di nozioni, inchiostro, penna d'oca, 10 fogli di pergamena, razioni e borraccia."},
    {"name": "Zaino da Sacerdote (Priest's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "19 mo", "weight": 10.0, "desc": "Contiene coperta, 10 candele, acciarino, incensiere, vesti da cerimonia, 2 razioni e borraccia."},
    {"name": "Strumenti da Scasso (Thieves' Tools)", "type": "Strumenti", "rarity": "Comune", "cost": "25 mo", "weight": 1.0, "desc": "Include lima, grimaldelli, specchietto, pinze. Necessario per scassinare serrature e disattivare trappole."},
    {"name": "Borsa da Guaritore (Healer's Kit)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "5 mo", "weight": 3.0, "desc": "10 usi. Spendendo 1 uso ed 1 Azione puoi stabilizzare una creatura a 0 PF senza prova di Medicina."},
    {"name": "Corda di Canapa 15m (Hempen Rope)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "1 mo", "weight": 10.0, "desc": "Corda da 15 metri (50 ft), 2 PF, può essere spezzata con una prova di Forza CD 17."},
    {"name": "Torcia (Torch)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "1 mr", "weight": 1.0, "desc": "Brucia per 1 ora proiettando luce intensa nel raggio di 6m e luce fioca per altri 6m."},
    {"name": "Lanterna Schermabile (Hooded Lantern)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "5 mo", "weight": 2.0, "desc": "Proietta luce intensa per 9m e luce fioca per altri 9m per 6 ore con una fiaschetta d'olio."},
]



# Catalogo Talenti D&D 5e Ufficiali (PHB / XGtE / TCoE)
STANDARD_5E_FEATS_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "Maestro d'Armi Possenti (Great Weapon Master)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Quando metti a segno un colpo critico con un'arma da mischia o riduci una creatura a 0 PF, puoi compiere un attacco con arma da mischia come azione bonus.\n• Prima di effettuare un attacco da mischia con un'arma pesante con cui sei competente, puoi scegliere di subire una penalita di -5 al tiro per colpire: se l'attacco colpisce, aggiungi +10 ai danni!",
        "source": "Player's Handbook"
    },
    {
        "name": "Tiratore Scelto (Sharpshooter)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Attaccare alla gittata lunga non impone svantaggio ai tuoi tiri per colpire con armi a distanza.\n• I tuoi attacchi con armi a distanza ignorano la mezza copertura e la copertura a tre quarti.\n• Prima di compiere un attacco con un'arma a distanza con cui sei competente, puoi scegliere di subire una penalita di -5 al tiro per colpire: se colpisci, aggiungi +10 ai danni!",
        "source": "Player's Handbook"
    },
    {
        "name": "Sentinella (Sentinel)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Quando colpisci una creatura con un attacco di opportunita, la sua velocita diventa 0 per il resto del turno.\n• Le creature provocano attacchi di opportunita da te anche se compiono l'azione di Disimpegno.\n• Quando una creatura entro 1.5m da te attacca un bersaglio diverso da te, puoi usare la tua reazione per effettuare un attacco con arma da mischia contro di essa.",
        "source": "Player's Handbook"
    },
    {
        "name": "Maestro delle Armi su Asta (Polearm Master)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Quando compi l'azione di Attacco impugnando solo una picca, alabarda, bastone ferrato o lancia, puoi compiere un attacco da mischia con l'estremita opposta come azione bonus (danno 1d4 contundente).\n• Mentre impugni una picca, alabarda, bastone ferrato o lancia, le altre creature provocano un attacco di opportunita quando entrano nella tua portata.",
        "source": "Player's Handbook"
    },
    {
        "name": "Incantatore da Guerra (War Caster)",
        "category": "Talenti", "type": "Magia",
        "prerequisite": "Capacita di lanciare almeno un incantesimo",
        "desc": "• Hai vantaggio ai tiri salvezza su Costituzione che effettui per mantenere la concentrazione su un incantesimo quando subisci danni.\n• Puoi eseguire le componenti somatiche degli incantesimi anche quando impugni armi o uno scudo in entrambe le mani.\n• Quando il movimento di una creatura provoca un attacco di opportunita da te, puoi usare la tua reazione per lanciare un incantesimo contro di essa anziche compiere un attacco.",
        "source": "Player's Handbook"
    },
    {
        "name": "Fortunato (Lucky)",
        "category": "Talenti", "type": "Generale",
        "prerequisite": "Nessuno",
        "desc": "Possiedi 3 punti fortuna. Quando effettui un tiro per colpire, una prova di caratteristica o un tiro salvezza, puoi spendere 1 punto fortuna per tirare un d20 aggiuntivo e scegliere quale d20 usare. Puoi anche spendere 1 punto fortuna per far ritirare un attacco contro di te. Recuperi tutti i punti fortuna con un riposo lungo.",
        "source": "Player's Handbook"
    },
    {
        "name": "Allerta (Alert)",
        "category": "Talenti", "type": "Percezione & Tattica",
        "prerequisite": "Nessuno",
        "desc": "• Ottieni un bonus permanente di +5 all'Iniziativa.\n• Non puoi essere colto di sorpresa finche sei cosciente.\n• Le altre creature non ottengono vantaggio ai tiri per colpire contro di te per il semplice fatto di non essere viste.",
        "source": "Player's Handbook"
    },
    {
        "name": "Robusto (Tough)",
        "category": "Talenti", "type": "Sopravvivenza",
        "prerequisite": "Nessuno",
        "desc": "I tuoi punti ferita massimi aumentano di una quantita pari al doppio del tuo livello attuale quando acquisisci questo talento. Ogni volta che guadagni un livello successivo, i tuoi punti ferita massimi aumentano di 2 punti ferita addizionali.",
        "source": "Player's Handbook"
    },
    {
        "name": "Resiliente (Resilient)",
        "category": "Talenti", "type": "Miglioramento Caratteristica",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta un punteggio di caratteristica a tua scelta di 1, fino a un massimo di 20.\n• Ottieni competenza nei tiri salvezza che utilizzano la caratteristica scelta (es. Costituzione, Saggezza o Destrezza).",
        "source": "Player's Handbook"
    },
    {
        "name": "Mobile (Mobile)",
        "category": "Talenti", "type": "Movimento",
        "prerequisite": "Nessuno",
        "desc": "• La tua velocita aumenta di 3 metri (10 ft).\n• Quando compi l'azione di Scatto, il terreno difficile non ti costa movimento extra per quel turno.\n• Quando effettui un attacco da mischia contro una creatura, non provochi attacchi di opportunita da quella creatura per il resto del turno, che tu la colpisca o meno.",
        "source": "Player's Handbook"
    },
    {
        "name": "Iniziato alla Magia (Magic Initiate)",
        "category": "Talenti", "type": "Magia",
        "prerequisite": "Nessuno",
        "desc": "Scegli una classe tra bardo, chierico, druido, mago, stregone o warlock. Apprendi 2 trucchetti a tua scelta dalla lista di quella classe e 1 incantesimo di 1° livello che puoi lanciare una volta per riposo lungo senza consumare slot (usando la caratteristica da incantatore della classe scelta).",
        "source": "Player's Handbook"
    },
    {
        "name": "Incantatore Rituale (Ritual Caster)",
        "category": "Talenti", "type": "Magia",
        "prerequisite": "Intelligenza o Saggezza 13 o superiore",
        "desc": "Acquisisci un libro dei rituali e scegli una classe (es. Mago o Chierico). Il libro contiene 2 incantesimi di 1° livello con tag rituale. Puoi lanciare tali incantesimi come rituali e trascrivere qualsiasi pergamena o libro rituale che trovi se il livello dell'incantesimo non supera meta del tuo livello di personaggio.",
        "source": "Player's Handbook"
    },
    {
        "name": "Esperto di Balestre (Crossbow Expert)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Ignori la proprieta di Ricarica delle balestre con cui sei competente.\n• Essere entro 1.5 metri da una creatura ostile non impone svantaggio ai tuoi tiri per colpire a distanza.\n• Quando compi l'azione di Attacco e attacchi con un'arma a una mano, puoi usare un'azione bonus per attaccare con una balestra a mano carica che impugni.",
        "source": "Player's Handbook"
    },
    {
        "name": "Combattente con Due Armi (Dual Wielder)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Ottieni un bonus di +1 alla Classe Armatura mentre impugni un'arma da mischia separata in ciascuna mano.\n• Puoi usare il combattimento con due armi anche quando le armi da mischia a una mano che impugni non possiedono la proprieta Leggera (es. due spade lunghe o stocchi).\n• Puoi estrarre o rinfoderare due armi a una mano nello stesso tempo in cui normalmente ne estrarresti una sola.",
        "source": "Player's Handbook"
    },
    {
        "name": "Maestro degli Scudi (Shield Master)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Se compi l'azione di Attacco nel tuo turno, puoi usare un'azione bonus per spingere una creatura entro 1.5m con il tuo scudo.\n• Se non sei incapacitato, aggiungi il bonus di CA del tuo scudo a qualsiasi tiro salvezza su Destrezza contro incantesimi o effetti che bersagliano solo te.\n• Se subisci un effetto che consente un TS su Destrezza per dimezzare il danno, puoi usare la reazione per non subire alcun danno con un successo.",
        "source": "Player's Handbook"
    },
    {
        "name": "Maestro delle Armature Pesanti (Heavy Armor Master)",
        "category": "Talenti", "type": "Difesa",
        "prerequisite": "Competenza nelle armature pesanti",
        "desc": "• Aumenta il tuo punteggio di Forza di 1, fino a un massimo di 20.\n• Mentre indossi un'armatura pesante, i danni contundenti, perforanti e taglienti che subisci da attacchi non magici sono ridotti di 3.",
        "source": "Player's Handbook"
    },
    {
        "name": "Maestro delle Armature Medie (Medium Armor Master)",
        "category": "Talenti", "type": "Difesa",
        "prerequisite": "Competenza nelle armature medie",
        "desc": "• Indossare armature medie non impone svantaggio alle tue prove di Destrezza (Furtivita).\n• Quando indossi un'armatura media, puoi aggiungere fino a +3 (anziche +2) dal tuo modificatore di Destrezza alla tua Classe Armatura.",
        "source": "Player's Handbook"
    },
    {
        "name": "Guaritore (Healer)",
        "category": "Talenti", "type": "Supporto",
        "prerequisite": "Nessuno",
        "desc": "• Quando usi una borsa da guaritore per stabilizzare una creatura morente, quella creatura recupera anche 1 punto ferita.\n• Come azione, puoi spendere un uso della borsa da guaritore per curare una creatura toccata di 1d6 + 4 punti ferita, piu un numero di PF pari al numero dei suoi Dadi Vita massimi (1 volta per creatura per riposo breve o lungo).",
        "source": "Player's Handbook"
    },
    {
        "name": "Leader Ispiratore (Inspiring Leader)",
        "category": "Talenti", "type": "Supporto",
        "prerequisite": "Carisma 13 o superiore",
        "desc": "Puoi dedicare 10 minuti a tenere un discorso motivazionale per ispirare i tuoi compagni. Scegli fino a 6 creature alleate (incluso te stesso) entro 9 metri: ciascuna guadagna punti ferita temporanei pari al tuo livello + modificatore di Carisma. Ricarica con riposo breve o lungo.",
        "source": "Player's Handbook"
    },
    {
        "name": "Osservatore (Observant)",
        "category": "Talenti", "type": "Percezione & Mente",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Intelligenza o Saggezza di 1, fino a un massimo di 20.\n• Se puoi vedere la bocca di una creatura mentre parla una lingua che comprendi, puoi leggere il labiale delle sue parole.\n• Ottieni un bonus permanente di +5 ai tuoi punteggi passivi di Saggezza (Percezione) e Intelligenza (Indagare).",
        "source": "Player's Handbook"
    },
    {
        "name": "Mente Acuta (Keen Mind)",
        "category": "Talenti", "type": "Mente",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Intelligenza di 1, fino a un massimo di 20.\n• Sai sempre esattamente dove si trova il nord.\n• Conosci sempre il numero esatto di ore prima della prossima alba o tramonto.\n• Puoi ricordare con precisione millimetrica qualsiasi cosa tu abbia visto o sentito nell'ultimo mese.",
        "source": "Player's Handbook"
    },
    {
        "name": "Attore (Actor)",
        "category": "Talenti", "type": "Sociale",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Carisma di 1, fino a un massimo di 20.\n• Hai vantaggio a tutte le prove di Carisma (Inganno) e Carisma (Intrattenere) quando cerchi di farti passare per qualcun altro.\n• Puoi imitare la voce di un'altra persona o i suoni emessi da altre creature dopo averli ascoltati per almeno 1 minuto.",
        "source": "Player's Handbook"
    },
    {
        "name": "Atleta (Athlete)",
        "category": "Talenti", "type": "Movimento",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Forza o Destrezza di 1, fino a un massimo di 20.\n• Rialzarsi da prono ti costa solo 1.5 metri di movimento anziche meta del tuo totale.\n• Scalare non ti costa movimento extra.\n• Ti basta prendere una rincorsa di 1.5 metri per compiere un salto lungo o in alto con rincorsa.",
        "source": "Player's Handbook"
    },
    {
        "name": "Duellante Difensivo (Defensive Duelist)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Destrezza 13 o superiore",
        "desc": "Quando impugni un'arma accurata con cui sei competente e un'altra creatura ti colpisce con un attacco da mischia, puoi usare la tua reazione per aggiungere il tuo bonus di competenza alla tua CA per quell'attacco, facendo potenzialmente fallire il colpo.",
        "source": "Player's Handbook"
    },
    {
        "name": "Sterminatore di Maghi (Mage Slayer)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Quando una creatura entro 1.5m lancia un incantesimo, puoi usare la reazione per compiere un attacco con arma da mischia contro di essa.\n• Quando danneggi una creatura concentrata su un incantesimo, questa ha svantaggio al tiro salvezza per mantenere la concentrazione.\n• Hai vantaggio a tutti i tiri salvezza contro gli incantesimi lanciati da creature entro 1.5 metri da te.",
        "source": "Player's Handbook"
    },
    {
        "name": "Marziale Esperto (Martial Adept)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Apprendi due manovre a tua scelta dalla lista del Maestro di Battaglia del guerriero.\n• Ottieni un Dado di Superiorita d6 che puoi spendere per alimentare le tue manovre (si ricarica con un riposo breve o lungo). La CD e 8 + competenza + mod FOR o DES.",
        "source": "Player's Handbook"
    },
    {
        "name": "Cecchino Magico (Spell Sniper)",
        "category": "Talenti", "type": "Magia",
        "prerequisite": "Capacita di lanciare almeno un incantesimo",
        "desc": "• Quando lanci un incantesimo che richiede un tiro per colpire, la sua gittata e raddoppiata.\n• I tuoi attacchi con incantesimi a distanza ignorano la mezza copertura e la copertura a tre quarti.\n• Apprendi un trucchetto che richiede un tiro per colpire dalla lista di bardo, chierico, druido, mago, stregone o warlock.",
        "source": "Player's Handbook"
    },
    {
        "name": "Adepto Elementale (Elemental Adept)",
        "category": "Talenti", "type": "Magia",
        "prerequisite": "Capacita di lanciare almeno un incantesimo",
        "desc": "Scegli un tipo di danno tra acido, freddo, fuoco, fulmine o tuono. Gli incantesimi che lanci ignorano la Resistenza a quel tipo di danno. Inoltre, quando tiri i danni di quell'elemento per un incantesimo, qualsiasi 1 ottenuto su un dado di danno viene considerato come un 2.",
        "source": "Player's Handbook"
    },
    {
        "name": "Lottatore (Grappler)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Forza 13 o superiore",
        "desc": "• Hai vantaggio ai tiri per colpire contro qualsiasi creatura afferrata da te.\n• Puoi usare la tua azione per tentare di immobilizzare una creatura afferrata: effettua un'altra prova di lottare e se riesci entrambe le creature sono trattenute (Restrained) finche la lotta continua.",
        "source": "Player's Handbook"
    },
    {
        "name": "Rissaiolo da Taverna (Tavern Brawler)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Forza o Costituzione di 1, fino a un massimo di 20.\n• Sei competente nelle armi improvvisate e i tuoi colpi disarmati infliggono 1d4 danni contundenti.\n• Quando colpisci una creatura con un colpo senz'armi o un'arma improvvisata nel tuo turno, puoi usare un'azione bonus per tentare di afferrarla.",
        "source": "Player's Handbook"
    },
    {
        "name": "Predatore delle Ombre (Skulker)",
        "category": "Talenti", "type": "Furtivita",
        "prerequisite": "Destrezza 13 o superiore",
        "desc": "• Puoi tentare di nasconderti anche quando sei solo leggermente oscurato da luce fioca o nebbia.\n• Quando sei nascosto da una creatura e manchi un tiro per colpire a distanza, il colpo a vuoto non rivela la tua posizione.\n• La luce fioca non impone svantaggio alle tue prove di Saggezza (Percezione) basate sulla vista.",
        "source": "Player's Handbook"
    },
    {
        "name": "Esploratore di Dungeon (Dungeon Delver)",
        "category": "Talenti", "type": "Esplorazione",
        "prerequisite": "Nessuno",
        "desc": "• Hai vantaggio alle prove di Saggezza (Percezione) e Intelligenza (Indagare) per individuare porte segrete e trappole celate.\n• Hai vantaggio ai tiri salvezza per evitare o resistere alle trappole e resistenza ai danni inflitti da trappole.\n• Viaggiare a passo rapido non impone la penalita di -5 alla tua Percezione passiva.",
        "source": "Player's Handbook"
    },
    {
        "name": "Abile (Skilled)",
        "category": "Talenti", "type": "Competenza",
        "prerequisite": "Nessuno",
        "desc": "Ottieni competenza in una qualsiasi combinazione di 3 abilita o strumenti a tua scelta.",
        "source": "Player's Handbook"
    },
    {
        "name": "Toccato dalle Fate (Fey Touched)",
        "category": "Talenti", "type": "Magia & Origine",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Intelligenza, Saggezza o Carisma di 1, fino a un massimo di 20.\n• Apprendi l'incantesimo Passo Velato (Misty Step) e un incantesimo di 1° livello di Divinazione o Ammaliamento a scelta. Puoi lanciare ciascuno 1 volta per riposo lungo senza consumare slot, o usando gli slot della tua classe.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Toccato dall'Ombra (Shadow Touched)",
        "category": "Talenti", "type": "Magia & Origine",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Intelligenza, Saggezza o Carisma di 1, fino a un massimo di 20.\n• Apprendi l'incantesimo Invisibilita (Invisibility) e un incantesimo di 1° livello di Illusione o Necromanzia a scelta. Puoi lanciare ciascuno 1 volta per riposo lungo senza consumare slot, o usando i tuoi normali slot.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Telecinetico (Telekinetic)",
        "category": "Talenti", "type": "Psionico",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Intelligenza, Saggezza o Carisma di 1, fino a un massimo di 20.\n• Apprendi il trucchetto Mano Magica (invisibile, gittata 18 metri, senza componenti).\n• Come azione bonus, puoi spingere o tirare telepaticamente una creatura entro 9 metri di 1.5 metri (TS su Forza CD 8+comp+mod per negare se non consenziente).",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Telepatico (Telepathic)",
        "category": "Talenti", "type": "Psionico",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta il tuo punteggio di Intelligenza, Saggezza o Carisma di 1, fino a un massimo di 20.\n• Puoi parlare telepaticamente con qualsiasi creatura entro 18 metri visibile che conosca almeno un linguaggio.\n• Puoi lanciare l'incantesimo Individuazione dei Pensieri (Detect Thoughts) 1 volta per riposo lungo senza consumare slot o componenti.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Adepto Metamagico (Metamagic Adept)",
        "category": "Talenti", "type": "Magia",
        "prerequisite": "Capacita di lanciare almeno un incantesimo",
        "desc": "• Apprendi due opzioni di Metamagia a tua scelta dalla lista dello Stregone (es. Incantesimo Rapido, Raddoppiato, Sottile).\n• Ottieni 2 Punti Stregoneria che puoi usare solo per alimentare la tua Metamagia (si ricaricano con un riposo lungo).",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Iniziato al Combattimento (Fighting Initiate)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Competenza in almeno un'arma marziale",
        "desc": "Apprendi un'opzione di Stile di Combattimento a tua scelta dalla classe del guerriero (es. Tiro, Difesa, Duellare, Armi a Due Mani, Combattere con Due Armi, Intercettazione). Puoi cambiare stile ogni volta che ottieni un aumento di caratteristica.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Adepto Occulto (Eldritch Adept)",
        "category": "Talenti", "type": "Magia",
        "prerequisite": "Capacita di lanciare incantesimi o privilegio Magia del Patto",
        "desc": "Apprendi una Supplica Occulta a tua scelta dalla classe del Warlock. Se la supplica ha un prerequisito, puoi sceglierla solo se sei un warlock e soddisfi tale requisito. Puoi sostituire la supplica ogni volta che aumenti di livello.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Cuoco (Chef)",
        "category": "Talenti", "type": "Supporto",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta Costituzione o Saggezza di 1 (max 20) e ottieni competenza negli strumenti da cuoco.\n• Durante un riposo breve prepari cibo speciale: chi spende Dadi Vita recupera 1d8 PF extra.\n• Al termine di un riposo lungo cucini dolcetti pari al tuo bonus di competenza: mangiarne uno come azione bonus dona PF temporanei pari al bonus di competenza.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Frantumatore (Crusher)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta Forza o Costituzione di 1 (max 20).\n• Una volta per turno, quando colpisci una creatura con danno contundente, puoi spostarla di 1.5m in uno spazio non occupato.\n• Quando metti a segno un colpo critico che infligge danno contundente, i tiri per colpire contro quel bersaglio hanno vantaggio fino all'inizio del tuo prossimo turno.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Perforatore (Piercer)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta Forza o Destrezza di 1 (max 20).\n• Una volta per turno, quando colpisci infliggendo danno perforante, puoi ritirare uno dei dadi di danno dell'attacco e devi usare il nuovo risultato.\n• Quando metti a segno un colpo critico che infligge danno perforante, tiri un dado di danno aggiuntivo dell'arma.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Squartatore (Slasher)",
        "category": "Talenti", "type": "Combattimento",
        "prerequisite": "Nessuno",
        "desc": "• Aumenta Forza o Destrezza di 1 (max 20).\n• Una volta per turno, quando colpisci infliggendo danno tagliente, riduci la velocita del bersaglio di 3 metri fino all'inizio del tuo prossimo turno.\n• Quando metti a segno un colpo critico che infligge danno tagliente, il bersaglio subisce svantaggio a tutti i tiri per colpire per 1 turno.",
        "source": "Tasha's Cauldron of Everything"
    },
    {
        "name": "Precisione Elfica (Elven Accuracy)",
        "category": "Talenti", "type": "Raziale",
        "prerequisite": "Elfo o Mezzelfo",
        "desc": "• Aumenta Destrezza, Intelligenza, Saggezza o Carisma di 1 (max 20).\n• Ogni volta che hai vantaggio a un tiro per colpire che usa Destrezza, Intelligenza, Saggezza o Carisma, puoi ritirare uno dei dadi una volta addizionale (il cosiddetto 'super-vantaggio' a 3 dadi d20!).",
        "source": "Xanathar's Guide to Everything"
    },
    {
        "name": "Fortuna Prodiga (Bountiful Luck)",
        "category": "Talenti", "type": "Raziale",
        "prerequisite": "Halfling",
        "desc": "Quando un alleato visibile entro 9 metri ottiene un 1 naturale su un tiro per colpire, prova di caratteristica o tiro salvezza, puoi usare la tua reazione per fargli ritirare il dado! L'alleato deve usare il nuovo risultato.",
        "source": "Xanathar's Guide to Everything"
    }
]

def get_all_feats_offline() -> List[Dict[str, Any]]:
    """Restituisce il catalogo completo dei talenti 5e offline."""
    return [dict(f) for f in STANDARD_5E_FEATS_CATALOG]



# Catalogo Background D&D 5e Ufficiali (PHB / XGtE / SCAG)
STANDARD_5E_BACKGROUNDS_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "Accolito (Acolyte)",
        "category": "Background", "type": "Background",
        "skills": "Intuizione, Religione",
        "tools": "Due lingue a scelta",
        "gold": "15 mo",
        "equipment": "Simbolo sacro, libro di preghiere, 5 bastoncini d'incenso, paramenti cerimoniali, abiti comuni e 15 mo.",
        "feature_name": "Rifugio del Fedele",
        "feature_desc": "Tu e i tuoi compagni potete ricevere cure e ospitalita gratuita presso i templi e santuari della tua fede. I sacerdoti condivideranno supporto nei limiti delle loro possibilita.",
        "desc": "Hai trascorso la vita al servizio di un tempio, venerando una divinita o una filosofia divina. Sei il tramite tra il reame sacro e il mondo terreno.\n\nCompetenze: Intuizione, Religione.\nStrumenti: Due lingue a scelta.\nPrivilegio: Rifugio del Fedele (Ospitalita e cure gratuite nei templi della tua fede).",
        "source": "Player's Handbook"
    },
    {
        "name": "Criminale / Spia (Criminal / Spy)",
        "category": "Background", "type": "Background",
        "skills": "Furtivita, Inganno",
        "tools": "Strumenti da scasso, un set da gioco",
        "gold": "15 mo",
        "equipment": "Piede di porco, abiti scuri con cappuccio comuni e 15 mo.",
        "feature_name": "Contatto Criminale",
        "feature_desc": "Possiedi un contatto fidato che funge da tramite con la rete della malavita locale per scambiare messaggi segreti, ricettare merci e ottenere informazioni riservate.",
        "desc": "Hai vissuto ai margini della legge, guadagnandoti da vivere con furti, informazioni segrete o contrabbando nelle ombre della citta.\n\nCompetenze: Furtivita, Inganno.\nStrumenti: Strumenti da scasso, set da gioco.\nPrivilegio: Contatto Criminale (Accesso a ricettatori e rete di spie).",
        "source": "Player's Handbook"
    },
    {
        "name": "Eroe Popolare (Folk Hero)",
        "category": "Background", "type": "Background",
        "skills": "Addestrare Animali, Sopravvivenza",
        "tools": "Strumenti da artigiano (un tipo), veicoli terrestri",
        "gold": "10 mo",
        "equipment": "Un set di strumenti da artigiano, una pala, un vaso di ferro, abiti comuni e 10 mo.",
        "feature_name": "Ospitalita Rustica",
        "feature_desc": "I popolani e i villici ti riconoscono come uno di loro e faranno di tutto per offrirti riparo, cibo e nasconderti da nobili tiranni o guardie corrotte.",
        "desc": "Vieni dal popolo semplice e hai compiuto un gesto di straordinario coraggio che ti ha reso una leggenda tra i contadini e la gente umile.\n\nCompetenze: Addestrare Animali, Sopravvivenza.\nStrumenti: Strumenti da artigiano, veicoli terrestri.\nPrivilegio: Ospitalita Rustica (Protezione e supporto spontaneo dei contadini).",
        "source": "Player's Handbook"
    },
    {
        "name": "Nobile (Noble)",
        "category": "Background", "type": "Background",
        "skills": "Storia, Persuasione",
        "tools": "Un set da gioco, una lingua a scelta",
        "gold": "25 mo",
        "equipment": "Abiti eleganti, anello con sigillo nobiliare, pergamena con albero genealogico e borsa con 25 mo.",
        "feature_name": "Privilegio di Posizione",
        "feature_desc": "La gente ti riserva rispetto e ti riconosce come persona di alto lignaggio. Hai diritto di udienza presso nobili e governanti e vieni accolto nell'alta societa.",
        "desc": "Sei cresciuto nell'opulenza, tra privilegi, etichetta di corte e titoli nobiliari. Sei abituato al rispetto e alla responsabilita del comando.\n\nCompetenze: Storia, Persuasione.\nStrumenti: Set da gioco, una lingua.\nPrivilegio: Privilegio di Posizione (Accoglienza nobiliare e udienze ufficiali).",
        "source": "Player's Handbook"
    },
    {
        "name": "Saggio (Sage)",
        "category": "Background", "type": "Background",
        "skills": "Arcano, Storia",
        "tools": "Due lingue a scelta",
        "gold": "10 mo",
        "equipment": "Boccetta d'inchiostro nero, penna d'oca, coltellino, lettera da un collega defunto con una domanda irrisolta, abiti comuni e 10 mo.",
        "feature_name": "Ricercatore",
        "feature_desc": "Quando tenti di apprendere o ricordare un'informazione storica o arcana, se non la conosci sai esattamente da chi o in quale biblioteca o archivio trovarla.",
        "desc": "Hai dedicato anni allo studio accademico di tomi antichi, pergamene, mappe astronomiche e segreti arcani. La conoscenza e la tua guida suprema.\n\nCompetenze: Arcano, Storia.\nStrumenti: Due lingue a scelta.\nPrivilegio: Ricercatore (Localizzazione infallibile di fonti e archivi di sapere).",
        "source": "Player's Handbook"
    },
    {
        "name": "Soldato (Soldier)",
        "category": "Background", "type": "Background",
        "skills": "Atletica, Intimidire",
        "tools": "Un set da gioco, veicoli terrestri",
        "gold": "10 mo",
        "equipment": "Emblema del tuo grado militare, trofeo preso a un nemico caduto, un set di dadi d'osso, abiti comuni e 10 mo.",
        "feature_name": "Grado Militare",
        "feature_desc": "Mantieni l'autorita del tuo grado. Soldati e guardie della tua fazione riconoscono il tuo comando e puoi accedere a fortilizi e accampamenti militari.",
        "desc": "La guerra e stata la tua scuola. Hai servito in un esercito, in una guardia cittadina o in una compagnia mercenaria, imparando la dura arte della disciplina marziale.\n\nCompetenze: Atletica, Intimidire.\nStrumenti: Set da gioco, veicoli terrestri.\nPrivilegio: Grado Militare (Autorita su soldati e accesso a presidi fortificati).",
        "source": "Player's Handbook"
    },
    {
        "name": "Marinaio (Sailor)",
        "category": "Background", "type": "Background",
        "skills": "Atletica, Percezione",
        "tools": "Strumenti da navigatore, veicoli marini",
        "gold": "10 mo",
        "equipment": "Caviglia da marinaio (randello), 15 metri di corda di canapa, portafortuna marino, abiti comuni e 10 mo.",
        "feature_name": "Passaggio Navale",
        "feature_desc": "Quando hai bisogno di viaggiare via mare, puoi ottenere un passaggio gratuito per te e i tuoi compagni su una nave mercantile o da pesca in cambio di aiuto a bordo.",
        "desc": "Il mare aperto, il vento tra le vele e le stelle sono stati la tua casa per anni. Conosci l'odore della tempesta e i segreti delle coste lontane.\n\nCompetenze: Atletica, Percezione.\nStrumenti: Strumenti da navigatore, veicoli marini.\nPrivilegio: Passaggio Navale (Trasporto marittimo gratuito per il party).",
        "source": "Player's Handbook"
    },
    {
        "name": "Forestiero (Outlander)",
        "category": "Background", "type": "Background",
        "skills": "Atletica, Sopravvivenza",
        "tools": "Uno strumento musicale, una lingua a scelta",
        "gold": "10 mo",
        "equipment": "Un bastone ferrato, una trappola per animali, un corno di cervo intagliato, abiti da viaggio e 10 mo.",
        "feature_name": "Viaggiatore Nato",
        "feature_desc": "Ricordi perfettamente la conformazione del terreno, le fonti d'acqua e le stelle. Puoi reperire cibo fresco e acqua potabile per te e fino a 5 compagni ogni giorno.",
        "desc": "Sei cresciuto nelle terre selvagge: foreste sterminate, steppe sconfinate o picchi innevati. La civilta ti e estranea, ma la natura non ha segreti per te.\n\nCompetenze: Atletica, Sopravvivenza.\nStrumenti: Strumento musicale, una lingua.\nPrivilegio: Viaggiatore Nato (Orientamento infallibile e cibo per 6 persone al giorno).",
        "source": "Player's Handbook"
    },
    {
        "name": "Monello (Urchin)",
        "category": "Background", "type": "Background",
        "skills": "Furtivita, Rapidita di Mano",
        "tools": "Kit per camuffamento, strumenti da scasso",
        "gold": "10 mo",
        "equipment": "Un piccolo coltellino, una mappa della citta natia disegnata a mano, un topolino addomesticato, abiti comuni logori e 10 mo.",
        "feature_name": "I Segreti della Citta",
        "feature_desc": "Conosci i passaggi nascosti, tetti, vicoli ciechi e fogne delle citta. Quando non sei in combattimento, tu e i tuoi compagni potete muovervi tra due punti della citta a doppia velocita.",
        "desc": "Sei cresciuto da solo per le strade fangose dei bassifondi, senza famiglia ne tetto. Hai imparato a sopravvivere grazie all'astuzia, alla velocita e agli occhi aperti.\n\nCompetenze: Furtivita, Rapidita di Mano.\nStrumenti: Kit da camuffamento, strumenti da scasso.\nPrivilegio: I Segreti della Citta (Movimento urbano a velocita doppia attraverso scorciatoie).",
        "source": "Player's Handbook"
    },
    {
        "name": "Artigiano della Gilda (Guild Artisan)",
        "category": "Background", "type": "Background",
        "skills": "Intuizione, Persuasione",
        "tools": "Un set di strumenti da artigiano, una lingua a scelta",
        "gold": "15 mo",
        "equipment": "Un set di strumenti da artigiano, lettera d'introduzione della gilda, abiti da viaggio eleganti e 15 mo.",
        "feature_name": "Tessera della Gilda",
        "feature_desc": "Come membro rispettato della gilda, hai vitto e alloggio gratuito presso le sedi della corporazione in qualsiasi citta e puoi contare sul supporto legale e politico dei confratelli.",
        "desc": "Sei un maestro in un'arte o mestiere riconosciuto. Fai parte di una gilda mercantile che tutela la qualita del lavoro e garantisce rispetto nel commercio.\n\nCompetenze: Intuizione, Persuasione.\nStrumenti: Strumenti da artigiano, una lingua.\nPrivilegio: Tessera della Gilda (Alloggio e assistenza legale/politica presso le gilde).",
        "source": "Player's Handbook"
    },
    {
        "name": "Intrattenitore (Entertainer)",
        "category": "Background", "type": "Background",
        "skills": "Acrobazia, Intrattenere",
        "tools": "Kit per camuffamento, uno strumento musicale",
        "gold": "15 mo",
        "equipment": "Uno strumento musicale a scelta, costume da scena sgargiante, regalo di un ammiratore devoto e 15 mo.",
        "feature_name": "Per il Piacere del Pubblico",
        "feature_desc": "Puoi sempre trovare alloggio e cibo gratuito di buon livello in qualsiasi locanda o teatro in cambio di spettacoli serali per gli avventori.",
        "desc": "Vivi per gli applausi, le risate e le lacrime del pubblico. Attore, musico, acrobata o giullare, sai come scaldare una taverna o incantare un banchetto nobiliare.\n\nCompetenze: Acrobazia, Intrattenere.\nStrumenti: Kit da camuffamento, strumento musicale.\nPrivilegio: Per il Piacere del Pubblico (Vitto e alloggio gratis in locande in cambio di show).",
        "source": "Player's Handbook"
    },
    {
        "name": "Eremita (Hermit)",
        "category": "Background", "type": "Background",
        "skills": "Medicina, Religione",
        "tools": "Borsa da erborista, una lingua a scelta",
        "gold": "5 mo",
        "equipment": "Borsa da erborista, custodia per pergamene con note filosofiche, coperta invernale, abiti comuni e 5 mo.",
        "feature_name": "Rivelazione Segreta",
        "feature_desc": "La tua prolungata solitudine ti ha svelato una grande verita cosmica: una profezia, la posizione di un santuario dimenticato o un segreto che cambiera il destino della campagna.",
        "desc": "Hai vissuto anni in solitudine ascetica in una grotta, su una vetta o nel profondo dei boschi, cercando una verita spirituale lontana dal frastuono del mondo.\n\nCompetenze: Medicina, Religione.\nStrumenti: Borsa da erborista, una lingua.\nPrivilegio: Rivelazione Segreta (Conoscenza di una verita occulta chiave per la campagna).",
        "source": "Player's Handbook"
    },
    {
        "name": "Ciarlatano (Charlatan)",
        "category": "Background", "type": "Background",
        "skills": "Inganno, Rapidita di Mano",
        "tools": "Kit per camuffamento, kit da falsario",
        "gold": "15 mo",
        "equipment": "Abiti eleganti, kit da falsario, dadi truccati o mazzo di carte segnate, flaconi con liquido colorato (false pozioni) e 15 mo.",
        "feature_name": "Seconda Identita",
        "feature_desc": "Hai creato una seconda identita completa di documenti falsi, lettere di credito e travestimenti credibili per muoverti indisturbato tra gli insospettabili.",
        "desc": "Sai cosa vuole sentirsi dire la gente e glielo vendi con un sorriso. Maestro delle false speranze, dei giochi di prestigio e delle identita fasulle.\n\nCompetenze: Inganno, Rapidita di Mano.\nStrumenti: Kit da camuffamento, kit da falsario.\nPrivilegio: Seconda Identita (Documenti falsi perfetti e alter ego insospettabile).",
        "source": "Player's Handbook"
    },
    {
        "name": "Cavaliere (Knight)",
        "category": "Background", "type": "Background",
        "skills": "Storia, Persuasione",
        "tools": "Un set da gioco, una lingua a scelta",
        "gold": "25 mo",
        "equipment": "Abiti eleganti, anello con sigillo dell'ordine, pergamena con albero genealogico, bandiera araldica e 25 mo.",
        "feature_name": "Scudieri e Seguito",
        "feature_desc": "Hai al tuo servizio tre attendenti leali (uno scudiero, un palafreniere e un cuoco/messaggero) che si occupano del tuo equipaggiamento e del cavallo.",
        "desc": "Sei un cavaliere consacrato di un ordine d'elite o feudale, vincolato da un codice d'onore e accompagnato da un seguito di servitori fedeli.\n\nCompetenze: Storia, Persuasione.\nStrumenti: Set da gioco, una lingua.\nPrivilegio: Scudieri e Seguito (3 attendenti che ti assistono negli accampamenti).",
        "source": "Player's Handbook"
    },
    {
        "name": "Pirata (Pirate)",
        "category": "Background", "type": "Background",
        "skills": "Atletica, Percezione",
        "tools": "Strumenti da navigatore, veicoli marini",
        "gold": "10 mo",
        "equipment": "Caviglia da marinaio, 15m di corda, bandana d'abbordaggio, abiti logori e 10 mo.",
        "feature_name": "Brutta Reputazione",
        "feature_desc": "Ovunque tu vada, la gente ti teme per la tua fama di tagliagole. Puoi compiere reati minori (non pagare locande o rompere porte) senza che la gente comune osi denunciarti alle guardie.",
        "desc": "Hai navigato sotto il teschio e le ossa incrociate, depredando mercantili e seminando il panico lungo le coste del continente.\n\nCompetenze: Atletica, Percezione.\nStrumenti: Strumenti da navigatore, veicoli marini.\nPrivilegio: Brutta Reputazione (Intimidazione naturale sui popolani che evitano di denunciarti).",
        "source": "Player's Handbook"
    },
    {
        "name": "Gladiatore (Gladiator)",
        "category": "Background", "type": "Background",
        "skills": "Acrobazia, Intrattenere",
        "tools": "Kit per camuffamento, un'arma da gladiatore esotica (tridente o rete)",
        "gold": "15 mo",
        "equipment": "Arma da gladiatore esotica, trofeo di una vittoria nell'arena, abiti da parata sgargianti e 15 mo.",
        "feature_name": "Idolo delle Arene",
        "feature_desc": "Nelle citta con un'arena o un anfiteatro, vieni accolto come una celebrità sportiva: ottieni vitto, alloggio e feste offerte da ammiratori entusiasti.",
        "desc": "Hai combattuto sulla sabbia insanguinata delle arene per l'intrattenimento delle folle ruggenti, imparando a combinare scherma letale e teatralita.\n\nCompetenze: Acrobazia, Intrattenere.\nStrumenti: Kit da camuffamento, arma esotica.\nPrivilegio: Idolo delle Arene (Accoglienza da superstar e alloggi pagati dai fan).",
        "source": "Player's Handbook"
    },
    {
        "name": "Cacciatore di Taglie Urbano (Urban Bounty Hunter)",
        "category": "Background", "type": "Background",
        "skills": "Due a scelta tra Furtivita, Inganno, Intuizione, Persuasione",
        "tools": "Uno strumento da gioco e strumenti da scasso",
        "gold": "20 mo",
        "equipment": "Abiti scuri appropriati, strumenti da scasso, mandati di cattura e borsa con 20 mo.",
        "feature_name": "Orecchio a Terra",
        "feature_desc": "Nelle citta conosci informatori, ricettatori e sbirri: puoi scoprire rapidamente dove si nascondono fuggitivi o chi comanda nei bassifondi.",
        "desc": "Guadagni oro consegnando criminali e fuggiaschi alla giustizia o a chi paga di piu. I vicoli delle metropoli sono il tuo terreno di caccia.\n\nCompetenze: 2 tra Furtivita, Inganno, Intuizione, Persuasione.\nStrumenti: Set da gioco, strumenti da scasso.\nPrivilegio: Orecchio a Terra (Informazioni rapide su fuggiaschi e malavita).",
        "source": "Sword Coast Adventurer's Guide"
    },
    {
        "name": "Viaggiatore Lontano (Far Traveler)",
        "category": "Background", "type": "Background",
        "skills": "Intuizione, Percezione",
        "tools": "Uno strumento musicale o un set da gioco, una lingua a scelta",
        "gold": "10 mo",
        "equipment": "Abiti da viaggio esotici, mappa della tua terra natia, pezzo d'ambra lavorato, strumento e 10 mo.",
        "feature_name": "Tutti gli Occhi su di Te",
        "feature_desc": "Il tuo accento, abiti e modi esotici attirano curiosita e ammirazione benevola: studiosi e nobili ti invitano per ascoltare i tuoi racconti.",
        "desc": "Provieni da una terra lontanissima oltre oceani inesplorati o deserti sterminati. Tutto cio che per la gente locale e comune, per te e meraviglia.\n\nCompetenze: Intuizione, Percezione.\nStrumenti: Strumento musicale, una lingua esotica.\nPrivilegio: Tutti gli Occhi su di Te (Accesso a banchetti di nobili e studiosi curiosi).",
        "source": "Sword Coast Adventurer's Guide"
    },
    {
        "name": "Tormentato / Stregato (Haunted One)",
        "category": "Background", "type": "Background",
        "skills": "Due a scelta tra Arcano, Indagare, Religione, Sopravvivenza",
        "tools": "Due lingue a scelta (una deve essere esotica come Abissale o Infernale)",
        "gold": "0 mo (hai donato o perduto tutto)",
        "equipment": "Piede di porco, set di abiti comuni, acqua santa, specchietto d'argento, cimelio dell'orrore vissuto.",
        "feature_name": "Cuore della Tenebra",
        "feature_desc": "Chi ti guarda scorge il tormento e il coraggio nei tuoi occhi: i popolani comprendono che hai affrontato l'orrore e faranno di tutto per aiutarti a combattere i mostri.",
        "desc": "Un evento terrificante e sovrannaturale ha spezzato la tua giovinezza. Non puoi fuggire dall'orrore, ma hai giurato di affrontarlo e proteggere gli altri.\n\nCompetenze: 2 tra Arcano, Indagare, Religione, Sopravvivenza.\nStrumenti: Due lingue (di cui una esotica).\nPrivilegio: Cuore della Tenebra (I popolani si sacrificano per assistere la tua crociata).",
        "source": "Curse of Strahd / Van Richten's Guide"
    }
]

def get_all_backgrounds_offline() -> List[Dict[str, Any]]:
    """Restituisce il catalogo completo dei background 5e offline."""
    return [dict(b) for b in STANDARD_5E_BACKGROUNDS_CATALOG]


STANDARD_5E_RULES_CATALOG: List[Dict[str, Any]] = [
    {"name": "Azioni in Combattimento (Actions in Combat)", "category": "Regole", "type": "Combattimento", "desc": "Durante il tuo turno puoi muoverti e compiere un'Azione:\n• Attacco: effettua un attacco in mischia o a distanza.\n• Lanciare un Incantesimo: tempo di lancio 1 azione.\n• Scatto (Dash): raddoppia il movimento per il turno.\n• Disimpegno (Disengage): il tuo movimento non provoca attacchi d'opportunità.\n• Schivata (Dodge): gli attacchi contro di te hanno svantaggio e hai vantaggio ai TS su Destrezza.\n• Aiuto (Help): dai vantaggio alla prossima prova o attacco di un alleato.\n• Nascondersi (Hide): effettua una prova di Furtività.\n• Preparare (Ready): prepara un'azione in risposta a un innesco usando la Reazione."},
    {"name": "Condizioni D&D 5e (Conditions)", "category": "Regole", "type": "Condizioni", "desc": "Riepilogo rapido delle condizioni:\n• Accecato (Blinded): fallisce prove basate sulla vista, attacchi con svantaggio, attacchi subiti con vantaggio.\n• Affascinato (Charmed): non può attaccare chi l'ha affascinato; questi ha vantaggio alle prove sociali.\n• Afferrato (Grappled): velocità 0.\n• Avvelenato (Poisoned): svantaggio ai tiri per colpire e alle prove di caratteristica.\n• Incosciente (Unconscious): incapacitato, prono, fallisce TS FOR/DES, attacchi subiti con vantaggio e critico automatico entro 1.5m.\n• Invisibile (Invisible): attacchi con vantaggio, attacchi subiti con svantaggio.\n• Paralizzato (Paralyzed): incapacitato, fallisce TS FOR/DES, critico automatico entro 1.5m.\n• Prono (Prone): svantaggio agli attacchi; attacchi subiti entro 1.5m hanno vantaggio, oltre 1.5m svantaggio.\n• Stordito (Stunned): incapacitato, fallisce TS FOR/DES, attacchi subiti con vantaggio.\n• Trattenuto (Restrained): velocità 0, attacchi con svantaggio, attacchi subiti con vantaggio, svantaggio ai TS DES."},
    {"name": "Riposo Breve e Riposo Lungo (Resting)", "category": "Regole", "type": "Avventura", "desc": "• Riposo Breve (Short Rest): almeno 1 ora di inattività leggera. Puoi spendere Dadi Vita (fino al tuo livello) aggiungendo il modificatore di Costituzione per recuperare Punti Ferita.\n• Riposo Lungo (Long Rest): almeno 8 ore. Recuperi tutti i Punti Ferita perduti, tutti gli slot incantesimo e fino a metà dei tuoi Dadi Vita totali (minimo 1), oltre a ridurre l'Indebolimento di 1 livello."},
    {"name": "Tiri Salvezza contro Morte (Death Saving Throws)", "category": "Regole", "type": "Combattimento", "desc": "Quando inizi il turno a 0 PF, tiri 1d20 senza modificatori:\n• 10 o più: 1 Successo (al 3° successo sei stabile a 0 PF).\n• 9 o meno: 1 Fallimento (al 3° fallimento il personaggio muore).\n• 1 Naturale: conta come 2 fallimenti.\n• 20 Naturale: recuperi immediatamente 1 Punto Ferita e torni cosciente!"},
    {"name": "Copertura e Terreno Difficile (Cover & Terrain)", "category": "Regole", "type": "Combattimento", "desc": "• Mezza Copertura (Half Cover): +2 a CA e ai Tiri Salvezza su Destrezza.\n• Tre Quarti di Copertura (Three-Quarters Cover): +5 a CA e ai Tiri Salvezza su Destrezza.\n• Copertura Totale (Total Cover): non può essere bersagliato direttamente da un attacco o incantesimo.\n• Terreno Difficile: ogni metro di movimento costa 1 metro extra (2x costo movimento)."},
    {"name": "Vantaggio e Svantaggio (Advantage & Disadvantage)", "category": "Regole", "type": "Meccaniche Base", "desc": "• Vantaggio: tiri 2d20 e usi il risultato più alto.\n• Svantaggio: tiri 2d20 e usi il risultato più basso.\n• Se hai sia vantaggio che svantaggio (indipendentemente da quanti), si annullano a vicenda e tiri 1d20 normale."},
    {"name": "Concentrazione sugli Incantesimi (Concentration)", "category": "Regole", "type": "Magia", "desc": "Se subisci danni mentre mantieni la concentrazione su un incantesimo, devi superare un Tiro Salvezza su Costituzione con CD pari a 10 o alla metà del danno subito (qualunque sia più alta). Puoi concentrarti su un solo incantesimo alla volta."},
    {"name": "Tabella Veleni D&D 5e (DMG)", "category": "Regole", "type": "Guida del DM", "desc": "Veleni ufficiali del Manuale del Dungeon Master:\n• Essenza di Etere (Inalazione, CD 13 COS, Incosciente per 8 ore)\n• Fumo Assassino (Inalazione, CD 15 COS, 42 danni da veleno)\n• Radice di Malva (Contatto, CD 13 COS, 11 danni da veleno per 1 minuto)\n• Sangue di Assassino (Ingestione, CD 10 COS, 6 danni e Avvelenato 24h)\n• Siero di Verita (Ingestione, CD 11 COS, costringe a dire la verita per 1h)\n• Veleno di Drow (Ferimento, CD 13 COS, Avvelenato 1h; fallimento di 5+ = Incosciente)\n• Veleno di Serpente (Ferimento, CD 11 COS, 10 danni veleno)\n• Veleno di Scorpione Gigante (Ferimento, CD 12 COS, 22 danni veleno)\n• Succo di Torpor (Ingestione, CD 15 COS, Paralizzato per 4d6 ore)\n• Olio di Taggit (Contatto, CD 13 COS, Incosciente per 24 ore)."},
    {"name": "Tabella Trappole e Pericoli (DMG)", "category": "Regole", "type": "Guida del DM", "desc": "Linee guida DM per creare trappole in base al pericolo:\n• Trappola Moderata (Livelli 1-4): CD Rilevamento/Disarmo 10-11, TxC +3 a +5, Danni: 1d10 o 2d10.\n• Trappola Pericolosa (Livelli 5-10): CD Rilevamento/Disarmo 12-15, TxC +6 a +8, Danni: 4d10.\n• Trappola Letale (Livelli 11-16): CD Rilevamento/Disarmo 16-18, TxC +9 a +11, Danni: 10d10.\n• Trappola Mortale (Livelli 17-20): CD Rilevamento/Disarmo 19-20, TxC +12+, Danni: 18d10 o 24d10.\n• Esempi classici: Botola a Trabocchetto (10ft = 1d6 contundente), Frecce Avvelenate dal Muro, Sfera Rotolante di Pietra (CD 15 DES o 10d10), Pozza d'Acido (4d10)."},
    {"name": "Tabella Servizi, Alloggio e Vitto (PHB)", "category": "Regole", "type": "Economia & Servizi", "desc": "Prezzi di riferimento ufficiali per stile di vita e locande:\n• Miserabile: Cibo per strada, 0 mo.\n• Povero: 2 ma al giorno (locanda squallida, zuppa d'orzo e giaciglio).\n• Modesto: 1 mo al giorno (locanda semplice, pasto caldo e letto pulito).\n• Confortevole: 2 mo al giorno (buona taverna, arrosto, birra e camera privata).\n• Ricco: 4 mo al giorno (locanda raffinata, vini pregiati, bagno caldo).\n• Aristocratico: 10+ mo al giorno (suite lussuosa, servitu personale).\n• Servizi comuni: Boccale di birra: 4 mr • Bottiglia di vino buono: 10 ma • Razione (1 giorno): 5 ma • Cavallo da sella (affitto): 2 ma/giorno • Servizio di un mercenario/guida: 2 mo/giorno • Lancio incantesimo 1° liv: 10-20 mo, 2° liv: 30-50 mo, 3° liv: 90-150 mo."},
    {"name": "Tabella Grado di Sfida (CR) ed Esperienza (XP)", "category": "Regole", "type": "Guida del DM", "desc": "Tabella Ufficiale Conversione Grado di Sfida (CR) -> Punti Esperienza (XP):\n• CR 0: 10 XP (0 se innocuo) • CR 1/8: 25 XP (Prof. +2)\n• CR 1/4: 50 XP (Prof. +2) • CR 1/2: 100 XP (Prof. +2)\n• CR 1: 200 XP • CR 2: 450 XP • CR 3: 700 XP • CR 4: 1.100 XP\n• CR 5: 1.800 XP (Prof. +3) • CR 6: 2.300 XP • CR 7: 2.900 XP • CR 8: 3.900 XP\n• CR 9: 5.000 XP (Prof. +4) • CR 10: 5.900 XP • CR 11: 7.200 XP • CR 12: 8.400 XP\n• CR 13: 10.000 XP (Prof. +5) • CR 14: 11.500 XP • CR 15: 13.000 XP • CR 16: 15.000 XP\n• CR 17: 18.000 XP (Prof. +6) • CR 18: 20.000 XP • CR 19: 22.000 XP • CR 20: 25.000 XP\n• CR 21-24: 33.000-62.000 XP (Prof. +7) • CR 25-30: 75.000-155.000 XP (Prof. +8 a +9)."},
    {"name": "Tabella Follia a Breve, Lungo e Tempo Indefinito (DMG)", "category": "Regole", "type": "Guida del DM", "desc": "Effetti di follia da orrori cosmici o traumi abissali:\n• Breve Termine (1d10 minuti): 1-20: La creatura e ritirata in posizione fetale; 21-40: Incapacitata da urla e pianto; 41-60: Fuga terrorizzata; 61-80: Parla solo a balbettii incomprensibili; 81-100: Attacca la creatura piu vicina.\n• Lungo Termine (1d10 x 10 ore): Paranoia (non accetta cibo ne cure), Amnesia parziale (non riconosce gli alleati), Cecita o sordita isterica, Mancanza totale di paura e autoconservazione.\n• Tempo Indefinito (Permanente fino a Ristorare Superiore): Allucinazioni persistenti, Ossessione compulsiva per un oggetto, Mania di persecuzione o deliri di onnipotenza."},
    {"name": "Tabella CA e Punti Ferita degli Oggetti (DMG)", "category": "Regole", "type": "Guida del DM", "desc": "Resistenza e solidita degli oggetti inanimati:\n• Classe Armatura (CA) per Materiale: Stoffa/Carta: 11 • Vetro/Ghiaccio: 13 • Legno/Osso: 15 • Pietra: 17 • Ferro/Acciaio: 19 • Mithral: 21 • Adamantio: 23.\n• Punti Ferita per Taglia (Oggetto Fragile vs Resiliente):\n  - Minuscolo (bottiglia, lucchetto): Fragile 2 (1d4), Resiliente 5 (2d4)\n  - Piccola (forziere, sedia): Fragile 3 (1d6), Resiliente 10 (3d6)\n  - Media (barile, porta normale): Fragile 5 (1d8), Resiliente 18 (4d8)\n  - Grande (carro, portone di ferro): Fragile 10 (1d10), Resiliente 27 (5d10)\n• Soglia di Danno: Oggetti massicci (mura di castello) ignorano qualsiasi danno inferiore alla soglia (es. 10 o 15)."},
    {"name": "Regole di Viaggio e Inseguimenti (Chases & Travel)", "category": "Regole", "type": "Avventura", "desc": "• Ritmo di Viaggio (1 giorno = 8 ore di marcia):\n  - Rapido: 45 km/giorno (+1/3 velocita, -5 a Percezione passiva)\n  - Normale: 36 km/giorno (andatura standard)\n  - Lento: 27 km/giorno (permette di muoversi furtivamente)\n• Marcia Forzata: Ogni ora oltre l'8ª richiede un TS su Costituzione CD 10 + 1 per ogni ora extra o si subisce 1 livello di Indebolimento.\n• Inseguimenti: I partecipanti possono compiere l'azione di Scatto gratis per un numero di volte pari a 3 + mod Costituzione; ogni scatto successivo richiede una prova di Costituzione CD 10 o si subisce 1 livello di Indebolimento."},
    {"name": "Livelli di Indebolimento (Exhaustion 1-6)", "category": "Regole", "type": "Condizioni", "desc": "L'Indebolimento si accumula in 6 gradi progressivi:\n• Livello 1: Svantaggio a tutte le prove di caratteristica.\n• Livello 2: Velocita di movimento dimezzata.\n• Livello 3: Svantaggio ai tiri per colpire e a tutti i tiri salvezza.\n• Livello 4: Punti Ferita massimi dimezzati.\n• Livello 5: Velocita di movimento ridotta a 0.\n• Livello 6: Morte istantanea del personaggio.\nUn Riposo Lungo con cibo e acqua riduce l'Indebolimento di 1 livello."}
]

def get_all_equipment_offline(category: str = "Equipaggiamento") -> List[Dict[str, Any]]:
    """Restituisce il catalogo offline per Equipaggiamento, Armi o Pozioni combinato con SRD Magic Items."""
    cat_l = str(category).lower()
    results = []
    seen = set()

    for it in STANDARD_5E_EQUIPMENT_CATALOG:
        t_low = str(it.get("type", "")).lower()
        if "armi" in cat_l and "arma" not in t_low and "weapon" not in t_low:
            continue
        if "pozion" in cat_l and "pozion" not in t_low and "potion" not in t_low:
            continue
        copy_it = dict(it)
        copy_it["source"] = "SRD 5e"
        results.append(copy_it)
        seen.add(copy_it["name"].lower())

    for mit in get_all_magic_items_offline():
        m_type = str(mit.get("type", "")).lower()
        m_name = str(mit.get("name", ""))
        if "armi" in cat_l and "weapon" not in m_type:
            continue
        if "pozion" in cat_l and "potion" not in m_type:
            continue
        if m_name.lower() not in seen:
            seen.add(m_name.lower())
            results.append(mit)

    return results


def get_all_rules_offline() -> List[Dict[str, Any]]:
    """Restituisce le voci del compendio per le Regole D&D 5e offline (incluse Tabelle Bottino DMG A-I)."""
    rules = [dict(r) for r in STANDARD_5E_RULES_CATALOG]
    try:
        from common.srd_items_complete import DMG_TREASURE_HOARDS_A_I
        for t_name, t_info in DMG_TREASURE_HOARDS_A_I.items():
            rolls = t_info.get("rolls", [])
            lines = [t_info.get("title", t_name), "", "Tiro d100 | Oggetto Ottenuto | Rarità", "----------------------------------------"]
            for r in rolls:
                lines.append(f"d100 [{r.get('range')}]: {r.get('item')} ({r.get('rarity')})")
            rules.append({
                "name": f"Tabella Bottino DMG: {t_name}",
                "category": "Regole",
                "type": "Tabelle Bottino DMG",
                "desc": "\n".join(lines),
                "source": "Dungeon Master's Guide",
            })
    except Exception:
        pass
    return rules


def get_all_subclasses_offline() -> List[Dict[str, Any]]:
    """Restituisce tutte le 117 sottoclassi ufficiali complete di albero dei privilegi e descrizioni."""
    try:
        from common.srd_subclasses_complete import ALL_OFFICIAL_SUBCLASSES
        out = []
        for s in ALL_OFFICIAL_SUBCLASSES:
            sc = dict(s)
            sc["category"] = "Sottoclassi"
            sc["type"] = f"Sottoclasse ({sc.get('class_name', '')})"
            feats = sc.get("features", [])
            lines = [sc.get("description", ""), "", "📜 Albero dei Privilegi:"]
            for f in feats:
                lines.append(f"• Livello {f.get('level')}: {f.get('name')} — {f.get('desc')}")
            sc["desc"] = "\n".join(lines)
            out.append(sc)
        return out
    except Exception:
        return []


def get_all_exotic_races_offline() -> List[Dict[str, Any]]:
    """Restituisce le 28+ razze esotiche e mostruose ufficiali D&D 5e."""
    try:
        from common.srd_exotic_races import ALL_EXOTIC_RACES_CATALOG
        out = []
        for r in ALL_EXOTIC_RACES_CATALOG:
            rc = dict(r)
            rc["category"] = "Razze"
            rc["type"] = f"Razza ({rc.get('size', 'Media')})"
            lines = [rc.get("description", ""), ""]
            lines.append(f"🏃 Velocità: {rc.get('speed', 9)}m | Taglia: {rc.get('size', 'Media')}")
            bonuses = rc.get("ability_bonuses", {})
            if bonuses:
                bonuses_str = ", ".join(f"{k} +{v}" for k, v in bonuses.items())
                lines.append(f"⭐ Incrementi di Caratteristica: {bonuses_str}")
            traits = rc.get("traits", [])
            if traits:
                lines.append("\n🌟 Tratti Razziali:")
                for t in traits:
                    lines.append(f"• {t.get('name')}: {t.get('desc')}")
            subraces = rc.get("subraces", [])
            if subraces:
                lines.append("\n🧬 Sottorazze:")
                for sub in subraces:
                    lines.append(f"  [{sub.get('name')}]:")
                    for st in sub.get("traits", []):
                        lines.append(f"    • {st.get('name')}: {st.get('desc')}")
            rc["desc"] = "\n".join(lines)
            out.append(rc)
        return out
    except Exception:
        return []


def get_all_races_offline() -> List[Dict[str, Any]]:
    """Restituisce tutte le 37+ razze giocabili ufficiali (9 base PHB + 28+ esotiche/mostruose)."""
    out = []
    # 1. 9 Razze Base PHB
    try:
        from common.races_data import RACES
        for r_name, r_info in RACES.items():
            lines = [r_info.get("desc", ""), "", f"🏃 Velocità: {r_info.get('speed', 9)}m | Taglia: {r_info.get('size', 'Media')}"]
            traits = r_info.get("traits", [])
            if traits:
                lines.append("\n🌟 Tratti Razziali:")
                for t_name, t_desc in traits:
                    lines.append(f"• {t_name}: {t_desc}")
            subraces = r_info.get("subraces", {})
            if subraces:
                lines.append("\n🧬 Sottorazze:")
                for sub_name, sub_data in subraces.items():
                    lines.append(f"  [{sub_name}]: {sub_data.get('desc', '')}")
            out.append({
                "name": r_name,
                "name_en": r_info.get("name_en", r_name),
                "category": "Razze",
                "type": f"Razza Base ({r_info.get('size', 'Media')})",
                "speed": r_info.get("speed", 9),
                "size": r_info.get("size", "Media"),
                "desc": "\n".join(lines),
                "source": "Player's Handbook",
            })
    except Exception:
        pass

    # 2. 28+ Razze Esotiche
    out.extend(get_all_exotic_races_offline())
    return out


def get_all_dmg_loot_tables_offline() -> Dict[str, Any]:
    """Restituisce le tabelle ufficiali DMG di tesori e bottino (A-I)."""
    try:
        from common.srd_items_complete import DMG_TREASURE_HOARDS_A_I
        return DMG_TREASURE_HOARDS_A_I
    except Exception:
        return {}


def get_all_classes_offline() -> List[Dict[str, Any]]:
    """Restituisce le schede di progressione complete 1-20 e le sottoclassi di tutte le 13 classi D&D 5e."""
    class_names_it = {
        "fighter": "Guerriero (Fighter)",
        "barbarian": "Barbaro (Barbarian)",
        "rogue": "Ladro (Rogue)",
        "wizard": "Mago (Wizard)",
        "cleric": "Chierico (Cleric)",
        "paladin": "Paladino (Paladin)",
        "ranger": "Ranger",
        "bard": "Bardo (Bard)",
        "druid": "Druido (Druid)",
        "monk": "Monaco (Monk)",
        "sorcerer": "Stregone (Sorcerer)",
        "warlock": "Warlock",
        "artificer": "Artefice (Artificer)",
    }
    out = []
    for c_key, c_data in CLASS_PROGRESSION_TABLE.items():
        title = class_names_it.get(c_key, c_key.title())
        hd = c_data.get("hit_die", 8)
        feats_map = c_data.get("features", {})
        subclasses = c_data.get("subclasses", [])
        
        lines = [f"🎲 Dado Vita: d{hd} per livello", ""]
        if subclasses:
            lines.append("🔮 Archetipi & Sottoclassi Ufficiali:")
            for sc in subclasses:
                lines.append(f"  • {sc}")
            lines.append("")
        lines.append("📈 Progressione Privilegi (Livelli 1-20):")
        for lvl in sorted(feats_map.keys()):
            f_list = ", ".join(feats_map[lvl])
            lines.append(f"• Livello {lvl}: {f_list}")
        out.append({
            "name": title,
            "category": "Classi",
            "type": f"Dado Vita d{hd}",
            "desc": "\n".join(lines),
            "source": "D&D 5e (PHB/TCoE)",
        })
    return out


def get_all_traits_offline() -> List[Dict[str, Any]]:
    """Restituisce l'elenco completo dei privilegi di classe e tratti razziali 5e offline."""
    traits = []
    seen = set()
    
    # 1. Tratti di classe (13 classi, livelli 1-20)
    for c_key, c_data in CLASS_PROGRESSION_TABLE.items():
        for lvl, f_list in c_data.get("features", {}).items():
            for feat in f_list:
                clean_name = feat.strip()
                if clean_name.lower() in seen or "asi" in clean_name.lower() or "aumento punteggi" in clean_name.lower():
                    continue
                seen.add(clean_name.lower())
                traits.append({
                    "name": clean_name,
                    "category": "Tratti",
                    "type": f"{c_key.title()} (Liv. {lvl})",
                    "desc": f"Privilegio della classe {c_key.title()} ottenuto al Livello {lvl}.",
                    "source": "D&D 5e (Classi)",
                })
                
    # 2. Tratti Razziali dalle 9 razze e relative sottorazze
    try:
        from common.races_data import RACES
        for r_name, r_info in RACES.items():
            for t_tuple in r_info.get("traits", []):
                t_name, t_desc = t_tuple[0], t_tuple[1]
                if t_name.lower() not in seen:
                    seen.add(t_name.lower())
                    traits.append({
                        "name": f"{t_name} ({r_name})",
                        "category": "Tratti",
                        "type": f"Tratto Razziale ({r_name})",
                        "desc": t_desc,
                        "source": "D&D 5e (Razze)",
                    })
    except Exception:
        pass

    # 3. Privilegi delle 117 Sottoclassi Ufficiali
    try:
        from common.srd_subclasses_complete import ALL_OFFICIAL_SUBCLASSES
        for sc in ALL_OFFICIAL_SUBCLASSES:
            sc_name = sc.get("name", "")
            c_name = sc.get("class_name", "")
            for feat in sc.get("features", []):
                f_name = feat.get("name", "").strip()
                if f_name.lower() not in seen:
                    seen.add(f_name.lower())
                    traits.append({
                        "name": f"{f_name} ({sc_name})",
                        "category": "Tratti",
                        "type": f"Sottoclasse {c_name} (Liv. {feat.get('level')})",
                        "desc": feat.get("desc", ""),
                        "source": sc.get("source", "D&D 5e"),
                    })
    except Exception:
        pass

    # 4. Tratti delle 28+ Razze Esotiche
    try:
        from common.srd_exotic_races import ALL_EXOTIC_RACES_CATALOG
        for er in ALL_EXOTIC_RACES_CATALOG:
            er_name = er.get("name", "")
            for t in er.get("traits", []):
                t_name = t.get("name", "").strip()
                if t_name.lower() not in seen:
                    seen.add(t_name.lower())
                    traits.append({
                        "name": f"{t_name} ({er_name})",
                        "category": "Tratti",
                        "type": f"Tratto Razziale ({er_name})",
                        "desc": t.get("desc", ""),
                        "source": er.get("source", "D&D 5e"),
                    })
            for sub in er.get("subraces", []):
                sub_name = sub.get("name", "")
                for st in sub.get("traits", []):
                    st_name = st.get("name", "").strip()
                    if st_name.lower() not in seen:
                        seen.add(st_name.lower())
                        traits.append({
                            "name": f"{st_name} ({sub_name})",
                            "category": "Tratti",
                            "type": f"Tratto Sottorazza ({sub_name})",
                            "desc": st.get("desc", ""),
                            "source": er.get("source", "D&D 5e"),
                        })
    except Exception:
        pass

    return traits


def resolve_compendium_item(raw_entry: str, default_qty: int = 1) -> Dict[str, Any]:
    """
    Risolve una stringa di oggetto (es. '2x Pozione di Guarigione', 'Spada Lunga +1', 'Corda di Canapa')
    interrogando nell'ordine:
    1. Compendio Custom (srd_data/custom_compendium.json)
    2. Compendio SRD Offline (srd_data/open5e_magicitems.json)
    3. Catalogo Equipaggiamento Standard 5e (common/starter_equipment.py)
    Restituisce un dizionario strutturato pronto per l'inventario VTT e la distribuzione del loot.
    """
    from common.starter_equipment import (
        lookup_standard_weight,
        DEFAULT_CAMPAIGN_STARTER_KIT,
        STARTER_PACK_CONTENTS,
        CLASS_STARTING_KITS,
    )

    s = str(raw_entry or "").strip().strip('"\'')
    qty = default_qty
    # Estrai prefisso o suffisso quantità: "2x Pozione", "3 Pozioni", "Pozione (x2)"
    m_pre = re.match(r'^(\d+)\s*[xX]\s*(.+)$', s)
    m_suf = re.match(r'^(.+?)\s*\(\s*[xX]?(\d+)\s*\)$', s)
    if m_pre:
        qty = max(1, int(m_pre.group(1)))
        s = m_pre.group(2).strip().strip('"\'')
    elif m_suf:
        qty = max(1, int(m_suf.group(2)))
        s = m_suf.group(1).strip().strip('"\'')

    clean_low = s.lower()

    # 1. Cerca nel Compendio Custom (custom_compendium.json)
    custom_path = os.path.join(SRD_DIR, "custom_compendium.json")
    if os.path.isfile(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            for cat in ("Oggetti Magici", "Equipaggiamento", "Armi", "Pozioni"):
                for cit in cdata.get(cat, []):
                    cname = str(cit.get("name") or cit.get("title") or "").strip()
                    if cname.lower() == clean_low:
                        w = cit.get("weight")
                        try:
                            w = float(w) if w is not None else lookup_standard_weight(cname)
                        except (ValueError, TypeError):
                            w = lookup_standard_weight(cname)
                        return {
                            "name": cname,
                            "qty": qty,
                            "type": cit.get("type") or cat,
                            "weight": w,
                            "rarity": cit.get("rarity", "Comune"),
                            "desc": cit.get("desc", ""),
                            "attuned": False,
                            "from_compendium": True,
                            "compendium_source": "Compendio Custom",
                        }
        except Exception:
            pass

    # 2. Cerca nel Compendio SRD Offline (open5e_magicitems.json)
    srd_it = OfflineSRD.get_instance().get_magic_item(s)
    if srd_it:
        raw_type = str(srd_it.get("type", "Oggetto Magico"))
        type_it = "Oggetto Magico"
        rt_low = raw_type.lower()
        if "potion" in rt_low or "pozion" in clean_low:
            type_it = "Pozione"
        elif "scroll" in rt_low or "pergamen" in clean_low:
            type_it = "Pergamena"
        elif "weapon" in rt_low or any(w in clean_low for w in ["spada", "ascia", "arco", "pugnale", "martello", "lancia"]):
            type_it = "Arma"
        elif "armor" in rt_low or "armatura" in clean_low or "corazza" in clean_low:
            type_it = "Armatura"
        elif "shield" in rt_low or "scudo" in clean_low:
            type_it = "Scudo"

        w = lookup_standard_weight(s)
        if w <= 0.0:
            w = 0.5 if type_it in ("Pozione", "Pergamena") else 1.0

        return {
            "name": s,
            "srd_name": srd_it.get("name", s),
            "qty": qty,
            "type": type_it,
            "weight": w,
            "rarity": srd_it.get("rarity", "Non Comune"),
            "desc": srd_it.get("desc", ""),
            "requires_attunement": bool(srd_it.get("requires_attunement")),
            "attuned": False,
            "from_compendium": True,
            "compendium_source": "SRD 5.1",
        }

    # 3. Cerca nel Catalogo Equipaggiamento Standard 5e (starter_equipment.py)
    std_catalog: List[Dict[str, Any]] = []
    std_catalog.extend(DEFAULT_CAMPAIGN_STARTER_KIT)
    for p_list in STARTER_PACK_CONTENTS.values():
        std_catalog.extend(p_list)
    for k_data in CLASS_STARTING_KITS.values():
        std_catalog.extend(k_data.get("inventory", []))

    for std_it in std_catalog:
        std_name = str(std_it.get("name", "")).strip()
        if std_name.lower() == clean_low or clean_low in std_name.lower():
            w = std_it.get("weight", 0.0) or lookup_standard_weight(std_name)
            return {
                "name": s if std_name.lower() != clean_low else std_name,
                "qty": qty,
                "type": std_it.get("type", "Equipaggiamento"),
                "weight": float(w),
                "rarity": "Comune",
                "desc": std_it.get("desc", ""),
                "attuned": False,
                "from_compendium": True,
                "compendium_source": "Equipaggiamento 5e",
            }

    # 4. Fallback se il nome corrisponde a un peso standard 5e (es. "Spada Lunga", "Corda di Seta", "Torcia")
    std_w = lookup_standard_weight(s)
    inferred_type = "Equipaggiamento"
    if any(k in clean_low for k in ["spada", "ascia", "pugnale", "arco", "balestra", "martello", "mazza", "lancia", "giavellotto", "stocco", "scimitarra", "alabarda"]):
        inferred_type = "Arma"
    elif any(k in clean_low for k in ["armatura", "corazza", "cotta", "giaco"]):
        inferred_type = "Armatura"
    elif "scudo" in clean_low:
        inferred_type = "Scudo"
    elif "pozion" in clean_low or "elisir" in clean_low or "antidoto" in clean_low:
        inferred_type = "Pozione"
    elif "pergamen" in clean_low:
        inferred_type = "Pergamena"

    return {
        "name": s,
        "qty": qty,
        "type": inferred_type,
        "weight": std_w,
        "rarity": "Comune",
        "desc": "Oggetto standard D&D 5e." if std_w > 0 else "",
        "attuned": False,
        "from_compendium": bool(std_w > 0),
        "compendium_source": "Equipaggiamento 5e" if std_w > 0 else "Personalizzato",
    }


def parse_loot_specification(raw_loot: Any) -> Dict[str, Any]:
    """
    Analizza una specifica di loot DndScript (es. '100 mo, 50 ma, 2x Pozione di Cura, Spada Lunga +1')
    separando le valute (MR, MA, ME, MO, MP) e risolvendo ciascun oggetto nel Compendio.
    """
    currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
    resolved_items: List[Dict[str, Any]] = []

    if not raw_loot:
        return {"currency": currency, "items": resolved_items}

    if isinstance(raw_loot, list):
        tokens = [str(x).strip() for x in raw_loot if str(x).strip()]
    else:
        tokens = [t.strip() for t in str(raw_loot).split(",") if t.strip()]

    coin_patterns = [
        ("MP", r"^(\d+)\s*(?:mp|pp|monete\s+d['i]\s*platino|platino)$"),
        ("ME", r"^(\d+)\s*(?:me|ep|monete\s+d['i]\s*electrum|electrum|electro)$"),
        ("MA", r"^(\d+)\s*(?:ma|sp|monete\s+d['i]\s*argento|argento)$"),
        ("MR", r"^(\d+)\s*(?:mr|cp|monete\s+di\s*rame|rame)$"),
        ("MO", r"^(\d+)\s*(?:mo|gp|monete\s+d['i]\s*oro|oro)$"),
    ]

    for tok in tokens:
        clean_tok = tok.strip().strip('"\'')
        if not clean_tok:
            continue
        matched_coin = False
        for c_code, pat in coin_patterns:
            m = re.match(pat, clean_tok, re.IGNORECASE)
            if m:
                currency[c_code] += int(m.group(1))
                matched_coin = True
                break
        if not matched_coin:
            resolved_items.append(resolve_compendium_item(clean_tok))

    return {"currency": currency, "items": resolved_items}


def format_monster_action_tooltip(action: Any, monster_name: str = "") -> str:
    """
    Formatta una stringa di ToolTip ricca e dettagliata per un'azione o attacco di un mostro/PNG,
    evidenziando Tiro per Colpire (TpC), formula e dadi danno, portata/gittata e Tiri Salvezza.
    """
    if not action:
        return "Nessuna informazione disponibile per questa azione."
        
    if isinstance(action, str):
        action_name = action.split(".")[0].strip() if "." in action else "Azione"
        desc = action.strip()
        act_dict = {"name": action_name, "desc": desc}
    elif isinstance(action, dict):
        act_dict = action
        action_name = act_dict.get("name", "Azione")
        desc = act_dict.get("desc", "")
    else:
        return str(action)

    lines = [f"⚔️ {action_name}"]
    tags = []

    # 1. Bonus al tiro per colpire
    atk_bonus = act_dict.get("attack_bonus")
    if atk_bonus is not None and atk_bonus != 0:
        val = int(atk_bonus)
        tags.append(f"🎯 TpC: +{val}" if val >= 0 else f"🎯 TpC: {val}")
    else:
        m_atk = re.search(r'([+-]\d+)\s+to\s+hit', desc, re.I)
        if m_atk:
            tags.append(f"🎯 TpC: {m_atk.group(1)}")

    # 2. Formula Danni e Tipo di Danno
    m_hit = re.search(r'Hit:\s*([0-9]+\s*\([^)]+\)[^.]+)', desc, re.I)
    if m_hit:
        dmg_clean = m_hit.group(1).strip()
        tags.append(f"💥 Danno: {dmg_clean}")
    elif act_dict.get("damage_dice"):
        d_dice = act_dict.get("damage_dice")
        d_bonus = act_dict.get("damage_bonus")
        if d_bonus:
            d_val = f"+{d_bonus}" if int(d_bonus) >= 0 else str(d_bonus)
            tags.append(f"💥 Danno: {d_dice} {d_val}")
        else:
            tags.append(f"💥 Danno: {d_dice}")
    else:
        m_takes = re.search(r'(?:taking|takes)\s+([0-9]+\s*\([^)]+\)\s*[a-zA-Z\s]+damage)', desc, re.I)
        if m_takes:
            tags.append(f"💥 Danno: {m_takes.group(1).strip()}")

    # 3. Portata / Gittata (reach / range)
    m_reach = re.search(r'reach\s+(\d+\s*(?:ft|m)\.?)', desc, re.I)
    m_range = re.search(r'range\s+(\d+(?:/\d+)?\s*(?:ft|m)\.?)', desc, re.I)
    m_area = re.search(r'(\d+[- ]foot\s*(?:line|cone|sphere|cube|radius))', desc, re.I)
    if m_reach:
        tags.append(f"📏 Portata: {m_reach.group(1)}")
    elif m_range:
        tags.append(f"🏹 Gittata: {m_range.group(1)}")
    elif m_area:
        tags.append(f"📐 Area: {m_area.group(1)}")

    # 4. Tiro Salvezza (DC / CD)
    m_dc = re.search(r'DC\s+(\d+)\s+([A-Za-z]+)\s+saving\s+throw', desc, re.I)
    if m_dc:
        stat_en = m_dc.group(2).lower()
        stat_map = {
            "strength": "FOR", "dexterity": "DES", "constitution": "COS",
            "intelligence": "INT", "wisdom": "SAG", "charisma": "CAR"
        }
        stat_label = stat_map.get(stat_en, m_dc.group(2).upper())
        tags.append(f"🛡️ TS: CD {m_dc.group(1)} {stat_label}")

    if tags:
        lines.append("  •  ".join(tags))

    if desc:
        lines.append("─────────────────────────────")
        lines.append(desc)

    return "\n".join(lines)


def normalize_ac_value(ac_data: Any, default: int = 10) -> int:
    """
    Estrae e normalizza un valore numerico intero valido per la Classe Armatura (CA).
    Gestisce formati eterogenei da API D&D 5e, compendi JSON e PDF:
    - int / float: 18 -> 18
    - list di dict: [{'type': 'natural', 'value': 22}] -> 22, [{}] -> default
    - dict: {'value': 18, 'type': 'armor'} -> 18, {'ac': 16} -> 16
    - stringhe: '18 (natural armor)' -> 18, '15' -> 15, '[{}]' -> default
    - liste vuote o annidate: [15] -> 15, [] -> default
    """
    if ac_data is None:
        return default
    if isinstance(ac_data, int):
        return ac_data
    if isinstance(ac_data, float):
        return int(ac_data)

    if isinstance(ac_data, str):
        s = ac_data.strip()
        # Prova a parsare come struttura letterale se contiene parentesi quadre/graffe
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                parsed = ast.literal_eval(s)
                return normalize_ac_value(parsed, default=default)
            except Exception:
                pass
        m = re.search(r'\b\d+\b', s)
        if m:
            try:
                return int(m.group(0))
            except ValueError:
                pass
        return default

    if isinstance(ac_data, list):
        for item in ac_data:
            val = normalize_ac_value(item, default=None)
            if val is not None:
                return val
        return default

    if isinstance(ac_data, dict):
        for key in ("value", "ac", "armor_class", "val"):
            if key in ac_data:
                val = normalize_ac_value(ac_data[key], default=None)
                if val is not None:
                    return val
        for v in ac_data.values():
            val = normalize_ac_value(v, default=None)
            if val is not None:
                return val
        return default

    return default


def normalize_speed_value(speed_data: Any, default_unit: Optional[str] = None) -> tuple:
    """
    Estrae e normalizza la velocità della creatura in:
      (speed_val: int, speed_display: str, speed_unit: str)
    - speed_val: intero pulito per la velocità base (es. 30 o 40 o 9)
    - speed_display: stringa descrittiva per tutti i movimenti (es. '40 ft • Volo 80 ft')
    - speed_unit: unità ('ft' o 'm')
    Non restituisce MAI rappresentazioni json grezze come '{}' o '[]'.
    """
    if speed_data is None:
        u = default_unit or "ft"
        return 30, f"30 {u}", u

    # Gestione stringhe
    if isinstance(speed_data, str):
        s = speed_data.strip()
        if not s or s in ("{}", "[]", "[{}]", "None"):
            u = default_unit or "ft"
            return 30, f"30 {u}", u

        # Se è una stringa che serializza una lista o dict (es. "[{}]" o "{'walk': '30 ft.'}")
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                parsed = ast.literal_eval(s)
                return normalize_speed_value(parsed, default_unit=default_unit)
            except Exception:
                pass

        unit = "m" if (" m" in s.lower() or "metr" in s.lower()) else (default_unit or "ft")
        m_first = re.search(r'\b\d+\b', s)
        base_val = int(m_first.group(0)) if m_first else 30

        # Se contiene modalità di movimento o virgole
        if any(w in s.lower() for w in ("fly", "swim", "burrow", "climb", "volo", "nuoto", "scavo", "scalata", ",")):
            cleaned = s
            cleaned = re.sub(r'\bfly\b', 'Volo', cleaned, flags=re.I)
            cleaned = re.sub(r'\bswim\b', 'Nuoto', cleaned, flags=re.I)
            cleaned = re.sub(r'\bburrow\b', 'Scavo', cleaned, flags=re.I)
            cleaned = re.sub(r'\bclimb\b', 'Scalata', cleaned, flags=re.I)
            cleaned = re.sub(r'\bwalk\b', '', cleaned, flags=re.I)
            parts = [p.strip(' .,') for p in re.split(r',\s*(?![^()]*\))', cleaned) if p.strip(' .,')]
            disp = " • ".join(parts) if parts else f"{base_val} {unit}"
            return base_val, disp, unit
        else:
            return base_val, f"{base_val} {unit}", unit

    # Gestione numeri
    if isinstance(speed_data, (int, float)):
        val = int(speed_data)
        u = default_unit or ("m" if val <= 18 else "ft")
        return val, f"{val} {u}", u

    # Gestione liste
    if isinstance(speed_data, list):
        if not speed_data:
            u = default_unit or "ft"
            return 30, f"30 {u}", u
        merged = {}
        for item in speed_data:
            if isinstance(item, dict):
                merged.update(item)
            elif isinstance(item, (int, float, str)):
                return normalize_speed_value(item, default_unit=default_unit)
        if merged:
            return normalize_speed_value(merged, default_unit=default_unit)
        u = default_unit or "ft"
        return 30, f"30 {u}", u

    # Gestione dict (es. {"walk": "40 ft.", "burrow": "40 ft.", "fly": "80 ft."})
    if isinstance(speed_data, dict):
        if not speed_data:
            u = default_unit or "ft"
            return 30, f"30 {u}", u

        all_vals_str = " ".join(str(v) for v in speed_data.values()).lower()
        if " m" in all_vals_str or "metro" in all_vals_str or "metri" in all_vals_str:
            unit = "m"
        elif "ft" in all_vals_str:
            unit = "ft"
        else:
            unit = default_unit or "ft"

        walk_val = speed_data.get("walk") or speed_data.get("walking")
        base_val = 30
        if walk_val is not None:
            m = re.search(r'\d+', str(walk_val))
            if m:
                base_val = int(m.group(0))
        else:
            for k, v in speed_data.items():
                if k == "hover":
                    continue
                m = re.search(r'\d+', str(v))
                if m:
                    base_val = int(m.group(0))
                    break

        parts = []
        if walk_val is not None:
            m = re.search(r'\d+', str(walk_val))
            if m:
                parts.append(f"{m.group(0)} {unit}")
        elif not any(k in speed_data for k in ("fly", "swim", "burrow", "climb")):
            parts.append(f"{base_val} {unit}")

        for mode, lbl in [("fly", "Volo"), ("swim", "Nuoto"), ("burrow", "Scavo"), ("climb", "Scalata")]:
            if mode in speed_data:
                m = re.search(r'\d+', str(speed_data[mode]))
                if m:
                    parts.append(f"{lbl} {m.group(0)} {unit}")

        if speed_data.get("hover") is True or "hover" in str(speed_data.get("fly", "")).lower():
            parts.append("(fluttua)")

        disp = " • ".join(parts) if parts else f"{base_val} {unit}"
        return base_val, disp, unit

    u = default_unit or "ft"
    return 30, f"30 {u}", u


def normalize_size_value(size_data: Any) -> int:
    """Converte la taglia D&D 5e (stringa o numero) nel numero di esagoni/caselle (size) del token."""
    if isinstance(size_data, (int, float)):
        return max(1, int(size_data))
    s = str(size_data or "").strip().lower()
    if any(k in s for k in ("gargantuan", "mastodontic", "colossal")):
        return 4
    if any(k in s for k in ("huge", "enorme")):
        return 3
    if any(k in s for k in ("large", "grande")):
        return 2
    # Tiny, Small, Medium, Piccola, Media -> 1 esagono
    return 1


def normalize_damage_list(damage_data: Any) -> List[str]:
    """Converte resistenze, immunità o vulnerabilità (lista o stringa) in lista normalizzata di tipi di danno."""
    if not damage_data:
        return []
    result = []
    if isinstance(damage_data, list):
        for item in damage_data:
            if isinstance(item, str):
                for sub in re.split(r'[,;]|(?:\band\b)|(?:\be\b)', item):
                    clean = sub.strip().lower()
                    if clean and clean not in result:
                        result.append(clean)
            elif isinstance(item, dict) and "name" in item:
                clean = str(item["name"]).strip().lower()
                if clean and clean not in result:
                    result.append(clean)
    elif isinstance(damage_data, str):
        for sub in re.split(r'[,;]|(?:\band\b)|(?:\be\b)', damage_data):
            clean = sub.strip().lower()
            if clean and clean not in result:
                result.append(clean)
    return result


def extract_legendary_stats(mdata: Dict[str, Any]) -> tuple:
    """Estrae (legendary_resistances, legendary_actions, has_lair) da dizionario o statblock di una creatura."""
    if not isinstance(mdata, dict):
        return 0, 0, False
    
    # 1. Legendary Resistances (es. 3/Day)
    leg_res = 0
    abilities = mdata.get("special_abilities") or mdata.get("features") or []
    if isinstance(abilities, list):
        for ab in abilities:
            ab_name = ab.get("name", "") if isinstance(ab, dict) else str(ab)
            ab_desc = ab.get("desc", "") if isinstance(ab, dict) else ""
            if "legendary resistance" in ab_name.lower() or "resistenza leggendaria" in ab_name.lower():
                m_count = re.search(r'\((\d+)\s*/\s*(?:day|giorno)\)', ab_name, re.IGNORECASE)
                if not m_count:
                    m_count = re.search(r'\((\d+)\s*/\s*(?:day|giorno)\)', ab_desc, re.IGNORECASE)
                leg_res = int(m_count.group(1)) if m_count else 3
                break

    # 2. Legendary Actions (di norma 3 azioni per round per creature leggendarie)
    leg_actions = mdata.get("legendary_actions") or []
    leg_act_count = 3 if (isinstance(leg_actions, list) and len(leg_actions) > 0) else 0

    # 3. Lair Actions
    has_lair = bool(mdata.get("lair_actions") or "lair_actions" in mdata)
    if not has_lair and isinstance(abilities, list):
        for ab in abilities:
            t = str(ab).lower()
            if "lair action" in t or "azione della tana" in t:
                has_lair = True
                break

    return leg_res, leg_act_count, has_lair


def extract_darkvision_flag(mdata: Dict[str, Any]) -> bool:
    """Verifica se una creatura possiede Scurovisione dai sensi o tratti."""
    if not isinstance(mdata, dict):
        return False
    senses = str(mdata.get("senses", "")).lower()
    if "darkvision" in senses or "scurovisione" in senses:
        return True
    traits = mdata.get("special_abilities") or mdata.get("features") or []
    if isinstance(traits, list):
        for t in traits:
            text = str(t).lower()
            if "darkvision" in text or "scurovisione" in text:
                return True
    return False


# -----------------------------------------------------------------------------
# FUNZIONI DI MATCHING & FILTRAGGIO RAPIDO (CR, TIPO, RARITÀ, SCUOLA)
# -----------------------------------------------------------------------------

def parse_cr_to_float(cr_val: Any) -> float:
    """Converte un Grado di Sfida (es. '1/2', '1/4', '0', 5, '17') in float."""
    if cr_val is None:
        return 0.0
    s = str(cr_val).strip()
    if "/" in s:
        parts = s.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def match_monster_cr(cr_val: Any, cr_filter: Optional[str]) -> bool:
    """Verifica se il CR soddisfa il filtro raggruppato."""
    if not cr_filter or cr_filter in ("Tutti i CR", "All CR"):
        return True
    val = parse_cr_to_float(cr_val)
    if "0 - 1/2" in cr_filter:
        return val <= 0.5
    elif "1 - 4" in cr_filter:
        return 1.0 <= val <= 4.0
    elif "5 - 9" in cr_filter:
        return 5.0 <= val <= 9.0
    elif "10 - 14" in cr_filter:
        return 10.0 <= val <= 14.0
    elif "15 - 19" in cr_filter:
        return 15.0 <= val <= 19.0
    elif "20+" in cr_filter:
        return val >= 20.0
    return True


CREATURE_TYPE_MAP = {
    "aberrazione": ["aberration", "aberrazione"],
    "bestia": ["beast", "bestia"],
    "celestiale": ["celestial", "celestiale"],
    "costrutto": ["construct", "costrutto"],
    "drago": ["dragon", "drago"],
    "elementale": ["elemental", "elementale"],
    "fata": ["fey", "fata"],
    "gigante": ["giant", "gigante"],
    "immondo": ["fiend", "immondo", "demon", "devil"],
    "melma": ["ooze", "melma"],
    "mostruosità": ["monstrosity", "mostruosita", "mostro"],
    "non morto": ["undead", "non morto", "non-morto"],
    "pianta": ["plant", "pianta"],
    "umanoide": ["humanoid", "umanoide"],
}


def match_monster_type(raw_type: Any, type_filter: Optional[str]) -> bool:
    """Verifica se la tipologia della creatura soddisfa il filtro bilingue."""
    if not type_filter or type_filter in ("Tutti i Tipi", "All Types"):
        return True
    if raw_type is None:
        return False
    t_str = str(raw_type).strip().lower()
    f_str = type_filter.strip().lower()

    keywords = CREATURE_TYPE_MAP.get(f_str, [f_str])
    return any(k in t_str for k in keywords)


ITEM_RARITY_MAP = {
    "comune": ["common", "comune"],
    "non comune": ["uncommon", "non comune"],
    "raro": ["rare", "raro"],
    "molto raro": ["very rare", "molto raro"],
    "leggendario": ["legendary", "leggendario"],
    "artefatto": ["artifact", "artefatto"],
}


def match_item_rarity(raw_rarity: Any, rarity_filter: Optional[str]) -> bool:
    """Verifica se la rarità dell'oggetto soddisfa il filtro."""
    if not rarity_filter or rarity_filter in ("Tutte le Rarità", "All Rarities"):
        return True
    if raw_rarity is None:
        return False
    r_str = str(raw_rarity).strip().lower()
    f_str = rarity_filter.strip().lower()

    keywords = ITEM_RARITY_MAP.get(f_str, [f_str])
    return any(k in r_str for k in keywords)


ITEM_TYPE_MAP = {
    "arma": ["weapon", "arma", "spada", "arco", "pugnale", "ascia"],
    "armatura": ["armor", "armatura", "scudo", "shield"],
    "pozione": ["potion", "pozione", "olio", "elixir"],
    "pergamena": ["scroll", "pergamena"],
    "anello": ["ring", "anello"],
    "bacchetta/verga": ["wand", "rod", "staff", "bacchetta", "verga", "bastone"],
    "meraviglia": ["wondrous", "meraviglia", "oggetto meraviglioso"],
}


def match_item_type(raw_type: Any, type_filter: Optional[str]) -> bool:
    """Verifica se la categoria dell'oggetto soddisfa il filtro."""
    if not type_filter or type_filter in ("Tutti i Tipi", "All Types"):
        return True
    if raw_type is None:
        return False
    t_str = str(raw_type).strip().lower()
    f_str = type_filter.strip().lower()

    keywords = ITEM_TYPE_MAP.get(f_str, [f_str])
    return any(k in t_str for k in keywords)


SPELL_SCHOOL_MAP = {
    "abiurazione": ["abjuration", "abiurazione"],
    "ammaliamento": ["enchantment", "ammaliamento"],
    "divinazione": ["divination", "divinazione"],
    "evocazione": ["conjuration", "evocazione"],
    "illusione": ["illusion", "illusione"],
    "invocazione": ["evocation", "invocazione"],
    "necromanzia": ["necromancy", "necromanzia"],
    "trasmutazione": ["transmutation", "trasmutazione"],
}


def match_spell_school(raw_school: Any, school_filter: Optional[str]) -> bool:
    """Verifica se la scuola di magia soddisfa il filtro."""
    if not school_filter or school_filter in ("Tutte le Scuole", "All Schools"):
        return True
    if raw_school is None:
        return False
    s_str = str(raw_school).strip().lower()
    f_str = school_filter.strip().lower()

    keywords = SPELL_SCHOOL_MAP.get(f_str, [f_str])
    return any(k in s_str for k in keywords)


def match_spell_level(raw_level: Any, level_filter: Optional[str]) -> bool:
    """Verifica se il livello dell'incantesimo soddisfa il filtro."""
    if not level_filter or level_filter in ("Tutti i Livelli", "All Levels"):
        return True
    if raw_level is None:
        return False
    s_val = str(raw_level).strip().lower()
    f_val = str(level_filter).strip().lower()

    if "trucchetto" in f_val or "cantrip" in f_val or "0" in f_val:
        return s_val in ("0", "cantrip", "trucchetto") or "cantrip" in s_val or "trucchetto" in s_val

    # Estrae il numero del livello dal filtro (es. "Livello 3" -> 3)
    m_f = re.search(r'\d+', f_val)
    m_s = re.search(r'\d+', s_val)
    if m_f and m_s:
        return int(m_f.group(0)) == int(m_s.group(0))
    return f_val in s_val





