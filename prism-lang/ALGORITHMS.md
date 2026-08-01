# Algorithms in Prism

> The ~300 drawings and animations here are **not** what Prism *is* — Prism is a contract-checked
> mini-language (type / effect / failure / exhaustiveness / capability). The gallery is the
> **proof**: a small language plus a few libraries reaches this far while every program still
> passes the checker. Treat it as evidence for the language, not as a graphics DSL.

How do you write classic algorithms in a language with **no loops, no mutable arrays, and
no `if`**? You **branch by matching** and **iterate by recursing**. This page walks through
the runnable samples in [`algorithms/`](algorithms/).

```sh
prism run algorithms/sorting.prism
prism check algorithms/tree.prism
```

If the algorithm names are unfamiliar, start with the Japanese reading guide:
[`ALGORITHM_GUIDE_JA.md`](ALGORITHM_GUIDE_JA.md).

## Quick map

- **Basics:** recursion, lists, sorting, trees, search
- **Graphs:** DFS/BFS, Dijkstra, Bellman-Ford, Kruskal MST, topological sort, graph coloring
- **Data structures:** binary search tree, Union-Find, Trie, Segment Tree, Skew Heap
- **Dynamic/recursive recurrences:** Fibonacci, coin change, knapsack, edit distance, Catalan
- **Sequence processing:** pattern matching, prefix sums, sliding window, quickselect, RLE
- **Number/numeric:** gcd, primes, sieve, extended Euclid, fast power, Newton method
- **Geometry:** orientation, segment crossing, polygon area, convex hull pieces

---

## The two moves

Everything below is built from just two ideas.

**1. Branch by `match` (or `if`).** You make a decision by matching on something:

- a number's shape — `n match 0 => … ; _ => …`
- a list's shape — `xs match [] => … ; [h, ..t] => …`
- an `or` type's variants — `t match Leaf => … ; Node{…} => …`
- a **Bool** — `(a < b) match true => … ; false => …`, or the shorthand
  **`if a < b then … else …`** (an expression that desugars to that Bool match)

**2. Iterate by recursion.** No `for`/`while`; a function calls itself on a smaller part
(the tail of a list, `n - 1`, a subtree). Often you thread a running result as an
**accumulator** parameter.

That's the whole vocabulary. The checker still holds you to the contract — and because every
`match` must be **exhaustive**, you cannot forget the base case: leave out `[]` or `false` and
`prism check` tells you, with the line number.

---

## 1. Recursion — [`algorithms/recursion.prism`](algorithms/recursion.prism)

Branch on a number's shape; recurse toward the base case.

```prism
factorial(n: Num) : Num  <-
  n match
    0  =>  1
    _  =>  n * factorial(n - 1)
```

`gcd` shows branching on **comparisons** (Bool match). v0 has no modulo operator, so this is
the *subtractive* Euclid:

```prism
gcd(a: Num, b: Num) : Num  <-
  (a == b) match
    true   =>  a
    false  =>
      (a < b) match
        true   =>  gcd(a, b - a)
        false  =>  gcd(a - b, b)
```

```
5!          = 120
fibonacci 10 = 55
2 ^ 10      = 1024
gcd(48, 36) = 12
```

## 2. Lists — [`algorithms/lists.prism`](algorithms/lists.prism)

The list is the workhorse: match `[]` vs `[h, ..t]`, rebuild with `[h, ..rest]`.

```prism
reverse(xs: List[Num]) : List[Num]  <-
  xs match
    []        =>  []
    [h, ..t]  =>  append(reverse(t), [h])
```

`maximum` threads the running best as an **accumulator** (the recursion idiom that replaces a
loop variable):

```prism
maxOf(best: Num, xs: List[Num]) : Num  <-
  xs match
    []        =>  best
    [h, ..t]  =>
      (best < h) match
        true   =>  maxOf(h, t)
        false  =>  maxOf(best, t)
```

`length`, `sum`, `append`, `member` (returns `Bool`) round it out.

## 3. Sorting — [`algorithms/sorting.prism`](algorithms/sorting.prism)

Comparisons drive the branches; lists are rebuilt immutably (no in-place arrays).

**Insertion sort** — insert each element into an already-sorted tail:

```prism
insert(x: Num, xs: List[Num]) : List[Num]  <-
  xs match
    []        =>  [x]
    [h, ..t]  =>
      (x < h) match
        true   =>  [x, h, ..t]
        false  =>  [h, ..insert(x, t)]
```

**Quicksort** — partition the tail around the head pivot, then recurse and concatenate:

```prism
quickSort(xs: List[Num]) : List[Num]  <-
  xs match
    []        =>  []
    [h, ..t]  =>  append(quickSort(below(h, t)), [h, ..quickSort(atLeast(h, t))])
```

```
insertion sort = [1, 1, 2, 3, 4, 5, 6, 9]
quicksort      = [1, 1, 2, 3, 4, 5, 6, 9]
```

## 4. Trees — [`algorithms/tree.prism`](algorithms/tree.prism)

Define the structure as an `or` type; every operation matches its variants exhaustively.

```prism
Tree : Leaf  or  Node{ value: Num, left: Tree, right: Tree }

insert(x: Num, t: Tree) : Tree  <-
  t match
    Leaf  =>  Node{ value: x, left: Leaf, right: Leaf }
    Node{value, left, right}  =>
      (x < value) match
        true   =>  Node{ value: value, left: insert(x, left), right: right }
        false  =>  Node{ value: value, left: left, right: insert(x, right) }
```

An in-order traversal of a binary **search** tree yields the values sorted:

```
in-order (sorted) = [1, 2, 3, 4, 5, 7, 8, 9]
contains 7 = true
contains 6 = false
```

## 5. Search — [`algorithms/search.prism`](algorithms/search.prism)

Search is a good stress test because the same question changes shape with the data:

