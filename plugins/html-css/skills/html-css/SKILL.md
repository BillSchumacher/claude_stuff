---
name: html-css
description: "HTML/CSS best practices: semantic markup, responsive images, CSS custom properties, Grid/Flexbox, fluid typography, dark mode"
---

# HTML / CSS

## HTML structure

1. **DOCTYPE, charset, viewport are non-negotiable.** Every HTML file starts with `<!DOCTYPE html>`, `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">`.
2. **Minimal markup — no unnecessary wrapper divs.** Before adding a `<div>`, check if a semantic element fits.
3. **Void elements have no closing tag.** `<br>`, `<img>`, `<input>`, `<meta>`, `<link>` — no `/>` needed in HTML5.
4. **Boolean attributes need no value.** `defer`, `async`, `required`, `open`, `muted` — not `defer="defer"`.
5. **`data-*` attributes for JS hooks, not classes.** Separate behavior from styling.

## Script and image loading

6. **`defer` by default for scripts.** `async` for independent scripts (analytics). `type="module"` for ES modules. Never bare `<script src>` (blocks rendering).
7. **Images: always `width`/`height` for CLS, `srcset`/`sizes` for responsive, `loading="lazy"` below fold.** `fetchpriority="high"` for hero images.
8. **`<picture>` for format fallback and art direction.** AVIF → WebP → JPEG/PNG. Different crops for narrow screens via `media` attribute.

## SEO and meta

9. **Open Graph meta tags:** `og:title`, `og:description`, `og:image`, `og:url`. Twitter card. Canonical URL.
10. **Favicon: SVG preferred** with PNG fallback and apple-touch-icon. SVG can adapt to dark mode.

## CSS custom properties

11. **All design tokens as custom properties.** Colors, spacing, radii, fonts on `:root`. Components reference `var(--token)`.
12. **`oklch()` for perceptually uniform colors.** `color-mix(in oklch, ...)` for derived shades.

## CSS layout

13. **Grid for 2D, Flexbox for 1D, never floats for layout.** `repeat(auto-fill, minmax(min(300px, 100%), 1fr))` for responsive grids without media queries.
14. **Container queries** (`@container`) for component-scoped responsive design. Component responds to its container, not viewport.
15. **`:has()` for parent/relational selection.** Style parent based on child state, e.g., `.form-group:has(:invalid)`.

## CSS modern features

16. **Native CSS nesting.** Nest selectors, pseudo-classes, and media queries inside rules. Reduces repetition.
17. **`clamp()` for fluid typography and spacing.** `clamp(1rem, 0.93rem + 0.28vw, 1.25rem)` scales smoothly between breakpoints.
18. **`aspect-ratio` for consistent media sizing.** `16/9` for video, `1` for avatars, `3/2` for thumbnails.
19. **Logical properties over physical.** `margin-inline`, `padding-block`, `border-inline-start`, `text-align: start`. Works in RTL.

## CSS quality

20. **`rem`/`em` for typography and spacing, not `px`.** px only for borders, shadows, fine details. Respects user font preferences.
21. **Low specificity selectors.** Single class preferred. `:where()` for zero-specificity resets. Avoid `!important` and long selector chains.
22. **Performance: `contain`, `content-visibility`, `will-change` sparingly.** `content-visibility: auto` skips rendering off-screen sections.

## Media queries

23. **`prefers-reduced-motion: reduce`** — disable/reduce all animations and transitions.
24. **Dark mode** via `prefers-color-scheme: dark` or class-based toggle. Use custom properties for all colors.
25. **Print styles** via `@media print` — hide nav/sidebar, avoid break-inside on cards, show link URLs.
