# Hometown Men's Grooming Lounge

Premium heritage booking hub for the open Stilwell shop at 110 West Maple.

## Update the website

Edit `shop-data.json` for prices, services, hours, phone numbers, and booking links. Verify changes against each barber's Squire menu and update `services_verified_on`. Then run:

```sh
python3 build.py
python3 -m unittest -v
node --check site.js
```

Commit both source files and generated `index.html`, `preview.html`, and `sitemap.xml`. GitHub Pages publishes the root of `main`. `preview.html` redirects to the main page and is excluded from indexing.

## What is underneath

- Complete static HTML: prices, contact details, and booking links remain available when JavaScript is unavailable.
- Separate location, barber, service, assignment, and offering records. This supports location-specific prices and booking links when a second shop is confirmed. The public website currently represents only the open Stilwell shop. A future multi-shop navigation/page rollout still needs to be built and verified.
- Build validation rejects invalid or duplicate assignments, missing offerings, unsafe booking destinations, and invalid prices.
- Prices on the page and search-engine structured data come from the same records.
- Responsive semantic service table, keyboard focus, skip navigation, reduced motion, limited decorative animation, and an accessible contextual booking bar.
- Search/social metadata, sitemap, explicit image sizing and prioritized logo loading.
- `hometown:action` is a local event hook for future booking/call/direction analytics. No analytics provider, cookies, personal data collection, backend, or automated Squire synchronization is enabled. These events indicate clicks, not completed appointments.

## Files

`styles.css` and `site.js` are the editable design and enhancement sources; the builder embeds them in the public HTML. `icons.json`, `logo.avif`, and `og-cover.png` preserve the original brand assets.

## Recovery

The previous live website is preserved at commit `90406a3cb8c3ed26bab4bf973e7315679f762c8c`. Restore its page files in a new commit if needed; keep a working custom-domain `CNAME` configuration unless intentionally changing the domain.