- an unsorted list scans head/tail until it finds the value;
- a sorted list can stop early once the head is already too large;
- a binary search tree chooses exactly one branch at each node;
- a multiway tree can be searched depth-first or breadth-first by changing how the forest is
  threaded through recursion.

```prism
orderedMember(x: Num, xs: List[Num]) : Bool  <-
  xs match
    []        =>  false
    [h, ..t]  =>
      (x == h) match
        true   =>  true
        false  =>
          (x < h) match
            true   =>  false
            false  =>  orderedMember(x, t)
```

For a multiway tree, DFS follows the children before the siblings:

```prism
dfsForestContains(x: Num, forest: List[NTree]) : Bool  <-
  forest match
    []        =>  false
    [h, ..t]  =>
      dfsContains(x, h) match
        true   =>  true
        false  =>  dfsForestContains(x, t)
```

BFS uses the list as a queue: remove the head, append that node's children to the tail.
The same file also shows a fallible path search:

```prism
dfsPath(x: Num, t: NTree) : List[Num]  ?NotFound  <-
  t match
    Branch{value, children}  =>
      (x == value) match
        true   =>  [value]
        false  =>  [value, ..try dfsPathInForest(x, children)]
```

That `?NotFound` is the Prism twist: "search may fail" is not hidden in a sentinel value unless
you choose one. It is part of the contract, and callers must either propagate it with `try` or
handle it with `match`.

```
linear search 7      = true
ordered search 6     = false
binary tree search 7 = true
multiway BFS 19      = true
DFS path to 14       = [10, 17, 14]
DFS path to 99       = not found
```

## 6. Number theory — [`algorithms/number_theory.prism`](algorithms/number_theory.prism)

Number theory shows what happens when the textbook normally reaches for `%` or a loop. In Prism
you either use a pure helper such as `modN(a, b) <- a - b * floor(a / b)`, or write the recurrence
directly. Trial division for primes is a recursive walk over candidate divisors:

```prism
isPrimeFrom(n: Num, d: Num) : Bool  <-
  (d * d > n) match
    true   =>  true
    false  =>
      divides(d, n) match
        true   =>  false
        false  =>  isPrimeFrom(n, d + 1)
```

The sample includes `gcd`, `lcm`, `isPrime`, `primesUpTo`, and Euler's totient:

```
gcd(84, 30)     = 6
primes <= 30    = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
totient(9)      = 6
```

## 7. Graphs — [`algorithms/graph.prism`](algorithms/graph.prism)

A graph is represented as a list of `Link{from, to}` records. DFS and BFS are the same idea with
one small change: DFS pushes fresh neighbours onto the front of the frontier; BFS appends them to
the back. Shortest distance is fallible:

```prism
shortestDistance(goal, frontier, edges, seen, depth) : Num  ?NoPath  <-
  frontier match
    []  =>  fail NoPath
    _   =>
      member(goal, frontier) match
        true   =>  depth
        false  =>  try shortestDistance(goal, expand(frontier, edges, seen),
                                        edges, append(frontier, seen), depth + 1)
```

```
DFS 1 -> 6      = true
BFS 1 -> 6      = true
distance 1 -> 6 = 3
distance 1 -> 9 = no path
```

## 8. Dynamic recurrences — [`algorithms/dynamic.prism`](algorithms/dynamic.prism)

This file keeps the recurrences visible: Fibonacci, stair-counting, coin change, 0/1 knapsack,
and edit distance. There is no mutable table in v0, so these are the mathematical definitions
without memoization.

```prism
coinWays(amount: Num, coins: List[Num]) : Num  <-
  (amount == 0) match
    true   =>  1
    false  =>
      coins match
        []        =>  0
        [c, ..cs]  =>  coinWays(amount - c, coins) + coinWays(amount, cs)
```

```
fib(10)             = 55
coin ways 5 [1,2,5] = 4
knapsack cap 8      = 12
edit distance       = 2
```

## 9. Sequence patterns — [`algorithms/patterns.prism`](algorithms/patterns.prism)

Prism v0 has `Text`, but not character indexing, so string algorithms are shown over `List[Num]`
as a token stream. The sample includes prefix matching, substring containment, overlapping counts,
common-prefix length, and LCS length.

```prism
startsWith(pat: List[Num], xs: List[Num]) : Bool  <-
  pat match
    []        =>  true
    [p, ..pt]  =>
      xs match
        []        =>  false
        [x, ..xt]  =>  if p == x then startsWith(pt, xt) else false
```

```
contains [2,3]      = true
count [1,2]         = 3
LCS length          = 3
```

## 10. Sorted sets — [`algorithms/sets.prism`](algorithms/sets.prism)

Sorted-list algorithms are especially readable in Prism because every branch mirrors the three
cases: left head wins, right head wins, or both heads are equal. The sample includes merge, union,
intersection, difference, and deduplication.

```
merge        = [1, 2, 2, 3, 4, 4, 7, 8]
union        = [1, 2, 3, 4, 7, 8]
intersection = [2, 4]
a - b        = [1, 7]
```

## 11. Backtracking — [`algorithms/backtracking.prism`](algorithms/backtracking.prism)

Backtracking is a natural fit for immutable lists: pick one choice, recurse on the remaining
choices, then concatenate the rows. The file includes permutations, combinations, and a 4-queens
counter.

```prism
permutations(xs: List[Num]) : List[List[Num]]  <-
  xs match
    []  =>  [[]]
    _   =>  permuteChoices(xs, xs)
```

The 4-queens solver keeps already placed queens in a list and rejects a column or diagonal clash:

```
permutations 3 count = 6
combinations 4C2     = [[1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4]]
4-queens count       = 2
```

## 12. Greedy algorithms — [`algorithms/greedy.prism`](algorithms/greedy.prism)

Greedy algorithms are only as good as the ordering you feed them. In this sample, activities are
already sorted by finish time, and coins are already sorted from large to small.

