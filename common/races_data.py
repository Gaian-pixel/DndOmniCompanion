# common/races_data.py
"""
Catalogo completo e autentico delle 9 Razze di D&D 5e (SRD & Manuale del Giocatore):
- Descrizioni narrative approfondite ed evocative
- Tratti razziali biologici e soprannaturali dettagliati con meccaniche 5e
- Bonus di Caratteristica, Velocità di base e Taglia
- Sensi speciali (Scurovisione) e Linguaggi conosciuti
- Resistenze ai danni & Immunità speciali
- Consiglio di Ruolo, Classi Consigliate & Sinergie di Classe
- Anteprima delle Sottorazze e Varianti
- Longevità ed Allineamento culturale tipico
"""

from typing import Dict, Any, List, Optional


RACES: Dict[str, Dict[str, Any]] = {
    "Umano": {
        "icon": "👤",
        "bonuses": {"FOR": 1, "DES": 1, "COS": 1, "INT": 1, "SAG": 1, "CAR": 1},
        "bonuses_display": "+1 a Tutte le Caratteristiche (FOR, DES, COS, INT, SAG, CAR)",
        "speed": 30,
        "size": "Media",
        "tagline": "I più adattabili, ambiziosi e determinati tra tutti i popoli mortali, costruttori di imperi e innovatori instancabili.",
        "languages": "Comune e un linguaggio aggiuntivo a scelta",
        "vision": "Normale",
        "lifespan": "Maturano verso i 18 anni e raramente vivono più di un secolo.",
        "synergies": "Eccezionali per qualsiasi classe e combinazioni multiclasse grazie al bonus universale a tutti i punteggi.",
        "best_classes": "Qualsiasi Classe, Guerriero, Mago, Multiclasse",
        "resistances": "Nessuna (bilanciata dal +1 a tutte le caratteristiche)",
        "key_traits_summary": "+1 a Tutte le Caratteristiche, Versatilità universale, Spirito pionieristico",
        "category_tags": ["Versatilità", "Umanoide", "Tutti i Ruoli"],
        "overview": (
            "Nelle terre del multiverso gli umani sono i più giovani tra i popoli comuni, ma la loro ambizione non conosce limiti. "
            "Laddove gli elfi contemplano un bosco per secoli e i nani perfezionano una singola forgia, gli umani costruiscono città, "
            "esplorano mari sconosciuti e affrontano pericoli indicibili mossi dal desiderio ardente di lasciare un'impronta duratura nella storia. "
            "Non possiedono legami rigidi a un dio o a un ambiente: si adattano, sopravvivono e prosperano ovunque."
        ),
        "traits": [
            ("Adattabilità Universale", (
                "La versatilità degli umani è ineguagliata: ottieni un incremento di +1 a ciascuno dei tuoi 6 punteggi di caratteristica "
                "(Forza, Destrezza, Costituzione, Intelligenza, Saggezza, Carisma)."
            )),
            ("Spirito Pionieristico", (
                "Guidati dall'urgenza della loro vita breve rispetto a popoli millenari, gli umani imparano in fretta qualsiasi arte, "
                "padronanza marziale o disciplina arcana, fondando regni e accademie che plasmano le epoche."
            ))
        ],
        "subraces_preview": [
            "Umano Standard (+1 a tutti i 6 punteggi di caratteristica)",
            "Umano Variante (+1 a due caratteristiche a scelta, 1 talento bonus al 1° livello e 1 competenza abilità aggiuntiva)"
        ]
    },
    "Elfo": {
        "icon": "🧝",
        "bonuses": {"DES": 2},
        "racial_skills": ["Percezione"],
        "subraces": {
            "Alto Elfo": {"bonuses": {"INT": 1}},
            "Elfo dei Boschi": {"bonuses": {"SAG": 1}, "speed": 35},
            "Elfo Oscuro (Drow)": {"bonuses": {"CAR": 1}}
        },
        "bonuses_display": "+2 Destrezza",
        "speed": 30,
        "size": "Media",
        "tagline": "Nobili creature di grazia immortale e fascino ultraterreno, intimamente legate alla Selva Fatata e all'arte della magia.",
        "languages": "Comune, Elfico",
        "vision": "Scurovisione 18 metri (60 ft)",
        "lifespan": "Raggiungono la maturità a circa 100 anni e possono vivere oltre i 750 anni.",
        "synergies": "Ideali per Ladri, Ranger, Monaci, Maghi e schermidori agili che sfruttano l'alta Destrezza e i riflessi.",
        "best_classes": "Ladro, Ranger, Monaco, Mago",
        "resistances": "Immunità Sonno Magico, Vantaggio vs Charme (Retaggio Fatato)",
        "key_traits_summary": "Scurovisione 18m, Sensi Acuti (+Percezione), Retaggio Fatato, Trance (4h)",
        "category_tags": ["Scurovisione", "Immunità/Difese", "Destrezza"],
        "overview": (
            "Gli elfi sono un popolo magico di bellezza sovrannaturale originario della Selva Fatata (Feywild). "
            "I loro corpi slanciati si muovono con passo leggero senza far rumore, e i loro volti non conoscono la decadenza senile. "
            "Considerano gli eventi del mondo con la prospettiva di chi osserva imperi nascere e crollare nell'arco di una singola vita, "
            "dedicandosi alla scherma, alla poesia e all'arcano con maestria millenaria."
        ),
        "traits": [
            ("Scurovisione (Darkvision)", (
                "Abituato ai boschi crepuscolari e alla notte stellata, puoi vedere fino a 18 metri nell'oscurità come se fosse luce fioca, "
                "e nella luce fioca come se fosse piena luce (non distingui i colori nel buio, solo sfumature di grigio)."
            )),
            ("Sensi Acuti (Keen Senses)", (
                "Possiedi sensi affinatissimi e ottieni competenza innata nell'abilità Percezione."
            )),
            ("Retaggio Fatato (Fey Ancestry)", (
                "Hai Vantaggio a tutti i tiri salvezza effettuati per evitare o interrompere l'essere affascinato (Charmed), "
                "e la magia non può farti addormentare."
            )),
            ("Trance", (
                "Gli elfi non dormono: meditano profondamente per 4 ore al giorno rimanendo semi-coscienti dell'ambiente. "
                "Questo stato garantisce gli stessi benefici di 8 ore di sonno profondo umano."
            ))
        ],
        "subraces_preview": [
            "Alto Elfo (+1 Intelligenza, un trucchetto da mago a scelta, 1 lingua extra e addestramento con armi elfiche)",
            "Elfo dei Boschi (+1 Saggezza, velocità 35 ft, Mascheramento Selvaggio per nascondersi con copertura naturale)",
            "Elfo Oscuro / Drow (+1 Carisma, Scurovisione Superiore 36m, Magia Drow innata con Luci Danzanti, Luminescenza e Oscurità)"
        ]
    },
    "Nano": {
        "icon": "🧔",
        "bonuses": {"COS": 2},
        "subraces": {
            "Nano delle Colline": {"bonuses": {"SAG": 1}, "hp_bonus": 1},
            "Nano delle Montagne": {"bonuses": {"FOR": 2}},
            "Nano Grigio (Duergar)": {"bonuses": {"FOR": 1}}
        },
        "bonuses_display": "+2 Costituzione",
        "speed": 25,
        "size": "Media (bassi ma massicci e pesanti quanto un umano adulto)",
        "tagline": "Fieri difensori delle fortezze montane, incrollabili come la roccia e leggendari lavoratori dell'acciaio e delle gemme.",
        "languages": "Comune, Nanico",
        "vision": "Scurovisione 18 metri (60 ft)",
        "lifespan": "Considerati giovani fino a 50 anni, vivono in media oltre 350 anni.",
        "synergies": "Perfetti per Guerrieri, Chierici, Barbari e Paladini grazie all'alta Costituzione e alla resistenza al veleno.",
        "best_classes": "Guerriero, Chierico, Barbaro, Paladino",
        "resistances": "Resistenza Veleno (danni dimezzati), Vantaggio vs Veleno",
        "key_traits_summary": "Scurovisione 18m, Resilienza Nanica (Resist. Veleno), Armi naniche, Passo Sicuro in armatura",
        "category_tags": ["Scurovisione", "Resistenze", "Mischia/Forza"],
        "overview": (
            "I nani sono rinomati in tutto il multiverso per il loro senso inflessibile dell'onore, la lealtà al clan e l'incredibile "
            "memoria per alleanze e faide. Scavano sale maestose nel grembo delle montagne, forgiando armi e armature indistruttibili. "
            "Il loro passo è fermo e la loro risolutezza è proverbiale: un nano non abbandona mai la propria posizione né viene piegato dal peso del metallo."
        ),
        "traits": [
            ("Scurovisione (Darkvision)", (
                "Abituato alla vita nelle gallerie sotterranee, vedi fino a 18 metri nell'oscurità come se fosse luce fioca."
            )),
            ("Resilienza Nanica (Dwarven Resilience)", (
                "Possiedi Vantaggio a tutti i tiri salvezza contro il Veleno e Resistenza ai danni da veleno (dimezza tutti i danni da veleno subiti!)."
            )),
            ("Addestramento al Combattimento Nanico", (
                "Competenza nell'uso di ascia da battaglia, ascia, martello leggero e martello da guerra."
            )),
            ("Passo Sicuro delle Montagne", (
                "La tua velocità di movimento di base (25 ft) non viene mai ridotta dall'indossare armature pesanti, anche se non soddisfi il requisito di Forza!"
            )),
            ("Conoscenza della Pietra (Stonecunning)", (
                "Quando effettui una prova di Intelligenza (Storia) relativa all'origine di una lavorazione in pietra, aggiungi il doppio del tuo bonus di competenza."
            ))
        ],
        "subraces_preview": [
            "Nano delle Colline (+1 Saggezza e Tenacia Nanica: ottieni +1 Punto Ferita massimo per ogni livello del personaggio)",
            "Nano delle Montagne (+2 Forza addizionale e competenza naturale nelle armature leggere e medie)",
            "Nano Grigio / Duergar (Scurovisione 36m, invisibilità innata e poteri di ingrandimento corporale nel Sottosuolo)"
        ]
    },
    "Halfling": {
        "icon": "🍀",
        "bonuses": {"DES": 2},
        "subraces": {
            "Halfling Piedelesto": {"bonuses": {"CAR": 1}},
            "Halfling Tozzo": {"bonuses": {"COS": 1}},
            "Halfling Spettrale": {"bonuses": {"SAG": 1}}
        },
        "bonuses_display": "+2 Destrezza",
        "speed": 25,
        "size": "Piccola (alti circa 90 cm)",
        "tagline": "Un popolo minuto e pacifico baciato da una fortuna sfacciata, capace di sfuggire a ogni pericolo con agilità e buonumore.",
        "languages": "Comune, Halfling",
        "vision": "Normale",
        "lifespan": "Adulti a 20 anni, vivono felicemente fino a circa 150 anni.",
        "synergies": "Fantastici per Ladri, Bardi, Ranger e Stregoni: il tratto Fortunato impedisce i fallimenti critici sui dadi!",
        "best_classes": "Ladro, Bardo, Ranger, Stregone",
        "resistances": "Vantaggio vs Paura (Coraggioso), Ritiro 1 naturali (Fortunato)",
        "key_traits_summary": "Fortunato (ritiro 1 naturali su d20), Coraggioso, Agilità Halfling tra taglie grandi",
        "category_tags": ["Taglia Piccola", "Immunità/Difese", "Destrezza"],
        "overview": (
            "Gli halfling amano la quiete, i campi coltivati, il buon cibo e i focolari accoglienti. Tuttavia, quando la sorte chiama, "
            "rivelano un coraggio e una determinazione sorprendenti. Piccoli di statura e silenziosi nei movimenti, sanno insinuarsi ovunque "
            "e superare gli ostacoli più temibili con una risata e una fortuna che ha del miracoloso."
        ),
        "traits": [
            ("Fortunato (Lucky)", (
                "Quando ottieni un 1 naturale con il d20 a un tiro per colpire, a una prova di caratteristica o a un tiro salvezza, "
                "puoi ritirare il dado e devi obbligatoriamente usare il nuovo risultato! (Uno dei tratti più potenti di D&D)."
            )),
            ("Coraggioso (Brave)", (
                "Hai Vantaggio a tutti i tiri salvezza effettuati contro l'essere spaventato (Frightened)."
            )),
            ("Agilità Halfling (Nimbleness)", (
                "Puoi muoverti liberamente attraverso lo spazio occupato da qualsiasi creatura di taglia superiore alla tua (Media o superiore)."
            ))
        ],
        "subraces_preview": [
            "Halfling Piedelesto (+1 Carisma e Furtività Innata: puoi tentare di nasconderti anche dietro a una creatura di taglia Media)",
            "Halfling Tozzo (+1 Costituzione, Vantaggio ai tiri salvezza contro veleno e resistenza ai danni da veleno)",
            "Halfling Spettrale (+1 Saggezza e Telepatia Silenziosa a breve raggio con i compagni)"
        ]
    },
    "Draconide": {
        "icon": "🐲",
        "bonuses": {"FOR": 2, "CAR": 1},
        "bonuses_display": "+2 Forza, +1 Carisma",
        "speed": 30,
        "size": "Media (imponenti e muscolosi, superano spesso 1,90 m e 110 kg)",
        "tagline": "Fieri umanoidi nati dal sangue dei draghi, devoti all'onore marziale, alla gloria del clan e alle armi a soffio elementali.",
        "languages": "Comune, Draconico",
        "vision": "Normale",
        "lifespan": "Crescono rapidamente (adulti a 15 anni) e vivono circa 80 anni.",
        "synergies": "Perfetti per Paladini, Guerrieri, Barbari e Stregoni grazie alla potente sinergia tra Forza elevata e Carisma.",
        "best_classes": "Paladino, Guerriero, Barbaro, Stregone",
        "resistances": "Resistenza Elementale (Fuoco, Freddo, Acido, Fulmine o Veleno in base alla stirpe)",
        "key_traits_summary": "Ascendenza Draconica, Arma a Soffio (cono/linea 2d6+ ricarica riposo), Resistenza ai Danni",
        "category_tags": ["Resistenze", "Mischia/Forza", "Magia Innata"],
        "overview": (
            "I draconidi portano nel loro portamento la fierezza e il retaggio dei draghi antichi. Privi di ali o coda, ma rivestiti "
            "di scaglie resistenti e con tratti draconici possenti, considerano l'onore personale e la reputazione del clan il bene più prezioso. "
            "In battaglia combattono con ferocia cavalleresca, esalando soffi di fuoco, fulmine o gelo capaci di spazzare via intere formazioni nemiche."
        ),
        "traits": [
            ("Ascendenza Draconica (Draconic Ancestry)", (
                "Scegli una stirpe di drago progenitore che determina l'elemento e la forma del tuo soffio e la tua resistenza elementale:\n"
                "• Rosso / Oro / Ottone: Fuoco\n"
                "• Blu / Bronzo: Fulmine\n"
                "• Nero / Rame: Acido\n"
                "• Argento / Bianco: Freddo\n"
                "• Verde: Veleno"
            )),
            ("Arma a Soffio (Breath Weapon)", (
                "Come azione, esali energia distruttiva in un cono di 4,5 metri o linea di 9 metri (in base all'ascendenza).\n"
                "• Infligge 2d6 danni (TS su Destrezza o Costituzione con CD = 8 + mod COS + competenza per dimezzare).\n"
                "• I danni scalano a 3d6 al 6° liv, 4d6 all'11° liv, 5d6 al 16° liv.\n"
                "• Si ricarica con un riposo breve o lungo!"
            )),
            ("Resistenza ai Danni (Damage Resistance)", (
                "Ottieni Resistenza permanente al tipo di danno associato alla tua ascendenza draconica (dimezza tutti i danni subiti di quell'elemento!)."
            ))
        ],
        "subraces_preview": [
            "Draconide Cromatico (Soffi esplosivi e immunità elementale temporanea avanzata)",
            "Draconide Metallico (Soffio secondario invalidante per respingere o addormentare i nemici)",
            "Draconide delle Gemme (Soffi di forza, psichici o radiosi con volo spettrale a volontà)"
        ]
    },
    "Gnomo": {
        "icon": "⚙️",
        "bonuses": {"INT": 2},
        "subraces": {
            "Gnomo delle Rocce": {"bonuses": {"COS": 1}},
            "Gnomo delle Foreste": {"bonuses": {"DES": 1}},
            "Gnomo del Profondo (Svirfneblin)": {"bonuses": {"DES": 1}}
        },
        "bonuses_display": "+2 Intelligenza",
        "speed": 25,
        "size": "Piccola (alti circa 90 cm-1 m)",
        "tagline": "Geniali inventori, studiosi e illusionisti, guidati da un'insaziabile curiosità e da una mente scintillante.",
        "languages": "Comune, Gnomesco",
        "vision": "Scurovisione 18 metri (60 ft)",
        "lifespan": "Adulti a 40 anni, vivono regolarmente tra i 350 e i 500 anni.",
        "synergies": "La scelta d'eccellenza per Maghi, Artefici e investigatori arcani grazie all'Intelligenza e all'Astuzia Gnomesca.",
        "best_classes": "Mago, Artefice, Ladro, Chierico",
        "resistances": "Vantaggio vs Magia (Astuzia Gnomesca: TS su INT, SAG, CAR contro incantesimi)",
        "key_traits_summary": "Scurovisione 18m, Astuzia Gnomesca (barriera difensiva vs magia mentale)",
        "category_tags": ["Taglia Piccola", "Scurovisione", "Immunità/Difese", "Magia Innata"],
        "overview": (
            "L'entusiasmo di uno gnomo per la vita e la conoscenza è incontenibile. Parlano rapidamente, i loro occhi brillano di meraviglia "
            "e considerano il multiverso un gigantesco rompicapo da esplorare e perfezionare. Abitano tane sotterranee nascoste o boschi incantati, "
            "fabbricando congegni meccanici o tessendo sottili illusioni per confondere i nemici e proteggere le loro comunità."
        ),
        "traits": [
            ("Scurovisione (Darkvision)", (
                "Abituato a vivere nel sottosuolo o in laboratori poco illuminati, vedi fino a 18 metri nell'oscurità come luce fioca."
            )),
            ("Astuzia Gnomesca (Gnome Cunning)", (
                "Possiedi Vantaggio a TUTTI i tiri salvezza su Intelligenza, Saggezza e Carisma contro la magia! "
                "(Una delle barriere difensive passive più potenti di D&D contro incantesimi di controllo mentale, illusioni e ammaliamenti)."
            ))
        ],
        "subraces_preview": [
            "Gnomo delle Rocce (+1 Costituzione, raddoppia le prove di Storia sui congegni, e privilegio 'Meccanico' per costruire orologi e carillon)",
            "Gnomo delle Foreste (+1 Destrezza, trucchetto Illusione Minore gratuito e capacità di parlare con piccoli animali)",
            "Gnomo del Profondo / Svirfneblin (Scurovisione 36m, mimetismo nella roccia e abilità di sopravvivenza nel Sottosuolo)"
        ]
    },
    "Mezzelfo": {
        "icon": "✨",
        "bonuses": {"CAR": 2, "DES": 1, "COS": 1},
        "bonus_choices": 2,
        "skill_choices": 2,
        "bonuses_display": "+2 Carisma, +1 a due altre caratteristiche a scelta",
        "speed": 30,
        "size": "Media",
        "tagline": "Eredi di due mondi: uniscono la passione e l'intraprendenza umana con l'eleganza estetica e i sensi fatati degli elfi.",
        "languages": "Comune, Elfico e una lingua aggiuntiva a scelta",
        "vision": "Scurovisione 18 metri (60 ft)",
        "lifespan": "Maturano a 20 anni e possono vivere oltre 180 anni.",
        "synergies": "Ideali per Bardi, Stregoni, Warlock e Paladini: il bonus di +2 a Carisma e le competenze extra li rendono irresistibili.",
        "best_classes": "Bardo, Stregone, Paladino, Warlock",
        "resistances": "Immunità Sonno Magico, Vantaggio vs Charme (Retaggio Fatato)",
        "key_traits_summary": "Scurovisione 18m, Retaggio Fatato, Versatilità nelle Competenze (2 abilità libere)",
        "category_tags": ["Scurovisione", "Immunità/Difese", "Carisma/Versatilità"],
        "overview": (
            "I mezzelfi camminano al confine tra due culture, spesso fungendo da diplomatici, ambasciatori e avventurieri cosmopoliti. "
            "Possiedono il fascino naturale e la longevità degli elfi, uniti alla determinazione instancabile e all'adattabilità degli umani. "
            "La loro capacità di apprendere competenze diverse li rende elementi preziosissimi e poliedrici per qualsiasi gruppo d'avventura."
        ),
        "traits": [
            ("Scurovisione (Darkvision)", (
                "Grazie al tuo retaggio elfico, puoi vedere nell'oscurità fino a 18 metri come se fosse luce fioca."
            )),
            ("Retaggio Fatato (Fey Ancestry)", (
                "Hai Vantaggio ai tiri salvezza per evitare o interrompere l'essere affascinato, e la magia non può addormentarti."
            )),
            ("Versatilità nelle Competenze (Skill Versatility)", (
                "Ottieni competenza in due abilità qualsiasi a tua scelta tra tutte quelle disponibili nel gioco!"
            ))
        ],
        "subraces_preview": [
            "Mezzelfo Tradizionale (Versatilità in due abilità qualsiasi a scelta)",
            "Variante Alto Elfo (Sostituisce le abilità con un trucchetto arcano da mago o addestramento con armi elfiche)",
            "Variante Elfo dei Boschi (Sostituisce le abilità con velocità aumentata a 35 ft o Mascheramento Selvaggio)"
        ]
    },
    "Mezzorco": {
        "icon": "🪓",
        "bonuses": {"FOR": 2, "COS": 1},
        "racial_skills": ["Intimidire"],
        "bonuses_display": "+2 Forza, +1 Costituzione",
        "speed": 30,
        "size": "Media (alti, possenti e minacciosi, tra 1,80 m e 2,10 m)",
        "tagline": "Guerrieri dalla tenacia inesauribile e dalla ferocia devastante, capaci di sopravvivere a colpi mortali per amore o per vendetta.",
        "languages": "Comune, Orchesco",
        "vision": "Scurovisione 18 metri (60 ft)",
        "lifespan": "Maturano a 14 anni e raramente superano i 75 anni a causa della loro indole bellicosa.",
        "synergies": "I sovrani assoluti della prima linea per Barbari, Guerrieri e Paladini: critici devastanti e salvataggio dallo 0 PF.",
        "best_classes": "Barbaro, Guerriero, Paladino",
        "resistances": "Tenacia Implacabile (sopravvive a 1 PF invece di cadere a 0 PF)",
        "key_traits_summary": "Scurovisione 18m, Minaccioso (+Intimidire), Tenacia Implacabile (1 PF), Attacchi Selvaggi",
        "category_tags": ["Scurovisione", "Mischia/Forza", "Immunità/Difese"],
        "overview": (
            "I mezzorchi sentono scorrere nelle vene passioni roventi: gioia sfrenata, collera selvaggia e una lealtà incrollabile verso chi "
            "dimostra loro vero rispetto. Spesso guardati con diffidenza nelle città, conquistano il loro posto nel mondo attraverso "
            "prove di forza titanica e coraggio stoico, rifiutando di cadere anche dinanzi al più letale dei fendenti."
        ),
        "traits": [
            ("Scurovisione (Darkvision)", (
                "Grazie al sangue orchesco, vedi nell'oscurità fino a 18 metri come se fosse luce fioca."
            )),
            ("Minaccioso (Menacing)", (
                "La tua presenza fisica incute timore: ottieni competenza gratuita nell'abilità Intimidire."
            )),
            ("Tenacia Implacabile (Relentless Endurance)", (
                "Quando vieni ridotto a 0 Punti Ferita ma non vieni ucciso sul colpo, puoi invece rimanere a 1 Punto Ferita! "
                "(Una volta per riposo lungo; questo privilegio ribalta gli scontri e salva la vita nei momenti più critici)."
            )),
            ("Attacchi Selvaggi (Savage Attacks)", (
                "Quando metti a segno un colpo critico con un'arma da mischia, puoi tirare uno dei dadi di danno dell'arma una volta "
                "aggiuntiva e sommarlo ai danni extra del colpo critico!"
            ))
        ],
        "subraces_preview": [
            "Mezzorco dei Clan Selvaggi (Tradizione sciamanica e resistenza ai climi estremi)",
            "Mezzorco Urbano (Adattato alla vita mercantile o delle guardie cittadine, esperto nei bassifondi)"
        ]
    },
    "Tiefling": {
        "icon": "🔥",
        "bonuses": {"CAR": 2, "INT": 1},
        "bonuses_display": "+2 Carisma, +1 Intelligenza",
        "speed": 30,
        "size": "Media (corporatura umana con corna ricurve, coda prensile e occhi d'ombra o zolfo)",
        "tagline": "Portatori di un'eredità infernale ancestrale, padroneggiano il fuoco e la magia oscura sfidando i pregiudizi del mondo.",
        "languages": "Comune, Infernale",
        "vision": "Scurovisione 18 metri (60 ft)",
        "lifespan": "Maturano come gli umani e vivono circa 90-100 anni.",
        "synergies": "Eccezionali per Stregoni, Warlock, Bardi e Maghi: Carisma dominante, resistenza al fuoco e magie gratuite innate.",
        "best_classes": "Stregone, Warlock, Bardo, Mago",
        "resistances": "Resistenza Fuoco (danni da fuoco dimezzati - Resistenza Infernale)",
        "key_traits_summary": "Scurovisione 18m, Resistenza Infernale (Fuoco), Eredità Infernale (magia oscura innata)",
        "category_tags": ["Scurovisione", "Resistenze", "Magia Innata"],
        "overview": (
            "I tiefling portano sul corpo il marchio visibile di un antico patto stretto dai loro avi con i signori dei Nove Inferi. "
            "Corna imponenti, pelle dai riflessi cremisi o bronzei, denti appuntiti e una coda affusolata li rendono spesso bersaglio di timori superstiziosi. "
            "Tuttavia, il loro destino non è scritto nelle fiamme infernali: molti tiefling scelgono la via della virtù e della redenzione, "
            "impiegando i loro doni oscuri per proteggere gli innocenti e abbattere i veri mostri."
        ),
        "traits": [
            ("Scurovisione (Darkvision)", (
                "I tuoi occhi infernali penetrano l'oscurità fino a 18 metri in sfumature di rosso e grigio."
            )),
            ("Resistenza Infernale (Hellish Resistance)", (
                "Il tuo retaggio ti protegge dalle fiamme: ottieni Resistenza permanente ai danni da Fuoco "
                "(dimezza tutti i danni da fuoco subiti da incantesimi, trappole o fiamme di drago!)."
            )),
            ("Eredità Infernale (Infernal Legacy)", (
                "Manifesti magia oscura innata che usa il Carisma come caratteristica da incantatore:\n"
                "• Al 1° livello: Conosci il trucchetto Taumaturgia.\n"
                "• Al 3° livello: Puoi lanciare Intimorire Infernale (Hellish Rebuke) come incantesimo di 2° livello 1 volta per riposo lungo.\n"
                "• Al 5° livello: Puoi lanciare Oscurità (Darkness) 1 volta per riposo lungo."
            ))
        ],
        "subraces_preview": [
            "Stirpe di Asmodeus (Intelligenza e Carisma con Taumaturgia, Hellish Rebuke e Darkness)",
            "Stirpe di Mephistopheles (+1 Intelligenza, Mani Brucianti e Lama di Fuoco)",
            "Stirpe di Zariel (+1 Forza, Colpo Infuocato e attacchi marziali infusi di fiamme)",
            "Stirpe di Levistus (+1 Costituzione, Raggio di Gelo e Armatura di Agathys)"
        ]
    }
}

