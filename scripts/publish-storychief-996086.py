"""Publish existing StoryChief 996086; no AI calls or editorial rewriting."""
from pathlib import Path
from copy import deepcopy
from urllib.parse import urlparse
import json
import xml.etree.ElementTree as ET
import markdown
import yaml
from bs4 import BeautifulSoup

ROOT = Path('.')
raw = (ROOT/'content-source/pl/przewracarka-czy-rozsiewacz-kompostu.md').read_text(encoding='utf-8')
_, front, body = raw.split('---', 2)
m = yaml.safe_load(front)
slug, title, desc, day = m['slug'], m['title'], m['description'], m['publishedAt']
href = f'/pl/{slug}/'
url = 'https://wiedza.biofarmlab.pl'+href
assert slug == 'przewracarka-czy-rozsiewacz-kompostu' and m['approvedForPublication'] is True
TEMPLATE = ROOT/'pl/jak-dobrac-przewracarke-kompostu/index.html'
def read(path): return BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
def save(path, page): path.write_text(str(page), encoding='utf-8')
doc = read(TEMPLATE)
assert doc.select_one('article.article') and doc.select_one('.prose')
for tag in doc.select('[data-article-slug]'): tag['data-article-slug'] = slug
doc.title.string = f'{title} | BioFarmLab'
doc.select_one('h1').string = title
doc.select_one('.article-header .lead').string = desc
for key, val in [('description',desc),('twitter:title',f'{title} | BioFarmLab'),('twitter:description',desc)]:
    tag=doc.find('meta',attrs={'name':key})
    if tag: tag['content']=val
for key,val in [('og:title',f'{title} | BioFarmLab'),('og:description',desc),('og:url',url)]:
    tag=doc.find('meta',attrs={'property':key})
    if tag: tag['content']=val
doc.select_one('link[rel="canonical"]')['href']=url
for tag in list(doc.select('link[hreflang], .translation-links')): tag.decompose()
for lang in ['pl','x-default']: doc.head.append(doc.new_tag('link',rel='alternate',hreflang=lang,href=url))
for tag in doc.select('script[type="application/ld+json"]'):
    data=json.loads(tag.string or tag.get_text())
    if isinstance(data,dict) and data.get('@type')=='Article':
        data.update(headline=title,description=desc,datePublished=f'{day}T00:00:00.000Z',dateModified=f'{day}T00:00:00.000Z',mainEntityOfPage=url,inLanguage='pl')
        tag.string=json.dumps(data,ensure_ascii=False,separators=(',',':'))
meta=doc.select_one('.article-meta'); assert meta is not None; meta.clear()
span=doc.new_tag('span'); span.string='BioFarmLab · '; meta.append(span)
time=doc.new_tag('time',datetime=f'{day}T00:00:00.000Z'); time.string='4.11.2026'; meta.append(time)
rendered=markdown.markdown(body.strip(),extensions=['tables'])
fragment=BeautifulSoup(rendered,'html.parser')
prose=doc.select_one('.prose'); prose.clear()
for node in list(fragment.contents): prose.append(node.extract())
assert len(prose.select('h2'))==7 and len(prose.select('h3'))==3 and len(prose.select('table'))==1
assert prose.get_text(' ',strip=True)==BeautifulSoup(rendered,'html.parser').get_text(' ',strip=True)
for a in prose.select('a[href]'):
    u=urlparse(a['href'])
    if u.netloc=='wiedza.biofarmlab.pl' or (not u.netloc and u.path.startswith('/')):
        path=ROOT/u.path.lstrip('/')
        if u.path.endswith('/'): path/='index.html'
        assert path.exists(),f'Missing internal article: {a["href"]}'
output=ROOT/'pl'/slug/'index.html'; output.parent.mkdir(parents=True,exist_ok=True); save(output,doc)
index_changed=[]
for path in [ROOT/'pl/index.html',ROOT/'index.html']:
    page=read(path)
    original=page.select_one('.library-row[href="/pl/jak-dobrac-przewracarke-kompostu/"]')
    if original is None:
        assert path.parent==ROOT,'Polish article list not found'
        continue
    if page.select_one(f'.library-row[href="{href}"]'): continue
    before={a['href'] for a in page.select('a[href]')}
    card=deepcopy(original); card['href']=href; card['data-article-slug']=slug
    card.select_one('h3').string=title; card.select_one('.library-row-copy p').string=desc
    original.insert_before(card)
    group=card.find_parent('section',class_='library-topic'); assert group is not None
    counters=[group.select_one('.library-topic-heading > span'),page.select_one('.library-count')]
    counters+=page.select('.topic-link[href="#temat-machines-technology"] > span')
    for c in counters:
        if c and c.get_text(strip=True).isdigit(): c.string=str(int(c.get_text(strip=True))+1)
    assert before<={a['href'] for a in page.select('a[href]')}
    assert len(page.select(f'.library-row[href="{href}"]'))==1
    save(path,page); index_changed.append(str(path))
assert read(ROOT/'pl/index.html').select_one(f'.library-row[href="{href}"]')
for path in [TEMPLATE,ROOT/'pl/jak-stosowac-gotowy-kompost/index.html']:
    page=read(path); grid=page.select_one('.related-grid'); assert grid is not None
    if grid.select_one(f'a[href="{href}"]'): continue
    card=deepcopy(grid.select_one('.related-card')); assert card is not None
    card['href']=href; card['data-destination-slug']=slug; card.select_one('strong').string=title
    category=card.select_one('.related-category')
    if category: category.string='Maszyny i technologia'
    hero=doc.select_one('.article-hero-image img'); image=card.select_one('img')
    if hero and image: image['src']=hero['src']; image['alt']=hero.get('alt','')
    grid.append(card); save(path,page)
ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
sets=[]; already=False
for path in ROOT.glob('sitemap*.xml'):
    xml=path.read_text(encoding='utf-8'); root=ET.fromstring(xml)
    if root.tag==ns+'urlset':
        sets.append((path,xml)); already=already or any(n.text==url for n in root.iter(ns+'loc'))
assert sets,'No sitemap URL set found'
if not already:
    path,xml=next(((p,x) for p,x in sets if '/pl/jak-dobrac-przewracarke-kompostu/' in x),sets[0])
    before=[n.text for n in ET.fromstring(xml).iter(ns+'loc')]
    assert '</urlset>' in xml
    new=xml.replace('</urlset>',f'<url><loc>{url}</loc><lastmod>{day}</lastmod></url></urlset>',1)
    assert [n.text for n in ET.fromstring(new).iter(ns+'loc')]==before+[url]
    path.write_text(new,encoding='utf-8')
final=read(output)
assert final.select_one('h1').get_text()==title
assert final.select_one('link[rel="canonical"]')['href']==url
assert final.select_one('link[rel="stylesheet"]')
assert 'bfl-knowledge-consent.js' in str(final) and 'preview-banner' not in str(final)
assert not any('noindex' in t.get('content','').lower() for t in final.find_all('meta',attrs={'name':'robots'}))
print(json.dumps({'status':'prepared_and_validated','storychief_id':996086,'url':url,'index_files':index_changed,'new_article_word_count':len(prose.get_text(' ',strip=True).split()),'ai_calls':0},ensure_ascii=False))