```prism
selectActivities(lastFinish: Num, acts: List[Activity]) : List[Num]  <-
  acts match
    []        =>  []
    [a, ..t]  =>
      a match
        Act{id, start, finish}  =>
          if start >= lastFinish
          then [id, ..selectActivities(finish, t)]
          else selectActivities(lastFinish, t)
```

```
activity selection = [1, 4, 5]
greedy coins 87    = [25, 25, 25, 10, 1, 1]
```

## 13. Weighted shortest paths — [`algorithms/shortest_path.prism`](algorithms/shortest_path.prism)

Dijkstra's algorithm normally wants a heap. Prism v0 has no heap, so the priority queue is a
sorted immutable list. That makes the algorithm slower but very explicit: `insertState` keeps the
frontier ordered, and `dijkstra` pops the cheapest unseen state.

```
dijkstra 1 -> 6 = 7
dijkstra 1 -> 5 = 8
dijkstra 6 -> 1 = no path
```

The `no path` case is a handled `?NoPath`, not a magic distance.

## 14. Topological sort — [`algorithms/topo_sort.prism`](algorithms/topo_sort.prism)

Kahn's algorithm becomes a repeated search for a node with no incoming edges. If no such node
exists while nodes remain, the function fails with `?Cycle`.

```prism
topo(nodes: List[Num], edges: List[Edge]) : List[Num]  ?Cycle  <-
  nodes match
    []  =>  []
    _   =>
      n <- try pickZero(nodes, edges)
      [n, ..try topo(removeNode(n, nodes), withoutOutgoing(n, edges))]
```

```
topological order = [1, 2, 3, 4, 5]
cycle detection   = cycle
```

## 15. Computational geometry — [`algorithms/geometry.prism`](algorithms/geometry.prism)

Geometry is a small but useful contrast: instead of list structure, most of the meaning is in
record fields. The sample has orientation, strict segment crossing, and polygon area by the
shoelace formula.

```
turn a-b-c        = left
diagonals cross   = true
parallel cross    = false
rectangle area    = 12
```

## 16. Divide and conquer — [`algorithms/divide_conquer.prism`](algorithms/divide_conquer.prism)

This file adds merge sort and binary search. Merge sort is the structural version: split a list
into alternating halves, sort each half, then merge. Binary search uses v0's `len`/`at` builtins
for indexed reads over an immutable list.

```
merge sort     = [1, 2, 3, 4, 5, 6, 7, 8, 9]
binary search 7 = true
binary search 0 = false
```

## 17. Union-Find — [`algorithms/union_find.prism`](algorithms/union_find.prism)

Union-Find is usually mutable. Here the parent table is a list of `Par{node, parent}` records, and
`union` returns a rebuilt parent table. Path compression is omitted so the value flow stays easy to
read.

```
connected 1 4 = true
connected 1 5 = false
root 1        = 4
```

## 18. Minimum spanning tree — [`algorithms/mst.prism`](algorithms/mst.prism)

Kruskal's algorithm combines sorted weighted edges with the immutable Union-Find idea. The sample
keeps the edge list pre-sorted so the focus stays on "take if it connects two components".

```
mst edge count = 3
mst weight     = 7
```

## 19. Bellman-Ford — [`algorithms/bellman_ford.prism`](algorithms/bellman_ford.prism)

Bellman-Ford is a repeated relaxation over an edge list. Distances are records, and relaxing an
edge rebuilds just the changed distance record.

```
bellman 1 -> 2 = 2
bellman 1 -> 4 = 4
bellman 1 -> 5 = -2
bellman 1 -> 9 = unreachable
```

## 20. Matrices — [`algorithms/matrix.prism`](algorithms/matrix.prism)

A fixed 2x2 matrix is a record. Addition, multiplication, determinant, and matrix powers become
ordinary pure record transformations. The Fibonacci matrix makes the result recognizable:

```
fib matrix ^5 = M2{a: 8, b: 5, c: 5, d: 3}
det fib       = -1
```

## 21. Run-length encoding — [`algorithms/rle.prism`](algorithms/rle.prism)

Compression is a good example of "thread the current state through recursion": keep the current
value and count until a different value appears, then emit a `Run{value, count}` record.

```
rle encoded = [Run{value: 1, count: 3}, Run{value: 2, count: 2}, Run{value: 3, count: 1}, Run{value: 1, count: 2}]
rle decoded = [1, 1, 1, 2, 2, 3, 1, 1]
```

## 22. Automata — [`algorithms/automata.prism`](algorithms/automata.prism)

The DFA sample accepts binary numbers divisible by 3. The state transition is a plain function
`step(state, bit)`, and the input is folded by recursion.

```
dfa accepts 110  = true
dfa accepts 1011 = false
dfa final 1001   = 0
```

## 23. Parser checks — [`algorithms/parsing.prism`](algorithms/parsing.prism)

The parser sample checks balanced parentheses over token lists (`1` for open, `0` for close).
Underflow is represented as `?Underflow`; callers either handle it or propagate it.

```
balanced good = true
balanced bad  = false
max depth     = 2
```

## 24. More tree algorithms — [`algorithms/tree_algorithms.prism`](algorithms/tree_algorithms.prism)

The binary tree gets a fuller toolbox: size, height, balance check, diameter, mirror, and inorder
traversal. The nice part is that every operation has the same two cases: `Leaf` or `Node`.

```
tree size      = 8
tree height    = 4
tree balanced  = true
tree diameter  = 6
mirror inorder = [9, 8, 7, 5, 4, 3, 2, 1]
```

## 25. Skew heap — [`algorithms/heap.prism`](algorithms/heap.prism)

A skew heap avoids array indexing: the core operation is heap merge. Insert is "merge with a
singleton", and sorting is repeated removal of the root.

```
heap min    = 1
heap sorted = [1, 2, 3, 5, 6, 9]
empty min   = empty
```

## 26. Combinatorics — [`algorithms/combinatorics.prism`](algorithms/combinatorics.prism)

