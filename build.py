"""Build a complete, dependency-free public page from validated business records."""
from pathlib import Path
from html import escape
from urllib.parse import urlparse
import hashlib
import json

ROOT = Path(__file__).resolve().parent

def validate(data):
    def unique(records, key):
        values = [x[key] for x in records]
        if len(values) != len(set(values)):
            raise ValueError(f'Duplicate {key}')
    for field in ('locations', 'barbers', 'services'):
        unique(data[field], 'id')
    locations = {x['id']: x for x in data['locations']}
    barbers = {x['id']: x for x in data['barbers']}
    services = {x['id']: x for x in data['services']}
    if data['active_location'] not in locations:
        raise ValueError('Unknown active location')
    if locations[data['active_location']]['status'] != 'open':
        raise ValueError('Cannot publish a location that is not open')
    if urlparse(data['site_url']).scheme != 'https':
        raise ValueError('Public URL must use HTTPS')
    assignments = set()
    for a in data['assignments']:
        pair = (a['location_id'], a['barber_id'])
        if pair in assignments or pair[0] not in locations or pair[1] not in barbers:
            raise ValueError('Invalid or duplicate barber assignment')
        assignments.add(pair)
        parsed = urlparse(a['booking_url'])
        if parsed.scheme != 'https' or parsed.hostname != 'getsquire.com':
            raise ValueError('Expected a secure Squire booking URL')
        if not a['days'] or a['opens'] >= a['closes']:
            raise ValueError('Invalid barber hours')
    offerings = set()
    for offering in data['offerings']:
        pair = (offering['location_id'], offering['barber_id'])
        if pair not in assignments or pair in offerings:
            raise ValueError('Offerings must have one valid barber/location assignment')
        offerings.add(pair)
        for service, price in offering['prices'].items():
            if service not in services or isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
                raise ValueError('Unknown service or invalid price')
    for loc in locations.values():
        if len(loc['barbers']) != len(set(loc['barbers'])):
            raise ValueError('Repeated barber in location')
        for barber in loc['barbers']:
            if (loc['id'], barber) not in assignments or (loc['id'], barber) not in offerings:
                raise ValueError('Every location barber needs hours, booking, and offerings')

