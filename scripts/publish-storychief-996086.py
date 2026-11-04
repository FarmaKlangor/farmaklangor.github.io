"""Publish the existing StoryChief article 996086, preserving the deployed site.
No AI calls. No editorial rewriting. Operates only on this article and navigation.
"""
from pathlib import Path
from copy import deepcopy
from urllib.parse import urlparse
import json
import re
import xml.etree.ElementTree as ET
import markdown
import yaml
from bs4 import BeautifulSoup

ROOT = Path('.')
SOURCE = ROOT / 'content-source/pl/przewracarka-czy-rozsiewacz-kompostu.md'
raw = SOURCE.read_text(encoding='utf-8')
_, front, body = raw.split('---', 2)
meta = yaml.safe_load(front)
slug = meta['slug']
title = meta['title']
desc = meta['description']
url = f'https://wiedza.biofarmlab.pl/pl/{slug}/'
href = f'/pl/{slug}/'
day = meta['publishedAt']
assert slug == 'przewracarka-czy-rozsiewacz-kompostu'
assert meta['approvedForPublication'] is True
TEMPLATE = ROOT / 'pl/jak-dobrac-przewracarke-kompostu/index.html'
rendered = markdown.markdown(body.strip(), extensions=['tables'])
doc = BeautifulSoup(TEMPLATE.read_text(encoding='utf-8'), 'html.parser')
article = doc.select_one('article.article')
assert article is not None and doc.select_one('.prose') is not None
article['data-article-slug'] = slug
for tag in doc.select('[data-article-slug]'):
    tag['data-article-slug'] = slug

doc.title.string = f'{title} | BioFarmLab'
doc.select_one('h1').string = title
doc.select_one('.article-header .lead').string = desc
for name, value in [('description', desc), ('twitter:title', f'{title} | BioFarmLab'), ('twitter:description', desc)]:
    tag = doc.find('meta', attrs={'name': name})
    if tag: tag['content'] = value
for name, value in [('og:title', f'{title} | BioFarmLab'), ('og:description', desc), ('og:url', url)]:
    tag = doc.find('meta', attrs={'property': name})
    if tag: tag['content'] = value
canonical = doc.find('link', attrs={'rel': 'canonical'})
assert canonical is not None
canonical['href'] = url
for tag in list(doc.select('link[hreflang]')):
    tag.decompose()
for lang in ['pl', 'x-default']:
    tag = doc.new_tag('link', rel='alternate', hreflang=lang, href=url)
    doc.head.append(tag)
for tag in list(doc.select('.translation-links')):
    tag.decompose()
for tag in doc.select('script[type="application/ld+json"]'):
    data = json.loads(tag.string or tag.get_text())
    if isinstance(data, dict) and data.get('@type') == 'Article':
        data.update(headline=title, description=desc, datePublished=f'{day}T00:00:00.000Z', dateModified=f'{day}T00:00:00.000Z', mainEntityOfPage=url, inLanguage='pl')
        tag.string = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
article_meta = doc.select_one('.article-meta')
assert article_meta is not None
article_meta.clear()
span = doc.new_tag('span'); span.string = 'BioFarmLab'; article_meta.append(span)
span = doc.new_tag('span'); span.string = ' · '; article_meta.append(span)
time = doc.new_tag('time', datetime=f'{day}T00:00:00.000Z'); time.string = '4.11.2026'; article_meta.append(time)
prose = doc.select_one('.prose')
prose.clear()
fragment = BeautifulSoup(rendered, 'html.parser')
for node in list(fragment.contents):
    prose.append(node.extract())
assert len(prose.select('h2')) == 8, f'Unexpected heading count: {len(prose.select("h2"))}'
assert len(prose.select('h3')) == 3 and len(prose.select('table')) == 1
assert prose.get_text(' ', strip=True) == BeautifulSoup(rendered, 'html.parser').get_text(' ', strip=True)
for a in prose.select('a[href]'):
    u = urlparse(a['href'])
    if u.netloc == 'wiedza.biofarmlab.pl' or (not u.netloc and u.path.startswith('/')):
        target = ROOT / u.path.lstrip('/')
        if u.path.endswith('/'): target /= 'index.html'
        assert target.exists(), f'Missing internal article: {a["href"]}'
OUTPUT = ROOT / 'pl' / slug / 'index.html'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(str(doc), encoding='utf-8')

