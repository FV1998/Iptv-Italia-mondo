# IPTV Italia + Mondo

Playlist unica senza categorie o gruppi:

**https://raw.githubusercontent.com/FV1998/Iptv-Italia-mondo/main/playlist.m3u**

Ordine: Italia per LCN disponibile, Spagna, canali internazionali. Non è una lista completa di tutti i canali terrestri: vengono pubblicati i flussi pubblici delle fonti selezionate che superano i controlli, con l’eccezione esplicita dei collegamenti ufficiali Rai/Mediaset che restituiscono 403/451: sono mantenuti per l’uso dall’Italia ma NON dichiarati funzionanti. I numeri LCN servono per l'ordinamento e non creano gruppi nel lettore.

## Fonti e selezione

- Italia: [Free-TV/IPTV](https://github.com/Free-TV/IPTV/blob/master/lists/italy.md), con selezione degli endpoint delle emittenti e dei CDN usati dalle televisioni nazionali, regionali e locali in `update.py`. Esclusi mirror, ritrasmissioni di provenienza incerta e link con token copiati. Le numerazioni locali variano per regione: in assenza di una regione specifica i canali locali seguono quelli nazionali in ordine alfabetico. LCN nazionali confrontabili con [MIMIT](https://www.mimit.gov.it/it/comunicazioni/televisione/fornitori-di-servizi-di-media-audiovisivi-fsma/banda-700-fsma-nazionali).
- Warner Bros. Discovery: piattaforma Aurora confermata dal codice del sito ufficiale [DMAX](https://dmax.it/live-streaming-dmax/), con DMAX, Real Time e gli altri simulcast pubblici disponibili.
- Rai: endpoint ufficiali RaiPlay e Rai Südtirol. Sono controllati anche i link Rai di [davidefulgione.com](https://davidefulgione.com/tv.m3u). La fonte aggiuntiva [Tundrak/IPTV-Italia](https://github.com/Tundrak/IPTV-Italia/blob/main/iptvitaplus.m3u) viene controllata per i soli URL Rai ufficiali, preservando lo user-agent richiesto dal lettore senza aggiungere gruppi.
- Spagna e mondo: [LaQuay/TDTChannels](https://github.com/LaQuay/TDTChannels), che raccoglie collegamenti alle emissioni ufficiali. Incluse le sezioni spagnole generaliste, regionali e sportive e le sezioni esplicitamente internazionali. Esclusi eventi temporanei e URL con segnaposto.
- I metadati delle fonti vengono trasformati: rimozione dei gruppi, verifica disponibilità, eliminazione dei duplicati e riordinamento. Licenza TDTChannels inclusa in `LICENSE-TDTChannels`; Free-TV/IPTV è citato come fonte dei singoli collegamenti pubblici. Nessuna licenza sul software o sui metadati concede diritti sui programmi televisivi.

Lo sport spagnolo dipende dai flussi disponibili nelle fonti, per esempio Teledeporte, Esport3 e canali dei club. Non è garantita la presenza di partite o campionati, né di canali a pagamento. Non vengono aggirate autenticazione, cifratura o restrizioni geografiche.

## Aggiornamenti e controlli

GitHub Actions esegue `update.py` ogni giorno alle 04:17 UTC (06:17 in Italia con ora legale, 05:17 con ora solare), oltre all'avvio manuale. Gli orari del servizio possono subire ritardi. Nei repository pubblici inattivi GitHub può sospendere gli aggiornamenti pianificati: controllare periodicamente la scheda Actions.

Il controllo scarica il manifest HLS, una variante e un piccolo campione di un segmento multimediale. Verifica la raggiungibilità, non decodifica l'intera trasmissione e non garantisce la riproduzione sul proprio dispositivo o territorio. I flussi cifrati sono esclusi. `status.json` riporta data UTC, conteggi totali (`counts`), conteggi verificati (`verified_counts`), collegamenti ufficiali inclusi ma non verificati (`access_limited_included`) e risultati per ogni candidato, inclusi gli esclusi. I collegamenti Rai/Mediaset con 403/451 non sono una garanzia di funzionamento: il lettore deve trovarsi in un territorio autorizzato e potrebbero esserci ulteriori limitazioni. Errori 404/503, manifest invalidi e cifratura non vengono trattati come semplici blocchi geografici.

Se una fonte non è leggibile, una sezione resta vuota o perde più della metà dei canali rispetto all'ultima versione, il processo fallisce senza sostituire la playlist già pubblicata. Un controllo da GitHub può dare risultati diversi da un controllo dall'Italia. In caso di errore vedere Actions; la data dell'ultimo aggiornamento rimane in `status.json`.

Per rigenerare: Python 3.10 o successivo, `python update.py`. Nessuna dipendenza esterna.

## Calcio: limiti della copertura

Non si garantisce la copertura di tutti i maggiori campionati. Radio TV Serie A offre informazione e approfondimenti: non equivale a tutte le partite della Serie A. La disponibilità dei diritti varia per paese e servizio. Consultare le fonti ufficiali: [Serie A](https://www.legaseriea.it/radiotv), [LaLiga](https://www.laliga.com/en-GB/where-to-watch-laliga-easports), [Premier League](https://www.premierleague.com/en/about/faq/broadcast), [Bundesliga](https://www.bundesliga.com/de/bundesliga/info/broadcasters), [Ligue 1](https://ligue1.com/en/international-broadcasters). I servizi a pagamento o con accesso riservato non vengono inseriti.