def render(data):
    validate(data)
    e = lambda value: escape(str(value), quote=True)
    loc = next(x for x in data['locations'] if x['id'] == data['active_location'])
    barbers = {x['id']:x for x in data['barbers']}
    crew = [barbers[key] for key in loc['barbers']]
    assignments = {x['barber_id']:x for x in data['assignments'] if x['location_id'] == loc['id']}
    prices = {x['barber_id']:x['prices'] for x in data['offerings'] if x['location_id'] == loc['id']}
    icons = json.loads((ROOT/'icons.json').read_text())
    def icon(name):
        return icons[name].replace('<svg ', '<svg aria-hidden="true" focusable="false" ')
    def book(barber, placement):
        secondary = ' secondary' if barber['id'] != crew[0]['id'] else ''
        return f'<a class="button{secondary}" href="{e(assignments[barber["id"]]["booking_url"])}" target="_blank" rel="noopener noreferrer" data-action="booking" data-location="{e(loc["id"])}" data-barber="{e(barber["id"])}" data-placement="{placement}">{e(barber["book_label"])}<span class="sr-only"> (opens in Squire in a new tab)</span></a>'
    def pair(placement, observed=True):
        return '<div class="booking-pair"'+(' data-booking-zone' if observed else '')+'>'+''.join(book(b, placement) for b in crew)+'</div>'
    cards=[]
    for b in crew:
        a=assignments[b['id']]
        phone = f'<a class="social-link" href="tel:{e(b["phone"])}" data-action="call" data-barber="{e(b["id"])}">{icon("phone")}{e(b["phone_display"])}</a>' if b.get('phone') else ''
        cards.append(f'''<article class="barber-card {e(b['id'])}" aria-labelledby="barber-{e(b['id'])}">
<div class="barber-top"><span class="initials" aria-hidden="true">{e(b['initials'])}</span><div><p class="role">{e(b['role'])}</p><h3 id="barber-{e(b['id'])}">{e(b['name'])}</h3></div></div>
<p class="barber-hours"><span>{e(a['days_display'])}</span><span>{e(a['hours_display'])}</span></p>
<div class="barber-actions" data-booking-zone>{book(b,'barber-card')}</div>
<div class="barber-footer">{phone}<a class="social-link" href="{e(b['instagram_url'])}" target="_blank" rel="noopener noreferrer" data-action="instagram" data-barber="{e(b['id'])}">{icon('instagram')}{e(b['instagram_handle'])}<span class="sr-only"> (opens in a new tab)</span></a></div></article>''')
    rows=[]
    category=None
    for s in data['services']:
        if not any(s['id'] in prices[b['id']] for b in crew):
            continue
        if s['category'] != category:
            category=s['category']
            rows.append(f'<tr class="group"><th colspan="{len(crew)+1}" scope="colgroup">{e(category)}</th></tr>')
        minutes=s['duration_minutes']
        duration=f'{minutes//60} hr {minutes%60} min' if minutes>=60 else f'{minutes} min'
        detail=e(s.get('detail',''))
        detail=(detail+' · ' if detail else '')+duration
        cells=''.join(f'<td data-barber="{e(b["id"])}" data-price="{prices[b["id"]][s["id"]]}">${prices[b["id"]][s["id"]]:g}</td>' if s['id'] in prices[b['id']] else f'<td data-barber="{e(b["id"])}"><span class="not-offered">Not offered</span></td>' for b in crew)
        rows.append(f'<tr data-service="{e(s["id"])}"><th scope="row"><span class="service-name">{e(s["name"])}</span><span class="service-detail">{detail}</span></th>{cells}</tr>')
    hours=''.join(f'<div class="hours-row"><strong>{e(b["name"])}</strong><span>{e(assignments[b["id"]]["days_display"])}<br>{e(assignments[b["id"]]["hours_display"])}</span></div>' for b in crew)
    url=data['site_url'].rstrip('/')+'/'
    title=data['brand']+' — '+loc['name']+', OK'
    city = e(loc['address']['city'])
    region = e(loc['address']['region'])
    address_line = e(loc['address']['street']) + ' · ' + city + ', ' + region
    chair_count = {1:'One',2:'Two',3:'Three',4:'Four'}.get(len(crew),str(len(crew)))
    day_count = len({day for a in assignments.values() for day in a['days']})
    day_label = {5:'Five',6:'Six',7:'Seven'}.get(day_count,str(day_count))
    description=f"Cuts, beards and straight razor shaves in {loc['address']['city']}, {loc['address']['region']}. View services and prices. Book with {' or '.join(b['name'] for b in crew)} through Squire."
    schema={'@context':'https://schema.org','@type':'HairSalon','@id':url+'#'+loc['id'],'name':data['brand'],'url':url,'description':description,'image':url+'og-cover.png','telephone':loc['phone'],'address':{'@type':'PostalAddress','streetAddress':loc['address']['street'],'addressLocality':loc['address']['city'],'addressRegion':loc['address']['region_code'],'addressCountry':loc['address']['country']},'employee':[{'@type':'Person','name':b['name'],'jobTitle':b['role'],'sameAs':b['instagram_url']} for b in crew]}
    day_hours={}
    for a in assignments.values():
        for day in a['days']:
            current=day_hours.get(day,(a['opens'],a['closes']))
            day_hours[day]=(min(current[0],a['opens']),max(current[1],a['closes']))
    schema['openingHoursSpecification']=[{'@type':'OpeningHoursSpecification','dayOfWeek':day,'opens':times[0],'closes':times[1]} for day,times in day_hours.items()]
    schema['hasOfferCatalog']={'@type':'OfferCatalog','name':'Services','itemListElement':[{'@type':'OfferCatalog','name':b['name'],'itemListElement':[{'@type':'Offer','price':prices[b['id']][s['id']],'priceCurrency':'USD','url':assignments[b['id']]['booking_url'],'itemOffered':{'@type':'Service','name':s['name']}} for s in data['services'] if s['id'] in prices[b['id']]]} for b in crew]}
    css=(ROOT/'styles.css').read_text()
    js=(ROOT/'site.js').read_text()
    build_id=hashlib.sha256((json.dumps(data,sort_keys=True)+css+js+Path(__file__).read_text()).encode()).hexdigest()[:12]
    schema_json=json.dumps(schema,ensure_ascii=False).replace('<', chr(92)+'u003c')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title><meta name="description" content="{e(description)}"><meta name="theme-color" content="#11130f"><meta name="color-scheme" content="dark light"><meta name="referrer" content="strict-origin-when-cross-origin"><meta name="hometown-build" content="{build_id}">
