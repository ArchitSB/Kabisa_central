# Accessibility and responsive checklist

Phase 6 checked the shared shell and feature primitives against the Kabisa
design system and the ui-ux-pro-max pre-delivery criteria.

- Text/action color pairs use documented token combinations at or above the
  4.5:1 normal-text target; status is never communicated by color alone.
- Global `:focus-visible` styling is present, the skip link targets main
  content, drawers/dialogs manage focus, mobile navigation traps focus and
  closes with Escape, and tabs support arrows plus Home/End.
- Inputs have programmatic labels; icon-only controls have accessible names;
  decorative icons are hidden; tables keep semantic headings and horizontal
  overflow rather than clipping columns.
- Clickable controls have pointer affordance and practical touch targets;
  status toggles and primary-image controls were normalized for mobile use.
- `prefers-reduced-motion` removes non-essential animation. Feature motion
  remains within the established 120/220/320 ms system.
- The layout retains shared responsive behavior at 375, 768, 1024, and 1440 px:
  mobile drawer navigation, wrapping filter/action rows, scrollable data
  tables, and bounded drawers/content widths.
- Every data page uses shared loading, empty, and error states; a top-level
  error boundary provides a safe recovery screen for unexpected render errors.

Run keyboard-only and screen-reader smoke tests in the target production
browser/OS combination before each release, especially after changes to shared
drawers, tables, tabs, navigation, or forms.

## Customer web and native implementation

The storefront's production mobile Lighthouse accessibility score is **100**. Normal reading/action text is at least 12 px, contrast failures found in search, product metadata and footer text were corrected, and the brand's visible label matches its accessible name. Four responsive widths (375, 768, 1024 and 1440 px) were exercised across public and authenticated journeys, including order confirmation, with no horizontal overflow.

Browser checks exercised the Radix mobile navigation focus trap and Escape dismissal, reduced-motion behavior, labelled forms, status/empty/error feedback, and persistent EN/SW locale choice. Font subsetting retains all Latin/punctuation/currency glyphs needed for current English/Swahili UI; other scripts use system fallback. See [screenshots and QA report](STOREFRONT_BUILD_REPORT.md#verification-record).

The Expo preview was checked across public and signed-in account/product/order screens. Empty-string React Native children were removed; corrected routes emitted no console errors. Native browser rendering is not a substitute for TalkBack/VoiceOver, device font scaling, keyboard behavior and touch testing on a signed app. Those remain release device checks in [Mobile readiness](MOBILE_READINESS.md).
