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


import re

# -----------------------------------------------------------------------------
# ARCHIVIO DI COERENZA NARRATIVA: RAZZE, CLASSI E BACKGROUND D&D 5e
# -----------------------------------------------------------------------------

RACE_NARRATIVE_LORE: Dict[str, Dict[str, str]] = {
    "umano": {
        "heritage": "figlio di una stirpe tanto effimera quanto audace, desiderosa di lasciare un'impronta duratura in un mondo dominato da forze secolari",
        "culture": "abituato fin dall'infanzia all'adattabilità e al confronto continuo tra culture, ambizioni e regni in rapida trasformazione",
        "presence": "uno sguardo fiero e determinato, temprato dalla consapevolezza che ogni giorno va conquistato con le proprie forze"
    },
    "elfo": {
        "heritage": "erede della grazia secolare degli elfi, custode di un legame intimo con la magia arcana e le foreste primordiali",
        "culture": "cresciuto nel silenzio meditativo del trance e nella contemplazione di architetture e canti tramandati attraverso i secoli",
        "presence": "movimenti fluidi e silenziosi, con occhi profondi che sembrano riflettere ere dimenticate e segreti arcani"
    },
    "mezzelfo": {
        "heritage": "nato all'incrocio tra la passione febbrile della stirpe umana e la grazia immortale elfica, ponte vivente tra due mondi",
        "culture": "abituato a navigare tra la diffidenza e l'ammirazione, sviluppando un'empatia straordinaria e una saggezza diplomatica precoce",
        "presence": "un fascino magnetico e uno sguardo accorto che coglie ogni sfumatura negli animi di chi gli sta intorno"
    },
    "nano": {
        "heritage": "figlio della pietra e del ferro, temprato dall'onore ancestrale dei clan delle fortezze montane",
        "culture": "allevato tra il rimbombo delle forge ardenti, i canti guerrieri e il rispetto reverenziale per le genealogie scolpite nel granito",
        "presence": "una complessione massiccia e incrollabile, con mani nodose e callose abituate al peso del martello e della corazza"
    },
    "halfling": {
        "heritage": "discendente di un popolo fiero e conviviale, dotato di una fortuna proverbiale e di un insospettabile coraggio indomito",
        "culture": "cresciuto tra colline ubertose, focolari caldi e leggende narrate sorseggiando birra scura, dove la generosità è la prima virtù",
        "presence": "un sorriso disarmante e passi così leggeri da non smuovere una foglia, capaci di svanire tra la folla in un batter d'occhio"
    },
    "dragonide": {
        "heritage": "portatore dell'antico retaggio dei draghi, con scaglie lucenti e la potenza del soffio elementale celata nel petto",
        "culture": "educato alla rigida condotta marziale del clan, dove l'onore, la lealtà e la rettitudine morale sono più preziosi della vita stessa",
        "presence": "una statura imponente e maestosa, la cui sola apparizione incute reverenza e rispetto sia tra gli alleati che tra i nemici"
    },
    "tiefling": {
        "heritage": "segnato dal retaggio dei piani inferiori, portatore di corna fiammanti e di una volontà d'acciaio forgiata contro il pregiudizio",
        "culture": "cresciuto dovendo imparare a difendere la propria dignità dagli sguardi inquisitori, conquistandosi ogni rispetto palmo a palmo",
        "presence": "occhi senza pupilla che scintillano nell'oscurità e una presenza carismatica che non lascia mai indifferenti"
    },
    "gnomo": {
        "heritage": "portatore della scintilla vivace e inestinguibile degli gnomi, una mente geniale che trova meraviglia in ogni congegno e mistero",
        "culture": "allevato tra banchi da lavoro colmi di molle, lenti d'ingrandimento, polveri alchemiche e tomi d'illusione",
        "presence": "un entusiasmo contagioso, occhi vispi che analizzano ogni dettaglio e mani che non restano mai con le dita ferme"
    },
    "mezzorco": {
        "heritage": "nato con la possanza titanica della stirpe orchesca unita alla tenacia umana, con un cuore in cui divampa una fiamma indomabile",
        "culture": "costretto fin da giovane a dimostrare il proprio valore in terre di confine spietate, dove la debolezza è una condanna a morte",
        "presence": "una corporatura muscolosa segnata da cicatrici onorevoli e zanne pronunciate che testimoniano un retaggio di fiera resistenza"
    },
    "tabaxi": {
        "heritage": "agile viandante felino giunto da terre lontane ed esotiche, spinto da un'insaziabile fame di scoperte, tesori e leggende",
        "culture": "cresciuto tra carovane nomadi e giungle fitte, ascoltando racconti attorno al fuoco e collezionando cimeli stravaganti",
        "presence": "artigli affilati come rasoi, passi felpati e una curiosità vivida che lo spinge a esplorare ogni anfratto sconosciuto"
    },
    "aasimar": {
        "heritage": "prescelto dai piani superiori, toccato dalla luce celestiale e guidato da una voce angelica verso un destino superiore",
        "culture": "accompagnato fin dall'infanzia da sogni premonitori e dalla solenne consapevolezza del peso morale affidatogli dalle divinità",
        "presence": "un'aura di calma sovrannaturale, pelle che emana un tenue riflesso dorato o argenteo quando la concentrazione si fa intensa"
    },
    "golia": {
        "heritage": "figlio dei picchi tempestosi e delle vette perennemente innevate, dove la vita è una competizione costante contro gli elementi",
        "culture": "educato all'autonomia spartana e alla meritocrazia assoluta, dove ciascuno è valutato unicamente per le proprie azioni concrete",
        "presence": "una sagoma ciclopica incisa da tatuaggi tribali che narrano le più grandi prove fisiche e sopravvivenze della sua vita"
    }
}

