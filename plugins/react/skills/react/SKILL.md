---
name: react
description: "Applies when building or reviewing React components and applications. Covers Server Components, hooks, custom hooks, state management, and performance optimization."
---

# React

## Server Components

1. **Default to Server Components (RSC).** Only add `'use client'` for interactivity. Server Components access DB/filesystem directly, reduce bundle, and stream to client.
2. **Push `'use client'` to the leaves.** Wrap only interactive parts, not entire pages.

## Hooks

3. **`useState` for local UI state.** Initialize with a function for expensive defaults: `useState(() => computeExpensive())`.
4. **`useEffect` for synchronization with external systems**, not for derived state. If you're setting state in useEffect based on props, use `useMemo` instead.
5. **`useMemo` for expensive computations, `useCallback` for stable function references** passed to memoized children. Don't memoize everything — measure first.
6. **Custom hooks for reusable stateful logic.** Name with `use` prefix. Extract when logic is shared or when a component gets complex.

## State management

7. **Context for low-frequency global state** (theme, locale, auth). Not for high-frequency updates — every consumer re-renders.
8. **Zustand, Jotai, or React Query for complex state.** Zustand for global stores, Jotai for atomic state, React Query for server state.
9. **Colocate state.** Keep state as close to where it's used as possible. Lift only when siblings need it.

## Performance

10. **`React.memo` only when you've measured a re-render problem.** Premature memoization adds complexity without benefit.
11. **Stable `key` prop on lists.** Never use array index as key when items can reorder/insert/delete.
12. **Suspense for data fetching boundaries.** Wrap async components in `<Suspense fallback={...}>`.
13. **Error boundaries (class components or react-error-boundary)** for graceful failure.

## Patterns

14. **Composition over inheritance.** Use children, render props, or custom hooks — never class inheritance.
15. **`forwardRef` when wrapping DOM elements** so parent can access the underlying node.
