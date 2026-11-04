"""Withdraw a specifically rejected article; preserve all other content."""
from pathlib import Path
from urllib.parse import urlsplit
from collections import Counter
from zipfile import ZipFile
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
REJECTED = '/pl/przewracarka-czy-rozsiewacz-kompostu/'
BASE = 'https://wiedza.biofarmlab.pl'
LANGS = ('pl','en','de','fr','it','es','cs')
changed = set()
removed = []
backup = ZipFile('/tmp/knowledge-withdrawn-backup.zip','w')
for rel in ('pl/przewracarka-czy-rozsiewacz-kompostu/index.html','content-source/pl/przewracarka-czy-rozsiewacz-kompostu.md'):
    p = ROOT / rel
    if p.is_file():
        backup.write(p, rel)
        p.unlink()
        changed.add(rel)
        removed.append(rel)
backup.close()
for p in [ROOT/'index.html'] + [p for lang in LANGS for p in (ROOT/lang).rglob('index.html')]:
    if not p.is_file(): continue
    raw = p.read_text(encoding='utf-8')
    if 'przewracarka-czy-rozsiewacz-kompostu' not in raw: continue
    doc = BeautifulSoup(raw,'html.parser')
    prose = doc.select_one('.prose')
    original_prose = prose.get_text(' ',strip=True) if prose else None
    removed_rows = 0
    touched = False
    for a in list(doc.select('a[href]')):
        u = urlsplit(a['href'])
        if u.netloc not in ('','wiedza.biofarmlab.pl') or u.path.rstrip('/') != REJECTED.rstrip('/'):
            continue
        classes = a.get('class',[])
        if 'library-row' in classes:
            group = a.find_parent('section',class_='library-topic')
            if group:
                counter = group.select_one('.library-topic-heading > span')
                if counter and counter.get_text(strip=True).isdigit():
                    counter.string = str(max(0,int(counter.get_text(strip=True))-1))
            for counter in doc.select('.topic-link[href="#temat-machines-technology"] > span'):
                if counter.get_text(strip=True).isdigit(): counter.string = str(max(0,int(counter.get_text(strip=True))-1))
            removed_rows += 1
            a.decompose()
        elif 'related-card' in classes:
            a.decompose()
        else:
            raise RuntimeError('Unexpected in-prose rejected link in '+str(p.relative_to(ROOT)))
        touched = True
    if touched:
        if removed_rows:
            counter = doc.select_one('.library-count')
            if counter and counter.get_text(strip=True).isdigit():
                counter.string = str(max(0,int(counter.get_text(strip=True))-removed_rows))
        if original_prose is not None:
            assert doc.select_one('.prose').get_text(' ',strip=True) == original_prose
        assert not any(urlsplit(a.get('href','')).path.rstrip('/') == REJECTED.rstrip('/') for a in doc.select('a[href]'))
        p.write_text(str(doc),encoding='utf-8')
        changed.add(str(p.relative_to(ROOT)))
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('',NS)
ET.register_namespace('xhtml','http://www.w3.org/1999/xhtml')
for p in ROOT.glob('sitemap*.xml'):
    tree = ET.fromstring(p.read_text(encoding='utf-8'))
    found = False
    for el in list(tree):
        if el.findtext('{%s}loc'%NS) == BASE+REJECTED:
            tree.remove(el)
            found = True
    if found:
        p.write_bytes(ET.tostring(tree,encoding='utf-8',xml_declaration=True)+b'\n')
        changed.add(str(p.relative_to(ROOT)))
assert not (ROOT/'pl/przewracarka-czy-rozsiewacz-kompostu/index.html').exists()
Path('/tmp/knowledge-rejected-changed-files.txt').write_text('\n'.join(sorted(changed))+'\n',encoding='utf-8')
print(json.dumps({'rejected_article_withdrawn':removed,'changed_files':sorted(changed),'other_article_prose_preserved':True},ensure_ascii=False,indent=2))
