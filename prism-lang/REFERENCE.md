# Prism language reference (v0)

This is the complete reference for the Prism v0 language as implemented by
`prism.py` (interpreter) and `check.py` (static checker). For the *why*, read
[README.md](README.md); to learn by doing, read [TUTORIAL.md](TUTORIAL.md).

Prism has **no build step**. A program is a text file (`.prism`) that you `run`
(interpret) and/or `check` (statically). The checker is optional and separate —
you can run code that has not been checked.

---

## 1. Lexical structure

- **Comments** start with `--` and run to end of line.
- **Numbers**: `42`, `3.14` (integer or decimal).
- **Text**: `"..."`, with `\` escapes and `{expr}` interpolation (see §10).
- **Booleans**: `true`, `false`.
- **Identifiers**: `[A-Za-z_][A-Za-z0-9_]*`.
  - **Lowercase-initial** → a variable, function, or method name (`divide`, `xs`).
  - **Uppercase-initial** → a constructor / variant / capability / type name (`Circle`, `DivByZero`, `Ord`).
- **Layout**: blocks are defined by **indentation** (like Python). A more-indented line
  opens a block; dedenting closes it. Inside `(` `)` `[` `]` `{` `}`, newlines and
  indentation are ignored, so an expression may wrap freely within brackets.

## 2. The four voices (overview)

Every computation answers four questions. Prism gives each its own connector and never
mixes them:

| Voice | Question | Marker |
|---|---|---|
| **fact** | what is it? (type / data) | `:`  `and`  `or` |
| **flow** | what is it derived from? | `<-`  `=>` |
| **effect** | what in the world does it change? | `!world` |
| **failure** | how can it fail? | `?Error`  `try`  `match` |
| (**time**) | in what order does it happen? | `~>` |

A function signature spells out all of them — a contract that cannot lie:

```prism
f(x: A) : B  !world  ?Error  <-  body
--      ^type  ^effect  ^failure   ^derivation
```

## 3. Definitions

A program is a list of definitions. **Definition order does not matter** — derivation is
by the `<-` arrow, not by line order (the interpreter uses lazy thunks). To run, a program
must define `main`.

`include "path"` at the top level merges another file's definitions into the **same global
space** (no namespaces — consistent with order-free global definitions). Paths are resolved
relative to the current working directory (**run from the project root**); cycles and
double-includes are ignored. (File-*relative* resolution would be friendlier when running a file
from another directory, but it's deferred: the browser runs programs from a string with no file
path, so there's no base to resolve against — the run-from-root convention keeps CLI and browser
identical.) This is how you keep a reusable library in its own file:

```prism
include "lib/physics2d.prism"
```

> **No namespaces — but collisions are now caught.** Because `include` merges into one flat
> global space, two top-level definitions with the **same name** would collide. Rather than
> silently letting one shadow the other (a real footgun — a demo's `maxN` constant once hid
> `lib/math`'s `maxN` function), **the checker rejects a duplicate top-level name**
> (see [`examples/collision.prism`](examples/collision.prism)). So keep names distinct (e.g.
> prefix domain-specific helpers) and don't redefine a name a library already provides. A real
> module/namespace system (qualified names) is still out of v0 scope — see [NOTES.md](NOTES.md)
> "horizon".

```prism
celsius    : Num  <-  30
fahrenheit : Num  <-  celsius * 9 / 5 + 32     -- may appear before `celsius`
```

Three shapes:

```prism
greet(name: Text) : () !console  <-  show!console "hi {name}"   -- function (with signature)
answer : Num  <-  42                                            -- value (with signature)
double(n)  <-  n * 2                                            -- no signature (inferred / gradual)
```

The signature (everything between the name and `<-`) is optional. Without it, the definition
is checked gradually (§11) and its contract can be inferred with `reveal` (§14).

### Bodies and blocks

A body is either an inline expression after `<-`, or an indented block on the next lines.
In a block, a line of the form `name <- expr` is a **local binding**; other lines are
statements; the block's value is its last expression.

```prism
area(r: Num) : Num  <-
  pi   <-  3
  pi * r * r
