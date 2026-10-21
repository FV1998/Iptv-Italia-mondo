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
# Only broadcaster-owned origins or explicitly identified broadcaster CDN endpoints.
ITALIAN_HOSTS = {'mediapolis.rai.it', 'live02-seg.msf.cdn.mediaset.net',
                 'hls-live-tv2000.akamaized.net', 'qrg.akamaized.net'}
SPANISH_GROUPS = {'Generalistas','Deportivos','Andalucía','Cataluña','C. Valenciana',
 'Canarias','País Vasco','Galicia','Castilla-La Mancha','C. de Madrid','Castilla y León',
 'R. de Murcia','Cantabria','C. Foral de Navarra','Extremadura','La Rioja','Illes Balears',
 'Melilla','P. de Asturias'}

def fetch(url, limit=3_000_000):
    req = ur.Request(url, headers={'User-Agent':'Mozilla/5.0 (IPTV public-stream check)'})
    with ur.urlopen(req, timeout=12) as r:
        return r.read(limit), r.url

def text(url):
    return fetch(url)[0].decode('utf-8-sig')

def candidates():
    result = []
    for line in text(ITALY).splitlines():
        if not line.startswith('|') or '[>]' not in line:
            continue
        cols = [c.strip() for c in line.split('|')]
        match = re.search(r'\[>\]\((https?://[^)]+)\)', cols[3])
        if not match or urlsplit(match[1]).hostname not in ITALIAN_HOSTS:
            continue
        name = re.sub(r'[ⒼⓈⓉⓎ]', '', cols[2]).strip()
        lcn = int(cols[1]) if cols[1].isdigit() and int(cols[1]) > 0 else None
        result.append(dict(name=name, url=match[1], country='IT', lcn=lcn, source=ITALY))
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

def probe_hls(url, depth=0):
    if depth > 3:
        raise ValueError('Too many nested playlists')
    data, final = fetch(url)
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
                return probe_hls(variant, depth+1)
            except Exception as exc:
                errors.append(str(exc))
        raise ValueError('Variants unavailable: ' + '; '.join(errors))
    segments = [urljoin(final,x) for x in lines if not x.startswith('#')]
    if not segments or '#EXTINF:' not in body:
        raise ValueError('No media segments')
    segment, _ = fetch(segments[-1], 1024)
    if not segment or segment.lstrip().lower().startswith((b'<html',b'<!doctype')):
        raise ValueError('Invalid media response')
    return 'HLS manifest and media segment reachable'

def check(item):
    try:
        detail = probe_hls(item['url'])
        return dict(item, available=True, detail=detail)
    except Exception as exc:
        return dict(item, available=False, detail=str(exc)[:250])

def render(items):
    lines = ['#EXTM3U', '# Sources: LaQuay/TDTChannels; Free-TV/IPTV. Modified: filtered, verified and reordered.']
    for c in items:
        name = c['name'].replace('\n',' ').replace('\r',' ')
        lines.extend([f'#EXTINF:-1,{name}', c['url']])
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
