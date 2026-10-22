# common/backgrounds_data.py
"""
Dati e logica narrativa per i Background di D&D 5e:
- Catalogo completo dei Background ufficiali SRD/5e (Accolito, Nobile, Soldato, Criminale, ecc.)
- Competenze abilità automatiche (2 per background)
- Privilegi di Background (Features)
- Tabelle ruolistiche: Tratti Caratteriali, Ideali, Legami, Difetti
- Ganci d'avventura & Obiettivi personali (Personal Quests)
- Segreti del personaggio (per colpi di scena con il Master)
- Legami con il gruppo (Party Ties)
- Cimeli personali (Trinkets)
- Generatore narrativo "Componi la mia Storia"
"""

import random
from typing import Dict, List, Any, Optional

ALIGNMENT_NONE = "Nessuno (Non specificato)"

ALIGNMENTS: Dict[str, str] = {
    ALIGNMENT_NONE: "Nessun allineamento predefinito: puoi scegliere liberamente la condotta del tuo personaggio durante la campagna senza etichette morali imposte.",
    "LB (Legale Buono)": "Un personaggio Legale Buono si comporta come la società si aspetta, in modo giusto e difendendo i deboli (es. i Paladini).",
    "NB (Neutrale Buono)": "Fanno del loro meglio per aiutare gli altri assecondando le loro necessità. Re e governanti sono importanti, ma l'aiuto diretto è primario.",
    "CB (Caotico Buono)": "Agiscono secondo coscienza senza preoccuparsi delle regole, aiutando chi ne ha bisogno seguendo la propria morale.",
    "LN (Legale Neutrale)": "Seguono la legge, le tradizioni o un codice personale senza farsi guidare da compassione o malvagità. L'ordine è assoluto.",
    "N (Neutrale Puro)": "Preferiscono tenersi a distanza dai problemi morali, evitando di schierarsi e agendo in modo naturale.",
    "CN (Caotico Neutrale)": "Seguono i loro capricci, valutando la propria libertà personale al di sopra di tutto. Sfuggono alle imposizioni.",
    "LM (Legale Malvagio)": "Sfruttano sistematicamente il sistema, le regole o una gerarchia per ottenere ciò che vogliono senza pietà.",
    "NM (Neutrale Malvagio)": "Fanno tutto ciò che serve per ottenere i loro scopi, senza alcun rimorso. Pensano solo ed esclusivamente a sé stessi.",
    "CM (Caotico Malvagio)": "Agiscono mossi da brama, odio e sete di distruzione. Brutali e imprevedibili."
}