```

## 4. Fact: types (`:`)

A type annotation is introduced with `:`. Built-in types: `Num`, `Text`, `Bool`, `()` (Unit),
`List[T]`. Type application uses square brackets: `List[Num]`, `F[A, B]`.

Function types: `(A, B) -> C !e ?g`.

### Records — the `and` type

A product (all fields present) is written with `and`:

```prism
Account : { name: Text  and  balance: Num }
```

A record value uses constructor syntax; a field is read with `.`:

```prism
acc  <-  Account{ name: "Ada", balance: 100 }
acc.balance
```

A field's **declared type flows through `.`**: if the value's type is a known record (e.g. an
annotated param `b: Box`, a constructor literal `Box{…}`, or a chain like `p.bbox`), then
`b.w` has `Box`'s declared type for `w`, and a mismatch downstream is caught (see
[`examples/mistyped-field.prism`](examples/mistyped-field.prism)). **Records stay open**: an
*undeclared* field (or a field on a value whose type isn't known, or on a multi-variant `or`
type where the variant is ambiguous) stays gradual (`_`) — so a shape can still carry an extra
hue `h`. Reading a field via a `match` binding (`Circle{radius} => …`) is the other common path.

**Construction must be complete.** Building a *declared* record without all of its declared
fields is an error — `Pt{ x: 3 }` is rejected because `Point` declares `Pt{ x, y }` (see
[`examples/incomplete-record.prism`](examples/incomplete-record.prism)). This is the dual of the
`and` reading (“all fields present”). *Extra* fields are still fine (records stay open), and an
*undeclared* constructor (e.g. an ad-hoc `Cell{u, v}` you never declared) carries no requirement.

### Variants — the `or` type (sum types)

A sum (one of several) is written with `or`, and may span multiple lines:

```prism
Shape : Circle{ radius: Num }
     or Square{ side: Num }
     or Triangle{ base: Num, height: Num }
```

Each `Tag{...}` is a constructor. A bare uppercase name (`DivByZero`) is a nullary
constructor. A value built with `Circle{...}` has the type of its owning sum (`Shape`).

> **Teaching point:** an `and` type demands you *provide every field*; its dual, an `or`
> type, demands you *handle every variant* (see exhaustiveness, §7).

## 5. Effect: `!world`

An effect marks a change to the world. The only built-in world in v0 is `console`:

```prism
show!console expr        -- write a line to stdout; yields ()
read!console             -- read a line from stdin; yields Text
```

`!world` in a signature declares which effects a function performs. **Purity is the absence
of `!`.** Effects **propagate**: if `f` calls `g` and `g` is `!console`, then `f` is
`!console` too — and the checker requires `f` to declare it.

**Granularity — a coarse effect subsumes finer ones.** `!io` is an umbrella effect: a function
may declare `!io` and still perform `!console` (and the reserved `!file` / `!net` / `!random` /
`!time`). It is **one-way** — an `!io` signature covers a `!console` body, but a `!console`
signature does *not* cover a body that performs `!io` (the coarse effect would leak unannounced;
see [`examples/effect-narrow.prism`](examples/effect-narrow.prism)). In v0 only `console` is a
real effect, so `!io` is mostly forward-looking; the relation is in place for when more worlds
arrive. ([`examples/effects.prism`](examples/effects.prism) shows `!io` covering `!console`.)

```prism
greetAll(names: List[Text]) : () !console  <-
  map(names, n -> show!console "hi {n}")
  ()
```

Effects accumulate as a **row** (a set of labels). Effects are tracked but the value is
unchanged — contrast failures (§6), which change the value.

## 6. Failure: `?Error`

> An error is not special: it is the `or` type "success **or** failure", lifted into flow.
> `: Num ?DivByZero` means "a `Num`, or a `DivByZero`".
>
> (`?` is the **failure** voice and nothing else — it is never a type. The gradual *Unknown*
> type is written `_` instead; see §11.)

Producing outcomes:

```prism
ok expr        -- a success carrying expr
fail Tag       -- a failure carrying the error Tag
```

Consuming them — exactly two ways:

```prism
try expr       -- PROPAGATE: if expr failed, throw the failure up to the caller's `?` row
               -- (binds tightly: `try f(x)` is `try (f(x))`, not `try (f(x) + ...)`)
```

```prism
expr match               -- HANDLE with match: consume the failure, removing `?` from the type
  ok v   =>  ...
  fail e =>  ...