Combinatorial identities are compact in Prism because the recurrence can be written directly:
factorial, binomial coefficients, Pascal rows, and Catalan numbers.

```
factorial 6 = 720
choose 6 2  = 15
pascal row5 = [1, 5, 10, 10, 5, 1]
catalan 5   = 42
```

## 27. Numeric algorithms — [`algorithms/numeric.prism`](algorithms/numeric.prism)

This file shows numeric recurrences rather than structural list recursion: fast exponentiation,
Horner polynomial evaluation, and Newton iteration for square roots.

```
powFast 2^10 = 1024
horner       = 234
sqrt 25      = 5
```

## 28. Intervals — [`algorithms/intervals.prism`](algorithms/intervals.prism)

Sorted interval merging is a fold with one carried interval. The sample also computes total
covered length and point containment.

```
merged intervals = [I{lo: 1, hi: 6}, I{lo: 8, hi: 12}]
covered length   = 9
contains 7       = false
```

## 29. Prefix sums — [`algorithms/prefix_sums.prism`](algorithms/prefix_sums.prism)

Prefix sums show the "precompute then answer indexed queries" shape. The same file includes
Kadane's maximum subarray recurrence.

```
prefix sums   = [0, 3, 4, 8, 9, 14, 23]
range 1..3    = 6
max subarray  = 6
```

## 30. Selection — [`algorithms/selection.prism`](algorithms/selection.prism)

Quickselect partitions around a pivot, then recurses only into the partition containing the
requested index. Out-of-range empty input is handled as `?Empty`.

```
select k=0 = 1
select k=3 = 6
select empty = empty
```

## 31. Trie — [`algorithms/trie.prism`](algorithms/trie.prism)

A trie is a recursive record: `T{terminal, children}` with each child linking a token to another
trie. Missing child lookup is a `?Missing` failure that insertion handles by using an empty trie.

```
trie has [1,2] = true
trie has [1]   = false
trie has [2]   = true
```

## 32. Segment tree — [`algorithms/segment_tree.prism`](algorithms/segment_tree.prism)

The segment tree is immutable: build, query, and update all return values. Updating one position
rebuilds the path from the leaf to the root.

```
segment sum 1..3 = 6
segment sum all  = 14
after update     = 12
```

## 33. Convex hull pieces — [`algorithms/convex_hull.prism`](algorithms/convex_hull.prism)

The monotone-chain stack is represented as a list with the newest point at the front. The sample
prints lower and upper hull pieces for pre-sorted points.

```
lower hull = [P{x: 0, y: 0}, P{x: 4, y: 0}]
upper hull = [P{x: 4, y: 0}, P{x: 3, y: 2}, P{x: 1, y: 1}, P{x: 0, y: 0}]
```

## 34. Graph coloring — [`algorithms/graph_coloring.prism`](algorithms/graph_coloring.prism)

Graph coloring is another backtracking example. Instead of returning the first solution, this
sample counts all proper colorings for a small graph.

```
3-colorings = 12
2-colorings = 0
```

## 35. Polynomials — [`algorithms/polynomial.prism`](algorithms/polynomial.prism)

Polynomials use coefficient lists in ascending power order. The sample implements addition,
convolution multiplication, derivatives, and evaluation.

```
poly product = [4, 13, 22, 15]
poly deriv   = [2, 6]
poly eval    = 321
```

## 36. Sieve — [`algorithms/sieve.prism`](algorithms/sieve.prism)

The Sieve of Eratosthenes is written as repeated filtering: take the head prime and remove its
multiples from the remaining candidate list.

```
sieve <= 30 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
```

## 37. Counting sort — [`algorithms/counting_sort.prism`](algorithms/counting_sort.prism)

Counting sort scans the input for each value in a small domain, then expands each count back into
sorted output.

```
counting sort = [0, 1, 2, 2, 2, 3, 4, 4]
count of 2    = 3
```

## 38. Majority vote — [`algorithms/majority_vote.prism`](algorithms/majority_vote.prism)

Boyer-Moore majority vote keeps a candidate and a counter. The second pass verifies whether the
candidate is truly a majority.

```
majority a = 2
majority b = none
```

## 39. Sliding window — [`algorithms/sliding_window.prism`](algorithms/sliding_window.prism)

Sliding-window sums are expressed by taking the sum of the next `k` elements, then recursing on the
tail. It is simple, explicit, and immutable.

```
window sums = [8, 6, 10, 15]
window max  = 15
```

## 40. Extended Euclid — [`algorithms/extended_euclid.prism`](algorithms/extended_euclid.prism)

Extended Euclid returns a record `EG{g, x, y}` satisfying `a*x + b*y = g`. Modular inverse is then
just the handled case where `g == 1`.

```
egcd(30,12) = EG{g: 6, x: 1, y: -2}
inverse 3 mod 11 = 4
inverse 6 mod 10 = none
```

## 41. Cycle detection — [`algorithms/cycle_detection.prism`](algorithms/cycle_detection.prism)

Floyd cycle detection uses a tortoise and hare over a functional graph. The sample function is
`f(x) = (2*x + 1) mod 9`.

```
cycle start 0 = 0
cycle len 0   = 6
cycle len 2   = 2
```

---

## Little apps (visualizers)

Because a picture is just a pure value, the playground can host small interactive visualizers:
- [`examples/grapher.prism`](examples/grapher.prism) — a **function grapher**: edit `f(x)`, drag
  the amp/freq sliders, and it graphs live. Built on [`lib/plot.prism`](lib/plot.prism) (axes,
  grid, `plot(f, a, b)`).
- [`examples/chart-bars.prism`](examples/chart-bars.prism) / [`examples/chart-pie.prism`](examples/chart-pie.prism)
  — **data charts** (bar + line, and pie) from a list of numbers, via [`lib/chart.prism`](lib/chart.prism)
  (`barChart` / `lineChart` / `pieChart`).
