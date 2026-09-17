# 5. Tipi, prove e guardie: chi controlla che cosa

> Il principio in una riga: **ogni regola che conta ha un controllo che la fa rispettare, e ogni
> controllo è stato visto fallire almeno una volta.**

## Tre controlli, tre domande diverse

| Comando | Che cosa domanda | Quanto ci mette | Serve Docker |
|---|---|---|---|
| `make app-test` | il comportamento è quello previsto? | centesimi di secondo | no |
| `make app-check` | i tipi tengono, e le porte sono rispettate? | qualche secondo | no |
| `make app-test-integration` | funziona contro MongoDB vero? | minuti | **sì** |

Sono tre domande distinte, e nessuna copre le altre. Le prime due si eseguono a ogni salvataggio;
la terza si chiede per nome.

## `mypy --strict` non è un accessorio

Nella maggior parte dei progetti Python il controllo dei tipi è una rete di sicurezza opzionale.
Qui è **strutturale**, per una ragione precisa: le porte del dominio sono `Protocol`, e la
conformità strutturale non si vede a occhio.

Un doppio con una firma sbagliata non protesta quando lo si scrive. A runtime `isinstance` lo
accetta — l'ho misurato, [M-004](Sources.md#m-004) — perché il controllo guarda i nomi e non le
firme. Il primo segnale arriverebbe da una prova che fallisce per un motivo che sembra un altro, in
un punto lontano da dove sta l'errore.

