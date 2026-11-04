"""Deterministic repairs to existing Knowledge pages; no AI generation.
Scope: an existing English offer's product/language labels, links between
published articles, demonstrably broken /wiedza/ paths, and the sitemap.
Original article prose is retained. Rejected StoryChief 996086 is excluded.
"""
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
from html import escape
from datetime import date
from collections import Counter
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://wiedza.biofarmlab.pl'
TODAY = '2026-11-04'
LANGS = ('pl', 'en', 'de', 'fr', 'it', 'es', 'cs')
REJECTED = '/pl/przewracarka-czy-rozsiewacz-kompostu/'
report = {'date': TODAY, 'base_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(), 'changes': [], 'content_generation': False}
paths = sorted([ROOT / 'index.html'] + [p for lang in LANGS for p in (ROOT / lang).rglob('index.html')])
original = {p: p.read_text(encoding='utf-8') for p in paths if p.exists()}
texts = dict(original)

def local_file(url, source):
    source_url = BASE + '/' + str(source.relative_to(ROOT)).replace('index.html','')
    u = urlsplit(urljoin(source_url, url))
    if u.netloc != urlsplit(BASE).netloc:
        return None
    rel = unquote(u.path).lstrip('/')
    p = ROOT / rel
    if u.path.endswith('/') or not Path(rel).suffix:
        p = p / 'index.html'
    return p

def broken_links(data):
    broken = set()
    for p, text in data.items():
        doc = BeautifulSoup(text, 'html.parser')
        for el in doc.find_all(['a','img','script','link']):
            attr = 'src' if el.name in ('img','script') else 'href'
            value = el.get(attr, '')
            if not value or value.startswith(('data:', 'mailto:', 'tel:', 'javascript:', '#')):
                continue
            target = local_file(value, p)
            if target is not None and not target.is_file():
                broken.add((str(p.relative_to(ROOT)), attr, value))
    return broken

before_broken = broken_links(texts)
report['pages_checked'] = len(texts)
report['broken_local_links_before'] = len(before_broken)

# Fix only legacy-prefixed local references whose original target is missing
# and whose corrected target demonstrably exists. Never rewrite remote URLs.
for p, text in list(texts.items()):
    def fix_legacy(match):
        old = match.group(2)
        new = old.replace('/wiedza/', '/', 1)
        before = local_file(old, p)
        after = local_file(new, p)
        if before is not None and not before.is_file() and after is not None and after.is_file():
            report['changes'].append({'file': str(p.relative_to(ROOT)), 'type': 'repair_local_reference', 'old': old, 'new': new})
            return match.group(1) + new + match.group(3)
        return match.group(0)
    texts[p] = re.sub(r'((?:href|src)=")(/wiedza/[^"<>]*)(")', fix_legacy, text)

# Product/language corrections only; facts and tools verified against the
# existing official English offer at https://livingsoilshortcut.com/.
p = ROOT / 'en/practical-soil-biology-course/index.html'
assert p in texts, 'Expected published English course article is missing'
replacements = [
    ('<p>Our Polish course includes a compost diary, a soil assessment radar and a compost materials calculator.', '<p>Living Soil Shortcut includes a compost diary, a soil assessment radar and a compost materials calculator.'),
    ('>Żywa Gleba Krok po Kroku: learning for your own land</h2>', '>Living Soil Shortcut: learning for your own land</h2>'),
    ('<p>Our Polish-language course has 28 lessons in five modules,', '<p>Our English-language course has 28 lessons in five modules,'),
    ('<p><a href="https://biofarmlab.pl/zywagleba">See the Polish course programme</a> to connect soil assessment, compost and recovery planning. For learning in English, explore <a href="https://livingsoilshortcut.com/">Living Soil Shortcut</a>.</p>', '<p><a href="https://livingsoilshortcut.com/">See the Living Soil Shortcut programme</a> to connect soil assessment, compost and recovery planning. For learning in Polish, explore <a href="https://biofarmlab.pl/zywagleba">Żywa Gleba Krok po Kroku</a>.</p>')
]
for old, new in replacements:
    if old in texts[p]:
        assert texts[p].count(old) == 1
        texts[p] = texts[p].replace(old, new, 1)
        report['changes'].append({'file': str(p.relative_to(ROOT)), 'type': 'correct_existing_english_offer_reference'})
    else:
        assert new in texts[p], 'The English article changed; manual reconciliation is required'

# Add navigational links with titles copied from the existing target articles.
# No new educational or promotional paragraphs are generated.
pairs = [
    ('pl/odzywianie-sie-roslin/index.html', 'pl/co-sprawdzic-najpierw-gleba-kompost/index.html'),
    ('pl/nawozy-a-zycie-gleby-siec-pokarmowa/index.html', 'pl/co-sprawdzic-najpierw-gleba-kompost/index.html'),
    ('pl/obornik-kompostowanie-7-21-dni/index.html', 'pl/jak-stosowac-gotowy-kompost/index.html'),
    ('en/what-to-check-first-soil-compost/index.html', 'en/practical-soil-biology-course/index.html'),
    ('en/why-compost-pile-is-not-heating/index.html', 'en/practical-soil-biology-course/index.html'),
    ('en/using-finished-compost/index.html', 'en/practical-soil-biology-course/index.html')
]
for source_rel, target_rel in pairs:
    source, target = ROOT / source_rel, ROOT / target_rel
    assert source in texts and target in texts, (source_rel, target_rel)
    target_url = '/' + target_rel.replace('index.html', '')
    assert target_url != REJECTED
    doc = BeautifulSoup(texts[source], 'html.parser')
    if any(local_file(a.get('href',''), source) == target for a in doc.find_all('a', href=True)):
        continue
    target_doc = BeautifulSoup(texts[target], 'html.parser')
    title = target_doc.find('h1')
    assert title is not None
    label = 'Czytaj dalej' if source_rel.startswith('pl/') else 'Read next'
    addition = '<p class="knowledge-next-reading">' + label + ': <a href="' + target_url + '">' + escape(title.get_text(' ', strip=True)) + '</a>.</p>\n'
    marker = '</div><section class="related-section">'
    assert texts[source].count(marker) == 1, source_rel
    texts[source] = texts[source].replace(marker, addition + marker, 1)
    report['changes'].append({'file': source_rel, 'type': 'connect_existing_articles', 'target': target_url})

# Keep Article modification dates truthful for changed pages, preserving
# the entire remaining JSON-LD object and original publication dates.
for p, text in list(texts.items()):
    if text == original[p]:
        continue
    def update_article_date(match):
        try:
            data = json.loads(match.group(2))
        except json.JSONDecodeError:
            return match.group(0)
        if isinstance(data, dict) and data.get('@type') in ('Article','BlogPosting'):
            data['dateModified'] = TODAY + 'T00:00:00.000Z'
            return match.group(1) + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + match.group(3)
        return match.group(0)
    texts[p] = re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', update_article_date, text, flags=re.S)

after_broken = broken_links(texts)
assert not (after_broken - before_broken), sorted(after_broken - before_broken)
report['broken_local_links_after'] = len(after_broken)
report['remaining_broken_local_links'] = sorted(after_broken)

# Build the sitemap from actual indexable pages, not a stale article count.
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('', NS)
existing_dates = {}
old_urls = set()
for sm in ROOT.glob('sitemap*.xml'):
    tree = ET.fromstring(sm.read_text(encoding='utf-8'))
    for el in tree.findall('{%s}url' % NS):
        loc = el.findtext('{%s}loc' % NS)
        if loc:
            old_urls.add(loc)
            existing_dates[loc] = el.findtext('{%s}lastmod' % NS)
entries = {}
article_count = 0
for p, text in texts.items():
    doc = BeautifulSoup(text, 'html.parser')
    robots = doc.find('meta', attrs={'name':'robots'})
    if robots and 'noindex' in robots.get('content','').lower():
        continue
    canonical = doc.find('link', rel='canonical')
    assert canonical and canonical.get('href'), 'Missing canonical: ' + str(p)
    loc = canonical['href']
    assert loc.startswith(BASE + '/'), 'Wrong canonical domain: ' + loc
    assert local_file(loc, p) == p, 'Canonical does not match file: ' + str(p)
    assert loc not in entries, 'Duplicate canonical: ' + loc
    assert urlsplit(loc).path != REJECTED, 'Rejected article unexpectedly exists in published pages'
    lastmod = existing_dates.get(loc)
    for el in doc.find_all('script', type='application/ld+json'):
        data = json.loads(el.string or el.get_text())
        if isinstance(data, dict) and data.get('@type') in ('Article','BlogPosting'):
            article_count += 1
            lastmod = data.get('dateModified') or data.get('datePublished') or lastmod
    entries[loc] = lastmod
assert len(entries) >= len(old_urls), 'Refuse unexpected reduction in indexed URLs'
urlset = ET.Element('{%s}urlset' % NS)
for loc in sorted(entries):
    item = ET.SubElement(urlset, '{%s}url' % NS)
    ET.SubElement(item, '{%s}loc' % NS).text = loc
    if entries[loc]:
        ET.SubElement(item, '{%s}lastmod' % NS).text = entries[loc]
new_sitemap = ET.tostring(urlset, encoding='utf-8', xml_declaration=True).decode('utf-8') + '\n'
report['article_pages_checked'] = article_count
report['sitemap_urls_before'] = len(old_urls)
report['sitemap_urls_after'] = len(entries)
report['new_sitemap_urls'] = sorted(set(entries) - old_urls)
report['missing_sitemap_urls'] = sorted(old_urls - set(entries))
assert not report['missing_sitemap_urls'], report['missing_sitemap_urls']

changed = []
for p, text in texts.items():
    if text != original[p]:
        p.write_text(text, encoding='utf-8')
        changed.append(str(p.relative_to(ROOT)))
sm = ROOT / 'sitemap-0.xml'
if sm.read_text(encoding='utf-8') != new_sitemap:
    sm.write_text(new_sitemap, encoding='utf-8')
    changed.append('sitemap-0.xml')
report['changed_files'] = changed
report['changed_file_sha256'] = {r: hashlib.sha256((ROOT/r).read_bytes()).hexdigest() for r in changed}
Path('/tmp/knowledge-repair-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
Path('/tmp/knowledge-changed-files.txt').write_text('\n'.join(changed) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
