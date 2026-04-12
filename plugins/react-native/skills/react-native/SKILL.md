---
name: react-native
description: "Applies when building or reviewing React Native mobile applications. Covers FlatList, navigation, platform-specific code, performance, and native modules."
---

# React Native

## Lists and rendering

1. **FlatList for any list >20 items.** Never ScrollView with `.map()` for long lists — it renders all items at once.
2. **`getItemLayout` for fixed-height items** to skip measurement and enable instant scroll-to-index.
3. **`keyExtractor` with stable unique IDs.** Never array index.
4. **Memoize renderItem with `useCallback`** and list items with `React.memo` to prevent re-renders.

## Navigation

5. **React Navigation for routing.** Stack, Tab, Drawer navigators. Use TypeScript param types for type-safe navigation.
6. **Lazy-load screens** with `React.lazy` or navigator's `lazy` prop to reduce startup time.

## Platform-specific code

7. **`Platform.OS` for small differences, `.ios.tsx`/`.android.tsx` files for large ones.**
8. **`Platform.select({ ios: ..., android: ... })` for inline platform values.**

## Performance

9. **Enable Hermes engine** (default in new projects). Faster startup, lower memory.
10. **Avoid inline object/array/function creation in JSX.** Creates new references every render, breaking `React.memo`.
11. **Use `InteractionManager.runAfterInteractions()` for expensive post-animation work.** Keeps animations at 60fps.
12. **MMKV over AsyncStorage** for fast synchronous key-value storage.

## Images and assets

13. **Use `react-native-fast-image` for network images.** Built-in Image has no disk caching on Android.
14. **Resize images before upload.** Don't send 12MP photos as-is.

## Debugging

15. **Flipper or React DevTools for debugging.** `console.log` in production destroys performance — strip with babel plugin.
