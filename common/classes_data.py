# common/classes_data.py
"""
Catalogo completo e autentico delle 12 Classi di D&D 5e (SRD & Manuale del Giocatore):
- Descrizioni narrative approfondite ed evocative
- Ruolo tattico nel gruppo (Party Role) e Grado di Complessità (Guida Neofiti/Esperti)
- Dadi Vita e calcolo PF al 1° livello
- Caratteristiche primarie e Tiri Salvezza con competenza
- Competenze complete (Armature, Armi, Strumenti, Abilità di classe)
- Privilegi chiave di 1° Livello dettagliati con regole 5e
- Guida allo stile di gioco e consigli tattici (combattimento ed esplorazione)
- Consiglio di Creazione Rapida (Quick Build) per assegnazione caratteristiche
- Dotazione & Equipaggiamento iniziale (Starter Kit)
- Dettaglio Magia & Incantesimi iniziali (per classi incantatrici)
- Anteprima degli archetipi e delle sottoclassi future
"""

from typing import Dict, Any, List, Optional


CLASS_CATEGORIES = ["Tutte", "⚔️ Marziali", "🔮 Incantatori", "🛡️ Ibridi", "🗡️ Esperti"]

CATEGORY_MAP = {
    "⚔️ Marziali": "Marziale",
    "🔮 Incantatori": "Incantatore",
    "🛡️ Ibridi": "Ibrido",
    "🗡️ Esperti": "Esperto"
}