BACKGROUNDS: Dict[str, Dict[str, Any]] = {
    "Accolito": {
        "name_en": "Acolyte",
        "desc": "Hai trascorso la vita al servizio di un tempio, venerando una divinità o una filosofia divina. Sei il tramite tra il reame sacro e il mondo terreno.",
        "skills": ["Intuizione", "Religione"],
        "tools": "Due lingue a scelta",
        "gold": 15,
        "equipment": "Simbolo sacro, libro di preghiere, 5 bastoncini d'incenso, paramenti cerimoniali, abiti comuni e 15 mo.",
        "feature_name": "Rifugio del Fedele",
        "feature_desc": "Tu e i tuoi compagni potete ricevere cure e ospitalità gratuita presso i templi e santuari della tua fede. I sacerdoti condivideranno supporto nei limiti delle loro possibilità.",
        "traits": [
            "Vedo la presenza e i presagi della mia divinità in ogni evento naturale.",
            "Sono tollerante verso le altre fedi e rispetto chi cerca una guida spirituale.",
            "Parlo con voce calma e solenne, trasmettendo serenità anche nel pericolo.",
            "Sono abituato a mediare conflitti con pazienza, citando sacre scritture."
        ],
        "ideals": [
            "Fede: Confido che la mia divinità guiderà le mie azioni verso il bene. (Buono)",
            "Tradizione: Gli antichi riti e le usanze preservano l'ordine e la civiltà. (Legale)",
            "Cambiamento: Dobbiamo aiutare il mondo a rinnovarsi ed evolvere. (Caotico)",
            "Potere: La devozione e la conoscenza divina sono la chiave per dominare. (Malvagio)"
        ],
        "bonds": [
            "Morirei pur di recuperare una sacra reliquia trafugata dal mio tempio.",
            "Ho un debito inestinguibile verso il sacerdote che mi ha accolto da orfano.",
            "Tutto ciò che faccio è per proteggere e onorare il mio tempio d'origine.",
            "Cerco di preservare un testo sacro che racchiude una profezia dimenticata."
        ],
        "flaws": [
            "Confido ciecamente nella gerarchia del mio tempio senza pormi domande.",
            "Giudico severamente chiunque mostri scarso rispetto verso il divino.",
            "Sono inflessibile nei miei principi morali anche quando la situazione richiederebbe compromessi.",
            "A volte dubito segretamente della mia fede quando assisto a grandi ingiustizie."
        ]
    },
    "Criminale / Spia": {
        "name_en": "Criminal / Spy",
        "desc": "Hai vissuto ai margini della legge, guadagnandoti da vivere con furti, informazioni segrete o contrabbando nelle ombre della città.",
        "skills": ["Furtività", "Inganno"],
        "tools": "Strumenti da scasso, un set da gioco",
        "gold": 15,
        "equipment": "Piede di porco, abiti scuri con cappuccio comuni, e 15 mo.",
        "feature_name": "Contatto Criminale",
        "feature_desc": "Possiedi un contatto fidato che funge da tramite con la rete della malavita locale per scambiare messaggi segreti, ricettare merci e ottenere informazioni riservate.",
        "traits": [
            "Ho sempre un piano di fuga pronto e controllo ogni porta e finestra.",
            "Non perdo mai la calma, anche quando una lama è a un passo dalla mia gola.",
            "Preferisco fare un accordo vantaggioso piuttosto che estrarre la lama.",
            "Diffido istintivamente di chiunque sorrida troppo o sembri onesto."
        ],
        "ideals": [
            "Onore tra ladri: Non rubo mai ai miei compagni né tradisco un patto d'ombra. (Legale)",
            "Libertà: Le catene e le leggi dei tiranni sono fatte per essere spezzate. (Caotico)",
            "Carità: Rubo ai nobili corrotti per aiutare chi muore di fame nei bassifondi. (Buono)",
            "Opportunismo: Faccio solo ed esclusivamente ciò che conviene a me. (Malvagio)"
        ],
        "bonds": [
            "Devo una grossa somma a un boss criminale che ha ancora la mia vita in pugno.",
            "I proventi delle mie rapine servono a mantenere segretamente la mia famiglia.",
            "Qualcuno a cui tenevo è stato incastrato per un mio colpo: devo scagionarlo.",
            "Custodisco un segreto che potrebbe far crollare l'intera nobiltà cittadina."
        ],
        "flaws": [
            "Quando vedo qualcosa di prezioso e incustodito, fatico a resistere all'impulso di prenderlo.",
            "Scappo al primo segno di trappola se la situazione diventa disperata.",
            "Non riesco a fidarmi completamente di nessuno, nemmeno dei miei amici più stretti.",
            "Sono vendicativo e non dimentico mai un torto subito."
        ]
    },
    "Eroe Popolare": {
        "name_en": "Folk Hero",
        "desc": "Vieni dal popolo semplice e hai compiuto un gesto di straordinario coraggio che ti ha reso una leggenda tra i contadini e la gente umile.",
        "skills": ["Addestrare Animali", "Sopravvivenza"],
        "tools": "Strumenti da artigiano (un tipo), veicoli terrestri",
        "gold": 10,
        "equipment": "Un set di strumenti da artigiano, una pala, un vaso di ferro, abiti comuni e 10 mo.",
        "feature_name": "Ospitalità Rustica",
        "feature_desc": "I popolani e i villici ti riconoscono come uno di loro e faranno di tutto per offrirti riparo, cibo e nasconderti da nobili tiranni o guardie corrotte.",
        "traits": [
            "Giudico le persone dalle loro azioni concrete, non dal loro rango sociale.",
            "Se c'è un'ingiustizia, non riesco a voltarmi dall'altra parte.",
            "Uso proverbi rustici e aneddoti campagnoli per spiegare grandi verità.",
            "Lavoro sodo e non mi lamento mai del fango o della fatica."
        ],
        "ideals": [
            "Rispetto: Tutti meritano di essere trattati con dignità, dal contadino al re. (Buono)",
            "Giustizia: I tiranni che opprimono i deboli devono essere abbattuti. (Caotico)",
            "Destino: Credo che le mie origini umili siano solo l'inizio di qualcosa di grande. (Neutrale)",
            "Protezione: La mia forza serve a fare da scudo a chi non può difendersi. (Legale)"
        ],
        "bonds": [
            "Proteggerò la mia terra natia e la mia gente a qualunque costo.",
            "Combatto per fare colpo su un amore d'infanzia rimasto al villaggio.",
            "Porto con me la medaglia o lo strumento di mio padre con orgoglio.",
            "Un nobile arrogante ha distrutto la mia casa: un giorno lo costringerò a inginocchiarsi."
        ],
        "flaws": [
            "I nobili e le guardie boriosi mi fanno perdere subito la pazienza.",
            "Confido troppo nell'onestà della gente comune e posso essere ingenuo.",
            "Sento il peso di dover essere sempre l'eroe perfetto e temo di deludere gli altri.",
            "Bevo troppo quando sono in taverna per dimenticare gli orrori visti."
        ]
    },
    "Nobile": {
        "name_en": "Noble",
        "desc": "Sei cresciuto nell'opulenza, tra privilegi, etichetta di corte e titoli nobiliari. Sei abituato al rispetto e alla responsabilità del comando.",
        "skills": ["Storia", "Persuasione"],
        "tools": "Un set da gioco, una lingua a scelta",
        "gold": 25,
        "equipment": "Abiti eleganti, anello con sigillo nobiliare, pergamena con albero genealogico e borsa con 25 mo.",
        "feature_name": "Privilegio di Posizione",
        "feature_desc": "La gente ti riserva rispetto e ti riconosce come persona di alto lignaggio. Hai diritto di udienza presso nobili e governanti e vieni accolto nell'alta società.",
        "traits": [
            "Non mi scompongo mai in pubblico e mantengo sempre una postura regale.",
            "Tratto chiunque con squisita cortesia formale, indipendentemente dal ceto.",
            "Il mio nome e l'onore della mia famiglia vengono prima di qualunque ricchezza.",
            "Sono abituato al meglio che il mondo può offrire e apprezzo l'eccellenza."
        ],
        "ideals": [
            "Noblesse Oblige: È dovere di chi ha potere proteggere e guidare chi non ne ha. (Buono)",
            "Responsabilità: I miei privilegi comportano doveri ferrei verso il reame. (Legale)",
            "Indipendenza: Voglio dimostrare il mio valore senza l'aiuto del mio titolo. (Caotico)",
            "Supremazia: Il sangue nobile mi conferisce il diritto naturale di comandare. (Malvagio)"
        ],
        "bonds": [
            "Devo restaurare l'onore e il prestigio del mio casato caduto in disgrazia.",
            "Darei la mia vita per proteggere il mio sovrano o la mia patria.",
            "Custodisco un'antica lama cerimoniale ereditata dai miei avi.",
            "Fuggo da un matrimonio combinato che avrebbe distrutto la mia felicità."
        ],
        "flaws": [
            "Fatico a comprendere i problemi pratici e le difficoltà della gente comune.",
            "Tendo a dare ordini e mi infastidisco se qualcuno mette in dubbio la mia autorità.",
            "Custodisco un vergognoso scandalo familiare che non deve mai trapelare.",
            "L'idea di dormire sul terreno o sporcarmi le vesti mi ripugna profondamente."
        ]
    },
    "Saggio": {
        "name_en": "Sage",
        "desc": "Hai dedicato anni allo studio accademico di tomi antichi, pergamene, mappe astronomiche e segreti arcani. La conoscenza è la tua guida suprema.",
        "skills": ["Arcano", "Storia"],
        "tools": "Due lingue a scelta",
        "gold": 10,
        "equipment": "Boccetta d'inchiostro nero, penna d'oca, coltellino, lettera da un collega defunto con una domanda irrisolta, abiti comuni e 10 mo.",
        "feature_name": "Ricercatore",
        "feature_desc": "Quando tenti di apprendere o ricordare un'informazione storica o arcana, se non la conosci sai esattamente da chi o in quale biblioteca o archivio trovarla.",
        "traits": [
            "Uso parole ricercate e faccio riferimenti a tomi storici anche per cose banali.",
            "Sono perennemente assorto nei miei pensieri e distratto dal mondo materiale.",
            "Non sopporto le risposte vaghe o l'ignoranza ostentata con orgoglio.",
            "Prendo appunti compulsivi su ogni mostro, pianta o rovina che incontro."
        ],
        "ideals": [
            "Conoscenza: L'apprendimento e la verità sono il fine ultimo dell'esistenza. (Neutrale)",
            "Progresso: La scienza e la magia devono essere usate per migliorare la vita di tutti. (Buono)",
            "Logica: Le emozioni offuscano il giudizio razionale; solo i fatti contano. (Legale)",
            "Potere: Chi possiede i segreti dell'universo possiede il dominio sul mondo. (Malvagio)"
        ],
        "bonds": [
            "Lavoro da una vita per decifrare un antico manoscritto intriso di mistero.",
            "I miei colleghi d'accademia mi hanno deriso: proverò che la mia teoria è corretta.",
            "Tutto ciò che scopro verrà donato alla grande biblioteca della mia città.",
            "Proteggerò un allievo o un giovane compagno per tramandare il mio sapere."
        ],
        "flaws": [
            "Mi concentro talmente sui dettagli teorici da ignorare i pericoli letali immediati.",
            "Per accedere a un tomo antico proibito rischierei la vita mia e dei miei compagni.",
            "Parlo senza filtri e tendo a far sentire gli altri stupidi senza accorgermene.",
            "Fatico a fidarmi delle intuizioni emotive che non posso verificare razionalmente."
        ]
    },
    "Soldato": {
        "name_en": "Soldier",
        "desc": "La guerra è stata la tua scuola. Hai servito in un esercito, in una guardia cittadina o in una compagnia mercenaria, imparando la dura arte della disciplina marziale.",
        "skills": ["Atletica", "Intimidire"],
        "tools": "Un set da gioco, veicoli terrestri",
        "gold": 10,
        "equipment": "Emblema del tuo grado militare, trofeo preso a un nemico caduto, un set di dadi d'osso, abiti comuni e 10 mo.",
        "feature_name": "Grado Militare",
        "feature_desc": "Mantieni l'autorità del tuo grado. Soldati e guardie della tua fazione riconoscono il tuo comando e puoi accedere a fortilizi e accampamenti militari.",
        "traits": [
            "Valuto le persone in base alla loro disciplina e lealtà sotto pressione.",
            "Mantengo sempre le mie armi e armature in condizioni impeccabili.",
            "Ho storie di guerra ed espressioni da trincea per quasi ogni occasione.",
            "Dormo con un occhio aperto e mi sveglio al minimo rumore di metallo."
        ],
        "ideals": [
            "Cameratismo: I miei compagni d'armi sono la mia vera famiglia; non ne lascerò indietro nessuno. (Buono)",
            "Disciplina: L'ordine, la catena di comando e il dovere tengono in piedi il mondo. (Legale)",
            "Libertà: Ho visto troppi soldati morire per capricci di tiranni; ora combatto solo per me. (Caotico)",
            "Forza: In questo mondo vince solo chi ha la spada più affilata e la determinazione più dura. (Malvagio)"
        ],
        "bonds": [
            "Combatto per onorare il ricordo del mio vecchio reggimento spazzato via.",
            "Darei la vita per proteggere il comandante che mi ha salvato in battaglia.",
            "Mando parte del mio bottino alle famiglie dei soldati caduti sotto il mio comando.",
            "Cerco il nemico giurato che ha commesso crimini di guerra contro la mia gente."
        ],
        "flaws": [
            "I ricordi traumatici della guerra mi perseguitano quando sento urla o fiamme.",
            "Seguo gli ordini troppo alla lettera anche quando le circostanze sono cambiate.",
            "Disprezzo chiunque non abbia mai imbracciato un'arma o provato il fango del fronte.",
            "Non riesco a resistere a una sfida al braccio di ferro o alla birra in taverna."
        ]
    },
    "Marinaio": {
        "name_en": "Sailor",
        "desc": "Il mare aperto, il vento tra le vele e le stelle sono stati la tua casa per anni. Conosci l'odore della tempesta e i segreti delle coste lontane.",
        "skills": ["Atletica", "Percezione"],
        "tools": "Strumenti da navigatore, veicoli marini",
        "gold": 10,
        "equipment": "Caviglia da marinaio (randello), 15 metri di corda di canapa, portafortuna marino, abiti comuni e 10 mo.",
        "feature_name": "Passaggio Navale",
        "feature_desc": "Quando hai bisogno di viaggiare via mare, puoi ottenere un passaggio gratuito per te e i tuoi compagni su una nave mercantile o da pesca in cambio di aiuto a bordo.",
        "traits": [
            "Non sto mai fermo e scruto continuamente l'orizzonte e il meteo.",
            "Ho una superstizione bizzarra per ogni cosa: gabbiani, nodi, maree e vento.",
            "Mi sento a disagio quando resto troppo a lungo lontano dall'odore del mare.",
            "Risolvo quasi ogni discussione amichevole con una scommessa o un canto marinaresco."
        ],
        "ideals": [
            "Libertà: Il mare è l'unico posto dove nessun re o legge può imprigionare l'anima. (Caotico)",
            "Solidarietà: Sulla nave si sopravvive solo lavorando all'unisono come una sola ciurma. (Buono)",
            "Lealtà: Il codice della nave e la parola data al capitano sono sacri. (Legale)",
            "Audacia: Chi non rischia non assaggia mai le ricchezze dei mari inesplorati. (Neutrale)"
        ],
        "bonds": [
            "La nave su cui ho navigato è stata affondata da un leviatano; un giorno lo troverò.",
            "Un compagno di ciurma mi ha salvato dall'annegamento: gli devo la mia vita.",
            "Il mio sogno è possedere una nave tutta mia ed essere capitano del mio destino.",
            "Custodisco una mappa incompleta che conduce a un'isola non segnata sulle carte."
        ],
        "flaws": [
            "Spendo tutto il mio oro in birra e dadi appena metto piede in un porto.",
            "Non resisto alla tentazione di tuffarmi nel pericolo quando c'è di mezzo una tempesta.",
            "Tendo a risolvere le dispute con pugni e risse da taverna portuale.",
            "Sono terrorizzato dalle creature sotterranee e dall'idea di essere sepolto vivo."
        ]
    },
    "Forestiero (Outlander)": {
        "name_en": "Outlander",
        "desc": "Sei cresciuto nelle terre selvagge: foreste sterminate, steppe sconfinate o picchi innevati. La civiltà ti è estranea, ma la natura non ha segreti per te.",
        "skills": ["Atletica", "Sopravvivenza"],
        "tools": "Uno strumento musicale, una lingua a scelta",
        "gold": 10,
        "equipment": "Un bastone ferrato, una trappola per animali, un corno di cervo intagliato, abiti da viaggio e 10 mo.",
        "feature_name": "Viaggiatore Nato",
        "feature_desc": "Ricordi perfettamente la conformazione del terreno, le fonti d'acqua e le stelle. Puoi reperire cibo fresco e acqua potabile per te e fino a 5 compagni ogni giorno.",
        "traits": [
            "Osservo attentamente la natura per prevedere pericoli prima che si manifestino.",
            "Le buone maniere cittadine mi sembrano ipocrite e ridicole; dico sempre ciò che penso.",
            "Tratto gli animali con rispetto pari o superiore a quello che riservo alle persone.",
            "Mi sento soffocare nelle città affollate e cerco sempre spazi aperti."
        ],
        "ideals": [
            "Armonia: Dobbiamo vivere in equilibrio con la natura senza depredarla. (Buono)",
            "Legge Naturale: Il forte protegge il branco e la terra; l'ordine della natura è perfetto. (Legale)",
            "Libertà: Nessun muro o confine dovrebbe mai limitare il cammino di un viandante. (Caotico)",
            "Sopravvivenza: Solo il più forte e adattabile merita di vedere l'alba successiva. (Malvagio)"
        ],
        "bonds": [
            "La mia tribù o il mio branco d'adozione è stato disperso: devo ritrovarne i superstiti.",
            "Proteggo un bosco antico o un luogo sacro della natura dalla contaminazione urbana.",
            "Porto con me un osso inciso con i canti ancestrali della mia gente.",
            "Un mostro terribile ha devastato la mia valle natale; devo cacciarlo fino alla fine."
        ],
        "flaws": [
            "Fatico a fidarmi di chi indossa abiti sfarzosi o vive dietro le mura di pietra.",
            "I miei impulsi selvaggi prendono il sopravvento quando sono ferito o sotto stress.",
            "Non capisco il concetto di proprietà privata per cose che la terra offre spontaneamente.",
            "Bevo alcolici troppo forti per sopportare il rumore e l'odore delle metropoli."
        ]
    },
    "Monello (Urchin)": {
        "name_en": "Urchin",
        "desc": "Sei cresciuto da solo per le strade fangose dei bassifondi, senza famiglia né tetto. Hai imparato a sopravvivere grazie all'astuzia, alla velocità e agli occhi aperti.",
        "skills": ["Furtività", "Prestidigitazione"],
        "tools": "Kit per camuffamento, strumenti da scasso",
        "gold": 10,
        "equipment": "Un piccolo coltellino, una mappa della città natia disegnata a mano, un topolino addomesticato, abiti comuni logori e 10 mo.",
        "feature_name": "I Segreti della Città",
        "feature_desc": "Conosci i passaggi nascosti, tetti, vicoli ciechi e fogne delle città. Quando non sei in combattimento, tu e i tuoi compagni potete muovervi tra due punti della città a doppia velocità.",
        "traits": [
            "Nascondo sempre un pezzo di pane secco o una moneta nelle cuciture degli stivali.",
            "Dormo rannicchiato con le spalle al muro e le mani strette attorno alle mie cose.",
            "Parlo velocemente, gesticolo e osservo costantemente le tasche altrui.",
            "Sono feroce con chiunque se la prenda con bambini o mendicanti indifesi."
        ],
        "ideals": [
            "Solidarietà: Nessuno dovrebbe soffrire la fame o il freddo come ho fatto io. (Buono)",
            "Furbizia: Le regole le fanno i ricchi per proteggere il loro oro; io faccio le mie. (Caotico)",
            "Riscatto: Un giorno sarò ricco e potente e nessuno oserà più guardarmi dall'alto in basso. (Neutrale)",
            "Vendetta: La società mi ha calpestato per anni; ora mi prenderò ciò che mi spetta. (Malvagio)"
        ],
        "bonds": [
            "La banda di ragazzini di strada con cui sono cresciuto è la mia vera famiglia.",
            "Un vecchio mendicante cieco mi ha insegnato a sopravvivere; veglio su di lui.",
            "Custodisco l'unico ricordo di mia madre: una medaglietta arrugginita con un ritratto sbiadito.",
            "Voglio comprare una casa calda e sicura dove nessun bambino debba più tremare di freddo."
        ],
        "flaws": [
            "Se minacciato o messo all'angolo, ricorro a morsi, unghie e trucchi sporchi senza onore.",
            "Non riesco a gettare via nulla di commestibile anche se stantio o avariato.",
            "Diffido di chi mi fa un complimento o mi offre un aiuto senza chiedere nulla in cambio.",
            "Tendo a rubare piccole cianfrusaglie luccicanti senza un reale valore."
        ]
    },
    "Artigiano della Gilda": {
        "name_en": "Guild Artisan",
        "desc": "Sei un maestro in un'arte o mestiere riconosciuto. Fai parte di una gilda mercantile che tutela la qualità del lavoro e garantisce rispetto nel commercio.",
        "skills": ["Intuizione", "Persuasione"],
        "tools": "Un set di strumenti da artigiano, una lingua a scelta",
        "gold": 15,
        "equipment": "Un set di strumenti da artigiano, lettera d'introduzione della gilda, abiti da viaggio eleganti e 15 mo.",
        "feature_name": "Tessera della Gilda",
        "feature_desc": "Come membro rispettato della gilda, hai vitto e alloggio gratuito presso le sedi della corporazione in qualsiasi città e puoi contare sul supporto legale e politico dei confratelli.",
        "traits": [
            "Valuto ogni oggetto o costruzione dalla qualità dei materiali e della manifattura.",
            "Sono meticoloso e preciso in tutto ciò che faccio; odio il lavoro frettoloso.",
            "Conosco il prezzo esatto di quasi ogni bene commerciale comune.",
            "Parlo con orgoglio del mio mestiere e della reputazione della mia corporazione."
        ],
        "ideals": [
            "Comunità: La corporazione protegge tutti i membri e arricchisce la società. (Legale)",
            "Generosità: Condivido i frutti della mia maestria per migliorare la vita altrui. (Buono)",
            "Innovazione: Voglio inventare nuove tecniche che superino le vecchie tradizioni. (Caotico)",
            "Avidità: L'unico vero metro del valore di una persona è il peso della sua borsa d'oro. (Malvagio)"
        ],
        "bonds": [
            "Il capolavoro della mia vita è stato rubato da un rivale; devo recuperarlo.",
            "Devo restituire alla gilda il prestito che mi ha permesso di aprire la mia prima bottega.",
            "Voglio diventare il maestro artigiano più rinomato dell'intero continente.",
            "Proteggerò i miei apprendisti e la memoria del mio vecchio maestro."
        ],
        "flaws": [
            "Faccio fatica a separarmi dalle monete d'oro e contratto su ogni singolo centesimo.",
            "Sono geloso dei miei segreti professionali e diffido di altri artigiani.",
            "Giudico grezzo o inferiore chiunque non possieda un mestiere o un'arte raffinata.",
            "Sacrificherei quasi tutto pur di mettere le mani su un materiale leggendario."
        ]
    },
    "Intrattenitore": {
        "name_en": "Entertainer",
        "desc": "Vivi per gli applausi, le risate e le lacrime del pubblico. Attore, musico, acrobata o giullare, sai come scaldare una taverna o incantare un banchetto nobiliare.",
        "skills": ["Acrobazia", "Intrattenere"],
        "tools": "Kit per camuffamento, uno strumento musicale",
        "gold": 15,
        "equipment": "Uno strumento musicale a scelta, costume da scena sgargiante, regalo di un ammiratore devoto e 15 mo.",
        "feature_name": "Per il Piacere del Pubblico",
        "feature_desc": "Puoi sempre trovare alloggio e cibo gratuito di buon livello in qualsiasi locanda o teatro in cambio di spettacoli serali per gli avventori.",
        "traits": [
            "Cambio umore e tono di voce come se stessi sempre recitando una scena teatrale.",
            "Faccio battute ironiche o intono una canzoncina anche nelle situazioni più tese.",
            "Adoro essere al centro dell'attenzione e fatico a stare in silenzio.",
            "Trovo bellezza e poesia anche nei momenti più tragici dell'esistenza."
        ],
        "ideals": [
            "Bellezza: L'arte e la musica sono ciò che rende la vita degna di essere vissuta. (Buono)",
            "Creatività: Il mondo è un palcoscenico e non tollero dogmi o censure. (Caotico)",
            "Tradizione: Le antiche canzoni e ballate preservano la memoria storica dei popoli. (Legale)",
            "Celebrità: Voglio che il mio nome e le mie ballate siano immortali a qualunque costo. (Malvagio)"
        ],
        "bonds": [
            "Il mio strumento musicale è un dono di inestimabile valore; morirei prima di perderlo.",
            "Cerco l'ispirazione per comporre la ballata perfetta che unificherà popoli in guerra.",
            "Un nobile potente mi ha bandito per una satira pungente; voglio prendermi la rivincita.",
            "Proteggo la compagnia di teatranti itineranti con cui ho mosso i primi passi."
        ],
        "flaws": [
            "Non so resistere alle lusinghe di un ammiratore attraente o alle attenzioni del pubblico.",
            "Ho una vanità smisurata e mi offendo a morte se qualcuno critica le mie doti artistiche.",
            "Tendo a drammatizzare ogni piccolo contrattempo come se fosse una tragedia epica.",
            "Bevo e festeggio troppo ogni volta che ricevo applausi e monete."
        ]
    },
    "Eremita": {
        "name_en": "Hermit",
        "desc": "Hai vissuto anni in solitudine ascetica in una grotta, su una vetta o nel profondo dei boschi, cercando una verità spirituale lontana dal frastuono del mondo.",
        "skills": ["Medicina", "Religione"],
        "tools": "Borsa da erborista, una lingua a scelta",
        "gold": 5,
        "equipment": "Borsa da erborista, custodia per pergamene con note filosofiche, coperta invernale, abiti comuni e 5 mo.",
        "feature_name": "Rivelazione Segreta",
        "feature_desc": "La tua prolungata solitudine ti ha svelato una grande verità cosmica: una profezia, la posizione di un santuario dimenticato o un segreto che cambierà il destino della campagna.",
        "traits": [
            "Parlo raramente e scelgo ogni singola parola con estrema ponderatezza.",
            "Trovo conforto nel silenzio e resto impassibile di fronte a urla e clamori.",
            "Spesso mi perdo a fissare il vuoto o le stelle comunicando coi miei pensieri.",
            "Sono completamente ignaro delle mode, del gossip e della politica moderna."
        ],
        "ideals": [
            "Illuminazione: La conoscenza di sé stessi e dell'universo è la meta finale. (Buono)",
            "Armonia: L'universo segue cicli immutabili che non devono essere turbati. (Legale)",
            "Libero Pensiero: L'isolamento mi ha insegnato che nessuna autorità possiede la verità assoluta. (Caotico)",
            "Distacco: Il mondo materiale è un'illusione passeggera senza valore. (Neutrale)"
        ],
        "bonds": [
            "Devo impedire che la rivelazione che ho scoperto cada nelle mani sbagliate.",
            "Il mio eremo sacro è minacciato da forze oscure; devo tornare a difenderlo.",
            "Sono uscito dal mio isolamento solo perché una visione mi ha ordinato di unirmi a questo gruppo.",
            "Custodisco l'ultima pianta medicinale rara capace di curare un morbo antico."
        ],
        "flaws": [
            "Fatico a comprendere le convenzioni sociali e posso sembrare scontroso o eccentrico.",
            "La mia rivelazione mi ossessiona al punto da farmi ignorare le necessità pratiche.",
            "Sono convinto che le mie intuizioni mistiche siano infallibili e fatico ad ascoltare consigli.",
            "Mi sento sopraffatto e ansioso quando mi trovo in mezzo a grandi folle cittadine."
        ]
    },
    "Ciarlatano": {
        "name_en": "Charlatan",
        "desc": "Sai cosa vuole sentirsi dire la gente e glielo vendi con un sorriso. Maestro delle false speranze, dei giochi di prestigio e delle identità fasulle.",
        "skills": ["Inganno", "Prestidigitazione"],
        "tools": "Kit per camuffamento, kit da falsario",
        "gold": 15,
        "equipment": "Abiti eleganti, kit da falsario, dadi truccati o mazzo di carte segnate, flaconi con liquido colorato (false pozioni) e 15 mo.",
        "feature_name": "Seconda Identità",
        "feature_desc": "Hai creato una seconda identità completa di documenti falsi, lettere di credito e travestimenti credibili per muoverti indisturbato tra gli insospettabili.",
        "traits": [
            "Non riesco a dire la verità schietta se posso renderla più interessante con un tocco di colore.",
            "Lusingo le persone facendo leva sulla loro vanità per ottenere ciò che voglio.",
            "Ho una battuta pronta e una risposta affascinante per ogni accusa.",
            "Cambio spesso nome e professione a seconda di chi ho di fronte."
        ],
        "ideals": [
            "Autonomia: Non sarò mai schiavo di un padrone; la mia mente è la mia unica padrona. (Caotico)",
            "Equità: Truffo solo chi è abbastanza avido o arrogante da meritarselo. (Buono)",
            "Fatturato: Se qualcuno è così sciocco da farsi spillare oro, è una legge di natura. (Neutrale)",
            "Controllo: Manipolare le menti altrui è l'arte più nobile e gratificante che esista. (Malvagio)"
        ],
        "bonds": [
            "Ho truffato la persona sbagliata e ora un cacciatore di taglie implacabile è sulle mie tracce.",
            "I proventi delle mie truffe servono a pagare i debiti di una persona che amo.",
            "Voglio realizzare il colpo del secolo e truffare un intero consiglio nobiliare.",
            "Custodisco una promessa fatta a un vecchio maestro ciarlatano sul letto di morte."
        ],
        "flaws": [
            "Non so resistere all'impulso di tirare un bidone quando la vittima è troppo presuntuosa.",
            "Sono un bugiardo compulsivo, anche su dettagli del tutto insignificanti.",
            "Scappo dalla porta posteriore non appena la situazione diventa poco limpida.",
            "L'avidità mi spinge a tirare troppo la corda rischiando di far crollare tutto il castello di carte."
        ]
    },
    "Personalizzato": {
        "name_en": "Custom",
        "desc": "Crea la tua storia unica selezionando 2 abilità a scelta, un privilegio narrativo personalizzato e spunti ruolistici a piacere.",
        "skills": ["Intuizione", "Percezione"],
        "tools": "Due strumenti o lingue a scelta",
        "gold": 15,
        "equipment": "Abiti da viaggio, un cimelio speciale e 15 mo.",
        "feature_name": "Privilegio Unico",
        "feature_desc": "Concorda con il Dungeon Master un vantaggio sociale o logistico coerente con le tue origini (es. contatti, conoscenze locali o favori).",
        "traits": [
            "Ho un tratto distintivo legato alle mie origini peculiari.",
            "Affronto il mondo secondo un mio codice personale maturato negli anni."
        ],
        "ideals": [
            "Autodeterminazione: Ognuno è artefice del proprio destino.",
            "Lealtà: Resto fedele a chi mi dimostra rispetto e stima."
        ],
        "bonds": [
            "C'è una promessa fatta in gioventù che guida ogni mio passo.",
            "Custodisco un ricordo tangibile delle mie radici."
        ],
        "flaws": [
            "Porto una cicatrice o un trauma che a volte riaffiora nei momenti critici.",
            "Tendo a confidare solo in me stesso e fatico a delegare."
        ]
    }
}