```

```prism
attempt                  -- HANDLE with attempt/rescue: run a block, catch declared failures
  a  <-  try askNumber("x?")
  show!console "got {a}"
rescue
  BadNumber  =>  show!console "not a number"
```

A fallible value used where a plain value is expected (an operand, an argument, a list
element, inside `"{...}"`) without being handled is an **error**: "unhandled failure".
Failures also accumulate as a **row** (`?{BadNumber, DivByZero}`).

`rescue` is partial by design: failures it does not handle propagate onward (and must then
be declared by the enclosing function).

## 7. Pattern matching and exhaustiveness

`scrutinee match` followed by an indented block of `pattern => body` arms:

```prism
classify(n: Num) : Text  <-
  n match
    0  =>  "zero"
    _  =>  "nonzero"
```

Patterns: number/text literals, `true` / `false` (Bool is a two-variant `or` type), `_`
(wildcard), a lowercase name (binds), `Tag{field: pat, ...}` or bare `Tag`, `ok pat`,
`fail pat`, and lists `[a, b]` / `[head, ..tail]`. Matching `true`/`false` is one way to branch
on a computed condition:

```prism
max(a: Num, b: Num) : Num  <-
  (a < b) match
    true   =>  b
    false  =>  a
```

For the common case there is also **`if cond then a else b`** — an expression that desugars to
exactly that Bool match (both branches required; `else if` chains naturally):

```prism
sign(n: Num) : Text  <-  if n < 0 then "neg" else if n == 0 then "zero" else "pos"
```

A `match` must be **exhaustive**. A wildcard `_` or a bare-variable pattern covers everything;
otherwise the checker requires, by scrutinee:

| Scrutinee | Exhaustive when… |
|---|---|
| `or` type | every variant is covered (an arm naming a non-variant is also an error) |
| `List[T]` | both `[]` and `[h, ..t]` are covered (or a single `[..t]`) |
| fallible value | both an `ok` and a `fail` pattern are present |
| `Bool` | both `true` and `false` are covered (or a `_`) |
| `Num` / `Text` | a catch-all `_` is present (these are unbounded) |
| unannotated (`_`) | always lenient (gradual) |

## 8. Time: `~>`

`<-` derivation has **no order** (it is lazy). When order matters, you are in the time
dimension — write it with `~>`:

```prism
greet(name: Text) : () !console  <-
  show!console "hello, {name}"  ~>  show!console "welcome"  ~>  show!console "bye"
```

Rule: **every step a `~>` orders must touch time** — it must carry an effect (`!`) or a
failure (`?`). Sequencing a pure step is an error ("pure derivation has no order; use `<-`").
A failed step aborts the sequence (the failure propagates). `~>` is a single-line operator
in v0 and binds looser than everything else.

## 9. Generics — holes in a dimension

A generic is a *hole* in one of the dimensions, declared in a `for` clause. Each hole wears
its dimension's marker:

| Hole | Form | Meaning |
|---|---|---|
| type | `T` | a type variable |
| flow | `(T) -> U` | a function (higher-order) |
| effect | `!e` | an effect row variable |
| failure | `?g` | a failure row variable |
| **container** | `F[_]` (or `F[_, _]`) | a higher-kinded type-constructor variable |

One polymorphic `map` covers pure, effectful, and fallible uses at once:

```prism
map for T, U, !e, ?g
  (xs: List[T], f: (T) -> U !e ?g) : List[U] !e ?g  <-
    xs match
      []        =>  []
      [h, ..t]  =>  [ try f(h), ..try map(t, f) ]
