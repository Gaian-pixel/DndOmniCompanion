# common/manuals_manager.py
"""
Sistema di Gestione ed Interpellazione dei Manuali di Gioco D&D 5e.
Supporta:
- Manuali Ufficiali 5e Integrati (PHB, DMG, MM, XGtE, TCoE) in Italiano e Inglese
- File Custom (.md, .txt, .json) caricati nella cartella 'manuals/'
- Ricerca Full-Text e Fuzzy per Argomento, Parola Chiave, Capitolo o Azione
- Interrogazione Rapida per Chat Command (/manuale <termine> o /rule <termine>)
- Interrogazione online di fallback tramite 5e SRD API (dnd5eapi.co)
"""

import os
import re
import json
import glob
import urllib.request
from typing import List, Dict, Optional, Tuple

MANUALS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "manuals")

# -----------------------------------------------------------------------------
# DATABASE UFFICIALE DEI MANUALI 5e CORE (PHB, DMG, MM, XGtE/TCoE)
# -----------------------------------------------------------------------------
CORE_MANUALS_DATA = [
    # =========================================================================
    # PHB - COMBATTIMENTO & AZIONI
    # =========================================================================
    {
        "id": "phb_actions_in_combat",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Combattimento",
        "title": "Azioni in Combattimento (Actions in Combat)",
        "keywords": ["azione", "azioni", "combattimento", "action", "actions", "turno"],
        "page_ref": "PHB p. 192",
        "summary": "Nel proprio turno, una creatura può compiere 1 Azione Standard, oltre al movimento e a un'eventuale Azione Bonus.",
        "content": (
            "### Azioni Principali Disponibili nel Turno:\n\n"
            "• **Attaccare (Attack)**: Esegue un attacco con arma da mischia o a distanza. Classi con 'Attacco Extra' possono compiere più attacchi con questa singola azione.\n\n"
            "• **Lanciare un Incantesimo (Cast a Spell)**: Lancia un incantesimo con tempo di lancio di '1 Azione'.\n\n"
            "• **Scatto (Dash)**: Raddoppia la velocità di movimento per il turno corrente (es. 9m -> 18m).\n\n"
            "• **Disimpegno (Disengage)**: Per il resto del turno, il tuo movimento non provoca attacchi d'opportunità da parte dei nemici.\n\n"
            "• **Schivata (Dodge)**: Fino all'inizio del tuo prossimo turno, qualsiasi attacco contro di te ha Svantaggio (se puoi vedere l'attaccante) e ottieni Vantaggio ai Tiri Salvezza su Destrezza.\n\n"
            "• **Aiuto (Help)**: Concedi Vantaggio alla prossima prova di caratteristica di un alleato, oppure Vantaggio al prossimo tiro per colpire di un alleato contro un bersaglio entro 1,5 metri da te.\n\n"
            "• **Nascondersi (Hide)**: Effettua una prova di Destrezza (Furtività) contrapposta alla Percezione Passiva nemica per diventare nascosto.\n\n"
            "• **Preparare un'Azione (Ready)**: Scegli un innesco percepibile e l'azione da eseguire come Reazione quando l'innesco si verifica (richiede concentrazione se si prepara un incantesimo).\n\n"
            "• **Cercare (Search)**: Dedichi l'attenzione a trovare qualcosa effettuando una prova di Saggezza (Percezione) o Intelligenza (Indagare).\n\n"
            "• **Usare un Oggetto (Use an Object)**: Interagisci con un secondo oggetto nel turno o con un congegno che richiede un'azione dedicata (es. bere una pozione secondo RAW o azionare una leva complessa)."
        )
    },
    {
        "id": "phb_opportunity_attack",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Combattimento",
        "title": "Attacco d'Opportunità (Opportunity Attack)",
        "keywords": ["opportunita", "attacco opportunita", "reazione", "portata", "mischia", "opportunity"],
        "page_ref": "PHB p. 195",
        "summary": "Reazione scatenata quando una creatura nemica visibile esce dalla tua portata in mischia senza usare il Disimpegno.",
        "content": (
            "### Regole dell'Attacco d'Opportunità (PHB p. 195):\n\n"
            "• **Innesco**: Puoi effettuare un attacco d'opportunità quando una creatura ostile che puoi vedere esce dalla tua portata in mischia.\n"
            "• **Costo**: Spende la tua **Reazione** per quel round.\n"
            "• **Esecuzione**: L'attacco si interrompe ed è effettuato *un istante prima* che il bersaglio lasci la tua portata. Consiste in un singolo attacco con arma da mischia.\n"
            "• **Eccezioni**: Non provochi attacchi d'opportunità se usi l'azione di **Disimpegno (Disengage)**, se vieni teletrasportato, o se vieni spostato contro la tua volontà senza usare il tuo movimento, azione o reazione (es. respinto da un'onda o da una spinta)."
        )
    },
    {
        "id": "phb_cover",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Combattimento",
        "title": "Copertura (Cover)",
        "keywords": ["copertura", "mezza copertura", "tre quarti", "riparo", "cover", "muro"],
        "page_ref": "PHB p. 196",
        "summary": "Ostacoli tra te e il bersaglio aumentano la Classe Armatura (CA) e i Tiri Salvezza su Destrezza.",
        "content": (
            "### Gradi di Copertura:\n\n"
            "• **Mezza Copertura (Half Cover)**: Il bersaglio ha almeno metà del corpo coperto da un ostacolo (muretto, tronco, un'altra creatura).\n"
            "  └ Effetto: **+2 alla CA** e **+2 ai Tiri Salvezza su Destrezza** contro gli effetti che provengono dall'altro lato.\n\n"
            "• **Tre Quarti di Copertura (Three-Quarters Cover)**: Il bersaglio ha circa tre quarti del corpo coperto (grata di ferro, feritoia, tronco massiccio).\n"
            "  └ Effetto: **+5 alla CA** e **+5 ai Tiri Salvezza su Destrezza**.\n\n"
            "• **Copertura Totale (Total Cover)**: Il bersaglio è completamente celato da un ostacolo.\n"
            "  └ Effetto: Non può essere bersagliato direttamente da un attacco o incantesimo (salvo incantesimi con area d'effetto che aggirano gli angoli)."
        )
    },
    {
        "id": "phb_death_and_dying",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Combattimento",
        "title": "Punti Ferita a 0 & Tiri Salvezza contro la Morte (Death Saves)",
        "keywords": ["morte", "ts morte", "salvezza morte", "0 hp", "stabilizzare", "incosciente", "dying", "death"],
        "page_ref": "PHB p. 197",
        "summary": "Regole per quando un personaggio scende a 0 HP: Tiri Salvezza contro la Morte, Danno a 0 HP e Morte Istantanea.",
        "content": (
            "### Meccaniche di Morte e Ferite a 0 HP:\n\n"
            "• **Condizione Incosciente**: Quando scendi a 0 Punti Ferita senza morire all'istante, cadi Incosciente e Prono.\n\n"
            "• **Tiro Salvezza contro la Morte**: All'inizio di ogni tuo turno tiri 1d20 (nessun modificatore):\n"
            "  - **10 o superiore**: Successo.\n"
            "  - **9 o inferiore**: Fallimento.\n"
            "  - **Naturale 1**: Conta come **DUE fallimenti**.\n"
            "  - **Naturale 20**: Recuperi immediatamente **1 Punto Ferita** e riprendi i sensi.\n"
            "  - **3 Successi**: Diventi stabile (non tiri più TS finché non subisci altri danni).\n"
            "  - **3 Fallimenti**: Il tuo personaggio è **MORTO**.\n\n"
            "• **Subire Danni a 0 HP**: Se subisci danni mentre sei a 0 HP, segni automaticamente **1 fallimento**. Se il danno è un colpo critico (es. attacco in mischia entro 1,5m), segni **2 fallimenti**!\n\n"
            "• **Morte Istantanea (Massive Damage)**: Se il danno che ti porta a 0 HP ha danni residui pari o superiori al tuo massimo di PF totali, muori all'istante senza tiri salvezza.\n\n"
            "• **Stabilizzare**: Una creatura può stabilizzarti superando una prova di Saggezza (Medicina) con **CD 10** o spendendo una carica di una Borsa del Medico."
        )
    },
    {
        "id": "phb_temp_hp",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Combattimento",
        "title": "Punti Ferita Temporanei (Temporary Hit Points)",
        "keywords": ["temp hp", "ferita temporanei", "pf temporanei", "assorbimento", "scudo"],
        "page_ref": "PHB p. 198",
        "summary": "Punti ferita speciali che assorbono i danni per primi. Non sono cumulabili e non contano come cure.",
        "content": (
            "### Regole dei PF Temporanei:\n\n"
            "• **Assorbimento**: Quando subisci danni, i PF Temporanei vengono consumati per primi; i danni residui scalano i tuoi PF effettivi.\n"
            "• **Nessun Cumulo**: I PF Temporanei non si sommano mai tra loro. Se ricevi nuovi PF temporanei mentre ne hai già, scegli se tenere quelli attuali o applicare i nuovi.\n"
            "• **Non Curano**: I PF temporanei non ripristinano PF a una creatura a 0 HP e non rimuovono la condizione di Incosciente.\n"
            "• **Durata**: Rimangono fino a quando non vengono esauriti o finché non completi un Riposo Lungo, salvo diversamente specificato."
        )
    },
    {
        "id": "phb_resting",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Avventura",
        "title": "Riposo Breve e Lungo (Short & Long Rest)",
        "keywords": ["riposo", "riposo breve", "riposo lungo", "dadi vita", "hit dice", "rest", "dormire"],
        "page_ref": "PHB p. 186",
        "summary": "Procedure e recupero risorse durante le pause dell'avventura.",
        "content": (
            "### Riposo Breve (Short Rest - 1 Ora):\n\n"
            "• Periodo di pausa di almeno 1 ora in cui il personaggio non compie sforzi superiori a mangiare, bere, leggere e medicare le ferite.\n"
            "• **Spesa Dadi Vita**: Puoi spendere uno o più Dadi Vita rimasti. Per ogni dado tirato: recuperi `1 Dado Vita + Modificatore Costituzione` Punti Ferita.\n"
            "• **Ricarica Privilegi**: Si ricaricano abilità a riposo breve (es. Secondo Fiato e Azione Furente del Guerriero, slot del Warlock, Forma Selvatica del Druido).\n\n"
            "### Riposo Lungo (Long Rest - 8 Ore):\n\n"
            "• Periodo di ristoro prolungato di almeno 8 ore (almeno 6 ore di sonno e massimo 2 ore di attività leggera di guardia).\n"
            "• **Recupero Salute**: Recuperi tutti i Punti Ferita persi.\n"
            "• **Recupero Dadi Vita**: Recuperi una quantità di Dadi Vita pari alla metà dei tuoi Dadi Vita totali (minimo 1).\n"
            "• **Recupero Magia**: Recuperi tutti gli slot incantesimo spesi.\n"
            "• **Riduzione Sfinimento**: Se hai livelli di Sfinimento e hai consumato cibo e acqua a sufficienza, il tuo livello di Sfinimento diminuisce di 1.\n"
            "• **Limite**: Un personaggio può beneficiare di un solo Riposo Lungo nell'arco di 24 ore."
        )
    },
    {
        "id": "phb_spellcasting_concentration",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Magia",
        "title": "Concentrazione negli Incantesimi (Concentration)",
        "keywords": ["concentrazione", "spezzare", "tiro salvezza costituzione", "concentration", "magia"],
        "page_ref": "PHB p. 203",
        "summary": "Mantenere attivo un incantesimo a concentrazione richiede focus mentale e Tiri Salvezza su Costituzione quando si subiscono danni.",
        "content": (
            "### Regole della Concentrazione (PHB p. 203):\n\n"
            "• **Limite**: Puoi concentrarti su **un solo incantesimo alla volta**. Se lanci un altro incantesimo che richiede concentrazione, il primo termina all'istante.\n\n"
            "• **Subire Danni**: Ogni volta che subisci danni mentre ti concentri, devi superare un **Tiro Salvezza su Costituzione**:\n"
            "  - **CD Minima**: La CD è pari a **10** oppure alla **metà dei danni subiti**, quale dei due valori sia il più alto.\n"
            "  - Se subisci danni da più fonti nello stesso turno (es. due frecce separate), effettui un tiro salvezza separato per ogni fonte di danno.\n\n"
            "• **Incapacitato o Morto**: Se cadi Incapacitato o muori, la tua concentrazione si spezza immediatamente senza alcun tiro.\n\n"
            "• **Fattori Ambientali**: Eventi violenti (come un'ondata travolgente su una nave in tempesta) possono richiedere un TS Costituzione con CD 10 a discrezione del DM."
        )
    },
    {
        "id": "phb_spell_components",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Magia",
        "title": "Componenti degli Incantesimi: Verbale, Somatica, Materiale (V, S, M)",
        "keywords": ["componenti", "verbale", "somatica", "materiale", "focus arcano", "focus", "vsm", "spells"],
        "page_ref": "PHB p. 203",
        "summary": "Requisiti fisici per lanciare incantesimi: voce, gesti e materiali o catalizzatori arcani.",
        "content": (
            "### I Tre Tipi di Componenti:\n\n"
            "• **Verbale (V)**: Pronuncia di formule mistiche con voce chiara. Una creatura imbavagliata o all'interno di un'area di *Silenzio* non può lanciare incantesimi con componente verbale.\n\n"
            "• **Somatica (S)**: Gesti precisi delle mani. L'incantatore deve avere almeno **una mano libera** per eseguire questi gesti.\n\n"
            "• **Materiale (M)**: Oggetti fisici specifici richiesti dal testo dell'incantesimo.\n"
            "  - Un incantatore può usare una **Borsa dei Componenti** o un **Focus Arcano/Divino** al posto dei materiali ordinari, purché il componente **non abbia un costo in monete d'oro indicato** e non venga consumato.\n"
            "  - Se un componente ha un costo specificato (es. diamante da 300 MO per *Rinascita*), deve essere posseduto fisicamente e viene consumato se espressamente indicato.\n"
            "  - La mano usata per la componente materiale può essere la stessa mano usata per la componente somatica."
        )
    },

    # =========================================================================
    # PHB - CONDIZIONI DI STATO (CONDITIONS)
    # =========================================================================
    {
        "id": "phb_conditions_all",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Condizioni",
        "title": "Tutte le Condizioni di Stato 5e (Conditions Appendix)",
        "keywords": ["condizioni", "stati", "accecato", "prono", "trattenuto", "paralizzato", "conditions"],
        "page_ref": "PHB p. 290",
        "summary": "Elenco e meccaniche complete delle 15 condizioni di stato ufficiali di D&D 5e.",
        "content": (
            "### Elenco Condizioni di Stato 5e (PHB Appendice A):\n\n"
            "• **Accecato (Blinded)**: Fallisce automaticamente qualsiasi prova basata sulla vista. I tiri per colpire contro di lui hanno Vantaggio, i suoi tiri per colpire hanno Svantaggio.\n\n"
            "• **Afferrato (Grappled)**: La sua velocità scende a 0 e non beneficia di alcun bonus alla velocità. La condizione termina se chi afferra diventa Incapacitato o se l'afferrato viene allontanato con la forza.\n\n"
            "• **Ammaliato (Charmed)**: Non può attaccare chi lo ha ammaliato né bersagliarlo con abilità/effetti dannosi. Chi ammalia ha Vantaggio a qualsiasi prova sociale contro la creatura.\n\n"
            "• **Assordato (Deafened)**: Fallisce automaticamente qualsiasi prova basata sull'udito.\n\n"
            "• **Avvelenato (Poisoned)**: Svantaggio ai tiri per colpire e alle prove di caratteristica.\n\n"
            "• **Incapacitato (Incapacitated)**: Non può compiere azioni né reazioni.\n\n"
            "• **Incosciente (Unconscious)**: Incapacitato, cade prono e lascia cadere ciò che impugna. Non è consapevole. Fallisce automaticamente i TS su FOR e DES. Gli attacchi contro di lui hanno Vantaggio. Qualsiasi attacco a segno entro 1,5m è un **colpo critico automatico**.\n\n"
            "• **Invisibile (Invisible)**: Impossibile da vedere senza ausili magici. Considerato pesantemente oscurato ai fini del nascondersi. I suoi attacchi hanno Vantaggio, gli attacchi contro di lui hanno Svantaggio.\n\n"
            "• **Paralizzato (Paralyzed)**: Incapacitato, non può muoversi né parlare. Fallisce automaticamente TS su FOR e DES. Gli attacchi contro di lui hanno Vantaggio. Qualsiasi attacco a segno entro 1,5m è un colpo critico.\n\n"
            "• **Pietrificato (Petrified)**: Trasformato in pietra, il peso aumenta di 10x e cessa di invecchiare. Incapacitato, fallisce TS su FOR e DES. Ha resistenza a tutti i danni ed è immune a veleno e malattie.\n\n"
            "• **Prono (Prone)**: La sua unica opzione di movimento è strisciare (costo 2 a 1) o spendere metà della velocità totale per rialzarsi. Ha Svantaggio ai tiri per colpire. Gli attacchi contro di lui hanno Vantaggio se l'attaccante è entro 1,5m, altrimenti Svantaggio se da lontano.\n\n"
            "• **Spaventato (Frightened)**: Svantaggio alle prove di caratteristica e tiri per colpire finché la fonte della paura è nella sua linea di vista. Non può avvicinarsi volontariamente alla fonte della paura.\n\n"
            "• **Stordito (Stunned)**: Incapacitato, non può muoversi e può solo balbettare. Fallisce automaticamente TS su FOR e DES. Gli attacchi contro di lui hanno Vantaggio.\n\n"
            "• **Trattenuto (Restrained)**: Velocità 0. I suoi attacchi hanno Svantaggio, gli attacchi contro di lui hanno Vantaggio. Svantaggio ai TS su Destrezza."
        )
    },
    {
        "id": "phb_exhaustion",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Condizioni",
        "title": "Sfinimento (Exhaustion)",
        "keywords": ["sfinimento", "esausto", "exhaustion", "livelli sfinimento", "fatica", "marcia forzata"],
        "page_ref": "PHB p. 291",
        "summary": "Effetti progressivi da 1 a 6 livelli di sfinimento dovuti a marce forzate, fame, sete o freddo estremo.",
        "content": (
            "### Livelli di Sfinimento (Cumulativi):\n\n"
            "• **Livello 1**: Svantaggio alle Prove di Caratteristica.\n"
            "• **Livello 2**: Velocità dimezzata.\n"
            "• **Livello 3**: Svantaggio ai Tiri per Colpire e ai Tiri Salvezza.\n"
            "• **Livello 4**: Massimo dei Punti Ferita dimezzato.\n"
            "• **Livello 5**: Velocità ridotta a 0.\n"
            "• **Livello 6**: **MORTE IMMEDIATA**.\n\n"
            "**Recupero**: Completare un Riposo Lungo consumando le razioni e l'acqua necessarie riduce il livello di Sfinimento di 1."
        )
    },

    # =========================================================================
    # PHB - ESPLORAZIONE, VIAGGI & ABILITÀ
    # =========================================================================
    {
        "id": "phb_travel_pace_rules",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Viaggio",
        "title": "Andature di Viaggio & Ruoli 5e (Travel Pace)",
        "keywords": ["andatura", "viaggio", "marcia", "pace", "navigatore", "sentinella", "foraggiare", "travel"],
        "page_ref": "PHB p. 181",
        "summary": "Regole di movimento su mappa del mondo: andatura Lenta, Normale, Veloce e ruoli del gruppo.",
        "content": (
            "### Andature di Viaggio (PHB p. 181-182):\n\n"
            "• **Lenta (Slow)**: 2 miglia/ora (18 miglia/giorno). Permette l'avanzamento furtivo dei personaggi e conferisce **+5 alla Percezione Passiva** delle Sentinelle.\n\n"
            "• **Normale (Normal)**: 3 miglia/ora (24 miglia/giorno). Andatura equilibrata standard.\n\n"
            "• **Veloce (Fast)**: 4 miglia/ora (30 miglia/giorno). Impone una penalità di **-5 alla Percezione Passiva** delle Sentinelle, **-5 alle prove di navigazione** e impedisce la caccia e la furtività.\n\n"
            "### Ruoli e Attività Durante il Viaggio (PHB p. 182):\n"
            "• **Navigatore**: Effettua prove di Saggezza (Sopravvivenza) contro la CD del terreno per prevenire lo smarrimento.\n"
            "• **Sentinella**: Vigila sul pericolo usando la propria Percezione Passiva contro la Furtività di eventuali imboscate.\n"
            "• **Cacciatore/Foraggiere**: Cerca cibo e acqua fresca con Sopravvivenza CD 15/20.\n"
            "• **Cartografo**: Disegna la mappa del percorso per consentire al party di tornare sui propri passi senza perdersi.\n"
            "• **Esploratore Furtivo**: Avanza silenziosamente per sorprendere o aggirare nemici (solo ad andatura Lenta)."
        )
    },
    {
        "id": "phb_forced_march",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Viaggio",
        "title": "Marcia Forzata (Forced March)",
        "keywords": ["marcia forzata", "viaggio forzato", "forced march", "8 ore"],
        "page_ref": "PHB p. 181",
        "summary": "Viaggiare più di 8 ore al giorno richiede Tiri Salvezza su Costituzione progressivi per resistere allo Sfinimento.",
        "content": (
            "### Regole della Marcia Forzata (PHB p. 181):\n\n"
            "• Il limite di viaggio raccomandato senza affaticamento è di **8 ore al giorno**.\n"
            "• Per **ogni ora aggiuntiva** oltre l'ottava, ogni personaggio deve effettuare un **Tiro Salvezza su Costituzione** al termine dell'ora.\n"
            "• **Calcolo CD**: La CD è pari a `10 + 1 per ogni ora oltre l'ottava`:\n"
            "  - 9ª Ora: CD 11\n"
            "  - 10ª Ora: CD 12\n"
            "  - 11ª Ora: CD 13\n"
            "  - 12ª Ora: CD 14\n"
            "• **Fallimento**: Se un personaggio fallisce il tiro salvezza, subisce immediatamente **1 livello di Sfinimento**."
        )
    },
    {
        "id": "phb_vision_and_light",
        "manual": "PHB",
        "manual_name": "Manuale del Giocatore (PHB)",
        "category": "Avventura",
        "title": "Visione e Luce (Vision and Light)",
        "keywords": ["luce", "visione", "scurovisione", "buio", "luce fioca", "oscurita", "darkvision", "light"],
        "page_ref": "PHB p. 183",
        "summary": "Gradi di illuminazione e sensi speciali come Scurovisione, Vista Cieca e Vista Tremula.",
        "content": (
            "### Livelli di Luce:\n\n"
            "• **Luce Intensa (Bright Light)**: La maggior parte delle creature vede normalmente.\n"
            "• **Luce Fioca (Dim Light)**: Crea un'area di oscurità parziale. I personaggi hanno **Svantaggio alle prove di Saggezza (Percezione)** basate sulla vista.\n"
            "• **Buio / Oscurità (Darkness)**: Crea un'area pesantemente oscurata. I personaggi subiscono la condizione di **Accecato** quando tentano di vedere all'interno.\n\n"
            "### Sensi Speciali:\n\n"
            "• **Scurovisione (Darkvision)**: Permette di vedere nel buio entro un raggio specificato come se fosse luce fioca, e nella luce fioca come luce intensa. Nel buio si vede solo in sfumature di grigio (nessun colore).\n"
            "• **Vista Cieca (Blindsight)**: Permette di percepire l'ambiente circostante entro un dato raggio senza affidarsi alla vista (tramite ecolocalizzazione o altri sensi acuti).\n"
            "• **Vista Tremula (Tremorsense)**: Rileva e localizza l'origine delle vibrazioni nel terreno o nel pavimento entro un dato raggio.\n"
            "• **Vista Pura (Truesight)**: Permette di vedere nel buio normale e magico, vedere creature invisibili, scoprire illusioni e percepire il Piano Etereo."
        )
    },

    # =========================================================================
    # DMG - GUIDA DEL DUNGEON MASTER (DMG)
    # =========================================================================
    {
        "id": "dmg_traps",
        "manual": "DMG",
        "manual_name": "Guida del Dungeon Master (DMG)",
        "category": "Regole DM",
        "title": "Trappole & Rischi (Traps & Hazards)",
        "keywords": ["trappole", "trappola", "cd trappola", "danno trappola", "traps", "hazard"],
        "page_ref": "DMG p. 120",
        "summary": "Tabelle per CD di rilevamento, disarmo e danni delle trappole in base alla letalità.",
        "content": (
            "### Gradi di Severità delle Trappole (DMG p. 120-121):\n\n"
            "• **Inconveniente (Livelli 1-4)**: CD Tiro Salvezza 10-11 | Bonus Attacco +3 a +5 | Danni: **1d10** o **2d10**.\n"
            "• **Pericolosa (Livelli 5-10)**: CD Tiro Salvezza 12-15 | Bonus Attacco +6 a +8 | Danni: **4d10**.\n"
            "• **Mortale (Livelli 11-16)**: CD Tiro Salvezza 16-19 | Bonus Attacco +9 a +11 | Danni: **10d10**.\n"
            "• **Devastante (Livelli 17-20)**: CD Tiro Salvezza 20-21 | Bonus Attacco +12 o più | Danni: **18d10** o **24d10**.\n\n"
            "### Esempi Noti:\n"
            "• **Pozzo con Aculei**: CD 15 Percezione per notare le frasche. Danno 2d6 caduta + 2d10 perforante dagli aculei.\n"
            "• **Dardi Avvelenati**: Piastra a pressione CD 15 Indagare. Bonus +8 per colpire, 1d4 perforante + 2d10 veleno (TS Costituzione CD 15 dimezza)."
        )
    },
    {
        "id": "dmg_poisons",
        "manual": "DMG",
        "manual_name": "Guida del Dungeon Master (DMG)",
        "category": "Regole DM",
        "title": "Veleni & Tossicologia (Poisons)",
        "keywords": ["veleni", "veleno", "ingestione", "contatto", "inalazione", "poisons", "tossico"],
        "page_ref": "DMG p. 257",
        "summary": "I 4 metodi di somministrazione dei veleni e veleni celebri di D&D 5e.",
        "content": (
            "### Metodi di Somministrazione (DMG p. 257):\n\n"
            "• **Contatto (Contact)**: Il veleno agisce quando tocca la pelle nuda della creatura.\n"
            "• **Ingestione (Ingested)**: Il veleno deve essere inghiottito (mescolato a cibo o bevande).\n"
            "• **Inalazione (Inhaled)**: Soffiato o rilasciato come nube o polvere (chiunque respiri l'area ne subisce gli effetti).\n"
            "• **Ferita (Injury)**: Applicato su un'arma tagliente o perforante o munizione; agisce quando l'arma infligge danno.\n\n"
            "### Veleni Notabili:\n"
            "• **Sangue di Assassino (Ingestione - 120 MO)**: TS Costituzione CD 10. Fallimento: 1d12 danni da veleno e Avvelenato per 24 ore.\n"
            "• **Essenza d'Etere (Inalazione - 300 MO)**: TS Costituzione CD 15. Fallimento: Incosciente per 8 ore (si risveglia se subisce danni).\n"
            "• **Veleno di Viverna (Ferita - 1.200 MO)**: TS Costituzione CD 15. Fallimento: **7d6 danni da veleno**, successo dimezza."
        )
    },
    {
        "id": "dmg_attunement",
        "manual": "DMG",
        "manual_name": "Guida del Dungeon Master (DMG)",
        "category": "Oggetti Magici",
        "title": "Sintonizzazione con Oggetti Magici (Attunement)",
        "keywords": ["sintonizzazione", "attunement", "oggetti magici", "magic items", "rarita"],
        "page_ref": "DMG p. 136",
        "summary": "Regole per sintonizzarsi con oggetti magici potenti: limite di 3 oggetti e tempo richiesto.",
        "content": (
            "### Regole di Sintonizzazione (DMG p. 136-138):\n\n"
            "• **Limite Massimo**: Una creatura può essere sintonizzata con un **massimo di 3 oggetti magici contemporaneamente**.\n"
            "• **Procedura**: Per sintonizzarsi con un oggetto, il personaggio deve completare un **Riposo Breve** trascorso a concentrarsi e maneggiare esclusivamente quell'oggetto.\n"
            "• **Rottura della Sintonizzazione**: Si spezza se la creatura si allontana a più di 30 metri dall'oggetto per 24 ore, se la creatura muore, se un'altra persona si sintonizza con esso, o se la creatura trascorre un riposo breve a disconnettersi intenzionalmente."
        )
    },

    # =========================================================================
    # MM - MANUALE DEI MOSTRI (MM)
    # =========================================================================
    {
        "id": "mm_legendary_rules",
        "manual": "MM",
        "manual_name": "Manuale dei Mostri (MM)",
        "category": "Mostri",
        "title": "Azioni Leggendarie, Tana & Resistenza Leggendaria",
        "keywords": ["azioni leggendarie", "leggendarie", "tana", "resistenza leggendaria", "legendary", "lair"],
        "page_ref": "MM p. 11",
        "summary": "Meccaniche speciali per boss e mostri leggendari in combattimento.",
        "content": (
            "### Tratti Leggendari dei Mostri Boss (MM p. 11):\n\n"
            "• **Azioni Leggendarie (Legendary Actions)**:\n"
            "  - Un mostro possiede generalmente **3 Azioni Leggendarie per round**.\n"
            "  - Può compierne solo una alla volta, **al termine del turno di un'altra creatura**.\n"
            "  - Il mostro recupera tutte le azioni leggendarie spese all'inizio del proprio turno.\n\n"
            "• **Resistenza Leggendaria (Legendary Resistance - tipicamente 3/giorno)**:\n"
            "  - Se il mostro fallisce un Tiro Salvezza, può decidere volontariamente di superarlo invece.\n\n"
            "• **Azioni di Tana (Lair Actions)**:\n"
            "  - Quando combatte nella propria tana, il mostro agisce al punteggio di **Iniziativa 20** (perdendo i pareggi) scatenando effetti ambientali potenti (crolli, rampicanti, miasmi, fulmini)."
        )
    },

    # =========================================================================
    # XGtE & TCoE - ESPANSIONI REGOLE & ATTREZZI
    # =========================================================================
    {
        "id": "xgte_tools_proficiencies",
        "manual": "XGtE",
        "manual_name": "Guida di Xanathar a Tutto (XGtE)",
        "category": "Attrezzi & Regole",
        "title": "Uso Avanzato degli Attrezzi da Lavoro (Tools & Synergies)",
        "keywords": ["attrezzi", "arnesi da scasso", "fabbro", "alchimia", "erboristeria", "strumenti", "tools"],
        "page_ref": "XGtE p. 78",
        "summary": "Vantaggi e sinergie quando si combina la competenza in un attrezzo con una prova di abilità.",
        "content": (
            "### Sinergia Attrezzo + Abilità (XGtE p. 78):\n\n"
            "Se un personaggio possiede competenza sia nell'attrezzo che nell'abilità pertinente a una data prova, il DM può concedergli **Vantaggio** alla prova o un beneficio speciale.\n\n"
            "• **Arnesi da Scasso (Thieves' Tools)**: Sinergia con *Indagare* (identificare trappole) e *Furtività* (scassinare serrature senza fare rumore).\n"
            "• **Strumenti da Alchimista (Alchemist's Supplies)**: Sinergia con *Arcano* (identificare pozioni) e *Indagare* (analizzare sostanze e acidi chimici).\n"
            "• **Borsa da Erborista (Herbalism Kit)**: Sinergia con *Medicina* (stabilizzare e creare antitossine/pozioni di cura) e *Natura* (identificare piante magiche).\n"
            "• **Strumenti da Fabbro (Smith's Tools)**: Sinergia con *Atletica* (forzare porte corazzate) e *Storia* (riconoscere armi e manufatti storici)."
        )
    },
    {
        "id": "xgte_falling_rules",
        "manual": "XGtE",
        "manual_name": "Guida di Xanathar a Tutto (XGtE)",
        "category": "Regole Opzionali",
        "title": "Cadute su una Creatura & Sonno in Armatura",
        "keywords": ["caduta creatura", "dormire armatura", "sonno", "cadute", "falling", "sleep"],
        "page_ref": "XGtE p. 77",
        "summary": "Ripartizione dei danni quando si cade su una creatura e penalità per dormire in armatura media/pesante.",
        "content": (
            "### Caduta su un'Altra Creatura (XGtE p. 77):\n\n"
            "• Se una creatura cade su un'altra creatura, la creatura bersaglio deve superare un **Tiro Salvezza su Destrezza con CD 15** (a meno che non sia Incapacitata).\n"
            "• **Fallimento**: I danni da caduta vengono **divisi equamente** a metà tra la creatura che cade e la creatura colpita, ed entrambe cadono **Prone**.\n"
            "• **Successo**: La creatura bersaglio schiva il colpo e non subisce danni; chi cade subisce l'intero danno da caduta.\n\n"
            "### Dormire in Armatura Media o Pesante (XGtE p. 77):\n\n"
            "• Quando un personaggio completa un Riposo Lungo indossando un'armatura media o pesante, recupera solo **un quarto (1/4)** dei propri Dadi Vita totali (invece della metà) e il riposo **non riduce** alcun livello di Sfinimento."
        )
    }
]


