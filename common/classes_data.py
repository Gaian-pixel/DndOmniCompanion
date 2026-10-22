# common/classes_data.py
"""
Catalogo completo e autentico delle 12 Classi di D&D 5e (SRD & Manuale del Giocatore):
- Descrizioni narrative approfondite ed evocative
- Ruolo tattico nel gruppo (Party Role)
- Dadi Vita e calcolo PF al 1° livello
- Caratteristiche primarie e Tiri Salvezza con competenza
- Competenze complete (Armature, Armi, Strumenti, Abilità di classe)
- Privilegi chiave di 1° Livello dettagliati con regole 5e
- Guida allo stile di gioco e consigli tattici (combattimento ed esplorazione)
- Anteprima degli archetipi e delle sottoclassi future
"""

from typing import Dict, Any, List, Tuple


CLASSES: Dict[str, Dict[str, Any]] = {
    "Barbaro": {
        "hd": 12,
        "role": "🛡️ Tank Primario & Danni da Mischia (Striker)",
        "tagline": "Un fiero guerriero primordiale alimentato da una furia selvaggia che sfida la morte e abbatte ogni ostacolo.",
        "primary_stat": "Forza (Attacco & Danni), Costituzione (Punti Ferita & CA)",
        "saving_throws": "Forza, Costituzione",
        "armor_prof": "Armature leggere, armature medie, scudi",
        "weapon_prof": "Armi semplici, armi marziali",
        "tools_prof": "Nessuno",
        "skills_info": "2 a scelta tra Atletica, Addestrare Animali, Intimidire, Natura, Percezione, Sopravvivenza",
        "overview": (
            "Dalle gelide tundre del nord ai recessi delle giungle primordiali, i barbari incarnano la potenza indomita "
            "della terra. In battaglia non si affidano alla fredda tecnica accademica, ma risvegliano una furia ancestrale "
            "che accresce a dismisura la loro possanza muscolare, affina i riflessi e rende il loro corpo eccezionalmente "
            "resistente al dolore. Per un barbaro, lo scontro è la massima celebrazione dei sensi e dell'istinto vitale."
        ),
        "features_lvl1": [
            ("Ira (Rage)", (
                "In combattimento puoi entrare in Ira come azione bonus (2 volte per riposo lungo al 1° livello).\n"
                "Finché sei in ira e non indossi armature pesanti:\n"
                "• Vantaggio a tutte le prove e ai tiri salvezza su Forza.\n"
                "• Bonus di +2 ai tiri per i danni degli attacchi in mischia che usano la Forza.\n"
                "• Resistenza ai danni contundenti, perforanti e taglienti (dimezza tutti i danni fisici subiti!).\n"
                "L'Ira dura 1 minuto e termina se perdi i sensi o se non attacchi una creatura ostile né subisci danni in un turno."
            )),
            ("Difesa Senz'Armatura (Unarmored Defense)", (
                "Finché non indossi alcuna armatura, la tua Classe Armatura è pari a 10 + modificatore di Destrezza + "
                "modificatore di Costituzione. Puoi comunque impugnare uno scudo mantenendo questo beneficio (+2 CA)."
            ))
        ],
        "playstyle": (
            "Sei la roccia inamovibile e la forza d'urto d'avanguardia del gruppo. Grazie al Dado Vita più alto di tutto "
            "il gioco (d12) e alla Resistenza ai danni garantita dall'Ira, puoi catapultarti nel cuore delle formazioni nemiche, "
            "assorbire i colpi più devastanti al posto degli alleati fragili e distruggere i bersagli chiave a colpi d'ascia o martello. "
            "Fuori dalla mischia, i tuoi sensi acuti e la tua prestanza atletica ti rendono eccellente per superare ostacoli fisici e pericoli selvaggi."
        ),
        "subclasses_preview": [
            "Cammino del Berserker (Frenesia travolgente con attacchi bonus come azione bonus e immunità a charme e spavento)",
            "Cammino del Combattente Totemico (Spirito dell'Orso per ottenere resistenza a ogni tipo di danno tranne psichico, Aquila o Lupo)",
            "Cammino dello Zelota (Furia divina con danni radiosi/necrotici ad ogni colpo e resurrezione a costo zero)"
        ]
    },
    "Bardo": {
        "hd": 8,
        "role": "🎭 Supporto d'Eccellenza, Buffer/Debuffer, Faccia del Party & Factotum",
        "tagline": "Maestro della parola, della canzone e della magia sottile, capace di tessere incantesimi dalle melodie del multiverso.",
        "primary_stat": "Carisma (Incantesimi & Abilità Sociali), Destrezza (CA & Armi Accurate)",
        "saving_throws": "Destrezza, Carisma",
        "armor_prof": "Armature leggere",
        "weapon_prof": "Armi semplici, balestre a mano, spade lunghe, stocchi, spade corte",
        "tools_prof": "3 strumenti musicali a scelta",
        "skills_info": "3 abilità qualsiasi a scelta (massima versatilità di personalizzazione)",
        "overview": (
            "Che intoni ballate nelle grandi corti o decanti leggende proibite nelle taverne del porto, il bardo comprende che "
            "il cosmo è scaturito dalla musica primordiale della Creazione. Imparando a manipolare tali armonie, il bardo tesse "
            "incantesimi che confondono la mente avversaria, risanano le ferite degli alleati e infondono coraggio anche dinanzi a draghi e demoni."
        ),
        "features_lvl1": [
            ("Incantesimi Bardici (Spellcasting)", (
                "Lanci incantesimi attingendo all'Armonia Cosmica usando il Carisma (CD = 8 + competenza + mod. Carisma).\n"
                "• Conosci 2 trucchetti e 4 incantesimi di 1° livello (con 2 slot al 1° livello).\n"
                "• Puoi usare uno strumento musicale come focus arcano e lanciare incantesimi contrassegnati come rituali."
            )),
            ("Ispirazione Bardica (Bardic Inspiration - d6)", (
                "Come azione bonus, puoi donare un dado Ispirazione Bardica (d6) a un alleato entro 18 metri.\n"
                "Entro i successivi 10 minuti, l'alleato può aggiungere il dado a un tiro per colpire, prova di caratteristica "
                "o tiro salvezza. Usi per riposo lungo pari al tuo modificatore di Carisma (minimo 1)."
            ))
        ],
        "playstyle": (
            "Sei il moltiplicatore di forza e il centro strategico del gruppo. Durante il combattimento controlli il flusso "
            "dello scontro con incantesimi di ammaliamento e illusione (come Sonno, Risata Incontenibile di Tasha, Parola Guaritrice per salvare "
            "compagni a distanza con azione bonus) dispensando dadi Ispirazione. Fuori dalla battaglia, le tue virtù sociali e la vastità delle tue competenze "
            "ti consentono di superare con eleganza ogni enigma o trattativa."
        ),
        "subclasses_preview": [
            "Collegio della Sapienza (Parole Taglienti per sabotare tiri nemici e Segreti Magici rubati da qualsiasi classe)",
            "Collegio del Valore (Armature medie, scudi, armi marziali e Ispirazione utilizzabile per infliggere danni extra)",
            "Collegio delle Spade (Duellante acrobatico ed elegante specializzato in fioriture d'armi e velocità da schermidore)"
        ]
    },
    "Chierico": {
        "hd": 8,
        "role": "☀️ Guaritore Supremo, Custode Divino, Buffer Protettivo & Off-Tank",
        "tagline": "Campione consacrato di una divinità o ideale cosmico, brandisce il potere dei piani per sanare i giusti e purificare il male.",
        "primary_stat": "Saggezza (Incantesimi), Costituzione (Concentrazione & PF), Forza (se in mischia)",
        "saving_throws": "Saggezza, Carisma",
        "armor_prof": "Armature leggere, armature medie, scudi (più armature pesanti con alcuni Domini)",
        "weapon_prof": "Armi semplici (più armi marziali con alcuni Domini)",
        "tools_prof": "Nessuno (utilizza un Simbolo Sacro come focus)",
        "skills_info": "2 a scelta tra Storia, Intuizione, Medicina, Persuasione, Religione",
        "overview": (
            "I chierici sono i tramiti viventi attraverso cui gli dèi manifestano la loro volontà nei regni mortali. "
            "Non sono semplici studiosi o officianti, ma veri campioni investiti direttamente di parte della grazia e della gloria divina. "
            "Con una preghiera sussurrata possono chiudere ferite mortali, benedire le armi degli alleati e scatenare tempeste di luce purificatrice."
        ),
        "features_lvl1": [
            ("Incantesimi Divini (Spellcasting)", (
                "Accedi all'intera lista degli incantesimi da chierico e prepari ogni mattina un numero di incantesimi pari a "
                "mod. Saggezza + livello da chierico. Conosci 3 trucchetti e possiedi 2 slot di 1° livello al 1° livello. "
                "Puoi lanciare rituali per gli incantesimi preparati che possiedono il tag rituale."
            )),
            ("Dominio Divino (Divine Domain - al 1° Livello)", (
                "Scegli la tua specializzazione divina fin dal 1° livello! Ciascun Dominio (Vita, Luce, Guerra, Tempesta, Inganno, Natura, Conoscenza) "
                "fornisce incantesimi di dominio permanentemente preparati e privilegi immediati unici (es. Vita concede armature pesanti e cure "
                "potenziate; Luce dardi radiosi e bagliori difensivi accecanti; Guerra attacchi aggiuntivi come azione bonus)."
            ))
        ],
        "playstyle": (
            "Sei il fondamento e l'assicurazione sulla vita di ogni gruppo d'avventura. Con magie essenziali come Benedizione (Bless), "
            "Parola Guaritrice (Healing Word) e Santuario puoi ribaltare le sorti di qualsiasi scontro. La combinazione di scudo, ottima armatura "
            "e incantesimi a tocco o a distanza ti consente di combattere comodamente sia in prima linea al fianco del guerriero che nelle retrovie."
        ),
        "subclasses_preview": [
            "Dominio della Vita (Il maestro supremo delle cure, ottiene armature pesanti e bonus massicci a tutti gli incantesimi di guarigione)",
            "Dominio della Guerra (Guerriero sacro con armature pesanti, armi marziali e attacchi aggiuntivi concessi dalla divinità)",
            "Dominio della Luce (Scatena bagliori radiosi accecanti, dardi di fuoco sacro e la devastante Palla di Fuoco)",
            "Dominio della Tempesta (Flagello delle nubi con contrattacchi elettrici e massimizzazione istantanea dei danni da fulmine e tuono)"
        ]
    },
    "Druido": {
        "hd": 8,
        "role": "🌿 Controllo del Campo (Crowd Control), Mutaforma, Guaritore & Tank Adattivo",
        "tagline": "Sacerdote della Vecchia Fede e custode dell'equilibrio naturale, muta la sua forma in fiera e comanda le forze della terra.",
        "primary_stat": "Saggezza (Incantesimi & Natura), Costituzione e Destrezza (Sopravvivenza)",
        "saving_throws": "Intelligenza, Saggezza",
        "armor_prof": "Armature leggere, medie, scudi (i druidi non indossano armature o scudi di metallo)",
        "weapon_prof": "Clave, pugnali, dardi, giavellotti, mazze, bastoni ferrati, scimitarre, falcetti, fionde, lance",
        "tools_prof": "Borsa da erborista",
        "skills_info": "2 a scelta tra Arcana, Addestrare Animali, Intuizione, Medicina, Natura, Percezione, Religione, Sopravvivenza",
        "overview": (
            "Lontano dal chiasso delle città fortificate, i druidi si radunano in cerchi megalitici e boschi sacri per onorare l'Antica Fede. "
            "Considerano la natura non un bene da sfruttare, ma un ecosistema sacro di cui preservare l'equilibrio. "
            "Quando tale armonia viene minacciata da aberrazioni o distruzione cieca, il druido scuote le fondamenta del suolo, "
            "invoca rampicanti soffocanti e scatena la furia primordiale degli artigli e delle zanne."
        ),
        "features_lvl1": [
            ("Incantesimi Druidici (Spellcasting)", (
                "Prepari ogni mattina incantesimi dall'intera lista del druido (mod. Saggezza + livello da druido). "
                "Conosci 2 trucchetti e disponi di 2 slot di 1° livello al 1° livello. Possiedi magie di alterazione ambientale "
                "e controllo territoriale senza rivali (Intralciare, Nube di Nebbia) e prodigi curativi (Bacche Benefiche, Cura Ferite)."
            )),
            ("Linguaggio Druidico (Druidic)", (
                "Conosci il Druidico, la lingua segreta dei custodi naturali, e sai scorgere e lasciare messaggi occulti celati "
                "nella corteccia, tra le pietre o nel fogliame, visibili solo ad altri compagni dell'Antica Fede."
            )),
            ("Forma Selvatica (Wild Shape - al 2° Livello)", (
                "Al 2° livello sblocchi la capacità leggendaria di mutare forma in una bestia (lupo, orso, ragno, falco): "
                "ottieni i punti ferita, la forza fisica, la velocità e i sensi speciali della fiera, creando una riserva di salute autonoma!"
            ))
        ],
        "playstyle": (
            "Sei il signore del campo di battaglia e un maestro assoluto di adattamento. In combattimento puoi paralizzare o rallentare "
            "intere formazioni nemiche con liane e nebbie fitte mentre nutri e curi gli alleati con le Bacche Benefiche. Fuori dallo scontro, "
            "la Forma Selvatica ti permette di infiltrarti ovunque come minuscolo insetto o esplorare canyon e scogliere impervie."
        ),
        "subclasses_preview": [
            "Circolo della Luna (Potenzia al massimo la Forma Selvatica: trasformazione in bestie predatrici letali come azione bonus e cure con slot)",
            "Circolo della Terra (Recupero naturale degli slot durante i riposi brevi e incantesimi legati ai biomi di montagna, foresta o palude)",
            "Circolo dei Sogni (Cure fatate a distanza che non consumano slot e rifugi magici inviolabili durante i riposi)"
        ]
    },
    "Guerriero": {
        "hd": 10,
        "role": "⚔️ Pilastro Marziale, Maestro d'Armi, Tank Difensivo & Striker Inarrestabile",
        "tagline": "Campione assoluto dell'arte militare e dell'acciaio, forgiato da una disciplina ferrea e versatile in ogni teatro di guerra.",
        "primary_stat": "Forza (Armi Pesanti & Armature a Piastre) o Destrezza (Tiro con l'Arco & Armi Accurate)",
        "saving_throws": "Forza, Costituzione",
        "armor_prof": "Tutte le armature (leggere, medie, pesanti), tutti gli scudi",
        "weapon_prof": "Tutte le armi semplici, tutte le armi marziali",
        "tools_prof": "Nessuno",
        "skills_info": "2 a scelta tra Acrobazia, Addestrare Animali, Atletica, Storia, Intuizione, Intimidire, Percezione, Sopravvivenza",
        "overview": (
            "Non tutti gli eroi devono il proprio valore a scintille divine o sangue fatato: il guerriero conquista la propria leggenda "
            "palmo a palmo con il sudore della fronte, la disciplina inflessibile e la padronanza millimetrica di ogni lama, scudo e armatura. "
            "Che sia un veterano brizzolato, una sentinella d'élite o un mercenario d'onore, il guerriero non cede mai dinanzi al pericolo ed è "
            "capace di sferrare più attacchi per round di chiunque altro sul campo di battaglia."
        ),
        "features_lvl1": [
            ("Stile di Combattimento (Fighting Style)", (
                "Scegli una specializzazione passiva permanente a scelta:\n"
                "• Tiro: Bonus permanente di +2 a tutti i tiri per colpire effettuati con armi a distanza.\n"
                "• Difesa: Bonus permanente di +1 alla Classe Armatura mentre indossi un'armatura.\n"
                "• Duellare: +2 ai danni quando impugni un'arma da mischia a una mano e nessun'altra arma.\n"
                "• Armi a Due Mani: Se ottieni 1 o 2 su un dado di danno con un'arma impugnata a due mani, puoi ritirare il dado.\n"
                "• Protezione: Usa la reazione per imporre Svantaggio a un attacco nemico contro un alleato adiacente usando il tuo scudo.\n"
                "• Combattere con Due Armi: Aggiungi il tuo modificatore di caratteristica anche al danno del secondo attacco."
            )),
            ("Secondo Fiato (Second Wind)", (
                "Possiedi una riserva di vigore a cui attingere nei momenti critici. Come azione bonus nel tuo turno, puoi recuperare "
                "un numero di punti ferita pari a 1d10 + il tuo livello da guerriero. Si ricarica con un riposo breve o lungo!"
            ))
        ],
        "playstyle": (
            "Sei la spina dorsale tattica di qualsiasi gruppo. La tua impareggiabile versatilità ti consente di plasmare esattamente "
            "il combattente che desideri: baluardo difensivo impenetrabile con scudo e corazza a piastre, infallibile tiratore scelto da 180 metri, "
            "o devastatore d'assalto con spadone a due mani. Con il Secondo Fiato e la futura Azione Furente (Action Surge al 2° livello), possiedi "
            "una resilienza e un potenziale di impatto immediato ineguagliati."
        ),
        "subclasses_preview": [
            "Campione (Pura eccellenza atletica: mette a segno colpi critici con un tiro di 19-20 sul d20 ed eccelle in ogni prova fisica)",
            "Maestro di Battaglia (Genio tattico con dadi di superiorità per manovre come disarmare, atterrare e guidare i compagni)",
            "Cavaliere Mistico (Combina la scherma marziale con la magia arcana di Abiurazione ed Evocazione: Scudo, Dardo Incantato e legame con l'arma)"
        ]
    },
    "Ladro": {
        "hd": 8,
        "role": "🗡️ Striker Furtivo a Singolo Bersaglio, Disattivatore di Trappole, Scout & Maestro delle Abilità",
        "tagline": "Maestro delle ombre, dell'inganno e della precisione chirurgica; colpisce nei punti vitali prima di dissolversi nel buio.",
        "primary_stat": "Destrezza (Attacco furtivo, CA, Iniziativa, Scasso), Intelligenza o Carisma",
        "saving_throws": "Destrezza, Intelligenza",
        "armor_prof": "Armature leggere",
        "weapon_prof": "Armi semplici, balestre a mano, spade lunghe, stocchi, spade corte",
        "tools_prof": "Strumenti da scasso (Thieves' Tools)",
        "skills_info": "4 abilità a scelta tra Acrobazia, Atletica, Furtività, Indagare, Inganno, Intimidire, Intrattenere, Intuizione, Percezione, Persuasione, Rapidità di Mano",
        "overview": (
            "I ladri sanno che la forza bruta è spesso un vicolo cieco: un colpo ben assestato tra i punti deboli di una corazza "
            "o un meccanismo sabotato nell'ombra neutralizzano il più temibile signore della guerra in un attimo. "
            "Che operi come spia di corte, acrobata, cacciatore di tesori perduti o genio del crimine, il ladro trova sempre una via "
            "dove gli altri vedono soltanto vicoli ciechi e porte sbarrate."
        ),
        "features_lvl1": [
            ("Attacco Furtivo (Sneak Attack)", (
                "Una volta per turno, infliggi 1d6 danni extra a una creatura colpita con un'arma accurata o a distanza se hai Vantaggio al tiro per colpire.\n"
                "Non ti serve il vantaggio se un alleato è adiacente al bersaglio (entro 1,5m), purché tu non sia svantaggiato!\n"
                "Il danno furtivo cresce con la tua progressione (2d6 al 3°, 3d6 al 5°, fino a 10d6)."
            )),
            ("Maestria (Expertise)", (
                "Scegli 2 delle tue competenze nelle abilità (oppure 1 abilità e gli Strumenti da Scasso): il tuo bonus di competenza "
                "viene raddoppiato per tutte le prove che utilizzano le competenze scelte! (Es. Furtività o Scasso quasi infallibili)."
            )),
            ("Gergo Ladresco (Thieves' Cant)", (
                "Un miscuglio segreto di dialetto, frasi in codice e segni grafici nascosti per scambiare messaggi e individuare rifugi sicuri."
            ))
        ],
        "playstyle": (
            "Sei l'ombra letale e il risolutore di problemi tecnici del gruppo. In combattimento sfrutta i compagni da mischia per "
            "attivare sistematicamente l'Attacco Furtivo a ogni round. Al 2° livello sbloccherai l'Azione Scaltra (Cunning Action), con cui "
            "potrai Scattare, Disimpegnarti o Nasconderti come azione bonus ogni singolo turno, diventando un bersaglio imprendibile. "
            "Fuori dalla battaglia, nessun forziere o congegno mortale può resistere alla tua perizia con i grimaldelli."
        ),
        "subclasses_preview": [
            "Furfante (Mani rapide per borseggiare e usare oggetti come azione bonus, oltre ad agilità e arrampicata superiore)",
            "Assassino (Letalità estrema con colpi critici istantanei automatici contro qualsiasi nemico colto di sorpresa)",
            "Mistificatore Arcano (Fonde furtività e trucchi magici con una Mano Magica invisibile in grado di disarmare congegni a distanza)"
        ]
    },
    "Mago": {
        "hd": 6,
        "role": "🔮 Maestro del Controllo dell'Area, Danni Magici ad Area (Blaster) & Risolutore Arcano",
        "tagline": "Il sommo studioso delle leggi arcane, custode del più vasto e formidabile grimorio di incantesimi del multiverso.",
        "primary_stat": "Intelligenza (Incantesimi & CD), Costituzione e Destrezza (Sopravvivenza & Concentrazione)",
        "saving_throws": "Intelligenza, Saggezza",
        "armor_prof": "Nessuna armatura, nessuno scudo",
        "weapon_prof": "Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",
        "tools_prof": "Nessuno (utilizza Bacchetta, Verga, Cristallo o Grimorio come focus)",
        "skills_info": "2 a scelta tra Arcana, Storia, Intuizione, Indagare, Medicina, Religione",
        "overview": (
            "Per il mago la magia non è un dono ereditario né una grazia divina: è una scienza esatta e sublime, le cui formule "
            "si svelano solo attraverso decenni di studio meticoloso, calcoli rigorosi e sperimentazioni ardite. "
            "I maghi trascrivono ogni formula nel loro prezioso grimorio, catalogando i segreti dell'universo per piegare tempo, "
            "spazio, gravità, fuoco e mente al proprio volere intellettuale."
        ),
        "features_lvl1": [
            ("Libro degli Incantesimi (Grimorio & Incantesimi)", (
                "Inizi con 3 trucchetti e un libro che contiene ben 6 incantesimi di 1° livello. Prepari ogni mattina un numero di incantesimi "
                "pari a mod. Intelligenza + livello da mago. Inoltre, puoi trascrivere nel grimorio qualsiasi pergamena o libro di magia trovato!"
            )),
            ("Lancio di Rituali (Ritual Casting)", (
                "Puoi lanciare qualsiasi incantesimo da mago presente nel tuo grimorio con il tag rituale (es. Individuazione del Magico, Identificare, "
                "Allarme, Trova Famiglio) senza consumare slot e senza neanche averlo preparato, aggiungendo 10 minuti al tempo di lancio!"
            )),
            ("Recupero Arcano (Arcane Recovery)", (
                "Una volta al giorno durante un riposo breve, puoi meditare sul tuo libro per recuperare slot incantesimo spesi "
                "pari a metà del tuo livello da mago arrotondato per eccesso (al 1° livello recuperi 1 slot di 1° livello)."
            ))
        ],
        "playstyle": (
            "Sei l'arsenale strategico supremo e l'artiglieria magica del gruppo. Sebbene fisicamente vulnerabile (Dado Vita d6 e nessuna armatura), "
            "disponi di risposte per ogni pericolo: Armatura Magica e Scudo per la difesa, Dardo Incantato per colpi infallibili, Sonno per neutralizzare "
            "intere pattuglie senza versare sangue, e rituali gratuiti che risolvono esplorazioni e indagini complesse."
        ),
        "subclasses_preview": [
            "Scuola di Invocazione (Maestro del fuoco e del fulmine: plasma gli incantesimi ad area per risparmiare automaticamente i compagni)",
            "Scuola di Abiurazione (Scudo e protezione magica: genera un'Egidia Arcana che assorbe i danni al posto del mago o degli alleati)",
            "Scuola di Divinazione (Presagio: tira due d20 ogni mattina e sostituisci qualsiasi tiro per colpire o salvezza della giornata con quei dadi)"
        ]
    },
    "Monaco": {
        "hd": 8,
        "role": "🥋 Skirmisher Ipermobile, Disruptor da Mischia, Cacciatore di Incantatori & Maestro del Ki",
        "tagline": "Maestro asceta delle arti marziali che incanala l'energia spirituale del Ki per colpire a raffica e muoversi come il vento.",
        "primary_stat": "Destrezza (Attacchi, Danni senz'armi & CA), Saggezza (CA & CD del Ki)",
        "saving_throws": "Forza, Destrezza",
        "armor_prof": "Nessuna armatura, nessuno scudo (il corpo è l'arma e l'armatura perfetta)",
        "weapon_prof": "Armi semplici, spade corte",
        "tools_prof": "Uno strumento da artigiano o uno strumento musicale a scelta",
        "skills_info": "2 a scelta tra Acrobazia, Atletica, Storia, Intuizione, Religione, Furtività",
        "overview": (
            "Nei monasteri arroccati su cime impervie o nascosti tra valli solitarie, i monaci apprendono a purificare corpo e spirito. "
            "Attraverso la meditazione e l'allenamento fisico estenuante, imparano a controllare il Ki: l'energia vitale primordiale che "
            "scorre in tutti i viventi. Senza corazze ingombranti né armi possenti, i loro pugni e calci fendono l'aria con la durezza dell'acciaio."
        ),
        "features_lvl1": [
            ("Difesa Senz'Armatura (Unarmored Defense)", (
                "Finché non indossi armature né scudi, la tua Classe Armatura è pari a 10 + mod. Destrezza + mod. Saggezza."
            )),
            ("Arti Marziali (Martial Arts)", (
                "Il tuo addestramento conferisce vantaggi unici con colpi senz'armi e armi da monaco (spade corte e armi semplici senza proprietà a due mani/pesante):\n"
                "• Puoi usare la Destrezza anziché la Forza per i tiri per colpire e per i danni.\n"
                "• I tuoi colpi senz'armi infliggono 1d4 danni contundenti (scala a 1d6, 1d8, 1d10 coi livelli).\n"
                "• Quando usi l'azione Attacco con un'arma da monaco o senz'armi, puoi compiere un attacco senz'armi addizionale come azione bonus (2 attacchi a round già dal 1° liv a costo zero!)."
            )),
            ("Energia Ki (al 2° Livello)", (
                "Al 2° livello ottieni punti Ki (che si ricaricano con un riposo breve!) per la Raffica di Colpi (due attacchi bonus immediati), "
                "Difesa Paziente (Schivata come azione bonus) e Passo del Vento (Disimpegno o Scatto con salto raddoppiato)."
            ))
        ],
        "playstyle": (
            "Sei un turbine rapido e imprevedibile. La tua eccezionale velocità ti permette di aggirare i difensori nemici, piombare sugli incantatori "
            "o sui tiratori avversari nelle retrovie e bersagliarli con colpi multipli continui. Al 5° livello sbloccherai il Colpo Stordente (Stunning Strike), "
            "con cui potrai paralizzare i nemici più pericolosi per un intero round spendendo solo 1 punto Ki."
        ),
        "subclasses_preview": [
            "Via della Mano Aperta (I colpi della Raffica atterrano, spingono di 4,5 metri o negano le reazioni ai nemici)",
            "Via dell'Ombra (Guerriero ninja che si teletrasporta da un'ombra all'altra a costo zero e crea oscurità magica)",
            "Via dei Quattro Elementi (Canalizza il Ki per scatenare getti infuocati, onde d'urto telluriche e folate di vento tagliente)"
        ]
    },
    "Paladino": {
        "hd": 10,
        "role": "🛡️ Tank Corazzato da Prima Linea, Danni da Raffica Esplosivi (Burst Smite) & Faro delle Auree",
        "tagline": "Sacro crociato vincolato da un giuramento incrollabile, fonde possanza marziale, armature pesanti e punizioni celesti.",
        "primary_stat": "Forza (Attacchi da Mischia & Armature Pesanti), Carisma (Incantesimi, Auree & CD)",
        "saving_throws": "Saggezza, Carisma",
        "armor_prof": "Tutte le armature (leggere, medie, pesanti), tutti gli scudi",
        "weapon_prof": "Tutte le armi semplici, tutte le armi marziali",
        "tools_prof": "Nessuno (utilizza un Simbolo Sacro come focus)",
        "skills_info": "2 a scelta tra Atletica, Intuizione, Intimidire, Medicina, Persuasione, Religione",
        "overview": (
            "Un paladino è definito dal proprio Giuramento: una promessa solenne e incrollabile fatta a una causa, a una divinità "
            "o a un principio assoluto di giustizia o redenzione. Tale determinazione è talmente pura da manifestarsi fisicamente sotto forma "
            "di grazia miracolosa che emana come luce splendente dalle sue armi, protegge i compagni dalle maledizioni e cura le ferite più atroci."
        ),
        "features_lvl1": [
            ("Senso del Divino (Divine Sense)", (
                "Come azione, espandi la tua percezione spirituale: fino alla fine del tuo prossimo turno, conosci la posizione esatta "
                "di ogni celestiale, immondo o non morto entro 18 metri non celato da copertura totale, e percepisci luoghi e oggetti consacrati o sconsacrati. "
                "Usi per riposo lungo pari a 1 + mod. Carisma."
            )),
            ("Imposizione delle Mani (Lay on Hands)", (
                "Possiedi una riserva curativa benedetta pari a 5 volte il tuo livello da paladino (5 PF al 1° livello).\n"
                "Con un tocco come azione, puoi ripristinare PF dalla tua riserva a una creatura toccata, oppure spendere 5 PF della riserva "
                "per guarirla da una malattia o neutralizzare un veleno. La riserva si riempie completamente con un riposo lungo."
            )),
            ("Punizione Divina (Divine Smite - al 2° Livello)", (
                "Dal 2° livello puoi convertire slot incantesimo in devastanti danni radiosi extra (+2d8 o più!) quando metti a segno "
                "un colpo decisivo con un'arma da mischia, raddoppiando tutti i dadi sui colpi critici!"
            ))
        ],
        "playstyle": (
            "Sei il baluardo corazzato e il flagello delle creature dell'oscurità. In armatura a piastre e scudo sei quasi impenetrabile, "
            "mentre con l'Imposizione delle Mani puoi strappare gli alleati alla morte a costo zero. Quando affronti i nemici più coriacei, "
            "scaricare la Punizione Divina su un colpo critico provocherà picchi di danno radioso capaci di incenerire qualsiasi boss."
        ),
        "subclasses_preview": [
            "Giuramento di Devozione (Il cavaliere splendente con armi infuse di luce sacra, scaccia non morti e immunità a charme)",
            "Giuramento degli Antichi (Campione della vita e della Selva Fatata: dona un'Aura di Resistenza che dimezza tutti i danni da incantesimi)",
            "Giuramento di Vendetta (Cacciatore inflessibile che ottiene Vantaggio automatico su tutti i tiri contro il bersaglio marchiato)"
        ]
    },
    "Ranger": {
        "hd": 10,
        "role": "🏹 Tiratore Infallibile (Sniper o Combattente a Due Armi), Scout d'Avanguardia & Guida Naturale",
        "tagline": "Maestro delle tracce e sentinella dei confini naturali, fonde precisione marziale e comunione con le terre selvagge.",
        "primary_stat": "Destrezza (Arco, Armi Accurate, CA & Iniziativa), Saggezza (Percezione, Sopravvivenza & Magia)",
        "saving_throws": "Forza, Destrezza",
        "armor_prof": "Armature leggere, armature medie, scudi",
        "weapon_prof": "Tutte le armi semplici, tutte le armi marziali",
        "tools_prof": "Nessuno",
        "skills_info": "3 a scelta tra Addestrare Animali, Atletica, Furtività, Indagare, Intuizione, Natura, Percezione, Sopravvivenza",
        "overview": (
            "Oltre i confini delle città fortificate si estendono foreste millenarie, paludi spettrali e picchi montani proibitivi. "
            "È qui che vive il ranger: una sentinella silenziosa che conosce i punti deboli di ogni predatore e le insidie del territorio. "
            "Il ranger anticipa le mosse delle creature mostruose, abbattendole nelle terre selvagge prima che possano minacciare il mondo civilizzato."
        ),
        "features_lvl1": [
            ("Nemico Prescelto (Favored Enemy)", (
                "Scegli una categoria di nemici giurati (es. Non-morti, Draghi, Bestie, Aberrazioni, o due etnie umanoidi come orchetti e goblin):\n"
                "• Vantaggio a tutte le prove di Saggezza (Sopravvivenza) per tracciarli.\n"
                "• Vantaggio a tutte le prove di Intelligenza per ricordare o dedurre informazioni su di essi.\n"
                "• Impari una lingua parlata dai tuoi nemici prescelti."
            )),
            ("Esploratore Naturale (Natural Explorer)", (
                "Scegli un ambiente prediletto (Foresta, Montagna, Palude, Prateria, Sottosuolo, ecc.). Nel tuo terreno:\n"
                "• Il terreno difficile non rallenta il viaggio del gruppo.\n"
                "• Il gruppo non può perdersi se non per magia.\n"
                "• Rimani vigile ai pericoli anche mentre cacci o cartografi.\n"
                "• Ti muovi furtivamente a velocità normale e ricavi il doppio del cibo cacciando provviste.\n"
                "• Tracciando creature ne scopri numero esatto, taglia e quanto tempo fa sono passate."
            )),
            ("Incantesimi del Ranger (al 2° Livello)", (
                "Dal 2° livello ottieni lo Stile di Combattimento (es. Tiro per +2 ai colpi a distanza) e incantesimi celebri come Marchio del Cacciatore (+1d6 danni su ogni colpo)."
            ))
        ],
        "playstyle": (
            "Sei la guida insostituibile durante i viaggi e il tiratore letale nelle schermaglie. Grazie alla tua vigilanza, il gruppo non cadrà "
            "mai vittima di imboscate. In combattimento puoi colpire a grandissima distanza con l'arco lungo abbattendo minacce volanti, oppure "
            "danzare nella mischia sferrando attacchi continui con due armi."
        ),
        "subclasses_preview": [
            "Cacciatore (Tecniche marziali specializzate come Ammazzagiganti e Sterminatore di Orde)",
            "Signore delle Bestie (Stringe un legame telepatico con un fiero compagno animale che combatte al suo fianco)",
            "Cacciatore delle Tenebre / Gloom Stalker (Terrore del buio: attacchi extra micidiali ed invisibile a chi usa la Scurovisione)"
        ]
    },
    "Stregone": {
        "hd": 6,
        "role": "💥 Bombardiere Arcano (Blaster), Nuke a Bersaglio Multiplo, Manipolatore di Magia & Volto",
        "tagline": "Incantatore con la magia che gli scorre direttamente nel sangue, capace di piegare e alterare le leggi dell'arcano con la Metamagia.",
        "primary_stat": "Carisma (Incantesimi, Attacchi & CD), Costituzione (Punti Ferita & Concentrazione)",
        "saving_throws": "Costituzione, Carisma (La competenza nei TS di Costituzione garantisce una tenuta eccezionale della Concentrazione)",
        "armor_prof": "Nessuna armatura, nessuno scudo",
        "weapon_prof": "Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",
        "tools_prof": "Nessuno (utilizza un Cristallo, Verga, Bacchetta o Focus Arcano)",
        "skills_info": "2 a scelta tra Arcana, Inganno, Intimidire, Intuizione, Persuasione, Religione",
        "overview": (
            "Lo stregone non ha bisogno di passare notti insonni su antichi tomi né di pregare divinità distanti: per lui la magia è "
            "un diritto di nascita, un fuoco primordiale che vibra direttamente nel suo sangue. Che tale retaggio discenda da un antenato drago, "
            "dall'esposizione al caos puro o da un influsso celestiale, lo stregone plasma l'energia arcana attraverso la pura forza della personalità."
        ),
        "features_lvl1": [
            ("Incantesimi Innati (Spellcasting)", (
                "Lanci incantesimi usando il Carisma. Inizi con ben 4 trucchetti (più di ogni altra classe al 1° liv!) e conosci 2 incantesimi "
                "di 1° livello con 2 slot al 1° livello. I tuoi incantesimi sono parte di te e non devono mai essere preparati al mattino."
            )),
            ("Origine Stregonesca (Sorcerous Origin - al 1° Livello)", (
                "Scegli la fonte del tuo potere arcano fin dal 1° livello!\n"
                "• Discendenza Draconica: Linguaggio Draconico, CA base senz'armatura pari a 13 + mod. Destrezza (scaglie protettive), e +1 PF massimo per ogni livello!\n"
                "• Magia Selvaggia: Maree del Caos (ottieni Vantaggio a comando a un tiro) rischiando di scatenare imprevedibili Sovraccarichi di Magia Selvaggia!"
            )),
            ("Metamagia & Punti Stregoneria (al 2° e 3° Livello)", (
                "Sblocchi l'abilità unica di alterare le regole degli incantesimi: Incantesimo Rapido (lancia come azione bonus magie da 1 azione normale!), "
                "Incantesimo Raddoppiato (colpisce due bersagli distinti con un incantesimo a bersaglio singolo), Incantesimo Esteso o Distante."
            ))
        ],
        "playstyle": (
            "Sei una potenza d'attacco devastante e concentrata. La competenza nativa nei Tiri Salvezza su Costituzione ti permette di mantenere "
            "la Concentrazione attiva anche quando subisci ferite. Con la Metamagia potrai infrangere le limitazioni dell'azione economica di D&D, "
            "lanciando una Palla di Fuoco come azione bonus e un trucchetto subito dopo, o raddoppiando potenziamenti vitali su due compagni."
        ),
        "subclasses_preview": [
            "Discendenza Draconica (Resistenza e danni elementali del tipo di drago scelto, ali di drago per volare al 14° livello)",
            "Magia Selvaggia (Manipolatore del fato e delle probabilità cosmiche con scariche di magia incontrollata)",
            "Anima Favolosa / Divine Soul (Scintilla divina: permette di scegliere incantesimi sia dalla lista dello Stregone che del Chierico)"
        ]
    },
    "Warlock": {
        "hd": 8,
        "role": "🔮 Cecchino Arcano a Volontà (Eldritch Blast), Magia a Ricarica Rapida (Riposo Breve) & Striker Ibrido",
        "tagline": "Cercatore di segreti proibiti legato da un patto occulto a un'entità ultraterrena; esercita slot che si ricaricano a ogni Riposo Breve!",
        "primary_stat": "Carisma (Incantesimi & CD), Destrezza e Costituzione (Sopravvivenza & CA)",
        "saving_throws": "Saggezza, Carisma",
        "armor_prof": "Armature leggere",
        "weapon_prof": "Armi semplici",
        "tools_prof": "Nessuno (utilizza un Focus Arcano)",
        "skills_info": "2 a scelta tra Arcana, Storia, Inganno, Intimidire, Indagare, Natura, Religione",
        "overview": (
            "Spinto da un'insaziabile brama di conoscenza o costretto da un destino avverso, il warlock ha osato stipulare un patto con "
            "un'entità millenaria appartenente a dimensioni ultraterrene: un arcidiavolo infernale, una regina delle fate, un'aberrazione "
            "delle stelle oscure o una lama senziente d'ombra. In cambio di servigi o devozione, ottiene brandelli di un potere occulto e devastante."
        ),
        "features_lvl1": [
            ("Patrono Ultraterreno (Otherworldly Patron - al 1° Livello)", (
                "Scegli l'entità soprannaturale patrona fin dal 1° livello!\n"
                "• Il Signore Immondo (Fiend): Benedizione dell'Oscuro (uccidere un nemico conferisce PF temporanei pari a mod. CAR + liv. warlock).\n"
                "• La Fatata (Archfey): Presenza Fatata (come azione puoi affascinare o spaventare tutte le creature in un cubo di 3m attorno a te).\n"
                "• Il Grande Antico (Great Old One): Mente Risvegliata (comunichi telepaticamente con qualsiasi creatura entro 9 metri)."
            )),
            ("Magia del Patto (Pact Magic - Ricarica a Riposo Breve)", (
                "La meccanica magica più iconica e peculiare di D&D:\n"
                "• Pochi slot, ma tutti lanciati sempre al massimo livello possibile!\n"
                "• Tutti i tuoi slot incantesimo si ricaricano completamente con un semplice Riposo Breve (1 ora) anziché richiedere una notte intera!\n"
                "• Conosci 2 trucchetti (tra cui l'imbattibile Deflagrazione Mistica / Eldritch Blast) e 2 incantesimi di 1° livello."
            )),
            ("Suppliche Occulte & Dono del Patto (al 2° e 3° Livello)", (
                "Al 2° livello sblocchi le Suppliche Occulte (es. Agonizing Blast per aggiungere il Carisma a ogni raggio di Eldritch Blast, o vedere nel buio magico); "
                "al 3° livello ricevi il Dono del Patto (Patto della Lama per evocare armi magiche, della Catena con famiglio speciale, o del Tomo per trucchetti universali)."
            ))
        ],
        "playstyle": (
            "Sei un cecchino magico implacabile e a ricarica rapidissima. Non devi aver paura di spendere i tuoi slot incantesimo, perché ti basta "
            "un'ora di sosta per ritornare al 100% delle tue potenzialità! In combattimento, la combinazione di Deflagrazione Mistica e le Suppliche Occulte "
            "ti fornisce il miglior danno a distanza a volontà di tutto il gioco con danni da forza (il tipo di danno meno resistito in assoluto)."
        ),
        "subclasses_preview": [
            "Il Signore Immondo (Magie catastrofiche di fuoco come Palla di Fuoco, scudi di PF temporanei e fortuna diabolica per i dadi)",
            "La Fatata (Inganni, teletrasporto nebbioso in risposta ai danni subiti e difese soprannaturali contro charme)",
            "Il Grande Antico (Sussurri alieni nella mente avversaria, scudi psichici e capacità di trasformare creature in servitori telepatici)",
            "La Lama del Patto / Hexblade (Brandisce il Carisma per attacchi e danni in mischia con armature medie, scudi e la Maledizione dell'Hexblade)"
        ]
    }
}

