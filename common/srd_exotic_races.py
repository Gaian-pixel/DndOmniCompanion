"""
Catalogo completo delle 28+ Razze Esotiche e Mostruose Ufficiali D&D 5e (VGM, MToF, ERLW, GGtR, MOoT, WBtW, SCC, MotM).
Integrazione al 100% per DndOmniCompanion.
"""

ALL_EXOTIC_RACES_CATALOG = [
    {
        "name": "Aasimar",
        "name_en": "Aasimar",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Carisma": 2
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Celestiale"
        ],
        "description": "Portatori del sangue celestiale toccati dal potere dei Piani Superiori, gli aasimar nascono come campioni predestinati della virtù e della giustizia.",
        "traits": [
            {
                "name": "Scurovisione (Aasimar)",
                "desc": "Puoi vedere nella penombra entro 18m come se fosse luce intensa, e nell'oscurità come se fosse penombra."
            },
            {
                "name": "Resistenza Celestiale",
                "desc": "Hai resistenza ai danni necrotici e ai danni radiosi."
            },
            {
                "name": "Mani Guaritrici",
                "desc": "Come azione puoi toccare una creatura e farle recuperare un numero di punti ferita pari al tuo livello. Si ricarica con un riposo lungo."
            },
            {
                "name": "Luce Divina",
                "desc": "Conosci il trucchetto Luce, lanciandolo usando il Carisma."
            }
        ],
        "subraces": [
            {
                "name": "Aasimar Protettore",
                "ability_bonuses": {
                    "Saggezza": 1
                },
                "traits": [
                    {
                        "name": "Anima Radiosa",
                        "desc": "Dal 3° livello, come azione bonus sprigioni ali luminose per 1 minuto (volare 9m) e un attacco o incantesimo a turno infligge danni radiosi extra pari al tuo livello."
                    }
                ]
            },
            {
                "name": "Aasimar Flagellatore",
                "ability_bonuses": {
                    "Costituzione": 1
                },
                "traits": [
                    {
                        "name": "Consunzione Radiosa",
                        "desc": "Dal 3° livello, come azione bonus sprigioni energia solare ardente: alla fine di ogni tuo turno le creature entro 3m subiscono danni radiosi pari a metà del tuo livello."
                    }
                ]
            },
            {
                "name": "Aasimar Caduto",
                "ability_bonuses": {
                    "Forza": 1
                },
                "traits": [
                    {
                        "name": "Sudario Necrotico",
                        "desc": "Dal 3° livello, trasformazione terrificante con ali scheletriche: le creature entro 3m devono superare un TS Carisma o essere spaventate, e i tuoi attacchi infliggono danni necrotici extra pari al tuo livello."
                    }
                ]
            }
        ]
    },
    {
        "name": "Goliath",
        "name_en": "Goliath",
        "source": "Elemental Evil Player's Companion / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Forza": 2,
            "Costituzione": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Gigante"
        ],
        "description": "Giganteschi nomadi delle cime innevate, i goliath incarnano la potenza selvaggia della roccia e la tenacia indomita delle montagne.",
        "traits": [
            {
                "name": "Resistenza della Pietra",
                "desc": "Quando subisci danni, puoi usare la tua reazione per tirare 1d12 + mod. Costituzione e ridurre il danno subito di quel totale. Si ricarica con un riposo breve o lungo."
            },
            {
                "name": "Corporatura Possente (Goliath)",
                "desc": "Sei considerato di una taglia più grande per determinare la tua capacità di carico e il peso che puoi spingere, trascinare o sollevare."
            },
            {
                "name": "Nato dalle Alture",
                "desc": "Sei naturalmente adattato alle altitudini superiori ai 6.000 metri ed hai resistenza ai danni da freddo."
            },
            {
                "name": "Atleta Naturale",
                "desc": "Hai competenza nell'abilità Atletica."
            }
        ]
    },
    {
        "name": "Tabaxi",
        "name_en": "Tabaxi",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Destrezza": 2,
            "Carisma": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Una a scelta"
        ],
        "description": "Umanoidi felini agili e curiosi, amanti dei segreti antichi, delle storie dimenticate e dei tesori esotici.",
        "traits": [
            {
                "name": "Scurovisione (Tabaxi)",
                "desc": "Visione felina nella penombra entro 18m."
            },
            {
                "name": "Scatto Felino",
                "desc": "In combattimento puoi raddoppiare la tua velocità di movimento per il turno corrente. Una volta usato, non puoi riutilizzarlo finché non trascorri un turno muovendoti di 0 metri."
            },
            {
                "name": "Artigli del Gatto",
                "desc": "I tuoi artigli sono armi naturali con cui sferri attacchi disarmati (1d6 + Des tagliente) e possiedi una velocità di scalare pari a 6 metri."
            },
            {
                "name": "Talento Felino",
                "desc": "Competenza nelle abilità Percezione e Furtività."
            }
        ]
    },
    {
        "name": "Firbolg",
        "name_en": "Firbolg",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Saggezza": 2,
            "Forza": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Elfico",
            "Gigante"
        ],
        "description": "Antichi guardiani dei boschi primordiali dotati di magia druidica naturale e di un profondo legame con la fauna e la flora selvaggia.",
        "traits": [
            {
                "name": "Magia dei Firbolg",
                "desc": "Puoi lanciare Rileva Magia e Camuffare Se Stesso (puoi sembrare fino a 90 cm più basso) usando la Saggezza."
            },
            {
                "name": "Passo Nascosto",
                "desc": "Come azione bonus puoi diventare magicamente invisibile fino all'inizio del tuo prossimo turno o finché non attacchi o lanci un incantesimo."
            },
            {
                "name": "Corporatura Possente (Firbolg)",
                "desc": "Capacità di carico calcolata come una creatura di taglia Grande."
            },
            {
                "name": "Discorso della Selva",
                "desc": "Puoi comunicare idee semplici a bestie e piante, con vantaggio alle prove di Carisma per influenzarle."
            }
        ]
    },
    {
        "name": "Tritone",
        "name_en": "Triton",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Forza": 1,
            "Costituzione": 1,
            "Carisma": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Primordiale (Aquan)"
        ],
        "description": "Nobili protettori delle profondità oceaniche, maestri della magia delle maree e guardiani contro i mostri degli abissi marini.",
        "traits": [
            {
                "name": "Anfibio",
                "desc": "Puoi respirare sia aria che acqua."
            },
            {
                "name": "Velocità di Nuotare",
                "desc": "Hai una velocità di nuotare di 9 metri."
            },
            {
                "name": "Controllo dell'Aria e dell'Acqua",
                "desc": "Puoi lanciare Fog Cloud (1° liv), Gust of Wind (3° liv) e Wall of Water (5° liv)."
            },
            {
                "name": "Emissario del Mare",
                "desc": "Puoi comunicare telepaticamente con qualsiasi creatura marina che possieda una velocità di nuoto."
            },
            {
                "name": "Guardiano delle Profondità",
                "desc": "Resistenza ai danni da freddo e immunità agli effetti negativi dell'alta pressione subacquea."
            }
        ]
    },
    {
        "name": "Kenku",
        "name_en": "Kenku",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Destrezza": 2,
            "Saggezza": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Auran (solo tramite Mimetismo)"
        ],
        "description": "Corvidi umanoidi privi di ali, dotati di una prodigiosa memoria fotografica e di un mimetismo sonoro perfetto.",
        "traits": [
            {
                "name": "Mimetismo Vocale",
                "desc": "Puoi imitare alla perfezione qualsiasi suono o voce che tu abbia mai udito. Chi ascolta deve superare Saggezza (Intuizione) CD 8 + comp + Carisma per scoprire l'inganno."
            },
            {
                "name": "Addestramento Kenku",
                "desc": "Competenza a scelta in due tra: Acrobazia, Inganno, Furtività, Rapidità di Mano."
            },
            {
                "name": "Falsario Esperto",
                "desc": "Vantaggio a tutte le prove per creare falsi o duplicare documenti grafici e calligrafie altrui."
            }
        ]
    },
    {
        "name": "Tortle",
        "name_en": "Tortle",
        "source": "The Tortle Package / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Forza": 2,
            "Saggezza": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Aquan"
        ],
        "description": "Rettili umanoidi simili a tartarughe giganti, viaggiatori pacifici dotati di una corazza ossea naturale impenetrabile.",
        "traits": [
            {
                "name": "Corazza Naturale (Tortle)",
                "desc": "La tua corazza ti conferisce una Classe Armatura base di 17 (non puoi indossare armature, ma puoi usare uno scudo)."
            },
            {
                "name": "Ritirarsi nel Guscio",
                "desc": "Come azione puoi ritirarti nel guscio: ottieni +4 alla CA e vantaggio ai tiri salvezza su Forza e Costituzione, ma la tua velocità diventa 0 e sei prono."
            },
            {
                "name": "Trattenere il Respiro",
                "desc": "Puoi trattenere il respiro fino a 1 ora continua."
            },
            {
                "name": "Artigli",
                "desc": "Attacchi disarmati da 1d6 + Forza danni taglienti."
            },
            {
                "name": "Intuizione della Natura",
                "desc": "Competenza a scelta in una tra: Addestrare Animali, Medicina, Natura, Percezione, Sopravvivenza."
            }
        ]
    },
    {
        "name": "Lucertoloide",
        "name_en": "Lizardfolk",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Costituzione": 2,
            "Saggezza": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Draconico"
        ],
        "description": "Rettiliani pragmatici e letali provenienti da paludi selvagge, maestri nella caccia, nell'artigianato osseo e nel nuoto.",
        "traits": [
            {
                "name": "Morso (Lucertoloide)",
                "desc": "Attacco naturale disarmato che infligge 1d6 + Forza danni perforanti."
            },
            {
                "name": "Nutrimento Vorace",
                "desc": "Come azione bonus puoi sferrare un attacco di morso e guadagnare punti ferita temporanei pari al tuo modificatore di Costituzione (ricarica riposo breve/lungo)."
            },
            {
                "name": "Artigiano della Natura",
                "desc": "Durante un riposo breve puoi intagliare ossa e pelli per creare scudi, clave, giavellotti, pugnali o dardi."
            },
            {
                "name": "Pelle Corazzata",
                "desc": "CA base pari a 13 + modificatore di Destrezza se non indossi armatura."
            },
            {
                "name": "Nuotatore d'Acqua Dolce",
                "desc": "Velocità di nuotare pari a 9 metri e trattieni il respiro fino a 15 minuti."
            }
        ]
    },
    {
        "name": "Coboldo",
        "name_en": "Kobold",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Piccola",
        "speed": 9,
        "ability_bonuses": {
            "Destrezza": 2
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Draconico"
        ],
        "description": "Piccoli rettiliani furbi legati alla stirpe dei draghi, maestri del lavoro di squadra e delle trappole sotterranee.",
        "traits": [
            {
                "name": "Tattiche di Branco",
                "desc": "Hai vantaggio al tiro per colpire contro una creatura se almeno uno dei tuoi alleati si trova entro 1.5m da essa e non è incapacitato."
            },
            {
                "name": "Supplica, Piagnucola e Striscia",
                "desc": "Come azione distrai i nemici: i tuoi alleati ottengono vantaggio ai tiri per colpire contro i nemici entro 3m da te fino alla fine del tuo prossimo turno."
            },
            {
                "name": "Sensibilità alla Luce del Sole",
                "desc": "Svantaggio ai tiri per colpire e alle prove di Percezione basate sulla vista quando sei esposto alla luce diretta del sole."
            }
        ]
    },
    {
        "name": "Goblin",
        "name_en": "Goblin",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Piccola",
        "speed": 9,
        "ability_bonuses": {
            "Destrezza": 2,
            "Costituzione": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Goblin"
        ],
        "description": "Piccoli umanoidi veloci e opportunisti, capaci di fuggire con agilità felina e colpire con ferocia nemici molto più grandi di loro.",
        "traits": [
            {
                "name": "Fuga Agile",
                "desc": "Puoi compiere l'azione di Disimpegno o Nascondersi come azione bonus in ciascuno dei tuoi turni."
            },
            {
                "name": "Furia del Piccolo",
                "desc": "Quando danneggi una creatura di taglia superiore alla tua, puoi infliggerle danni extra pari al tuo livello totale. Ricarica con un riposo breve o lungo."
            }
        ]
    },
    {
        "name": "Hobgoblin",
        "name_en": "Hobgoblin",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Costituzione": 2,
            "Intelligenza": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Goblin"
        ],
        "description": "Guerrieri marziali orgogliosi, disciplinati e feroci, guidati da una ferrea gerarchia militare e da un infallibile senso dell'onore di battaglia.",
        "traits": [
            {
                "name": "Addestramento Marziale degli Hobgoblin",
                "desc": "Competenza in due armi marziali a scelta e nelle armature leggere."
            },
            {
                "name": "Salvare la Faccia",
                "desc": "Se fallisci un tiro per colpire, una prova di caratteristica o un tiro salvezza, puoi aggiungere un bonus pari al numero di alleati che vedi entro 9m (massimo +5). Ricarica riposo breve/lungo."
            }
        ]
    },
    {
        "name": "Bugbear",
        "name_en": "Bugbear",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Forza": 2,
            "Destrezza": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Goblin"
        ],
        "description": "Goblinoidi colossali e silenziosi, cacciatori d'imboscata dalle braccia straordinariamente lunghe capaci di spezzare le difese a sorpresa.",
        "traits": [
            {
                "name": "Braccia Lunghe",
                "desc": "Quando effettui un attacco da mischia nel tuo turno, la tua portata è di 1.5m maggiore del normale (3 metri totali)."
            },
            {
                "name": "Corporatura Possente (Bugbear)",
                "desc": "Calcoli la capacità di carico come taglia Grande."
            },
            {
                "name": "Furtivo",
                "desc": "Competenza nell'abilità Furtività."
            },
            {
                "name": "Attacco a Sorpresa",
                "desc": "Se colpisci una creatura sorpresa nel primo turno di combattimento, infliggi 2d6 danni extra con l'attacco."
            }
        ]
    },
    {
        "name": "Orco",
        "name_en": "Orc",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Forza": 2,
            "Costituzione": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Orchesco"
        ],
        "description": "Fieri guerrieri dotati della forza selvaggia del dio Gruumsh, capaci di caricare con furia indomabile verso le linee nemiche.",
        "traits": [
            {
                "name": "Aggressivo",
                "desc": "Come azione bonus puoi muoverti fino alla tua velocità verso una creatura ostile che puoi vedere."
            },
            {
                "name": "Tenacia Implacabile",
                "desc": "Quando vieni ridotto a 0 punti ferita ma non ucciso sul colpo, scendi invece a 1 punto ferita. Ricarica con un riposo lungo."
            },
            {
                "name": "Corporatura Possente (Orco)",
                "desc": "Capacità di carico calcolata come taglia Grande."
            },
            {
                "name": "Intimidazione Istintiva",
                "desc": "Competenza nell'abilità Intimidire."
            }
        ]
    },
    {
        "name": "Yuan-ti Purosangue",
        "name_en": "Yuan-ti Pureblood",
        "source": "Volo's Guide to Monsters / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Carisma": 2,
            "Intelligenza": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Abissale",
            "Draconico"
        ],
        "description": "Eredi di un antico impero serpente, insidiosi oratori dotati di sangue velenoso e di una straordinaria resistenza alla magia.",
        "traits": [
            {
                "name": "Resistenza Magica (Yuan-ti)",
                "desc": "Hai vantaggio a tutti i tiri salvezza contro incantesimi e altri effetti magici."
            },
            {
                "name": "Immunità al Veleno (Yuan-ti)",
                "desc": "Immune a tutti i danni da veleno e alla condizione avvelenato."
            },
            {
                "name": "Lancio Innato",
                "desc": "Conosci il trucchetto Poison Spray a volontà, Animal Friendship (solo serpenti) a volontà, e Suggestion dal 3° livello (1/giorno)."
            }
        ]
    },
    {
        "name": "Genasi dell'Aria",
        "name_en": "Air Genasi",
        "source": "Elemental Evil / Multiverse",
        "size": "Media",
        "speed": 10.5,
        "ability_bonuses": {
            "Costituzione": 2,
            "Destrezza": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Primordiale"
        ],
        "description": "Toccati dalla brezza eterna del Piano Elementale dell'Aria, agili come venti d'alta quota.",
        "traits": [
            {
                "name": "Respiro Infinito",
                "desc": "Puoi trattenere il respiro a tempo indefinito finché non sei incapacitato."
            },
            {
                "name": "Fusione con il Vento",
                "desc": "Puoi lanciare Levitate una volta al giorno senza componenti materiali."
            },
            {
                "name": "Passo dell'Aria",
                "desc": "Velocità di movimento di 10.5 metri."
            }
        ]
    },
    {
        "name": "Genasi della Terra",
        "name_en": "Earth Genasi",
        "source": "Elemental Evil / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Costituzione": 2,
            "Forza": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Primordiale"
        ],
        "description": "Figli della roccia granitica e dei metalli preziosi del Piano della Terra.",
        "traits": [
            {
                "name": "Camminare sulla Terra",
                "desc": "Puoi muoverti su terreni difficili fatti di terra o roccia senza spendere movimento extra."
            },
            {
                "name": "Fusione con la Pietra",
                "desc": "Puoi lanciare Pass Without Trace e Blade Ward usando la Costituzione."
            }
        ]
    },
    {
        "name": "Genasi del Fuoco",
        "name_en": "Fire Genasi",
        "source": "Elemental Evil / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Costituzione": 2,
            "Intelligenza": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Primordiale"
        ],
        "description": "Ardentemente vivi, con occhi fiammeggianti e capigliatura che danza come brace vivente.",
        "traits": [
            {
                "name": "Resistenza al Fuoco",
                "desc": "Hai resistenza ai danni da fuoco."
            },
            {
                "name": "Portatore della Fiamma",
                "desc": "Conosci il trucchetto Produce Flame. Dal 3° livello puoi lanciare Burning Hands (1 volta per riposo lungo)."
            }
        ]
    },
    {
        "name": "Genasi dell'Acqua",
        "name_en": "Water Genasi",
        "source": "Elemental Evil / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Costituzione": 2,
            "Saggezza": 1
        },
        "darkvision": 18,
        "languages": [
            "Comune",
            "Primordiale"
        ],
        "description": "Pelle sfumata d'azzurro e capelli ondeggianti come alghe, maestri dell'acqua e del ghiaccio.",
        "traits": [
            {
                "name": "Anfibio",
                "desc": "Puoi respirare sia aria che acqua."
            },
            {
                "name": "Velocità di Nuotare",
                "desc": "Velocità di nuotare di 9 metri."
            },
            {
                "name": "Resistenza all'Acido",
                "desc": "Hai resistenza ai danni da acido."
            },
            {
                "name": "Richiamo dell'Onda",
                "desc": "Conosci Shape Water, Create or Destroy Water e Water Walk."
            }
        ]
    },
    {
        "name": "Forgiato",
        "name_en": "Warforged",
        "source": "Eberron: Rising from the Last War",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Costituzione": 2,
            "Una a scelta": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Una a scelta"
        ],
        "description": "Costrutti viventi forgiati in legnoscuro, pietra e acciaio per la Grande Guerra, dotati di una coscienza senziente e di un'incredibile resilienza biologico-meccanica.",
        "traits": [
            {
                "name": "Resilienza del Costrutto",
                "desc": "Vantaggio ai TS contro veleno, resistenza al veleno, non hai bisogno di mangiare, bere o respirare, e sei immune a malattie e sonno magico."
            },
            {
                "name": "Riposo Sentinella",
                "desc": "Non dormi: per un riposo lungo trascorri 6 ore in stato inattivo ma vigile, mantenendo la piena consapevolezza sensoriale."
            },
            {
                "name": "Protezione Integrata",
                "desc": "Ottieni un bonus permanente di +1 alla Classe Armatura. Impieghi 1 ora per incorporare un'armatura nel tuo corpo."
            },
            {
                "name": "Specializzazione Integrata",
                "desc": "Competenza in un'abilità e uno strumento artigianale a scelta."
            }
        ]
    },
    {
        "name": "Cangiante",
        "name_en": "Changeling",
        "source": "Eberron / Multiverse",
        "size": "Media o Piccola",
        "speed": 9,
        "ability_bonuses": {
            "Carisma": 2,
            "Una a scelta": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Due a scelta"
        ],
        "description": "Esseri mutaforma capaci di alterare voce, sesso e fattezze all'istante per infiltrarsi in qualsiasi società mortale.",
        "traits": [
            {
                "name": "Istinto del Cangiante",
                "desc": "Competenza in due abilità a scelta tra Inganno, Intuizione, Intimidire e Persuasione."
            },
            {
                "name": "Mutaforma Istintivo",
                "desc": "Come azione puoi mutare il tuo aspetto fisico e la tua voce in qualsiasi razza umanoide conosciuta (mantenendo le tue statistiche)."
            }
        ]
    },
    {
        "name": "Kalashtar",
        "name_en": "Kalashtar",
        "source": "Eberron: Rising from the Last War",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Saggezza": 2,
            "Carisma": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Quori"
        ],
        "description": "Umani legati a spiriti della luce onirica provenienti dal piano dei sogni Dal Quor, telepati nati dotati di uno scudo mentale incrollabile.",
        "traits": [
            {
                "name": "Telepatia a Doppio Spirito",
                "desc": "Puoi parlare telepaticamente con qualsiasi creatura entro 3m per livello."
            },
            {
                "name": "Mente Disciplinata",
                "desc": "Hai resistenza ai danni psichici e vantaggio a tutti i tiri salvezza su Saggezza."
            },
            {
                "name": "Immune agli Incubi",
                "desc": "Immune a effetti che inducono sogni forzati o incantesimi come Dream."
            }
        ]
    },
    {
        "name": "Morfico",
        "name_en": "Shifter",
        "source": "Eberron / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Una caratteristica +2, una +1": 0
        },
        "darkvision": 18,
        "languages": [
            "Comune"
        ],
        "description": "Discendenti dei licantropi, capaci di manifestare le zanne, gli artigli o la pelle coriacea della bestia interiore in combattimento.",
        "traits": [
            {
                "name": "Scurovisione (Morfico)",
                "desc": "Vista nella penombra fino a 18 metri."
            },
            {
                "name": "Trasformazione Bestiale (Shifting)",
                "desc": "Come azione bonus assumi tratti bestiali per 1 minuto, guadagnando PF temporanei pari a livello + mod. Costituzione e il tratto speciale della tua sottorazza (Beasthide, Longtooth, Swiftstride o Wildhunt). Ricarica con riposo breve/lungo."
            }
        ]
    },
    {
        "name": "Fata",
        "name_en": "Fairy",
        "source": "The Wild Beyond the Witchlight / Multiverse",
        "size": "Piccola",
        "speed": 9,
        "ability_bonuses": {
            "Tre caratteristiche +1": 0
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Silvano"
        ],
        "description": "Creature fatate alate native della Selva Fatata, giocose, magiche e capaci di fluttuare nell'aria fin dalla nascita.",
        "traits": [
            {
                "name": "Tipo Creatura: Folletto",
                "desc": "Sei considerato un Folletto anziché un Umanoide."
            },
            {
                "name": "Volo Fatato",
                "desc": "Possiedi una velocità di volare pari alla tua velocità sul terreno (non utilizzabile con armature medie o pesanti)."
            },
            {
                "name": "Magia Fatata",
                "desc": "Conosci il trucchetto Druidcraft, e puoi lanciare Faerie Fire (1° livello) ed Enlarge/Reduce (3° livello)."
            }
        ]
    },
    {
        "name": "Leporide",
        "name_en": "Harengon",
        "source": "The Wild Beyond the Witchlight / Multiverse",
        "size": "Media o Piccola",
        "speed": 9,
        "ability_bonuses": {
            "Una caratteristica +2, una +1": 0
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Silvano"
        ],
        "description": "Umanoidi leporini veloci e scattanti originari della Selva Fatata, dotati di riflessi prodigiosi e di salti formidabili.",
        "traits": [
            {
                "name": "Iniziativa Leporina",
                "desc": "Aggiungi il tuo bonus di competenza a tutti i tuoi tiri di iniziativa."
            },
            {
                "name": "Sensi Vigili",
                "desc": "Competenza nell'abilità Percezione."
            },
            {
                "name": "Balzo del Coniglio",
                "desc": "Come azione bonus puoi compiere un balzo straordinario pari a 5 volte il tuo bonus di competenza senza provocare attacchi d'opportunità."
            }
        ]
    },
    {
        "name": "Owlin",
        "name_en": "Owlin",
        "source": "Strixhaven: A Curriculum of Chaos",
        "size": "Media o Piccola",
        "speed": 9,
        "ability_bonuses": {
            "Una caratteristica +2, una +1": 0
        },
        "darkvision": 36,
        "languages": [
            "Comune",
            "Una a scelta"
        ],
        "description": "Umanoidi gufo saggi e silenziosi, maestri del volo notturno e dell'osservazione arcana.",
        "traits": [
            {
                "name": "Volo Silenzioso",
                "desc": "Possiedi una velocità di volare pari alla tua velocità di camminare (non utilizzabile con armature medie o pesanti)."
            },
            {
                "name": "Scurovisione Superiore (Owlin)",
                "desc": "Vedi nella penombra e oscurità fino a 36 metri."
            },
            {
                "name": "Piumaggio Furtivo",
                "desc": "Competenza nell'abilità Furtività."
            }
        ]
    },
    {
        "name": "Centauro",
        "name_en": "Centaur",
        "source": "Guildmasters' Guide to Ravnica / Multiverse",
        "size": "Media",
        "speed": 12,
        "ability_bonuses": {
            "Forza": 2,
            "Saggezza": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Silvano"
        ],
        "description": "Fieri guerrieri metà umani e metà cavalli nativi delle vaste pianure, velocissimi e devastanti nella carica a zoccoli ferrati.",
        "traits": [
            {
                "name": "Tipo Creatura: Fey",
                "desc": "Sei una fata (Fey), non un umanoide."
            },
            {
                "name": "Velocità Equina",
                "desc": "Velocità sul terreno di 12 metri."
            },
            {
                "name": "Zoccoli",
                "desc": "Armi naturali disarmate: 1d4 + Forza danni contundenti."
            },
            {
                "name": "Carica dei Centauri",
                "desc": "Se ti muovi di almeno 9m prima di colpire con zoccoli o arma da mischia, puoi sferrare un attacco con zoccoli come azione bonus."
            }
        ]
    },
    {
        "name": "Minotauro",
        "name_en": "Minotaur",
        "source": "Guildmasters' Guide to Ravnica / Multiverse",
        "size": "Media",
        "speed": 9,
        "ability_bonuses": {
            "Forza": 2,
            "Costituzione": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Minotauro"
        ],
        "description": "Guerrieri taurini colossali dotati di possenti corna, orientamento labirintico infallibile e forza bruta devastante.",
        "traits": [
            {
                "name": "Incornata",
                "desc": "Arma naturale da mischia: 1d6 + Forza danni perforanti."
            },
            {
                "name": "Carica Incornante",
                "desc": "Se scatti per almeno 6m in linea retta puoi attaccare con le corna come azione bonus."
            },
            {
                "name": "Spinta con le Corna",
                "desc": "Quando colpisci una creatura puoi spingerla indietro fino a 3m se fallisce un TS su Forza CD 8 + comp + Forza."
            }
        ]
    },
    {
        "name": "Satiro",
        "name_en": "Satyr",
        "source": "Mythic Odysseys of Theros / Multiverse",
        "size": "Media",
        "speed": 10.5,
        "ability_bonuses": {
            "Carisma": 2,
            "Destrezza": 1
        },
        "darkvision": 0,
        "languages": [
            "Comune",
            "Silvano"
        ],
        "description": "Figli della gioia e della musica della Selva Fatata e di Theros, caprini agili e festosi protetti da un'innata resistenza alla magia.",
        "traits": [
            {
                "name": "Tipo Creatura: Fey",
                "desc": "Sei considerato Folletto (Fey)."
            },
            {
                "name": "Resistenza Magica (Satiro)",
                "desc": "Hai vantaggio a tutti i tiri salvezza contro incantesimi ed effetti magici."
            },
            {
                "name": "Velocità del Satiro",
                "desc": "Velocità sul terreno di 10.5 metri."
            },
            {
                "name": "Incornata",
                "desc": "Attacco con le corna: 1d4 + Forza danni contundenti."
            },
            {
                "name": "Festa e Musica",
                "desc": "Competenza nelle abilità Intrattenere e Persuasione, oltre a uno strumento musicale a scelta."
            }
        ]
    }
]