class ManualsManager:
    """Gestisce la collezione dei manuali, la ricerca full-text, e l'integrazione con file custom e API."""
    
    def __init__(self):
        self.manuals_dir = MANUALS_DIR
        os.makedirs(self.manuals_dir, exist_ok=True)
        self.rules: List[Dict] = list(CORE_MANUALS_DATA)
        self.load_custom_manuals()
        self.load_pdf_manuals()
        
    def load_pdf_manuals(self):
        """Carica le voci indicizzate dai manuali PDF in 'manuals_pdf/'."""
        try:
            from common.pdf_manuals_indexer import PDFManualsIndexer
            self.pdf_indexer = PDFManualsIndexer()
            pdf_entries = self.pdf_indexer.get_all_entries()
            if pdf_entries:
                self.rules.extend(pdf_entries)
            elif not self.pdf_indexer.is_cache_valid() and self.pdf_indexer.get_pdf_files():
                self.pdf_indexer.reindex_async(on_done_callback=self._on_pdf_indexing_done)
        except Exception as e:
            print(f"[MANUALS] Errore caricamento manuali PDF: {e}")

    def _on_pdf_indexing_done(self, count: int):
        """Callback eseguito al termine dell'indicizzazione in background."""
        print(f"[MANUALS] Indicizzazione PDF completata in background: {count} voci aggiunte.")
        if hasattr(self, 'pdf_indexer'):
            new_entries = self.pdf_indexer.get_all_entries()
            self.rules = [r for r in self.rules if not str(r.get("id", "")).startswith("pdf_")]
            self.rules.extend(new_entries)

    def load_custom_manuals(self):
        """Scansiona la cartella 'manuals/' e carica documenti Markdown, TXT e JSON personalizzati."""
        if not os.path.exists(self.manuals_dir):
            return

        # Carica file .json
        for jpath in glob.glob(os.path.join(self.manuals_dir, "*.json")):
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    base_name = os.path.splitext(os.path.basename(jpath))[0]
                    if isinstance(data, list):
                        for idx, entry in enumerate(data):
                            if isinstance(entry, dict) and "title" in entry:
                                entry.setdefault("manual", "Custom")
                                entry.setdefault("manual_name", f"Manuale Custom ({base_name})")
                                entry.setdefault("category", "Custom")
                                entry.setdefault("page_ref", f"{base_name} #{idx+1}")
                                entry.setdefault("id", f"custom_{base_name}_{idx}")
                                self.rules.append(entry)
            except Exception as e:
                print(f"[MANUALS] Errore lettura JSON custom {jpath}: {e}")

        # Carica file .md e .txt
        for mdpath in glob.glob(os.path.join(self.manuals_dir, "*.md")) + glob.glob(os.path.join(self.manuals_dir, "*.txt")):
            try:
                base_name = os.path.splitext(os.path.basename(mdpath))[0]
                with open(mdpath, "r", encoding="utf-8") as f:
                    text = f.read()

                # Dividi per sezioni '# ' o '## '
                sections = re.split(r'\n(?=#{1,3}\s+)', text)
                for s_idx, sec in enumerate(sections):
                    sec = sec.strip()
                    if not sec: continue
                    lines = sec.split("\n", 1)
                    title_line = lines[0].lstrip("#").strip()
                    body = lines[1].strip() if len(lines) > 1 else title_line
                    
                    self.rules.append({
                        "id": f"custom_md_{base_name}_{s_idx}",
                        "manual": "Custom",
                        "manual_name": f"Manuale Custom ({base_name})",
                        "category": "Homebrew / Appunti",
                        "title": title_line,
                        "keywords": [title_line.lower(), base_name.lower()],
                        "page_ref": f"{base_name}.md",
                        "summary": body[:120] + "..." if len(body) > 120 else body,
                        "content": sec
                    })
            except Exception as e:
                print(f"[MANUALS] Errore lettura MD custom {mdpath}: {e}")

    def get_manual_categories(self, manual_filter: Optional[str] = None) -> List[str]:
        """Restituisce le categorie disponibili per un manuale specifico o per tutti."""
        cats = set()
        for r in self.rules:
            if not manual_filter or manual_filter == "Tutti" or r.get("manual") == manual_filter:
                cats.add(r.get("category", "Generale"))
        return sorted(list(cats))

    def get_available_manuals(self) -> List[Tuple[str, str]]:
        """Restituisce lista di (codice, nome esteso)."""
        seen = {}
        for r in self.rules:
            code = r.get("manual", "Altro")
            name = r.get("manual_name", code)
            if code not in seen:
                seen[code] = name
        return [("Tutti", "Tutti i Manuali")] + sorted(seen.items())

    def search(self, query: str = "", manual_filter: Optional[str] = None, category_filter: Optional[str] = None) -> List[Dict]:
        """Cerca tra le regole del compendio con punteggio di rilevanza."""
        query = query.strip().lower()
        results = []

        for r in self.rules:
            # Filtro manuale
            if manual_filter and manual_filter != "Tutti" and r.get("manual") != manual_filter:
                continue
            # Filtro categoria
            if category_filter and category_filter != "Tutte" and r.get("category") != category_filter:
                continue

            score = 0
            if not query:
                results.append((10, r))
                continue

            title = r.get("title", "").lower()
            keywords = [k.lower() for k in r.get("keywords", [])]
            content = r.get("content", "").lower()
            summary = r.get("summary", "").lower()

            if query == title:
                score += 100
            elif query in title:
                score += 50
            elif any(query == kw for kw in keywords):
                score += 40
            elif any(query in kw for kw in keywords):
                score += 25
            elif query in summary:
                score += 15
            elif query in content:
                score += 5

            # Multi-word match
            tokens = query.split()
            if len(tokens) > 1:
                token_matches = sum(1 for t in tokens if t in title or any(t in kw for kw in keywords) or t in content)
                score += token_matches * 10

            if score > 0:
                results.append((score, r))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in results]

    def quick_lookup(self, query: str) -> Optional[Dict]:
        """Trova la migliore corrispondenza per un comando chat o tooltip."""
        res = self.search(query)
        if res:
            return res[0]
        return None

    def query_online_srd_rule(self, rule_name: str) -> Optional[Dict]:
        """Cerca una regola specifica dall'API ufficiale dnd5eapi.co."""
        clean_idx = re.sub(r'[^a-zA-Z0-9]+', '-', rule_name.strip().lower())
        try:
            url = f"https://www.dnd5eapi.co/api/2014/rules/{clean_idx}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return {
                    "id": f"srd_online_{clean_idx}",
                    "manual": "SRD",
                    "manual_name": "5e SRD Online (dnd5eapi.co)",
                    "category": "Regole SRD",
                    "title": data.get("name", rule_name.title()),
                    "page_ref": "5e SRD v5.1",
                    "summary": (data.get("desc") or "")[:150] + "...",
                    "content": data.get("desc", "Nessuna descrizione disponibile.")
                }
        except Exception:
            return None