CLASS_NARRATIVE_LORE: Dict[str, Dict[str, str]] = {
    "guerriero": {
        "vocation": "la maestria tattica e la disciplina assoluta del combattimento",
        "training": "Anni di marce forzate, duelli alla prima goccia di sangue e studio delle formazioni belliche hanno trasformato ogni arma in un'estensione naturale della sua mente e del suo corpo.",
        "battle_style": "Sul campo di battaglia non si lascia guidare dal panico: analizza i varchi nella difesa nemica con lucidità strategica e colpisce con precisione inesorabile."
    },
    "mago": {
        "vocation": "la decifrazione delle leggi universali e la tessitura della trama arcana",
        "training": "Notti insonni trascorse su pergamene ingiallite, formule matematico-geometriche e diagrammi d'evocazione hanno svelato alla sua mente la sintassi segreta che governa la realtà.",
        "battle_style": "Affronta le minacce con intelletto calcolatore, attingendo al proprio grimorio per piegare gli elementi, creare barriere impenetrabili e dominare il flusso dello scontro."
    },
    "chierico": {
        "vocation": "il sacro sacerdozio e l'incarnazione vivente della volontà divina",
        "training": "La sua investitura non è nata dalla teoria dottrinale, ma da una profonda epifania spirituale in cui la divinità ha toccato il suo spirito, conferendogli il dono dei miracoli.",
        "battle_style": "Brandisce il simbolo sacro come faro di speranza per gli alleati feriti e punizione folgorante contro le forze sacrileghe che minacciano gli innocenti."
    },
    "ladro": {
        "vocation": "l'arte dell'invisibilità, dell'infiltrazione e dell'opportunismo letale",
        "training": "I vicoli bui, i tetti scivolosi e le serrature più complesse sono stati la sua accademia; ha imparato che un passo silenzioso vale più di dieci corazze a piastre.",
        "battle_style": "Danza tra le ombre attendendo il momento perfetto per colpire dove l'armatura non protegge, dileguandosi prima ancora che il nemico comprenda da dove sia giunto l'affondo."
    },
    "stregone": {
        "vocation": "la magia primordiale e innata che pulsa direttamente nelle vene",
        "training": "Non ha mai dovuto studiare formule né pregare entità celesti: il potere magico è scaturito dalla sua carne per diritto di nascita, divampando come fiamma indomita.",
        "battle_style": "Modella l'energia arcana per puro istinto e carisma, plasmando incantesimi potenti con la metamagia per adattarli istantaneamente a ogni situazione."
    },
    "paladino": {
        "vocation": "il sacro Giuramento d'onore e la crociata contro l'oscurità",
        "training": "Ha piegato il ginocchio dinanzi all'altare e ha pronunciato parole eterne che hanno fatto vibrare la sua anima, consacrando ogni respiro alla giustizia e alla protezione.",
        "battle_style": "In combattimento è un baluardo inscalfibile; i suoi colpi sono infusi dal sacro castigo radioso e la sua sola presenza ispira coraggio a chiunque combatta al suo fianco."
    },
    "barbaro": {
        "vocation": "la furia primigenia e la comunione con gli spiriti ancestrali",
        "training": "Nelle terre selvagge e tra le prove più cruente ha scoperto che nel petto cova una tempesta che non conosce catene, pronta a scatenarsi quando il sangue chiama la battaglia.",
        "battle_style": "Quando entra nell'Ira ancestrale ignora il dolore e la stanchezza, abbattendosi sulle schiere avversarie con la forza inarrestabile di una frana alpina."
    },
    "bardo": {
        "vocation": "la musica della creazione e la custodia delle grandi leggende",
        "training": "Ha appreso che i primi suoni del multiverso erano accordi e parole di potere; attraverso strumenti e versi poetici è in grado di toccare l'essenza stessa della realtà.",
        "battle_style": "Tesse incantesimi tra una melodia e una battuta di spirito, rinvigorendo gli alleati demoralizzati e confondendo le menti dei nemici con illusioni e fascinazioni."
    },
    "druido": {
        "vocation": "la sacra custodia degli equilibri naturali e delle terre incontaminate",
        "training": "Ha bevuto alle sorgenti antiche nei circoli di pietre e ha compreso il linguaggio segreto delle bestie e delle fronde, consacrandosi alla difesa della vita contro la corruzione.",
        "battle_style": "Invoca il furore delle tempeste, fa germogliare rovi soffocanti e muta la propria forma nelle più letali creature della foresta per sbranare chi devasta il mondo naturale."
    },
    "monaco": {
        "vocation": "l'armonia ascetica tra spirito, mente e corpo attraverso il Ki",
        "training": "Anni di meditazione sul respiro, isolamento nei monasteri e ripetizione metodica dei kata hanno temprato il suo corpo fino a renderlo duro come l'ebano e agile come il vento.",
        "battle_style": "Schiva i colpi con movimenti impercettibili e colpisce con raffiche micidiali a mani nude, incanalando l'energia vitale per stordire e disarmare gli avversari."
    },
    "ranger": {
        "vocation": "la caccia, la sopravvivenza estrema e la vigilanza delle terre di confine",
        "training": "Ha fatto dei boschi ostili e delle brughiere desolate la propria dimora, imparando a interpretare ogni filo d'erba piegato e a seguire le tracce delle creature più infide.",
        "battle_style": "Mantiene il controllo dello spazio con frecce infallibili o rapide lame gemelle, abbattendo le mostruosità prima ancora che possano scorgere la sua posizione."
    },
    "warlock": {
        "vocation": "il patto occulto stretto con un'entità patrona ultraterrena",
        "training": "Spinto da una disperata necessità o da un'incontrollabile ambizione, ha osato guardare oltre il velo della realtà mortale, stringendo un legame indissolubile con un patrono arcano.",
        "battle_style": "Scatena deflagrazioni mistiche cariche di energia crepuscolare e invoca maledizioni ataviche con la sicurezza di chi comanda poteri che sfidano la comprensione umana."
    },
    "artefice": {
        "vocation": "la fusione innovativa tra artigianato metallurgico e magia applicata",
        "training": "Tra il fumo delle sostanze alchemiche e il tintinnio di ingranaggi di precisione, ha scoperto come infondere frammenti di potere arcano in metalli, gemme e congegni.",
        "battle_style": "Interviene sul campo schierando prototipi prodigiosi, potenziando gli equipaggiamenti dei compagni e scatenando alchimie tattiche inaspettate."
    }
}

