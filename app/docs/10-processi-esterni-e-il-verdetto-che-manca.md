# 10. Un processo esterno, e il verdetto che manca

> Il principio in una riga: **quando l'adattatore non chiama una funzione ma lancia un processo, il
> verdetto è un numero intero che decide qualcun altro — e se quel numero mente, l'adattatore è il
> posto in cui si ripara.**

Tutti gli adattatori visti fino al [capitolo 9](09-adattatori-veri-e-contratto-condiviso.md) parlano
con una libreria. `PymongoStore` riceve una `Collection`, chiama un metodo, ottiene un valore di
ritorno o un'eccezione: il confine fra l'applicazione e MongoDB è una chiamata di funzione, e Python
si occupa di tutto il resto.

`SubprocessBackup` è il primo adattatore che attraversa un confine di **sistema operativo**. Dall'
altra parte non c'è una libreria: c'è `mongodump`, un programma scritto in Go che parla soltanto tre
lingue — gli argomenti con cui lo si lancia, il testo che scrive, e l'intero con cui muore. Tre
lingue povere, e ognuna delle tre nasconde una trappola che questo capitolo racconta.

---

## Quattro cose che cambiano, e vengono tutte dalla stessa

| Con una libreria | Con un processo |
|---|---|
| la credenziale è un argomento di funzione | la credenziale attraversa il confine del sistema operativo, e da qualche parte deve passare |
| l'avanzamento è un valore di ritorno | l'avanzamento è **testo**, da riconoscere riga per riga |
| l'errore è un'eccezione tipizzata | l'errore è un intero, più eventualmente del testo che lo spiega |
| l'oggetto muore quando lo lascia il garbage collector | il processo **sopravvive** a chi lo ha lanciato, se nessuno lo ferma |

Le quattro righe della colonna di destra sono le quattro sezioni centrali di questo capitolo. Non è
una coincidenza: sono la stessa cosa vista quattro volte, cioè che un processo è un'entità
indipendente e non un pezzo del nostro programma.

---

## L'iteratore che è già partito

La porta lo diceva dal Task 4:

```python
class BackupTool(Protocol):
    def dump(self, destinazione: Path) -> Iterator[Progress]: ...
```

`Iterator[Progress]`, non `list[Progress]`, ed è il Passo 1 del piano: l'avanzamento **si consuma
man mano**. È ciò che permette all'Atto III del Blocco 2 di mostrare, sulla stessa schermata, la
barra del dump che avanza e il throughput delle scritture che *non* crolla. Con una lista, la
schermata resterebbe ferma per tutta la durata del dump e poi mostrerebbe la storia di qualcosa che
è già finito.

C'è però una seconda proprietà, meno ovvia, e il doppio del Task 4 l'aveva già congelata. Dalla
docstring di `FakeBackup`:

> `dump` **non è una funzione generatrice, ed è deliberato.**

Se `dump` fosse scritta con un `yield` dentro, chiamarla non eseguirebbe **niente**: Python
restituirebbe un generatore sospeso alla prima riga, e `mongodump` partirebbe solo al primo `next()`.
Il codice che fa

```python
avanzamenti = strumento.dump(destinazione)   # qui il dump è già in corso
...                                           # qualcos'altro
for progresso in avanzamenti:                 # e qui si comincia a leggerlo
    ...
```

sarebbe corretto in un caso e sbagliato nell'altro, con la stessa identica forma. Peggio: sarebbe
sbagliato in modo **silenzioso**, perché un eseguibile che non esiste solleverebbe `FileNotFoundError`
non dove è stato chiesto il dump, ma molto più in là, dentro il ciclo che disegna la schermata.

Per questo `dump` è una funzione normale che *ritorna* l'iteratore prodotto da un'altra:

```python
def dump(self, destinazione: Path) -> Iterator[Progress]:
    argomenti = [...]
    return self._avanzamento(self._avvia(argomenti), self._comando_dump[-1])
```

