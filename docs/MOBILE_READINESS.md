# Native app and release readiness

An actual Expo app is implemented in `apps/mobile`, following the user's direct request. Expo Router mirrors the customer store: Home, Catalog, Product, Quick Order, Basket, Checkout, Login/Register/Reset, Account sections, Order detail, FAQs and policies. SecureStore stores rotating sessions; native document picking and sharing support private certificates, prescriptions and invoices. Guest baskets persist separately without prices. The core and transport packages are shared unchanged.

## Local use

```bash
pnpm install
pnpm dev:mobile
# Expo web rendering for local UI inspection:
pnpm --filter @kabisa/mobile web # http://localhost:8082
# Native JavaScript/Hermes export (does not produce an installable APK):
pnpm --filter @kabisa/mobile build
```

SDK 54 uses React Native 0.81 and React 19.1, isolated from the web apps. Android emulator default API: `http://10.0.2.2:8000/api/v1/store`. For a physical phone, copy `apps/mobile/.env.example` to `.env.local`, set `EXPO_PUBLIC_API_URL` and `EXPO_PUBLIC_STORE_URL` to reachable hosts, and restart Metro. Bind the development API to the LAN only when needed. Production URLs must be HTTPS. Public Expo variables contain URLs, never database or gateway secrets. See [Expo monorepos](https://docs.expo.dev/guides/monorepos/) and [SecureStore](https://docs.expo.dev/versions/v54.0.0/sdk/securestore/).

For a physical phone on the same Wi-Fi, set the public URLs to your computer's LAN address (replace the example address below):

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000/api/v1/store
EXPO_PUBLIC_STORE_URL=http://192.168.1.10:5174
```

Use an Expo Go client compatible with SDK 54, or the EAS preview APK described below.

Start the API with `uvicorn app.main:app --app-dir apps/api --host 0.0.0.0 --reload`, the storefront with `pnpm --filter @kabisa/store-web dev --host 0.0.0.0`, then `pnpm dev:mobile` and scan the Expo QR code. The storefront host supplies admin-configured public images; native's default hero is also bundled. Use the emulator's `10.0.2.2` default only inside the Android emulator.

## Signing and distribution

Configured Android application ID / iOS bundle ID: `tz.co.kabisapharma.store`; scheme: `kabisa`; initial version 1.0.0. Confirm ownership before first release, then keep the app ID stable. EAS uses remote build versioning and production auto-increment. `eas.json` has preview APK and production AAB profiles. Link the project to the company's Expo account, set production URL variables, configure signing, and run `eas build --platform android --profile preview` for device QA or `--profile production` for the store artifact. EAS account/project IDs and signing credentials are intentionally not fabricated. See [Expo build setup](https://docs.expo.dev/build/setup/) and [Android submission](https://docs.expo.dev/submit/android/).

Native bundle export is a compilation check. It is not evidence of installation, physical-device behavior or Play approval. Before release, test a signed APK on the target Android phones, including large text, screen reader, reduced motion, slow network/retry, background/foreground session restoration, document upload and share-sheet invoice download. Complete iOS signing/device QA separately if shipping iOS.

## Play Console checklist

- Company developer account, verified ownership, package ID, upload signing key/Play App Signing, version code and staged test track.
- Real screenshots, support contact, privacy-policy URL and account/data deletion request flow in-app and on the web. Account deletion fulfillment and any business-record retention policy need company approval; the current security screen supports session revocation, not account deletion.
- Publish reviewed Privacy/Terms/Returns pages from Admin → Storefront. Intended privacy URL: `https://store.kabisapharma.co.tz/pages/privacy`; the seed keeps it draft.
- Complete the Health apps declaration and disclose the pharmacy functionality. This is licensed-business procurement; verification is enforced on orders. That framing does **not** exempt the app from health policies or permit unsupported claims. Confirm product/licensing eligibility with the company's compliance owner. [Google health declaration](https://support.google.com/googleplay/android-developer/answer/14738291?hl=en), [Health Content and Services](https://support.google.com/googleplay/android-developer/answer/16679511?hl=en-GB).
- Data Safety disclosures must match actual collection: contact/business identity, delivery address, orders/payment records, submitted business files and purchase authorizations. No background location, microphone, advertising or analytics SDK is implemented. Remote push remains inactive. Document the configured gateway's processing and retention before declaring data practices.
- Audit the final merged Android manifest: document picker uses system selection, invoice sharing uses temporary files; broad external storage and microphone permissions are blocked in app config. Network access is required. SecureStore protects tokens. No medical diagnosis or treatment advice is provided by the app.

Remaining external release work: company-approved policies and deletion process, live message gateway, public TLS domains, real inventory photography, Expo/Play credentials, signed-device QA and store review. No live payment aggregator or push service was requested for this phase.