BACKGROUND_NARRATIVE_LORE: Dict[str, Dict[str, str]] = {
    "accolito": {
        "past": "ha trascorso gli anni formativi all'interno di un santuario, officiando liturgie sacre, meditando sulle antiche scritture e offrendo conforto ai pellegrini",
        "expertise": "la conoscenza profonda delle gerarchie religiose e la capacità di trovare rifugio e assistenza presso i templi devoti",
        "memory": "il profumo acre dell'incenso che bruciava durante le lunghe veglie notturne ai piedi delle statue dorate"
    },
    "soldato": {
        "past": "ha servito nei ranghi di un reggimento militare, conoscendo la rigida gerarchia, le fatiche dei turni di guardia e il sangue versato sulla linea del fronte",
        "expertise": "la ferrea disciplina bellica, il rispetto per i ranghi di comando e l'istinto immediato di fare quadrato con i propri compagni",
        "memory": "il clangore assordante dei gladi che sbattevano sugli scudi prima dell'impatto con la fanteria nemica"
    },
    "criminale / spia": {
        "past": "ha mosso i primi passi nelle viscere umide della città, guadagnandosi da vivere grazie a colpi furtivi, ricettazione e commercio di informazioni riservate",
        "expertise": "una fitta rete di contatti fidati nel sottobosco criminale e la capacità di scovare vie di fuga e trappole prima di chiunque altro",
        "memory": "la sensazione della pietra umida sotto le dita durante le fughe precipitose sui tetti al chiaro di luna"
    },
    "nobile": {
        "past": "è cresciuto tra arazzi sontuosi, banchetti cerimoniali e i sussurri velenosi dell'alta aristocrazia, educato al comando e al galateo delle corti",
        "expertise": "l'autorevolezza innata nel farsi ascoltare dalle autorità e la padronanza delle sottili trame del potere politico",
        "memory": "il sigillo in ceralacca del proprio stemma nobiliare impresso su documenti che decidevano le sorti di intere contee"
    },
    "saggio": {
        "past": "ha consumato la propria giovinezza nelle biblioteche labirintiche e negli scriptoria accademici, dedicandosi alla ricerca di verità dimenticate",
        "expertise": "la capacità di rintracciare qualsiasi frammento di sapere storico o cosmologico consultando archivi e cerchie di studiosi",
        "memory": "la polvere sottile dei manoscritti millenari che volteggiava nel fascio di luce di una finestra a sesto acuto"
    },
    "marinaio": {
        "past": "ha solcato le acque tumultuose a bordo di galeoni e velieri mercantili, affrontando tempeste furiose, mostri abissali e la vita spartana di bordo",
        "expertise": "la confidenza naturale con le rotte nautiche, i nodi marinari e la solidarietà spontanea che unisce ogni lupo di mare nei porti",
        "memory": "il sale che bruciava sulla pelle e il richiamo solitario dei gabbiani al levare del sole sull'oceano sconfinato"
    },
    "forestiero (outlander)": {
        "past": "è cresciuto lontano dalla civiltà urbana, tra valli incontaminate e picchi montuosi dove ogni errore si paga con la vita",
        "expertise": "un senso dell'orientamento impeccabile e la prodigiosa capacità di procacciare cibo e acqua pulita per sé e per il gruppo",
        "memory": "il cielo notturno terso e privo di fumi cittadini, costellato da una miriade di stelle che fungevano da bussola eterna"
    },
    "monello (urchin)": {
        "past": "è cresciuto da orfano nei quartieri più poveri e degradati, dovendo fare affidamento solo sulla propria furbizia e agilità per sfamarsi",
        "expertise": "la conoscenza viscerale delle scorciatoie urbane, delle fogne e dei segreti sussurrati nei vicoli dove la guardia cittadina non osa entrare",
        "memory": "il gelo pungente dell'inverno affrontato rannicchiato sotto una tettoia di legno fradicio stringendo un tozzo di pane"
    },
    "eroe popolare": {
        "past": "viveva come semplice cittadino o contadino fino al giorno in cui ha trovato il coraggio di opporsi a un tiranno locale o a una bestia predone",
        "expertise": "l'affetto incondizionato della gente umile, disposta a offrire asilo, cibo caldo e nascondigli sicuri senza chiedere nulla in cambio",
        "memory": "gli sguardi riconoscenti dei vicini radunati nella piazza del villaggio quando la minaccia fu sventata"
    },
    "artigiano della gilda": {
        "past": "ha imparato i segreti della maestria manuale all'interno di una prestigiosa gilda cittadina, perfezionando la lavorazione di materiali preziosi",
        "expertise": "il supporto logistico e legale della corporazione degli artigiani e l'occhio clinico per valutare manufatti ed equipaggiamenti",
        "memory": "il calore rassicurante della bottega e la soddisfazione tangibile nel vedere nascere un'opera d'arte dalla materia grezza"
    },
    "intrattenitore": {
        "past": "ha calcato i palcoscenici di fiere paesane e teatri nobiliari, facendo della recitazione, del canto e dell'acrobazia il proprio sostentamento",
        "expertise": "la facilità nell'ottenere ospitalità gratuita in cambio di esibizioni artistiche e la capacità di ammaliare e distrarre le folle",
        "memory": "il brusio che si spegneva di colpo quando saliva sulla scena, prima dell'esplosione di applausi e monete sul tavolaccio"
    },
    "eremita": {
        "past": "si è ritirato per lunghi anni dal consorzio umano in una grotta remota o in un monastero isolato, in cerca di contemplazione e verità interiore",
        "expertise": "la rivelazione di una grande scoperta spirituale o cosmologica che ha cambiato per sempre il suo modo di concepire il mondo",
        "memory": "il silenzio assoluto dell'alba sulle cime solitarie, rotto soltanto dal proprio respiro regolare in meditazione"
    },
    "ciarlatano": {
        "past": "ha fatto della truffa elegante e della manipolazione il proprio pane quotidiano, vendendo illusioni, falsi elisir e identità fittizie ai creduloni",
        "expertise": "la maestria nel falsificare documenti ufficiali, travestirsi e inventare al volo scuse e storie credibili per uscire dai guai",
        "memory": "il ghigno soddisfatto nel contare le monete d'oro mentre il carro si allontanava dalla città prima che la farsa venisse scoperta"
    },
    "personalizzato": {
        "past": "ha vissuto un percorso unico e fuori dagli schemi convenzionali, combinando esperienze diverse che ne hanno forgiato l'identità",
        "expertise": "una versatilità singolare nell'affrontare sfide pratiche e sociali attingendo a un bagaglio personale irripetibile",
        "memory": "il ricordo indelebile di una scelta radicale compiuta quando decise di non conformarsi al volere altrui"
    }
}

