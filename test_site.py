"""Business and release regressions. Run with python3 -m unittest -v."""
import copy
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from build import ROOT, render, validate

class Document(HTMLParser):
    def __init__(self, page):
        super().__init__(); self.nodes=[]; self.feed(page)
    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag,dict(attrs)))

class SiteTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'shop-data.json').read_text())
        self.page=render(self.data)
        self.doc=Document(self.page)
    def test_release_is_rebuilt(self):
        self.assertEqual((ROOT/'index.html').read_text(),self.page,'Run python3 build.py before publishing')
    def test_booking_destinations_are_preserved(self):
        expected={a['barber_id']:a['booking_url'] for a in self.data['assignments']}
        links=[a for tag,a in self.doc.nodes if tag=='a' and a.get('data-action')=='booking']
        self.assertEqual(len(links),8)
        for a in links:
            self.assertEqual(a['href'],expected[a['data-barber']])
    def test_verified_squire_price_regressions(self):
        offerings={o['barber_id']:o['prices'] for o in self.data['offerings']}
        self.assertEqual(offerings['ap']['head'],20)
        self.assertEqual(offerings['nick']['head'],25)
        self.assertEqual(offerings['nick']['face'],25)
        self.assertNotIn('vip',offerings['nick']); self.assertNotIn('beard',offerings['nick'])
        rendered={}; service=None
        for tag,a in self.doc.nodes:
            if tag=='tr' and 'data-service' in a: service=a['data-service']
            if tag=='td' and 'data-price' in a: rendered[(a['data-barber'],service)]=float(a['data-price'])
        self.assertEqual(rendered,{(b,s):p for b,prices in offerings.items() for s,p in prices.items()})
    def test_anchors_assets_and_external_links(self):
        ids=[a['id'] for _,a in self.doc.nodes if 'id' in a]
        self.assertEqual(len(ids),len(set(ids)))
        for tag,a in self.doc.nodes:
            if tag=='a' and a.get('href','').startswith('#'): self.assertIn(a['href'][1:],ids)
            if a.get('target')=='_blank': self.assertTrue({'noopener','noreferrer'}<=set(a.get('rel','').split()))
            if tag=='img': self.assertTrue((ROOT/a['src']).is_file()); self.assertTrue(a.get('alt'))
    def test_schema_agrees_with_visible_business(self):
        raw=self.page.split('<script type="application/ld+json">')[1].split('</script>')[0]
        schema=json.loads(raw)
        self.assertEqual(schema['address']['streetAddress'],'110 West Maple')
        self.assertEqual(len(schema['employee']),2)
        for catalog,offering in zip(schema['hasOfferCatalog']['itemListElement'],self.data['offerings']):
            self.assertEqual([x['price'] for x in catalog['itemListElement']], [offering['prices'][s['id']] for s in self.data['services'] if s['id'] in offering['prices']])
    def test_invalid_business_records_block_publish(self):
        mutations=[lambda d:d['assignments'].append(d['assignments'][0]),lambda d:d['offerings'][0]['prices'].update(head=-2),lambda d:d['assignments'][0].update(booking_url='https://example.com/'),lambda d:d['locations'][0].update(status='planned'),lambda d:d['offerings'].pop()]
        for mutate in mutations:
            data=copy.deepcopy(self.data); mutate(data)
            with self.assertRaises(ValueError): validate(data)
    def test_text_is_escaped(self):
        data=copy.deepcopy(self.data); data['barbers'][0]['name']='<img src=x onerror=alert(1)>'
        self.assertNotIn('<img src=x',render(data))
    def test_essential_content_is_static(self):
        html=self.page.split('<script>')[0]
        for text in ['Adam Phillips','Nick Wallen','Services &amp; prices.','110 West Maple','$35']:
            self.assertIn(text,html)
        self.assertIn('prefers-reduced-motion:reduce',html)
        self.assertNotIn('opacity:0',html)

if __name__=='__main__': unittest.main()