- [`physics/spirograph-studio.prism`](physics/spirograph-studio.prism) — a **Spirograph studio**:
  three sliders (ring/roll/pen) you drag to design a hypotrochoid.

- [`physics/harmonograph-studio.prism`](physics/harmonograph-studio.prism) — a **harmonograph
  studio**: two frequencies + a phase on sliders, a decaying Lissajous figure.
- [`physics/clock-anim.prism`](physics/clock-anim.prism) — a working **analog clock** (hands
  driven by `frame(t)`), showing a time-driven app.
- [`fractals/rule110.prism`](fractals/rule110.prism) / [`fractals/rule30.prism`](fractals/rule30.prism)
  — **elementary cellular automata** via [`lib/ca.prism`](lib/ca.prism): from one live cell,
  60 generations are computed and stacked (Rule 110 is Turing-complete; Rule 30 is chaotic).
  Verified exact against a reference (986 / 1734 cells) — real iterative computation in Prism.

- [`fractals/maze.prism`](fractals/maze.prism) — a **maze** generated by recursive division
  (split a region with a gapped wall, recurse the halves; gaps from a sin-hash).
- [`physics/contour-map.prism`](physics/contour-map.prism) — a **contour/topographic map**: a
  height field coloured by elevation band.
- [`physics/chord-wheel-anim.prism`](physics/chord-wheel-anim.prism) — **music theory**: a major
  triad as a triangle on the 12-note circle, rolling through every key.
- [`physics/bouncing-logo-anim.prism`](physics/bouncing-logo-anim.prism) — the classic bouncing
  logo (triangle-wave motion, colour changes).
- [`fractals/sort-diagram.prism`](fractals/sort-diagram.prism) — a **sorting visualization**:
  each row is the array after one more bubble-sort pass, coloured by value (the order emerges).
- [`physics/fourier-anim.prism`](physics/fourier-anim.prism) — a **Fourier** machine: odd
  harmonics as chained rotating circles whose tip traces a square wave.
- [`physics/lissajous-table.prism`](physics/lissajous-table.prism) — a 4×4 **Lissajous table**
  (frequency ratios), the classic oscilloscope chart.
- [`physics/newton-converge-anim.prism`](physics/newton-converge-anim.prism) — **Newton's method**
  visualized: each step drops to the curve and slides down the tangent to the next x (converging).
- [`fractals/tree-wind-anim.prism`](fractals/tree-wind-anim.prism) — a recursive **tree swaying**
  in the wind (branch angles nudged by `sin(t)`, more toward the tips).
- [`physics/double-slit.prism`](physics/double-slit.prism) — the **double-slit** interference
  pattern (cos² fringes under a fading envelope, brightness = opacity).

Game effects (the trajectories/particles old arcade games used — trails are drawn by sampling
the path at earlier times `t - δ` and fading them):
- [`physics/galaxian-swoop-anim.prism`](physics/galaxian-swoop-anim.prism) — a Galaxian-style
  attack: enemies peel off a formation and dive in curved arcs with a fading streak.
- [`physics/slash-trail-anim.prism`](physics/slash-trail-anim.prism) — a sword slash with a
  glowing motion-blur crescent.
- [`physics/sparkle-burst-anim.prism`](physics/sparkle-burst-anim.prism) — a star/sparkle hit
  burst (fly out, arc under gravity, twinkle, fade).
- [`physics/fireball-anim.prism`](physics/fireball-anim.prism) — a fireball bouncing with a
  shrinking, cooling flame trail.

And a whole pack more in the same family (all pure `frame(t)`, in `physics/`): **magic-circle**,
**explosion-ring**, **coin-spin**, **powerup-aura**, **lightning-spell**, **shield-bubble**, **portal**,
**heal**, **muzzle-flash**, **laser-beam**, **levelup-rays**, **freeze**, **vortex-pull**, **star-trail**,
**hit-flash**, **energy-orb**, **spark-shower**, **dash-afterimage**, **electric-aura**, **rune-ring**,
**starfall**, **shockwave-grid**, **aura-flame**, **boss-charge**. The recurring tricks: trails = sample
the path at earlier times `t − δ` and fade them; sparks = radial launch + gravity + fade; "randomness"
= a `sin`-hash; flashes/blinks = `frac(t·k)`; glow = a translucent (`a`) filled shape under a bright core.

