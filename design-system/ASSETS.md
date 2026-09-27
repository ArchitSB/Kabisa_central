# Storefront assets

The generated editorial source is `apps/store-web/public/images/kabisa-care-hero.png`; web and Expo use the optimized 900px WebP (`kabisa-care-hero.webp`, about 35KB). The Expo copy is `apps/mobile/assets/care-hero.webp`. It illustrates healthcare supplies and never substitutes for actual product photography.

Generation brief: premium photographic still life on warm ivory and pale aqua sculptural plinths; unbranded matte white medicine bottle with teal lid, blank white carton, amber bottle, sealed silver blister and a small leaf. Soft morning sunlight, tactile glass and paper, no people, labels, logos, readable text, watermarks or medical claims. Preserve space for surrounding editorial typography. Generated using the imagegen skill.

Icons use the Kabisa K mark with a teal dot. Product fallback illustrations are native/vector UI elements and are not inventory photos. Product images can be uploaded in the existing admin catalog; homepage images are editable in Storefront → Banners.

## Web fonts

The storefront carries local Inter and Fraunces web subsets covering Latin, Latin-1, punctuation and currency symbols at weights 400–700. This retains every weight used by the design, including 550/560/650. Native retains its bundled Google Fonts. Other scripts fall back to the system font.

Source: the locked `@fontsource-variable/inter` and `@fontsource-variable/fraunces` packages. Font licences ship in `apps/store-web/public/font-licenses.txt`. Rebuild the subsets with `python scripts/subset_store_fonts.py` in an environment containing `fonttools[woff]`; no font tool is needed for ordinary builds.