`_avvia` lancia il processo e scrive la password; `_avanzamento` è la funzione generatrice. Quando
`dump` ritorna, il processo esiste già. La prova che difende questa distinzione chiede un dump con
un eseguibile inesistente e pretende `FileNotFoundError` **senza iterare niente** — ed è una delle
sei mutazioni che l'adattatore ha subìto per verifica: trasformare quel `return` in `yield from`
rende la prova rossa.

---

## Il comando arriva dal costruttore, e non è un dettaglio di comodo

`SubprocessBackup` non sa come si raggiunge `mongodump`. Lo riceve:

```python
SubprocessBackup(
    host="rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017",
    comando_dump=("docker", "exec", "-i", "mongo-rs-1", "mongodump"),
    ...
)
```

È la stessa scelta che fa arrivare a `PymongoStore` una `Collection` già fatta invece di una stringa
di connessione: **questo oggetto non ha una politica di esecuzione**. Dall'host di chi sviluppa,
dove `mongodump` non è installato, il comando passa per `docker exec`; dall'interno della rete
Compose, al Task 12, sarà `("mongodump",)` e basta.

Se la politica stesse dentro l'adattatore, l'applicazione containerizzata di
[ADR-0012](../../docs/Decision.md#adr-0012) si porterebbe dietro una **dipendenza dal socket Docker**
— cioè il permesso di comandare il demone che fa girare tutto il laboratorio — per fare una cosa,
un dump, che dal suo container sa già fare da sé. Un adattatore che decide come raggiungere lo
strumento decide anche, senza volerlo, quali privilegi servono per usarlo.

Nel prefisso di prova il `-i` non è decorativo: senza, `docker exec` non collega lo `stdin` del
client al processo dentro il container, e la sezione che viene dopo smette di funzionare.

---

## La password: il piano aveva ragione sulla regola e torto sul motivo

Il Passo 2 del piano del Task 9 dice:

> Il processo esterno si lancia con gli argomenti in **lista**, mai con una stringa di shell: la
> password dell'amministratore è uno degli argomenti, e una stringa di shell la fa comparire nella
> tabella dei processi di chiunque guardi.

La regola è giusta. Il motivo, misurato, è **incompleto**. Con `-p <valore>` come elemento della
lista — nessuna shell coinvolta — dentro il container:

```
mongorestore --host rs0/mongo-rs-1:27017,... --username admin
--authenticationDatabase admin -p <PASSWORD> --nsInclude lab.* ...
```

Sedici campioni su sedici, presi a 50 ms l'uno dall'altro con un banale `ps -eo args`
([M-025](Sources.md#m-025)). La tabella dei processi legge `argv`, e ad `argv` non importa da dove è
arrivato: lista o stringa di shell, il risultato è lo stesso. Chiunque abbia un `exec` su quel
container, per tutti i secondi in cui il dump gira, legge la password dell'amministratore.

Quello che funziona è **non mettercela**. Omesso `-p`, gli strumenti chiedono la password e la
leggono dallo `stdin` — anche quando lo `stdin` non è un terminale ([M-023](Sources.md#m-023)):

```
2026-09-03T12:41:52.688+0000	reading password from standard input
Enter password for mongo user:
```

L'adattatore la scrive, chiude il tubo, e il segreto non compare in nessun `argv` di nessun
processo:

```python
def _autenticazione(self) -> list[str]:
    """Utente e database di autenticazione, e **mai** la password."""
    if self._utente is None:
        return []
    return ["--username", self._utente,
            "--authenticationDatabase", self._database_autenticazione]
```

La lista resta comunque la scelta giusta, per la ragione che il piano non nomina: senza shell non
c'è nessuno a interpretare uno spazio, un apice o un `$` dentro una password o dentro un percorso.
Ma la cosa che protegge il segreto è un'altra, e prima di misurare non si sapeva quale delle due
fosse.

Una prova di integrazione guarda la tabella dei processi del container mentre `mongorestore` gira e
pretende di **non** trovare il segreto. La classe che campiona espone due booleani e un contatore,
e mai il testo campionato: una prova che maneggia la password per verificare che non si veda è una
prova che la fa vedere il giorno in cui fallisce.

---

## Tutto quello che dicono lo dicono su `stderr`

Misurato per entrambi gli strumenti: `stdout` resta **vuoto**, zero righe. Tutto — il prompt, le
righe di avanzamento, le barre, il sommario, gli errori — esce da `stderr`.

Qui `stdout` va a `DEVNULL` apposta, e la ragione non è che non serva:

```python
processo = subprocess.Popen(
    list(argomenti),
    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
)
```

Un tubo che nessuno svuota si riempie, e un processo che scrive in un tubo pieno si ferma per
sempre. Chiedere un `PIPE` per `stdout` e poi leggere solo `stderr` è il modo canonico di far
bloccare un figlio a metà, e il blocco arriverebbe **solo** su un output abbastanza grande da
riempire il buffer del sistema operativo — cioè mai in prova, e forse in scena. Buttarlo via è
l'unica scelta che non può bloccarsi, e non si perde niente perché non ci passa niente.

---

## Riconoscere l'avanzamento, e l'unità che non c'è

`leggi_avanzamento` prende una riga e restituisce un `Progress` o `None`. Le forme che riconosce
sono sei, e sono tutte state osservate contro gli strumenti veri prima di essere scritte:

| Riga | Diventa |
|---|---|
| `writing \`lab.ordini\` to \`/tmp/...\`` | fase `lab.ordini`, zero completati, nessun totale |
| `[####....]  lab.ordini  1863086/2000000  (93.2%)` | fase `lab.ordini`, 1 863 086 su 2 000 000 |
| `done dumping \`lab.ordini\` (50000 documents)` | fase `lab.ordini`, 50 000 su 50 000 |
| `writing captured oplog to \`\`` | fase `oplog` |
| `dumped 1 oplog entry` | fase `oplog`, 1 su 1 — al singolare, che è la forma vera |
| `finished restoring \`dest.ordini\` (400000 documents, 0 failures)` | fase `dest.ordini` |

Tutto il resto — il prompt, `preparing collections to restore from`, `don't know what to do with
file prelude.json`, le cinquantamila righe di `continuing through error` — è rumore, e diventa
`None`. Una prova parametrica gliele passa tutte e pretende `None` da ognuna.

Due dettagli che si vedono solo misurando. Il prefisso dell'orario apre *quasi* ogni riga: il prompt
della password no, perché non è un messaggio di log ma il testo scritto sul terminale che non c'è —
ed è la ragione per cui il riconoscitore, che quel prefisso lo pretende, scarta il prompt senza
doverlo nominare. E il `MB` delle barre di `mongorestore` vale **1024²**, verificato mettendo la
barra accanto alla dimensione vera del file: `6094260` byte annunciati come `5.81MB`
([M-026](Sources.md#m-026)).

### Un inconveniente dichiarato: `completati` non porta con sé l'unità

Le barre dei due strumenti contano cose diverse. `mongodump` conta **documenti**; `mongorestore`
conta **byte**. `Progress` ha un solo campo `completati`, e non ha un campo per l'unità.

Non è una svista: `Progress` è nel dominio, è congelato dal Task 2, e cambiarlo per accomodare una
particolarità di due strumenti esterni significherebbe far entrare `mongorestore` dentro
`domain/modelli.py`. La conseguenza pratica è piccola — la percentuale è giusta in entrambi i casi,
ed è quella che la barra disegna — ma va scritta: chi legge `completati` deve sapere da quale
operazione arriva. Il punto resta aperto, e si chiude al Task 10 se la TUI avrà bisogno di
stampare il numero e non solo la percentuale.

---

## Il verdetto, e il verdetto che manca

Un'uscita diversa da zero diventa un'eccezione con il codice e il messaggio, non un iteratore che
finisce in silenzio:

```python
codice = processo.wait()
if codice != 0:
    raise ComandoFallito(eseguibile, codice, motivo)
```

Questo è il Passo 3, ed è [ADR-0077](../../docs/Decision.md#adr-0077): un avviso che non cambia il
codice d'uscita è un avviso che nessuno legge. Il `motivo` è l'ultima riga `Failed: ...` vista
passare, perché l'errore vero di `mongodump` arriva lì e non nel codice d'uscita, che dice solo
«qualcosa è andato storto».

E poi c'è il caso che il piano non prevedeva, perché nessuno lo prevede finché non lo esegue.

### `mongorestore` ha perso cinquantamila documenti ed è uscito **zero**

```
2026-09-03T12:42:04.982+0000	finished restoring `mongolab_prove_m9.ordini` (0 documents, 50000 failures)
2026-09-03T12:42:04.982+0000	0 document(s) restored successfully. 50000 document(s) failed to restore.
```

Codice d'uscita: **0** ([M-024](Sources.md#m-024)). Lo strumento sa di aver perso tutto, lo scrive,
e poi dichiara successo al sistema operativo. Chi controlla il processo nel modo in cui si controlla
un processo — guardando l'intero che restituisce — riceve «riuscito».

Non è un caso limite costruito per l'occasione. È quello che succede ogni volta che un restore
ricade su documenti il cui `_id` esiste già: `mongorestore` **inserisce**, non fonde, e il secondo
giro sulla stessa destinazione collide su tutto.

L'adattatore legge la riga di sommario e, quando i falliti sono più di zero, solleva
`RestoreIncompleto` con i due conteggi. Mette cioè il verdetto che lo strumento non ha messo, ed è
[ADR-0084](../../docs/Decision.md#adr-0084), che estende ADR-0077: la regola valeva per gli avvisi
che scriviamo noi, e l'aggiunta è che quando lo strumento di qualcun altro commette lo stesso
errore, l'adattatore che lo incapsula è il posto in cui si ripara.

Tre cose che `RestoreIncompleto` **non** è. Non sostituisce il codice d'uscita: un'uscita diversa da
zero resta `ComandoFallito` e ha la precedenza. Non annulla niente: i documenti già entrati restano
dentro, e l'eccezione racconta l'accaduto senza disfarlo. Non è una politica sul numero atteso:
l'adattatore non sa quanti dovessero essere, sa solo che lo strumento ne ha dichiarati alcuni persi.

### Come questa guardia è stata scoperta

Non progettandola. Le prime due prove di integrazione sul restore davano per **idempotente** un
restore ripetuto — c'era scritto nella docstring di una di loro, come premessa ovvia. Eseguite,
l'adattatore ha sollevato:

```
RestoreIncompleto: mongorestore è uscito con codice 0 dopo aver ripristinato 0 documenti
e averne persi 100000
```

Il codice di produzione ha bocciato un'affermazione della prova, e l'affermazione era la parte
sbagliata. Le due prove sono state riscritte su destinazioni fresche, la frase falsa è stata tolta,
e il caso è diventato una prova sua — quella che oggi difende ADR-0084 contro lo strumento vero.

---

## L'iteratore abbandonato, e un limite che va detto

Un processo sopravvive a chi lo ha lanciato. Se la TUI smette di leggere l'avanzamento — perché
l'operatore chiude la schermata, o perché un'altra eccezione ha interrotto il ciclo — `mongodump`
continuerebbe a girare, con nessuno a svuotargli `stderr`, fino a fermarsi in un tubo pieno.

```python
except GeneratorExit:
    processo.kill()
    processo.wait()
    raise
```

Chiudere l'iteratore uccide il processo e ne raccoglie il cadavere. `wait()` dopo `kill()` non è
zelo: senza, resta uno zombie nella tabella dei processi.

**Il limite, dichiarato.** Quando il comando è `("docker", "exec", ...)`, ciò che viene ucciso è il
**client** `docker`, non `mongodump` dentro il container. Un dump abbandonato dall'host continua
fino alla fine per conto suo. Non è un difetto dell'adattatore — è la conseguenza di non avere una
politica di esecuzione, che è esattamente la proprietà che lo rende containerizzabile al Task 12,
dove il problema sparisce perché non c'è più nessun `docker exec` in mezzo. Nel frattempo va saputo,
e sta scritto accanto al `kill`.

---

## Le prove: un eseguibile vero al posto di un mock

Le prove unitarie di questo adattatore non contengono un `Mock` di `subprocess`, e non è purismo.
Metà di ciò che l'adattatore deve garantire — che il figlio parta alla chiamata, che la password non
finisca fra i suoi argomenti, che l'iteratore abbandonato non lasci un processo orfano — riguarda
proprio il confine col sistema operativo, cioè esattamente la parte che un mock sostituirebbe con la
propria opinione. Un mock che dicesse «sì, ho ricevuto `kill`» non dimostrerebbe che il processo è
morto.

Al posto di `mongodump` c'è un programma Python di sei righe che scrive il proprio pid e i propri
argomenti in un diario, legge lo `stdin`, stampa su `stderr` le righe che la prova gli detta ed esce
col codice che la prova gli detta. Un eseguibile vero, che si comporta come lo strumento vero perché
la prova gli ha detto come — e le righe dettate sono **le righe misurate**, non righe inventate che
somigliano a quelle vere.

Il pid nel diario è ciò che permette alla prova sulla chiusura di essere una prova: dopo
`avanzamenti.close()` chiede al sistema operativo se quel pid è ancora vivo, e non a un mock se ha
ricevuto una chiamata.

### Sei mutazioni, e la sesta che nessuno vedeva

L'adattatore è stato rotto sei volte di seguito, una alla volta, per verificare che una prova
precisa se ne accorgesse: la password rimessa in `argv`, il sommario ridotto ad avviso, `dump`
trasformata in funzione generatrice, il `kill` tolto, il codice d'uscita ignorato, la base 1024
cambiata in 1000.

Cinque sono diventate rosse subito. La sesta — la base — è rimasta **verde**: l'unica prova sulle
barre usava il formato senza unità di `mongodump`, dove il moltiplicatore non entra mai in gioco.
Da lì sono nate due prove sulle barre del restore, e una di loro giudica contro la dimensione vera
del file misurata con `stat` ([M-026](Sources.md#m-026)) invece che contro un `1024**2` riscritto
nella prova: altrimenti avrebbe verificato che due copie della stessa scelta coincidono, che non è
una verifica.

---

## Che cosa questo capitolo lascia aperto

**Il formato del testo è un'interfaccia che nessuno ha promesso.** La riga di sommario, le barre, i
messaggi di apertura e chiusura sono testo della versione **100.18.0**. Se una versione futura li
riscrive, l'adattatore non diventa sbagliato: diventa **muto**, che è peggio, perché smette di
riconoscere l'avanzamento e — nel caso del sommario — smette di sollevare. La difesa è la suite di
integrazione, che esegue gli strumenti veri e diventa rossa il giorno in cui il formato cambia. Le
prove unitarie, da sole, verificherebbero soltanto che il riconoscitore riconosce le stringhe che
gli abbiamo scritto noi.

**Uccidere il client non uccide lo strumento**, finché in mezzo c'è `docker exec`. Si chiude al
Task 12.

**`Progress` non dice l'unità.** Documenti per il dump, byte per il restore, e nessun campo che lo
distingua.

**Il `BrokenPipeError` non è mai stato riprodotto.** Se il processo muore prima che la password
finisca di essere scritta, la scrittura sul tubo fallisce. Non è gestito perché non è mai successo,
e gestire un caso mai visto significa scrivere codice che nessuna prova copre.

**Il costo delle prove è cresciuto.** La suite di integrazione è passata da 1,46 s a **28–40 s**
— due esecuzioni consecutive hanno dato 39,6 s e 28,4 s — e la ragione è che dieci di quelle prove
eseguono `mongodump` e `mongorestore` veri su centomila documenti. È il prezzo di [ADR-0020](../../docs/Decision.md#adr-0020) applicato a uno
strumento lento, ed è dichiarato qui perché la prossima persona che veda la suite rallentare sappia
dove guardare.

---

**Torna a:** [README.md](README.md) per l'indice · [capitolo 9](09-adattatori-veri-e-contratto-condiviso.md)
per gli adattatori che parlano con una libreria.