More game UI/feel, same family: **combo-anim** (a hit counter using the 7-segment number renderer
in [`lib/digits.prism`](lib/digits.prism)), **screen-shake** (the whole scene jitters on impact),
**hp-bar** (chip-damage health bar), **treasure-chest** (lid rotated open about its hinge, light + gem).
And three computational set-pieces: [`physics/gravity-slingshot.prism`](physics/gravity-slingshot.prism)
(five probes Euler-integrated past a planet), [`fractals/voronoi.prism`](fractals/voronoi.prism)
(grid coloured by nearest of nine seeds), [`fractals/terrain3d.prism`](fractals/terrain3d.prism)
(a sine-noise height field as a wire mesh in oblique projection),
[`fractals/life.prism`](fractals/life.prism) (Conway's Game of Life — six generations of an 18×18
toroidal world, verified against a Python reference) and [`fractals/pathfind.prism`](fractals/pathfind.prism)
(a maze solved by flood-fill BFS: the distance field is relaxed Bellman-Ford style, then the shortest
path is descended from the goal). Both treat a stateful grid as a *fold over immutable grids* — no
arrays, no mutation — leaning on the fact that bound values are memoised (so the generation chain
isn't recomputed). `nth` lives in [`lib/list.prism`](lib/list.prism).

These are *client-side* visualizers (Prism is pure — no real I/O, audio, network, or storage);
the playground's `slider(...)` gives the interactivity, `frame(t)` the time.

## See it — ASCII and canvas

Algorithms are more fun when the result is *visible*. Three samples turn computation into
something you can look at:

- [`algorithms/sierpinski.prism`](algorithms/sierpinski.prism) — a Sierpinski triangle in
  **ASCII**, built by recursively composing rows of text (`prism run` it).
- [`algorithms/bounce.prism`](algorithms/bounce.prism) — a **1-D bouncing ball** by Euler
  integration; each line is the height at one instant, drawn with spaces.
- [`algorithms/draw.prism`](algorithms/draw.prism) — a Sierpinski triangle as a **picture**:
  a pure value `picture : [Line{…}, …]` that the **browser playground draws on a canvas**
  (`prism serve`, open the page, pick a ★ example, press **Draw**).
- [`algorithms/koch.prism`](algorithms/koch.prism) — a **Koch snowflake**, and
  [`algorithms/pythagoras.prism`](algorithms/pythagoras.prism) — a **Pythagoras tree**:
  curved fractals whose branches are *rotations*, so they use the math builtins
  `sin` / `cos` / `pi` (`sqrt` / `abs` are available too). Also drawn on the canvas.
- [`examples/projectile.prism`](examples/projectile.prism) — **2-D physics**: a projectile
  under gravity, drawn as a trajectory of `Dot`s. It `include`s a reusable vector/physics
  library, [`lib/physics2d.prism`](lib/physics2d.prism) (`Vec`, `vadd`, `vscale`, `vlen`,
  a `Body`, and an Euler `step`).
### Compose it — the Picture algebra ([`lib/picture.prism`](lib/picture.prism))

All of the above hand-build a flat `picture : List[Shape]` in absolute coordinates (call this
**Layer A** — what the canvas draws). On top of it sits a small, *composable* **Layer B**: a
`Picture` carries its shapes **and** a bounding box, so pictures can be laid out relative to
each other. It's a pure Prism library — no language change.

```prism
include "lib/picture.prism"
over(a, b)        -- draw b on top of a (same coordinates)
beside(a, b)      -- put b to the right of a   (uses a's bounding box)
above(a, b)       -- put b below a
scale(k, p)       -- scale about the origin   |  rotate(deg, p) -- turn about the origin
quartet(a,b,c,d)  -- 2x2 layout               |  cycle(p)       -- p turned 0/90/180/270
render(p)         -- lower a Picture back to the List[Shape] the canvas draws
```

Composition is the **flow** voice: `over(a, b)` is just *data*, not a sequence of draw commands.
See [`examples/picture-basics.prism`](examples/picture-basics.prism) and
[`examples/picture-transforms.prism`](examples/picture-transforms.prism) (run them);
[`fractals/htree-pic.prism`](fractals/htree-pic.prism) — the H-tree rebuilt as `over`-composed
sub-pictures instead of a threaded accumulator (compare `fractals/htree.prism`); and
[`fractals/square-limit.prism`](fractals/square-limit.prism) — an Escher-style **square limit**
(`cycle(cycle(tile))`), the SICP/Henderson functional-geometry demo. The library declares the
drawing vocabulary as one `or` type, `Shape : Line | Dot | Circle | Rect`, so a `match` may
return any shape and the checker unifies the arms — records stay open, so the optional `h` hue
still works.

### Animate it — the picture as a function of time

Define a **pure** function `frame(t) : Picture` and press **Animate**: the playground advances
`t` (seconds) and renders each frame. The scene is a *function of time* with no mutable state —
and since `frame` has no `!` in its signature, the checker **certifies the animation is pure**
(a `frame` that hides a `show!console` is rejected). See
[`physics/pendulum-anim.prism`](physics/pendulum-anim.prism) — a pendulum swung by `sin(t)`,
its rod `rotate`d about the pivot. Write `frame` periodic over `t ∈ [0, 2π]` for a smooth loop.

More animations (all pure `frame(t)`): [`double-pendulum-anim`](physics/double-pendulum-anim.prism)
(a driven double pendulum), [`orbits-anim`](physics/orbits-anim.prism) (planets + a moon on an
epicycle, gravity), [`bounce-anim`](physics/bounce-anim.prism) (balls bouncing, height `|sin|`),
[`flag-anim`](physics/flag-anim.prism) (a flag waving — a mesh of `Poly` rows under a travelling
wave), and [`fluid-anim`](physics/fluid-anim.prism) (a grid of dots with radial ripples). The
grid demos use `times(n, f)` / `concatAll` from `lib/picture.prism` to lay out the mesh.

More **fluid / wave** variations: [`interference-anim`](physics/interference-anim.prism)
(two-source fringes), [`ripple-rings-anim`](physics/ripple-rings-anim.prism) (raindrop rings
spreading, `Circle`s), [`ocean-anim`](physics/ocean-anim.prism) (a perspective wave sheet of
`Poly` rows), [`drum-anim`](physics/drum-anim.prism) (a 2-D *standing* wave — a vibrating drum
membrane, height shown as hue), and [`flow-anim`](physics/flow-anim.prism) (a churning,
swirling flow field). All are pure `frame(t)`, periodic and bounded.

And some pure eye-candy: [`cube3d-anim`](physics/cube3d-anim.prism) (a **3-D** wireframe cube —
corners rotated about two axes and projected with perspective), [`galaxy-anim`](physics/galaxy-anim.prism)
(a turning spiral galaxy), [`starfield-anim`](physics/starfield-anim.prism) (a warp starfield of
streaks), [`rose-morph-anim`](physics/rose-morph-anim.prism) (a rose curve whose petal count
drifts, one morphing `Poly`), and [`kaleidoscope-anim`](physics/kaleidoscope-anim.prism) (a motif
copied at eight spinning rotations).

**3-D and particle systems:** [`torus3d-anim`](physics/torus3d-anim.prism) and
[`sphere3d-anim`](physics/sphere3d-anim.prism) (point clouds rotated in 3-D, shaded by depth),
[`fountain-anim`](physics/fountain-anim.prism) (droplets on parabolic arcs), [`fireworks-anim`](physics/fireworks-anim.prism)
(bursting shells), and [`snow-anim`](physics/snow-anim.prism) (drifting flakes). The particle
systems loop their lifetimes with `frac` / `mod` (built on the `floor` math builtin).

Everyday nature effects: [`rain-anim`](physics/rain-anim.prism) (slanted streaks),
[`sakura-anim`](physics/sakura-anim.prism) (cherry-blossom petals that tumble — small `Poly`s
rotated inline so they keep their pink hue) and [`leaves-anim`](physics/leaves-anim.prism)
(autumn leaves in a wide zig-zag, warm hues), plus
[`fireflies-anim`](physics/fireflies-anim.prism) (wandering glow), [`shooting-stars-anim`](physics/shooting-stars-anim.prism)
(streaks over a star field), [`grass-anim`](physics/grass-anim.prism) (blades swaying in wind),
[`bubbles-anim`](physics/bubbles-anim.prism) (rising, growing) and [`embers-anim`](physics/embers-anim.prism)
(sparks cooling yellow→red as they rise).

With **translucency** (an optional `a` opacity field, and `fill` to fill Circle/Poly):
[`fog-anim`](physics/fog-anim.prism) (soft drifting banks), [`blizzard-anim`](physics/blizzard-anim.prism)
(wind-driven snow), [`lightning-anim`](physics/lightning-anim.prism) (a forked bolt that flashes
— opacity spikes then fades), [`confetti-anim`](physics/confetti-anim.prism) (filled tumbling
squares in every colour), [`balloons-anim`](physics/balloons-anim.prism) (rising, with strings),
[`dandelion-anim`](physics/dandelion-anim.prism) (soft floating tufts), [`twinkle-anim`](physics/twinkle-anim.prism)
(stars whose opacity pulses) and [`waves-shore-anim`](physics/waves-shore-anim.prism) (rolling
swell), plus glow effects [`glow-fireflies-anim`](physics/glow-fireflies-anim.prism) (halo +
bright core, pulsing), [`neon-anim`](physics/neon-anim.prism) (a spinning neon star, colours
flowing), [`caustics-anim`](physics/caustics-anim.prism) (dappled underwater light) and
[`smoke-anim`](physics/smoke-anim.prism) (puffs rising, growing and fading).

More: glow/fantasy (`aurora`, `sparkler`, `firefly-river`, `glow-fireworks`); everyday/seasonal
(`rain-puddle`, `river`, `campfire`, `lanterns`, `milkyway`); and **mechanism** demos —
`pendulum-wave` (periods stepping up drift into travelling waves), `gears` (a meshing train),
`dna` (a turning double helix), `newtons-cradle`, and `wave-superposition` (two waves and their
sum); and more **2-D/3-D physics** — `solar-system` (sun, planets, a moon), `wave3d` (a rippling
3-D sheet), `lissajous3d` (a spinning 3-D knot), `octahedron3d`/`tetrahedron3d`/`icosahedron3d`/`dodecahedron3d` (all five Platonic wireframes —
edges found by nearest-neighbour distance, e.g. exactly 30 for the icosa/dodecahedron),
`torus-knot`/`figure8-knot` (3-D knots), `spring3d`/`conical-spiral` (coils), `loxodrome` (a
sphere spiral), and `mobius` (a half-twisted band).

For number theory, [`fractals/sacks-spiral.prism`](fractals/sacks-spiral.prism) plots the
**Sacks prime spiral**: integer n at radius √n / angle 2π√n, drawn only when n is prime (tested
by trial division) — the primes fall along curving streaks.

Also: [`physics/lorenz3d.prism`](physics/lorenz3d.prism) integrates the chaotic Lorenz ODE and
projects the butterfly with a 3-D tilt; [`physics/epicycloid-morph-anim.prism`](physics/epicycloid-morph-anim.prism)
drifts an epicycloid's cusp count so petals grow and reabsorb; and
[`physics/rose-garden.prism`](physics/rose-garden.prism) tiles a 4×4 grid of rhodonea
`r=cos(kθ)` for k=1..16 (the whole rose family at a glance).

And more number theory: [`fractals/ulam-spiral.prism`](fractals/ulam-spiral.prism) walks the
integers on a square spiral (run-lengths 1,1,2,2,…) and marks primes (they cluster on
diagonals); [`fractals/collatz-steps.prism`](fractals/collatz-steps.prism) plots each n's
Collatz stopping time; and [`physics/times-table-anim.prism`](physics/times-table-anim.prism)
joins k to (k·m mod N) on a circle, sweeping the multiplier m so the envelope morphs through a
cardioid, nephroid and beyond; and [`fractals/barnsley-fern.prism`](fractals/barnsley-fern.prism)
grows **Barnsley's fern** by the chaos game — four affine maps picked by a deterministic
sin-hash (there's no RNG), ~2200 points. (The dropdown is Japanese-labelled.)

- [`fractals/`](fractals/) — **26** recursive fractals:
  - **trees & plants** — `fractal-tree`, `windy-tree`, `fern`, `plant`, `plant2`, `bush`, `tree3`;
  - **curves** — `dragon`, `levy`, `cesaro`, `terdragon`, `koch-square`, `koch-antiflake`,
    `koch-island`, `arrowhead` (Sierpinski as one stroke);
  - **squares & sets** — `carpet`, `vicsek`, `tsquare`, `cantor`, `pythagoras-lean`;
  - **space-fillers** — `hilbert`, `htree`, `gosper` (flowsnake), `peano`, `moore`, `pentaflake`;
  - **Picture algebra** — `htree-pic`, `square-limit` (Escher), `koch-lsys`/`plant-lsys`
    (data-driven L-systems), `poly-vortex` (tilted squares as `Poly`, faithfully rotated);
  - **escape-time (Mandelbrot family)** — `mandelbrot`, `multibrot` (z⁵) / `multibrot3` (z³),
    `burning-ship`, `julia`. Each iterates `z → z^d + c` per grid cell (a complex number is a
    `Pt{x, y}`) and colours by the escape count; inside points are left undrawn. See
    [`lib/escape.prism`](lib/escape.prism);
  - **Mandelbrot variants** — `tricorn` (Mandelbar, conjugate before squaring), `celtic`
    (|Re(z²)|), `buffalo` (|Re|,|Im| of z²), plus zoom-ins `mandelbrot-seahorse` and
    `mandelbrot-elephant` (same iteration, small window, more iterations);
  - **Julia sets** — `julia`, `julia-rabbit` (Douady rabbit, c=−0.123+0.745i), `julia-dendrite`
    (c=i); a **Newton fractal** — `newton` colours each point by which root of z³−1 Newton's
    method sends it to (the basin boundaries are fractal; every point converges, so it fills);
    and a **biomorph** (Pickover) — a Julia iteration that bails on either component, giving
    organic cell shapes.

  The L-system curves (`gosper`, `peano`, `terdragon`, `koch-island`, `arrowhead`) and the
  branching plants (`plant`, `bush`) run on a little **turtle**,
  [`lib/turtle.prism`](lib/turtle.prism): `fwd`/`turn` thread the turtle's state through `let`
  bindings, and `restore` implements the L-system bracket `[ ]` (branch, then come back).

  **Data-driven L-systems** — [`lib/lsystem.prism`](lib/lsystem.prism) takes this further: a
  fractal is just an **axiom and a rewrite rule** (a word is a `List` of symbol tags like
  `[F, L, F, R, R, F, L, F]`). `expand(rule, axiom, n)` rewrites *n* times and `draw` turtles
  the result into a `Picture`. See [`fractals/koch-lsys.prism`](fractals/koch-lsys.prism)
  (`F -> F L F R R F L F`, 256 segments = 4⁴) and
  [`fractals/plant-lsys.prism`](fractals/plant-lsys.prism) (a bracketed, branching plant) —
  no hand-written recursion, the generic engine does it.
- [`physics/`](physics/) — a **gallery of 90** (simulations, ~20 strange attractors, spirals,
  many roses & Maurer lattices, roulettes & classic curves) — a selection:
  - **simulations** — `orbit`, `bounce2d`, `pendulum`, `double-pendulum`, `three-body`,
    `binary-star`, `spring`, `damped`, `vanderpol`, `duffing`, `projectile-fan`;
  - **17 strange attractors** — `lorenz`, `lorenz-xy`, `dejong`, `dejong2`, `clifford`,
    `clifford2`, `henon`, `tinkerbell`, `rossler`, `gingerbread`, `gumowski-mira`, `gumowski2`,
    `svensson`, `fractal-dream`, `bedhead`, `ikeda`, `hopalong`;
  - **spirals** — `spiral`, `logspiral`, `fermat`, `involute`, `vortex`, `circles-spiral`,
    `kaleidoscope`;
  - **roses & lattices** — `rose`, `rose3`, `rose5`, `rose6`, `rose7`, `quadrifolium`,
    `maurer`, `maurer2`, `maurerb`, `mandala`, `ripples`, `star`;
  - **roulettes & classics** — `epicycloid`, `hypocycloid`, `hypocycloid5`, `epitrochoid`,
    `deltoid`, `nephroid`, `spirograph`, `spirograph2`, `harmonograph`, `lissajous`,
    `lissajous54`, `gear`, `heart`, `cardioid`, `lemniscate`, `limacon`, `trefoil`, `cycloid`,
    `phyllotaxis`, `flag`, `wave`;
  - **classic named curves** — `astroid`, `lituus`, `cochleoid`, `hyperbolic-spiral`,
    `witch-of-agnesi`, `tschirnhausen` (cubic), `semicubical-parabola`, `serpentine`, `bicorn`,
    `folium-descartes` — each a single parametric/rational equation sampled into one `Poly`.

  Sims integrate with Euler steps; curves use [`lib/draw2d.prism`](lib/draw2d.prism)'s
  `polyline`. **★ fractals/physics: …** → **Draw**. (**~120 pictures in all.**)

  > Note: a simulation of N steps recurses N deep (Prism has no loops, and the tree-walker
  > uses the host stack), so the interpreter lifts its recursion limit. Very long runs are
  > still bounded by the host's stack — keep step counts to a few hundred.

The drawing approach keeps the language pure: the program returns the *geometry* as an
ordinary value (a list of `Line` / `Dot` / `Circle` / `Rect`); rendering it is the tool's
job — exactly like `check` and `reveal` are tooling around a pure language. The canvas
**animates** the picture (revealing it a few shapes at a time) and **colours** it — by a
rainbow along the draw order, or by an explicit `h` hue field on a shape (0–360), e.g.
`Dot{x: 0, y: 0, h: 200}`. A number written as **`slider(default, min, max)`** becomes a live
drag control in the playground (it just returns the default on the CLI) — see the ★
`dejong-live` / `rose-live` / `lissajous-live` examples.

```prism
picture  <-  [ Line{x1: 0, y1: 0, x2: 100, y2: 50}, Dot{x: 100, y: 50} ]
```

## What does NOT fit v0 (honest limits)

These need primitives v0 deliberately omits — worth knowing before you reach for them:

- **Array-indexed algorithms** (binary search by index, in-place heapsort, dynamic-programming
  tables): lists are singly-linked with no `O(1)` indexing or mutation. You recurse instead.
- **Modulo-based math** (`gcd` via `mod`, hashing, sieve): there is no `%` operator — work
  subtractively, or it doesn't fit. (`sin`/`cos`/`sqrt`/`abs`/`pi` *are* available.)
- **Anything needing real I/O / a standard library** (read a file, time something, big maps):
  not in v0 — see [OVERVIEW.md](OVERVIEW.md) §1.

The takeaway: Prism expresses **structurally-recursive** algorithms cleanly and makes their
contracts (does it fail? does it touch the world? are all cases handled?) explicit. It is a
thinking tool, not a place to ship a production sort.
