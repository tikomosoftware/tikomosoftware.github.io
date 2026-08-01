# Prism overview — ideas and how to use it

This is the front door to Prism: what it is, how to think about it, and how to use it.
For the complete specification, see [REFERENCE.md](REFERENCE.md). For hands-on learning, see
[TUTORIAL.md](TUTORIAL.md) or [GETTING_STARTED.md](GETTING_STARTED.md). For algorithm examples,
see [ALGORITHMS.md](ALGORITHMS.md).

---

## 1. What it is — and what it is not

**Prism is a pedagogy-first programming language for the AI era**: a design experiment intended
to be worth learning from. Its goal is not production speed or brevity. It aims for two things:

- **Let people strengthen their way of thinking by reading code.**
- **Let people read what AI-written code may touch and how it may fail from its contract (signature).**
  That narrows review: instead of reading every line with the same intensity, you can focus on the
  parts that need it. (The contract guarantees effects and failures; the correctness of the
  computation itself still needs separate validation.)

> **It is not a first programming language for beginners.** It uses substantial type-system ideas
> such as effects, failures, capabilities, and higher-kinded types. Anyone can explore the visual
> playground, but the language itself is conceptually dense and meant for people who want to learn
> about types and contracts.

Be clear about what it is *not*:

- **It is not procedural.** `<-` is an order-free derivation: line order has no meaning because
  evaluation is lazy. Prism is declarative and functional in spirit. When you genuinely need
  “this, then that,” say so with the time voice, `~>`.
- **It is not a production language.** I/O is limited to the console; there is no standard library,
  module system, file or network access, or package manager. It is a precise, working scale model
  of an engine: the combustion mechanism (the semantics) is real, but it is not a commuter car
  with all the production equipment. That is a deliberate constraint, not an omission.

## 2. The central idea — four fundamental voices, plus time

Every computation answers four questions at once. Prism gives each dimension its own notation and
**never mixes them**.

| Voice | Question | Notation |
|---|---|---|
| **fact** | What is it? (types and data) | `:`  `and`  `or` |
| **flow** | What is it derived from? (dependencies) | `<-`  `=>`  `\|>` |
| **effect** | What in the world does it change? | `!world` |
| **failure** | How can it fail? | `?Error`  `try`  `match` |

There is a fifth, advanced voice: **time**, `~>`, for ordering itself. Use it only when you need
“this, then that”; pure flow has no order. The first four voices come first, and `~>` is an
advanced feature — the same framing used in the README and reference.

A function signature puts all of this in one place, making an **honest contract**:

```prism
divide(a: Num, b: Num) : Num  ?DivByZero  <-  ...
--                       ^type  ^failure    ^body
```

The static checker (`check.py`) enforces that the implementation keeps that contract. **Prism’s
value is not new notation, but this static checker — its type system.** Without checking, `!` and
`?` are only marks you can write, not claims the language verifies.

## 3. How it differs from related languages

Its closest relatives are Rust (`Result` and traits) and Haskell (purity and type classes). Prism
has its own emphases:

- **The fundamental voices appear in the contract.** Types, effects, and failures sit together in
  a signature; when needed, time `~>` is explicit too. They do not scatter through the program.
- **`<-` is order-free derivation.** Swap two lines and the meaning is unchanged. It declares
  dependencies rather than listing commands.
- **Errors are OR types written in the type.** `?DivByZero` is part of the type. The only paths are
  `try` for propagation and `match`/`rescue` for handling, so there is no hidden exception path.
- **Effects appear in the type.** `!console` is required in the signature and propagates through
  calls. Purity means the absence of `!`.
- **Time `~>` is checked as a first-class concern.** Every ordered step must have an effect or a
  failure; a pure step has no order. A language that can point out “you do not need an order here”
  is unusual.
- **Generics are holes opened in a dimension.** `for T, U, !e, ?g, F[_]` shows which dimension each
  hole belongs to. One `map` can cover pure, effectful, and fallible computations.
- **AND and OR are symmetric.** `and` types demand that you provide every field; `or` types demand
  that you handle every case (exhaustively). Constructing a declared record also requires every
  declared field.
- **The pipe `|>` is pure flow sugar.** `x |> f` means `f(x)`, and `x |> f(a)` means `f(x, a)` with
  data first. It desugars to a call, so types, effects, and failures pass through unchanged. It
  intentionally does not blur the time voice `~>`.
- **Effects can have granularity.** `!io` contains `!console` in one direction. A broad declared
  effect may use a narrower one in its body; the reverse is rejected as a leak.

```prism
-- Failures, effects, exhaustiveness, and capabilities all show up in signatures and checking.
Shape : Circle{ radius: Num }  or  Square{ side: Num }

area(s: Shape) : Num  <-          -- no ? and no ! = pure and infallible
  s match                          -- omitting Circle or Square is rejected by static checking
    Circle{radius}  =>  radius * radius * 3
    Square{side}    =>  side * side
```