NARRATIVE_STYLES: Dict[str, Dict[str, str]] = {
    "heroic": {
        "name": "Eroico & Epico",
        "tone_p1": "Nelle vene di {hero_name} scorre la tempra e la fierezza di un destino che non ammette mediocrità.",
        "tone_closure": "Con lo sguardo fiero rivolto alle sfide dell'orizzonte e il cuore colmo di coraggio, {hero_name} avanza a testa alta: la sua leggenda è solo all'inizio."
    },
    "dark": {
        "name": "Dark Fantasy & Tormentato",
        "tone_p1": "Il mondo non ha mai fatto sconti a {hero_name}: ogni cicatrice impressa sulla sua carne e nel suo spirito racconta di prove spietate e perdite dolorose.",
        "tone_closure": "Tra ombre che allungano le loro mani sul suo cammino e un passato che non concede tregua, {hero_name} impugna le proprie armi: non cerca la gloria, ma la sopravvivenza o una faticosa redenzione."
    },
    "mystery": {
        "name": "Misterioso & Arcano",
        "tone_p1": "Fin dal primo vagito, la nascita di {hero_name} è stata accompagnata da presagi indecifrabili e coincidenze che sfidano le leggi del caso.",
        "tone_closure": "Guidato da intuizioni sussurrate nel vento e da enigmi che attendono di essere svelati, {hero_name} cammina sui confini tra il visibile e l'arcano: il suo destino nasconde segreti che potrebbero scuotere il mondo."
    },
    "picaresque": {
        "name": "Picaresco & Avventuroso",
        "tone_p1": "Se c'è una cosa che {hero_name} ha imparato presto, è che la vita è un gioco d'azzardo e che la fortuna bacia solo chi ha il coraggio di osare.",
        "tone_closure": "Con un sorriso beffardo, la lama ben affilata e la prontezza di chi sa cogliere al volo ogni occasione favorevole, {hero_name} è pronto a gettarsi nella mischia: l'avventura è appena cominciata."
    }
}


