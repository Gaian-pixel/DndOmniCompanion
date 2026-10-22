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


def get_race_info(race_name: str) -> Dict[str, Any]:
    """Restituisce le informazioni dettagliate della razza o Umano come fallback."""
    return RACES.get(race_name, RACES["Umano"])


def get_race_names() -> List[str]:
    """Restituisce l'elenco di tutte le razze disponibili ordinate."""
    return list(RACES.keys())