<link rel="canonical" href="{e(url)}"><link rel="icon" href="logo.avif"><link rel="preload" href="logo.avif" as="image" type="image/avif">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(data['brand'])}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(url)}og-cover.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Hometown Men's Grooming Lounge emblem"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(description)}"><meta name="twitter:image" content="{e(url)}og-cover.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,400;1,500&amp;family=Manrope:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
<style>{css}</style>
<script type="application/ld+json">{schema_json}</script>
</head>
<body data-location="{e(loc['id'])}">
<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap header-inner"><a class="wordmark" href="#top" aria-label="Hometown Men's Grooming Lounge home"><img src="hometown-wordmark.png" width="1920" height="832" alt="Hometown Men’s Grooming Lounge" decoding="async"></a><nav class="nav" aria-label="Main navigation"><a href="#barbers">Barbers</a><a href="#services">Services</a><a href="#visit">Visit</a><a class="nav-book" href="#barbers">Book a chair</a></nav></div></header>
<main id="main">
<section class="hero" id="top" aria-labelledby="hero-title"><div class="wrap hero-inner"><div class="hero-copy"><p class="eyebrow">LOOK GOOD · FEEL CONFIDENT · STAY LOCAL</p><h1 id="hero-title">{city}’s<br><em>barbershop.</em></h1><p class="hero-description">Cuts, beards and straight razor shaves.<br>{chair_count} chairs. {day_label} days a week.</p>{pair('hero')}<p class="hero-note">Choose your barber. Booking opens in Squire.</p></div><div class="hero-art"><div class="poles" aria-hidden="true"><div class="pw l"><div class="cap"></div><div class="pole"><i></i><b></b></div><div class="cap"></div></div><div class="pw r"><div class="cap"></div><div class="pole"><i></i><b></b></div><div class="cap"></div></div></div><img class="hero-logo" src="logo.avif" width="350" height="350" alt="Hometown Men's Grooming Lounge emblem" fetchpriority="high"><p class="logo-caption">{city}, {region}</p></div></div><div class="wrap hero-base"><p>{address_line}</p><a class="scroll-link" href="#services">Explore services &amp; prices</a></div></section>
<section class="section barbers" id="barbers" aria-labelledby="barbers-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow"><span class="section-number">01</span>The chairs</p><h2 id="barbers-title">Who’s cutting.</h2></div><p>Pick your barber.<br>We’ll take you to his booking page.</p></div><div class="crew">{''.join(cards)}</div></div></section>
<section class="section services" id="services" aria-labelledby="services-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow"><span class="section-number">02</span>The menu</p><h2 id="services-title">Services &amp; prices.</h2></div><p>Find your service.<br>See each barber’s price.</p></div><div class="menu-wrap"><table class="menu"><caption class="sr-only">Services, appointment durations, and prices in US dollars for each barber at {city}.</caption><thead><tr><th scope="col">Service</th>{''.join(f'<th scope="col">{e(b["book_label"].removeprefix("Book "))}</th>' for b in crew)}</tr></thead><tbody>{''.join(rows)}</tbody></table></div><div class="menu-foot"><p>Prices and appointment durations are listed from Squire. Your selected barber’s booking page confirms the final details.</p><a href="#barbers">Choose your barber</a></div></div></section>
<section class="section visit" id="visit" aria-labelledby="visit-title"><div class="wrap visit-grid"><div><p class="eyebrow"><span class="section-number">03</span>Find us</p><h2 id="visit-title">Come see us.</h2><address class="address">{e(loc['address']['street'])}<br>{e(loc['address']['city'])}, {e(loc['address']['region'])}</address><div class="visit-actions"><a class="text-link" href="{e(loc['directions_url'])}" target="_blank" rel="noopener noreferrer" data-action="directions">{icon('directions')}Get directions<span class="sr-only"> (opens in a new tab)</span></a><a class="text-link" href="tel:{e(loc['phone'])}" data-action="call">{icon('phone')}{e(loc['phone_display'])}</a></div></div><div class="hours-panel"><h3>Hours by barber</h3>{hours}</div></div></section>
<section class="closing" aria-labelledby="closing-title"><div class="wrap"><p class="eyebrow">Ready when you are</p><h2 id="closing-title">Grab the chair.</h2>{pair('footer')}<div class="closing-brand"><img src="hometown-wordmark.png" width="1920" height="832" alt="Hometown Men’s Grooming Lounge" loading="lazy" decoding="async"></div></div></section>
</main>
<footer class="footer"><div class="wrap footer-inner"><p class="footer-brand">Hometown Men’s Grooming Lounge</p><p>{address_line}</p><a href="https://getsquire.com/" target="_blank" rel="noopener noreferrer">Booking by Squire<span class="sr-only"> (opens in a new tab)</span></a></div></footer>
<aside class="dock" aria-label="Quick booking" aria-hidden="true" inert data-visible="false"><div class="dock-inner"><p class="dock-label">Your next good cut.<small>{city.upper()}, {region.upper()}</small></p>{pair('sticky',False)}</div></aside>
<script>{js}</script>
</body></html>'''

def build():
    data=json.loads((ROOT/'shop-data.json').read_text())
    page=render(data)
    (ROOT/'index.html').write_text(page)
    url=data['site_url'].rstrip('/')+'/'
    (ROOT/'preview.html').write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><link rel="canonical" href="{escape(url)}"><meta http-equiv="refresh" content="0;url=./"><title>Hometown — Website</title><body><p><a href="./">Continue to Hometown Men’s Grooming Lounge</a></p></body></html>')
    (ROOT/'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{escape(url)}</loc></url></urlset>\n')
    print(f'Built {len(page.encode()):,} byte website; all public content is present without JavaScript.')

if __name__=='__main__':
    build()