PERSONAL_QUESTS: List[Dict[str, str]] = [
    {
        "title": "Redenzione per un Passato Oscuro",
        "desc": "Cerchi di espiare una grave colpa o un tragico errore del tuo passato che tormenta la tua coscienza e i tuoi sogni."
    },
    {
        "title": "Vendetta / Nemesi Giurata",
        "desc": "Insegui chi ha tradito il tuo mentore, sterminato la tua famiglia o confiscato le terre che ti spettavano di diritto."
    },
    {
        "title": "Debito d'Onore o Monetario",
        "desc": "Devi estinguere un debito enorme contratto con una gilda spietata o un nobile influente prima che riscuotano la tua vita."
    },
    {
        "title": "Pellegrinaggio & Fede Risvegliata",
        "desc": "Una visione mistica o la voce della tua divinità ti ha ordinato di viaggiare fino ai confini del mondo conosciuto."
    },
    {
        "title": "Maledizione da Spezzare",
        "desc": "Tu o una persona a te cara siete afflitti da una maledizione o morbo arcano che solo un antico artefatto o rituale può purificare."
    },
    {
        "title": "Gloria Eterna & Poemi Bardici",
        "desc": "Vuoi dimostrare il tuo valore contro mostri leggendari, guadagnarti un titolo e far sì che i bardi cantino le tue gesta per secoli."
    },
    {
        "title": "Ricerca del Mentore Scomparso",
        "desc": "La persona che ti ha insegnato tutto è svanita nel nulla all'improvviso, lasciando solo un enigma indecifrabile."
    },
    {
        "title": "Protezione degli Oppressi",
        "desc": "Hai giurato sulla tua arma di essere lo scudo per chiunque non possa difendersi dalla tirannia e dalla crudeltà."
    },
    {
        "title": "Segreti Arcani & Sapere Proibito",
        "desc": "Sei spinto da un'insaziabile sete di conoscenza verso rovine dimenticate, antiche biblioteche e magie credute perdute."
    },
    {
        "title": "Riconquista del Retaggio Ereditario",
        "desc": "Vuoi riscattare il blasone, le terre o la bottega avita che ti sono stati sottratti con l'inganno o con la spada."
    }
]

