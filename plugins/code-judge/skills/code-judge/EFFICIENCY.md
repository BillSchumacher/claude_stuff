# Efficiency Reference

## Data structure selection

| Access pattern | Optimal structure | Avoid |
|---|---|---|
| Key-value lookup | Hash map (dict, Map, HashMap) O(1) | Linear scan O(n) |
| Sorted iteration | Balanced BST, sorted array | Repeated sort O(n log n) per query |
| Top-k elements | Min/max heap O(n log k) | Full sort then slice O(n log n) |
| Membership test | Hash set O(1) | List/array contains O(n) |
| FIFO queue | Deque O(1) both ends | Array shift/unshift O(n) |
| Range queries | Segment tree, BIT, sorted + bisect | Linear scan per query O(n) |
| Prefix sums | Precomputed prefix array O(1) query | Sum of slice per query O(n) |
| Graph (sparse) | Adjacency list O(V+E) | Adjacency matrix O(V²) |
| String building | StringBuilder/Buffer/join O(n) | String += in loop O(n²) |
| Deduplication | Hash set O(n) | Nested loop O(n²) |
| Priority scheduling | Binary heap O(log n) insert/extract | Sorted list O(n) insert |
| Interval overlap | Interval tree O(log n + k) | Pairwise check O(n²) |

## Common O(n²) anti-patterns

1. **String concatenation in loop** — `s += chunk` copies the entire string each iteration. Use language-specific builder (StringBuilder, strings.Builder, join, Buffer).
2. **Nested contains/indexOf** — `for x in a: if x in b` is O(n×m). Convert `b` to a set for O(n+m).
3. **Repeated index/find** — `list.index(x)` is O(n) per call; n calls = O(n²). Build an index dict once.
4. **Array splice/unshift in loop** — O(n) shift per op × n ops = O(n²). Use deque or reverse + push.
5. **Sort inside loop** — O(n log n) × n iterations = O(n² log n). Sort once outside the loop.
6. **Cartesian product by accident** — two nested loops when a hash or two-pointer approach gives O(n).
7. **Repeated regex compilation** — compile once, reuse the pattern object.
8. **N+1 queries** — fetching related records one-by-one in a loop; batch or JOIN instead.

## Memory anti-patterns

1. **Materializing large sequences** — `list(range(10**9))`. Use generators, iterators, or streams.
2. **Accumulating full results** — building a complete list to return. Yield/stream rows instead.
3. **Unnecessary deep copies** — copying entire structures when shallow copy or borrow suffices.
4. **Stale references in closures/caches** — large objects kept alive by forgotten references.
5. **Unbounded caches** — missing eviction policy (LRU, TTL). Memory grows without limit.

## Amortized analysis reminders

- **Dynamic array append**: O(1) amortized (capacity doubles). Pre-allocate with `reserve`/`with_capacity` when size is known.
- **Hash table insert**: O(1) amortized (resizes at load factor). Reserve when size is known.
- **Union-Find with path compression + union by rank**: O(α(n)) ≈ O(1) per operation.
- **Splay tree access**: O(log n) amortized; frequently accessed nodes migrate to root.

## Complexity class quick reference

| Class | Example operations |
|-------|-------------------|
| O(1) | Hash lookup, array index, stack push/pop |
| O(log n) | Binary search, balanced BST ops, heap insert/extract |
| O(n) | Linear scan, single-pass aggregation, counting sort |
| O(n log n) | Merge/heap/quick sort, sweep-line algorithms |
| O(n²) | Naive nested loops, bubble sort, all-pairs |
| O(2ⁿ) | Subset enumeration, naive recursive Fibonacci |

When reviewing, flag any operation that is a complexity class higher than necessary for the access pattern.