CLASSES: Dict[str, Dict[str, Any]] = {
    "Barbaro": {
        "hd": 12,
        "category": "Marziale",
        "complexity": "⭐ Principiante (Azione diretta, salute colossale, gestione intuitiva dell'Ira)",
        "role": "🛡️ Tank Primario & Danni da Mischia (Striker)",
        "tagline": "Un fiero guerriero primordiale alimentato da una furia selvaggia che sfida la morte e abbatte ogni ostacolo.",
        "primary_stat": "Forza (Attacco & Danni), Costituzione (Punti Ferita & CA)",
        "saving_throws": "Forza, Costituzione",
        "armor_prof": "Armature leggere, armature medie, scudi",
        "weapon_prof": "Armi semplici, armi marziali",
        "tools_prof": "Nessuno",
        "skills_info": "2 a scelta tra Atletica, Addestrare Animali, Intimidire, Natura, Percezione, Sopravvivenza",
        "quick_build": "Assegna il tuo 15 a Forza e il 14 a Costituzione. Metti il 13 a Destrezza (per alzare la CA senz'armatura) e lascia l'8 a Intelligenza.",
        "starter_gear": "Ascia Bipenne (1d12), 2 Asce da Lancio, 4 Giavellotti, Zaino da Esploratore, 10 Monete d'Oro (Nessuna armatura necessaria)",
        "starter_spells": None,
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
        "category": "Incantatore",
        "complexity": "⭐⭐⭐ Avanzato (Incantatore versatile a tutto tondo, gestione dadi Ispirazione e magie di controllo)",
        "role": "🎭 Supporto d'Eccellenza, Buffer/Debuffer, Faccia del Party & Factotum",
        "tagline": "Maestro della parola, della canzone e della magia sottile, capace di tessere incantesimi dalle melodie del multiverso.",
        "primary_stat": "Carisma (Incantesimi & Abilità Sociali), Destrezza (CA & Armi Accurate)",
        "saving_throws": "Destrezza, Carisma",
        "armor_prof": "Armature leggere",
        "weapon_prof": "Armi semplici, balestre a mano, spade lunghe, stocchi, spade corte",
        "tools_prof": "3 strumenti musicali a scelta",
        "skills_info": "3 abilità qualsiasi a scelta (massima versatilità di personalizzazione)",
        "quick_build": "Assegna il tuo 15 a Carisma e il 14 a Destrezza. Metti il 13 a Costituzione (per i tiri Concentrazione) e lascia l'8 a Forza.",
        "starter_gear": "Corazza di Cuoio (CA 11+DES), Stocco (1d8 accurata), Pugnale, Liuto (Focus Arcano), Zaino da Intrattenitore, 15 Monete d'Oro",
        "starter_spells": "2 Trucchetti (Beffa Crudele, Luci Danzanti) + 4 Incantesimi di 1° liv (Cura Ferite, Parola Guaritrice, Sonno, Sussurri Dissonanti) | 2 Slot di 1° livello",
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
        "category": "Incantatore",
        "complexity": "⭐⭐ Intermedio (Ottima armatura e sopravvivenza, intera lista incantesimi preparabili ogni giorno)",
        "role": "☀️ Guaritore Supremo, Custode Divino, Buffer Protettivo & Off-Tank",
        "tagline": "Campione consacrato di una divinità o ideale cosmico, brandisce il potere dei piani per sanare i giusti e purificare il male.",
        "primary_stat": "Saggezza (Incantesimi), Costituzione (Concentrazione & PF), Forza (se in mischia)",
        "saving_throws": "Saggezza, Carisma",
        "armor_prof": "Armature leggere, armature medie, scudi (più armature pesanti con alcuni Domini)",
        "weapon_prof": "Armi semplici (più armi marziali con alcuni Domini)",
        "tools_prof": "Nessuno (utilizza un Simbolo Sacro come focus)",
        "skills_info": "2 a scelta tra Storia, Intuizione, Medicina, Persuasione, Religione",
        "quick_build": "Assegna il tuo 15 a Saggezza e il 14 a Costituzione. Metti il 13 a Forza (se usi armature pesanti o combatti in mischia) o a Destrezza.",
        "starter_gear": "Cotta di Maglia (CA 16) o Armatura Media, Mazza da Guerra, Scudo con Emblema (+2 CA), Balestra Leggera con 20 Dardi, Simbolo Sacro, Zaino da Sacerdote, 10 Monete d'Oro",
        "starter_spells": "3 Trucchetti (Fiamma Sacra, Guida, Taumaturgia) + Incantesimi di Dominio sempre pronti + Tutta la lista di 1° liv preparabile (Benedizione, Cura Ferite, Santuario, Scudo della Fede) | 2 Slot di 1° livello",
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
        "category": "Incantatore",
        "complexity": "⭐⭐⭐ Avanzato (Controllo dell'area, intera lista incantesimi della natura e Forma Selvatica con statistiche di bestie)",
        "role": "🌿 Controllo del Campo (Crowd Control), Mutaforma, Guaritore & Tank Adattivo",
        "tagline": "Sacerdote della Vecchia Fede e custode dell'equilibrio naturale, muta la sua forma in fiera e comanda le forze della terra.",
        "primary_stat": "Saggezza (Incantesimi & Natura), Costituzione e Destrezza (Sopravvivenza)",
        "saving_throws": "Intelligenza, Saggezza",
        "armor_prof": "Armature leggere, medie, scudi (i druidi non indossano armature o scudi di metallo)",
        "weapon_prof": "Clave, pugnali, dardi, giavellotti, mazze, bastoni ferrati, scimitarre, falcetti, fionde, lance",
        "tools_prof": "Borsa da erborista",
        "skills_info": "2 a scelta tra Arcana, Addestrare Animali, Intuizione, Medicina, Natura, Percezione, Religione, Sopravvivenza",
        "quick_build": "Assegna il tuo 15 a Saggezza e il 14 a Costituzione. Metti il 13 a Destrezza (per CA e iniziativa) e lascia l'8 a Forza o Carisma.",
        "starter_gear": "Corazza di Cuoio (CA 11+DES), Scudo di Legno (+2 CA non metallico), Scimitarra (1d6), Focus Druidico (Vischio/Tasso), Zaino da Esploratore, 10 Monete d'Oro",
        "starter_spells": "2 Trucchetti (Prod чудо di Fiamma, Druidcraft) + Tutta la lista di 1° liv preparabile (Intralciare, Bacche Benefiche, Cura Ferite, Nube di Nebbia) | 2 Slot di 1° livello",
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
        "category": "Marziale",
        "complexity": "⭐ Principiante (Ideale per neofiti, massima personalizzazione di stili di combattimento e armi)",
        "role": "⚔️ Pilastro Marziale, Maestro d'Armi, Tank Difensivo & Striker Inarrestabile",
        "tagline": "Campione assoluto dell'arte militare e dell'acciaio, forgiato da una disciplina ferrea e versatile in ogni teatro di guerra.",
        "primary_stat": "Forza (Armi Pesanti & Armature a Piastre) o Destrezza (Tiro con l'Arco & Armi Accurate)",
        "saving_throws": "Forza, Costituzione",
        "armor_prof": "Tutte le armature (leggere, medie, pesanti), tutti gli scudi",
        "weapon_prof": "Tutte le armi semplici, tutte le armi marziali",
        "tools_prof": "Nessuno",
        "skills_info": "2 a scelta tra Acrobazia, Addestrare Animali, Atletica, Storia, Intuizione, Intimidire, Percezione, Sopravvivenza",
        "quick_build": "Se usi armi pesanti da mischia: 15 Forza, 14 Costituzione, 13 Destrezza. Se sei arciere o schermidore: 15 Destrezza, 14 Costituzione, 13 Forza.",
        "starter_gear": "Cotta di Maglia (CA 16) o Armatura di Cuoio con Arco Lungo, Spada Lunga e Scudo (+2 CA) o Spadone a Due Mani, Balestra Leggera con 20 Dardi, Zaino da Avventuriero, 10 Monete d'Oro",
        "starter_spells": None,
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
        "category": "Esperto",
        "complexity": "⭐⭐ Intermedio (Precisione chirurgica, posizionamento per Attacco Furtivo e maestria eccezionale nelle abilità)",
        "role": "🗡️ Striker Furtivo a Singolo Bersaglio, Disattivatore di Trappole, Scout & Maestro delle Abilità",
        "tagline": "Maestro delle ombre, dell'inganno e della precisione chirurgica; colpisce nei punti vitali prima di dissolversi nel buio.",
        "primary_stat": "Destrezza (Attacco furtivo, CA, Iniziativa, Scasso), Intelligenza o Carisma",
        "saving_throws": "Destrezza, Intelligenza",
        "armor_prof": "Armature leggere",
        "weapon_prof": "Armi semplici, balestre a mano, spade lunghe, stocchi, spade corte",
        "tools_prof": "Strumenti da scasso (Thieves' Tools)",
        "skills_info": "4 abilità a scelta tra Acrobazia, Atletica, Furtività, Indagare, Inganno, Intimidire, Intrattenere, Intuizione, Percezione, Persuasione, Rapidità di Mano",
        "quick_build": "Assegna il tuo 15 a Destrezza. Metti il 14 a Costituzione e il 13 a Intelligenza (se investigatore o futuro mistificatore arcano) o Carisma (se ingannatore). Lascia l'8 a Forza.",
        "starter_gear": "Corazza di Cuoio (CA 11+DES), Stocco (1d8 accurata), Arco Corto con Faretra e 20 Frecce, Due Pugnali, Strumenti da Scasso, Zaino da Scassinatore, 10 Monete d'Oro",
        "starter_spells": None,
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
        "category": "Incantatore",
        "complexity": "⭐⭐⭐ Avanzato (Il più vasto arsenale d'incantesimi del gioco, gestione del grimorio, trascrizione tomi e lancio di rituali)",
        "role": "🔮 Maestro del Controllo dell'Area, Danni Magici ad Area (Blaster) & Risolutore Arcano",
        "tagline": "Il sommo studioso delle leggi arcane, custode del più vasto e formidabile grimorio di incantesimi del multiverso.",
        "primary_stat": "Intelligenza (Incantesimi & CD), Costituzione e Destrezza (Sopravvivenza & Concentrazione)",
        "saving_throws": "Intelligenza, Saggezza",
        "armor_prof": "Nessuna armatura, nessuno scudo",
        "weapon_prof": "Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",
        "tools_prof": "Nessuno (utilizza Bacchetta, Verga, Cristallo o Grimorio come focus)",
        "skills_info": "2 a scelta tra Arcana, Storia, Intuizione, Indagare, Medicina, Religione",
        "quick_build": "Assegna il tuo 15 a Intelligenza. Metti il 14 a Costituzione (per PF e Concentrazione) e il 13 a Destrezza (per la CA). Lascia l'8 a Forza.",
        "starter_gear": "Libro degli Incantesimi (Grimorio con 6 incantesimi di 1° liv), Pugnale, Focus Arcano (Bacchetta o Cristallo), Zaino da Studioso, Borsa per Componenti, 10 Monete d'Oro",
        "starter_spells": "3 Trucchetti (Raggio di Gelo, Prestidigitazione, Luce) + 6 Incantesimi nel Grimorio (Dardo Incantato, Armatura Magica, Scudo, Sonno, Individuazione del Magico, Allarme) | 2 Slot di 1° liv + Recupero Arcano",
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
        "category": "Marziale",
        "complexity": "⭐⭐⭐ Avanzato (Combattente senz'armi iper-mobile, gestione attenta dei punti Ki e posizionamento tattico)",
        "role": "🥋 Skirmisher Ipermobile, Disruptor da Mischia, Cacciatore di Incantatori & Maestro del Ki",
        "tagline": "Maestro asceta delle arti marziali che incanala l'energia spirituale del Ki per colpire a raffica e muoversi come il vento.",
        "primary_stat": "Destrezza (Attacchi, Danni senz'armi & CA), Saggezza (CA & CD del Ki)",
        "saving_throws": "Forza, Destrezza",
        "armor_prof": "Nessuna armatura, nessuno scudo (il corpo è l'arma e l'armatura perfetta)",
        "weapon_prof": "Armi semplici, spade corte",
        "tools_prof": "Uno strumento da artigiano o uno strumento musicale a scelta",
        "skills_info": "2 a scelta tra Acrobazia, Atletica, Storia, Intuizione, Religione, Furtività",
        "quick_build": "Assegna il tuo 15 a Destrezza e il 14 a Saggezza (entrambe alzano la CA senz'armatura!). Metti il 13 a Costituzione e lascia l'8 a Forza.",
        "starter_gear": "Spada Corta (1d6), 10 Dardi da Lancio, Zaino da Esploratore, 5 Monete d'Oro (Nessuna armatura o scudo necessari)",
        "starter_spells": None,
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
        "category": "Ibrido",
        "complexity": "⭐⭐ Intermedio (Formidabile bastione corazzato con riserva curativa autonoma e devastanti punizioni divine)",
        "role": "🛡️ Tank Corazzato da Prima Linea, Danni da Raffica Esplosivi (Burst Smite) & Faro delle Auree",
        "tagline": "Sacro crociato vincolato da un giuramento incrollabile, fonde possanza marziale, armature pesanti e punizioni celesti.",
        "primary_stat": "Forza (Attacchi da Mischia & Armature Pesanti), Carisma (Incantesimi, Auree & CD)",
        "saving_throws": "Saggezza, Carisma",
        "armor_prof": "Tutte le armature (leggere, medie, pesanti), tutti gli scudi",
        "weapon_prof": "Tutte le armi semplici, tutte le armi marziali",
        "tools_prof": "Nessuno (utilizza un Simbolo Sacro come focus)",
        "skills_info": "2 a scelta tra Atletica, Intuizione, Intimidire, Medicina, Persuasione, Religione",
        "quick_build": "Assegna il tuo 15 a Forza (per cotta di maglia e armi pesanti) e il 14 a Carisma (per incantesimi, auree e CD). Metti il 13 a Costituzione.",
        "starter_gear": "Cotta di Maglia (CA 16 pesante), Spada Lunga (1d8/1d10), Scudo con Emblema Sacro (+2 CA), 5 Giavellotti, Simbolo Sacro, Zaino da Sacerdote, 10 Monete d'Oro",
        "starter_spells": "Magia Divina al 2° livello | Incantesimi di punizione, cura e protezione (Punizione Divina, Benedizione, Scudo della Fede)",
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
        "category": "Ibrido",
        "complexity": "⭐⭐ Intermedio (Tiratore d'élite o schermidore furtivo con abilità di sopravvivenza ed esplorazione)",
        "role": "🏹 Tiratore Infallibile (Sniper o Combattente a Due Armi), Scout d'Avanguardia & Guida Naturale",
        "tagline": "Maestro delle tracce e sentinella dei confini naturali, fonde precisione marziale e comunione con le terre selvagge.",
        "primary_stat": "Destrezza (Arco, Armi Accurate, CA & Iniziativa), Saggezza (Percezione, Sopravvivenza & Magia)",
        "saving_throws": "Forza, Destrezza",
        "armor_prof": "Armature leggere, armature medie, scudi",
        "weapon_prof": "Tutte le armi semplici, tutte le armi marziali",
        "tools_prof": "Nessuno",
        "skills_info": "3 a scelta tra Addestrare Animali, Atletica, Furtività, Indagare, Intuizione, Natura, Percezione, Sopravvivenza",
        "quick_build": "Assegna il tuo 15 a Destrezza e il 14 a Saggezza (per incantesimi e Percezione). Metti il 13 a Costituzione e lascia l'8 a Forza o Carisma.",
        "starter_gear": "Cotta a Scaglie (CA 14+DES max +2), Due Spade Corte, Arco Lungo con Faretra e 20 Frecce, Zaino da Esploratore, 10 Monete d'Oro",
        "starter_spells": "Magia Silvana al 2° livello | Incantesimi di caccia e sopravvivenza (Marchio del Cacciatore, Bacche Benefiche, Salto)",
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
        "category": "Incantatore",
        "complexity": "⭐⭐⭐ Avanzato (Potenza arcana esplosiva, gestione dei punti stregoneria e Metamagia per alterare le regole magiche)",
        "role": "💥 Bombardiere Arcano (Blaster), Nuke a Bersaglio Multiplo, Manipolatore di Magia & Volto",
        "tagline": "Incantatore con la magia che gli scorre direttamente nel sangue, capace di piegare e alterare le leggi dell'arcano con la Metamagia.",
        "primary_stat": "Carisma (Incantesimi, Attacchi & CD), Costituzione (Punti Ferita & Concentrazione)",
        "saving_throws": "Costituzione, Carisma (La competenza nei TS di Costituzione garantisce una tenuta eccezionale della Concentrazione)",
        "armor_prof": "Nessuna armatura, nessuno scudo",
        "weapon_prof": "Pugnali, dardi, fionde, bastoni ferrati, balestre leggere",
        "tools_prof": "Nessuno (utilizza un Cristallo, Verga, Bacchetta o Focus Arcano)",
        "skills_info": "2 a scelta tra Arcana, Inganno, Intimidire, Intuizione, Persuasione, Religione",
        "quick_build": "Assegna il tuo 15 a Carisma e il 14 a Costituzione (la competenza nei TS di Costituzione protegge la Concentrazione!). Metti il 13 a Destrezza per la CA.",
        "starter_gear": "Balestra Leggera con 20 Dardi, Due Pugnali, Focus Arcano (Cristallo), Zaino da Esploratore Sotterraneo, 10 Monete d'Oro",
        "starter_spells": "4 Trucchetti (Dardo di Fuoco, Raggio di Gelo, Prestidigitazione, Illusione Minore) + 2 Incantesimi noti (Mani Brucianti, Armatura Magica o Scudo) | 2 Slot di 1° livello",
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
        "category": "Incantatore",
        "complexity": "⭐⭐⭐ Avanzato (Magia del Patto con slot a livello massimo che si ricaricano a Riposo Breve e personalizzazione con Suppliche Occulte)",
        "role": "🔮 Cecchino Arcano a Volontà (Eldritch Blast), Magia a Ricarica Rapida (Riposo Breve) & Striker Ibrido",
        "tagline": "Cercatore di segreti proibiti legato da un patto occulto a un'entità ultraterrena; esercita slot che si ricaricano a ogni Riposo Breve!",
        "primary_stat": "Carisma (Incantesimi & CD), Destrezza e Costituzione (Sopravvivenza & CA)",
        "saving_throws": "Saggezza, Carisma",
        "armor_prof": "Armature leggere",
        "weapon_prof": "Armi semplici",
        "tools_prof": "Nessuno (utilizza un Focus Arcano)",
        "skills_info": "2 a scelta tra Arcana, Storia, Inganno, Intimidire, Indagare, Natura, Religione",
        "quick_build": "Assegna il tuo 15 a Carisma e il 14 a Costituzione. Metti il 13 a Destrezza (per CA e iniziativa con armature leggere) e lascia l'8 a Forza.",
        "starter_gear": "Corazza di Cuoio (CA 11+DES), Balestra Leggera con 20 Dardi, Due Pugnali, Focus Arcano (Verga), Zaino da Studioso, 10 Monete d'Oro",
        "starter_spells": "2 Trucchetti (Deflagrazione Mistica / Eldritch Blast, Tocco Gelido) + 2 Incantesimi noti (Armatura di Agathys, Anatema / Hex) | 1 Slot al livello massimo (Ricarica a Riposo Breve in 1 ora!)",
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
    _spells_text = f"\n✨ Magia Iniziale:\n  {_c_info['starter_spells']}\n" if _c_info.get("starter_spells") else ""
    _c_info["desc"] = (
        f"{_c_info['tagline']}\n\n"
        f"🎲 Dado Vita: d{_c_info['hd']} (PF al 1° liv: {_c_info['hd']} + mod. COS)\n"
        f"⭐ Caratteristiche Primarie: {_c_info['primary_stat']}\n"
        f"🛡️ Tiri Salvezza: {_c_info['saving_throws']}\n"
        f"⚔️ Competenze Armature: {_c_info['armor_prof']}\n"
        f"⚔️ Competenze Armi: {_c_info['weapon_prof']}\n"
        f"🎭 Ruolo nel Party: {_c_info['role']}\n"
        f"📊 Complessità: {_c_info['complexity']}\n"
        f"💡 Creazione Rapida: {_c_info['quick_build']}\n"
        f"🎒 Dotazione Iniziale: {_c_info['starter_gear']}"
        f"{_spells_text}\n"
        f"📖 Panoramica & Identità:\n{_c_info['overview']}\n\n"
        f"⚔️ Privilegi di Livello 1:\n{_feats_text}\n\n"
        f"🎯 Stile di Gioco & Tattica:\n{_c_info['playstyle']}\n\n"
        f"🔮 Archetipi Futuri (Sottoclassi):\n{_subs_text}"
    )



CLASSES_EN: Dict[str, Dict[str, Any]] = {
    "Barbaro": {
        "complexity": "⭐ Beginner (Direct action, colossal health pool, intuitive Rage management)",
        "role": "🛡️ Primary Tank & Melee Damage (Striker)",
        "tagline": "A fierce primordial warrior fueled by a savage fury that defies death and crushes every obstacle.",
        "primary_stat": "Strength (Attack & Damage), Constitution (Hit Points & AC)",
        "saving_throws": "Strength, Constitution",
        "armor_prof": "Light armor, medium armor, shields",
        "weapon_prof": "Simple weapons, martial weapons",
        "tools_prof": "None",
        "skills_info": "Choose 2 from Animal Handling, Athletics, Intimidation, Nature, Perception, Survival",
        "quick_build": "Assign your 15 to Strength and 14 to Constitution. Put 13 in Dexterity (for unarmored AC) and leave 8 in Intelligence.",
        "starter_gear": "Greataxe (1d12), 2 Handaxes, 4 Javelins, Explorer's Pack, 10 Gold Coins (No armor needed)",
        "starter_spells": None,
        "overview": (
            "From the frozen northern tundras to the depths of primordial jungles, barbarians embody the untamed power "
            "of the earth. In battle, they do not rely on cold academic technique; instead, they awaken an ancestral rage "
            "that vastly expands their physical strength, sharpens their reflexes, and renders their flesh exceptionally "
            "resilient to pain. For a barbarian, combat is the ultimate celebration of vitality and primal instinct."
        ),
        "features_lvl1": [
            ("Rage", (
                "In battle, you can enter a rage as a bonus action (2 times per long rest at 1st level).\n"
                "While raging and wearing no heavy armor:\n"
                "• Advantage on all Strength checks and Strength saving throws.\n"
                "• +2 bonus to melee weapon damage rolls using Strength.\n"
                "• Resistance to bludgeoning, piercing, and slashing damage (halving incoming physical damage!).\n"
                "Rage lasts for 1 minute and ends early if you are knocked unconscious or if your turn ends and you haven't attacked a hostile creature or taken damage."
            )),
            ("Unarmored Defense", (
                "While you are not wearing any armor, your Armor Class equals 10 + your Dexterity modifier + "
                "your Constitution modifier. You can use a shield and still gain this benefit (+2 AC)."
            ))
        ],
        "playstyle": (
            "You are the immovable rock and the vanguard battering ram of the party. With the highest Hit Die in the game "
            "(d12) and damage resistance from Rage, you can leap into the thick of enemy lines, absorb devastating blows "
            "meant for fragile allies, and shatter key targets with greataxe or hammer. Outside battle, your keen senses and "
            "athletic prowess make you ideal for overcoming physical hazards."
        ),
        "subclasses_preview": [
            "Path of the Berserker (Overwhelming frenzy granting bonus action attacks, plus immunity to charm and fear)",
            "Path of the Totem Warrior (Bear Spirit for resistance to all damage types except psychic, Eagle, or Wolf)",
            "Path of the Zealot (Divine fury dealing extra radiant/necrotic damage on every hit, and free resurrection)"
        ]
    },
    "Bardo": {
        "complexity": "⭐⭐⭐ Advanced (Versatile full spellcaster, Bardic Inspiration economy, and battlefield control)",
        "role": "🎭 Supreme Support, Buffer/Debuffer, Party Face & Skill Expert",
        "tagline": "Master of word, song, and subtle magic, weaving spells from the resonant harmonies of the multiverse.",
        "primary_stat": "Charisma (Spellcasting & Social Skills), Dexterity (AC & Finesse Weapons)",
        "saving_throws": "Dexterity, Charisma",
        "armor_prof": "Light armor",
        "weapon_prof": "Simple weapons, hand crossbows, longswords, rapiers, shortswords",
        "tools_prof": "Three musical instruments of your choice",
        "skills_info": "Choose any 3 skills (maximum customization versatility)",
        "quick_build": "Assign 15 to Charisma and 14 to Dexterity. Put 13 in Constitution (for Concentration saves) and leave 8 in Strength.",
        "starter_gear": "Leather Armor (AC 11+DEX), Rapier (1d8 finesse), Dagger, Lute (Arcane Focus), Entertainer's Pack, 15 Gold Coins",
        "starter_spells": "2 Cantrips (Vicious Mockery, Dancing Lights) + 4 1st-level Spells (Cure Wounds, Healing Word, Sleep, Dissonant Whispers) | 2 1st-level Spell Slots",
        "overview": (
            "Whether chanting stirring ballads in royal courts or reciting forbidden lore in harbor taverns, bards understand that "
            "the cosmos sprang from the primordial music of Creation. By learning to pluck and weave these cosmic threads, the bard "
            "casts spells that confound enemy minds, mend ally wounds, and inspire legendary bravery in the face of dragons and fiends."
        ),
        "features_lvl1": [
            ("Spellcasting", (
                "You cast spells drawing upon cosmic harmony using Charisma as your spellcasting ability "
                "(Spell Save DC = 8 + proficiency + CHA mod; Attack = prof + CHA mod)."
            )),
            ("Bardic Inspiration", (
                "As a bonus action, grant an ally within 60 ft an Inspiration Die (1d6). The creature can add it to one ability "
                "check, attack roll, or saving throw within 10 minutes. Uses equal to your Charisma modifier (minimum 1), resetting on a long rest."
            ))
        ],
        "playstyle": (
            "You are the tactical conductor of the party. With healing, crowd-control enchantments, and Bardic Inspiration, "
            "you turn close battles into effortless triumphs. Outside combat, your Charisma and Jack of All Trades allow you "
            "to talk your way into anywhere and overcome any social obstacle."
        ),
        "subclasses_preview": [
            "College of Lore (Bonus skills, Cutting Words to debuff enemy rolls, and early Magical Secrets)",
            "College of Valor (Medium armor, shields, martial weapons, and inspiring combat damage)",
            "College of Glamour (Mantle of Inspiration and mesmerizing fey charm)"
        ]
    },
    "Chierico": {
        "complexity": "⭐⭐ Intermediate (Full prepared spellcaster, divine domain specialization, and armor proficiency)",
        "role": "⛪ Healer, Radiant Damage Striker & Divine Support",
        "tagline": "A devout champion of the divine, channeling holy wrath and miraculous healing power.",
        "primary_stat": "Wisdom (Spells & Perception), Strength or Constitution (Armor & Concentration)",
        "saving_throws": "Wisdom, Charisma",
        "armor_prof": "Light armor, medium armor, shields (plus heavy armor for select domains)",
        "weapon_prof": "Simple weapons (plus martial weapons for select domains)",
        "tools_prof": "None",
        "skills_info": "Choose 2 from History, Insight, Medicine, Persuasion, Religion",
        "quick_build": "Assign 15 to Wisdom and 14 to Constitution (or Strength for heavy armor). Put 13 in Strength and leave 8 in Dexterity.",
        "starter_gear": "Mace, Scale Mail (AC 14+DEX) or Chain Mail, Shield (+2 AC), Holy Symbol, Priest's Pack, 15 Gold Coins",
        "starter_spells": "3 Cantrips (Sacred Flame, Guidance, Thaumaturgy) + Prepared Spells (WIS mod + 1) | 2 1st-level Spell Slots",
        "overview": (
            "Clerics are conduits of divine power. Where ordinary mortals offer prayers, clerics invest their very souls "
            "into serving cosmic deities of Life, Light, War, or the Grave, unleashing miracles that heal lethal injuries or "
            "smite the unholy with radiant dawn."
        ),
        "features_lvl1": [
            ("Divine Domain", (
                "Choose your deity's domain at 1st level (Life, Light, War, Tempest, etc.), gaining bonus domain spells "
                "and signature 1st-level divine powers."
            )),
            ("Spellcasting", (
                "You prepare spells each long rest from the entire Cleric list using Wisdom as your spellcasting ability."
            ))
        ],
        "playstyle": (
            "A versatile pillar of strength in both front line and back line. You can wear durable armor, wield a shield, "
            "protect companions with Bless and Healing Word, and blast fiends with Sacred Flame and Guiding Bolt."
        ),
        "subclasses_preview": [
            "Life Domain (Supreme healing output with Disciple of Life and heavy armor)",
            "Light Domain (Warding Flare defensive reaction and blasting with Fireball)",
            "War Domain (Bonus melee attacks as bonus action and guided strikes)"
        ]
    },
    "Druido": {
        "complexity": "⭐⭐⭐ Advanced (Wild Shape mechanics, prepared nature spellcasting, battlefield shaping)",
        "role": "🌿 Nature Controller, Elemental Blaster, Off-Tank (Wild Shape) & Healer",
        "tagline": "Keeper of the ancient order of nature, mastering beast transformations and raw elemental magic.",
        "primary_stat": "Wisdom (Spellcasting & Insight), Constitution (Concentration & Hit Points)",
        "saving_throws": "Intelligence, Wisdom",
        "armor_prof": "Light armor, medium armor, shields (druids will not wear armor or use shields made of metal)",
        "weapon_prof": "Clubs, daggers, darts, javelins, maces, quarterstaffs, scimitars, sickles, slings, spears",
        "tools_prof": "Herbalism kit",
        "skills_info": "Choose 2 from Arcana, Animal Handling, Insight, Medicine, Nature, Perception, Religion, Survival",
        "quick_build": "Assign 15 to Wisdom and 14 to Constitution. Put 13 in Dexterity and leave 8 in Strength.",
        "starter_gear": "Wooden Shield (+2 AC), Scimitar, Leather Armor, Druidic Focus, Explorer's Pack, Herbalism Kit",
        "starter_spells": "2 Cantrips (Druidcraft, Produce Flame) + Prepared Spells (WIS mod + 1) | 2 1st-level Spell Slots",
        "overview": (
            "Druids revere nature above all, gaining their spells and abilities from the primordial spirits of the wilderness. "
            "Holding counsel in sacred groves, they guard the balance of life, commanding storms, tangling roots, and "
            "transforming their bodies into fierce beasts."
        ),
        "features_lvl1": [
            ("Druidic Language", (
                "You know Druidic, the secret language of druids, leaving hidden messages that only other druids can discern."
            )),
            ("Spellcasting", (
                "You prepare spells each long rest from the entire Druid list using Wisdom as your spellcasting ability."
            ))
        ],
        "playstyle": (
            "You excel at controlling the battlefield with spells like Entangle and Faerie Fire, supporting allies with healing, "
            "and transforming into bears, wolves, or scouts with Wild Shape starting at level 2."
        ),
        "subclasses_preview": [
            "Circle of the Moon (Combat Wild Shape as a bonus action into powerful CR 1 beasts like brown bears)",
            "Circle of the Land (Natural Recovery spell slot restoration and expanded domain spells)",
            "Circle of the Stars (Starry forms boosting healing, ranged radiant attacks, or concentration)"
        ]
    },
    "Guerriero": {
        "complexity": "⭐ Beginner (Unmatched weapon mastery, durable defense, tactical versatility)",
        "role": "⚔️ Primary Martial Striker, Front-Line Guardian & Weapon Master",
        "tagline": "A master of martial combat, skilled with a variety of weapons and armor to conquer any battle.",
        "primary_stat": "Strength or Dexterity (Attacks & Damage), Constitution (Health)",
        "saving_throws": "Strength, Constitution",
        "armor_prof": "All armor, shields",
        "weapon_prof": "Simple weapons, martial weapons",
        "tools_prof": "None",
        "skills_info": "Choose 2 from Acrobatics, Animal Handling, Athletics, History, Insight, Intimidation, Perception, Survival",
        "quick_build": "Assign 15 to Strength (or Dexterity for archers) and 14 to Constitution. Put 13 in Dexterity/Strength and leave 8 in Intelligence.",
        "starter_gear": "Chain Mail (AC 16) or Leather Armor + Longbow, Longsword + Shield or Greatsword (2d6), Light Crossbow, Dungeoneer's Pack",
        "starter_spells": None,
        "overview": (
            "Knights, champions, mercenaries, and veteran guards: fighters master the art of warfare through rigorous training. "
            "Clad in heavy armor and wielding lethal weaponry with deadly discipline, they stand firm against monstrous hordes and dread warlords."
        ),
        "features_lvl1": [
            ("Fighting Style", (
                "Adopt a particular fighting style: Archery (+2 attack with ranged weapons), Defense (+1 AC), "
                "Dueling (+2 damage with 1-handed weapons), or Great Weapon Fighting (reroll 1s and 2s on two-handed damage)."
            )),
            ("Second Wind", (
                "You have a limited well of stamina. On your turn, you can use a bonus action to regain Hit Points "
                "equal to 1d10 + your fighter level once per short or long rest!"
            ))
        ],
        "playstyle": (
            "You are the backbone of any martial group. You dish out consistent high damage, lock down foes, and "
            "shrug off blows with Second Wind and heavy plate."
        ),
        "subclasses_preview": [
            "Champion (Improved Critical on 19-20 and athletic mastery)",
            "Battle Master (Combat maneuvers and superiority dice: Trip Attack, Riposte, Menacing Attack)",
            "Eldritch Knight (Blending blade mastery with Abjuration and Evocation wizard magic)"
        ]
    },
    "Monaco": {
        "complexity": "⭐⭐ Intermediate (Ki point economy, mobility, unarmored martial arts strikes)",
        "role": "🥋 High-Mobility Skirmisher, Stunner & Flurry Striker",
        "tagline": "A master of martial arts, harnessing the primordial power of the body in pursuit of spiritual perfection.",
        "primary_stat": "Dexterity (Martial Arts Attacks & AC), Wisdom (Ki Save DC & Unarmored Defense)",
        "saving_throws": "Strength, Dexterity",
        "armor_prof": "None",
        "weapon_prof": "Simple weapons, shortswords",
        "tools_prof": "One type of artisan's tools or one musical instrument",
        "skills_info": "Choose 2 from Acrobatics, Athletics, History, Insight, Religion, Stealth",
        "quick_build": "Assign 15 to Dexterity and 14 to Wisdom. Put 13 in Constitution and leave 8 in Intelligence.",
        "starter_gear": "Shortsword (1d6), 10 Darts, Dungeoneer's Pack, Explorer's Pack (No armor needed)",
        "starter_spells": None,
        "overview": (
            "Monks harness the inner energy flowing through all living things: Ki. In secluded monasteries, they train "
            "mind and body until their fists strike with the force of clubs and their swiftness allows them to deflect arrows out of midair."
        ),
        "features_lvl1": [
            ("Unarmored Defense", (
                "Beginning at 1st level, while you wear no armor and wield no shield, your AC equals 10 + your Dexterity modifier + your Wisdom modifier."
            )),
            ("Martial Arts", (
                "Mastery of unarmed combat: use Dexterity instead of Strength for monk weapons and unarmed strikes, "
                "roll a d4 for unarmed damage, and make an unarmed strike as a bonus action after attacking!"
            ))
        ],
        "playstyle": (
            "Sprint across the battlefield with unparalleled speed, harass enemy spellcasters, and unleash multiple strikes "
            "per turn before dashing away unhindered."
        ),
        "subclasses_preview": [
            "Way of the Open Hand (Techniques to knock enemies prone, push them 15 ft, or strip reactions)",
            "Way of Shadow (Shadow teleportation and silent ninja stealth magic)",
            "Way of the Kensei (Expanding martial arts to swords, longbows, and signature weapons)"
        ]
    },
    "Paladino": {
        "complexity": "⭐⭐ Intermediate (Martial combat, divine spellcasting, smites, and sacred auras)",
        "role": "🛡️ Front-Line Tank, Divine Burst Striker & Aura Buffer",
        "tagline": "A holy warrior bound by a sacred oath, channeling righteous power to vanquish evil and heal the fallen.",
        "primary_stat": "Strength (Melee Attacks & Armor), Charisma (Spellcasting & Auras)",
        "saving_throws": "Wisdom, Charisma",
        "armor_prof": "All armor, shields",
        "weapon_prof": "Simple weapons, martial weapons",
        "tools_prof": "None",
        "skills_info": "Choose 2 from Athletics, Insight, Intimidation, Medicine, Persuasion, Religion",
        "quick_build": "Assign 15 to Strength and 14 to Charisma. Put 13 in Constitution and leave 8 in Dexterity.",
        "starter_gear": "Chain Mail (AC 16), Longsword + Shield (+2 AC) or Greatsword, 5 Javelins, Priest's Pack, Holy Symbol",
        "starter_spells": None,
        "overview": (
            "Paladins swear sacred oaths that resonate through the cosmos. Whether devoted to Justice, Devotion, Vengeance, "
            "or the Ancients, a paladin's conviction is so unyielding that it manifests as radiant divine magic, smiting fiends and curing diseases."
        ),
        "features_lvl1": [
            ("Divine Sense", (
                "As an action, detect the presence of celestials, fiends, and undead within 60 feet (uses equal to 1 + CHA mod per long rest)."
            )),
            ("Lay on Hands", (
                "You have a pool of healing power equal to your paladin level × 5. As an action, touch a creature to restore "
                "Hit Points or spend 5 points to cure a disease or neutralize a poison."
            ))
        ],
        "playstyle": (
            "You lead from the front, absorbing enemy strikes, curing ailments, and delivering massive burst damage with "
            "Divine Smite when you score critical hits."
        ),
        "subclasses_preview": [
            "Oath of Devotion (Sacred Weapon adding Charisma to attack rolls and Turn the Unholy)",
            "Oath of Vengeance (Vow of Enmity granting advantage on all attacks against a chosen foe and Hunter's Mark)",
            "Oath of the Ancients (Aura of Warding granting resistance to all spell damage)"
        ]
    },
    "Ranger": {
        "complexity": "⭐⭐ Intermediate (Survival tracking, martial archery/melee, nature spells)",
        "role": "🏹 Ranged Scout, Survivalist & Skirmisher",
        "tagline": "A warrior of the wild frontier, tracking prey with supernatural precision and lethal archery.",
        "primary_stat": "Dexterity (Ranged Attacks & AC), Wisdom (Spells & Survival)",
        "saving_throws": "Strength, Dexterity",
        "armor_prof": "Light armor, medium armor, shields",
        "weapon_prof": "Simple weapons, martial weapons",
        "tools_prof": "None",
        "skills_info": "Choose 3 from Animal Handling, Athletics, Insight, Investigation, Nature, Perception, Stealth, Survival",
        "quick_build": "Assign 15 to Dexterity and 14 to Wisdom. Put 13 in Constitution and leave 8 in Intelligence.",
        "starter_gear": "Scale Mail or Leather Armor, 2 Shortswords, Longbow + 20 Arrows, Dungeoneer's Pack",
        "starter_spells": None,
        "overview": (
            "Rangers stand guard on the fringes of civilization. Tracking monstrosities through trackless wilds, they master "
            "the terrain, turn the environment against their foes, and weave nature magic to strike unseen."
        ),
        "features_lvl1": [
            ("Favored Enemy", (
                "Advantage on Wisdom (Survival) checks to track your chosen foes (e.g. Aberrations, Undead, Beasts) "
                "and Intelligence checks to recall lore about them, plus their language."
            )),
            ("Natural Explorer", (
                "You are adept at traveling through chosen terrain (Forest, Mountain, Swamp, etc.): your group's travel is not "
                "slowed by difficult terrain, you cannot become lost except by magical means, and you remain alert to danger while foraging."
            ))
        ],
        "playstyle": (
            "You excel at reconnaissance, ambush tactics, tracking, and rapid ranged attacks with Hunter's Mark."
        ),
        "subclasses_preview": [
            "Hunter (Colossus Slayer dealing extra 1d8 damage on wounded targets, Horde Breaker)",
            "Gloom Stalker (Dread Ambusher bonus attack, darkvision mastery, invisibility to creatures relying on darkvision)",
            "Beast Master (Bonding with a loyal animal companion to fight alongside you)"
        ]
    },
    "Ladro": {
        "complexity": "⭐ Beginner (Sneak Attack tactics, Cunning Action mobility, unmatched skill expertise)",
        "role": "🗡️ Critical Burst Striker, Infiltrator, Trap Specialist & Skill Master",
        "tagline": "A master of stealth, precision strikes, and clever tricks, exploiting weaknesses to turn the tide.",
        "primary_stat": "Dexterity (Finesse Attacks, Stealth & AC), Intelligence or Charisma (Skills)",
        "saving_throws": "Dexterity, Intelligence",
        "armor_prof": "Light armor",
        "weapon_prof": "Simple weapons, hand crossbows, longswords, rapiers, shortswords",
        "tools_prof": "Thieves' tools",
        "skills_info": "Choose 4 skills from Acrobatics, Athletics, Deception, Insight, Intimidation, Investigation, Perception, Performance, Persuasion, Sleight of Hand, Stealth",
        "quick_build": "Assign 15 to Dexterity and 14 to Constitution (or Charisma/Intelligence). Put 13 in Wisdom and leave 8 in Strength.",
        "starter_gear": "Rapier (1d8 finesse) or Shortsword, Shortbow + 20 Arrows, Leather Armor (AC 11+DEX), Thieves' Tools, Burglar's Pack",
        "starter_spells": None,
        "overview": (
            "Rogues rely on cunning, stealth, and exploiting every opening. In dark alleys, forgotten tombs, or glittering "
            "ballrooms, they solve puzzles, disarm deadly traps, pick ornate locks, and eliminate priority threats with a single lethal thrust."
        ),
        "features_lvl1": [
            ("Expertise", (
                "Choose two of your skill proficiencies (or one skill and thieves' tools): your proficiency bonus is DOUBLED "
                "for any ability check that uses either choice! (e.g. +7 Stealth at level 1)."
            )),
            ("Sneak Attack", (
                "Once per turn, you can deal an extra 1d6 damage to one creature you hit with an attack using a finesse or ranged "
                "weapon, provided you have advantage on the roll OR an ally is within 5 feet of the target and you don't have disadvantage. "
                "Damage scales every 2 levels (+1d6)."
            )),
            ("Thieves' Cant", (
                "A secret dialect of jargon, slang, and hidden code symbols that allows you to convey hidden messages to other rogues."
            ))
        ],
        "playstyle": (
            "Position yourself carefully to trigger Sneak Attack every turn, disarm traps before they wipe the party, "
            "and use Cunning Action at level 2 to Dash, Disengage, or Hide as a bonus action."
        ),
        "subclasses_preview": [
            "Thief (Fast Hands bonus action lockpicking, Second-Story Work climbing agility)",
            "Assassin (Assassinate advantage on foes that haven't acted, automatic critical hits on surprised targets)",
            "Arcane Trickster (Mage Hand Legerdemain and enchantment/illusion wizard spellcasting)"
        ]
    },
    "Stregone": {
        "complexity": "⭐⭐ Intermediate (Flexible spontaneous spellcaster, Metamagic sorcery points, spell slots)",
        "role": "🔥 Arcane Blaster, Flexible Twin/Quick Spellcaster & Sorcerous Striker",
        "tagline": "A spellcaster bearing innate magic bestowed by an exotic bloodline, otherworldly blessing, or cosmic anomaly.",
        "primary_stat": "Charisma (Spellcasting & Social Influence), Constitution (Concentration & Health)",
        "saving_throws": "Constitution, Charisma",
        "armor_prof": "None",
        "weapon_prof": "Daggers, darts, slings, quarterstaffs, light crossbows",
        "tools_prof": "None",
        "skills_info": "Choose 2 from Arcana, Deception, Insight, Intimidation, Persuasion, Religion",
        "quick_build": "Assign 15 to Charisma and 14 to Constitution. Put 13 in Dexterity (for AC) and leave 8 in Strength.",
        "starter_gear": "Light Crossbow + 20 Bolts, Arcane Focus (Crystal/Orb), Dungeoneer's Pack or Explorer's Pack, 2 Daggers",
        "starter_spells": "4 Cantrips (Fire Bolt, Mage Hand, Ray of Frost, Shocking Grasp) + 2 1st-level Spells (Shield, Magic Missile) | 2 1st-level Spell Slots",
        "overview": (
            "Sorcerers carry magic in their very veins. Unlike wizards who spend decades studying ancient tomes, sorcerers "
            "manifest spells through raw will and supernatural heritage—born of dragon blood, wild planar storms, or celestial touched souls."
        ),
        "features_lvl1": [
            ("Sorcerous Origin", (
                "Choose your origin at 1st level (Draconic Bloodline, Wild Magic, etc.), gaining immediate supernatural resilience or wild surges."
            )),
            ("Spellcasting", (
                "You cast spells from innate power using Charisma as your spellcasting ability "
                "(Spell Save DC = 8 + prof + CHA mod; Attack = prof + CHA mod)."
            ))
        ],
        "playstyle": (
            "You unleash devastating area-of-effect and single-target spells, using Metamagic at level 3 (Quickened Spell, "
            "Twinned Spell) to break the normal rules of magic."
        ),
        "subclasses_preview": [
            "Draconic Bloodline (Dragon Ancestor resilience: +1 HP per level and permanent 13 + DEX unarmored AC)",
            "Wild Magic (Tides of Chaos advantage on demand, triggering unpredictable Wild Magic Surges)",
            "Divine Soul (Access to the entire Cleric spell list alongside Sorcerer spells, and Favored by the Gods)"
        ]
    },
    "Warlock": {
        "complexity": "⭐⭐ Intermediate (Pact Magic short rest spell slots, Invocations, customization)",
        "role": "👁️ Eldritch Striker, Eldritch Blast Specialist & Dark Controller",
        "tagline": "A wielder of magic derived from a bargain with an extraordinary otherworldly patron.",
        "primary_stat": "Charisma (Spells & Eldritch Invocations), Constitution or Dexterity (Survival)",
        "saving_throws": "Wisdom, Charisma",
        "armor_prof": "Light armor",
        "weapon_prof": "Simple weapons",
        "tools_prof": "None",
        "skills_info": "Choose 2 from Arcana, Deception, History, Intimidation, Investigation, Nature, Religion",
        "quick_build": "Assign 15 to Charisma and 14 to Constitution. Put 13 in Dexterity and leave 8 in Strength.",
        "starter_gear": "Leather Armor (AC 11+DEX), Light Crossbow, Arcane Focus, Scholar's Pack, Dagger",
        "starter_spells": "2 Cantrips (Eldritch Blast, Minor Illusion) + 2 1st-level Spells (Hex, Armor of Agathys) | 1 Pact Magic Slot (recharges on SHORT rest!)",
        "overview": (
            "Warlocks seek knowledge and power beyond mortal reach, forging pacts with ancient entities: archfey, "
            "fiends from the lower planes, or eldritch horrors from the Great Far Realm. In exchange for service, they receive "
            "dark secrets and potent magical boons."
        ),
        "features_lvl1": [
            ("Otherworldly Patron", (
                "Choose your patron at 1st level (The Fiend, The Great Old One, The Archfey, The Hexblade), "
                "granting unique patron spells and special features."
            )),
            ("Pact Magic", (
                "Unique magic: all your spell slots are always cast at the highest spell level you can cast, and they recharge "
                "on a SHORT rest as well as a long rest!"
            ))
        ],
        "playstyle": (
            "You rain down consistent long-range force damage with Eldritch Blast (enhanced by Agonizing Blast and Hex) "
            "and unleash high-impact patron spells every short rest."
        ),
        "subclasses_preview": [
            "The Fiend (Dark One's Blessing granting temporary HP whenever you reduce a hostile creature to 0 HP)",
            "The Great Old One (Awakened Mind telepathy and psychic shielding)",
            "The Hexblade (Wield Charisma for melee attack/damage rolls, medium armor, and Hexblade's Curse)"
        ]
    },
    "Mago": {
        "complexity": "⭐⭐⭐ Advanced (Massive spellbook, ritual casting without preparing, tactical flexibility)",
        "role": "📚 Ultimate Utility, Battlefield Controller, Ritualist & High-Tier Blaster",
        "tagline": "A scholarly magic-user capable of manipulating the fabric of reality through arcane study.",
        "primary_stat": "Intelligence (Spellcasting & Arcana), Constitution or Dexterity (Concentration & Defense)",
        "saving_throws": "Intelligence, Wisdom",
        "armor_prof": "None",
        "weapon_prof": "Daggers, darts, slings, quarterstaffs, light crossbows",
        "tools_prof": "None",
        "skills_info": "Choose 2 from Arcana, History, Insight, Investigation, Medicine, Religion",
        "quick_build": "Assign 15 to Intelligence and 14 to Constitution. Put 13 in Dexterity (for AC) and leave 8 in Strength.",
        "starter_gear": "Quarterstaff or Dagger, Arcane Focus (Wand/Orb), Scholar's Pack, Spellbook (with 6 1st-level spells)",
        "starter_spells": "3 Cantrips (Fire Bolt, Mage Hand, Prestidigitation) + 6 1st-level Spells in Spellbook (e.g. Shield, Mage Armor, Magic Missile, Sleep, Detect Magic, Find Familiar) | 2 1st-level Slots",
        "overview": (
            "Wizards are the supreme scholars of the arcane. Through lifetimes of intense study, meticulous calculation, "
            "and mastering ancient grimoires, they decipher the laws of reality. Where other casters are limited by innate "
            "blood or divine favor, a wizard can learn and transcribe virtually any arcane spell in existence."
        ),
        "features_lvl1": [
            ("Spellcasting & Spellbook", (
                "You possess a Spellbook containing 6 1st-level spells. You prepare INT mod + level spells each day and "
                "can transcribe new spells found on scrolls for 50 gp per level."
            )),
            ("Ritual Casting", (
                "You can cast any wizard spell in your spellbook as a ritual if it has the ritual tag, WITHOUT needing to prepare it!"
            )),
            ("Arcane Recovery", (
                "Once per day during a short rest, you can regain expended spell slots with a combined level equal to "
                "up to half your wizard level (rounded up)."
            ))
        ],
        "playstyle": (
            "You have an answer for every tactical situation: crowd control with Sleep or Web, defensive survival with "
            "Shield and Absorb Elements, and world-shaping utility with ritual spells."
        ),
        "subclasses_preview": [
            "School of Evocation (Sculpt Spells protects allies from your Fireballs)",
            "School of Abjuration (Arcane Ward absorbs damage directed at you or allies)",
            "School of Divination (Portent rolls two d20s every morning to replace any roll throughout the day)"
        ]
    }
}


def get_class_info(class_name: str, lang: Optional[str] = None) -> Dict[str, Any]:
    """Restituisce le informazioni dettagliate della classe o Guerriero come fallback, localizzate in lingua."""
    if lang is None:
        try:
            from common.i18n import get_current_language
            lang = get_current_language()
        except Exception:
            lang = "it"
            
    from common.i18n import translate_class
    it_name = translate_class(class_name, "it")
    base_info = dict(CLASSES.get(it_name, CLASSES.get(class_name, CLASSES["Guerriero"])))
    
    if lang == "en":
        en_info = CLASSES_EN.get(it_name, CLASSES_EN.get(class_name))
        if en_info:
            base_info.update(en_info)
    return base_info



def get_class_names() -> List[str]:
    """Restituisce l'elenco di tutte le classi disponibili ordinate."""
    return list(CLASSES.keys())


def get_classes_by_category(category_filter: str) -> List[str]:
    """Restituisce l'elenco delle classi filtrate per categoria o tutte."""
    if not category_filter or category_filter == "Tutte":
        return list(CLASSES.keys())
    target_cat = CATEGORY_MAP.get(category_filter, category_filter)
    return [name for name, info in CLASSES.items() if info.get("category") == target_cat]
