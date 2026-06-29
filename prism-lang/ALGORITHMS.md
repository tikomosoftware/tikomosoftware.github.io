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
