---
name: vue
description: "Applies when building or reviewing Vue 3 applications. Covers Composition API, ref vs reactive, composables, Pinia, and Vue Router."
---

# Vue 3

## Composition API

1. **Use `<script setup>` for all components.** Cleaner than `setup()` function. Auto-exposes variables to template.
2. **`ref` for primitives and single values. `reactive` for objects.** Access ref values with `.value` in script, auto-unwrapped in templates. Avoid `reactive` for values that get reassigned.
3. **`computed` for derived state. `watch`/`watchEffect` for side effects.** Never use `watch` where `computed` suffices — computed is cached.

## Composables

4. **Extract reusable logic into composables** (functions returning reactive state). Name with `use` prefix: `useAuth()`, `usePagination()`.
5. **`provide`/`inject` for deep prop drilling.** Use typed InjectionKeys. Provide from layout, inject in deeply nested components.

## Props and events

6. **`defineProps` with TypeScript types** for compile-time checking. Use `withDefaults` for default values.
7. **`defineEmits` with typed events.** Never emit undeclared events.
8. **v-model on components:** use `defineModel()` (3.4+) or `modelValue` prop + `update:modelValue` emit.

## State management

9. **Pinia for global state.** `defineStore` with `setup` syntax (composition-style). Never Vuex in new projects.
10. **Keep stores focused.** One store per domain (authStore, cartStore). Never a monolithic store.

## Router and SSR

11. **Lazy-load routes:** `component: () => import('./views/Dashboard.vue')`. Reduces initial bundle.
12. **Navigation guards for auth.** `beforeEach` on the router, not in every component.
13. **For SSR (Nuxt), use `useAsyncData`/`useFetch` instead of `onMounted` data fetching.**

## Performance

14. **`v-once` for static content that never changes.** `v-memo` for expensive list renders.
15. **Template refs with `useTemplateRef()` (3.5+)** for DOM access. Avoid direct DOM manipulation.