```

Row variables (`!e`, `?g`) are instantiated per call site from the argument and flow into the
result. The spread `..` is uniform across dimensions: lists `[h, ..t]`, effect rows
`!{console, ..e}`, failure rows `?{BadNumber, ..g}`.

### Higher-kinded types `F[_]`

`F[_]` is to types what `(T) -> U` is to values — a hole that is itself an arrow. `F` ranges
over container shapes; `F[T]` applies it. Unification decomposes `F[T]` against `List[Num]`
into `F := List`, `T := Num`, and rebuilds `F[U]` as `List[U]`:

```prism
keep for F[_], T (xs: F[T]) : F[T]  <-  xs
nums(xs: List[Num]) : List[Num]  <-  keep(xs)
```

## 10. String interpolation

Inside `"..."`, `{expr}` evaluates `expr` and inserts its text. Interpolation is
**brace-depth aware**, so records nest fine: `"{area(Circle{radius: 2})}"`. The interpolated
expression is real code: its effects propagate and its failures must be handled — nothing
hides in a string.

## 11. Gradual typing (the `_` boundary)

The **gradual Unknown** type is written `_` — the same "don't-care / fill-in" glyph as the
wildcard pattern. It is **not** weak checking; it is the gradual-typing boundary. It applies
where you have **not** annotated (signature-less functions, lambda parameters), and there it is
compatible with anything; `reveal` prints it as `_`. You may also write `_` explicitly as a
type (`f(x: _) : _`). But two **known** types that disagree are always an error. This matches
the design promise: *the compiler infers, the tool reveals* — no annotation means "not yet
contracted."

> **One glyph, one voice.** `?` belongs to the **failure** voice and *only* failure
> (`?Error`, `?{E1, E2}`, `?g`; §6) — `?` is never a type. The Unknown *type* wears the
> fact-voice's `_`. Keeping them on separate glyphs is the point: Prism's whole discipline is
> "one sigil per dimension," so the Unknown type does not borrow the failure sigil.

## 12. Operators and precedence

From loosest to tightest:

| Level | Operators | Notes |
|---|---|---|
| loosest | `~>` | time sequence (single line, right-associative) |
| | `\|>` | pipe (flow sugar, left-associative) — see below |
| | `match` | postfix on the preceding expression |
| | `==` `!=` `<` `>` `<=` `>=` | comparisons → `Bool` |
| | `+` `-` | `+`: `Num+Num→Num` or `Text+Text→Text` (no mixing); `-`: Num |
| tightest | `*` `/` | Num |

**Pipe `|>`** is pure flow-voice sugar that reads left-to-right instead of inside-out:
`x |> f` desugars to `f(x)`, and `x |> f(a)` to `f(x, a)` — the piped value becomes the **first**
argument (Prism's libraries are data-first: `clamp`, `nth`, `at`, `length`, …). It is left-
associative (`x |> f |> g` is `g(f(x))`) and desugars to an ordinary call, so types, effects and
failures flow exactly as the written-out call. The right side is a function name or a call
(`f(a)`); for anything richer, pipe into a lambda: `x |> (v -> f(v) + 1)`. The time voice `~>`
is deliberately *not* overloaded as a pipe (a sequenced step must touch an effect or failure;
conflating it with value-threading muddies the voice — see [NOTES](NOTES.md)).

Unary minus: `-x` parses as `0 - x`. `try`, `ok`, `fail` bind to the immediately following
**postfix** expression (`try f(x)`), so wrap with parentheses for more: `try (a + b)`.
An effect argument also binds tightly: `show!console a + b` is `show!console (a + b)` only
within one line and never crosses a `~>`.

There is no implicit coercion: `1 + "x"` is rejected by both the checker and the runtime.
Build text with interpolation instead: `"{n}x"`.

## 13. Capabilities and constraints

A **capability** is a named set of methods a type can provide (a trait / typeclass):

```prism
capability Ord for T
  compare(a: T, b: T) : Num
```

An **instance** provides it for a concrete type, supplying every method:

```prism
Num provides Ord
  compare(a, b)  <-  a - b
```

A function **requires** a capability with `given`:

```prism
larger for T given T: Ord (a: T, b: T) : T  <-  a
```

The checker enforces four things, each echoing an existing voice:

1. **Discharge** — at a call site, `given T: Cap` requires the concrete `T` to `provide Cap`
   (or the caller to re-declare the same `given`, propagating it). Mirrors failure handling.
2. **Completeness** — a `provides` must define exactly the capability's methods (missing or
   extra → error). Mirrors `and`-fields / match-exhaustiveness.
3. **Coherence** — at most one instance per (type-combination, capability); duplicates are rejected.
4. **Method bodies** — each instance method is checked against the declared signature
   (return type, effects, failures), with the capability's type variable bound to the
   instance type.

A capability-method call (`compare(a, b)`, `fmap(xs, f)`) resolves to its capability, requires
the receiver's type to provide it, and yields the declared return type. At runtime it
**dispatches on the runtime types at the method's type-variable positions** — the parameters
typed by the capability's `T` / `F[_]`.

### Multiple dispatch

A capability may range over **more than one type variable** (`for A, B`); then an instance names a
type **combination** (`A provides Cap for B`), and a method is chosen by the runtime types of
**several arguments at once** — the case single dispatch can't express (the outcome depends on
*both* operands, not one "owner"). Resolution stays exhaustive: a combination with no instance is
rejected at the call site. See [`examples/collide.prism`](examples/collide.prism).

```prism
capability Collide for A, B
  hit(a: A, b: B) : Text