# Calcolo desc preformattata per retrocompatibilità totale con qualsiasi accesso a CLASSES[c]["desc"]
for _c_name, _c_info in CLASSES.items():
    _feats_text = "\n".join(f"  • {_fn}:\n    {_fd}" for _fn, _fd in _c_info["features_lvl1"])
    _subs_text = "\n".join(f"  • {_sub}" for _sub in _c_info["subclasses_preview"])
    _c_info["desc"] = (
        f"{_c_info['tagline']}\n\n"
        f"🎲 Dado Vita: d{_c_info['hd']} (PF al 1° liv: {_c_info['hd']} + mod. COS)\n"
        f"⭐ Caratteristiche Primarie: {_c_info['primary_stat']}\n"
        f"🛡️ Tiri Salvezza: {_c_info['saving_throws']}\n"
        f"⚔️ Competenze Armature: {_c_info['armor_prof']}\n"
        f"⚔️ Competenze Armi: {_c_info['weapon_prof']}\n"
        f"🎭 Ruolo nel Party: {_c_info['role']}\n\n"
        f"📖 Panoramica & Identità:\n{_c_info['overview']}\n\n"
        f"⚔️ Privilegi di Livello 1:\n{_feats_text}\n\n"
        f"🎯 Stile di Gioco & Tattica:\n{_c_info['playstyle']}\n\n"
        f"🔮 Archetipi Futuri (Sottoclassi):\n{_subs_text}"
    )


def get_class_info(class_name: str) -> Dict[str, Any]:
    """Restituisce le informazioni dettagliate della classe o Guerriero come fallback."""
    return CLASSES.get(class_name, CLASSES["Guerriero"])


def get_class_names() -> List[str]:
    """Restituisce l'elenco di tutte le classi disponibili ordinate."""
    return list(CLASSES.keys())
