---
name: tailwind
description: "Applies when styling with Tailwind CSS. Covers utility-first patterns, responsive design, dark mode, custom themes, and component extraction."
---

# Tailwind CSS

## Utility-first

1. **Prefer utility classes over custom CSS.** `className="flex items-center gap-4 p-4 rounded-lg bg-white shadow"`. Every class is a single CSS property.
2. **Use `@apply` sparingly** — only in component CSS files for repeated patterns. Overusing it defeats the utility-first approach.
3. **Extract component patterns into React/Vue components, not CSS classes.** A `<Card>` component with utility classes is better than a `.card` CSS class.

## Responsive design

4. **Mobile-first breakpoints.** Unprefixed styles apply to all sizes. `sm:`, `md:`, `lg:`, `xl:`, `2xl:` apply at that breakpoint and up.
5. **Stack vertically on mobile, horizontal on desktop:** `className="flex flex-col md:flex-row"`.

## Dark mode

6. **`dark:` prefix for dark mode styles.** `className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white"`.
7. **Set `darkMode: 'class'` in config** for manual toggle, or `'media'` for system preference.

## Configuration

8. **Customize in `tailwind.config.js`.** Extend colors, fonts, spacing under `theme.extend`. Don't override the entire theme.
9. **Set `content` paths correctly** to enable tree-shaking. Include all files with Tailwind classes: `content: ['./src/**/*.{js,ts,jsx,tsx}']`.
10. **Arbitrary values with square brackets:** `w-[300px]`, `text-[#1a2b3c]`, `grid-cols-[1fr_2fr]`.

## Patterns

11. **Group and peer modifiers** for parent/sibling state: `group-hover:opacity-100`, `peer-invalid:text-red-500`.
12. **Animations:** `animate-spin`, `animate-pulse`, `animate-bounce`. Custom with `@keyframes` in config.
13. **Ring for focus styles:** `focus:ring-2 focus:ring-blue-500 focus:ring-offset-2` for accessible focus indicators.
14. **Prose for content typography:** `@tailwindcss/typography` plugin with `prose` class for rendered markdown/HTML.
15. **Container queries** (3.4+) with `@container` for component-scoped responsive design.