Mypy è l'unico che guarda le firme, e lo dice lui stesso: «`isinstance()` with protocols is not
completely safe at runtime. For example, signatures of methods are not checked»
([A-003](Sources.md#a-003)). Senza `make app-check`, `Protocol` sarebbe documentazione.

La configurazione sta in `app/pyproject.toml`:

```toml
[tool.mypy]
strict = true
files = ["src", "tests"]
```

`files` include `tests` deliberatamente. Le prove sono il posto in cui i doppi vengono dichiarati
conformi alle porte, e lasciarle fuori dal controllo significherebbe non controllare proprio la cosa
per cui il controllo esiste.

Dal Task 4 questo vale anche per `tests/doppi/`, che è codice a tutti gli effetti — cinque
implementazioni delle porte — ma non contiene prove. Le due configurazioni lo trattano ciascuna a
modo suo, e va bene così: mypy lo controlla perché sta sotto `tests`, pytest non lo raccoglie perché
`testpaths` nomina `tests/unit`. Un doppio è un attrezzo di misura: si tara con `mypy` e con le
prove che lo riguardano, non lo si esegue da solo.

## Le due suite, e perché sono separate

`app/pyproject.toml` dichiara:

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
```

**`tests/unit`, non `tests`.** È una riga sola e decide molto. Con `testpaths = ["tests"]`, dal
momento in cui esisterà la prima prova di integrazione (Task 8), `make app-test` comincerebbe a
richiedere Docker — senza che nessuno l'abbia deciso, e senza che nessuno se ne accorgesse subito.
La suite veloce smetterebbe di essere veloce per accumulo, che è il modo in cui le suite veloci
muoiono.

L'integrazione si chiede per nome: `make app-test-integration`.

## Il codice d'uscita 5, tradotto invece che nascosto

Finché `tests/integration/` è vuota — le prove arrivano al Task 8 — pytest esce **5**, che secondo
la sua documentazione significa «No tests collected» ([A-004](Sources.md#a-004)) e qui è stato
verificato sulla versione installata ([M-005](Sources.md#m-005)).

Non è un errore e non è un successo. Ci sono tre modi di trattarlo, e due sono sbagliati:

- **lasciarlo passare come fallimento** manda a cercare Docker chi non ha ancora niente da eseguire;
- **sopprimerlo con `|| true`** insegna che il verde di quel bersaglio non vuol dire niente, e
  l'insegnamento sopravvive al Task 8, quando le prove ci saranno davvero;
- **tradurlo** — intercettare *quel* codice e stampare la frase che spiega perché — è ciò che fa il
  `Makefile`.

```make
app-test-integration:
	@uv run --directory app pytest -q tests/integration; esito=$$?; \
	if [ $$esito -eq 5 ]; then \
		echo "Nessuna prova di integrazione: arrivano al Task 8 del piano."; \
	else \
		exit $$esito; \
	fi
```

È la nota di metodo 143 del [registro operativo](../../docs/registro-operativo-sviluppo.md), ed è il
rovescio della 135: lì c'era il messaggio senza il codice, qui il codice senza il messaggio.

## Le prove di integrazione usano gli stack veri

La scelta naturale sarebbe `testcontainers-python`, e all'inizio del progetto lo era: c'era un ADR
che la prescriveva. È stata rovesciata dopo aver letto la libreria
([ADR-0020](../../docs/Decision.md#adr-0020) sostituisce ADR-0011).

`MongoDbContainer` avvia un'istanza **standalone** e non conosce i replica set: il modulo non nomina
mai «replica», «replSet» o «rs.initiate» ([S-013](../../docs/Sources.md#s-013)). Per una demo che
esiste per mostrare un failover, è il pezzo che manca. La classe `DockerCompose` della stessa
libreria esiste nel codice ma non compare nella documentazione pubblicata: dipenderne significherebbe
appoggiarsi a un'API non documentata per ottenere ciò che `docker compose` fa già.

Le prove di integrazione avviano quindi gli stack Compose **del repository**, con `make up-0X`, e ci
girano contro. Il guadagno non è una dipendenza in meno: è che le prove verificano **l'artefatto che
il pubblico eseguirà davvero**, non un facsimile costruito da una libreria.

## La guardia architetturale

`app/tests/unit/test_scheletro.py` contiene un controllo che non riguarda il comportamento ma la
**forma** del progetto: percorre i sorgenti di `domain/` e `application/` con il modulo `ast`,
raccoglie ogni nome importato e boccia tutto ciò che non sia libreria standard o il pacchetto stesso.

```python
def estranei(sorgente: str) -> set[str]:
    ammessi = sys.stdlib_module_names | {PACCHETTO}
    return moduli_importati(sorgente) - ammessi
```

Perché `ast` e non un `grep`: la ricerca testuale non distingue un import vero da uno dentro una
stringa o un commento, e non vede `__import__("pymongo")`. L'albero sintattico è quello che
l'interprete vede.

La guardia porta anche una difesa contro se stessa: asserisce di aver esaminato almeno tanti moduli
quanti sono gli strati sorvegliati. Senza, il giorno in cui una directory venisse rinominata la
prova continuerebbe a passare **guardando il vuoto**.

## Ogni guardia è stata vista fallire

Questa è la disciplina che il repository applica, e che ha un nome: **nota di metodo 142** — un
controllo scritto quando non può fallire va rotto apposta, subito.

La ragione è che una guardia architetturale nasce davanti a un albero vuoto. Il suo primo verde non
distingue «tutto a posto» da «non c'era niente da guardare», e la differenza si scopre mesi dopo,
quando serviva. Costa trenta secondi introdurre la violazione, vedere il messaggio e toglierla — e
quei trenta secondi verificano due cose: che il controllo scatti, e che quando scatta dica **dove**.

Gli esperimenti fatti finora, con l'esito:

| Guardia | Violazione introdotta | Esito |
|---|---|---|
| import estranei nel dominio | `import pymongo` in `domain/__init__.py` | fallisce: «`domain/__init__.py` importa `['pymongo']`» |
| la guardia guarda il vuoto | — | coperta da un'asserzione sul numero di moduli esaminati |
| eventi tutti congelati | un evento in più `@dataclass` senza `frozen` | **la classe non nasce** ([M-002](Sources.md#m-002)) |
| eventi tutti slottati | un evento in più `frozen=True` senza `slots=True` | fallisce, nominando la classe |
| la base congelata e slottata | tolto `slots=True` a `Evento` | fallisce su due prove |

### Fare una tornata di rotture: tre trappole dell'arnese

Rompere una cosa alla volta e pretendere che una prova **nominata in anticipo** diventi rossa è il
modo più economico di misurare la differenza fra «le prove che ci sono passano» e «le prove che
servono esistono». Lo script che lo fa è di venti righe, si scrive ogni volta da capo, e ogni volta
inciampa negli stessi tre posti. Stanno scritti qui perché è qui che li si rilegge — un registro
ricorda a chi lo apre, e chi scrive venti righe di utilità non lo apre.

**Il codice d'uscita di `pytest` non è un booleano.** Esce **4** su errore d'uso e **5** quando non
ha raccolto nessuna prova: un nome di prova scritto male produce «diverso da zero», che uno script
ingenuo legge come «la mutazione è stata vista». Il rapporto risulta perfetto, ed è perfetto perché
non ha eseguito niente. Il segnale è sempre lo stesso — **un rapporto troppo pulito**.

**Due modifiche della stessa lunghezza nello stesso secondo sono la stessa modifica.** Python decide
se ricompilare confrontando data di modifica **al secondo** e dimensione **in byte**; il contenuto
non lo guarda. Sostituire `1024**2` con `1000**2` non cambia né l'una né l'altra, e la corsa esegue
il bytecode di quella prima. `PYTHONDONTWRITEBYTECODE=1` nell'ambiente dei sottoprocessi, e
`__pycache__` cancellati prima di cominciare.

**Una mutazione che resta verde non è sempre una prova che manca.** Può essere una riscrittura
**equivalente** sotto un invariante che il codice attorno garantisce già. Prima di aggiungere una
guardia si verifica l'invariante alla fonte; se c'è, la mutazione non era una rottura e va tolta
dall'elenco invece che coperta.

## Il terzo esito

La riga in grassetto nella tabella è quella che ha insegnato qualcosa di nuovo.

Rompere una guardia apposta ha **tre** esiti, non due: il controllo scatta e va bene; il controllo
tace e va corretto; oppure **la violazione non è costruibile**, perché il linguaggio la vieta prima.

Il terzo è il più facile da leggere male, perché somiglia al primo — entrambi finiscono con la suite
verde. La differenza è che nel terzo caso l'asserzione è decorazione: controlla il compilatore, e
chi la legge crede che stia sorvegliando qualcosa che invece nessuno può violare.

Va tolta, e va tolta **nominando l'esperimento** che l'ha dimostrata superflua — senza, il prossimo
lettore la riaggiunge in buona fede. Quel che resta è la sola proprietà che può ancora perdersi, e
su quella la guardia va vista fallire davvero.

È la nota di metodo 144.

## Un limite scritto come prova verde

L'ultima tecnica vale la pena isolarla, perché è controintuitiva.

Che `isinstance` contro un `Protocol` guardi i nomi e non le firme è un limite noto. Scritto in un
commento, invecchia senza dirlo. Scritto come **prova che passa** — un oggetto con la firma
sbagliata che *supera* il controllo, e l'asserzione che dice proprio questo — diventa due cose
insieme: documentazione che il lettore incontra dove serve, e sentinella che fallirebbe il giorno in
cui il comportamento cambiasse.

Costa una prova verde in più. È la nota di metodo 145, e la si paga volentieri: è l'unico modo
perché un buco conosciuto resti conosciuto anche quando chi lo conosceva non c'è più.

## Niente integrazione continua

Non c'è CI, ed è una scelta. Il repository deve funzionare **offline**
([ADR-0009](../../docs/Decision.md#adr-0009)), su un portatile, in una sala in cui la rete potrebbe
non esserci. I controlli sono comandi `make` che chiunque esegue in locale, e il loro esito è
verificabile senza dipendere da un servizio esterno.

Il rovescio è che nessuno li esegue al posto tuo. Per questo il piano prescrive `mypy --strict`
verde **a ogni commit**, e non alla fine.

---

**Torna a:** [README.md](README.md) per l'indice, oppure
[registro-sviluppo-app.md](registro-sviluppo-app.md) per la cronaca di come tutto questo è stato
costruito.

**Fonti:** [A-003](Sources.md#a-003), [A-004](Sources.md#a-004), [M-002](Sources.md#m-002),
[M-004](Sources.md#m-004), [M-005](Sources.md#m-005), [S-013](../../docs/Sources.md#s-013).
**Decisioni:** [ADR-0009](../../docs/Decision.md#adr-0009),
[ADR-0020](../../docs/Decision.md#adr-0020).
