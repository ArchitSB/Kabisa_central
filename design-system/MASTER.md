# Kabisa Admin Design System

> Global source of truth. Page-specific files in `design-system/pages/` may only
> override rules explicitly documented there. This file overrides generic tool
> recommendations wherever the build brief supplies an exact value.

**Project:** Kabisa Admin Panel

**Profile:** B2B pharmaceutical operations · analytics dashboard · data-dense executive UI

**Design reference:** Written Redseer admin description supplied in the build brief. The reference screenshot was not attached, so layout fidelity is based on the quantified written pattern and exact Kabisa tokens.

**Generated:** 2026-07-26

## Design direction

Kabisa is calm, exact, and operational. The interface pairs an editorial
Fraunces hierarchy with compact Inter data UI. A near-black sidebar anchors a
warm, light workspace. Teal is used with discipline: deep teal for actions and
true logo teal for focus, charts, and accents. Cards rely on borders and very
soft elevation instead of decorative effects.

The UI/UX Pro Max dashboard recommendation was used for spacing, table
responsiveness, bulk actions, focus management, and pre-delivery checks. Its
generic blue/amber palette, dark-mode recommendation, and Fira typography are
intentionally replaced by the exact §4 Kabisa specification.

## Color

| Token | Value | Use |
|---|---:|---|
| `primary-50` | `#F4FAFC` | tinted hover and selected surfaces |
| `primary-100` | `#E4F2F6` | pale teal surface |
| `primary-200` | `#C4E2EA` | subtle teal border |
| `primary-300` | `#9ECFDC` | disabled accent |
| `primary-400` | `#74B7CB` | supporting chart tone |
| `primary-500` | `#50A0C0` | logo-true accent, focus, dark-surface link |
| `primary-600` | `#4187A6` | interactive accent |
| `primary-700` | `#366F8A` | primary button and active nav |
| `primary-800` | `#2C596F` | primary hover |
| `primary-900` | `#244A5C` | darkest brand text |
| `sidebar-bg` | `#101619` | fixed navigation |
| `sidebar-fg` | `#E6EAEC` | navigation text |
| `sidebar-fg-muted` | `#7C8A90` | section labels and metadata |
| `bg` | `#F6F7F6` | warm application background |
| `surface` | `#FFFFFF` | cards and tables |
| `border` | `#E8EAE9` | 1px dividers |
| `row-hover` | `#F9FAFA` | table row hover |
| `text` | `#14181A` | primary text |
| `text-secondary` | `#5A6672` | supporting copy |
| `text-muted` | `#68747E` | muted copy with WCAG AA contrast on white |
| `success` | `#1E7A4D` on `#E9F9F0` | approved, verified, delivered |
| `warning` | `#9A5C00` on `#FFF6E6` | pending, low stock, expiring |
| `danger` | `#C4382E` on `#FDECEA` | rejected, failed, destructive |
| `neutral` | `#5A6672` on `#EFF1F2` | draft, unassigned |

Never hardcode a currency symbol. Display the currency code read from
`settings.currency`; the Phase 0 preview uses `TZS` as seed-shaped dummy copy.

## Typography

- Display, page titles, wordmark: `Fraunces`, weight 500–600, tracking `-0.025em`.
- UI, body, forms, tables: `Inter`, weight 400–700.
- IDs and numeric codes: `JetBrains Mono`, weight 500, tabular numerals.
- Display: 36/42 desktop, 30/36 mobile.
- H1: 32/38 desktop, 28/34 mobile.
- H2: 24/31.
- H3: 18/26.
- Body: 14/22.
- Small: 13/19.
- Caption/overline: 11/16, weight 700, tracking `0.12em`.

## Layout and rhythm

- Base spacing unit: 4px; scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64.
- Fixed desktop sidebar: 260px. Tablet sidebar: 224px. Mobile: off-canvas.
- Main content: fluid with 1600px practical max; 24–40px desktop gutters, 16px mobile.
- List-page rhythm: page header → 24px → filter card → 16px → bulk row →
  12px → table → 16px → pagination.
- Data density is comfortable: 52–60px table rows, concise labels, no cramped cards.
- Responsive checkpoints: 375px, 768px, 1024px, and 1440px.
- Tables use an overflow container on narrow viewports; primary identity and action
  columns stay clear. No document-level horizontal scroll.

## Shape, border, and elevation

- Card radius: 14px.
- Input and button radius: 10px.
- Badge and row-action radius: 9999px.
- Border: 1px solid `#E8EAE9`.
- Card shadow: `0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06)`.
- Elevated drawer shadow: `0 24px 64px rgba(16,24,40,.16)`.
- Avoid glassmorphism, glow, deep gradients, and layout-shifting hover transforms.

## Component language

- Primary actions: deep teal fill, white text, 40px minimum height.
- Secondary actions: white, subtle border, dark text.
- Row actions: compact outlined pills labelled with verbs; icons supplement text.
- Inputs: visible labels, 42px height, pale background, teal border and 3px focus halo.
- Filter cards: bordered white surface with aligned controls and a clear reset action.
- Status badges: icon or dot plus text; color is never the only signal.
- Data tables: selectable rows, sortable headers, right-aligned numeric columns,
  visible hover and keyboard focus.
- Drawers: right-side panel, focus trapped, labelled close button, focus returned to trigger.
- Empty/loading/error states are calm and direct. Lottie is reserved for a small
  verification success state in a later phase, with a static reduced-motion fallback.

## Motion identity

**Personality:** corporate/calm. Motion confirms state and spatial relationship.

- Signature easing: `cubic-bezier(0.2, 0, 0, 1)`.
- Duration palette: 120ms micro, 220ms standard, 320ms spatial.
- Entrance: 8–16px translate plus opacity, decelerating.
- Exit: shorter accelerate curve.
- Hover: color, border, or shadow only; no decorative scale.
- Drawer: 320ms slide; overlay fades in 180ms.
- Table row insertion/removal: 180–240ms with a total stagger under 200ms.
- Animate only `transform` and `opacity` for spatial movement.
- `prefers-reduced-motion` removes spatial movement and shortens or disables motion.
- No continuous ambient animation in the admin shell.

## Accessibility and pre-delivery checklist

- [ ] Normal text contrast is at least 4.5:1; large text at least 3:1.
- [ ] All interactive elements show a visible `primary-500` focus ring.
- [ ] All icon-only controls have accessible names and 40px touch targets.
- [ ] Labels, icons, or text accompany status colors.
- [ ] Modal and drawer focus is trapped and restored.
- [ ] Clickable controls use the pointer cursor and stable hover feedback.
- [ ] Motion is 120–320ms, functional, and reduced-motion safe.
- [ ] No emojis substitute for Lucide icons.
- [ ] 375/768/1024/1440 layouts have no document-level horizontal overflow.
- [ ] Loading, empty, error, and disabled states are legible.
- [ ] All UI copy lives outside JSX where practical for later localization.

## Explicitly forbidden in the admin

Three.js, particle systems, custom cursors, SiriOrb, DynamicIsland, FluidMorph,
MatrixCard, CursorFollow, ScrambleHover, WaveText, and TypewriterText. SmoothUI
may only be cherry-picked from the allowlist recorded in the frontend registry policy.
