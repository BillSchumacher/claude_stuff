---
name: maud
description: "Applies when writing or reviewing Maud HTML templates in Rust. Covers templating macros, components, escaping, and Axum integration."
---

# Maud

## Templating

1. **`html!` for all HTML generation.** Auto-escapes interpolated values. Never manual HTML strings.
2. **Components as plain functions returning `Markup`.** Idiomatic partials pattern.
3. **`PreEscaped` only for trusted, pre-sanitized HTML.** Every call is a potential XSS vector.

## Layout and control flow

4. **Base layout function** taking title and content parameters. Replaces template inheritance.
5. **`@if`, `@for`, `@match`, `@let` for control flow.**
6. **Boolean attributes: `[condition]` syntax.** `required[true]`, `disabled[!is_active]`. CSS shorthand: `div.container#main`.

## Integration

7. **Return `Markup` from Axum handlers** — implements IntoResponse with text/html.
8. **Compiles at compile time.** No runtime parsing. Template errors are compile errors.
9. **Arbitrary attribute names** for data-*, hx-*, aria-*.
10. **Split into small functions.** Large html! blocks slow compilation.
11. **`Render` trait for custom types** that render themselves in templates.
12. **Semicolon for empty elements:** `br;` not `br {}`.
