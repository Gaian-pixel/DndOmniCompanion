"""
Catalogo completo delle creature ufficiali D&D 5e protette da IP WotC (Monster Manual, Volo, MToF).
Integrazione offline al 100% per DndOmniCompanion.
"""

ALL_WOTC_MONSTERS = [
    {
        "name": "Spectator",
        "size": "Medium",
        "type": "aberration",
        "alignment": "lawful neutral",
        "armor_class": 14,
        "hit_points": 39,
        "hit_dice": "6d8 + 12",
        "speed": "0 ft., fly 30 ft. (hover)",
        "strength": 8,
        "dexterity": 14,
        "constitution": 14,
        "intelligence": 13,
        "wisdom": 14,
        "charisma": 11,
        "challenge_rating": "3",
        "cr": 3,
        "senses": "darkvision 120 ft., passive Perception 16",
        "languages": "Deep Speech, Undercommon, telepathy 120 ft.",
        "special_abilities": [
            {
                "name": "Spell Reflection",
                "desc": "Se lo spettatore supera un tiro salvezza contro un incantesimo o un attacco con incantesimo lo manca, può riflettere l'incantesimo su un'altra creatura entro 9m."
            }
        ],
        "actions": [
            {
                "name": "Bite",
                "desc": "Melee Weapon Attack: +1 to hit, reach 5 ft., one target. Hit: 5 (2d4) piercing damage."
            },
            {
                "name": "Eye Rays",
                "desc": "Spara fino a 2 raggi oculari a caso: 1. Confusione (TS Saggezza CD 13), 2. Paralisi (TS Costituzione CD 13, 1 minuto), 3. Paura (TS Saggezza CD 13), 4. Ferimento (TS Costituzione CD 13, 16 (3d10) danni necrotici)."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Gauth",
        "size": "Medium",
        "type": "aberration",
        "alignment": "lawful evil",
        "armor_class": 15,
        "hit_points": 67,
        "hit_dice": "9d8 + 27",
        "speed": "0 ft., fly 20 ft. (hover)",
        "strength": 10,
        "dexterity": 14,
        "constitution": 16,
        "intelligence": 15,
        "wisdom": 15,
        "charisma": 13,
        "challenge_rating": "6",
        "cr": 6,
        "senses": "darkvision 120 ft., passive Perception 15",
        "languages": "Deep Speech, Undercommon",
        "special_abilities": [
            {
                "name": "Stunning Gaze",
                "desc": "Occhio centrale stordente: TS Saggezza CD 14 all'inizio del turno o la creatura è stordita fino all'inizio del suo prossimo turno."
            }
        ],
        "actions": [
            {
                "name": "Bite",
                "desc": "Melee Weapon Attack: +3 to hit, reach 5 ft., one target. Hit: 9 (2d8) piercing damage."
            },
            {
                "name": "Eye Rays",
                "desc": "Spara 3 raggi oculari tra i 6 disponibili (Fuoco, Esaurimento, Spinta, Debilitazione, Sonno, Telecinesi) con CD 14."
            }
        ],
        "source": "Volo's Guide to Monsters"
    },
    {
        "name": "Death Tyrant",
        "size": "Large",
        "type": "undead",
        "alignment": "lawful evil",
        "armor_class": 19,
        "hit_points": 187,
        "hit_dice": "25d10 + 50",
        "speed": "0 ft., fly 20 ft. (hover)",
        "strength": 10,
        "dexterity": 14,
        "constitution": 14,
        "intelligence": 19,
        "wisdom": 15,
        "charisma": 19,
        "challenge_rating": "14",
        "cr": 14,
        "senses": "darkvision 120 ft., passive Perception 17",
        "languages": "Deep Speech, Undercommon",
        "special_abilities": [
            {
                "name": "Negative Energy Cone",
                "desc": "Occhio centrale genera un cono di energia negativa da 45m. Chi muore nell'area si rianima immediatamente come zombi sotto il suo controllo."
            }
        ],
        "actions": [
            {
                "name": "Bite",
                "desc": "Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 14 (4d6) piercing damage."
            },
            {
                "name": "Eye Rays",
                "desc": "Spara 3 raggi della morte/paralisi/disintegrazione/paura/telecinesi/sonno tra i 10 disponibili con CD 17."
            }
        ],
        "legendary_actions": [
            {
                "name": "Eye Ray",
                "desc": "Usa un raggio oculare a caso."
            },
            {
                "name": "Move",
                "desc": "Vola fino a metà della sua velocità."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Mindwitness",
        "size": "Large",
        "type": "aberration",
        "alignment": "lawful evil",
        "armor_class": 15,
        "hit_points": 75,
        "hit_dice": "10d10 + 20",
        "speed": "0 ft., fly 20 ft. (hover)",
        "strength": 10,
        "dexterity": 14,
        "constitution": 14,
        "intelligence": 15,
        "wisdom": 15,
        "charisma": 10,
        "challenge_rating": "5",
        "cr": 5,
        "senses": "darkvision 120 ft., passive Perception 15",
        "languages": "Deep Speech, Undercommon, telepathy 600 ft.",
        "special_abilities": [
            {
                "name": "Telepathic Hub",
                "desc": "Funge da ripetitore per la mente alveare illithid con raggio di 180 metri."
            }
        ],
        "actions": [
            {
                "name": "Tentacles",
                "desc": "Melee Weapon Attack: +5 to hit, reach 9 ft. Hit: 20 (4d8 + 2) psychic damage."
            },
            {
                "name": "Eye Rays",
                "desc": "Spara 3 raggi oculari con CD 13 (Avversione, Paura, Psichico, Lentezza, Stordimento, Telecinesi)."
            }
        ],
        "source": "Volo's Guide to Monsters"
    },
    {
        "name": "Elder Brain",
        "size": "Large",
        "type": "aberration",
        "alignment": "lawful evil",
        "armor_class": 10,
        "hit_points": 210,
        "hit_dice": "20d10 + 100",
        "speed": "5 ft., swim 10 ft.",
        "strength": 15,
        "dexterity": 10,
        "constitution": 20,
        "intelligence": 21,
        "wisdom": 19,
        "charisma": 24,
        "challenge_rating": "14",
        "cr": 14,
        "senses": "blindsight 120 ft., passive Perception 19",
        "languages": "telepathy 5 miles, understands Common, Deep Speech, Undercommon",
        "special_abilities": [
            {
                "name": "Creature Sense",
                "desc": "Percepisce qualsiasi creatura con Int > 3 entro 8 km."
            },
            {
                "name": "Telepathic Hub",
                "desc": "Può connettere telepaticamente fino a 10 creature simultaneamente."
            }
        ],
        "actions": [
            {
                "name": "Tentacle",
                "desc": "Melee Weapon Attack: +7 to hit, reach 30 ft. Hit: 20 (4d8 + 2) bludgeoning plus grapple and 13 (3d8) psychic damage."
            },
            {
                "name": "Mind Blast (Recharge 5-6)",
                "desc": "Cono da 18m: TS Intelligenza CD 18 o 32 (5d10 + 5) danni psichici e stordito per 1 minuto."
            }
        ],
        "legendary_actions": [
            {
                "name": "Tentacle",
                "desc": "Effettua un attacco con tentacolo."
            },
            {
                "name": "Break Concentration",
                "desc": "Interrompe la concentrazione di un bersaglio con CD 18."
            }
        ],
        "source": "Volo's Guide to Monsters"
    },
    {
        "name": "Ulitharid",
        "size": "Large",
        "type": "aberration",
        "alignment": "lawful evil",
        "armor_class": 15,
        "hit_points": 127,
        "hit_dice": "17d10 + 34",
        "speed": "30 ft.",
        "strength": 15,
        "dexterity": 12,
        "constitution": 15,
        "intelligence": 21,
        "wisdom": 19,
        "charisma": 21,
        "challenge_rating": "9",
        "cr": 9,
        "senses": "darkvision 120 ft., passive Perception 18",
        "languages": "Deep Speech, Undercommon, telepathy 2 miles",
        "special_abilities": [
            {
                "name": "Magic Resistance",
                "desc": "Vantaggio ai TS contro incantesimi ed effetti magici."
            }
        ],
        "actions": [
            {
                "name": "Tentacles",
                "desc": "Melee Weapon Attack: +9 to hit, reach 10 ft. Hit: 27 (4d10 + 5) psychic damage and target is grappled and stunned."
            },
            {
                "name": "Extract Brain",
                "desc": "Melee Weapon Attack: +9 to hit against incapacitated target. Hit: 55 (10d10) piercing damage. Kills if reduced to 0 HP."
            },
            {
                "name": "Mind Blast (Recharge 5-6)",
                "desc": "Cono da 18m: TS Intelligenza CD 17 o 31 (4d12 + 5) danni psichici e stordito per 1 minuto."
            }
        ],
        "source": "Volo's Guide to Monsters"
    },
    {
        "name": "Alhoon",
        "size": "Medium",
        "type": "undead",
        "alignment": "neutral evil",
        "armor_class": 15,
        "hit_points": 120,
        "hit_dice": "16d8 + 48",
        "speed": "30 ft.",
        "strength": 11,
        "dexterity": 12,
        "constitution": 16,
        "intelligence": 19,
        "wisdom": 17,
        "charisma": 17,
        "challenge_rating": "10",
        "cr": 10,
        "senses": "truesight 120 ft., passive Perception 17",
        "languages": "Deep Speech, Undercommon, telepathy 120 ft.",
        "special_abilities": [
            {
                "name": "Magic Resistance",
                "desc": "Vantaggio ai TS contro la magia."
            },
            {
                "name": "Innate Spellcasting (Psionics)",
                "desc": "Lancia Globe of Invulnerability, Chain Lightning, Disintegrate, Wall of Force."
            }
        ],
        "actions": [
            {
                "name": "Chilling Grasp",
                "desc": "Melee Spell Attack: +8 to hit, reach 5 ft. Hit: 14 (4d6) cold damage."
            },
            {
                "name": "Mind Blast (Recharge 5-6)",
                "desc": "Cono da 18m: TS Intelligenza CD 16 o 22 (4d8 + 4) danni psichici e stordito per 1 minuto."
            }
        ],
        "source": "Volo's Guide to Monsters"
    },
    {
        "name": "Flumph",
        "size": "Small",
        "type": "aberration",
        "alignment": "lawful good",
        "armor_class": 12,
        "hit_points": 7,
        "hit_dice": "2d6",
        "speed": "5 ft., fly 30 ft.",
        "strength": 6,
        "dexterity": 15,
        "constitution": 10,
        "intelligence": 14,
        "wisdom": 14,
        "charisma": 11,
        "challenge_rating": "1/8",
        "cr": 0.125,
        "senses": "darkvision 60 ft., passive Perception 12",
        "languages": "understands Undercommon, telepathy 60 ft.",
        "special_abilities": [
            {
                "name": "Telepathic Cloaking",
                "desc": "Immune a letture del pensiero e percezioni telepatiche non volute."
            }
        ],
        "actions": [
            {
                "name": "Tendrils",
                "desc": "Melee Weapon Attack: +4 to hit, reach 5 ft. Hit: 4 (1d4 + 2) piercing plus 2 (1d4) acid damage."
            },
            {
                "name": "Stench Spray (1/Day)",
                "desc": "Spruzzo fetido in cono da 4.5m: TS Destrezza CD 10 o avvelenato per 1d4 ore."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Hook Horror",
        "size": "Large",
        "type": "monstrosity",
        "alignment": "neutral",
        "armor_class": 15,
        "hit_points": 75,
        "hit_dice": "10d10 + 20",
        "speed": "30 ft., climb 30 ft.",
        "strength": 18,
        "dexterity": 10,
        "constitution": 15,
        "intelligence": 6,
        "wisdom": 12,
        "charisma": 7,
        "challenge_rating": "3",
        "cr": 3,
        "senses": "blindsight 60 ft., darkvision 10 ft., passive Perception 13",
        "languages": "Hook Horror",
        "special_abilities": [
            {
                "name": "Echolocation",
                "desc": "Non può usare la vista cieca se assordato."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua due attacchi con gli uncini."
            },
            {
                "name": "Hook",
                "desc": "Melee Weapon Attack: +6 to hit, reach 10 ft. Hit: 11 (2d6 + 4) piercing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Nothic",
        "size": "Medium",
        "type": "aberration",
        "alignment": "neutral evil",
        "armor_class": 15,
        "hit_points": 45,
        "hit_dice": "6d8 + 18",
        "speed": "30 ft.",
        "strength": 14,
        "dexterity": 16,
        "constitution": 16,
        "intelligence": 13,
        "wisdom": 10,
        "charisma": 8,
        "challenge_rating": "2",
        "cr": 2,
        "senses": "truesight 120 ft., passive Perception 12",
        "languages": "Undercommon",
        "special_abilities": [
            {
                "name": "Keen Sight",
                "desc": "Vantaggio alle prove di Saggezza (Percezione) basate sulla vista."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua due attacchi con gli artigli."
            },
            {
                "name": "Claw",
                "desc": "Melee Weapon Attack: +4 to hit, reach 5 ft. Hit: 6 (1d6 + 3) slashing damage."
            },
            {
                "name": "Rotting Gaze",
                "desc": "Sguardo necrotico entro 9m: TS Costituzione CD 12 o 10 (3d6) danni necrotici."
            },
            {
                "name": "Weird Insight",
                "desc": "Contesa di Intuizione contro Inganno per carpire un segreto intimo della mente della vittima."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Grell",
        "size": "Medium",
        "type": "aberration",
        "alignment": "neutral evil",
        "armor_class": 12,
        "hit_points": 55,
        "hit_dice": "10d8 + 10",
        "speed": "10 ft., fly 30 ft. (hover)",
        "strength": 15,
        "dexterity": 14,
        "constitution": 13,
        "intelligence": 12,
        "wisdom": 11,
        "charisma": 9,
        "challenge_rating": "3",
        "cr": 3,
        "senses": "blindsight 60 ft., passive Perception 12",
        "languages": "Grell",
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua un attacco con tentacoli e uno con becco."
            },
            {
                "name": "Tentacles",
                "desc": "Melee Weapon Attack: +4 to hit, reach 10 ft. Hit: 7 (1d10 + 2) piercing plus 7 (2d6) poison damage and target is poisoned and paralyzed (DC 11 Con)."
            },
            {
                "name": "Beak",
                "desc": "Melee Weapon Attack: +4 to hit, reach 5 ft. Hit: 7 (2d4 + 2) piercing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Rust Monster",
        "size": "Medium",
        "type": "monstrosity",
        "alignment": "unaligned",
        "armor_class": 14,
        "hit_points": 27,
        "hit_dice": "5d8 + 5",
        "speed": "40 ft.",
        "strength": 13,
        "dexterity": 12,
        "constitution": 13,
        "intelligence": 2,
        "wisdom": 13,
        "charisma": 6,
        "challenge_rating": "1/2",
        "cr": 0.5,
        "senses": "darkvision 60 ft., passive Perception 11",
        "languages": "-",
        "special_abilities": [
            {
                "name": "Iron Scent",
                "desc": "Fiuta la presenza di metallo ferroso fino a 9 metri di distanza."
            },
            {
                "name": "Rust Metal",
                "desc": "Qualsiasi arma non magica di ferro o acciaio che colpisce il rugginofago subisce una penalità permanente di -1 fino a distruggersi a -5."
            }
        ],
        "actions": [
            {
                "name": "Bite",
                "desc": "Melee Weapon Attack: +3 to hit, reach 5 ft. Hit: 5 (1d8 + 1) piercing damage."
            },
            {
                "name": "Antennae",
                "desc": "Corrode e distrugge armature o scudi di metallo non magici (penalità cumulativa -1 alla CA finché non si distrugge)."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Peryton",
        "size": "Medium",
        "type": "monstrosity",
        "alignment": "chaotic evil",
        "armor_class": 13,
        "hit_points": 33,
        "hit_dice": "6d8 + 6",
        "speed": "20 ft., fly 60 ft.",
        "strength": 16,
        "dexterity": 12,
        "constitution": 13,
        "intelligence": 9,
        "wisdom": 12,
        "charisma": 10,
        "challenge_rating": "2",
        "cr": 2,
        "senses": "passive Perception 11",
        "languages": "understands Common and Elvish",
        "special_abilities": [
            {
                "name": "Flyby",
                "desc": "Non provoca attacchi d'opportunità quando vola fuori dalla portata nemica."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua un attacco con corna e uno con artigli."
            },
            {
                "name": "Gore",
                "desc": "Melee Weapon Attack: +5 to hit, reach 5 ft. Hit: 7 (1d8 + 3) piercing damage."
            },
            {
                "name": "Talons",
                "desc": "Melee Weapon Attack: +5 to hit, reach 5 ft. Hit: 8 (2d4 + 3) piercing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Gorgon",
        "size": "Large",
        "type": "monstrosity",
        "alignment": "unaligned",
        "armor_class": 19,
        "hit_points": 114,
        "hit_dice": "12d10 + 48",
        "speed": "40 ft.",
        "strength": 20,
        "dexterity": 11,
        "constitution": 18,
        "intelligence": 2,
        "wisdom": 12,
        "charisma": 7,
        "challenge_rating": "5",
        "cr": 5,
        "senses": "darkvision 60 ft., passive Perception 14",
        "languages": "-",
        "special_abilities": [
            {
                "name": "Trampling Charge",
                "desc": "Se si muove di almeno 6m prima di colpire con incornata, il bersaglio deve superare un TS su Forza CD 16 o cadere prono."
            }
        ],
        "actions": [
            {
                "name": "Gore",
                "desc": "Melee Weapon Attack: +8 to hit, reach 5 ft. Hit: 18 (2d12 + 5) piercing damage."
            },
            {
                "name": "Petrifying Breath (Recharge 5-6)",
                "desc": "Emette un cono da 9m di gas pietrificante: TS Costituzione CD 15 o pietrificato."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Thri-kreen",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "chaotic neutral",
        "armor_class": 15,
        "hit_points": 33,
        "hit_dice": "6d8 + 6",
        "speed": "40 ft.",
        "strength": 12,
        "dexterity": 15,
        "constitution": 13,
        "intelligence": 8,
        "wisdom": 12,
        "charisma": 7,
        "challenge_rating": "1",
        "cr": 1,
        "senses": "darkvision 60 ft., passive Perception 13",
        "languages": "Thri-kreen, telepathy 60 ft.",
        "special_abilities": [
            {
                "name": "Chameleon Carapace",
                "desc": "Vantaggio alle prove di Furtività per nascondersi."
            },
            {
                "name": "Standing Leap",
                "desc": "Salto in lungo fino a 9m, salto in alto fino a 4.5m."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua due attacchi con armi da mischia o a distanza."
            },
            {
                "name": "Gythka",
                "desc": "Melee Weapon Attack: +4 to hit, reach 5 ft. Hit: 6 (1d8 + 2) slashing damage."
            },
            {
                "name": "Chatkcha",
                "desc": "Ranged Weapon Attack: +4 to hit, range 30/120 ft. Hit: 5 (1d6 + 2) slashing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Githzerai Zerth",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "lawful neutral",
        "armor_class": 17,
        "hit_points": 84,
        "hit_dice": "13d8 + 26",
        "speed": "30 ft.",
        "strength": 13,
        "dexterity": 18,
        "constitution": 15,
        "intelligence": 16,
        "wisdom": 17,
        "charisma": 12,
        "challenge_rating": "6",
        "cr": 6,
        "senses": "passive Perception 16",
        "languages": "Gith",
        "special_abilities": [
            {
                "name": "Psychic Defense",
                "desc": "Aggiunge il modificatore di Saggezza alla sua CA quando non indossa armature."
            },
            {
                "name": "Innate Spellcasting (Psionics)",
                "desc": "Lancia See Invisibility, Feather Fall, Jump, Shield, Phantasmal Killer, Plane Shift."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua due attacchi a mani nude."
            },
            {
                "name": "Unarmed Strike",
                "desc": "Melee Weapon Attack: +7 to hit, reach 5 ft. Hit: 11 (2d6 + 4) bludgeoning plus 10 (3d6) psychic damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Blue Slaad",
        "size": "Large",
        "type": "aberration",
        "alignment": "chaotic neutral",
        "armor_class": 15,
        "hit_points": 123,
        "hit_dice": "13d10 + 52",
        "speed": "30 ft.",
        "strength": 20,
        "dexterity": 15,
        "constitution": 18,
        "intelligence": 7,
        "wisdom": 12,
        "charisma": 9,
        "challenge_rating": "7",
        "cr": 7,
        "senses": "darkvision 60 ft., passive Perception 11",
        "languages": "Slaad, telepathy 60 ft.",
        "special_abilities": [
            {
                "name": "Regeneration",
                "desc": "Recupera 10 PF all'inizio di ogni suo turno se ha almeno 1 PF."
            },
            {
                "name": "Magic Resistance",
                "desc": "Vantaggio ai TS contro la magia."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua un attacco col morso e due con gli artigli."
            },
            {
                "name": "Claw",
                "desc": "Melee Weapon Attack: +8 to hit, reach 5 ft. Hit: 12 (2d6 + 5) slashing damage and infects target with Chaos Phage (DC 15 Con)."
            },
            {
                "name": "Bite",
                "desc": "Melee Weapon Attack: +8 to hit, reach 5 ft. Hit: 12 (2d6 + 5) piercing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Green Slaad",
        "size": "Medium",
        "type": "aberration",
        "alignment": "chaotic neutral",
        "armor_class": 16,
        "hit_points": 127,
        "hit_dice": "15d8 + 60",
        "speed": "30 ft.",
        "strength": 18,
        "dexterity": 15,
        "constitution": 18,
        "intelligence": 11,
        "wisdom": 8,
        "charisma": 12,
        "challenge_rating": "8",
        "cr": 8,
        "senses": "darkvision 60 ft., passive Perception 9",
        "languages": "Slaad, telepathy 60 ft.",
        "special_abilities": [
            {
                "name": "Regeneration",
                "desc": "Recupera 10 PF all'inizio del suo turno."
            },
            {
                "name": "Shapechanger",
                "desc": "Può trasformarsi in un umanoide Piccolo o Medio mantenendo le proprie statistiche."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua due attacchi con bastone ferrato o con artigli e morso."
            },
            {
                "name": "Innate Spellcasting",
                "desc": "Lancia Fireball (8d6), Fear, Darkness, Detect Magic a volontà o 2/giorno."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Death Slaad",
        "size": "Medium",
        "type": "aberration",
        "alignment": "chaotic evil",
        "armor_class": 18,
        "hit_points": 170,
        "hit_dice": "20d8 + 80",
        "speed": "30 ft.",
        "strength": 20,
        "dexterity": 15,
        "constitution": 19,
        "intelligence": 15,
        "wisdom": 10,
        "charisma": 16,
        "challenge_rating": "10",
        "cr": 10,
        "senses": "darkvision 60 ft., passive Perception 14",
        "languages": "Slaad, telepathy 60 ft.",
        "special_abilities": [
            {
                "name": "Regeneration",
                "desc": "Recupera 10 PF all'inizio del suo turno."
            },
            {
                "name": "Magic Resistance",
                "desc": "Vantaggio ai TS contro la magia."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua tre attacchi con la sua grande spada o artigli."
            },
            {
                "name": "Greatsword",
                "desc": "Melee Weapon Attack: +9 to hit, reach 5 ft. Hit: 12 (2d6 + 5) slashing plus 7 (2d6) necrotic damage."
            },
            {
                "name": "Innate Spellcasting",
                "desc": "Lancia Cloudkill, Fireball, Fly, Invisibility, Plane Shift."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Monodrone",
        "size": "Small",
        "type": "construct",
        "alignment": "lawful neutral",
        "armor_class": 15,
        "hit_points": 5,
        "hit_dice": "1d6 + 2",
        "speed": "30 ft., fly 30 ft.",
        "strength": 10,
        "dexterity": 13,
        "constitution": 12,
        "intelligence": 4,
        "wisdom": 10,
        "charisma": 5,
        "challenge_rating": "1/8",
        "cr": 0.125,
        "senses": "truesight 120 ft., passive Perception 10",
        "languages": "Modron",
        "special_abilities": [
            {
                "name": "Axiomatic Mind",
                "desc": "Immune a qualsiasi effetto che ne alteri l'allineamento o ne controlli la mente."
            },
            {
                "name": "Disintegration",
                "desc": "Se muore, il suo corpo si disintegra in polvere lasciando solo le sue armi."
            }
        ],
        "actions": [
            {
                "name": "Dagger",
                "desc": "Melee Weapon Attack: +3 to hit, reach 5 ft. Hit: 3 (1d4 + 1) piercing damage."
            },
            {
                "name": "Javelin",
                "desc": "Ranged Weapon Attack: +3 to hit, range 30/120 ft. Hit: 4 (1d6 + 1) piercing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Pentadrone",
        "size": "Large",
        "type": "construct",
        "alignment": "lawful neutral",
        "armor_class": 16,
        "hit_points": 32,
        "hit_dice": "5d10 + 5",
        "speed": "40 ft.",
        "strength": 15,
        "dexterity": 14,
        "constitution": 12,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 13,
        "challenge_rating": "2",
        "cr": 2,
        "senses": "truesight 120 ft., passive Perception 12",
        "languages": "Modron",
        "special_abilities": [
            {
                "name": "Axiomatic Mind",
                "desc": "Mente incrollabile dell'ordine assoluto."
            },
            {
                "name": "Disintegration",
                "desc": "Si dissolve in polvere alla morte."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua cinque attacchi con i suoi bracci metallici."
            },
            {
                "name": "Arm",
                "desc": "Melee Weapon Attack: +4 to hit, reach 7 ft. Hit: 5 (1d6 + 2) bludgeoning damage."
            },
            {
                "name": "Paralysis Gas (Recharge 5-6)",
                "desc": "Soffia un cono da 9m di gas paralizzante: TS Costituzione CD 11 o paralizzato per 1 minuto."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Goristro",
        "size": "Huge",
        "type": "fiend (demon)",
        "alignment": "chaotic evil",
        "armor_class": 19,
        "hit_points": 310,
        "hit_dice": "23d12 + 161",
        "speed": "40 ft.",
        "strength": 25,
        "dexterity": 11,
        "constitution": 25,
        "intelligence": 6,
        "wisdom": 13,
        "charisma": 14,
        "challenge_rating": "17",
        "cr": 17,
        "senses": "darkvision 120 ft., passive Perception 17",
        "languages": "Abyssal",
        "special_abilities": [
            {
                "name": "Charge",
                "desc": "Se si muove di 4.5m prima di colpire con incornata, infligge 45 (7d10 + 7) danni extra."
            },
            {
                "name": "Siege Monster",
                "desc": "Infligge danni doppi a oggetti e strutture."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua tre attacchi: due pugni e un'incornata."
            },
            {
                "name": "Fist",
                "desc": "Melee Weapon Attack: +13 to hit, reach 10 ft. Hit: 20 (3d8 + 7) bludgeoning damage."
            },
            {
                "name": "Gore",
                "desc": "Melee Weapon Attack: +13 to hit, reach 10 ft. Hit: 45 (7d10 + 7) piercing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Marilith",
        "size": "Large",
        "type": "fiend (demon)",
        "alignment": "chaotic evil",
        "armor_class": 18,
        "hit_points": 189,
        "hit_dice": "18d10 + 90",
        "speed": "40 ft.",
        "strength": 18,
        "dexterity": 20,
        "constitution": 20,
        "intelligence": 18,
        "wisdom": 16,
        "charisma": 20,
        "challenge_rating": "16",
        "cr": 16,
        "senses": "truesight 120 ft., passive Perception 18",
        "languages": "Abyssal, telepathy 120 ft.",
        "special_abilities": [
            {
                "name": "Reactive",
                "desc": "Può compiere una reazione in ogni turno di combattimento (non solo una per round)."
            },
            {
                "name": "Magic Resistance",
                "desc": "Vantaggio ai TS contro incantesimi."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua sette attacchi: sei con le spade e uno con la coda."
            },
            {
                "name": "Longsword",
                "desc": "Melee Weapon Attack: +9 to hit, reach 5 ft. Hit: 13 (2d8 + 4) slashing damage."
            },
            {
                "name": "Tail",
                "desc": "Melee Weapon Attack: +9 to hit, reach 10 ft. Hit: 15 (2d10 + 4) bludgeoning plus grapple and restrain."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Nalfeshnee",
        "size": "Large",
        "type": "fiend (demon)",
        "alignment": "chaotic evil",
        "armor_class": 18,
        "hit_points": 184,
        "hit_dice": "16d10 + 96",
        "speed": "20 ft., fly 30 ft.",
        "strength": 21,
        "dexterity": 10,
        "constitution": 22,
        "intelligence": 19,
        "wisdom": 12,
        "charisma": 15,
        "challenge_rating": "13",
        "cr": 13,
        "senses": "truesight 120 ft., passive Perception 16",
        "languages": "Abyssal, telepathy 120 ft.",
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Usa Luce dell'Orrore ed effettua tre attacchi: un morso e due artigli."
            },
            {
                "name": "Horror Nimbus (Recharge 5-6)",
                "desc": "Emette luce magica caleidoscopica entro 4.5m: TS Saggezza CD 15 o spaventato per 1 minuto."
            },
            {
                "name": "Bite",
                "desc": "Melee Weapon Attack: +10 to hit, reach 5 ft. Hit: 32 (5d10 + 5) piercing damage."
            },
            {
                "name": "Claw",
                "desc": "Melee Weapon Attack: +10 to hit, reach 10 ft. Hit: 15 (3d6 + 5) slashing damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Barlgura",
        "size": "Large",
        "type": "fiend (demon)",
        "alignment": "chaotic evil",
        "armor_class": 15,
        "hit_points": 68,
        "hit_dice": "8d10 + 24",
        "speed": "40 ft., climb 40 ft.",
        "strength": 18,
        "dexterity": 15,
        "constitution": 16,
        "intelligence": 7,
        "wisdom": 14,
        "charisma": 9,
        "challenge_rating": "5",
        "cr": 5,
        "senses": "blindsight 30 ft., darkvision 120 ft., passive Perception 15",
        "languages": "Abyssal, telepathy 120 ft.",
        "special_abilities": [
            {
                "name": "Reckless",
                "desc": "All'inizio del turno può ottenere vantaggio a tutti gli attacchi con armi da mischia, concedendo vantaggio contro di sé."
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "desc": "Effettua tre attacchi: un morso e due pugni."
            },
            {
                "name": "Bite",
                "desc": "Melee Weapon Attack: +7 to hit, reach 5 ft. Hit: 11 (2d6 + 4) piercing damage."
            },
            {
                "name": "Fist",
                "desc": "Melee Weapon Attack: +7 to hit, reach 5 ft. Hit: 9 (1d10 + 4) bludgeoning damage."
            }
        ],
        "source": "Monster Manual"
    },
    {
        "name": "Chasme",
        "size": "Large",
        "type": "fiend (demon)",
        "alignment": "chaotic evil",
        "armor_class": 15,
        "hit_points": 84,
        "hit_dice": "13d10 + 13",
        "speed": "20 ft., fly 60 ft.",
        "strength": 15,
        "dexterity": 15,
        "constitution": 12,
        "intelligence": 6,
        "wisdom": 14,
        "charisma": 10,
        "challenge_rating": "6",
        "cr": 6,
        "senses": "blindsight 10 ft., darkvision 120 ft., passive Perception 15",
        "languages": "Abyssal, telepathy 120 ft.",
        "special_abilities": [
            {
                "name": "Drone",
                "desc": "Il suo ronzio incessante costringe le creature entro 9m a un TS Costituzione CD 12 o cadere addormentate per 10 minuti."
            }
        ],
        "actions": [
            {
                "name": "Proboscis",
                "desc": "Melee Weapon Attack: +5 to hit, reach 5 ft. Hit: 16 (4d6 + 2) piercing plus 24 (7d6) necrotic damage. Riduce i PF massimi."
            }
        ],
        "source": "Monster Manual"
    }
]

MONSTER_IT_TO_EN_EXPANSION = {
    "spettatore": "Spectator",
    "gauth": "Gauth",
    "tiranno della morte": "Death Tyrant",
    "testimone mentale": "Mindwitness",
    "gazer": "Gazer",
    "bacio della morte": "Death Kiss",
    "ulitharid": "Ulitharid",
    "cervello antico": "Elder Brain",
    "alhoon": "Alhoon",
    "flumph": "Flumph",
    "orrore uncinato": "Hook Horror",
    "nothic": "Nothic",
    "grell": "Grell",
    "rugginofago": "Rust Monster",
    "mostro rugginoso": "Rust Monster",
    "peryton": "Peryton",
    "gorgone": "Gorgon",
    "thri-kreen": "Thri-kreen",
    "githzerai zerth": "Githzerai Zerth",
    "slaad blu": "Blue Slaad",
    "slaad verde": "Green Slaad",
    "slaad della morte": "Death Slaad",
    "monodrone": "Monodrone",
    "pentadrone": "Pentadrone",
    "goristro": "Goristro",
    "marilith": "Marilith",
    "nalfeshnee": "Nalfeshnee",
    "barlgura": "Barlgura",
    "chasme": "Chasme"
}
