"""Build a flat, verified public-stream playlist; standard library only."""
import concurrent.futures as cf
import datetime as dt
import json
import re
import urllib.request as ur
from urllib.parse import urljoin, urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ITALY = 'https://raw.githubusercontent.com/Free-TV/IPTV/master/lists/italy.md'
TDT = 'https://www.tdtchannels.com/lists/tv.m3u8'
TUNDRAK = 'https://raw.githubusercontent.com/Tundrak/IPTV-Italia/main/iptvitaplus.m3u'
# Only broadcaster-owned origins or explicitly identified broadcaster CDN endpoints.
ITALIAN_HOSTS = {'streaming.aurora.enhanced.live', 'mediapolis.rai.it', 'live02-seg.msf.cdn.mediaset.net',
                 'hls-live-tv2000.akamaized.net', 'qrg.akamaized.net',
 'live02-seg.msr.cdn.mediaset.net', 'radioitaliatv.akamaized.net',
 'ilsole24ore-radiovisual.akamaized.net', 'stream.rdstv.radio',
 'legaseriea-live-prd.cdn.netrw.it', 'distribution.sportitalialive.it',
 'live-embed.supertennix.hiway.media', 'sportsitalia-samsungitaly.amagi.tv'}
LOCAL_CDNS = ('streamlock.net','xdevel.com','netrw.it','streamshow.it','msvdn.net',
 'arcapuglia.it','saiuzwebnetwork.it','rtvweb.com','aswifi.it','softwarecreation.it',
 'streamingwebtv24.it','ipstream.it','mediastreaming.it','newradio.it','selftv.video',
 'mariatvcdn.com','mariatvcdn.it','ets-sistemi.it','telemia.tv','telesveva.com',
 'nuovatv.net','velcom.it','azotosolutions.com','tvavicenza.it','teleromagna.it',
 'top-ix.org','fluid.stream','seeweb.it','zivoli.it','radiotv.it','paroledivita.org',
 'telesirio.it','teleterni.it','videolina.it','granducatotv.eu','liberta.it',
 'trgmedia.it','ntimedia.it','nuvola.tv','rossinitv.it','rubidia.it','uno4.it')
SPANISH_GROUPS = {'Generalistas','Deportivos','Andalucía','Cataluña','C. Valenciana',
 'Canarias','País Vasco','Galicia','Castilla-La Mancha','C. de Madrid','Castilla y León',
 'R. de Murcia','Cantabria','C. Foral de Navarra','Extremadura','La Rioja','Illes Balears',
 'Melilla','P. de Asturias'}

def fetch(url, limit=3_000_000, user_agent=None):
    req = ur.Request(url, headers={'User-Agent':user_agent or 'Mozilla/5.0 (IPTV public-stream check)'})
    with ur.urlopen(req, timeout=12) as r:
        return r.read(limit), r.url

def text(url):
    return fetch(url)[0].decode('utf-8-sig')

def candidates():
    result = []
    section = ''
    for line in text(ITALY).splitlines():
        if '<h2>' in line:
            section = re.sub('<[^>]*>', '', line).strip()
        if not line.startswith('|') or '[>]' not in line:
            continue
        cols = [c.strip() for c in line.split('|')]
        match = re.search(r'\[>\]\((https?://[^)]+)\)', cols[3])
        if not match:
            continue
        host = urlsplit(match[1]).hostname or ''
        local_origin = any(host == h or host.endswith('.'+h) for h in LOCAL_CDNS)
        if host not in ITALIAN_HOSTS and not (local_origin and section in ('Regional DVB-T','National DVB-T')):
            continue
        name = re.sub(r'[ⒼⓈⓉⓎ]', '', cols[2]).strip()
        lcn = int(cols[1]) if section == 'National DVB-T' and cols[1].isdigit() and int(cols[1]) > 0 else None
        result.append(dict(name=name, url=match[1], country='IT', lcn=lcn, source=ITALY))
    rai_meta = None
    for line in text(TUNDRAK).splitlines():
        if line.startswith('#EXTINF:'):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            name = line.rsplit(',',1)[-1].strip()
            name = name.replace(' (HbbTV)','').replace(' + HD','')
            if name == 'Rai Radio 2 Visual':
                name = 'Rai Radio 2 Visual Radio'
            rai_meta = dict(name=name, country='IT', lcn=int(attrs['tvg-chno']) if attrs.get('tvg-chno','').isdigit() else None, source=TUNDRAK) if name.startswith('Rai ') else None
        elif rai_meta and line.startswith('#EXTVLCOPT:http-user-agent='):
            rai_meta['user_agent'] = line.split('=',1)[1]
        elif rai_meta and line.startswith(('http://','https://')):
            host = urlsplit(line).hostname or ''
            if host.endswith('.rai.it') or host == 'raievent10-elem-live.akamaized.net':
                result.append(dict(rai_meta, url=line.strip()))
            rai_meta = None
    result.extend([dict(name='Rai Sudtirol', url='https://wzstreaming.rai.it/TVlive/smil:liveStream.smil/index.m3u8', country='IT', lcn=None, source='https://www.raisudtirol.rai.it/'), dict(name='Rai News 24', url='https://rainews1-live.akamaized.net/hls/live/598326/rainews1/rainews1/playlist.m3u8', country='IT', lcn=48, source='https://www.raiplay.it/dirette/rainews24')])
    meta = None
    for line in text(TDT).splitlines():
        if line.startswith('#EXTINF:'):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            group = attrs.get('group-title','')
            country = 'WORLD' if group.startswith('Int.') or group == 'Deportivos Int.' else 'ES' if group in SPANISH_GROUPS else None
            meta = dict(name=line.rsplit(',',1)[-1].strip(), country=country, lcn=None, source=TDT)
        elif meta and line.startswith(('http://','https://')):
            if meta['country'] and not any(c in line for c in '[]'):
                result.append(dict(meta, url=line.strip()))
            meta = None
    if not any(c['country']=='IT' for c in result) or not any(c['country']=='ES' for c in result):
        raise RuntimeError('Source parsing failed; existing playlist preserved')
    return result