# Calcolo desc preformattata per retrocompatibilità totale con qualsiasi accesso a RACES[r]["desc"]
for _r_name, _r_info in RACES.items():
    _traits_text = "\n".join(f"  • {_tname}:\n    {_tdesc}" for _tname, _tdesc in _r_info["traits"])
    _subs_text = "\n".join(f"  • {_sub}" for _sub in _r_info.get("subraces_preview", []))
    _r_info["desc"] = (
        f"{_r_info['tagline']}\n\n"
        f"⚡ Bonus Caratteristiche: {_r_info['bonuses_display']}\n"
        f"🏃 Velocità: {_r_info['speed']} ft (taglia {_r_info['size']})\n"
        f"👁️ Sensi: {_r_info['vision']}\n"
        f"🗣️ Linguaggi: {_r_info['languages']}\n"
        f"⏳ Longevità: {_r_info['lifespan']}\n"
        f"🛡️ Resistenze & Difese: {_r_info.get('resistances', 'Nessuna')}\n"
        f"⭐ Sinergie di Classe: {_r_info['synergies']}\n"
        f"🎯 Classi Consigliate: {_r_info.get('best_classes', '')}\n\n"
        f"📖 Panoramica & Lore:\n{_r_info['overview']}\n\n"
        f"🧬 Tratti Razziali:\n{_traits_text}\n\n"
        f"🌿 Sottorazze & Varianti:\n{_subs_text}"
    )



