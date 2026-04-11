---
name: accessibility
description: "HTML accessibility: semantic elements, WCAG 2.2 AA compliance, ARIA patterns, keyboard navigation, color contrast"
---

# Accessibility (HTML / WCAG 2.2 / ARIA)

When generating HTML, apply every applicable rule below. Accessibility is not optional — it is a core quality requirement.

## Semantic HTML

1. **Heading hierarchy must not skip levels.** One `<h1>` per page, then `<h2>`, `<h3>`, etc. Never `<h1>` → `<h3>`.
2. **Use landmark elements.** Every page: `<header>`, `<nav>`, `<main>`, `<footer>`. Use `<aside>` for supplementary content. Only one `<main>`.
3. **Use list elements for lists.** `<ul>` unordered, `<ol>` ordered, `<dl>`/`<dt>`/`<dd>` for name-value pairs. Never a stack of `<div>`s.
4. **`<button>` for actions, `<a>` for navigation.** If it triggers an in-page action, `<button>`. If it navigates to a URL, `<a href>`. Never `<div onclick>` or `<a href="#">`.
5. **`<fieldset>` + `<legend>` for related form controls.** Radio groups, address fields, checkbox groups.
6. **`<figure>` + `<figcaption>` for captioned media.** `alt` still describes the image; `<figcaption>` is the visible caption.
7. **`<time datetime="...">` for dates/times.** Machine-parseable datetime attribute.
8. **No div/span soup.** Before writing `<div>`, check `<section>`, `<article>`, `<nav>`, `<details>`, `<summary>`, `<mark>`, `<address>`, `<blockquote>`.

## WCAG 2.2 AA

9. **Every `<img>` must have `alt`.** Meaningful images: descriptive text. Decorative: `alt=""` (empty, not omitted).
10. **Color contrast AA ratios.** Normal text: 4.5:1. Large text (24px+ / 18.66px+ bold): 3:1. UI components: 3:1 against adjacent colors.
11. **All interactive elements keyboard-accessible.** Reachable via Tab, operable via Enter/Space. No keyboard traps.
12. **Visible focus indicators.** Never `outline: none` without replacement. Use `:focus-visible` with 2px solid outline, 3:1 contrast.
13. **Skip navigation link** as the first focusable element. Lets keyboard users bypass repetitive nav.
14. **Every input needs a `<label>`.** Use `<label for="id">` or wrap input inside `<label>`. Placeholder is not a label substitute.
15. **Associate errors with inputs via `aria-describedby`.** Set `aria-invalid="true"` on invalid inputs. Error must identify the field and describe how to fix it.
16. **Set `lang` on `<html>`.** Use `lang` on sub-elements when language changes inline.
17. **Manage focus after dynamic content changes.** Move focus to new content after SPA navigation, modal open, or inline expansion. Never leave focus on an invisible element.
18. **Respect `prefers-reduced-motion`.** Disable or reduce animations for users who request it.
19. **Touch targets minimum 24x24 CSS pixels** (WCAG 2.5.8 AA). 44x44px recommended. Ensure spacing between adjacent targets.

## ARIA

20. **First rule: don't use ARIA if native HTML works.** `<button>` over `<div role="button">`. `<nav>` over `<div role="navigation">`. Native elements provide keyboard behavior for free.
21. **No redundant roles.** Never `role="button"` on `<button>`, `role="navigation"` on `<nav>`, `role="heading"` on `<h2>`.
22. **`aria-label` vs `aria-labelledby` vs `aria-describedby`.** `aria-label`: accessible name as string (no visible label). `aria-labelledby`: points to visible label element(s). `aria-describedby`: supplementary description (hints, errors).
23. **`aria-live` for dynamic status updates.** `"polite"` for non-urgent ("3 results found"). `"assertive"` for urgent (errors, session expiring). Or use `role="status"` / `role="alert"`. The live region must exist in the DOM before content is injected.
24. **`aria-expanded` + `aria-controls` for disclosure widgets.** Toggle `aria-expanded="true|false"` on trigger. Reference content panel ID.
25. **`aria-hidden="true"` for decorative/duplicate content.** Icons next to text labels, decorative separators. Never on focusable elements.
26. **`aria-current="page"` for navigation state.** Indicates the current page in nav links.
27. **Dialog pattern:** `<dialog>` or `role="dialog"`, `aria-modal="true"`, `aria-labelledby` to title. Trap focus inside. Return focus to trigger on close.
28. **Tabs pattern:** `role="tablist/tab/tabpanel"`, `aria-selected`, arrow keys between tabs, Tab key into panel. Connect via `aria-controls`/`aria-labelledby`.

## Sources

- https://www.w3.org/WAI/WCAG22/quickref/?versions=2.2&levels=aaa
- https://www.w3.org/WAI/ARIA/apg/