CHARACTER_SECRETS: List[Dict[str, str]] = [
    {
        "title": "Erede Nascosto",
        "desc": "Sei il legittimo discendente di un casato nobile spodestato, fatto fuggire in fasce e creduto morto da tutti."
    },
    {
        "title": "Marchio dell'Occulto",
        "desc": "Porti sul corpo un marchio o tatuaggio arcano impresso alla nascita che pulsa in presenza di certe entità o reliquie."
    },
    {
        "title": "Falsa Identità",
        "desc": "Il nome e la storia con cui ti presenti sono un'invenzione accurata: stai fuggendo da una taglia salata sulla tua testa."
    },
    {
        "title": "Cimelio Pericoloso",
        "desc": "Custodisci un piccolo oggetto che hai trovato o sottratto, ignaro che contenga un frammento di potere bramato da cultisti."
    },
    {
        "title": "Ricatto Riluttante",
        "desc": "Un'organizzazione conosce un tuo terribile segreto e ti costringe a inviare messaggi periodici sui movimenti del gruppo."
    },
    {
        "title": "Sopravvissuto Unico",
        "desc": "Sei l'unico superstite di un massacro compiuto da una creatura mostruosa che ancora infesta i tuoi incubi."
    },
    {
        "title": "Patto dell'Ombra",
        "desc": "In un momento di disperazione hai stretto un giuramento con un'entità misteriosa che prima o poi verrà a riscuotere il conto."
    },
    {
        "title": "Sangue Fatato o Infernale Latente",
        "desc": "Nelle tue vene scorre una traccia sopita di sangue planare che a volte influenza i tuoi sogni o le reazioni degli animali."
    },
    {
        "title": "Nessun Segreto Oscuro",
        "desc": "Un passato limpido e onesto, senza scheletri nell'armadio né nemici occulti nell'ombra."
    }
]

