---
name: nextjs
description: "Applies when building or reviewing Next.js applications. Covers Server/Client Components, Server Actions, data fetching, Image optimization, and metadata."
---

# Next.js (App Router)

## Server vs Client Components

1. **Default to Server Components.** Only add `'use client'` when you need interactivity (useState, useEffect, event handlers, browser APIs). Server Components reduce bundle size and can directly access databases/filesystems.
2. **Push `'use client'` as far down the tree as possible.** Wrap only the interactive leaf, not the entire page. A client component wrapping server children forces all children client-side.
3. **Never import server-only code in client components.** Use `server-only` package to guard modules that should never be bundled for the browser.

## Data fetching

4. **Use `fetch()` with `next: { revalidate }` for ISR.** `revalidate: 0` for dynamic, `revalidate: 3600` for hourly. `cache: 'no-store'` for fully dynamic.
5. **Colocate data fetching in Server Components, not client useEffect.** Eliminates waterfalls and exposes no API keys to the client.
6. **Use Server Actions for mutations.** `'use server'` functions handle form submissions without API routes. Revalidate with `revalidatePath()` or `revalidateTag()`.

## Layout and routing

7. **Layouts persist across navigations.** Put shared UI (nav, sidebar) in `layout.tsx`. Use `template.tsx` only when you need fresh state per navigation.
8. **Use `loading.tsx` for streaming Suspense boundaries** and `error.tsx` for error boundaries per route segment.
9. **Use `generateMetadata` for dynamic SEO metadata.** Never hardcode title/description when they depend on data.

## Performance

10. **Use `next/image` for all images.** Automatic lazy loading, responsive sizing, WebP/AVIF conversion. Never bare `<img>` tags.
11. **Use `next/font` for fonts.** Self-hosted, zero layout shift, no external requests.
12. **Use `dynamic()` for heavy client components** that don't need SSR: `dynamic(() => import('./Chart'), { ssr: false })`.
13. **Middleware for auth/redirects at the edge.** Runs before rendering. Keep it lightweight — no DB calls.