def probe_hls(url, depth=0, user_agent=None):
    if depth > 3:
        raise ValueError('Too many nested playlists')
    data, final = fetch(url, user_agent=user_agent)
    body = data.decode('utf-8-sig')
    if not body.lstrip().startswith('#EXTM3U'):
        raise ValueError('Not an HLS manifest')
    if '#EXT-X-KEY:' in body and re.search(r'METHOD=(?!NONE)[A-Z0-9-]+', body):
        raise ValueError('Encrypted stream omitted')
    lines = [x.strip() for x in body.splitlines() if x.strip()]
    if '#EXT-X-STREAM-INF:' in body:
        errors = []
        variants = [urljoin(final,lines[i+1]) for i,l in enumerate(lines[:-1]) if l.startswith('#EXT-X-STREAM-INF:')]
        for variant in variants[:3]:
            try:
                return probe_hls(variant, depth+1, user_agent)
            except Exception as exc:
                errors.append(str(exc))
        raise ValueError('Variants unavailable: ' + '; '.join(errors))
    segments = [urljoin(final,x) for x in lines if not x.startswith('#')]
    if not segments or '#EXTINF:' not in body:
        raise ValueError('No media segments')
    segment, _ = fetch(segments[-1], 1024, user_agent)
    if not segment or segment.lstrip().lower().startswith((b'<html',b'<!doctype')):
        raise ValueError('Invalid media response')
    return 'HLS manifest and media segment reachable'

def check(item):
    try:
        detail = probe_hls(item['url'], user_agent=item.get('user_agent'))
        return dict(item, available=True, detail=detail)
    except Exception as exc:
        return dict(item, available=False, detail=str(exc)[:250])

def render(items):
    lines = ['#EXTM3U', '# Sources: LaQuay/TDTChannels; Free-TV/IPTV; Tundrak/IPTV-Italia. Modified: filtered, verified and reordered.']
    for c in items:
        name = c['name'].replace('\n',' ').replace('\r',' ')
        lines.append(f'#EXTINF:-1,{name}')
        if c.get('user_agent'):
            lines.append('#EXTVLCOPT:http-user-agent='+c['user_agent'].replace('\n','').replace('\r',''))
        lines.append(c['url'])
    return '\n'.join(lines)+'\n'

def main():
    pool = candidates()
    with cf.ThreadPoolExecutor(max_workers=16) as executor:
        checked = list(executor.map(check,pool))
    good, seen = [], set()
    for c in checked:
        key = (c['country'], c['name'].casefold().replace(' geo cat','').replace(' geo',''))
        if c['available'] and key not in seen:
            good.append(c); seen.add(key)
    good.sort(key=lambda c: ({'IT':0,'ES':1,'WORLD':2}[c['country']], c['lcn'] or 9999, c['name'].casefold()))
    counts = {country:sum(c['country']==country for c in good) for country in ('IT','ES','WORLD')}
    if any(n==0 for n in counts.values()):
        raise RuntimeError(f'Empty geographic section: {counts}; existing playlist preserved')
    old_report = ROOT/'status.json'
    if old_report.exists():
        old = json.loads(old_report.read_text())['counts']
        if any(counts[k] < old[k]*0.5 for k in counts):
            raise RuntimeError('More than half a section lost; existing playlist preserved for review')
    output = render(good)
    assert 'group-title' not in output and '#EXTGRP' not in output
    (ROOT/'playlist.m3u').write_text(output,encoding='utf-8')
    report = {'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'counts':counts,
              'verification':'HLS manifest, variant and sample media bytes; not a full playback or territorial guarantee',
              'channels':checked}
    (ROOT/'status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(counts))

if __name__ == '__main__':
    main()