PARTY_TIES: List[Dict[str, str]] = [
    {
        "title": "Compagni d'Armi del Passato",
        "desc": "Avete già combattuto fianco a fianco in una scaramuccia passata o servito nella stessa milizia cittadina."
    },
    {
        "title": "Salvezza Reciproca",
        "desc": "Uno dei compagni ti ha salvato la vita in una situazione critica, o sei stato tu a trarlo d'impaccio."
    },
    {
        "title": "Rivali Amichevoli",
        "desc": "Vi conoscete da tempo e siete in costante, giocosa competizione per dimostrare chi è più abile sul campo."
    },
    {
        "title": "Debito Morale / Promessa",
        "desc": "Hai promesso a un amico comune o a un vecchio mentore che avresti vegliato su questo compagno."
    },
    {
        "title": "Radici Comuni",
        "desc": "Siete cresciuti nello stesso villaggio, quartiere o comunità e condividete amici e ricordi d'infanzia."
    },
    {
        "title": "Incontro sulla Strada",
        "desc": "Vi siete incontrati lungo il cammino verso questa missione e avete stretto un patto di reciproca assistenza."
    },
    {
        "title": "Primo Incontro",
        "desc": "Vi conoscete per la prima volta all'inizio di questa avventura: vi studierete durante le prime prove."
    }
]

