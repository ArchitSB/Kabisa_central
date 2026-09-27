# Kabisa native customer app

Expo Router / SDK 54, consuming `@kabisa/core`, `@kabisa/api-client` and `@kabisa/design-tokens` without platform forks. This is the implemented app requested in the conversation, beyond the original placeholder brief.

From repository root: `pnpm dev:mobile`. See [release and local-device instructions](../../docs/MOBILE_READINESS.md). Run `pnpm --filter @kabisa/mobile typecheck`, `lint`, and `build`. Build exports Android Hermes JavaScript; EAS preview produces an installable APK after company Expo setup. Never put secrets in `EXPO_PUBLIC_*` variables.
