# 1. L'architettura esagonale, e perché qui serve davvero

> Il principio in una riga: **il nucleo dell'applicazione non sa che MongoDB esiste.** Lo sa un
> adattatore, che sta al bordo, e che si può togliere.

## Il problema che risolve

`mongolab` esiste per mostrare, dal vivo e in sala, tre cose difficili da raccontare a parole: che
cosa vede un client durante un failover, come si distribuiscono i documenti fra shard, e che cosa
succede a un'applicazione mentre il cluster sotto di lei cambia forma. Sono tutte cose che
succedono **fra** l'applicazione e il cluster.

Questo crea una tensione. Da un lato il valore didattico sta proprio nel contatto con MongoDB
vero — un facsimile non dimostrerebbe niente
([ADR-0020](../../docs/Decision.md#adr-0020)). Dall'altro, se ogni pezzo di codice tocca il driver,
allora ogni prova ha bisogno di un cluster acceso, e una suite che richiede undici container per
dire se una percentuale è calcolata bene non verrà eseguita mai.

L'architettura esagonale risolve esattamente questa tensione, e non è ornamento: è ciò che permette
alle due esigenze di coesistere invece di scegliere.

## La forma

Cinque pezzi, e una sola regola sul verso delle frecce.

```
                        ┌──────────────────┐
                        │  presentation    │   Rich, Typer: come si vede
                        └────────┬─────────┘
                                 │ dipende da
                        ┌────────▼─────────┐
                        │   application    │   i casi d'uso: che cosa fa
                        └────────┬─────────┘
                                 │ dipende da
                        ┌────────▼─────────┐
                        │     domain       │   modelli, eventi, PORTE
                        └────────▲─────────┘
                                 │ dipende da
                        ┌────────┴─────────┐
                        │ infrastructure   │   pymongo, mongodump: con che cosa
                        └──────────────────┘
```

Si guardi la freccia in basso. `infrastructure` — dove vive pymongo — **dipende da** `domain`, non
il contrario. È l'inversione delle dipendenze, e la si legge così: è il dominio a dichiarare di che
cosa ha bisogno, e l'infrastruttura a rincorrere quella forma. Il dominio non ha mai visto pymongo
e non lo vedrà.

Nel codice i cinque pezzi sono cinque directory sotto `app/src/mongolab/`, più `cli.py` che è la
radice di composizione: l'unico punto in cui i pezzi veri vengono costruiti e messi insieme.

| Directory | Che cosa contiene | Che cosa può importare |
|---|---|---|
| `domain/` | modelli, eventi, le cinque porte | **solo la libreria standard** |
| `application/` | i casi d'uso: `WorkloadRunner`, `TopologyWatcher` | **solo la libreria standard** e `domain` |
| `infrastructure/` | gli adattatori: pymongo, `mongodump` come sottoprocesso | tutto |
| `presentation/` | la resa: Rich, e il formato testuale di riserva | tutto |
| `cli.py` | costruisce e collega — nient'altro | tutto |

## La regola è codice, non convenzione

Un diagramma come quello sopra si trova in molti repository, e in molti repository non corrisponde
più al codice. La differenza qui è che **una prova lo verifica**, e fallisce se qualcuno sbaglia.

`app/tests/unit/test_scheletro.py` percorre i sorgenti di `domain/` e `application/`, ne analizza
l'albero sintattico con il modulo `ast` della libreria standard, raccoglie ogni nome importato e lo
confronta con `sys.stdlib_module_names`. Qualunque cosa non sia libreria standard o il pacchetto
stesso è una violazione, e il messaggio nomina il file e il modulo colpevole.

Perché `ast` e non una ricerca testuale: un `grep` per `import pymongo` non trova
`__import__("pymongo")`, non distingue un import dentro una stringa da uno vero, e segnala come
violazione una riga di commento. L'albero sintattico è ciò che l'interprete vede davvero.

La guardia è stata **rotta apposta** appena scritta, aggiungendo un `import pymongo` al dominio, per
verificare due cose in una: che scatti, e che quando scatta dica *dove*. È una disciplina che nel
repository ha un nome — nota di metodo 142 del
[registro operativo](../../docs/registro-operativo-sviluppo.md) — e una motivazione precisa: una
guardia architetturale nasce davanti a un albero vuoto, quindi il suo primo verde non significa
niente.

## Che cosa si guadagna, in concreto

**Una suite unitaria che gira in centesimi di secondo.** Al momento in cui questa pagina è scritta,
`make app-test` esegue diciannove prove in circa venti millisecondi, senza Docker, senza rete,
senza un cluster. Non è un vezzo: è la condizione perché le prove vengano eseguite a ogni
salvataggio invece che una volta prima del rilascio.

**Prove sul failover che non aspettano un failover.** Il tempo entra nel dominio da una porta,
`Clock`. Un doppio che avanza solo quando qualcuno chiama `sleep` permette di provare in
millisecondi una regola definita in decine di secondi — «dopo 30 s senza primario, smetti di
ritentare» — e di asserire il risultato **esatto** invece di una tolleranza.

**La possibilità di cambiare la resa senza toccare il nucleo.** Il talk ha bisogno di
un'interfaccia Rich che si legga dall'ultima fila; le registrazioni di riserva hanno bisogno di
testo semplice ([ADR-0050](../../docs/Decision.md#adr-0050)). Sono due implementazioni della stessa
porta, e il nucleo non sa quale sta parlando.

**Una separazione fra prove veloci e prove vere.** Le prove di integrazione esistono e usano gli
stack Compose del repository — non un facsimile — ma stanno in una directory separata e si chiedono
per nome. Il dettaglio sta in [05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md).

## Che cosa costa

Sarebbe disonesto elencare solo i vantaggi.

**Più file, e un livello di indirezione.** Chiamare `insert_many` su una porta invece che su una
`Collection` significa che chi legge il codice deve fare un salto in più per sapere che cosa
succede davvero. In un'applicazione di questa dimensione è un costo reale, non teorico.

**Il rischio di porte che copiano il driver.** Una porta che riproduce la firma di pymongo metodo
per metodo non inverte niente: sposta soltanto il nome. Le cinque porte di `mongolab` sono state
scritte guardando **che cosa serve alle scene**, non che cosa offre il driver — per esempio
`insert_many` restituisce un conteggio e non un elenco di identificatori, perché il numero della
scena è «confermate contro ritrovate» e le chiavi costerebbero memoria dentro oggetti che
attraversano una coda.

**Il confine va difeso attivamente.** Senza la guardia automatica, il primo `import pymongo` dentro
`application/` entrerebbe in un pomeriggio e non uscirebbe più.

## Perché l'applicazione gira in un container

C'è un punto in cui l'architettura del codice incontra quella dell'infrastruttura, e conviene
saperlo prima di provare a eseguire il lab.

Un client che si collega a un replica set con `directConnection=false` — il valore predefinito — non
parla solo con l'host indicato: scopre gli altri membri e manda le operazioni al primario
([S-007](../../docs/Sources.md#s-007)). Quella scoperta è esattamente ciò che il talk vuole
mostrare, ed è anche la prima cosa che si rompe se l'applicazione gira sull'host e il cluster dentro
Docker, perché i nomi che il replica set annuncia non sono risolvibili da fuori.

Per questo `mongolab` gira in un container sulla rete Compose dello stack e si connette con i nomi
dei servizi; `directConnection=true` si usa solo contro lo standalone, dove non c'è niente da
scoprire ([ADR-0012](../../docs/Decision.md#adr-0012)). È una decisione presa prima che il codice
esistesse, e il codice la eredita: l'adattatore `infrastructure` riceve una stringa di connessione,
non la costruisce.

---

**Da leggere dopo:** [02-porte-e-doppi.md](02-porte-e-doppi.md), che spiega come è fatto il confine
di cui questa pagina descrive il verso.

**Fonti:** [S-007](../../docs/Sources.md#s-007). **Decisioni:**
[ADR-0007](../../docs/Decision.md#adr-0007), [ADR-0012](../../docs/Decision.md#adr-0012),
[ADR-0020](../../docs/Decision.md#adr-0020), [ADR-0050](../../docs/Decision.md#adr-0050).