TRINKETS: List[str] = [
    "Una moneta d'argento spezzata esattamente a metà, lucidata dall'usura.",
    "Una lettera d'amore sigillata con ceralacca nera, mai recapitata né aperta.",
    "Un piccolo pezzo di vetro scuro che riflette le stelle anche in pieno giorno.",
    "Un dado a sei facce in osso intagliato che sembra cadere sempre sullo stesso numero.",
    "Una scaglia di drago grande quanto un palmo, fredda al tatto in qualunque stagione.",
    "Un taccuino logoro parzialmente bruciato con mappe e appunti scarabocchiati a mano.",
    "Una piuma di corvo argentata che galleggia a mezz'aria se lasciata cadere.",
    "Una pesante chiave di ferro arrugginita senza alcuna serratura conosciuta.",
    "Un carillon tascabile che suona una melodia dolce, malinconica e dimenticata.",
    "Un pugnale giocattolo in legno intagliato con due iniziali intrecciate sull'elsa.",
    "Una boccetta di vetro con sabbia che risplende debolmente al buio.",
    "Un anello di ottone che diventa caldo quando avverte la presenza di magia."
]


def generate_backstory(
    name: str,
    race: str,
    char_class: str,
    background: str,
    origin_place: str = "",
    trait: str = "",
    ideal: str = "",
    bond: str = "",
    flaw: str = "",
    quest: str = "",
    secret: str = "",
    trinket: str = ""
) -> str:
    """Genera una biografia narrativa (2-3 paragrafi) fluida ed evocativa basata sulle scelte del giocatore."""
    hero_name = name.strip() if name and name.strip() else "L'eroe"
    place = origin_place.strip() if origin_place and origin_place.strip() else "terre lontane segnate da antiche leggende"
    bg_clean = background.split("(")[0].strip() if background else "un passato avvolto nel mistero"
    
    # Paragrafo 1: Origini e indole
    p1 = f"Nato e cresciuto tra {place}, {hero_name} ha conosciuto presto le sfide e le asperità del mondo come {bg_clean}."
    if trait:
        p1 += f" Chi lo ha incontrato sul suo cammino ha imparato a conoscerne l'indole caratteristica: {trait.rstrip('.')}."
    if ideal:
        p1 += f" Nel proprio cuore custodisce una salda bussola morale: '{ideal.rstrip('.')}."
    if flaw:
        p1 += f" Tuttavia, anche l'animo più saldo nasconde una debolezza: {flaw.rstrip('.')}."

    # Paragrafo 2: Vocazione, Legame e Cimelio
    p2 = f"La sua dedizione all'arte di {char_class} unita alla tempra di {race} ne hanno forgiato il destino."
    if quest:
        p2 += f" Ciò che lo ha spinto ad abbandonare la quiete per affrontare i pericoli delle terre selvagge è un obiettivo chiaro: {quest.rstrip('.')}."
    if bond:
        p2 += f" Nelle notti più buie, la memoria resta legata a un voto incrollabile: '{bond.rstrip('.')}."
    if trinket:
        p2 += f" Tra i suoi averi più cari conserva con gelosa cura {trinket.rstrip('.')}."

    # Paragrafo 3: L'Ombra e il Futuro
    p3 = ""
    if secret and "Nessun" not in secret:
        p3 = f"Mentre cammina al fianco dei propri compagni d'arme, un'ombra silenziosa accompagna i suoi passi: {secret.rstrip('.')}."
        p3 += f" Solo il corso della campagna svelerà se {hero_name} saprà superare le ombre del proprio passato o se ne verrà consumato."
    else:
        p3 = f"Con lo sguardo rivolto verso l'orizzonte e la spada o il tomo al proprio fianco, {hero_name} è pronto a scrivere il proprio capitolo nella storia di questa terra."

    paragraphs = [p1, p2]
    if p3:
        paragraphs.append(p3)
    return "\n\n".join(paragraphs)