Ship provides Collide for Asteroid               -- (A := Ship, B := Asteroid)
  hit(a, b)  <-  "ship grazes the asteroid"
Bullet provides Collide for Asteroid             -- a different pair -> a different `hit`
  hit(a, b)  <-  "bullet shatters the asteroid"

hit(Ship{}, Asteroid{})                          -- picks the (Ship, Asteroid) instance
```

Single dispatch is just the one-type-variable case (`for T` → a one-element combination), so both
share one mechanism.

```prism
capability Functor for F[_]
  fmap for T, U (xs: F[T], f: (T) -> U) : F[U]

List provides Functor
  fmap(xs, f)  <-
    xs match
      []        =>  []
      [h, ..t]  =>  [ f(h), ..fmap(t, f) ]

doubleAll(xs: List[Num]) : List[Num]  <-  fmap(xs, n -> n * 2)
```

## 14. Tooling: check and reveal

- `prism check <file>` reports every violation, each prefixed with its **source line**
  (`line N: ...`). A clean program prints `OK`.
- `prism reveal <file>` prints the full contract of each definition. For signed definitions
  it shows the declared contract `[declared]`; for unsignatured ones it shows the contract it
  **inferred** from the body `[inferred]` — the "the tool reveals" half of the thesis.

```sh
$ prism reveal examples/infer.prism
  ask : Num !{console} ?{BadNumber}      [inferred]
  greet(name) : Unit !{console}          [inferred]
```

## 15. Built-ins

| Name | Contract |
|---|---|
| `parseNum` | `(Text) -> Num ?BadNumber` |
| `show!console` | `(_) -> () !console` (writes a line) |
| `read!console` | `() -> Text !console` (reads a line) |
| `sin` `cos` `sqrt` `abs` `floor` | `(Num) -> Num` (math) |
| `pi` | `Num` (the constant π) |
| `at` | `(List, Num) -> _` — **O(1)** indexed read (0-based). Lists stay immutable; this only reads. In-bounds is the caller's contract (out-of-bounds is a hard error, like `sqrt` of a negative). |
| `len` | `(List) -> Num` — **O(1)** length. |
| `words` | `(Text) -> List` — split Text on whitespace into a list of word-Texts (drops empties). |

> `at`/`len` are the fast primitives; [`lib/list`](lib/list.prism)'s `nth`/`length` are the
> O(n) structural-recursion versions kept for teaching. Reach for `at` in grids and simulations
> (neighbour lookups), where O(n) access turns an O(n) pass into an O(n²) one.

## Drawing and animation (the canvas contract)

Prism the *language* knows nothing about graphics — a drawing is just a pure **value**, and
rendering is the tool's job (the same stance as `check` / `reveal`). The browser playground
recognises two shapes of value:

- **A still picture (Layer A).** Define `picture : List[Shape]` — a list of absolute-coordinate
  shapes. Press **Draw**. The drawing vocabulary the canvas knows is exactly:

  | Shape | Fields |
  |---|---|
  | `Line` | `x1, y1, x2, y2` |
  | `Dot` | `x, y` |
  | `Circle` | `x, y, r` |
  | `Rect` | `x, y, w, h` |
  | `Poly` | `pts` (a `List` of `Pt{x, y}`) — a polyline / polygon |

  Any shape may also carry optional fields (records are open, so adding them is free):
  **`h`** (hue 0–360; without it, a rainbow along draw order), **`a`** (opacity 0–1, for
  translucent blobs / glow / fog), and **`fill`** (fill a `Circle`/`Poly` instead of stroking
  it). See the translucency demos (`fog`, `lightning`, `confetti`, …) in ALGORITHMS.md.

- **An animation.** Define a **pure** function `frame(t) : Picture` (or `: List[Shape]`). Press
  **Animate**: the host advances `t` (in seconds) and renders `frame(t)` each tick. The whole
  scene is a *function of time* with **no mutable state** — and because `frame`'s signature has
  no `!`, the checker **certifies the animation is pure**: a `frame` that hides a `show!console`
  is rejected (`performs effect !console but its signature declares no effects`). Write `frame`
  periodic over `t ∈ [0, 2π]` for a smooth loop. See
  [`physics/pendulum-anim.prism`](physics/pendulum-anim.prism).

The composable **Picture algebra** (`over` / `beside` / `above` / `scale` / `rotate` / `render`)
lives in the pure library [`lib/picture.prism`](lib/picture.prism); `render` lowers a `Picture`
back to the `List[Shape]` the canvas draws. (`rotate` turns a `Rect` into a `Poly` of its four
corners, since a tilted rectangle is no longer axis-aligned.)

**Share a link.** The playground's **🔗 Share** button encodes the current code into the page's
`#code=…` URL fragment (no server) — open that link and the editor loads straight into that
program. Priority on load: a shared `#code=` link, then your auto-saved code, then the default.