## 4. Using Prism (CLI and browser)

There is no build step. You need only **Python 3**. The unified CLI is `cli.py` (with the `prism`
launcher included).

```sh
prism run    examples/calc.prism      # run (= python cli.py run ...)
prism check  examples/calc.prism      # static check (OK / FAIL with line numbers)
prism reveal examples/infer.prism     # infer and show the contract of unsigned code
prism test [core|gallery|all]         # regression tests (core: language only; all: everything, default)
prism serve                           # start the browser playground
```

- **The static checker teaches as well as rejects.** Errors identify their location with `line N:`.
- **`reveal`** is the second half of “the compiler infers, the tool makes visible”: it infers and
  displays the contract (types, effects, and failures) of a function without a signature.
- **The browser edition** (`playground.html`) runs the same `prism.py` and `check.py` through
  Pyodide (CPython compiled to WASM). It is neither a port nor a separate implementation. For
  offline use, run `prism fetch-pyodide` to prefer a local copy.

## 5. Working with AI — the core thesis

“Working with AI” has two distinct meanings. Keep them separate.

**(A) A method of working — the main point.** No special API is needed; it is a development
practice:

```
Human          → writes the signature (contract)
AI             → writes the implementation (the right side of <-)
Static checker → guarantees the implementation respects the contract (prism check → OK)
Human          → uses the signature to check the behavioral boundary, then focuses review on
                 contract violations, edge cases, and the algorithm
```

Normally, trusting AI-written code means reviewing its whole body. Prism’s bet is this: **if types,
effects, failures, and time are forced into a signature, and static checking ensures they agree,
then the signature guarantees the boundary of what the code touches and how it can fail. Review can
focus on the necessary part: whether the implementation is correct.** It does not guarantee that
correctness by itself. The collaboration is a division of labor: **human = contract, AI =
implementation, static checker = referee**.

**(B) A practical loop for asking an LLM to write Prism.** An AI does not know Prism from its
training data, because it is a new language. Therefore:

1. Give it `REFERENCE.md` and a few examples as context (a system prompt).
2. Have it write the **signature first**, then generate the implementation — the division of labor
   in (A).
3. Run **`prism check`, return the error to the AI unchanged, and ask it to fix the code**. Repeat.

This is where error quality matters: errors have line numbers and focus on the contract, so you can
paste them straight back to the AI. `reveal` can also show an inferred contract.

> The practical scope is not “build real applications with AI in Prism.” It is to make small,
> contract-dense programs with AI; practise reading contracts and trusting them appropriately; and
> take that method back to production languages.

## 6. The language core and repository layout

**The engine itself is only two files:**

| File | Role |
|---|---|
| **`prism.py`** | The language itself: lexer, parser, and tree-walk evaluator (what `run` executes) |
| **`check.py`** | Static checker: types, effects, failures, exhaustiveness, capabilities, higher-kinded types, time, and `--reveal` inference |

Together they are about 1,900 lines. They stay small because (1) a tree walker is the simplest
execution model, (2) Python supplies low-level facilities such as numbers, strings, memory, and
exceptions, (3) the scope is deliberately narrow, and (4) the four voices are orthogonal, so new
features fit existing mechanisms (`unify` and `subst`). **Being small enough to read the semantics
at once is part of what makes the language worth learning from.**

**The skeleton is closed.** The roadmap has been completed: pipes `|>`, effect granularity,
**multiple dispatch**, and include-collision detection are implemented. A deliberate boundary has
been drawn around the remaining horizon ([NOTES.md](NOTES.md), observation #22): full namespaces
(flat merging plus collision detection is enough) and real I/O expansion (the effect relationship
exists, but `console` is the only effect). *Being able to explain why a feature is not added is
closer to completion than adding features forever.*

**Supporting tools and artifacts:**

```
cli.py  prism  prism.cmd          unified CLI and launchers
test.py                           regression tests (split into core / gallery / all)
playground.html                   browser playground (runs the core and a 300-image gallery)
lib/(12)                          includable standard libraries (list/math/picture/…)
examples/(34)  tutorial/(6)  algorithms/(9)   sample programs
README / GETTING_STARTED / TUTORIAL /          documentation
  REFERENCE / ALGORITHMS / NOTES / IDEAS / OVERVIEW.md
LICENSE  .gitignore
pyodide/                          optional: fetched by fetch-pyodide and not committed
```

## 7. Positioning, in one sentence

> Prism is an **educational tool** for experiencing how to build trust in the AI era with a minimal
> set of tools (about 1,900 lines). Its collaboration model is a way of working: **humans write the
> contract, AI writes the implementation, and static checking acts as referee.**