RACES_EN: Dict[str, Dict[str, Any]] = {
    "Umano": {
        "tagline": "The most adaptable, ambitious, and driven among all mortal peoples, builders of empires and tireless innovators.",
        "bonuses_display": "+1 to All Ability Scores (STR, DEX, CON, INT, WIS, CHA)",
        "languages": "Common and one additional language of your choice",
        "vision": "Normal",
        "lifespan": "Reach adulthood around 18 and rarely live past a century.",
        "synergies": "Exceptional for any class and multiclass combinations thanks to universal score increases.",
        "best_classes": "Any Class, Fighter, Wizard, Multiclass",
        "resistances": "None (balanced by +1 to all ability scores)",
        "key_traits_summary": "+1 to All Ability Scores, Universal versatility, Pioneering spirit",
        "category_tags": ["Versatility", "Humanoid", "All Roles"],
        "overview": (
            "Across the multiverse, humans are the youngest of the common peoples, yet their ambition knows no bounds. "
            "Where elves contemplate a forest for centuries and dwarves spend decades perfecting a single forge, humans build cities, "
            "explore uncharted seas, and confront unimaginable perils driven by a burning desire to leave a lasting mark upon history. "
            "Bound neither to a single god nor to one terrain, they adapt, survive, and thrive everywhere."
        ),
        "traits": [
            ("Universal Adaptability", (
                "Human versatility is unmatched: you gain a +1 increase to each of your 6 ability scores "
                "(Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma)."
            )),
            ("Pioneering Spirit", (
                "Urged on by lives that are brief compared to thousand-year-old kin, humans swiftly master any craft, "
                "martial discipline, or arcane art, founding kingdoms and academies that define epochs."
            ))
        ],
        "subraces_preview": [
            "Standard Human (+1 to all 6 ability scores)",
            "Variant Human (+1 to two chosen abilities, 1 bonus feat at 1st level, and 1 extra skill proficiency)"
        ]
    },
    "Elfo": {
        "tagline": "Noble beings of immortal grace and otherworldly beauty, intimately tied to the Feywild and the art of magic.",
        "bonuses_display": "+2 Dexterity",
        "languages": "Common, Elvish",
        "vision": "Darkvision 60 ft (18 m)",
        "lifespan": "Reach adulthood at around 100 years and can live over 750 years.",
        "synergies": "Ideal for Rogues, Rangers, Monks, Wizards, and agile skirmishers leveraging high Dexterity and keen reflexes.",
        "best_classes": "Rogue, Ranger, Monk, Wizard",
        "resistances": "Immunity to Magical Sleep, Advantage vs Charmed (Fey Ancestry)",
        "key_traits_summary": "Darkvision 60ft, Keen Senses (+Perception), Fey Ancestry, Trance (4h)",
        "category_tags": ["Darkvision", "Defenses/Immunities", "Dexterity"],
        "overview": (
            "Elves are a magical people of ethereal beauty hailing from the Feywild. Their lithe forms tread silently without "
            "making a sound, and their faces never wither with age. They view the unfolding of history from the perspective of "
            "those who watch entire empires rise and crumble across a single lifetime, devoting centuries to fencing, lyric poetry, "
            "and the arcane arts with timeless mastery."
        ),
        "traits": [
            ("Darkvision", (
                "Accustomed to twilit forests and the starlit night, you can see in dim light within 60 feet as if it were bright light, "
                "and in darkness as if it were dim light (discerning shades of gray in darkness)."
            )),
            ("Keen Senses", (
                "You possess heightened senses and gain innate proficiency in the Perception skill."
            )),
            ("Fey Ancestry", (
                "You have advantage on saving throws against being charmed, and magic cannot put you to sleep."
            )),
            ("Trance", (
                "Elves do not sleep: they meditate deeply for 4 hours a day while remaining semiconscious of their surroundings. "
                "This state provides the same benefits as 8 hours of deep human sleep."
            ))
        ],
        "subraces_preview": [
            "High Elf (+1 Intelligence, one wizard cantrip of your choice, 1 extra language, and elven weapon training)",
            "Wood Elf (+1 Wisdom, 35 ft speed, and Mask of the Wild to hide even when lightly obscured by nature)",
            "Dark Elf / Drow (+1 Charisma, Superior Darkvision 120ft, and innate Drow Magic: Dancing Lights, Faerie Fire, Darkness)"
        ]
    },
    "Nano": {
        "tagline": "Proud defenders of mountain strongholds, unyielding as bedrock and legendary crafters of steel and gemstones.",
        "bonuses_display": "+2 Constitution",
        "languages": "Common, Dwarvish",
        "vision": "Darkvision 60 ft (18 m)",
        "lifespan": "Considered youth until age 50, living on average over 350 years.",
        "synergies": "Perfect for Fighters, Clerics, Barbarians, and Paladins thanks to colossal Constitution and poison resilience.",
        "best_classes": "Fighter, Cleric, Barbarian, Paladin",
        "resistances": "Poison Resistance (halve all poison damage), Advantage vs Poison",
        "key_traits_summary": "Darkvision 60ft, Dwarven Resilience (Poison Resist), Dwarven Combat Training, Speed unhindered by heavy armor",
        "category_tags": ["Darkvision", "Resistances", "Melee/Strength"],
        "overview": (
            "Dwarves are renowned across the cosmos for their unbending sense of honor, fierce clan loyalty, and enduring memory "
            "for ancient alliances and blood feuds. Carving magnificent halls in the bellies of mountains, they forge indestructible arms "
            "and armor. Their stride is resolute and their tenacity proverbial: a dwarf never surrenders ground nor bows beneath the burden of heavy plate."
        ),
        "traits": [
            ("Darkvision", (
                "Accustomed to subterranean shafts and caverns, you can see in darkness within 60 feet as if it were dim light."
            )),
            ("Dwarven Resilience", (
                "You have advantage on saving throws against poison, and you have resistance against poison damage (halving all incoming poison damage)."
            )),
            ("Dwarven Combat Training", (
                "Proficiency with the battleaxe, handaxe, light hammer, and warhammer."
            )),
            ("Surefooted Stride", (
                "Your base walking speed (25 ft) is never reduced by wearing heavy armor, even if you lack the Strength requirement!"
            )),
            ("Stonecunning", (
                "Whenever you make an Intelligence (History) check related to the origin of stonework, you add double your proficiency bonus to the check."
            ))
        ],
        "subraces_preview": [
            "Hill Dwarf (+1 Wisdom and Dwarven Toughness: gain +1 maximum Hit Point per character level)",
            "Mountain Dwarf (+2 additional Strength and natural proficiency with light and medium armor)",
            "Gray Dwarf / Duergar (Superior Darkvision 120ft, innate invisibility, and growth powers in the Underdark)"
        ]
    },
    "Halfling": {
        "tagline": "A diminutive and gentle folk blessed with uncanny good fortune, navigating every hazard with agility and cheerful resolve.",
        "bonuses_display": "+2 Dexterity",
        "languages": "Common, Halfling",
        "vision": "Normal",
        "lifespan": "Adults at 20, happily living up to about 150 years.",
        "synergies": "Superb for Rogues, Bards, Rangers, and Sorcerers: the Lucky trait practically eliminates critical failures on d20s!",
        "best_classes": "Rogue, Bard, Ranger, Sorcerer",
        "resistances": "Advantage vs Frightened (Brave), Reroll natural 1s (Lucky)",
        "key_traits_summary": "Lucky (reroll natural 1s on d20s), Brave, Halfling Nimbleness through larger spaces",
        "category_tags": ["Small Size", "Defenses/Immunities", "Dexterity"],
        "overview": (
            "Halflings cherish peaceful pastoral routines, lush hearths, rich feasts, and good cheer. Yet when fate calls, "
            "they display startling courage and grit. Small of stature and whisper-quiet in movement, they slip past perils "
            "and overcome towering adversaries with lighthearted humor and luck that borders on the miraculous."
        ),
        "traits": [
            ("Lucky", (
                "When you roll a 1 on the d20 for an attack roll, ability check, or saving throw, you can reroll the die and must use the new roll! "
                "(One of the most potent passive traits in D&D)."
            )),
            ("Brave", (
                "You have advantage on saving throws against being frightened."
            )),
            ("Halfling Nimbleness", (
                "You can move through the space of any creature that is of a size larger than yours (Medium or larger)."
            ))
        ],
        "subraces_preview": [
            "Lightfoot Halfling (+1 Charisma and Naturally Stealthy: attempt to hide even when obscured only by a Medium creature)",
            "Stout Halfling (+1 Constitution, advantage on saving throws against poison, and poison damage resistance)",
            "Ghostwise Halfling (+1 Wisdom and short-range silent telepathy with companions)"
        ]
    },
    "Draconide": {
        "tagline": "Proud humanoids carrying the blood of ancient dragons, devoted to martial honor, clan glory, and elemental breath weapons.",
        "bonuses_display": "+2 Strength, +1 Charisma",
        "languages": "Common, Draconic",
        "vision": "Normal",
        "lifespan": "Mature rapidly (adults by 15) and live around 80 years.",
        "synergies": "Ideal for Paladins, Fighters, Barbarians, and Sorcerers thanks to the synergy of colossal Strength and commanding Charisma.",
        "best_classes": "Paladin, Fighter, Barbarian, Sorcerer",
        "resistances": "Elemental Resistance (Fire, Cold, Acid, Lightning, or Poison based on ancestry)",
        "key_traits_summary": "Draconic Ancestry, Breath Weapon (cone/line 2d6+ resets on rest), Damage Resistance",
        "category_tags": ["Resistances", "Melee/Strength", "Innate Magic"],
        "overview": (
            "Dragonborn carry in their every gesture the poise and legacy of ancient wyrms. Lacking wings or tail but clad in iridescent "
            "scale armor with imposing draconic silhouettes, they hold personal honor and the renown of their clan above all else. "
            "In battle they fight with chivalrous fury, unleashing breath weapons of searing fire, crackling lightning, or biting frost that break enemy formations."
        ),
        "traits": [
            ("Draconic Ancestry", (
                "Choose a dragon progenitor heritage that dictates your elemental breath weapon damage type and matching damage resistance:\n"
                "• Red / Gold / Brass: Fire\n"
                "• Blue / Bronze: Lightning\n"
                "• Black / Copper: Acid\n"
                "• Silver / White: Cold\n"
                "• Green: Poison"
            )),
            ("Breath Weapon", (
                "As an action, exhale destructive energy in a 15-ft cone or 30-ft line (based on ancestry).\n"
                "• Deals 2d6 damage (Dex or Con save DC = 8 + CON mod + prof for half).\n"
                "• Damage scales to 3d6 at 6th lvl, 4d6 at 11th lvl, 5d6 at 16th lvl.\n"
                "• Recharges on a short or long rest!"
            )),
            ("Damage Resistance", (
                "You gain permanent resistance to the damage type associated with your draconic ancestry (halving all incoming damage of that element!)."
            ))
        ],
        "subraces_preview": [
            "Chromatic Dragonborn (Explosive breath cones and temporary elemental immunity at higher levels)",
            "Metallic Dragonborn (Secondary debilitating breath to push back or incapacitate foes)",
            "Gem Dragonborn (Force, psychic, or radiant breath with spectral flight at will)"
        ]
    },
    "Gnomo": {
        "tagline": "Ingenious inventors, scholars, and illusionists, driven by an unquenchable curiosity and sparkling intellect.",
        "bonuses_display": "+2 Intelligence",
        "languages": "Common, Gnomish",
        "vision": "Darkvision 60 ft (18 m)",
        "lifespan": "Adults at 40, regularly living between 350 and 500 years.",
        "synergies": "The prime choice for Wizards, Artificers, Rogues, and investigative Clerics thanks to high Intelligence and Gnome Cunning.",
        "best_classes": "Wizard, Artificer, Rogue, Cleric",
        "resistances": "Advantage vs Magic (Gnome Cunning: INT, WIS, CHA saves against spells)",
        "key_traits_summary": "Darkvision 60ft, Gnome Cunning (defensive aegis vs mental magic)",
        "category_tags": ["Small Size", "Darkvision", "Defenses/Immunities", "Innate Magic"],
        "overview": (
            "A gnome's enthusiasm for life, invention, and lore is boundless. Speaking at a rapid clip with eyes alight with curiosity, "
            "they treat the multiverse as a grand puzzle waiting to be unlocked and perfected. Dwelling in hidden burrow towns or enchanted woodlands, "
            "they assemble wondrous mechanical gadgets or weave subtle illusions to confound enemies and shield their communities."
        ),
        "traits": [
            ("Darkvision", (
                "Accustomed to life underground or dimly lit workshops, you can see in darkness within 60 feet as if it were dim light."
            )),
            ("Gnome Cunning", (
                "You have advantage on ALL Intelligence, Wisdom, and Charisma saving throws against magic! "
                "(One of the most potent passive defenses in D&D against mental domination, illusions, and charms)."
            ))
        ],
        "subraces_preview": [
            "Rock Gnome (+1 Constitution, double History checks on clockwork/magic items, and Tinker ability to craft music boxes and lighters)",
            "Forest Gnome (+1 Dexterity, free Minor Illusion cantrip, and the ability to speak with small beasts)",
            "Deep Gnome / Svirfneblin (Superior Darkvision 120ft, stone camouflage, and Underdark stealth)"
        ]
    },
    "Mezzelfo": {
        "tagline": "Heirs to two worlds: blending human passion and drive with the timeless elegance and fey senses of the elves.",
        "bonuses_display": "+2 Charisma, +1 to two other ability scores of your choice",
        "languages": "Common, Elvish, and one extra language of your choice",
        "vision": "Darkvision 60 ft (18 m)",
        "lifespan": "Mature at 20 and can live past 180 years.",
        "synergies": "Ideal for Bards, Sorcerers, Warlocks, and Paladins: +2 Charisma, versatile ability scores, and extra skills make them unstoppable.",
        "best_classes": "Bard, Sorcerer, Paladin, Warlock",
        "resistances": "Immunity to Magical Sleep, Advantage vs Charmed (Fey Ancestry)",
        "key_traits_summary": "Darkvision 60ft, Fey Ancestry, Skill Versatility (2 free skill proficiencies)",
        "category_tags": ["Darkvision", "Defenses/Immunities", "Charisma/Versatility"],
        "overview": (
            "Half-elves walk the boundary between two worlds, frequently thriving as diplomats, ambassadors, and cosmopolitan wanderers. "
            "They possess the ethereal charm and longevity of elves matched with the relentless grit and resourcefulness of humans. "
            "Their knack for mastering diverse proficiencies makes them invaluable and multifaceted in any adventuring party."
        ),
        "traits": [
            ("Darkvision", (
                "Thanks to your elven blood, you can see in darkness within 60 feet as if it were dim light."
            )),
            ("Fey Ancestry", (
                "You have advantage on saving throws against being charmed, and magic cannot put you to sleep."
            )),
            ("Skill Versatility", (
                "You gain proficiency in two skills of your choice from any available in the game!"
            ))
        ],
        "subraces_preview": [
            "Traditional Half-Elf (Skill Versatility granting two free skill proficiencies of your choice)",
            "High Elf Variant (Trades extra skills for a wizard cantrip or elven weapon training)",
            "Wood Elf Variant (Trades extra skills for 35 ft speed or Mask of the Wild camouflage)"
        ]
    },
    "Mezzorco": {
        "tagline": "Warriors of inexhaustible stamina and devastating ferocity, enduring mortal blows out of fierce love or boundless fury.",
        "bonuses_display": "+2 Strength, +1 Constitution",
        "languages": "Common, Orc",
        "vision": "Darkvision 60 ft (18 m)",
        "lifespan": "Mature at 14 and rarely live beyond 75 due to their martial lifestyle.",
        "synergies": "Supreme front-line powerhouses for Barbarians, Fighters, and Paladins: brutal critical hits and defying 0 HP death.",
        "best_classes": "Barbarian, Fighter, Paladin",
        "resistances": "Relentless Endurance (drop to 1 HP instead of falling to 0 HP)",
        "key_traits_summary": "Darkvision 60ft, Menacing (+Intimidation), Relentless Endurance (survive at 1 HP), Savage Attacks",
        "category_tags": ["Darkvision", "Melee/Strength", "Defenses/Immunities"],
        "overview": (
            "Half-orcs feel passions burning hot in their veins: unbridled joy, savage wrath, and unbreakable loyalty toward those who "
            "demonstrate true respect. Though often met with wary glances in cities, they forge their place in the world through "
            "feats of titanic strength and stoic courage, refusing to yield even when struck by the deadliest blow."
        ),
        "traits": [
            ("Darkvision", (
                "Thanks to your orc heritage, you can see in darkness within 60 feet as if it were dim light."
            )),
            ("Menacing", (
                "Your imposing presence inspires fear: you gain free proficiency in the Intimidation skill."
            )),
            ("Relentless Endurance", (
                "When you are reduced to 0 Hit Points but not killed outright, you can drop to 1 Hit Point instead! "
                "(Once per long rest; this trait regularly turns the tide of combat in clutch moments)."
            )),
            ("Savage Attacks", (
                "When you score a critical hit with a melee weapon attack, you can roll one of the weapon's damage dice one additional time "
                "and add it to the extra damage of the critical hit!"
            ))
        ],
        "subraces_preview": [
            "Wild Clan Half-Orc (Shamanic traditions and hardened resistance to extreme wilderness)",
            "Urban Half-Orc (Adapted to mercantile guilds, city watch, or underworld enforcers)"
        ]
    },
    "Tiefling": {
        "tagline": "Bearers of an ancient infernal bloodline, mastering fire and dark magic while defying the prejudices of the world.",
        "bonuses_display": "+2 Charisma, +1 Intelligence",
        "languages": "Common, Infernal",
        "vision": "Darkvision 60 ft (18 m)",
        "lifespan": "Mature at the same rate as humans and live around 90-100 years.",
        "synergies": "Sensational for Sorcerers, Warlocks, Bards, and Wizards: commanding Charisma, fire resistance, and free innate spells.",
        "best_classes": "Sorcerer, Warlock, Bard, Wizard",
        "resistances": "Fire Resistance (halves all fire damage received - Hellish Resistance)",
        "key_traits_summary": "Darkvision 60ft, Hellish Resistance (Fire), Infernal Legacy (innate dark spells)",
        "category_tags": ["Darkvision", "Resistances", "Innate Magic"],
        "overview": (
            "Tieflings carry upon their flesh the indelible mark of an ancient pact struck by their ancestors with the lords of the Nine Hells. "
            "Imposing horns, skin in shades of crimson or bronze, sharp teeth, and a prehensile tail frequently make them targets of superstitious fear. "
            "Yet their destiny is not dictated by hellfire: many tieflings walk paths of nobility and redemption, wielding their dark gifts to protect the innocent and vanquish true monsters."
        ),
        "traits": [
            ("Darkvision", (
                "Your infernal eyes pierce darkness up to 60 feet in shades of red and gray."
            )),
            ("Hellish Resistance", (
                "Your infernal heritage shields you from flames: you have permanent resistance to fire damage (halving all fire damage from spells, traps, or dragon breath!)."
            )),
            ("Infernal Legacy", (
                "You manifest innate dark magic using Charisma as your spellcasting ability:\n"
                "• 1st level: You know the Thaumaturgy cantrip.\n"
                "• 3rd level: You can cast Hellish Rebuke as a 2nd-level spell once per long rest.\n"
                "• 5th level: You can cast Darkness once per long rest."
            ))
        ],
        "subraces_preview": [
            "Bloodline of Asmodeus (Intelligence and Charisma with Thaumaturgy, Hellish Rebuke, and Darkness)",
            "Bloodline of Mephistopheles (+1 Intelligence, Burning Hands, and Flame Blade)",
            "Bloodline of Zariel (+1 Strength, Searing Smite, and flame-infused martial prowess)",
            "Bloodline of Levistus (+1 Constitution, Ray of Frost, and Armor of Agathys)"
        ]
    }
}


def get_race_info(race_name: str, lang: Optional[str] = None) -> Dict[str, Any]:
    """Restituisce le informazioni dettagliate della razza o Umano come fallback, localizzate in lingua."""
    if lang is None:
        try:
            from common.i18n import get_current_language
            lang = get_current_language()
        except Exception:
            lang = "it"
            
    from common.i18n import translate_race
    it_name = translate_race(race_name, "it")
    base_info = dict(RACES.get(it_name, RACES.get(race_name, RACES["Umano"])))
    
    if lang == "en":
        en_info = RACES_EN.get(it_name, RACES_EN.get(race_name))
        if en_info:
            base_info.update(en_info)
    return base_info



def get_race_names() -> List[str]:
    """Restituisce l'elenco di tutte le razze disponibili ordinate."""
    return list(RACES.keys())
