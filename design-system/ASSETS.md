# Kabisa web assets

Both portals use the supplied red/navy logo at `public/images/kabisa-logo.png`, with their own layout and styles. Admin's login illustration is built from CSS and Lucide icons. Product fallback drawings are interface elements, not inventory photographs.

The current storefront uses `apps/store-web/public/images/pharmacy-partner.webp` and the labelled fictional demo product images `demo-dressings.webp`, `demo-thermometer.webp` and `demo-gloves.webp`. Illustrations must not imply actual customers, endorsements or product evidence. Real product images are managed in the admin catalog; homepage imagery is configurable under Storefront → Banners.

The older `kabisa-care-hero.png` / `.webp` assets are retained for earlier references and the deferred native app. They depict unbranded healthcare supplies and are not the current storefront's design direction.

## Fonts

The current web interfaces use locally hosted Inter. Admin's copy is `apps/admin-web/src/assets/fonts/inter-latin.woff2`. Storefront font licences are in `apps/store-web/public/font-licenses.txt`. Existing Fraunces assets may remain for earlier/native references; the current admin does not use them.

The source packages are locked Fontsource variable fonts. The existing `scripts/subset_store_fonts.py` script rebuilds storefront subsets in an environment with `fonttools[woff]`; ordinary builds do not need font tooling.