def _clean_rp_item(text: str) -> str:
    """Pulisce elementi ruolistici rimuovendo etichette come (Buono), (Legale), ecc."""
    if not text:
        return ""
    t = str(text).strip()
    t = re.sub(r"\s*\((?:Buono|Legale|Caotico|Malvagio|Neutrale|Qualsiasi|Buona|Legale/Buono|Buono/Neutrale)\)", "", t, flags=re.IGNORECASE)
    # Rimuovi etichette prima del trattino lungo se presente (es. 'Vendetta — Insegui...')
    return t.strip().rstrip(".")


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
    trinket: str = "",
    party_tie: str = "",
    narrative_style: str = "heroic",
    include_headers: bool = True,
    seed: Optional[int] = None,
    variation: int = 0
) -> str:
    """
    Generatore Narrativo Avanzato per D&D 5e:
    Compone una biografia ricca, articolata e coerente intrecciando le origini razziali,
    la formazione di background, la chiamata di classe, i pilastri ruolistici (Tratti, Ideali, Legami, Difetti),
    l'evento scatenante con il proprio cimelio e il legame con il gruppo d'avventura.
    """
    if seed is not None:
        random.seed(seed)

    hero_name = name.strip() if name and name.strip() else "L'eroe"
    place = origin_place.strip() if origin_place and origin_place.strip() else "terre lontane segnate da antiche leggende"
    
    # Risoluzione chiavi normalizzate
    r_key = str(race).strip().lower()
    for k in RACE_NARRATIVE_LORE:
        if k in r_key:
            r_key = k
            break
    race_info = RACE_NARRATIVE_LORE.get(r_key, RACE_NARRATIVE_LORE["umano"])

    c_key = str(char_class).strip().lower()
    for k in CLASS_NARRATIVE_LORE:
        if k in c_key:
            c_key = k
            break
    class_info = CLASS_NARRATIVE_LORE.get(c_key, CLASS_NARRATIVE_LORE["guerriero"])

    bg_raw = str(background).strip()
    bg_clean = bg_raw.split("(")[0].strip() if bg_raw else "Accolito"
    bg_key = bg_raw.lower()
    for k in BACKGROUND_NARRATIVE_LORE:
        if k in bg_key:
            bg_key = k
            break
    bg_info = BACKGROUND_NARRATIVE_LORE.get(bg_key, BACKGROUND_NARRATIVE_LORE["accolito"])

    style_key = narrative_style.lower() if narrative_style else "heroic"
    if "dark" in style_key or "cupo" in style_key or "tormentato" in style_key:
        style_key = "dark"
    elif "myster" in style_key or "arcano" in style_key:
        style_key = "mystery"
    elif "picar" in style_key or "avventur" in style_key:
        style_key = "picaresque"
    else:
        style_key = "heroic"
    style_info = NARRATIVE_STYLES.get(style_key, NARRATIVE_STYLES["heroic"])

    # Pulizia input ruolistici
    clean_trait = _clean_rp_item(trait)
    clean_ideal = _clean_rp_item(ideal)
    clean_bond = _clean_rp_item(bond)
    clean_flaw = _clean_rp_item(flaw)
    clean_quest = _clean_rp_item(quest)
    clean_secret = _clean_rp_item(secret)
    clean_trinket = _clean_rp_item(trinket)
    clean_party = _clean_rp_item(party_tie)

    # -------------------------------------------------------------------------
    # PARAGRAFO 1: ORIGINI E RETAGGIO
    # -------------------------------------------------------------------------
    p1_lines = []
    p1_open = style_info["tone_p1"].format(hero_name=hero_name)
    p1_lines.append(f"{p1_open} Nato e cresciuto tra {place}, {hero_name} è {race_info['heritage']}.")
    p1_lines.append(f"I suoi primi anni sono stati segnati dalla cultura di {race}: {race_info['culture']}.")
    if race_info.get("presence"):
        p1_lines.append(f"Chiunque lo incontri per la prima volta nota subito la sua presenza distintiva: {race_info['presence']}.")
    p1 = " ".join(p1_lines)

    # -------------------------------------------------------------------------
    # PARAGRAFO 2: GLI ANNI DELLA FORMAZIONE (BACKGROUND)
    # -------------------------------------------------------------------------
    p2_lines = []
    p2_lines.append(f"Prima di rispondere alla chiamata dell'avventura, la sua vita ha conosciuto le sfide e le fatiche del mondo come {bg_clean}.")
    p2_lines.append(f"In quel periodo formativo {bg_info['past']}, maturando {bg_info['expertise']}.")
    if bg_info.get("memory"):
        p2_lines.append(f"Tra i ricordi più vividi di quel capitolo di vita riaffiora ancora {bg_info['memory']}.")
    if clean_trait:
        p2_lines.append(f"Chi ha condiviso con lui la quotidianità ha imparato a conoscerne l'indole caratteristica: {clean_trait}.")
    p2 = " ".join(p2_lines)

    # -------------------------------------------------------------------------
    # PARAGRAFO 3: LA CHIAMATA DELLA CLASSE
    # -------------------------------------------------------------------------
    p3_lines = []
    p3_lines.append(f"Tuttavia, il corso della sua esistenza era destinato a una vocazione superiore: {class_info['vocation']}.")
    p3_lines.append(f"La sua dedizione all'arte di {char_class} unita alla tempra di {race} ne hanno forgiato il destino. {class_info['training']}")
    p3_lines.append(f"{class_info['battle_style']}")
    p3 = " ".join(p3_lines)

    # -------------------------------------------------------------------------
    # PARAGRAFO 4: L'EVENTO SCATENANTE, L'OBIETTIVO E IL CIMELIO
    # -------------------------------------------------------------------------
    p4_lines = []
    if clean_quest:
        p4_lines.append(f"A strapparlo dalla quiete del passato per spingerlo sui sentieri perigliosi dell'ignoto è stato un richiamo ineludibile: {clean_quest}.")
    else:
        p4_lines.append(f"Il desiderio insopprimibile di scoprire cosa si celi oltre i confini del mondo conosciuto lo ha infine spinto a imbracciare armi e bagagli.")

    if clean_trinket:
        p4_lines.append(f"Tra i suoi averi più cari conserva con gelosa cura {clean_trinket}, un cimelio a cui la sua memoria e il suo cuore sono indissolubilmente legati.")
    p4 = " ".join(p4_lines)

    # -------------------------------------------------------------------------
    # PARAGRAFO 5: L'ANIMA DELL'EROE, IL SEGRETO E IL GRUPPO
    # -------------------------------------------------------------------------
    p5_lines = []
    if clean_ideal:
        p5_lines.append(f"Nel proprio cuore custodisce una salda bussola morale: {clean_ideal}.")
    if clean_bond:
        p5_lines.append(f"Nelle notti più buie, la memoria e l'onore restano saldati a un voto incrollabile: {clean_bond}.")
    if clean_flaw:
        p5_lines.append(f"Eppure, anche l'animo più saldo nasconde una vulnerabilità: {clean_flaw}.")

    # Segreto del Personaggio (per il DM)
    if clean_secret and "nessun segreto" not in clean_secret.lower() and "nessuno" not in clean_secret.lower():
        p5_lines.append(f"Dietro la fermezza del suo sguardo si cela inoltre un'ombra silenziosa che non confida a nessuno: {clean_secret}.")

    # Legame con il gruppo
    if clean_party:
        p5_lines.append(f"Con i propri compagni d'arme condivide un vincolo speciale: {clean_party}.")

    p5_lines.append(style_info["tone_closure"].format(hero_name=hero_name))
    p5 = " ".join(p5_lines)

    # Assemblaggio finale
    if include_headers:
        chapters = [
            f"### I. Origini e Retaggio\n{p1}",
            f"### II. Gli Anni della Formazione come {bg_clean}\n{p2}",
            f"### III. La Chiamata del Destino: {char_class}\n{p3}",
            f"### IV. L'Evento Scatenante & Il Cimelio\n{p4}",
            f"### V. L'Anima dell'Eroe & L'Ombra del Segreto\n{p5}"
        ]
        return "\n\n".join(chapters)
    else:
        return "\n\n".join([p1, p2, p3, p4, p5])

