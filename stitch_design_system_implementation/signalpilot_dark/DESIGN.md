---
name: SignalPilot Dark
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#191b23'
  surface-container: '#1d2027'
  surface-container-high: '#272a31'
  surface-container-highest: '#32353c'
  on-surface: '#e1e2ec'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e1e2ec'
  inverse-on-surface: '#2e3038'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#10131a'
  on-background: '#e1e2ec'
  surface-variant: '#32353c'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  numeric-data:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  grid-margin: 40px
  grid-gutter: 20px
---

## Brand & Style

The design system is engineered to evoke a sense of quiet authority and precision, essential for a private wealth management context. The aesthetic follows a **Modern Corporate** direction with subtle **Minimalist** influences, focusing on information density without visual clutter.

The user experience is designed to be calm and professional, utilizing deep, receding background tones to allow high-value financial data to emerge at the forefront. The style prioritizes clarity and high-contrast legibility, ensuring that the interface feels like a sophisticated tool for decision-making rather than a consumer-grade app.

## Colors

The palette is anchored in a deep navy foundation to establish a premium, "private vault" atmosphere.

- **Primary & Secondary:** A vibrant blue (#3B82F6) serves as the primary action and focus color, while a soft emerald green (#10B981) is reserved for positive performance indicators and success states.
- **Neutrals:** The background uses a rich navy (#0F172A), contrasted by slate cards (#1E293B).
- **Functional Accents:** Use specialized "Alert Gold" (#F59E0B) for warnings and "Critical Red" (#EF4444) sparingly for negative market movements, ensuring they do not disrupt the overall calm of the interface.

## Typography

This design system utilizes **Manrope** exclusively to maintain a modern, balanced, and trustworthy feel.

- **High Contrast:** All primary text is rendered in Slate-50 (#F8FAFC) to ensure maximum readability against the dark background.
- **Hierarchy:** Use semi-bold and bold weights for data labels and headers to create a clear scan path.
- **Numeric Integrity:** For financial figures, enable tabular lining (tnum) to ensure decimal points and currency symbols align vertically in tables and lists.
- **Labels:** Use the "label-caps" style for small metadata and section headers to provide structural separation without using heavy lines.

## Layout & Spacing

The design system employs a **Fixed Grid** model for the main dashboard content, typically constrained to a 1440px maximum width to maintain information density and prevent eye strain on ultra-wide monitors.

- **Rhythm:** A 4px base unit drives all spacing.
- **Grid:** Use a 12-column grid system. For financial widgets, common widths include 3-column (quarter width), 4-column (one-third), and 6-column (half) spans.
- **Density:** Maintain generous "safe zones" around high-level portfolio summaries while increasing density within data-heavy tables and transaction logs.

## Elevation & Depth

Visual hierarchy in this design system is achieved through **Tonal Layering** rather than heavy shadows, preserving the sleek, modern aesthetic.

- **Layer 0 (Background):** #0F172A — The foundation of the app.
- **Layer 1 (Cards/Containers):** #1E293B — Raised elements where the primary interaction occurs.
- **Layer 2 (Modals/Popovers):** #334155 — The highest surface level, utilizing a subtle 1px border (#475569) to define edges.
- **Shadows:** Use very soft, long-range ambient shadows (0px 20px 40px rgba(0,0,0,0.4)) only on floating elements like dropdowns or modals to separate them from the card layer.

## Shapes

The shape language is **Soft** and restrained.

- **Containers:** Dashboard cards and containers use a 0.5rem (8px) radius. This provides a modern touch while maintaining a professional, structured look.
- **Action Elements:** Buttons and input fields follow the 0.25rem (4px) radius for a more precise, "technical" feel.
- **Selection States:** Use subtle rounded-sm (2px) corners for focus states and table row selections to keep the interface feeling crisp.

## Components

The components within the design system focus on high utility and data visualization.

- **Buttons:** Primary buttons use the vibrant blue (#3B82F6) with white text. Secondary buttons should be ghost-styled with a Slate-700 border.
- **Cards:** Essential for the wealth dashboard; they must feature a 1px border (#334155) to ensure they are distinct from the background.
- **Data Tables:** Use zebra-striping with a very subtle variance in slate tones. Hover states should highlight the entire row in a slightly lighter slate (#334155).
- **Charts:** Line charts should use the primary blue with a subtle gradient fill below the stroke. Positive performance is indicated by the soft green, and negative by a muted red.
- **Inputs:** Dark-filled fields (#0F172A) with a 1px border. On focus, the border transitions to the primary blue with a subtle outer glow.
- **Portfolio Specifics:** Include specialized "Trend Chips" that combine a sparkline with a percentage change indicator for a quick pulse-check on assets.