# Add an article card using the existing visual design. Preserve all current links.
index_changed = []
for index_path in [ROOT / 'pl/index.html', ROOT / 'index.html']:
    page = BeautifulSoup(index_path.read_text(encoding='utf-8'), 'html.parser')
    source_card = page.select_one('.library-row[href="/pl/jak-dobrac-przewracarke-kompostu/"]')
    if source_card is None:
        assert index_path.name == 'index.html' and index_path.parent == ROOT, 'Polish article list not found'
        continue
    if page.select_one(f'.library-row[href="{href}"]'):
        continue
    before = {a.get('href') for a in page.select('a[href]')}
    card = deepcopy(source_card)
    card['href'] = href
    card['data-article-slug'] = slug
    card.select_one('h3').string = title
    card.select_one('.library-row-copy p').string = desc
    source_card.insert_before(card)
    group = card.find_parent('section', class_='library-topic')
    assert group is not None
    for selector in ['.library-topic-heading > span']:
        counter = group.select_one(selector)
        if counter and counter.get_text(strip=True).isdigit(): counter.string = str(int(counter.get_text(strip=True)) + 1)
    counter = page.select_one('.library-count')
    if counter and counter.get_text(strip=True).isdigit(): counter.string = str(int(counter.get_text(strip=True)) + 1)
    for counter in page.select('.topic-link[href="#temat-machines-technology"] > span'):
        if counter.get_text(strip=True).isdigit(): counter.string = str(int(counter.get_text(strip=True)) + 1)
    assert before <= {a.get('href') for a in page.select('a[href]')}
    assert len(page.select(f'.library-row[href="{href}"]')) == 1
    index_path.write_text(str(page), encoding='utf-8')
    index_changed.append(str(index_path))
assert BeautifulSoup((ROOT/'pl/index.html').read_text(encoding='utf-8'), 'html.parser').select_one(f'.library-row[href="{href}"]')

# Link the new article from two relevant existing articles without rewriting them.
for backlink_path in [TEMPLATE, ROOT/'pl/jak-stosowac-gotowy-kompost/index.html']:
    page = BeautifulSoup(backlink_path.read_text(encoding='utf-8'), 'html.parser')
    grid = page.select_one('.related-grid')
    assert grid is not None
    if grid.select_one(f'a[href="{href}"]'): continue
    card = deepcopy(grid.select_one('.related-card'))
    assert card is not None
    card['href'] = href
    card['data-destination-slug'] = slug
    card.select_one('strong').string = title
    category = card.select_one('.related-category')
    if category: category.string = 'Maszyny i technologia'
    hero = doc.select_one('.article-hero-image img')
    image = card.select_one('img')
    if hero and image:
        image['src'] = hero['src']; image['alt'] = hero.get('alt', '')
    grid.append(card)
    backlink_path.write_text(str(page), encoding='utf-8')

# Preserve existing sitemap XML byte-for-byte except the one new URL.
namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
sitemap_files = list(ROOT.glob('sitemap*.xml'))
urlsets = []
already = False
for path in sitemap_files:
    xml = path.read_text(encoding='utf-8')
    root = ET.fromstring(xml)
    if root.tag == namespace+'urlset':
        urlsets.append((path, xml))
        already = already or any(n.text == url for n in root.iter(namespace+'loc'))
assert urlsets, 'No sitemap URL set found'
if not already:
    path, xml = next(((p,x) for p,x in urlsets if '/pl/jak-dobrac-przewracarke-kompostu/' in x), urlsets[0])
    old_locs = [n.text for n in ET.fromstring(xml).iter(namespace+'loc')]
    entry = f'<url><loc>{url}</loc><lastmod>{day}</lastmod></url>'
    assert '</urlset>' in xml
    new_xml = xml.replace('</urlset>', entry+'</urlset>', 1)
    new_locs = [n.text for n in ET.fromstring(new_xml).iter(namespace+'loc')]
    assert new_locs == old_locs + [url]
    path.write_text(new_xml, encoding='utf-8')

# Basic checks against template/canonical leakage and missing styling.
final = BeautifulSoup(OUTPUT.read_text(encoding='utf-8'), 'html.parser')
assert final.select_one('h1').get_text() == title
assert final.select_one('link[rel="canonical"]')['href'] == url
assert final.select_one('link[rel="stylesheet"]') is not None
assert 'bfl-knowledge-consent.js' in str(final)
assert 'preview-banner' not in str(final)
assert not any('noindex' in t.get('content','').lower() for t in final.find_all('meta', attrs={'name':'robots'}))
print(json.dumps({'status':'prepared_and_validated','storychief_id':996086,'url':url,'index_files':index_changed,'new_article_word_count':len(prose.get_text(' ',strip=True).split()),'ai_calls':0},ensure_ascii=False))