## 16. Grammar (informal)

```
program     := definition*
definition  := funcOrVal | typeDecl | capability | provides | include
include     := "include" Text
funcOrVal   := name [generics] ["(" params ")"] [":" sigTail] "<-" body
typeDecl    := Name ":" variant ("or" variant)*            -- no "<-"
capability  := "capability" Name ["for" tvar ["[" "_"("," "_")* "]"]] memberBlock
provides    := Name "provides" Name memberBlock
generics    := "for" hole ("," hole)* ["given" tvar ":" Name ("," ...)*]
hole        := name | "!" name | "?" name | name "[" "_"("," "_")* "]"
sigTail     := type ("!" row | "?" row)*
type        := Name ["[" type ("," type)* "]"] | "(" type* ")" ["->" sigTail]
params      := (name [":" type]) ("," ...)*
body        := expr | INDENT stmt+ DEDENT
stmt        := name "<-" expr | expr
expr        := seq
seq         := opExpr ("~>" opExpr)*
opExpr      := <Pratt: comparisons, + -, * /> postfix-match
postfix     := atom ( "(" args ")" | "." name | "!" world [arg] )*
atom        := Num | Text | "true" | "false" | name | Ctor["{"fields"}"]
             | "ok" postfix | "fail" postfix | "try" postfix
             | "(" [params "->" expr | expr] ")" | "[" listItems "]" | "attempt" ...
pattern     := "_" | literal | name | Tag ["{" fieldPats "}"] | "ok" pat | "fail" pat
             | "[" pat* [".." name] "]"
```

## 17. Error catalog (what the checker reports)

All errors are prefixed `line N:`.

- **type mismatch** — return value vs declared type; argument vs parameter; list elements
  disagree; match arms disagree; arithmetic needs `Num`; `+` mixes `Text`/`Num`.
- **incomplete record** — building a declared record without all its fields (`Pt{ x: 3 }`).
- **duplicate definition** — two top-level names collide after `include` merges them flat.
- **unhandled failure** — a fallible value used (operand / argument / list element /
  interpolation) without `try` or `match`.
- **effect leak** — a function performs an effect its signature omits.
- **failure leak** — a function can fail with a `?` its signature omits.
- **non-exhaustive match** — a missing variant / list case / `ok`-or-`fail` / catch-all;
  or an arm naming a non-variant.
- **pure step in `~>`** — a sequenced step that touches neither effect nor failure.
- **capability** — unsatisfied `given`; incomplete or duplicate instance; an instance method
  body that violates the declared signature.

## 18. Command-line reference

```sh
prism run    <file.prism>     # run (alias: python prism.py <file>)
prism check  <file.prism>     # static check (alias: python check.py <file>)
prism reveal <file.prism>     # infer + show contracts (alias: python check.py --reveal <file>)
prism test                    # regression suite (alias: python test.py)
prism help
```

(`prism` = the bundled launcher; everywhere it can be replaced by `python cli.py`.)
