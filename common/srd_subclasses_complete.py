"""
Catalogo completo delle 117 Sottoclassi Ufficiali D&D 5e (Tutti i 13 alberi di classe al 100%).
PHB, DMG, XGtE, TCoE, SCAG, VRGtR, EGtW, FTD, Dragonlance.
Integrazione seamless offline al 100% per DndOmniCompanion.
"""

ALL_OFFICIAL_SUBCLASSES = [
    {
        "name": "Alchimista (Alchemist)",
        "name_en": "Alchemist",
        "class_name": "Artefice",
        "source": "Tasha's Cauldron of Everything",
        "description": "Maestro delle misture e degli elisir arcani, cura ferite e potenzia gli alleati attraverso reazioni chimico-magiche prodigiose.",
        "features": [
            {
                "level": 3,
                "name": "Strumenti del Mestiere (Alchimista)",
                "desc": "Competenza negli strumenti da alchimista; crei elisir sperimentali a ogni riposo lungo."
            },
            {
                "level": 3,
                "name": "Elisir Sperimentale",
                "desc": "Crei elisir che conferiscono guarigione, velocità, volo, trasformazione o benedizione."
            },
            {
                "level": 5,
                "name": "Trattamento Alchemico",
                "desc": "Aggiungi il tuo modificatore di Intelligenza ai danni o alle cure da incantesimi di acido, fuoco, necrotico o veleno."
            },
            {
                "level": 9,
                "name": "Elisir Ristoratore",
                "desc": "Chi beve il tuo elisir guadagna PF temporanei pari a 2d6 + mod Int e rimuove condizioni debilitanti."
            },
            {
                "level": 15,
                "name": "Maestria Chimica",
                "desc": "Resistenza ad acido e veleno, immunità ad avvelenamento e puoi lanciare Guarigione e Raggio della Morte senza slot."
            }
        ]
    },
    {
        "name": "Armaiolo (Armorer)",
        "name_en": "Armorer",
        "class_name": "Artefice",
        "source": "Tasha's Cauldron of Everything",
        "description": "Modifica la propria armatura trasformandola in una seconda pelle tecnologica corazzata, commutabile tra Guardiano possente o Infiltratore furtivo.",
        "features": [
            {
                "level": 3,
                "name": "Strumenti e Armatura Arcana",
                "desc": "Indossi qualsiasi armatura pesante senza requisiti di Forza e non può esserti rimossa contro la tua volontà."
            },
            {
                "level": 3,
                "name": "Modello di Armatura",
                "desc": "Scegli Guardiano (Pugni di Tuono e Campo Difensivo) o Infiltratore (Dardo Fulminante e Movimento Veloce)."
            },
            {
                "level": 5,
                "name": "Attacco Extra (Armaiolo)",
                "desc": "Puoi attaccare due volte anziché una quando usi l'azione di Attacco."
            },
            {
                "level": 9,
                "name": "Modifiche dell'Armatura",
                "desc": "L'armatura conta come quattro oggetti separati per le infusioni (elmo, pettorale, stivali, arma)."
            },
            {
                "level": 15,
                "name": "Armatura Perfezionata",
                "desc": "Potenziamenti avanzati: Guardiano tira i nemici con gravità magnetica; Infiltratore rilascia bagliori di luce e amplifica i danni."
            }
        ]
    },
    {
        "name": "Artigliere (Artillerist)",
        "name_en": "Artillerist",
        "class_name": "Artefice",
        "source": "Tasha's Cauldron of Everything",
        "description": "Specialista dell'artiglieria magica a distanza, schiera torrette magiche ambulanti ed evoca bacchette d'assalto devastanti.",
        "features": [
            {
                "level": 3,
                "name": "Cannone Arcano",
                "desc": "Come azione crei un cannone magico Piccolo o Minuscolo (Lanciafiamme, Balista di Forza o Protettore con PF temporanei)."
            },
            {
                "level": 5,
                "name": "Arma da Fuoco Arcana",
                "desc": "Trasformi una bacchetta o bastone in arma da fuoco, aggiungendo 1d8 ai danni degli incantesimi dell'artefice."
            },
            {
                "level": 9,
                "name": "Posizione Esplosiva",
                "desc": "I tuoi cannoni infliggono 1d8 danni extra e possono autodistruggersi infliggendo 3d8 danni da forza."
            },
            {
                "level": 15,
                "name": "Comando Rafforzato",
                "desc": "Puoi schierare due cannoni contemporaneamente e forniscono mezza copertura agli alleati vicini."
            }
        ]
    },
    {
        "name": "Fabbro da Battaglia (Battle Smith)",
        "name_en": "Battle Smith",
        "class_name": "Artefice",
        "source": "Tasha's Cauldron of Everything",
        "description": "Ingegnere guerriero che combatte in prima linea affiancato da un fedele Difensore d'Acciaio a quattro zampe.",
        "features": [
            {
                "level": 3,
                "name": "Addestramento da Battaglia",
                "desc": "Competenza nelle armi marziali e usi l'Intelligenza per i tiri per colpire e per i danni con armi magiche."
            },
            {
                "level": 3,
                "name": "Difensore d'Acciaio",
                "desc": "Evochi un leale costrutto quadrupede che agisce subito dopo di te e protegge gli alleati con reazioni difensive."
            },
            {
                "level": 5,
                "name": "Attacco Extra (Fabbro da Battaglia)",
                "desc": "Puoi attaccare due volte a ogni turno."
            },
            {
                "level": 9,
                "name": "Scarica Arcana",
                "desc": "Quando colpisci puoi canalizzare energia curando il difensore o un alleato per 2d6 o infliggendo 2d6 danni da forza extra."
            },
            {
                "level": 15,
                "name": "Difensore Migliorato",
                "desc": "Il danno di Scarica Arcana e la CA del difensore aumentano di +2, e il difensore riflette i danni con la sua reazione."
            }
        ]
    },
    {
        "name": "Sentiero del Berserker (Path of the Berserker)",
        "name_en": "Path of the Berserker",
        "class_name": "Barbaro",
        "source": "Player's Handbook",
        "description": "La quintessenza della furia cieca: entra in frenesia totale scatenando raffiche di colpi letali incurante della fatica.",
        "features": [
            {
                "level": 3,
                "name": "Frenesia",
                "desc": "Mentre sei in ira puoi entrare in frenesia: puoi effettuare un attacco con arma da mischia come azione bonus in ogni tuo turno. Al termine dell'ira subisci un livello di indebolimento."
            },
            {
                "level": 6,
                "name": "Furia Senza Mente",
                "desc": "Mentre sei in ira non puoi essere affascinato o spaventato."
            },
            {
                "level": 10,
                "name": "Presenza Intimidatoria",
                "desc": "Come azione puoi spaventare una creatura entro 9m che fallisce un tiro salvezza su Saggezza."
            },
            {
                "level": 14,
                "name": "Ritorsione",
                "desc": "Quando subisci danni da una creatura entro 1.5m da te, puoi usare la tua reazione per sferrare un attacco con arma da mischia contro di essa."
            }
        ]
    },
    {
        "name": "Sentiero del Guerriero Totemico (Path of the Totem Warrior)",
        "name_en": "Path of the Totem Warrior",
        "class_name": "Barbaro",
        "source": "Player's Handbook",
        "description": "Guidato dagli spiriti primordiali della natura: incanala la resistenza dell'Orso, l'agilità dell'Aquila o la furia del Lupo.",
        "features": [
            {
                "level": 3,
                "name": "Cercatore di Spiriti",
                "desc": "Puoi lanciare Parlare con gli Animali e Senso delle Bestie come rituali."
            },
            {
                "level": 3,
                "name": "Spirito Totemico",
                "desc": "Orso (resistenza a tutti i danni eccetto psichici), Aquila (scatto bonus e svantaggio attacchi d'opportunità), Lupo (alleati hanno vantaggio contro i nemici entro 1.5m da te)."
            },
            {
                "level": 6,
                "name": "Aspetto della Bestia",
                "desc": "Sensi acuti dell'aquila, forza di sollevamento titanica dell'orso o abilità di tracciamento implacabile del lupo."
            },
            {
                "level": 10,
                "name": "Camminatore degli Spiriti",
                "desc": "Puoi lanciare Comunione con la Natura come rituale."
            },
            {
                "level": 14,
                "name": "Sintonia Totemica",
                "desc": "Poteri totemici supremi: volare a scatti come l'aquila o atterrare i nemici proni con l'urto dell'orso."
            }
        ]
    },
    {
        "name": "Sentiero del Guardiano Ancestrale (Path of the Ancestral Guardian)",
        "name_en": "Path of the Ancestral Guardian",
        "class_name": "Barbaro",
        "source": "Xanathar's Guide to Everything",
        "description": "Chiama a raccolta gli spiriti dei propri antenati per ostacolare i nemici e formare uno scudo spirituale per gli alleati.",
        "features": [
            {
                "level": 3,
                "name": "Protettori Ancestrali",
                "desc": "Il primo nemico che colpisci in ira ha svantaggio ad attaccare chiunque non sia tu, e gli alleati hanno resistenza ai suoi danni."
            },
            {
                "level": 6,
                "name": "Scudo Spirituale",
                "desc": "Come reazione riduci di 2d6 i danni subiti da un alleato entro 9m."
            },
            {
                "level": 10,
                "name": "Consultare gli Spiriti",
                "desc": "Puoi lanciare Chiaroveggenza o Augurio senza spendere slot incantesimo."
            },
            {
                "level": 14,
                "name": "Antenati Vendicativi",
                "desc": "Quando Scudo Spirituale assorbe danni, il nemico attaccante subisce danni da forza pari al danno prevenuto."
            }
        ]
    },
    {
        "name": "Sentiero del Furioso di Battaglia (Path of the Battlerager)",
        "name_en": "Path of the Battlerager",
        "class_name": "Barbaro",
        "source": "Sword Coast Adventurer's Guide",
        "description": "Guerrieri nani corazzati di corazze chiodate che si gettano nella mischia dilaniando chiunque osi avvicinarsi.",
        "features": [
            {
                "level": 3,
                "name": "Armatura Chiodata",
                "desc": "Infiggi 1d4 danni taglienti bonus con attacco chiodato come azione bonus in ira e 3 danni quando afferri una creatura."
            },
            {
                "level": 6,
                "name": "Fervore Spietato",
                "desc": "Quando usi Attacco Irruente in ira ottieni punti ferita temporanei pari al mod Costituzione."
            },
            {
                "level": 10,
                "name": "Carica Chiodata",
                "desc": "Puoi scattare come azione bonus mentre sei in ira."
            },
            {
                "level": 14,
                "name": "Ritorsione Chiodata",
                "desc": "Chiunque ti colpisca con attacco da mischia subisce 3 danni perforanti se indossi l'armatura chiodata."
            }
        ]
    },
    {
        "name": "Sentiero della Bestia (Path of the Beast)",
        "name_en": "Path of the Beast",
        "class_name": "Barbaro",
        "source": "Tasha's Cauldron of Everything",
        "description": "Muta il proprio corpo in forma bestiale primordiale manifestando morsi sanguinari, artigli laceranti o una coda uncinata.",
        "features": [
            {
                "level": 3,
                "name": "Forma della Bestia",
                "desc": "In ira manifesti: Morso (cura PF pari a comp), Artigli (attacco extra ogni turno) o Coda (+1d8 alla CA come reazione)."
            },
            {
                "level": 6,
                "name": "Anima Bestiale",
                "desc": "Ottieni nuoto pari a velocità, arrampicata su pareti lisce o salti straordinari con prova di Atletica."
            },
            {
                "level": 10,
                "name": "Furore Infettivo",
                "desc": "Quando colpisci con le tue armi naturali, il bersaglio fallisce un TS Saggezza: attacca un suo compagno o subisce 2d12 danni psichici."
            },
            {
                "level": 14,
                "name": "Richiamo del Branco",
                "desc": "Conferisci 5 PF temporanei agli alleati vicini e infliggi 1d6 danni da forza extra per ogni alleato potenziato."
            }
        ]
    },
    {
        "name": "Sentiero dell'Araldo della Tempesta (Path of the Storm Herald)",
        "name_en": "Path of the Storm Herald",
        "class_name": "Barbaro",
        "source": "Xanathar's Guide to Everything",
        "description": "Emana un'aura tempestosa elementale legata al Deserto ardente, al Mare fulmineo o alla Tundra gelida.",
        "features": [
            {
                "level": 3,
                "name": "Aura della Tempesta",
                "desc": "Mentre sei in ira crei un'aura di 3m: Deserto (fuoco), Mare (fulmini a bersaglio singolo), Tundra (PF temporanei agli alleati)."
            },
            {
                "level": 6,
                "name": "Anima della Tempesta",
                "desc": "Resistenza ai danni elementali e benefici ambientali (camminare sull'acqua o respirare sott'acqua)."
            },
            {
                "level": 10,
                "name": "Scudo della Tempesta",
                "desc": "Condividi la tua resistenza elementale con gli alleati vicini entro la tua aura."
            },
            {
                "level": 14,
                "name": "Tempesta Furente",
                "desc": "Effetti di contraccolpo estremi nell'aura: fiamme accecanti, fulmini che atterrano proni o gelo che immobilizza i nemici."
            }
        ]
    },
    {
        "name": "Sentiero della Magia Selvaggia (Path of Wild Magic)",
        "name_en": "Path of Wild Magic",
        "class_name": "Barbaro",
        "source": "Tasha's Cauldron of Everything",
        "description": "Imbevuto della magia instabile del Piano Fatato, ogni ira sprigiona effetti magici imprevedibili e benefici.",
        "features": [
            {
                "level": 3,
                "name": "Consapevolezza Magica",
                "desc": "Come azione percepisci la presenza di incantesimi e oggetti magici entro 18m."
            },
            {
                "level": 3,
                "name": "Ira della Magia Selvaggia",
                "desc": "Tira su una tabella d8 quando entri in ira: teletrasporto bonus, raggi radiosi, viticci intricanti o esplosioni di forza."
            },
            {
                "level": 6,
                "name": "Infusione Ristoratrice",
                "desc": "Tocchi un alleato conferendogli +1d3 ai tiri per colpire o ripristinando uno slot incantesimo di 1°-3° livello."
            },
            {
                "level": 10,
                "name": "Ritorsione Instabile",
                "desc": "Quando subisci danno o fallisci un TS puoi usare la reazione per ritirare sulla tabella di Magia Selvaggia."
            },
            {
                "level": 14,
                "name": "Ira Controllata",
                "desc": "Tiri due volte sulla tabella di Magia Selvaggia e scegli quale effetto attivare."
            }
        ]
    },
    {
        "name": "Sentiero dello Zelota (Path of the Zealot)",
        "name_en": "Path of the Zealot",
        "class_name": "Barbaro",
        "source": "Xanathar's Guide to Everything",
        "description": "Guerriero sacro animato dal favore divino, combatte oltre la morte e infligge devastanti colpi radiosi o necrotici.",
        "features": [
            {
                "level": 3,
                "name": "Furia Divina",
                "desc": "Il primo colpo a segno in ogni turno di ira infligge 1d6 + metà livello danni radiosi o necrotici."
            },
            {
                "level": 3,
                "name": "Guerriero degli Dei",
                "desc": "Gli incantesimi che ti riportano in vita (come Rianimare Morti) non richiedono componenti materiali preziose."
            },
            {
                "level": 6,
                "name": "Mente Fanatica",
                "desc": "Una volta per ira puoi ripetere un tiro salvezza fallito."
            },
            {
                "level": 10,
                "name": "Presenza Zelota",
                "desc": "Come azione bonus ispiri fino a 10 alleati entro 18m conferendo vantaggio a tiri per colpire e TS per 1 round."
            },
            {
                "level": 14,
                "name": "Ira Oltre la Morte",
                "desc": "Rimanere a 0 punti ferita non ti fa svenire mentre sei in ira; continui a combattere e muori solo se l'ira termina a 0 PF."
            }
        ]
    },
    {
        "name": "Collegio del Sapere (College of Lore)",
        "name_en": "College of Lore",
        "class_name": "Bardo",
        "source": "Player's Handbook",
        "description": "Eruditi e custodi dei segreti del multiverso, indeboliscono i nemici con parole taglienti e apprendono magie da qualsiasi classe.",
        "features": [
            {
                "level": 3,
                "name": "Competenze Aggiuntive",
                "desc": "Ottieni competenza in tre abilità a tua scelta."
            },
            {
                "level": 3,
                "name": "Parole Taglienti",
                "desc": "Usi l'Ispirazione Bardica come reazione per sottrarre il dado dal tiro per colpire, prova o danno di un nemico entro 18m."
            },
            {
                "level": 6,
                "name": "Segreti Magici Aggiuntivi",
                "desc": "Apprendi due incantesimi di qualsiasi classe fino al 3° livello."
            },
            {
                "level": 14,
                "name": "Abilità Impareggiabile",
                "desc": "Puoi aggiungere il dado di Ispirazione Bardica alle tue stesse prove di caratteristica."
            }
        ]
    },
    {
        "name": "Collegio del Valore (College of Valor)",
        "name_en": "College of Valor",
        "class_name": "Bardo",
        "source": "Player's Handbook",
        "description": "Canta le gesta degli eroi marziali brandendo armi e scudi, ispirando la difesa e il danno degli alleati in battaglia.",
        "features": [
            {
                "level": 3,
                "name": "Competenze da Battaglia",
                "desc": "Competenza nelle armature medie, scudi e armi marziali."
            },
            {
                "level": 3,
                "name": "Ispirazione da Combattimento",
                "desc": "Gli alleati possono aggiungere l'Ispirazione Bardica ai danni delle armi o alla propria CA contro un colpo."
            },
            {
                "level": 6,
                "name": "Attacco Extra (Valore)",
                "desc": "Puoi attaccare due volte ad ogni turno."
            },
            {
                "level": 14,
                "name": "Magia da Battaglia",
                "desc": "Quando usi la tua azione per lanciare un incantesimo da bardo puoi sferrare un attacco con arma come azione bonus."
            }
        ]
    },
    {
        "name": "Collegio della Seduzione (College of Glamour)",
        "name_en": "College of Glamour",
        "class_name": "Bardo",
        "source": "Xanathar's Guide to Everything",
        "description": "Incanta le corti e gli eserciti con la travolgente bellezza della Selva Fatata, dominando le menti con maestà ultraterrena.",
        "features": [
            {
                "level": 3,
                "name": "Manto d'Ispirazione",
                "desc": "Spendi Ispirazione Bardica: fino a 5 alleati ottengono PF temporanei (5-14) e possono muoversi come reazione senza provocare AdO."
            },
            {
                "level": 3,
                "name": "Esibizione Ammaliante",
                "desc": "Dop un'esibizione di 1 minuto affascini gli spettatori che falliscono un TS su Saggezza."
            },
            {
                "level": 6,
                "name": "Manto di Maestà",
                "desc": "Puoi lanciare Comando come azione bonus in ogni tuo turno per 1 minuto senza spendere slot incantesimo."
            },
            {
                "level": 14,
                "name": "Maestà Inviolabile",
                "desc": "Chiunque tenti di attaccarti deve superare un TS su Carisma o essere costretto a scegliere un altro bersaglio."
            }
        ]
    },
    {
        "name": "Collegio delle Spade (College of Swords)",
        "name_en": "College of Swords",
        "class_name": "Bardo",
        "source": "Xanathar's Guide to Everything",
        "description": "Danza tra le lame con acrobazie spettacolari, usando la propria arma come catalizzatore e spendendo l'ispirazione in virtuosismi letali.",
        "features": [
            {
                "level": 3,
                "name": "Addestramento con la Spada",
                "desc": "Competenza nelle armature medie e scimitarra; stile di combattimento Duellare o Combattere con Due Armi."
            },
            {
                "level": 3,
                "name": "Virtuosismi di Lama",
                "desc": "Aggiungi l'Ispirazione Bardica ai danni sferrando Virtuosismo Difensivo (+CA), Virtuosismo Fendente (danno adiacente) o Virtuosismo Mobile (spinta e passo)."
            },
            {
                "level": 6,
                "name": "Attacco Extra (Spade)",
                "desc": "Puoi attaccare due volte a ogni turno."
            },
            {
                "level": 14,
                "name": "Virtuosismo del Maestro",
                "desc": "Puoi usare un d6 al posto del dado di Ispirazione Bardica per i virtuosismi senza spendere usi di ispirazione."
            }
        ]
    },
    {
        "name": "Collegio dei Sussurri (College of Whispers)",
        "name_en": "College of Whispers",
        "class_name": "Bardo",
        "source": "Xanathar's Guide to Everything",
        "description": "Spie e assassini delle corti nobiliari, iniettano veleno psichico nelle lame e rubano le ombre dei caduti per indossarne l'identità.",
        "features": [
            {
                "level": 3,
                "name": "Lame Psichiche",
                "desc": "Spendi Ispirazione Bardica quando colpisci con un'arma: infliggi da 2d6 a 8d6 danni psichici extra."
            },
            {
                "level": 3,
                "name": "Parole di Terrore",
                "desc": "Parlando in privato con un umanoide per 1 minuto puoi terrorizzarlo (paranoico e spaventato per 1 ora)."
            },
            {
                "level": 6,
                "name": "Manto di Ombre",
                "desc": "Quando una persona muore entro 9m puoi catturarne l'ombra: puoi camuffarti in essa assumendone memorie superficiali per 1 ora."
            },
            {
                "level": 14,
                "name": "Sussurro dell'Ombra",
                "desc": "Sussurri un segreto a una creatura: se fallisce un TS Saggezza diventa incantata credendo che tu conosca il suo segreto più oscuro."
            }
        ]
    },
    {
        "name": "Collegio dell'Eloquenza (College of Eloquence)",
        "name_en": "College of Eloquence",
        "class_name": "Bardo",
        "source": "Tasha's Cauldron of Everything",
        "description": "Maestri assoluti del dibattito e della retorica, piegano le difese mentali con parole inconfutabili e non sprecano mai un'ispirazione.",
        "features": [
            {
                "level": 3,
                "name": "Discorso d'Argento",
                "desc": "Tratti qualsiasi risultato di 9 o inferiore su un d20 per Inganno o Persuasione come un 10."
            },
            {
                "level": 3,
                "name": "Parole Sconfortanti",
                "desc": "Come azione bonus spendi Ispirazione Bardica per sottrarre il dado dal prossimo tiro salvezza del nemico."
            },
            {
                "level": 6,
                "name": "Ispirazione Infallibile",
                "desc": "Se un alleato fallisce una prova usando la tua Ispirazione Bardica, non perde il dado di ispirazione."
            },
            {
                "level": 14,
                "name": "Monologo Contagioso",
                "desc": "Quando un alleato ha successo con l'Ispirazione Bardica, puoi ispirare un altro alleato entro 18m come reazione senza consumare usi."
            }
        ]
    },
    {
        "name": "Collegio della Creazione (College of Creation)",
        "name_en": "College of Creation",
        "class_name": "Bardo",
        "source": "Tasha's Cauldron of Everything",
        "description": "Incanala la Canzone della Creazione cosmica dando vita a note danzanti e manifestando oggetti tangibili dal nulla.",
        "features": [
            {
                "level": 3,
                "name": "Nota di Potenziale",
                "desc": "Le tue ispirazioni creano un motus sonoro: conferisce benefici unici a prove di caratteristica, tiri per colpire o tiri salvezza."
            },
            {
                "level": 3,
                "name": "Esibizione della Creazione",
                "desc": "Come azione crei un oggetto non magico dal nulla del valore fino a 20 volte il tuo livello da bardo."
            },
            {
                "level": 6,
                "name": "Danza Animata",
                "desc": "Come azione bonus animi un oggetto Grande o più piccolo che cammina o fluttua e combatte al tuo fianco."
            },
            {
                "level": 14,
                "name": "Crescendo Creativo",
                "desc": "Puoi creare oggetti senza limiti di costo e creare più oggetti contemporaneamente."
            }
        ]
    },
    {
        "name": "Collegio degli Spiriti (College of Spirits)",
        "name_en": "College of Spirits",
        "class_name": "Bardo",
        "source": "Van Richten's Guide to Ravenloft",
        "description": "Comunica con le anime dei defunti attraverso tarocchi e tavolette spiritiche, scatenando racconti spettrali dai potenti effetti.",
        "features": [
            {
                "level": 3,
                "name": "Catalizzatore Spiritico",
                "desc": "Usi candele, teschi o carte di tarocchi come catalizzatore per gli incantesimi da bardo."
            },
            {
                "level": 3,
                "name": "Racconti dall'Aldilà",
                "desc": "Spendi Ispirazione Bardica tirando su una tabella per invocare spiriti di eroi, giganti, draghi, mostri o fantasmi con effetti magici unici."
            },
            {
                "level": 6,
                "name": "Seduta Spiritica",
                "desc": "Conduci un rituale con gli alleati per apprendere un incantesimo di divinazione o negromanzia di qualsiasi classe."
            },
            {
                "level": 14,
                "name": "Connessione Mistica",
                "desc": "Tiri due volte sulla tabella dei Racconti dall'Aldilà e scegli quale effetto applicare."
            }
        ]
    },
    {
        "name": "Dominio della Conoscenza (Knowledge Domain)",
        "name_en": "Knowledge Domain",
        "class_name": "Chierico",
        "source": "Player's Handbook",
        "description": "Servitori degli dei del sapere e dell'arcano, leggono i pensieri altrui e ottengono maestria istantanea in qualsiasi arte.",
        "features": [
            {
                "level": 1,
                "name": "Benedizioni della Conoscenza",
                "desc": "Due lingue extra e competenza con Maestria raddoppiata in due abilità tra Arcano, Storia, Natura, Religione."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Conoscenza delle Ere",
                "desc": "Ottieni competenza in una qualsiasi abilità o strumento a scelta per 10 minuti."
            },
            {
                "level": 6,
                "name": "Incanalare Divinità: Lettura del Pensiero",
                "desc": "Leggi i pensieri di una creatura e puoi lanciare Suggestione senza spendere slot incantesimo."
            },
            {
                "level": 8,
                "name": "Incantesimi Potenziati",
                "desc": "Aggiungi il modificatore di Saggezza ai danni inflitti con i trucchetti da chierico."
            },
            {
                "level": 17,
                "name": "Visioni del Passato",
                "desc": "Meditando puoi vedere eventi accaduti nel passato in un luogo o toccando un oggetto."
            }
        ]
    },
    {
        "name": "Dominio della Vita (Life Domain)",
        "name_en": "Life Domain",
        "class_name": "Chierico",
        "source": "Player's Handbook",
        "description": "Il prototipo del guaritore supremo: armature pesanti e magie curative amplificate dal potere della luce vitale.",
        "features": [
            {
                "level": 1,
                "name": "Competenza Extra (Vita)",
                "desc": "Competenza nelle armature pesanti."
            },
            {
                "level": 1,
                "name": "Discepolo della Vita",
                "desc": "Le tue magie di cura curano 2 + livello dell'incantesimo punti ferita addizionali."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Preservare Vita",
                "desc": "Cura fino a 5 volte il tuo livello chierico distribuendoli tra le creature entro 9m sotto la metà dei PF."
            },
            {
                "level": 6,
                "name": "Guaritore Benedetto",
                "desc": "Quando lanci una magia di cura su qualcun altro, recuperi anche tu 2 + livello incantesimo PF."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Vita)",
                "desc": "Una volta per turno infliggi 1d8 (2d8 a liv 14) danni radiosi extra con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Guarigione Suprema",
                "desc": "Tutte le tue magie di cura curano il valore massimo dei dadi senza bisogno di tirare."
            }
        ]
    },
    {
        "name": "Dominio della Luce (Light Domain)",
        "name_en": "Light Domain",
        "class_name": "Chierico",
        "source": "Player's Handbook",
        "description": "Canalizza la gloria radiosa del sole, incenerendo l'oscurità e i non morti con palle di fuoco e lampi accecanti.",
        "features": [
            {
                "level": 1,
                "name": "Trucchetto Bonus",
                "desc": "Apprendi il trucchetto Luce se non lo conosci già."
            },
            {
                "level": 1,
                "name": "Bagliore Tutelare",
                "desc": "Come reazione imponi svantaggio al tiro per colpire di un nemico visibile entro 9m che ti attacca."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Splendore dell'Alba",
                "desc": "Dissipa qualsiasi oscurità magica entro 9m e infligge 2d10 + livello chierico danni radiosi (TS Des dimezza)."
            },
            {
                "level": 6,
                "name": "Bagliore Migliorato",
                "desc": "Puoi usare Bagliore Tutelare quando un nemico attacca un alleato entro 9m."
            },
            {
                "level": 8,
                "name": "Incantesimi Potenziati",
                "desc": "Aggiungi Saggezza ai danni dei trucchetti da chierico."
            },
            {
                "level": 17,
                "name": "Corona di Luce",
                "desc": "Emetti luce intensa per 18m: i nemici nell'area hanno svantaggio ai tiri salvezza contro i tuoi incantesimi di fuoco e radiosi."
            }
        ]
    },
    {
        "name": "Dominio della Natura (Nature Domain)",
        "name_en": "Nature Domain",
        "class_name": "Chierico",
        "source": "Player's Handbook",
        "description": "Custode della purezza della terra e delle bestie, indossa armature pesanti e padroneggia gli elementi naturali.",
        "features": [
            {
                "level": 1,
                "name": "Accolito della Natura",
                "desc": "Un trucchetto da druido a scelta, competenza nelle armature pesanti e in una tra Addestrare Animali, Natura, Sopravvivenza."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Ammaliare Animali e Piante",
                "desc": "Bestie e piante entro 9m devono superare un TS Saggezza o essere affascinate per 1 minuto."
            },
            {
                "level": 6,
                "name": "Smorzare Elementi",
                "desc": "Come reazione concedi resistenza a freddo, fuoco, fulmine o acido a te o un alleato entro 9m che subisce quel danno."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Natura)",
                "desc": "Infliggi 1d8 danni extra da freddo, fuoco o fulmine con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Maestro della Natura",
                "desc": "Puoi comandare le creature affascinate da Ammaliare Animali come azione bonus."
            }
        ]
    },
    {
        "name": "Dominio della Tempesta (Tempest Domain)",
        "name_en": "Tempest Domain",
        "class_name": "Chierico",
        "source": "Player's Handbook",
        "description": "Venera gli dei delle tempeste oceaniche e dei fulmini, respingendo i nemici con tuoni assordanti e massimizzando i fulmini.",
        "features": [
            {
                "level": 1,
                "name": "Competenze da Tempesta",
                "desc": "Competenza nelle armature pesanti e in tutte le armi marziali."
            },
            {
                "level": 1,
                "name": "Collera della Tempesta",
                "desc": "Quando vieni colpito entro 1.5m, come reazione infliggi 2d8 danni da fulmine o tuono (TS Des dimezza)."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Furore Distruttivo",
                "desc": "Quando tiri danni da fulmine o da tuono, infliggi il massimo dei danni anziché tirare i dadi."
            },
            {
                "level": 6,
                "name": "Colpo di Tuono",
                "desc": "Quando infliggi danni da fulmine a una creatura Grande o più piccola, puoi spingerla indietro fino a 3 metri."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Tempesta)",
                "desc": "Infliggi 1d8 danni da tuono extra con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Nato dalla Tempesta",
                "desc": "Ottieni velocità di volare pari alla tua velocità sul terreno purché tu non sia sottoterra o al chiuso."
            }
        ]
    },
    {
        "name": "Dominio dell'Inganno (Trickery Domain)",
        "name_en": "Trickery Domain",
        "class_name": "Chierico",
        "source": "Player's Handbook",
        "description": "Devoto alle divinità del caos, dei ladri e delle illusioni: schiera duplicati illusori ed elargisce furtività magica.",
        "features": [
            {
                "level": 1,
                "name": "Benedizione dell'Ingannatore",
                "desc": "Tocchi una creatura consenziente conferendole vantaggio a tutte le prove di Destrezza (Furtività) per 1 ora."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Invocare Duplicato",
                "desc": "Crei un'illusione perfetta di te stesso entro 9m attraverso cui puoi lanciare incantesimi e ottenere vantaggio."
            },
            {
                "level": 6,
                "name": "Incanalare Divinità: Manto d'Ombre",
                "desc": "Diventi completamente invisibile fino alla fine del tuo prossimo turno."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Inganno)",
                "desc": "Infliggi 1d8 danni da veleno extra con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Duplicato Migliorato",
                "desc": "Puoi creare fino a quattro duplicati illusori simultanei e puoi teletrasportarti scambiando posizione con essi."
            }
        ]
    },
    {
        "name": "Dominio della Guerra (War Domain)",
        "name_en": "War Domain",
        "class_name": "Chierico",
        "source": "Player's Handbook",
        "description": "Condottiero d'acciaio consacrato alla battaglia, trasforma gli attacchi mancati in colpi perfetti con bonus divini.",
        "features": [
            {
                "level": 1,
                "name": "Competenze di Guerra",
                "desc": "Competenza nelle armature pesanti e in tutte le armi marziali."
            },
            {
                "level": 1,
                "name": "Sacerdote di Guerra",
                "desc": "Quando usi l'azione di Attacco puoi sferrare un attacco con arma extra come azione bonus (volte pari a Saggezza)."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Colpo Guidato",
                "desc": "Ottieni un bonus di +10 al tuo tiro per colpire dopo aver visto il tiro."
            },
            {
                "level": 6,
                "name": "Incanalare Divinità: Benedizione del Dio della Guerra",
                "desc": "Concedi il bonus di +10 al tiro per colpire di un alleato vicino entro 9m come reazione."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Guerra)",
                "desc": "Infliggi 1d8 danni con arma extra dello stesso tipo dell'arma."
            },
            {
                "level": 17,
                "name": "Avatar della Battaglia",
                "desc": "Ottieni resistenza ai danni contundenti, perforanti e taglienti da armi non magiche."
            }
        ]
    },
    {
        "name": "Dominio della Morte (Death Domain)",
        "name_en": "Death Domain",
        "class_name": "Chierico",
        "source": "Dungeon Master's Guide",
        "description": "Devoto al passaggio nell'oltretomba o alla negromanzia blasfema, trafigge i nemici con energia necrotica che ignora le resistenze.",
        "features": [
            {
                "level": 1,
                "name": "Competenze della Morte",
                "desc": "Competenza in tutte le armi marziali e apprendi un trucchetto di negromanzia che può colpire due bersagli adiacenti."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Tocco della Morte",
                "desc": "Colpendo in mischia infliggi 5 + doppio del livello chierico danni necrotici extra."
            },
            {
                "level": 6,
                "name": "Distruzione Inevitabile",
                "desc": "I tuoi danni necrotici da incantesimi e Incanalare Divinità ignorano la resistenza ai danni necrotici."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Morte)",
                "desc": "Infliggi 1d8 danni necrotici extra con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Negromanzia Raddoppiata",
                "desc": "Gli incantesimi di negromanzia dal 1° al 5° livello a bersaglio singolo possono colpire due bersagli contemporaneamente."
            }
        ]
    },
    {
        "name": "Dominio dell'Arcano (Arcana Domain)",
        "name_en": "Arcana Domain",
        "class_name": "Chierico",
        "source": "Sword Coast Adventurer's Guide",
        "description": "Ponte tra fede divina e misteri arcani di Mystra o Boccob, dissipa magie ostili e punisce le creature ultraterrene.",
        "features": [
            {
                "level": 1,
                "name": "Iniziato dell'Arcano",
                "desc": "Competenza nell'abilità Arcano e due trucchetti da mago che contano come trucchetti da chierico."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Abiura Arcana",
                "desc": "Bandisce o scaccia celestiali, elementali, immondi e folletti come se fossero non morti."
            },
            {
                "level": 6,
                "name": "Spezza-Incantesimo",
                "desc": "Quando curi una creatura con un incantesimo, puoi dissolvere un incantesimo di livello pari o inferiore sullo stesso bersaglio."
            },
            {
                "level": 8,
                "name": "Incantesimi Potenziati",
                "desc": "Aggiungi Saggezza ai danni dei trucchetti da chierico."
            },
            {
                "level": 17,
                "name": "Maestria Arcana",
                "desc": "Scegli quattro incantesimi da mago (uno per 6°, 7°, 8° e 9° livello) aggiungendoli agli incantesimi preparati."
            }
        ]
    },
    {
        "name": "Dominio della Forgia (Forge Domain)",
        "name_en": "Forge Domain",
        "class_name": "Chierico",
        "source": "Xanathar's Guide to Everything",
        "description": "Benedetto dagli dei fabbri, indossa corazze incandescenti invulnerabili al fuoco e forgia armi magiche direttamente sul campo.",
        "features": [
            {
                "level": 1,
                "name": "Benedizione della Forgia",
                "desc": "Competenza nelle armature pesanti e strumenti da fabbro. Conferisci +1 magico a un'arma o armatura ogni giorno."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Benedizione dell'Artigiano",
                "desc": "Crei qualsiasi oggetto di metallo del valore fino a 100 mo attraverso un rituale di 1 ora."
            },
            {
                "level": 6,
                "name": "Anima della Forgia",
                "desc": "Resistenza ai danni da fuoco e +1 alla CA quando indossi un'armatura pesante."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Forgia)",
                "desc": "Infliggi 1d8 danni da fuoco extra con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Santo della Forgia e del Fuoco",
                "desc": "Immunità totale ai danni da fuoco e resistenza ai danni non magici se indossi un'armatura pesante."
            }
        ]
    },
    {
        "name": "Dominio della Tomba (Grave Domain)",
        "name_en": "Grave Domain",
        "class_name": "Chierico",
        "source": "Xanathar's Guide to Everything",
        "description": "Custode del confine sacro tra vita e morte, annulla i colpi critici nemici e massimizza le cure sugli alleati a terra.",
        "features": [
            {
                "level": 1,
                "name": "Cerchio della Mortalità",
                "desc": "Curando una creatura a 0 PF massimizzi tutti i dadi di cura. Impari il trucchetto Salvare i Morenti come azione bonus con gittata 9m."
            },
            {
                "level": 1,
                "name": "Occhi della Tomba",
                "desc": "Percepisci la presenza e l'ubicazione di qualsiasi non morto entro 18m."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Sentiero della Tomba",
                "desc": "Maledici una creatura: subisce vulnerabilità a tutti i danni del prossimo attacco che la colpisce."
            },
            {
                "level": 6,
                "name": "Sentinella alle Porte della Morte",
                "desc": "Come reazione trasformi un colpo critico subito da te o un alleato entro 9m in un colpo normale."
            },
            {
                "level": 8,
                "name": "Incantesimi Potenziati",
                "desc": "Aggiungi Saggezza ai danni dei trucchetti da chierico."
            },
            {
                "level": 17,
                "name": "Custode delle Anime",
                "desc": "Quando una creatura muore entro 18m, tu o un alleato recuperate PF pari ai Dadi Vita della creatura caduta."
            }
        ]
    },
    {
        "name": "Dominio dell'Ordine (Order Domain)",
        "name_en": "Order Domain",
        "class_name": "Chierico",
        "source": "Tasha's Cauldron of Everything",
        "description": "Incarna la legge assoluta e l'autorità divina, guidando gli alleati a contrattaccare immediatamente su comando.",
        "features": [
            {
                "level": 1,
                "name": "Voce dell'Autorità",
                "desc": "Quando lanci un incantesimo di 1° livello o superiore su un alleato, quell'alleato può compiere un attacco con arma come reazione."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Ordine della Legge",
                "desc": "Costringi i nemici entro 9m a superare un TS Saggezza o lasciar cadere le armi ed essere affascinati."
            },
            {
                "level": 6,
                "name": "Imposizione Corporea",
                "desc": "Puoi lanciare incantesimi di ammaliamento come azione bonus se il tempo di lancio normale è di un'azione."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Ordine)",
                "desc": "Infliggi 1d8 danni psichici extra con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Ira dell'Ordine",
                "desc": "I nemici maledetti dal tuo Colpo Divino subiscono 2d8 danni psichici extra quando vengono colpiti dai tuoi alleati."
            }
        ]
    },
    {
        "name": "Dominio della Pace (Peace Domain)",
        "name_en": "Peace Domain",
        "class_name": "Chierico",
        "source": "Tasha's Cauldron of Everything",
        "description": "Forgia legami empatici indistruttibili tra i compagni, permettendo loro di scambiarsi danni e teletrasportarsi per proteggersi a vicenda.",
        "features": [
            {
                "level": 1,
                "name": "Legame Incoraggiante",
                "desc": "Leghi fino a comp alleati: una volta per turno possono aggiungere 1d4 a un tiro per colpire, prova o tiro salvezza."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Balsamo della Pace",
                "desc": "Ti muovi fino alla tua velocità senza provocare AdO curando 2d6 + Sag PF a chiunque oltrepassi."
            },
            {
                "level": 6,
                "name": "Legame Protettivo",
                "desc": "Quando un alleato legato sta per subire danni, un altro alleato legato entro 9m può teletrasportarsi e subire il danno al suo posto."
            },
            {
                "level": 8,
                "name": "Incantesimi Potenziati",
                "desc": "Aggiungi Saggezza ai danni dei trucchetti da chierico."
            },
            {
                "level": 17,
                "name": "Legame Espansivo",
                "desc": "La portata di Legame Protettivo aumenta a 18 metri e chi assorbe il danno ottiene resistenza a quel danno."
            }
        ]
    },
    {
        "name": "Dominio del Crepuscolo (Twilight Domain)",
        "name_en": "Twilight Domain",
        "class_name": "Chierico",
        "source": "Tasha's Cauldron of Everything",
        "description": "Vigila sulla transizione tra luce e oscurità, donando scurovisione illimitata, volo notturno e un'aura protettiva di punti ferita temporanei continui.",
        "features": [
            {
                "level": 1,
                "name": "Occhi della Notte",
                "desc": "Scurovisione fino a 90 metri condivisa con gli alleati consenzienti. Competenza in armature pesanti e armi marziali."
            },
            {
                "level": 1,
                "name": "Benedizione Vigilante",
                "desc": "Concedi vantaggio al prossimo tiro di iniziativa a te stesso o a un alleato."
            },
            {
                "level": 2,
                "name": "Incanalare Divinità: Santuario Crepuscolare",
                "desc": "Sfera di penombra di 9m: alla fine del turno di ogni alleato concedi 1d6 + livello chierico PF temporanei o rimuovi charme/paura."
            },
            {
                "level": 6,
                "name": "Passo della Notte",
                "desc": "Puoi volare con velocità pari alla tua velocità sul terreno per 1 minuto in penombra o buio."
            },
            {
                "level": 8,
                "name": "Colpo Divino (Crepuscolo)",
                "desc": "Infliggi 1d8 danni radiosi extra con un attacco con arma."
            },
            {
                "level": 17,
                "name": "Sudario del Crepuscolo",
                "desc": "Il tuo Santuario Crepuscolare concede mezza copertura (+2 alla CA e TS Des) a tutti gli alleati al suo interno."
            }
        ]
    },
    {
        "name": "Circolo della Terra (Circle of the Land)",
        "name_en": "Circle of the Land",
        "class_name": "Druido",
        "source": "Player's Handbook",
        "description": "Mistico legato a un bioma naturale (Artico, Costa, Deserto, Foresta, Montagna, Palude, Prateria o Sottosuolo), recupera slot con la meditazione.",
        "features": [
            {
                "level": 2,
                "name": "Trucchetto Bonus",
                "desc": "Apprendi un trucchetto da druido aggiuntivo."
            },
            {
                "level": 2,
                "name": "Recupero Naturale",
                "desc": "Durante un riposo breve puoi recuperare slot incantesimo spesi fino a metà del tuo livello da druido."
            },
            {
                "level": 3,
                "name": "Incantesimi del Circolo",
                "desc": "Incantesimi sempre preparati legati al bioma prescelto."
            },
            {
                "level": 6,
                "name": "Passo della Terra",
                "desc": "Muoverti su terreno difficile non magico non costa movimento extra e attraversi piante non magiche senza subire danni."
            },
            {
                "level": 10,
                "name": "Difesa della Natura",
                "desc": "Immune al veleno, alle malattie e non puoi essere affascinato o spaventato da folletti o elementali."
            },
            {
                "level": 14,
                "name": "Santuario della Natura",
                "desc": "Le bestie e le piante devono superare un TS su Saggezza per poterti attaccare."
            }
        ]
    },
    {
        "name": "Circolo della Luna (Circle of the Moon)",
        "name_en": "Circle of the Moon",
        "class_name": "Druido",
        "source": "Player's Handbook",
        "description": "Maestro supremo della Forma Selvatica: assume forme feroci come azione bonus trasformandosi in orsi, tigri ed elementali devastanti.",
        "features": [
            {
                "level": 2,
                "name": "Forma Selvatica da Combattimento",
                "desc": "Puoi trasformarti come azione bonus e puoi spendere slot incantesimo per curarti di 1d8 per livello dello slot."
            },
            {
                "level": 2,
                "name": "Forme del Circolo",
                "desc": "Puoi trasformarti in bestie con GS fino a 1 (e GS pari a livello/3 dal 6° livello)."
            },
            {
                "level": 6,
                "name": "Colpo Primordiale",
                "desc": "I tuoi attacchi in forma bestiale contano come magici allo scopo di superare resistenze e immunità."
            },
            {
                "level": 10,
                "name": "Forma Selvatica Elementale",
                "desc": "Spendi due usi di Forma Selvatica per trasformarti in un Elementale dell'Aria, della Terra, del Fuoco o dell'Acqua."
            },
            {
                "level": 14,
                "name": "Mille Forme",
                "desc": "Puoi lanciare Alterare Se Stesso a volontà senza spendere slot incantesimo."
            }
        ]
    },
    {
        "name": "Circolo dei Sogni (Circle of Dreams)",
        "name_en": "Circle of Dreams",
        "class_name": "Druido",
        "source": "Xanathar's Guide to Everything",
        "description": "Legato al regno feerico dei sogni e del riposo ristoratore, guarisce con balsami fatati e teletrasporta il gruppo.",
        "features": [
            {
                "level": 2,
                "name": "Balsamo della Corte Estiva",
                "desc": "Riserva di dadi d6 (pari al livello) per curare come azione bonus entro 36m donando anche PF temporanei."
            },
            {
                "level": 6,
                "name": "Focolare della Luce e dell'Ombra",
                "desc": "Crei una sfera invisibile di 9m durante i riposi che conferisce +5 a Percezione e Furtività e maschera la luce."
            },
            {
                "level": 10,
                "name": "Sentieri Nascosti",
                "desc": "Come azione bonus ti teletrasporti fino a 18m, o teletrasporti un alleato consenziente fino a 9m."
            },
            {
                "level": 14,
                "name": "Passaggio Onirico",
                "desc": "Puoi lanciare Sogno, Cerchio di Teletrasporto o Scrutare senza spendere slot incantesimo."
            }
        ]
    },
    {
        "name": "Circolo del Pastore (Circle of the Shepherd)",
        "name_en": "Circle of the Shepherd",
        "class_name": "Druido",
        "source": "Xanathar's Guide to Everything",
        "description": "Protettore degli spiriti animali e condottiero di bestie evocate, schiera totem spirituali che curano e rendono magici gli attacchi del branco.",
        "features": [
            {
                "level": 2,
                "name": "Linguaggio dei Boschi",
                "desc": "Impari il Silvano e puoi comunicare con qualsiasi bestia comprendendone le risposte."
            },
            {
                "level": 2,
                "name": "Totem Spirituale",
                "desc": "Evochi uno spirito entro 18m: Orso (PF temporanei a tutti gli alleati), Falco (vantaggio ad attaccare) o Unicorno (cure ad area triplicate)."
            },
            {
                "level": 6,
                "name": "Evocatore Possente",
                "desc": "Le creature che evochi guadagnano +2 PF per Dado Vita e i loro attacchi naturali contano come magici."
            },
            {
                "level": 10,
                "name": "Spirito Guardiano",
                "desc": "Quando il tuo totem spirituale è attivo, le tue bestie ed elementali evocati recuperano PF all'inizio di ogni turno."
            },
            {
                "level": 14,
                "name": "Pastore Fedele",
                "desc": "Se vieni ridotto a 0 PF, l'incantesimo Evoca Animali di 9° livello si attiva istantaneamente proteggendoti con quattro bestie di GS 2."
            }
        ]
    },
    {
        "name": "Circolo delle Spore (Circle of Spores)",
        "name_en": "Circle of Spores",
        "class_name": "Druido",
        "source": "Guildmasters' Guide to Ravnica / TCoE",
        "description": "Trova bellezza nel ciclo della decomposizione micotica, rilasciando spore letali e rianimando zombi fungini.",
        "features": [
            {
                "level": 2,
                "name": "Aura di Spore",
                "desc": "Come reazione infliggi 1d4 (fino a 1d10) danni necrotici a un nemico che inizia il turno entro 3m."
            },
            {
                "level": 2,
                "name": "Entità Simbiotica",
                "desc": "Spendi Forma Selvatica per ottenere 4 PF per livello da druido e raddoppiare i danni dell'Aura di Spore oltre a 1d6 necrotico con ogni attacco."
            },
            {
                "level": 6,
                "name": "Infestazione Fungina",
                "desc": "Come reazione rianimi un mostro Piccolo o Medio ucciso vicino a te come zombi fungino con 1 PF per 1 ora."
            },
            {
                "level": 10,
                "name": "Diffusione delle Spore",
                "desc": "Come azione bonus lanci le tue spore in un'area di 3m creando una zona mortale di danno continuo."
            },
            {
                "level": 14,
                "name": "Corpo Fungino",
                "desc": "Immune a condizioni cieco, sordo, spaventato e avvelenato, e qualsiasi colpo critico contro di te diventa un colpo normale."
            }
        ]
    },
    {
        "name": "Circolo delle Stelle (Circle of Stars)",
        "name_en": "Circle of Stars",
        "class_name": "Druido",
        "source": "Tasha's Cauldron of Everything",
        "description": "Traccia le costellazioni celesti con mappe stellari, assumendo forme stellari luminose (Arciere, Calice, Drago) che dominano il campo.",
        "features": [
            {
                "level": 2,
                "name": "Mappa Stellare",
                "desc": "Conosci il trucchetto Guida e puoi lanciare Dardo Tracciante senza consumare slot incantesimo."
            },
            {
                "level": 2,
                "name": "Forma Stellare",
                "desc": "Assumi forma stellare: Arciere (attacco bonus radioso 1d8+Sag), Calice (cura extra 1d8+Sag) o Drago (minimo 10 su Concentrazione)."
            },
            {
                "level": 6,
                "name": "Presagio Cosmico",
                "desc": "Usi Weal o Woe tirando 1d6 per aggiungere o sottrarre il dado a tiri per colpire, prove o tiri salvezza."
            },
            {
                "level": 10,
                "name": "Stelle Scintillanti",
                "desc": "I dadi della Forma Stellare aumentano a 2d8 e puoi cambiare costellazione all'inizio di ogni tuo turno."
            },
            {
                "level": 14,
                "name": "Piena di Stelle",
                "desc": "In forma stellare ottieni resistenza ai danni contundenti, perforanti e taglienti."
            }
        ]
    },
    {
        "name": "Circolo del Fuoco Selvaggio (Circle of Wildfire)",
        "name_en": "Circle of Wildfire",
        "class_name": "Druido",
        "source": "Tasha's Cauldron of Everything",
        "description": "Comprende che la distruzione del fuoco prepara il terreno a una nuova e rigogliosa rinascita, combattendo con uno Spirito di Fuoco Selvaggio.",
        "features": [
            {
                "level": 2,
                "name": "Evocare Spirito di Fuoco Selvaggio",
                "desc": "Come azione spendi Forma Selvatica per evocare uno spirito ardente che infligge 2d6 fuoco e combatte al tuo fianco."
            },
            {
                "level": 6,
                "name": "Legame Fiammeggiante",
                "desc": "Aggiungi 1d8 ai danni da fuoco o alle cure dei tuoi incantesimi e puoi far scaturire incantesimi dallo spirito."
            },
            {
                "level": 10,
                "name": "Cauterizzazione Rinata",
                "desc": "Quando una creatura muore entro 9m puoi far scaturire fiamme curative per gli alleati o dannose per i nemici (2d10 + Sag)."
            },
            {
                "level": 14,
                "name": "Scintilla della Fenice",
                "desc": "Se vieni ridotto a 0 PF mentre lo spirito è attivo, lo spirito esplode infliggendo danni ai nemici e tu torni a metà PF."
            }
        ]
    },
    {
        "name": "Campione (Champion)",
        "name_en": "Champion",
        "class_name": "Guerriero",
        "source": "Player's Handbook",
        "description": "La massima eccellenza atletica e marziale: colpi critici devastanti con 19-20 e rigenerazione passiva in fin di vita.",
        "features": [
            {
                "level": 3,
                "name": "Critico Migliorato",
                "desc": "I tuoi attacchi con arma ottengono un colpo critico con un risultato di 19 o 20 al tiro del d20."
            },
            {
                "level": 7,
                "name": "Atleta Straordinario",
                "desc": "Aggiungi metà competenza a qualsiasi prova di Forza, Destrezza o Costituzione che non la usi già, e aumenti i salti."
            },
            {
                "level": 10,
                "name": "Stile di Combattimento Aggiuntivo",
                "desc": "Scegli un secondo stile di combattimento."
            },
            {
                "level": 15,
                "name": "Critico Superiore",
                "desc": "I tuoi attacchi con arma ottengono un colpo critico con un risultato di 18, 19 o 20."
            },
            {
                "level": 18,
                "name": "Sopravvissuto",
                "desc": "All'inizio di ogni tuo turno recuperi 5 + modificatore di Costituzione punti ferita se sei sotto la metà dei tuoi PF massimi."
            }
        ]
    },
    {
        "name": "Maestro di Battaglia (Battle Master)",
        "name_en": "Battle Master",
        "class_name": "Guerriero",
        "source": "Player's Handbook",
        "description": "Tattico e stratega d'acciaio, padroneggia le Manovre spendendo Dadi Superiorità (d8/d10/d12) per disarmare, atterrare e manovrare gli alleati.",
        "features": [
            {
                "level": 3,
                "name": "Superiorità da Combattimento",
                "desc": "Ottieni 4 Dadi Superiorità (d8) per eseguire Manovre marziali (Disarmare, Sbilanciare, Finta, Parata, ecc.)."
            },
            {
                "level": 3,
                "name": "Studioso di Guerra",
                "desc": "Competenza in uno strumento da artigiano a scelta."
            },
            {
                "level": 7,
                "name": "Conosci il Tuo Nemico",
                "desc": "Osservando un nemico per 1 minuto scopri se le sue caratteristiche fisiche, CA o PF sono superiori o inferiori alle tue."
            },
            {
                "level": 10,
                "name": "Superiorità Migliorata",
                "desc": "I tuoi Dadi Superiorità diventano d10 (e d12 al livello 18)."
            },
            {
                "level": 15,
                "name": "Implacabile",
                "desc": "Quando tiri l'iniziativa e non hai dadi superiorità rimasti, ne recuperi subito uno."
            }
        ]
    },
    {
        "name": "Cavaliere Mistico (Eldritch Knight)",
        "name_en": "Eldritch Knight",
        "class_name": "Guerriero",
        "source": "Player's Handbook",
        "description": "Combina perizia bellica marziale con gli incantesimi di Abiura ed Evocazione da Mago, legandosi magicamente alla propria arma.",
        "features": [
            {
                "level": 3,
                "name": "Lancio di Incantesimi (Abiura/Evocazione)",
                "desc": "Usi l'Intelligenza per lanciare incantesimi da mago dal 1° al 4° livello."
            },
            {
                "level": 3,
                "name": "Legame con l'Arma",
                "desc": "Ti leghi a due armi: non puoi esserne disarmato e puoi richiamarle nella tua mano come azione bonus da qualsiasi distanza."
            },
            {
                "level": 7,
                "name": "Magia da Guerra",
                "desc": "Quando usi la tua azione per lanciare un trucchetto, puoi sferrare un attacco con arma come azione bonus."
            },
            {
                "level": 10,
                "name": "Colpo Mistico",
                "desc": "Quando colpisci una creatura con un'arma, questa ha svantaggio al prossimo TS contro un tuo incantesimo."
            },
            {
                "level": 15,
                "name": "Carica Arcana",
                "desc": "Quando usi Slancio d'Azione (Action Surge) puoi teletrasportarti fino a 9 metri prima o dopo l'azione extra."
            },
            {
                "level": 18,
                "name": "Magia da Guerra Superiore",
                "desc": "Quando lanci un incantesimo di qualsiasi livello come azione, puoi effettuare un attacco con arma come azione bonus."
            }
        ]
    },
    {
        "name": "Arciere Arcano (Arcane Archer)",
        "name_en": "Arcane Archer",
        "class_name": "Guerriero",
        "source": "Xanathar's Guide to Everything",
        "description": "Tradizione elfica che infonde le frecce scoccate con potenti magie arcane di interdizione, teletrasporto e danni elementali.",
        "features": [
            {
                "level": 3,
                "name": "Tiro Arcano",
                "desc": "Infondi frecce con colpi speciali (Freccia Esplosiva, Ombra, Perforante, Rifiuto, ecc.) due volte per riposo."
            },
            {
                "level": 3,
                "name": "Sapienza dell'Arciere Arcano",
                "desc": "Competenza in Arcano o Natura e impari il trucchetto Prestidigitazione o Guida Druidica."
            },
            {
                "level": 7,
                "name": "Freccia Magica",
                "desc": "Ogni freccia scoccata conta come magica per superare resistenze."
            },
            {
                "level": 7,
                "name": "Tiro Curvo",
                "desc": "Se manchi un bersaglio con una freccia magica, come azione bonus puoi reindirizzare la freccia contro un altro bersaglio entro 18m."
            },
            {
                "level": 15,
                "name": "Tiro Sempre Pronto",
                "desc": "Se tiri l'iniziativa senza usi di Tiro Arcano rimasti, ne recuperi subito uno."
            }
        ]
    },
    {
        "name": "Cavaliere (Cavalier)",
        "name_en": "Cavalier",
        "class_name": "Guerriero",
        "source": "Xanathar's Guide to Everything",
        "description": "Nobile protettore a cavallo e a piedi: intercetta gli attacchi rivolti ai compagni e punisce severamente chi tenta di fuggire.",
        "features": [
            {
                "level": 3,
                "name": "Nato per la Sella",
                "desc": "Montare o smontare costa solo 1.5m, hai vantaggio contro cadute da sella e non atterri mai prono."
            },
            {
                "level": 3,
                "name": "Marchio Inflessibile",
                "desc": "I nemici che colpisci in mischia sono marchiati: hanno svantaggio ad attaccare chiunque non sia tu, e se lo fanno puoi contrattaccarli."
            },
            {
                "level": 7,
                "name": "Manovra di Difesa",
                "desc": "Come reazione aggiungi 1d8 alla CA di un compagno adiacente attaccato; se il colpo va a segno dimezzi il danno subito."
            },
            {
                "level": 10,
                "name": "Trattenere la Linea",
                "desc": "Gli attacchi d'opportunità si attivano anche quando una creatura si muove entro la tua portata e azzerano la sua velocità."
            },
            {
                "level": 15,
                "name": "Carica Violenta",
                "desc": "Se ti muovi di almeno 3m prima di colpire con un'arma, puoi atterrare la creatura prona (TS Forza CD 8+comp+Forza)."
            },
            {
                "level": 18,
                "name": "Sentinella Vigilante",
                "desc": "Puoi compiere una reazione speciale in ogni turno di combattimento (non solo una per round) per attacchi d'opportunità."
            }
        ]
    },
    {
        "name": "Samurai (Samurai)",
        "name_en": "Samurai",
        "class_name": "Guerriero",
        "source": "Xanathar's Guide to Everything",
        "description": "Guerriero dalla volontà indomita, canalizza il proprio spirito per ottenere vantaggio su tutti gli attacchi e rifiutarsi di crollare a terra.",
        "features": [
            {
                "level": 3,
                "name": "Spirito da Combattimento",
                "desc": "Come azione bonus ottieni vantaggio su tutti i tiri per colpire fino alla fine del turno e 5 (fino a 15) PF temporanei (3 usi)."
            },
            {
                "level": 7,
                "name": "Cortigiano Elegante",
                "desc": "Aggiungi la Saggezza alle prove di Carisma (Persuasione) e ottieni competenza nei tiri salvezza su Saggezza."
            },
            {
                "level": 10,
                "name": "Spirito Indomito",
                "desc": "Quando tiri l'iniziativa senza usi di Spirito da Combattimento, ne recuperi uno."
            },
            {
                "level": 15,
                "name": "Colpo Rapido",
                "desc": "Se hai vantaggio a un attacco con arma nel tuo turno puoi rinunciare al vantaggio per sferrare un attacco addizionale."
            },
            {
                "level": 18,
                "name": "Forza Prima della Morte",
                "desc": "Se vieni ridotto a 0 PF puoi usare la reazione per compiere immediatamente un turno completo extra prima di cadere a terra."
            }
        ]
    },
    {
        "name": "Guerriero dell'Eco (Echo Knight)",
        "name_en": "Echo Knight",
        "class_name": "Guerriero",
        "source": "Explorer's Guide to Wildemount",
        "description": "Trascina le linee temporali creando un'eco grigia traslucida di se stesso con cui scambiarsi di posto e attaccare a sorpresa.",
        "features": [
            {
                "level": 3,
                "name": "Manifestare Eco",
                "desc": "Come azione bonus evochi un'eco entro 4.5m da cui puoi far scaturire i tuoi attacchi e con cui scambiarti di posto per 4.5m di movimento."
            },
            {
                "level": 3,
                "name": "Scatenare Incarnazione",
                "desc": "Puoi sferrare un attacco extra dall'eco ogni volta che usi l'azione di Attacco (volte pari a mod Costituzione)."
            },
            {
                "level": 7,
                "name": "Avatar dell'Eco",
                "desc": "Puoi proiettare la tua coscienza nell'eco fino a 300 metri di distanza per esplorare e spiare."
            },
            {
                "level": 10,
                "name": "Martire dell'Ombra",
                "desc": "Come reazione puoi teletrasportare l'eco davanti a un attacco diretto a un alleato, facendo subire il colpo all'eco."
            },
            {
                "level": 15,
                "name": "Potenziale Reclamato",
                "desc": "Quando un'eco viene distrutta guadagni punti ferita temporanei pari a 2d6 + Costituzione."
            },
            {
                "level": 18,
                "name": "Legione di Uno",
                "desc": "Puoi manifestare due echi contemporaneamente e quando tiri l'iniziativa senza usi di Scatenare Incarnazione ne recuperi uno."
            }
        ]
    },
    {
        "name": "Guerriero Psionico (Psi Warrior)",
        "name_en": "Psi Warrior",
        "class_name": "Guerriero",
        "source": "Tasha's Cauldron of Everything",
        "description": "Potenzia la lama e la propria armatura con la telecinesi psionica, respingendo colpi e compiendo salti prodigiosi.",
        "features": [
            {
                "level": 3,
                "name": "Potere Psionico",
                "desc": "Dadi di Energia Psionica (d6/d8/d10/d12) per: Colpo Protettivo (riduci danni agli alleati), Colpo Psionico (danno da forza) e Movimento Telecinetico."
            },
            {
                "level": 7,
                "name": "Balzo Telecinetico",
                "desc": "Come azione bonus ottieni velocità di volare pari al doppio della tua velocità fino alla fine del turno."
            },
            {
                "level": 10,
                "name": "Mente Custodita",
                "desc": "Resistenza ai danni psichici e all'inizio del turno puoi spendere un dado psionico per porre fine a charme o paura."
            },
            {
                "level": 15,
                "name": "Baluardo della Mente",
                "desc": "Conferisci mezza copertura (+2 CA e TS Des) a te e agli alleati entro 9m per 1 minuto."
            },
            {
                "level": 18,
                "name": "Maestro della Telecinesi",
                "desc": "Puoi lanciare l'incantesimo Telecinesi senza componenti verbali o somatiche, usando l'Intelligenza."
            }
        ]
    },
    {
        "name": "Cavaliere Runico (Rune Knight)",
        "name_en": "Rune Knight",
        "class_name": "Guerriero",
        "source": "Tasha's Cauldron of Everything",
        "description": "Incisione delle antiche rune dei giganti su armi e armature: cresce fino a taglia Grande o Enorme aumentando danni e portata.",
        "features": [
            {
                "level": 3,
                "name": "Magia delle Rune",
                "desc": "Incidi rune su armature e armi (Runa delle Nuvole, del Fuoco, del Gelo, della Pietra, della Collina, della Tempesta)."
            },
            {
                "level": 3,
                "name": "Statura del Gigante",
                "desc": "Come azione bonus diventi di taglia Grande per 1 minuto, guadagnando vantaggio a prove/TS di Forza e +1d6 a un attacco per turno."
            },
            {
                "level": 7,
                "name": "Scudo Runico",
                "desc": "Come reazione costringi un nemico che colpisce un tuo alleato a ripetere il tiro per colpire usando il nuovo risultato."
            },
            {
                "level": 10,
                "name": "Grande Statura",
                "desc": "La tua altezza permanente cresce di 3d4 pollici e il danno bonus di Statura del Gigante diventa 1d8."
            },
            {
                "level": 15,
                "name": "Rune del Maestro",
                "desc": "Puoi invocare ogni runa due volte per riposo anziché una."
            },
            {
                "level": 18,
                "name": "Colosso Runico",
                "desc": "Con Statura del Gigante diventi di taglia Enorme, la tua portata aumenta di 1.5m e il danno extra diventa 1d10."
            }
        ]
    },
    {
        "name": "Cavaliere del Dragone Purpureo (Purple Dragon Knight)",
        "name_en": "Purple Dragon Knight",
        "class_name": "Guerriero",
        "source": "Sword Coast Adventurer's Guide",
        "description": "Leggendario cavaliere del Cormyr (Banneret), ispira il coraggio delle truppe e condivide le proprie abilità di ripresa col battaglione.",
        "features": [
            {
                "level": 3,
                "name": "Stendardo della Speranza",
                "desc": "Quando usi Recuperare Energie (Second Wind), fino a tre alleati entro 18m recuperano PF pari al tuo livello da guerriero."
            },
            {
                "level": 7,
                "name": "Emissario Reale",
                "desc": "Competenza nell'abilità Persuasione con bonus di competenza raddoppiato (Maestria)."
            },
            {
                "level": 10,
                "name": "Attacco Ispiratore",
                "desc": "Quando usi Slancio d'Azione (Action Surge), un alleato entro 18m può compiere un attacco con arma come reazione."
            },
            {
                "level": 15,
                "name": "Baluardo",
                "desc": "Quando usi Indomito per ripetere un tiro salvezza su Int, Sag o Carisma, un alleato entro 18m può ripetere lo stesso tiro."
            }
        ]
    },
    {
        "name": "Via del Palmo Aperto (Way of the Open Hand)",
        "name_en": "Way of the Open Hand",
        "class_name": "Monaco",
        "source": "Player's Handbook",
        "description": "La via tradizionale del combattimento marziale a mani nude, manipola il ki dell'avversario atterrandolo, spingendolo o bloccandogli le reazioni, fino al letale Palmo Tremante.",
        "features": [
            {
                "level": 3,
                "name": "Tecnica del Palmo Aperto",
                "desc": "Colpendo con Raffica di Colpi puoi: atterrare prono (TS Des), spingere fino a 4.5m (TS Forza) o togliere le reazioni fino alla fine del tuo prossimo turno."
            },
            {
                "level": 6,
                "name": "Integrità del Corpo",
                "desc": "Come azione puoi recuperare punti ferita pari a 3 volte il tuo livello da monaco. Ricarica con un riposo lungo."
            },
            {
                "level": 11,
                "name": "Tranquillità",
                "desc": "All'inizio di ogni giorno ottieni i benefici dell'incantesimo Santuario fino all'inizio del tuo prossimo riposo lungo."
            },
            {
                "level": 17,
                "name": "Palmo Tremante",
                "desc": "Spendi 3 punti ki per creare vibrazioni letali: come azione successiva puoi costringere la vittima a un TS su Costituzione: se fallisce scende a 0 PF, se supera subisce 10d10 danni necrotici."
            }
        ]
    },
    {
        "name": "Via dell'Ombra (Way of Shadow)",
        "name_en": "Way of Shadow",
        "class_name": "Monaco",
        "source": "Player's Handbook",
        "description": "Monaci ninja che padroneggiano il furto, l'infiltrazione e il teletrasporto da un'ombra all'altra.",
        "features": [
            {
                "level": 3,
                "name": "Arti dell'Ombra",
                "desc": "Spendi 2 punti ki per lanciare Oscurità, Scurovisione, Passare Senza Tracce o Silenzio. Impari il trucchetto Illusione Minore."
            },
            {
                "level": 6,
                "name": "Passo dell'Ombra",
                "desc": "Come azione bonus in penombra o buio puoi teletrasportarti fino a 18m in un altro punto in penombra/buio, ottenendo vantaggio al primo attacco."
            },
            {
                "level": 11,
                "name": "Manto d'Ombre",
                "desc": "Come azione in penombra o buio puoi diventare completamente invisibile finché non attacchi o lanci incantesimi."
            },
            {
                "level": 17,
                "name": "Opportunista",
                "desc": "Quando una creatura entro 1.5m viene colpita da un attacco di qualcun altro, puoi usare la tua reazione per sferrare un attacco da mischia contro di essa."
            }
        ]
    },
    {
        "name": "Via dei Quattro Elementi (Way of the Four Elements)",
        "name_en": "Way of the Four Elements",
        "class_name": "Monaco",
        "source": "Player's Handbook",
        "description": "Canalizza il ki per dominare i quattro elementi primordiali scatenando getti di fiamma, muri d'acqua e raffiche di vento.",
        "features": [
            {
                "level": 3,
                "name": "Discepolo degli Elementi",
                "desc": "Impari Sintonia Elementale e discipline elementali che spendono punti ki per scatenare effetti come Mani Brucianti o Onda Tonante."
            },
            {
                "level": 6,
                "name": "Discipline di 6° Livello",
                "desc": "Puoi apprendere discipline come Pugno dell'Aria Infranta, Zanne del Serpente di Fuoco o Frusta d'Acqua potenziate."
            },
            {
                "level": 11,
                "name": "Discipline di 11° Livello",
                "desc": "Apprendi discipline di alto livello come Cavalcare il Vento (Volare) o Fiamme della Fenice (Palla di Fuoco)."
            },
            {
                "level": 17,
                "name": "Discipline di 17° Livello",
                "desc": "Discipline supreme come Fiume del Gelo Famelico (Cono di Freddo) o Respiro dell'Inverno."
            }
        ]
    },
    {
        "name": "Via della Lunga Morte (Way of the Long Death)",
        "name_en": "Way of the Long Death",
        "class_name": "Monaco",
        "source": "Sword Coast Adventurer's Guide",
        "description": "Monaci ossessionati dai misteri della morte: assorbono l'energia vitale di chi uccidono e spendono ki per rifiutarsi di morire.",
        "features": [
            {
                "level": 3,
                "name": "Tocco della Morte",
                "desc": "Quando riduci una creatura entro 1.5m a 0 PF guadagni punti ferita temporanei pari a mod Saggezza + livello da monaco."
            },
            {
                "level": 6,
                "name": "Presenza Spaventosa",
                "desc": "Come azione costringi ogni creatura entro 9m a un TS Saggezza o essere spaventata da te fino alla fine del tuo prossimo turno."
            },
            {
                "level": 11,
                "name": "Maestria della Morte",
                "desc": "Quando scendi a 0 PF puoi spendere 1 punto ki per scendere invece a 1 PF."
            },
            {
                "level": 17,
                "name": "Tocco dei Dannati",
                "desc": "Spendi da 1 a 10 punti ki: la creatura toccata deve superare un TS su Costituzione o subire 2d10 danni necrotici per ogni punto ki speso."
            }
        ]
    },
    {
        "name": "Via dell'Anima Solare (Way of the Sun Soul)",
        "name_en": "Way of the Sun Soul",
        "class_name": "Monaco",
        "source": "Xanathar's Guide to Everything",
        "description": "Trasforma la propria energia spirituale in dardi di luce radiosa e raggi solari incandescenti proiettati a distanza.",
        "features": [
            {
                "level": 3,
                "name": "Dardo del Sole Radioso",
                "desc": "Sferri attacchi con incantesimo a distanza da 9m usando la Destrezza, infliggendo danni radiosi pari al dado delle arti marziali."
            },
            {
                "level": 6,
                "name": "Colpo dell'Arco Infuocato",
                "desc": "Dopo aver usato l'azione di Attacco puoi spendere 2 punti ki per lanciare Mani Brucianti come azione bonus."
            },
            {
                "level": 11,
                "name": "Esplosione del Sole Candente",
                "desc": "Crei una sfera di luce brillante di 6m di raggio entro 45m: TS Costituzione o 2d6 (fino a 8d6) danni radiosi."
            },
            {
                "level": 17,
                "name": "Scudo Solare",
                "desc": "Emetti luce intensa per 9m. Come reazione quando vieni colpito infliggi 5 + Saggezza danni radiosi all'attaccante."
            }
        ]
    },
    {
        "name": "Via del Maestro Ubriaco (Way of the Drunken Master)",
        "name_en": "Way of the Drunken Master",
        "class_name": "Monaco",
        "source": "Xanathar's Guide to Everything",
        "description": "Finge barcolli e sbandamenti imprevedibili muovendosi con agilità fulminea tra i nemici e reindirizzando i loro colpi a vuoto.",
        "features": [
            {
                "level": 3,
                "name": "Tecnica dell'Ubriaco",
                "desc": "Competenza in Intrattenere e strumenti da birraio. Quando usi Raffica di Colpi ottieni Disimpegno automatico e +3m velocità."
            },
            {
                "level": 6,
                "name": "Ondeggiare Impulsivo",
                "desc": "Rialzarsi da terra costa solo 1.5m di movimento. Quando un nemico ti manca puoi spendere 1 ki per far colpire un'altra creatura adiacente."
            },
            {
                "level": 11,
                "name": "Fortuna dell'Ubriaco",
                "desc": "Spendi 1 punto ki per annullare lo svantaggio a un tiro per colpire, prova di caratteristica o tiro salvezza."
            },
            {
                "level": 17,
                "name": "Raffica Intossicante",
                "desc": "Puoi effettuare fino a tre attacchi addizionali con Raffica di Colpi (fino a 5 colpi totali), purché ciascun attacco colpisca un bersaglio diverso."
            }
        ]
    },
    {
        "name": "Via del Kensei (Way of the Kensei)",
        "name_en": "Way of the Kensei",
        "class_name": "Monaco",
        "source": "Xanathar's Guide to Everything",
        "description": "Dedica la propria vita alla perfezione dell'arma bianca, trasformando spade, archi e alabarde in estensioni vive del proprio corpo.",
        "features": [
            {
                "level": 3,
                "name": "Armi del Kensei",
                "desc": "Scegli armi marziali che contano come armi da monaco. Ottieni Parata Agile (+2 CA in mischia) e Tiro del Kensei (+1d4 a distanza)."
            },
            {
                "level": 6,
                "name": "Uno con la Lama",
                "desc": "Le armi del Kensei contano come magiche e puoi spendere 1 ki per infliggere danni extra pari al dado delle arti marziali."
            },
            {
                "level": 11,
                "name": "Affilare la Lama",
                "desc": "Come azione bonus spendi fino a 3 punti ki per conferire alla tua arma un bonus fino a +3 al tiro per colpire e ai danni per 1 minuto."
            },
            {
                "level": 17,
                "name": "Precisione Infallibile",
                "desc": "Se manchi un attacco con arma da monaco nel tuo turno, puoi ripetere il tiro per colpire."
            }
        ]
    },
    {
        "name": "Via del Sé Astrale (Way of the Astral Self)",
        "name_en": "Way of the Astral Self",
        "class_name": "Monaco",
        "source": "Tasha's Cauldron of Everything",
        "description": "Manifesta un'armatura e possenti braccia spettrali di pura energia ki astrale, combattendo usando la saggezza al posto della forza.",
        "features": [
            {
                "level": 3,
                "name": "Braccia del Sé Astrale",
                "desc": "Come azione bonus evochi braccia spettrali per 10 minuti: usi Saggezza per tiri per colpire, danni e prove di Forza (portata 3m, danni da forza)."
            },
            {
                "level": 6,
                "name": "Visage del Sé Astrale",
                "desc": "Evochi la maschera astrale: scurovisione magica 36m, vantaggio a Intuizione e Intimidire, e voce udibile fino a 180m."
            },
            {
                "level": 11,
                "name": "Corpo del Sé Astrale",
                "desc": "Defletti o assorbi danni elementali come reazione e puoi sferrare un attacco addizionale con le braccia astrali a ogni turno."
            },
            {
                "level": 17,
                "name": "Sé Astrale Risvegliato",
                "desc": "Spendi 5 ki per la forma astrale completa: +2 alla CA e puoi sferrare tre attacchi extra con Raffica di Colpi."
            }
        ]
    },
    {
        "name": "Via del Drago Ascendente (Way of the Ascendant Dragon)",
        "name_en": "Way of the Ascendant Dragon",
        "class_name": "Monaco",
        "source": "Fizban's Treasury of Dragons",
        "description": "Incanala il soffio e la maestà dei draghi cromatici e metallici, volando con ali spettrali e scatenando soffi elementali.",
        "features": [
            {
                "level": 3,
                "name": "Discepolo Draconico",
                "desc": "I tuoi colpi senz'armi possono infliggere acido, freddo, fuoco, fulmine o veleno. Puoi reindirizzare fallimenti sociali con Presenza Draconica."
            },
            {
                "level": 3,
                "name": "Soffio del Drago",
                "desc": "Sostituisci un attacco con un soffio (cono da 6m o linea da 9m): 2 dadi delle arti marziali di danno elementale (TS dimezza)."
            },
            {
                "level": 6,
                "name": "Ali Sfrenate",
                "desc": "Quando usi Passo del Vento manifesti ali draconiche temporanee volando fino alla fine del turno senza provocare AdO."
            },
            {
                "level": 11,
                "name": "Aspetto del Drago",
                "desc": "Crei un'aura di 3m che spaventa i nemici o concede resistenza elementale a te e agli alleati."
            },
            {
                "level": 17,
                "name": "Forma del Drago Ascendente",
                "desc": "Vista cieca 9m, soffi elementali esplosivi devastanti e ali draconiche perenni per 1 minuto."
            }
        ]
    },
    {
        "name": "Via della Misericordia (Way of Mercy)",
        "name_en": "Way of Mercy",
        "class_name": "Monaco",
        "source": "Tasha's Cauldron of Everything",
        "description": "Monaci mascherati da medici della peste, manipolano il flusso vitale per curare ferite con Mani Guaritrici o uccidere all'istante con Mani Nocive.",
        "features": [
            {
                "level": 3,
                "name": "Mani Guaritrici e Nocive",
                "desc": "Spendi 1 ki per curare con il tocco (dado arti marziali + Sag) o infliggere danno necrotico extra con un colpo senz'armi."
            },
            {
                "level": 6,
                "name": "Tocco del Medico",
                "desc": "Le tue Mani Guaritrici curano anche veleno, cecità, sordità, paralisi; le tue Mani Nocive avvelenano la vittima senza tiro salvezza."
            },
            {
                "level": 11,
                "name": "Raffica di Guarigione",
                "desc": "Puoi sostituire ciascun colpo di Raffica di Colpi con Mani Guaritrici senza spendere punti ki extra."
            },
            {
                "level": 17,
                "name": "Mano della Grazia Suprema",
                "desc": "Spendi 5 punti ki per riportare in vita una creatura morta entro 24 ore ripristinando tutti i suoi punti ferita."
            }
        ]
    },
    {
        "name": "Giuramento di Devozione (Oath of Devotion)",
        "name_en": "Oath of Devotion",
        "class_name": "Paladino",
        "source": "Player's Handbook",
        "description": "L'archetipo del cavaliere senza macchia: arma consacrata dalla luce, immunità al fascino e aura di purezza radiosa.",
        "features": [
            {
                "level": 3,
                "name": "Incanalare Divinità: Arma Sacra",
                "desc": "Aggiungi il modificatore di Carisma a tutti i tiri per colpire con l'arma per 1 minuto ed emette luce intensa."
            },
            {
                "level": 3,
                "name": "Incanalare Divinità: Scacciare l'Empio",
                "desc": "Scaccia immondi e non morti entro 9m che falliscono un TS su Saggezza."
            },
            {
                "level": 7,
                "name": "Aura di Devozione",
                "desc": "Tu e gli alleati entro 3m (9m al 18°) non potete essere affascinati."
            },
            {
                "level": 15,
                "name": "Purezza dello Spirito",
                "desc": "Sei costantemente sotto gli effetti dell'incantesimo Protezione dal Bene e dal Male."
            },
            {
                "level": 20,
                "name": "Nimbo Sacro",
                "desc": "Emetti luce solare per 9m per 1 minuto: 10 danni radiosi a turno a immondi/non morti e vantaggio ai TS contro i loro incantesimi."
            }
        ]
    },
    {
        "name": "Giuramento degli Antichi (Oath of the Ancients)",
        "name_en": "Oath of the Ancients",
        "class_name": "Paladino",
        "source": "Player's Handbook",
        "description": "Cavaliere Verde devoto alla luce naturale e alla gioia della vita: un'aura impenetrabile che dimezza i danni da tutti gli incantesimi.",
        "features": [
            {
                "level": 3,
                "name": "Incanalare Divinità: Ira della Natura",
                "desc": "Viticci spettrali avvolgono un nemico entro 3m trattenendolo (TS Forza o Des)."
            },
            {
                "level": 3,
                "name": "Incanalare Divinità: Scacciare l'Infedele",
                "desc": "Scaccia folletti e immondi entro 9m."
            },
            {
                "level": 7,
                "name": "Aura di Interdizione",
                "desc": "Tu e gli alleati entro 3m (9m al 18°) avete resistenza a tutti i danni da incantesimi."
            },
            {
                "level": 15,
                "name": "Sentinella Indomabile",
                "desc": "Quando vieni ridotto a 0 PF puoi scendere invece a 1 PF (1 volta per riposo lungo) e non subisci penalità dall'invecchiamento."
            },
            {
                "level": 20,
                "name": "Campione della Natura",
                "desc": "Ti trasformi in avatar naturale per 1 minuto: recuperi 10 PF a inizio turno, incantesimi lanciabili come azione bonus e nemici vicini svantaggiati."
            }
        ]
    },
    {
        "name": "Giuramento di Vendetta (Oath of Vengeance)",
        "name_en": "Oath of Vengeance",
        "class_name": "Paladino",
        "source": "Player's Handbook",
        "description": "Cacciatore inarrestabile consacrato a punire il male supremo: ottiene vantaggio assoluto contro la sua preda prescelta.",
        "features": [
            {
                "level": 3,
                "name": "Incanalare Divinità: Abiura Nemica",
                "desc": "Spaventa una creatura entro 18m riducendone la velocità a 0 (TS Saggezza)."
            },
            {
                "level": 3,
                "name": "Incanalare Divinità: Voto di Inimicizia",
                "desc": "Come azione bonus ottieni vantaggio a tutti i tiri per colpire contro un bersaglio designato entro 3m per 1 minuto."
            },
            {
                "level": 7,
                "name": "Vendicatore Implacabile",
                "desc": "Colpendo con attacco d'opportunità puoi muoverti fino a metà della tua velocità come parte della reazione senza provocare AdO."
            },
            {
                "level": 15,
                "name": "Anima della Vendetta",
                "desc": "Quando il bersaglio del Voto di Inimicizia compie un attacco, puoi usare la reazione per effettuare un attacco con arma contro di esso."
            },
            {
                "level": 20,
                "name": "Angelo Vendicatore",
                "desc": "Spieghi ali scure per 1 ora (volare 18m) ed emetti un'aura di terrore da 9m che paralizza i nemici spaventati."
            }
        ]
    },
    {
        "name": "Spezza-Giuramento (Oathbreaker)",
        "name_en": "Oathbreaker",
        "class_name": "Paladino",
        "source": "Dungeon Master's Guide",
        "description": "Cavaliere decaduto che ha rinnegato i voti sacri per servire potenze oscure o ambizioni malvagie, dominando non morti e immondi.",
        "features": [
            {
                "level": 3,
                "name": "Incanalare Divinità: Controllare Non Morti",
                "desc": "Assoggetti un non morto di GS inferiore al tuo livello al tuo comando mentale (TS Saggezza)."
            },
            {
                "level": 3,
                "name": "Incanalare Divinità: Aspetto Terrificante",
                "desc": "Spaventi tutte le creature entro 9m per 1 minuto."
            },
            {
                "level": 7,
                "name": "Aura di Odio",
                "desc": "Tu, i tuoi immondi e i tuoi non morti entro 3m aggiungete il tuo modificatore di Carisma ai danni delle armi da mischia."
            },
            {
                "level": 15,
                "name": "Resistenza Sovrannaturale",
                "desc": "Resistenza ai danni contundenti, perforanti e taglienti da armi non magiche."
            },
            {
                "level": 20,
                "name": "Signore delle Tenebre",
                "desc": "Aura di buio di 9m per 1 minuto: 4d10 danni psichici ai nemici a turno e attacchi nemici svantaggiati."
            }
        ]
    },
    {
        "name": "Giuramento della Corona (Oath of the Crown)",
        "name_en": "Oath of the Crown",
        "class_name": "Paladino",
        "source": "Sword Coast Adventurer's Guide",
        "description": "Devoto alla legge del regno e alla tutela della civiltà, incatena i nemici in duello e subisce i danni al posto del proprio sovrano e dei compagni.",
        "features": [
            {
                "level": 3,
                "name": "Incanalare Divinità: Sfida del Campione",
                "desc": "I nemici entro 9m non possono allontanarsi più di 9m da te se falliscono un TS su Saggezza."
            },
            {
                "level": 3,
                "name": "Incanalare Divinità: Marea Ristoratrice",
                "desc": "Cura 1d6 + Carisma a tutti gli alleati sotto la metà dei PF entro 9m."
            },
            {
                "level": 7,
                "name": "Fedeltà Divina",
                "desc": "Quando un alleato entro 1.5m subisce danni, come reazione puoi assorbire tu per intero quel danno."
            },
            {
                "level": 15,
                "name": "Spirito Inflessibile",
                "desc": "Hai vantaggio a tutti i tiri salvezza contro condizioni paralizzato e stordito."
            },
            {
                "level": 20,
                "name": "Campione Esaltato",
                "desc": "Per 1 ora ottieni resistenza ai danni fisici, vantaggio a tutti i tiri salvezza contro la magia e gli alleati vicini superano i tiri salvezza su Morte."
            }
        ]
    },
    {
        "name": "Giuramento di Conquista (Oath of Conquest)",
        "name_en": "Oath of Conquest",
        "class_name": "Paladino",
        "source": "Xanathar's Guide to Everything",
        "description": "Guerriero tiranno d'acciaio spietato: schiaccia la volontà nemica incutendo un terrore paralizzante che infligge danni continui.",
        "features": [
            {
                "level": 3,
                "name": "Incanalare Divinità: Presenza Conquistatrice",
                "desc": "Tutte le creature entro 9m devono superare un TS su Saggezza o essere spaventate per 1 minuto."
            },
            {
                "level": 3,
                "name": "Incanalare Divinità: Colpo Guidato",
                "desc": "Ottieni +10 al tuo tiro per colpire."
            },
            {
                "level": 7,
                "name": "Aura di Conquista",
                "desc": "I nemici spaventati entro 3m (9m al 18°) hanno velocità ridotta a 0 e subiscono danni psichici pari a metà livello paladino ogni turno."
            },
            {
                "level": 15,
                "name": "Ritorsione del Disprezzo",
                "desc": "Chiunque ti colpisca subisce danni psichici pari al tuo modificatore di Carisma."
            },
            {
                "level": 20,
                "name": "Campione Invincibile",
                "desc": "Per 1 minuto ottieni resistenza a tutti i danni, sferri un attacco extra a ogni turno e ottieni colpi critici con 19-20."
            }
        ]
    },
    {
        "name": "Giuramento di Redenzione (Oath of Redemption)",
        "name_en": "Oath of Redemption",
        "class_name": "Paladino",
        "source": "Xanathar's Guide to Everything",
        "description": "Apostolo della pace e della diplomazia che ricorre alla violenza solo come estrema risorsa: riflette la violenza contro chi la scatena.",
        "features": [
            {
                "level": 3,
                "name": "Emissario di Pace",
                "desc": "+5 a tutte le prove di Carisma (Persuasione) per 10 minuti con Incanalare Divinità."
            },
            {
                "level": 3,
                "name": "Rimproverare i Violenti",
                "desc": "Come reazione quando un nemico colpisce un alleato, il nemico deve superare un TS Saggezza o subire danni radiosi pari al danno appena inflitto."
            },
            {
                "level": 7,
                "name": "Aura del Custode",
                "desc": "Come reazione subisci tu il danno destinato a un alleato entro 3m (9m al 18°)."
            },
            {
                "level": 15,
                "name": "Spirito Protettivo",
                "desc": "Recuperi 1d6 + metà livello punti ferita all'inizio di ogni tuo turno se sei sotto la metà dei tuoi PF."
            },
            {
                "level": 20,
                "name": "Emissario della Redenzione",
                "desc": "Resistenza a tutti i danni da qualsiasi creatura e chiunque ti danneggi subisce automaticamente la metà del danno inflitto a te come radioso."
            }
        ]
    },
    {
        "name": "Giuramento di Gloria (Oath of Glory)",
        "name_en": "Oath of Glory",
        "class_name": "Paladino",
        "source": "Tasha's Cauldron of Everything",
        "description": "Eroe epico destinato a compiere imprese leggendarie, aumenta la velocità della schiera e difende i compagni con colpi prodigiosi.",
        "features": [
            {
                "level": 3,
                "name": "Atleta Ineguagliabile",
                "desc": "Vantaggio ad Atletica e Acrobazia, salti aumentati e capacità di carico raddoppiata per 10 minuti."
            },
            {
                "level": 3,
                "name": "Punizione Ispiratrice",
                "desc": "Quando metti a segno una Punizione Divina distribuisci 2d8 + livello paladino PF temporanei tra gli alleati entro 9m."
            },
            {
                "level": 7,
                "name": "Aura di Alacrità",
                "desc": "Tu e gli alleati entro 3m (9m al 18°) avete la velocità aumentata di 3 metri."
            },
            {
                "level": 15,
                "name": "Difesa Gloriosa",
                "desc": "Come reazione aumenti la CA di un compagno attaccato di Carisma; se l'attacco fallisce puoi attaccare l'aggressore."
            },
            {
                "level": 20,
                "name": "Leggenda Vivente",
                "desc": "Per 1 minuto puoi ritirare un tiro per colpire fallito a turno, hai vantaggio a prove di Carisma e puoi trasformare un TS fallito in successo."
            }
        ]
    },
    {
        "name": "Giuramento dei Custodi (Oath of the Watchers)",
        "name_en": "Oath of the Watchers",
        "class_name": "Paladino",
        "source": "Tasha's Cauldron of Everything",
        "description": "Sentinella contro le minacce extraplanari (immondi, aberrazioni ed elementali), conferisce bonus massicci all'iniziativa e respinge gli invasori.",
        "features": [
            {
                "level": 3,
                "name": "Volontà del Custode",
                "desc": "Vantaggio a tutti i tiri salvezza su Int, Sag e Carisma per te e fino a Carisma alleati entro 9m per 1 minuto."
            },
            {
                "level": 3,
                "name": "Scacciare l'Extraplanare",
                "desc": "Scaccia aberrazioni, celestiali, elementali, folletti e immondi entro 9m."
            },
            {
                "level": 7,
                "name": "Aura della Sentinella",
                "desc": "Tu e gli alleati entro 3m (9m al 18°) aggiungete il vostro bonus di competenza ai tiri di iniziativa."
            },
            {
                "level": 15,
                "name": "Rimprovero Vigilante",
                "desc": "Quando tu o un alleato superate un TS su Int, Sag o Carisma, infliggi 2d8 + Carisma danni da forza all'incantatore nemico."
            },
            {
                "level": 20,
                "name": "Campione Mortale",
                "desc": "Visione del Vero 36m, vantaggio ai tiri per colpire contro creature extraplanari e le bandisci nel loro piano natio quando le colpisci."
            }
        ]
    },
    {
        "name": "Cacciatore (Hunter)",
        "name_en": "Hunter",
        "class_name": "Ranger",
        "source": "Player's Handbook",
        "description": "Il prototipo del predatore naturale, sceglie tattiche specializzate per abbattere prede giganti, sciami di mostri o colossi corazzati.",
        "features": [
            {
                "level": 3,
                "name": "Preda del Cacciatore",
                "desc": "Scegli: Sterminatore di Colossi (+1d8 danni a turno a creature ferite), Uccisore di Giganti (reazione contro creature Grandi) o Rompi-Orda (attacco extra contro bersaglio adiacente)."
            },
            {
                "level": 7,
                "name": "Tattiche Difensive",
                "desc": "Scegli: Fuggire dall'Orda (svantaggio AdO nemici), Difesa contro Attacchi Multipli (+4 CA dopo il primo colpo) o Volontà di Ferro (vantaggio TS contro paura)."
            },
            {
                "level": 11,
                "name": "Attacco Multiplo (Cacciatore)",
                "desc": "Scegli Attacco a Raffica (attacchi a distanza contro tutte le creature in un cono) o Attacco Turbinante (attacchi da mischia a tutti i nemici entro 1.5m)."
            },
            {
                "level": 15,
                "name": "Difesa Superiore del Cacciatore",
                "desc": "Scegli Evasione, Schivata Prodigiosa o Deviare l'Attacco."
            }
        ]
    },
    {
        "name": "Signore delle Bestie (Beast Master)",
        "name_en": "Beast Master",
        "class_name": "Ranger",
        "source": "Player's Handbook / TCoE",
        "description": "Combatte in perfetta sintonia simbiotica con un compagno animale leale (Bestia della Terra, del Mare o del Cielo) che attacca e cresce con lui.",
        "features": [
            {
                "level": 3,
                "name": "Compagno Animale Primordiale",
                "desc": "Ti leghi a una bestia fedele che agisce subito dopo di te in combattimento e a cui puoi comandare di attaccare come azione bonus."
            },
            {
                "level": 7,
                "name": "Addestramento Straordinario",
                "desc": "La bestia può Scattare, Disimpegnarsi o Schivare come azione bonus nel suo turno e i suoi attacchi contano come magici."
            },
            {
                "level": 11,
                "name": "Furia Bestiale",
                "desc": "Il tuo compagno animale può effettuare due attacchi anziché uno ogni volta che attacca."
            },
            {
                "level": 15,
                "name": "Condividere Incantesimi",
                "desc": "Quando lanci un incantesimo su te stesso, l'incantesimo ha effetto contemporaneamente anche sul tuo compagno animale se è entro 9m."
            }
        ]
    },
    {
        "name": "Cacciatore delle Ombre (Gloom Stalker)",
        "name_en": "Gloom Stalker",
        "class_name": "Ranger",
        "source": "Xanathar's Guide to Everything",
        "description": "Letale assassino dell'Underdark e della notte, invisibile alle creature dotate di scurovisione e devastante nel round iniziale.",
        "features": [
            {
                "level": 3,
                "name": "Imboscata Terrificante",
                "desc": "Aggiungi la Saggezza all'iniziativa; nel primo turno la tua velocità aumenta di 3m ed effettui un attacco extra che infligge 1d8 danni extra."
            },
            {
                "level": 3,
                "name": "Vista dell'Ombra",
                "desc": "Scurovisione aumentata di 9m e sei completamente invisibile a qualsiasi creatura che fa affidamento sulla scurovisione per vederti nel buio."
            },
            {
                "level": 7,
                "name": "Mente di Ferro",
                "desc": "Ottieni competenza nei tiri salvezza su Saggezza (o Int/Carisma se già competente)."
            },
            {
                "level": 11,
                "name": "Raffica dello Schivatore",
                "desc": "Una volta per turno, se manchi con un attacco con arma puoi sferrare un attacco addizionale."
            },
            {
                "level": 15,
                "name": "Schivata dell'Ombra",
                "desc": "Come reazione quando vieni attaccato puoi imporre svantaggio al tiro per colpire dell'avversario."
            }
        ]
    },
    {
        "name": "Viandante dell'Orizzonte (Horizon Walker)",
        "name_en": "Horizon Walker",
        "class_name": "Ranger",
        "source": "Xanathar's Guide to Everything",
        "description": "Guardiano dei portali planari, teletrasporta se stesso a ogni passo e converte tutti i danni dei suoi colpi in pura energia di forza.",
        "features": [
            {
                "level": 3,
                "name": "Percepire Portali",
                "desc": "Come azione percepisci la distanza e la direzione del portale planare più vicino entro 1.5 km."
            },
            {
                "level": 3,
                "name": "Guerriero Planare",
                "desc": "Come azione bonus converti tutto il danno del tuo prossimo attacco in danno da forza e aggiungi 1d8 (2d8 a liv 11) danni da forza extra."
            },
            {
                "level": 7,
                "name": "Passo Etereo",
                "desc": "Come azione bonus puoi lanciare Forma Eterea senza spendere slot incantesimo fino alla fine del tuo turno corrente."
            },
            {
                "level": 11,
                "name": "Colpo Distorcente",
                "desc": "Prima di ciascuno dei tuoi attacchi con l'azione di Attacco puoi teletrasportarti fino a 3m; se attacchi due bersagli diversi ottieni un terzo attacco."
            },
            {
                "level": 15,
                "name": "Difesa Spettrale",
                "desc": "Come reazione quando subisci danni puoi diventare incorporeo dimezzando tutto il danno subito dall'attacco."
            }
        ]
    },
    {
        "name": "Uccisore di Mostri (Monster Slayer)",
        "name_en": "Monster Slayer",
        "class_name": "Ranger",
        "source": "Xanathar's Guide to Everything",
        "description": "Esperto nel cacciare e disarmare vampiri, draghi, streghe e immondi, analizzando immunità e interrompendo incantesimi nemici.",
        "features": [
            {
                "level": 3,
                "name": "Senso del Cacciatore",
                "desc": "Come azione scopri tutte le immunità, resistenze e vulnerabilità ai danni di una creatura visibile entro 18m."
            },
            {
                "level": 3,
                "name": "Preda dell'Uccisore",
                "desc": "Come azione bonus marchi una creatura entro 18m: infliggi 1d6 danni extra la prima volta che la colpisci in ogni turno."
            },
            {
                "level": 7,
                "name": "Difesa Sovrannaturale",
                "desc": "Aggiungi 1d6 a tutti i tiri salvezza contro incantesimi o abilità della tua Preda dell'Uccisore e alle prove per sfuggire alla sua presa."
            },
            {
                "level": 11,
                "name": "Nemesi della Magia",
                "desc": "Come reazione quando una creatura entro 18m lancia un incantesimo o si teletrasporta, costringila a un TS Saggezza o l'effetto fallisce sprecato."
            },
            {
                "level": 15,
                "name": "Contrattacco dell'Uccisore",
                "desc": "Se la tua preda ti costringe a un tiro salvezza, come reazione puoi sferrarle un attacco; se colpisce superi automaticamente il tiro salvezza."
            }
        ]
    },
    {
        "name": "Viandante Fatato (Fey Wanderer)",
        "name_en": "Fey Wanderer",
        "class_name": "Ranger",
        "source": "Tasha's Cauldron of Everything",
        "description": "Incanala la magia ingannevole della Selva Fatata: aggiunge Saggezza a tutte le prove sociali e rimanda indietro charme e paura nemici.",
        "features": [
            {
                "level": 3,
                "name": "Attacchi Terrificanti",
                "desc": "Una volta per turno infliggi 1d4 (1d6 a liv 11) danni psichici extra a una creatura che colpisci con un'arma."
            },
            {
                "level": 3,
                "name": "Presenza Ultraterrena",
                "desc": "Aggiungi il tuo modificatore di Saggezza a tutte le prove di Carisma e ottieni competenza in Inganno, Intrattenere o Persuasione."
            },
            {
                "level": 7,
                "name": "Torsione Fatata",
                "desc": "Vantaggio ai TS contro charme e paura. Se tu o un alleato vicino superate il tiro, puoi reindirizzare l'effetto su un nemico entro 36m."
            },
            {
                "level": 11,
                "name": "Evocazioni Fatate",
                "desc": "Puoi lanciare Evoca Folletto senza spendere componenti e puoi modificarlo per non richiedere concentrazione."
            },
            {
                "level": 15,
                "name": "Passo Nebbioso",
                "desc": "Puoi lanciare Passo Velato più volte al giorno e portare con te un compagno consenziente ogni volta che ti teletrasporti."
            }
        ]
    },
    {
        "name": "Custode dello Sciame (Swarmkeeper)",
        "name_en": "Swarmkeeper",
        "class_name": "Ranger",
        "source": "Tasha's Cauldron of Everything",
        "description": "Circondato da uno sciame intangibile di insetti, spiriti o piccoli uccelli che pungono i nemici, lo muovono sul campo o lo sollevano in volo.",
        "features": [
            {
                "level": 3,
                "name": "Sciame Radunato",
                "desc": "Colpendo con un'arma puoi: infliggere 1d6 danni perforanti extra, spingere il bersaglio di 4.5m o muoverti tu di 1.5m senza provocare AdO."
            },
            {
                "level": 7,
                "name": "Marea Arricciata",
                "desc": "Ottieni una velocità di volare di 3m e puoi fluttuare per 1 minuto (usi pari a competenza)."
            },
            {
                "level": 11,
                "name": "Sciame Possente",
                "desc": "I danni dello sciame aumentano a 1d8, puoi atterrare i nemici proni e quando ti muovi ottieni mezza copertura fino al prossimo turno."
            },
            {
                "level": 15,
                "name": "Dispersione dello Sciame",
                "desc": "Come reazione quando subisci danni puoi dissolverti nello sciame: ottieni resistenza all'attacco e ti teletrasporti fino a 9m."
            }
        ]
    },
    {
        "name": "Guardiano del Drago (Drakewarden)",
        "name_en": "Drakewarden",
        "class_name": "Ranger",
        "source": "Fizban's Treasury of Dragons",
        "description": "Genera e cresce un leale compagno Drago (Drake) cavalcabile, che evolve da piccolo cucciolo a drago volante gigantesco.",
        "features": [
            {
                "level": 3,
                "name": "Dono Draconico",
                "desc": "Impari il trucchetto Taumaturgia, parli il Draconico e puoi evocare il tuo Cucciolo di Drago che agisce subito dopo di te."
            },
            {
                "level": 7,
                "name": "Legame del Guardiano",
                "desc": "Il drago cresce a taglia Media, può essere cavalcato sul terreno, infligge danni da morso maggiorati e ti conferisce resistenza elementale."
            },
            {
                "level": 11,
                "name": "Soffio del Drago (Drakewarden)",
                "desc": "Come azione tu o il drago potete emettere un possente soffio elementale (cono da 9m o linea da 18m) che infligge 8d6 danni."
            },
            {
                "level": 15,
                "name": "Drago Perfetto",
                "desc": "Il drago diventa di taglia Grande, ottiene ali con velocità di volare pari alla sua velocità sul terreno e il soffio infligge 10d6 danni."
            }
        ]
    },
    {
        "name": "Furfante (Thief)",
        "name_en": "Thief",
        "class_name": "Ladro",
        "source": "Player's Handbook",
        "description": "L'infiltratore classico: rapidità di mano superiore per usare oggetti come azione bonus, scalare veloce e usare qualsiasi oggetto magico.",
        "features": [
            {
                "level": 3,
                "name": "Mani Veloci",
                "desc": "Puoi usare l'Azione Scaltra per: effettuare una prova di Rapidità di Mano, disattivare trappole o Usare un Oggetto come azione bonus."
            },
            {
                "level": 3,
                "name": "Lavoro da Scassinatore",
                "desc": "Scalare non ti costa movimento extra e la distanza dei salti in corsa aumenta del tuo modificatore di Destrezza."
            },
            {
                "level": 9,
                "name": "Furtività Suprema",
                "desc": "Hai vantaggio alle prove di Furtività se ti muovi a non più di metà della tua velocità."
            },
            {
                "level": 13,
                "name": "Usare Oggetti Magici",
                "desc": "Ignori tutti i requisiti di classe, razza e livello per sintonizzarti o utilizzare qualsiasi oggetto magico."
            },
            {
                "level": 17,
                "name": "Riflessi da Ladro",
                "desc": "Durante il primo turno di combattimento puoi compiere due turni completi: uno alla tua iniziativa e uno a iniziativa -10."
            }
        ]
    },
    {
        "name": "Assassino (Assassin)",
        "name_en": "Assassin",
        "class_name": "Ladro",
        "source": "Player's Handbook",
        "description": "Maestro dell'agguato letale e dell'avvelenamento, garantisce colpi critici automatici contro nemici colti di sorpresa.",
        "features": [
            {
                "level": 3,
                "name": "Competenze Bonus (Assassino)",
                "desc": "Competenza negli strumenti da camuffamento e nella borsa da avvelenatore."
            },
            {
                "level": 3,
                "name": "Assassinare",
                "desc": "Vantaggio ai tiri per colpire contro chiunque non abbia ancora agito nel combattimento, e ogni colpo a segno contro un bersaglio sorpreso è un Colpo Critico automatico."
            },
            {
                "level": 9,
                "name": "Infiltrazione Esperta",
                "desc": "Puoi creare false identità inattaccabili complete di documenti, storia personale e abbigliamento in 7 giorni."
            },
            {
                "level": 13,
                "name": "Impostore",
                "desc": "Puoi imitare alla perfezione la parlata, calligrafia e comportamento di un'altra persona dopo averla osservata per 3 ore."
            },
            {
                "level": 17,
                "name": "Colpo Mortale",
                "desc": "Quando colpisci una creatura sorpresa, deve superare un TS su Costituzione o raddoppiare tutti i danni dell'attacco."
            }
        ]
    },
    {
        "name": "Mistificatore Arcano (Arcane Trickster)",
        "name_en": "Arcane Trickster",
        "class_name": "Ladro",
        "source": "Player's Handbook",
        "description": "Combina la furtività del ladro con le illusioni e gli ammaliamenti del mago, manovrando una Mano Magica invisibile per borseggiare.",
        "features": [
            {
                "level": 3,
                "name": "Lancio di Incantesimi (Illusione/Ammaliamento)",
                "desc": "Lanci incantesimi da mago fino al 4° livello usando l'Intelligenza."
            },
            {
                "level": 3,
                "name": "Mano Magica Furtiva",
                "desc": "La tua Mano Magica è invisibile e puoi usarla come azione bonus per scassinare serrature, disinnescare trappole o borseggiare a distanza."
            },
            {
                "level": 9,
                "name": "Imboscata Magica",
                "desc": "Se sei nascosto quando lanci un incantesimo, i bersagli hanno svantaggio ai tiri salvezza contro quell'incantesimo."
            },
            {
                "level": 13,
                "name": "Distrazione Versatile",
                "desc": "Puoi usare la Mano Magica come azione bonus per distrarre un bersaglio entro 1.5m concedendoti vantaggio al tiro per colpire."
            },
            {
                "level": 17,
                "name": "Ladro di Incantesimi",
                "desc": "Come reazione a un incantesimo subito costringi l'incantatore a un TS: se fallisce neghi l'incantesimo e puoi lanciarlo tu per 8 ore."
            }
        ]
    },
    {
        "name": "Inquisitore (Inquisitive)",
        "name_en": "Inquisitive",
        "class_name": "Ladro",
        "source": "Xanathar's Guide to Everything",
        "description": "Investigatore infallibile dalle deduzioni fulminee, legge le mosse dei nemici applicando l'Attacco Furtivo senza bisogno di alleati o vantaggio.",
        "features": [
            {
                "level": 3,
                "name": "Orecchio per l'Inganno",
                "desc": "Tratti qualsiasi risultato di 9 o inferiore su un d20 per Saggezza (Intuizione) come un 10."
            },
            {
                "level": 3,
                "name": "Occhio per il Dettaglio",
                "desc": "Puoi compiere una prova di Percezione o Indagare come azione bonus."
            },
            {
                "level": 3,
                "name": "Combattimento Intuitivo",
                "desc": "Contesa di Intuizione contro Inganno come azione bonus: se vinci applichi l'Attacco Furtivo al bersaglio per 1 minuto senza condizioni."
            },
            {
                "level": 9,
                "name": "Vista Firme",
                "desc": "Vantaggio a Percezione e Indagare se non ti muovi più di metà velocità."
            },
            {
                "level": 13,
                "name": "Sguardo Infallibile",
                "desc": "Percepisci la presenza di illusioni e mutaforma visibili entro 9 metri."
            },
            {
                "level": 17,
                "name": "Occhio per la Debolezza",
                "desc": "Il tuo Attacco Furtivo infligge 3d6 danni addizionali contro il bersaglio di Combattimento Intuitivo."
            }
        ]
    },
    {
        "name": "Pianificatore (Mastermind)",
        "name_en": "Mastermind",
        "class_name": "Ladro",
        "source": "Xanathar's Guide to Everything",
        "description": "Manipolatore da dietro le quinte, dirige la battaglia usando l'azione di Aiuto come azione bonus a distanza fino a 9 metri.",
        "features": [
            {
                "level": 3,
                "name": "Maestro degli Intrighi",
                "desc": "Competenza in kit di travestimento, kit di falsificazione, una lingua e puoi imitare accenti dopo 1 minuto di ascolto."
            },
            {
                "level": 3,
                "name": "Maestro delle Tattiche",
                "desc": "Puoi compiere l'azione di Aiuto come azione bonus con una portata estesa fino a 9 metri."
            },
            {
                "level": 9,
                "name": "Manipolatore Accorto",
                "desc": "Studiando una persona per 1 minuto scopri se le sue statistiche mentali o sociali sono superiori alle tue."
            },
            {
                "level": 13,
                "name": "Deviare Sospetti",
                "desc": "Come reazione quando vieni attaccato puoi frapporre un alleato o nemico vicino facendo subire il colpo a lui."
            },
            {
                "level": 17,
                "name": "Mente Inespugnabile",
                "desc": "I tuoi pensieri non possono essere letti con la telepatia e sei immune a qualsiasi magia che rilevi se stai mentendo."
            }
        ]
    },
    {
        "name": "Esploratore (Scout)",
        "name_en": "Scout",
        "class_name": "Ladro",
        "source": "Xanathar's Guide to Everything",
        "description": "Pattugliatore delle terre selvagge: scivola via dai nemici come reazione e scatena due Attacchi Furtivi nello stesso turno.",
        "features": [
            {
                "level": 3,
                "name": "Schermagliatore",
                "desc": "Come reazione quando un nemico termina il turno entro 1.5m da te, puoi muoverti fino a metà della tua velocità senza provocare AdO."
            },
            {
                "level": 3,
                "name": "Sopravvissuto",
                "desc": "Competenza nelle abilità Natura e Sopravvivenza con competenza raddoppiata (Maestria)."
            },
            {
                "level": 9,
                "name": "Mobilita Superiore",
                "desc": "La tua velocità sul terreno aumenta di 3 metri e la tua velocità di scalare e nuotare eguaglia la tua velocità normale."
            },
            {
                "level": 13,
                "name": "Maestro d'Imboscata",
                "desc": "Vantaggio all'iniziativa; il primo bersaglio che colpisci nel primo round concede vantaggio agli attacchi dei tuoi alleati."
            },
            {
                "level": 17,
                "name": "Colpo Improvviso",
                "desc": "Puoi effettuare un attacco addizionale con l'azione bonus e puoi applicare l'Attacco Furtivo due volte nello stesso turno su bersagli diversi."
            }
        ]
    },
    {
        "name": "Spadaccino (Swashbuckler)",
        "name_en": "Swashbuckler",
        "class_name": "Ladro",
        "source": "Xanathar's Guide to Everything",
        "description": "Duellante carismatico e audace, applica l'Attacco Furtivo in duello solitario 1 contro 1 e non subisce attacchi d'opportunità.",
        "features": [
            {
                "level": 3,
                "name": "Passo Flessuoso",
                "desc": "Se attacchi una creatura in mischia non subisci attacchi d'opportunità da essa per il resto del turno."
            },
            {
                "level": 3,
                "name": "Audacia Spavalda",
                "desc": "Aggiungi il modificatore di Carisma all'iniziativa. Applichi l'Attacco Furtivo a un nemico se sei entro 1.5m da esso e nessun altro è entro 1.5m da te."
            },
            {
                "level": 9,
                "name": "Panache",
                "desc": "Prova di Carisma (Persuasione) contro Saggezza (Intuizione) come azione: affascini un non combattente o costringi un nemico a mirare solo te con svantaggio verso gli altri."
            },
            {
                "level": 13,
                "name": "Manovra Elegante",
                "desc": "Puoi usare l'azione bonus per ottenere vantaggio alla tua prossima prova di Atletica o Acrobazia nello stesso turno."
            },
            {
                "level": 17,
                "name": "Maestro Duellante",
                "desc": "Se manchi un attacco puoi tirarlo di nuovo con vantaggio (1 volta per riposo breve o lungo)."
            }
        ]
    },
    {
        "name": "Fantasma (Phantom)",
        "name_en": "Phantom",
        "class_name": "Ladro",
        "source": "Tasha's Cauldron of Everything",
        "description": "Comunica con le anime dei trapassati, rubando schegge d'anima dai cadaveri per fluttuare come uno spettro e infliggere danni necrotici a catena.",
        "features": [
            {
                "level": 3,
                "name": "Sussurri dei Morti",
                "desc": "A ogni riposo ottieni competenza in una qualsiasi abilità o strumento a scelta canalizzando uno spirito defunto."
            },
            {
                "level": 3,
                "name": "Lamenti dalla Tomba",
                "desc": "Quando metti a segno un Attacco Furtivo infliggi metà dei dadi di danno furtivo come danni necrotici a un secondo nemico entro 9m."
            },
            {
                "level": 9,
                "name": "Gettone delle Anime",
                "desc": "Quando una creatura muore entro 9m catturi una scheggia d'anima: ti conferisce vantaggio a tiri salvezza su Costituzione e Morte."
            },
            {
                "level": 13,
                "name": "Camminatore Fantasma",
                "desc": "Come azione bonus diventi incorporeo (volare 3m, attraversi creature e muri) per 10 minuti."
            },
            {
                "level": 17,
                "name": "Amico della Morte",
                "desc": "I Lamenti dalla Tomba infliggono danno a entrambi i bersagli contemporaneamente e recuperi una scheggia d'anima a ogni riposo."
            }
        ]
    },
    {
        "name": "Lama Psionica (Soulknife)",
        "name_en": "Soulknife",
        "class_name": "Ladro",
        "source": "Tasha's Cauldron of Everything",
        "description": "Manifesta letali lame di pura energia psionica scintillante che trafiggono la mente senza lasciare ferite esteriori né fare alcun rumore.",
        "features": [
            {
                "level": 3,
                "name": "Potere Psionico (Ladro)",
                "desc": "Dadi di energia psionica (d6/d8/d10/d12) per: Talento Potenziato (aggiungi il dado alle prove fallite) e Sussurri Psionici (telepatia di gruppo)."
            },
            {
                "level": 3,
                "name": "Lame Psichiche",
                "desc": "Manifesti lame psioniche dal nulla: attacco da mischia o a distanza (18m) che infligge 1d6 + Des danni psichici e attacco bonus con seconda lama (1d4)."
            },
            {
                "level": 9,
                "name": "Lame dell'Anima",
                "desc": "Teletrasporto psionico lanciando la lama fino a un punto (distanza pari al dado x 3 metri) e aggiungi il dado al tiro per colpire se manchi."
            },
            {
                "level": 13,
                "name": "Velo Psichico",
                "desc": "Come azione diventi magicamente invisibile per 1 ora (o finché non infliggi danno a qualcuno)."
            },
            {
                "level": 17,
                "name": "Dilaniare la Mente",
                "desc": "Quando metti a segno un Attacco Furtivo costringi la vittima a un TS Saggezza o essere stordita per 1 minuto."
            }
        ]
    },
    {
        "name": "Discendenza Draconica (Draconic Bloodline)",
        "name_en": "Draconic Bloodline",
        "class_name": "Stregone",
        "source": "Player's Handbook",
        "description": "Il sangue dei draghi scorre nelle vene: scaglie che aumentano la CA a 13 + Des, ali da drago permanenti e potenza elementale devastante.",
        "features": [
            {
                "level": 1,
                "name": "Antenato Draconico",
                "desc": "Scegli un tipo di drago (Rosso, Oro, Blu, ecc.) che determina il tipo di danno associato e parli il Draconico."
            },
            {
                "level": 1,
                "name": "Resilienza Draconica",
                "desc": "+1 PF per livello da stregone e la tua CA senza armatura è pari a 13 + modificatore di Destrezza."
            },
            {
                "level": 6,
                "name": "Affinità Elementale",
                "desc": "Aggiungi il modificatore di Carisma ai danni degli incantesimi del tuo tipo elementale e puoi spendere 1 punto stregoneria per ottenere resistenza."
            },
            {
                "level": 14,
                "name": "Ali di Drago",
                "desc": "Come azione bonus manifesti ali di drago dalla schiena ottenendo velocità di volare pari alla tua velocità di movimento."
            },
            {
                "level": 18,
                "name": "Presenza Draconica",
                "desc": "Come azione spendi 5 punti stregoneria per emanare un'aura da 18m che affascina o spaventa tutti i nemici per 1 minuto."
            }
        ]
    },
    {
        "name": "Magia Selvaggia (Wild Magic)",
        "name_en": "Wild Magic",
        "class_name": "Stregone",
        "source": "Player's Handbook",
        "description": "Canalizza il caos puro del multiverso: ogni incantesimo rischia di innescare una Sovrattassa di Magia Selvaggia dagli effetti imprevedibili.",
        "features": [
            {
                "level": 1,
                "name": "Impulso di Magia Selvaggia",
                "desc": "Dopo aver lanciato un incantesimo di 1° livello o superiore, il DM può farti tirare un d20: con un 1 tiri sulla tabella della Magia Selvaggia (50 effetti)."
            },
            {
                "level": 1,
                "name": "Maree del Caos",
                "desc": "Ottieni vantaggio a un tiro per colpire, prova o tiro salvezza. Ricarica con riposo lungo o quando il DM attiva un Impulso Selvaggio."
            },
            {
                "level": 6,
                "name": "Piegare la Sorte",
                "desc": "Come reazione spendi 2 punti stregoneria per aggiungere o sottrarre 1d4 dal tiro di una creatura visibile."
            },
            {
                "level": 14,
                "name": "Caos Controllato",
                "desc": "Ogni volta che tiri sulla tabella di Magia Selvaggia, tiri due volte e scegli quale dei due effetti applicare."
            },
            {
                "level": 18,
                "name": "Bombardamento Magico",
                "desc": "Se tiri il massimo su uno dei dadi di danno di un incantesimo, tiri un dado di danno addizionale aggiungendolo al totale."
            }
        ]
    },
    {
        "name": "Anima Divina (Divine Soul)",
        "name_en": "Divine Soul",
        "class_name": "Stregone",
        "source": "Xanathar's Guide to Everything",
        "description": "Erede di una stirpe celestiale o divina, può apprendere tutti gli incantesimi sia dalla lista dello Stregone che del Chierico.",
        "features": [
            {
                "level": 1,
                "name": "Magia Divina",
                "desc": "Puoi scegliere i tuoi incantesimi conosciuti sia dalla lista dello Stregone che dalla lista del Chierico."
            },
            {
                "level": 1,
                "name": "Favorito dagli Dei",
                "desc": "Se fallisci un tiro per colpire o un tiro salvezza, puoi aggiungere 2d4 al risultato potendo trasformare il fallimento in successo."
            },
            {
                "level": 6,
                "name": "Guarigione Potenziata",
                "desc": "Spendi 1 punto stregoneria per ritirare qualsiasi numero di dadi di cura lanciati da te o da un alleato vicino."
            },
            {
                "level": 14,
                "name": "Ali Alate",
                "desc": "Come azione bonus manifesti ali piumate angeliche (o d'aquila o pipistrello) ottenendo velocità di volare 9m."
            },
            {
                "level": 18,
                "name": "Recupero Ultraterreno",
                "desc": "Come azione bonus recuperi punti ferita pari a metà dei tuoi PF massimi se sei sotto la metà dei tuoi PF."
            }
        ]
    },
    {
        "name": "Magia delle Ombre (Shadow Magic)",
        "name_en": "Shadow Magic",
        "class_name": "Stregone",
        "source": "Xanathar's Guide to Everything",
        "description": "Toccato dall'energia oscura della Coltre d'Ombra (Shadowfell), sopravvive alla morte, vede nell'oscurità magica ed evoca segugi spettrali.",
        "features": [
            {
                "level": 1,
                "name": "Occhi dell'Oscurità",
                "desc": "Scurovisione 36m. Puoi lanciare Oscurità spendendo 2 punti stregoneria e puoi vedere perfettamente attraverso di essa."
            },
            {
                "level": 1,
                "name": "Forza dell'Oltretomba",
                "desc": "Quando scendi a 0 PF puoi effettuare un TS su Carisma (CD 5 + danno) per scendere invece a 1 PF."
            },
            {
                "level": 6,
                "name": "Segugio della Sventura",
                "desc": "Spendi 3 punti stregoneria per evocare un lupo d'ombra che bersaglia un nemico: il nemico ha svantaggio contro tutti i tuoi incantesimi."
            },
            {
                "level": 14,
                "name": "Camminare nell'Ombra",
                "desc": "Come azione bonus in penombra o buio ti teletrasporti fino a 36m in un altro punto in penombra o buio."
            },
            {
                "level": 18,
                "name": "Forma dell'Ombra",
                "desc": "Spendi 6 punti stregoneria per trasformarti in ombra incorporea per 1 minuto: resistenza a tutti i danni tranne forza e radioso."
            }
        ]
    },
    {
        "name": "Stregoneria della Tempesta (Storm Sorcery)",
        "name_en": "Storm Sorcery",
        "class_name": "Stregone",
        "source": "Xanathar's Guide to Everything",
        "description": "Padroneggia il potere dei fulmini, dei tuoni e dei venti impetuosi, volando a scatti ogni volta che lancia un incantesimo.",
        "features": [
            {
                "level": 1,
                "name": "Oratore del Vento",
                "desc": "Impari il Primordiale e tutti i suoi dialetti (Aquan, Auran, Ignan, Terran)."
            },
            {
                "level": 1,
                "name": "Magia Tempestosa",
                "desc": "Subito prima o dopo aver lanciato un incantesimo di 1° livello o superiore, puoi volare fino a 3m come azione bonus senza provocare AdO."
            },
            {
                "level": 6,
                "name": "Cuore della Tempesta",
                "desc": "Resistenza a fulmine e tuono. Quando lanci magie di fulmine/tuono infliggi danni da tuono o fulmine ai nemici entro 3m."
            },
            {
                "level": 6,
                "name": "Guida della Tempesta",
                "desc": "Puoi arrestare o deviare la pioggia e i venti attorno a te per 6 metri."
            },
            {
                "level": 14,
                "name": "Furia della Tempesta",
                "desc": "Come reazione quando vieni colpito infliggi danni da fulmine pari al tuo livello e respingi l'attaccante di 6m."
            },
            {
                "level": 18,
                "name": "Anima del Vento",
                "desc": "Immunità a fulmine e tuono, velocità di volare 18m e puoi conferire velocità di volare 9m a compagni per 1 ora."
            }
        ]
    },
    {
        "name": "Mente Aberrante (Aberrant Mind)",
        "name_en": "Aberrant Mind",
        "class_name": "Stregone",
        "source": "Tasha's Cauldron of Everything",
        "description": "Mutato da un parassita illithid o da un'aberrazione del Reame Lontano, manipola la telepatia e lancia incantesimi psionici senza componenti.",
        "features": [
            {
                "level": 1,
                "name": "Parlata Telepatica",
                "desc": "Stabilisci un legame telepatico a due vie con una creatura entro un numero di chilometri pari al mod Carisma."
            },
            {
                "level": 1,
                "name": "Incantesimi Psionici",
                "desc": "Incantesimi psionici extra sempre preparati (Braccia di Hadar, Corona di Follia, Calmare Emozioni, Tentacoli di Evard, ecc.)."
            },
            {
                "level": 6,
                "name": "Stregoneria Psionica",
                "desc": "Puoi lanciare gli incantesimi della lista psionica spendendo punti stregoneria senza componenti verbali, somatiche o materiali non preziose."
            },
            {
                "level": 6,
                "name": "Difese Psichiche",
                "desc": "Resistenza ai danni psichici e vantaggio a tutti i tiri salvezza contro condizioni affascinato e spaventato."
            },
            {
                "level": 14,
                "name": "Forma della Rivelazione",
                "desc": "Spendi 1-4 punti stregoneria per trasformarti: volare fluttuando, nuotare e respirare sott'acqua, attraversare fessure di 2.5cm o vista invisibilità."
            },
            {
                "level": 18,
                "name": "Implosione Spaziale",
                "desc": "Come azione ti teletrasporti fino a 36m lasciando una singolarità che risucchia i nemici infliggendo 3d10 danni da forza."
            }
        ]
    },
    {
        "name": "Anima Meccanica (Clockwork Soul)",
        "name_en": "Clockwork Soul",
        "class_name": "Stregone",
        "source": "Tasha's Cauldron of Everything",
        "description": "Imbevuto dell'ordine cosmico e degli ingranaggi di Mechanus, neutralizza il caos dei dadi e ripristina la simmetria sul campo di battaglia.",
        "features": [
            {
                "level": 1,
                "name": "Magia Meccanica",
                "desc": "Incantesimi di protezione e ordine sempre preparati (Allarme, Armatura di Agathys, Ristorare Inferiore, Dissolvi Magie, ecc.)."
            },
            {
                "level": 1,
                "name": "Ripristinare l'Equilibrio",
                "desc": "Come reazione entro 18m annulli qualsiasi vantaggio o svantaggio a un tiro per colpire, prova o tiro salvezza."
            },
            {
                "level": 6,
                "name": "Baluardo della Legge",
                "desc": "Spendi fino a 5 punti stregoneria per creare uno scudo di d8 (pari ai punti spesi) che assorbe danni destinati a te o un alleato."
            },
            {
                "level": 14,
                "name": "Trance dell'Ordine",
                "desc": "Come azione bonus entri in sintonia meccanica: qualsiasi tiro del d20 pari a 9 o inferiore conta come un 10."
            },
            {
                "level": 18,
                "name": "Cavalcata Meccanica",
                "desc": "Evochi spiriti d'ingranaggio in un cubo di 9m: curi 100 PF tra gli alleati, ripari oggetti e dissolvi incantesimi fino al 6° livello."
            }
        ]
    },
    {
        "name": "Stregoneria Lunare (Lunar Sorcery)",
        "name_en": "Lunar Sorcery",
        "class_name": "Stregone",
        "source": "Dragonlance: Shadow of the Black Rose",
        "description": "Canalizza le tre fasi della luna (Luna Piena, Luna Nuova, Mezza Luna) commutando incantesimi preparati e riducendo i costi di metamagia.",
        "features": [
            {
                "level": 1,
                "name": "Incarnazione Lunare",
                "desc": "Scegli quale fase lunare manifestare (Piena, Nuova o Mezza) ottenendo un trucchetto e incantesimi gratuiti legati a quella fase."
            },
            {
                "level": 6,
                "name": "Barlumi della Luna",
                "desc": "Spendi 1 punto stregoneria per ridurre di 1 punto il costo della metamagia quando lanci incantesimi della tua fase corrente."
            },
            {
                "level": 14,
                "name": "Crescente Lunare",
                "desc": "Come azione bonus cambi istantaneamente la tua fase lunare attiva scatenando un effetto radioso o necrotico contro i nemici vicini."
            },
            {
                "level": 18,
                "name": "Potere delle Maree Celesti",
                "desc": "Ottieni i benefici di tutte e tre le fasi contemporaneamente per 1 minuto una volta al giorno."
            }
        ]
    },
    {
        "name": "Il Signore Fatato (The Archfey)",
        "name_en": "The Archfey",
        "class_name": "Warlock",
        "source": "Player's Handbook",
        "description": "Patto stretto con una nobile entità della Selva Fatata: affascina folle, svanisce nella nebbia quando colpito e proietta illusioni da incubo.",
        "features": [
            {
                "level": 1,
                "name": "Presenza Fatata",
                "desc": "Come azione costringi le creature in un cubo di 3m a un TS Saggezza o essere affascinate o spaventate da te fino alla fine del tuo prossimo turno."
            },
            {
                "level": 6,
                "name": "Fuga Nebbiosa",
                "desc": "Come reazione quando subisci danni diventi invisibile e ti teletrasporti fino a 18m in uno spazio non occupato visibile."
            },
            {
                "level": 10,
                "name": "Difesa Allettante",
                "desc": "Immune all'ammaliamento. Quando qualcuno tenta di affascinarti puoi rivoltare l'effetto contro di lui affascinandolo per 1 minuto."
            },
            {
                "level": 14,
                "name": "Delirio Oscuro",
                "desc": "Intrappoli una creatura in un labirinto illusorio di terrore per 1 minuto (TS Saggezza)."
            }
        ]
    },
    {
        "name": "L'Immondo (The Fiend)",
        "name_en": "The Fiend",
        "class_name": "Warlock",
        "source": "Player's Handbook",
        "description": "Patto stretto con un signore dei Nove Inferi o dell'Abisso: ruba la vitalità di chi uccide, piega il destino e scaglia i nemici all'Inferno.",
        "features": [
            {
                "level": 1,
                "name": "Benedizione dell'Oscuro",
                "desc": "Quando riduci una creatura ostile a 0 PF guadagni punti ferita temporanei pari a mod Carisma + livello da warlock."
            },
            {
                "level": 6,
                "name": "Fortuna dell'Oscuro",
                "desc": "Aggiungi 1d10 a una prova di caratteristica o a un tiro salvezza una volta per riposo."
            },
            {
                "level": 10,
                "name": "Resistenza Immonda",
                "desc": "Scegli un tipo di danno a ogni riposo a cui ottieni resistenza totale (tranne danni da armi magiche o argento)."
            },
            {
                "level": 14,
                "name": "Gettare all'Inferno",
                "desc": "Quando colpisci una creatura con un attacco la scagli istantaneamente nei piani inferiori: scompare fino alla fine del tuo prossimo turno e subisce 10d10 danni psichici."
            }
        ]
    },
    {
        "name": "Il Grande Antico (The Great Old One)",
        "name_en": "The Great Old One",
        "class_name": "Warlock",
        "source": "Player's Handbook",
        "description": "Legato a divinità aliene cosmiche come Cthulhu o Dendar, comunica telepaticamente, protegge la mente e crea schiavi dominati.",
        "features": [
            {
                "level": 1,
                "name": "Mente Risvegliata",
                "desc": "Puoi comunicare telepaticamente con qualsiasi creatura entro 9 metri purché conosca almeno un linguaggio."
            },
            {
                "level": 6,
                "name": "Scudo Entropico",
                "desc": "Come reazione imponi svantaggio al tiro per colpire di un nemico; se manca, il tuo prossimo attacco contro di lui ha vantaggio."
            },
            {
                "level": 10,
                "name": "Scudo Psichico",
                "desc": "I tuoi pensieri non possono essere letti, ottieni resistenza ai danni psichici e rifletti il danno psichico subito all'aggressore."
            },
            {
                "level": 14,
                "name": "Creare Schiavo",
                "desc": "Tocchi un umanoide incapacitato legandolo telepaticamente a te: diventa affascinato da te in modo permanente finché non viene rimosso con Rimuovi Maledizione."
            }
        ]
    },
    {
        "name": "L'Immortale (The Undying)",
        "name_en": "The Undying",
        "class_name": "Warlock",
        "source": "Sword Coast Adventurer's Guide",
        "description": "Patto con un lich antico o un faraone immortale: rifiuta la morte, respinge i non morti e rigenera le proprie membra.",
        "features": [
            {
                "level": 1,
                "name": "Tra la Vita e la Morte",
                "desc": "Impari Salvare i Morenti. I non morti devono superare un TS Saggezza per poterti attaccare direttamente."
            },
            {
                "level": 6,
                "name": "Sfidare la Morte",
                "desc": "Quando superi un TS su Morte o usi Salvare i Morenti recuperi 1d8 + Costituzione punti ferita (1 volta per riposo lungo)."
            },
            {
                "level": 10,
                "name": "Natura Immortale",
                "desc": "Non hai bisogno di respirare, cibo o acqua, invecchi solo di 1 anno ogni 10 e sei immune a invecchiamento magico."
            },
            {
                "level": 14,
                "name": "Vita Indistruttibile",
                "desc": "Come azione bonus recuperi 1d8 + livello warlock PF e puoi riattaccare arti recisi."
            }
        ]
    },
    {
        "name": "Il Celestiale (The Celestial)",
        "name_en": "The Celestial",
        "class_name": "Warlock",
        "source": "Xanathar's Guide to Everything",
        "description": "Patto con un solare, un ki-rin o un unicorno: guarisce con riserve di dadi di luce e incenerisce i nemici con fiamme sacre e radiose.",
        "features": [
            {
                "level": 1,
                "name": "Guarigione della Luce",
                "desc": "Riserva di dadi d6 pari a 1 + livello warlock per curare come azione bonus entro 18m senza consumare slot incantesimo."
            },
            {
                "level": 1,
                "name": "Trucchetti Bonus",
                "desc": "Apprendi Luce e Fiamma Sacra."
            },
            {
                "level": 6,
                "name": "Anima Radiosa",
                "desc": "Resistenza ai danni radiosi e aggiungi Carisma ai danni da fuoco o radiosi dei tuoi incantesimi."
            },
            {
                "level": 10,
                "name": "Resilienza Celestiale",
                "desc": "Ottieni PF temporanei pari a livello warlock + Carisma alla fine di ogni riposo (e Carisma a fino a cinque alleati)."
            },
            {
                "level": 14,
                "name": "Vendetta Celestiale",
                "desc": "Quando effettui un TS contro la morte puoi balzare in piedi con metà dei PF massimi accecando i nemici vicini per 2d8 + Carisma radioso."
            }
        ]
    },
    {
        "name": "La Lama del Malocchio (The Hexblade)",
        "name_en": "The Hexblade",
        "class_name": "Warlock",
        "source": "Xanathar's Guide to Everything",
        "description": "Patto con le entità senzienti della Regina delle Ombre: attacca con armi usando il Carisma, indossa armature medie e vincola spettri al proprio comando.",
        "features": [
            {
                "level": 1,
                "name": "Guerriero del Malocchio (Hex Warrior)",
                "desc": "Competenza nelle armature medie, scudi e armi marziali. Usi il Carisma per i tiri per colpire e danni delle armi."
            },
            {
                "level": 1,
                "name": "Maledizione del Malocchio",
                "desc": "Marchi un nemico per 1 minuto: aggiungi bonus di competenza ai danni, critici con 19-20 e recuperi PF pari a livello + Carisma alla sua morte."
            },
            {
                "level": 6,
                "name": "Spettro Accattivato",
                "desc": "Quando uccidi un umanoide ne rianimi lo spettro che combatte per te fino al termine del tuo prossimo riposo lungo."
            },
            {
                "level": 10,
                "name": "Armatura di Malocchio",
                "desc": "Se il bersaglio maledetto ti colpisce con un attacco, tira 1d6: con un 4 o più il colpo ti manca completamente."
            },
            {
                "level": 14,
                "name": "Maestro del Malocchio",
                "desc": "Quando il bersaglio maledetto muore puoi trasferire immediatamente la maledizione su un'altra creatura senza consumare usi."
            }
        ]
    },
    {
        "name": "L'Abissale delle Profondità (The Fathomless)",
        "name_en": "The Fathomless",
        "class_name": "Warlock",
        "source": "Tasha's Cauldron of Everything",
        "description": "Patto con kraken o signori degli oceani profondi, evoca tentacoli spettrali che colpiscono e proteggono e viaggia nelle profondità marine.",
        "features": [
            {
                "level": 1,
                "name": "Tentacolo degli Abissi",
                "desc": "Come azione bonus crei un tentacolo spettrale entro 18m che attacca (1d8 danni da freddo) e riduce la velocità di 3m."
            },
            {
                "level": 1,
                "name": "Dono del Mare",
                "desc": "Velocità di nuoto 12m e puoi respirare sott'acqua liberamente."
            },
            {
                "level": 6,
                "name": "Anima Oceanica",
                "desc": "Resistenza ai danni da freddo e puoi comunicare telepaticamente sott'acqua."
            },
            {
                "level": 6,
                "name": "Tentacolo Guardiano",
                "desc": "Il tentacolo riduce di 1d8 i danni subiti da te o un alleato vicino come reazione."
            },
            {
                "level": 10,
                "name": "Presa Rinserrante",
                "desc": "Quando lanci Tentacoli Neri di Evard ottieni punti ferita temporanei e la tua concentrazione non può essere interrotta."
            },
            {
                "level": 14,
                "name": "Tuffo nelle Profondità",
                "desc": "Puoi teletrasportare te e fino a cinque alleati attraverso l'acqua fino a 1.5 km di distanza in un bacino idrico noto."
            }
        ]
    },
    {
        "name": "Il Genio (The Genie)",
        "name_en": "The Genie",
        "class_name": "Warlock",
        "source": "Tasha's Cauldron of Everything",
        "description": "Patto con un nobile Dao (Terra), Djiin (Aria), Efreeti (Fuoco) o Marid (Acqua), custodisce la propria anima in una lampada magica e realizza desideri.",
        "features": [
            {
                "level": 1,
                "name": "Ricettacolo del Genio",
                "desc": "Possiedi una lampada/anello in cui puoi rifugiarti come santuario extradimensionale ed infliggi danno elementale extra a turno."
            },
            {
                "level": 6,
                "name": "Dono Elementale",
                "desc": "Resistenza al tipo elementale del tuo patrono e puoi volare (velocità 9m fluttuando) come azione bonus per 10 minuti."
            },
            {
                "level": 10,
                "name": "Santuario del Ricettacolo",
                "desc": "Puoi portare fino a cinque alleati all'interno della tua lampada per completare un riposo breve in soli 10 minuti."
            },
            {
                "level": 14,
                "name": "Desiderio Limitato",
                "desc": "Chiedi al genio di esaudire un desiderio: lanci qualsiasi incantesimo di 1°-6° livello di qualsiasi classe come un'azione."
            }
        ]
    },
    {
        "name": "Il Non Morto (The Undead)",
        "name_en": "The Undead",
        "class_name": "Warlock",
        "source": "Van Richten's Guide to Ravenloft",
        "description": "Patto con Azalin Rex, Strahd o Acererak, assume una Forma di Terrore spettrale, trasforma gli attacchi in danno necrotico e si proietta come spirito.",
        "features": [
            {
                "level": 1,
                "name": "Forma del Terrore",
                "desc": "Come azione bonus assumi fattezze scheletriche per 1 minuto: PF temporanei, immunità alla paura e spaventi chi colpisci."
            },
            {
                "level": 6,
                "name": "Tocco Sepolcrale",
                "desc": "Non hai bisogno di mangiare, bere o respirare. Una volta per turno converti i tuoi danni in necrotico aggiungendo un dado extra."
            },
            {
                "level": 10,
                "name": "Guscio Necrotico",
                "desc": "Resistenza ai danni necrotici (immunità in Forma del Terrore). Se scendi a 0 PF esplodi (2d10 necrotico) e torni a 1 PF."
            },
            {
                "level": 14,
                "name": "Proiezione Spirituale",
                "desc": "Proietti il tuo spirito fuori dal corpo per 1 ora: resistenza a danni fisici, voli a 9m e puoi volare attraverso i muri solidi."
            }
        ]
    },
    {
        "name": "Scuola di Abiura (School of Abjuration)",
        "name_en": "School of Abjuration",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Specialista delle barriere protettive, crea un Interdizione Arcana che assorbe tutti i danni per sé e per i propri alleati.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente dell'Abiura",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Abiura nel libro degli incantesimi."
            },
            {
                "level": 2,
                "name": "Interdizione Arcana",
                "desc": "Lanciando un'abiura crei uno scudo magico con PF pari al doppio del livello mago + mod Int che subisce i danni al posto tuo."
            },
            {
                "level": 6,
                "name": "Interdizione Proiettata",
                "desc": "Come reazione puoi usare la tua Interdizione Arcana per assorbire danni diretti a un alleato entro 9m."
            },
            {
                "level": 10,
                "name": "Abiura Migliorata",
                "desc": "Aggiungi il tuo bonus di competenza alle prove di caratteristica per Controincantesimo e Dissolvi Magie."
            },
            {
                "level": 14,
                "name": "Resistenza agli Incantesimi",
                "desc": "Hai vantaggio a tutti i tiri salvezza contro gli incantesimi e resistenza a tutti i danni da incantesimi."
            }
        ]
    },
    {
        "name": "Scuola di Evocazione (School of Conjuration)",
        "name_en": "School of Conjuration",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Crea materia e oggetti dal nulla, si teletrasporta scambiando posizione con gli alleati ed evoca servitori con concentrazione infrangibile.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente dell'Evocazione",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Evocazione."
            },
            {
                "level": 2,
                "name": "Evocazione Minore",
                "desc": "Come azione crei un oggetto non magico non vivente in mano del peso fino a 5 kg che dura 1 ora o finché non subisce danni."
            },
            {
                "level": 6,
                "name": "Traslocazione Benigna",
                "desc": "Come azione puoi teletrasportarti fino a 9m o scambiare posizione con un alleato consenziente entro 9m (si ricarica lanciando evocazioni)."
            },
            {
                "level": 10,
                "name": "Evocazione Focalizzata",
                "desc": "La tua concentrazione su incantesimi di Evocazione non può essere interrotta dal subire danni."
            },
            {
                "level": 14,
                "name": "Evocazioni Resistenti",
                "desc": "Qualsiasi creatura evocata con i tuoi incantesimi di evocazione ottiene 30 punti ferita temporanei."
            }
        ]
    },
    {
        "name": "Scuola di Divinazione (School of Divination)",
        "name_en": "School of Divination",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Scrute il futuro manipolando i dadi del destino con la Portentosa Portent: sostituisce qualsiasi d20 prima che venga tirato.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente della Divinazione",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Divinazione."
            },
            {
                "level": 2,
                "name": "Portento",
                "desc": "A ogni riposo lungo tiri due d20 registrando i risultati: puoi sostituire qualsiasi tiro per colpire, prova o TS con uno di questi risultati."
            },
            {
                "level": 6,
                "name": "Esperto Divinatore",
                "desc": "Quando lanci un incantesimo di divinazione di 2° livello o superiore recuperi uno slot speso di livello inferiore."
            },
            {
                "level": 10,
                "name": "Il Terzo Occhio",
                "desc": "Come azione ottieni uno a scelta tra: Scurovisione 18m, Visione Eterea 18m, Lettura Linguaggi o Vedere Invisibilità."
            },
            {
                "level": 14,
                "name": "Portento Superiore",
                "desc": "Tiri tre d20 per il Portento anziché due a ogni riposo lungo."
            }
        ]
    },
    {
        "name": "Scuola di Ammaliamento (School of Enchantment)",
        "name_en": "School of Enchantment",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Manipolatore delle menti, paralizza con lo Sguardo Ipnotico, reindirizza attacchi ostili e sdoppia magie di controllo mentale.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente dell'Ammaliamento",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Ammaliamento."
            },
            {
                "level": 2,
                "name": "Sguardo Ipnotico",
                "desc": "Come azione guardi una creatura entro 1.5m: se fallisce un TS Saggezza è incapacitata e la sua velocità è 0 finché mantieni lo sguardo."
            },
            {
                "level": 6,
                "name": "Deviare Attacco",
                "desc": "Come reazione quando vieni attaccato puoi reindirizzare il colpo su un'altra creatura entro la portata dell'attaccante."
            },
            {
                "level": 10,
                "name": "Ammaliamento Diviso",
                "desc": "Quando lanci un incantesimo di ammaliamento di 1° livello o superiore che bersaglia una sola creatura, puoi bersagliare una seconda creatura."
            },
            {
                "level": 14,
                "name": "Modificare Memoria",
                "desc": "Le creature che affascini con i tuoi incantesimi non si accorgono di essere state manipolate e puoi cancellarne i ricordi."
            }
        ]
    },
    {
        "name": "Scuola di Invocazione (School of Evocation)",
        "name_en": "School of Evocation",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Il maestro supremo della distruzione elementale: modella le aree di Palle di Fuoco risparmiando gli alleati e massimizza i danni.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente dell'Invocazione",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Invocazione."
            },
            {
                "level": 2,
                "name": "Plasmare Incantesimi",
                "desc": "Quando lanci un incantesimo di invocazione ad area puoi proteggere 1 + livello incantesimo alleati: superano automaticamente il TS e subiscono 0 danni."
            },
            {
                "level": 6,
                "name": "Trucchetto Potente",
                "desc": "I tuoi trucchetti infliggono metà dei danni anche alle creature che superano il tiro salvezza."
            },
            {
                "level": 10,
                "name": "Invocazione Potenziata",
                "desc": "Aggiungi il modificatore di Intelligenza a un tiro di danno di qualsiasi tuo incantesimo di invocazione."
            },
            {
                "level": 14,
                "name": "Sovraccarico",
                "desc": "Massimizzi i danni di un incantesimo di 1°-5° livello. Se riutilizzato prima di un riposo lungo subisci danni necrotici crescenti."
            }
        ]
    },
    {
        "name": "Scuola di Illusione (School of Illusion)",
        "name_en": "School of Illusion",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Tesse inganni sensoriali perfetti, muove illusioni continuative, schiva colpi con repliche illusorie e trasforma le illusioni in solida realtà.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente dell'Illusione",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Illusione."
            },
            {
                "level": 2,
                "name": "Illusione Minore Migliorata",
                "desc": "Con il trucchetto Illusione Minore puoi creare sia un suono che un'immagine visiva contemporaneamente."
            },
            {
                "level": 6,
                "name": "Illusioni Malleabili",
                "desc": "Come azione puoi alterare completamente la natura di un'illusione già lanciata purché tu ne mantenga i requisiti."
            },
            {
                "level": 10,
                "name": "Sé Illusorio",
                "desc": "Come reazione quando vieni attaccato crei un duplicato istantaneo facendo fallire automaticamente l'attacco nemico (1 volta per riposo)."
            },
            {
                "level": 14,
                "name": "Realtà Illusoria",
                "desc": "Come azione bonus puoi rendere un oggetto inanimato non magico facente parte di una tua illusione reale e solido per 1 minuto."
            }
        ]
    },
    {
        "name": "Scuola di Negromanzia (School of Necromancy)",
        "name_en": "School of Necromancy",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Comanda le forze oscure della vita e della morte: assorbe vita con Mietitore Tetro, crea orde di non morti potenziati e soggioga non morti altrui.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente della Negromanzia",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Negromanzia."
            },
            {
                "level": 2,
                "name": "Mietitore Tetro",
                "desc": "Quando uccidi una creatura con un incantesimo recuperi PF pari al doppio del livello dello slot (o triplo se è negromanzia)."
            },
            {
                "level": 6,
                "name": "Servitori della Non Morte",
                "desc": "Animare Morti crea un non morto addizionale; i tuoi non morti hanno PF massimi aumentati del tuo livello e aggiungono competenza ai danni."
            },
            {
                "level": 10,
                "name": "Assuefazione alla Non Morte",
                "desc": "Resistenza ai danni necrotici e i tuoi PF massimi non possono essere ridotti."
            },
            {
                "level": 14,
                "name": "Comandare Non Morti",
                "desc": "Come azione tenti di assoggettare un non morto nemico (anche creato da altri): TS Carisma o cade permanentemente sotto il tuo comando."
            }
        ]
    },
    {
        "name": "Scuola di Trasmutazione (School of Transmutation)",
        "name_en": "School of Transmutation",
        "class_name": "Mago",
        "source": "Player's Handbook",
        "description": "Modifica la struttura della materia: muta legni e metalli, crea la Pietra del Trasmutatore e padroneggia la metamorfosi.",
        "features": [
            {
                "level": 2,
                "name": "Sapiente della Trasmutazione",
                "desc": "Dimezza tempi e costi per trascrivere incantesimi di Trasmutazione."
            },
            {
                "level": 2,
                "name": "Alchimia Minore",
                "desc": "Trasformi temporaneamente un materiale in un altro (legno in argento, pietra in ferro) per 1 ora per 0.3 metri cubi."
            },
            {
                "level": 6,
                "name": "Pietra del Trasmutatore",
                "desc": "Crei una pietra magica che dona a chi la trasporta: scurovisione, velocità aumentata di 3m, resistenza a un elemento o competenza nei TS Costituzione."
            },
            {
                "level": 10,
                "name": "Mutamento di Forma",
                "desc": "Aggiungi Metamorfosi al libro e puoi lanciarlo su te stesso senza spendere slot per trasformarti in una bestia con GS 1 o inferiore."
            },
            {
                "level": 14,
                "name": "Maestro Trasmutatore",
                "desc": "Consumi la Pietra del Trasmutatore per: Trasformazione Totale (crei un oggetto), Risanare la Vita (cura totale), Resurrezione o Ringiovanire."
            }
        ]
    },
    {
        "name": "Magia da Guerra (War Magic)",
        "name_en": "War Magic",
        "class_name": "Mago",
        "source": "Xanathar's Guide to Everything",
        "description": "Sviluppata per i maghi da battaglia militari: aggiunge l'Intelligenza all'iniziativa, devia attacchi con barriere reattive e punisce i nemici con scariche di forza.",
        "features": [
            {
                "level": 2,
                "name": "Deviazione Arcana",
                "desc": "Come reazione ottieni +2 alla CA contro un attacco o +4 a un tiro salvezza (nel turno successivo puoi lanciare solo trucchetti)."
            },
            {
                "level": 2,
                "name": "Stratega Tattico",
                "desc": "Aggiungi il tuo modificatore di Intelligenza ai tuoi tiri di iniziativa."
            },
            {
                "level": 6,
                "name": "Scarica di Potere",
                "desc": "Accumuli cariche dissolvendo incantesimi o usando Controincantesimo: spendi cariche per infliggere danni da forza extra con gli incantesimi."
            },
            {
                "level": 10,
                "name": "Magia Durevole",
                "desc": "Mentre mantieni la concentrazione su un incantesimo ottieni un bonus di +2 alla CA e a tutti i tiri salvezza."
            },
            {
                "level": 14,
                "name": "Deviazione Eterea",
                "desc": "Quando usi Deviazione Arcana scateni energia magica contro fino a tre creature entro 18m infliggendo danni da forza pari a metà livello."
            }
        ]
    },
    {
        "name": "Canto della Lama (Bladesinging)",
        "name_en": "Bladesinging",
        "class_name": "Mago",
        "source": "Tasha's Cauldron of Everything / SCAG",
        "description": "Antica arte elfica che fonde scherma elegante e magia arcana: entra nel Canto della Lama aumentando vertiginosamente CA, concentrazione e velocità.",
        "features": [
            {
                "level": 2,
                "name": "Addestramento della Guerra e del Canto",
                "desc": "Competenza nelle armature leggere, in un'arma da mischia a una mano e nell'abilità Intrattenere."
            },
            {
                "level": 2,
                "name": "Canto della Lama",
                "desc": "Come azione bonus entri in canto per 1 minuto: aggiungi Intelligenza alla CA, velocità +3m, vantaggio ad Acrobazia e aggiungi Int ai TS di Concentrazione."
            },
            {
                "level": 6,
                "name": "Attacco Extra (Canto della Lama)",
                "desc": "Attacchi due volte ad ogni turno e puoi sostituire uno degli attacchi con il lancio di un trucchetto."
            },
            {
                "level": 10,
                "name": "Canto della Difesa",
                "desc": "Come reazione spendi uno slot incantesimo per assorbire danni subiti pari a 5 volte il livello dello slot."
            },
            {
                "level": 14,
                "name": "Canto della Vittoria",
                "desc": "Mentre il Canto della Lama è attivo aggiungi il tuo modificatore di Intelligenza ai danni delle tue armi da mischia."
            }
        ]
    },
    {
        "name": "Magia Cronurgica (Chronurgy Magic)",
        "name_en": "Chronurgy Magic",
        "class_name": "Mago",
        "source": "Explorer's Guide to Wildemount",
        "description": "Maestro delle linee temporali della dunamanzia: altera il tempo per forzare ritiri di dadi, congela nemici in stasi temporale e condensa incantesimi in perle.",
        "features": [
            {
                "level": 2,
                "name": "Spostamento Temporale",
                "desc": "Come reazione entro 9m costringi una creatura a ripetere un tiro per colpire, prova o TS appena effettuato (2 usi per riposo)."
            },
            {
                "level": 2,
                "name": "Iniziativa Cronale",
                "desc": "Aggiungi il tuo modificatore di Intelligenza ai tuoi tiri di iniziativa."
            },
            {
                "level": 6,
                "name": "Stasi Momentanea",
                "desc": "Come azione intrappoli una creatura Media o più piccola in stasi temporale per 1 round (TS Costituzione)."
            },
            {
                "level": 10,
                "name": "Sfera Arcano-Temporale",
                "desc": "Condensi un incantesimo di 1°-4° livello in una perla grigia che un compagno può scatenare entro 1 ora."
            },
            {
                "level": 14,
                "name": "Successo Convergente",
                "desc": "Come reazione trasformi un tiro salvezza, prova o attacco fallito da te o un alleato in un successo immediato (subisci un livello di indebolimento)."
            }
        ]
    },
    {
        "name": "Magia Graviturgica (Graviturgy Magic)",
        "name_en": "Graviturgy Magic",
        "class_name": "Mago",
        "source": "Explorer's Guide to Wildemount",
        "description": "Padroneggia le forze gravitazionali della dunamanzia: altera la massa degli oggetti e delle creature, attira o respinge bersagli e schiaccia con gravità estrema.",
        "features": [
            {
                "level": 2,
                "name": "Densità Regolabile",
                "desc": "Come azione raddoppi o dimezzi il peso di una creatura o oggetto: dimezzato (+3m velocità, salti doppi), raddoppiato (velocità -3m, vantaggio prove Forza)."
            },
            {
                "level": 6,
                "name": "Pozzo Gravitazionale",
                "desc": "Ogni volta che lanci un incantesimo su una creatura puoi muoverla involontariamente fino a 1.5 metri in qualsiasi direzione."
            },
            {
                "level": 10,
                "name": "Attrazione Violenta",
                "desc": "Come reazione aumenti la velocità d'impatto di un attacco o di una caduta infliggendo 2d10 danni extra da forza."
            },
            {
                "level": 14,
                "name": "Attrazione Eventuale",
                "desc": "Come azione crei un campo di gravità schiacciante: nemici rallentati e schiacciati per 2d10 danni da forza a inizio turno."
            }
        ]
    },
    {
        "name": "Ordine dei Sapienti (Order of Scribes)",
        "name_en": "Order of Scribes",
        "class_name": "Mago",
        "source": "Tasha's Cauldron of Everything",
        "description": "Il più devoto alla scrittura magica pura: anima il proprio libro degli incantesimi con una coscienza senziente e cambia il tipo di danno degli incantesimi a piacimento.",
        "features": [
            {
                "level": 2,
                "name": "Piuma del Mago",
                "desc": "Manifesti una piuma magica che non richiede inchiostro e riduce il tempo di copia degli incantesimi a 2 minuti per livello."
            },
            {
                "level": 2,
                "name": "Libro degli Incantesimi Risvegliato",
                "desc": "Il libro è un catalizzatore senziente: puoi sostituire il tipo di danno di un incantesimo con uno qualsiasi presente nel tuo libro."
            },
            {
                "level": 6,
                "name": "Manifestazione della Mente",
                "desc": "Proietti la mente del libro come un ologramma spettrale entro 90m attraverso cui puoi vedere, udire e lanciare incantesimi."
            },
            {
                "level": 10,
                "name": "Maestro Scriba",
                "desc": "Durante un riposo lungo crei una pergamena speciale di 1° o 2° livello che puoi lanciare come azione bonus."
            },
            {
                "level": 14,
                "name": "Unico con il Tomo",
                "desc": "Se stai per subire danni letali, il libro assorbe il danno bruciando temporaneamente alcuni dei tuoi incantesimi scritti al tuo posto."
            }
        ]
    }
]
