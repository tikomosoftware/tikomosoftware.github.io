# Prism tutorial

A guided path from "hello" to capabilities, in six small steps. Each step is a real,
runnable file in [`tutorial/`](tutorial/). Run any of them with:

```sh
prism run   tutorial/01-hello.prism      # or: python cli.py run tutorial/01-hello.prism
prism check tutorial/01-hello.prism
```

If you haven't set up `prism` on your PATH yet, see [GETTING_STARTED.md](GETTING_STARTED.md);
just read `prism` below as `python cli.py`.

The one idea behind all of it: **a signature is a contract, and the checker holds you to it.**
Every step, try breaking the program and running `prism check` — the error (with a line number)
is the lesson.

---

## 1. Hello — a program is its contract

[`tutorial/01-hello.prism`](tutorial/01-hello.prism)

```prism
main : () !console  <-
  show!console "hello, Prism"
```

`main : () !console` reads "returns `()` (nothing), and **touches the console**". The `<-`
introduces the body. `show!console` is the one effect we use; `!console` in the signature
declares it.

```sh
$ prism run tutorial/01-hello.prism
hello, Prism
```

**Try it:** delete `!console` from the signature and `prism check`. The checker reports the
undeclared effect, at the line of the declaration. That refusal is the whole point.

## 2. Values — derivation has no order

[`tutorial/02-values.prism`](tutorial/02-values.prism)

```prism
fahrenheit : Num  <-  celsius * 9 / 5 + 32
celsius    : Num  <-  30
```

`<-` derives a value from others. **Line order is meaningless** — `fahrenheit` is written
above the `celsius` it uses, and that's fine. You're forced to think in dependencies, not in
"top to bottom". (`"... {celsius} ..."` is string interpolation: `{expr}` inserts a value.)

```sh
$ prism run tutorial/02-values.prism
celsius 30 = fahrenheit 86
```

## 3. Failure — errors are values you must handle

[`tutorial/03-failure.prism`](tutorial/03-failure.prism)

```prism
divide(a: Num, b: Num) : Num ?DivByZero  <-
  b match
    0  =>  fail DivByZero
    _  =>  ok (a / b)
```

`?DivByZero` in the signature says "this can fail with `DivByZero`". You produce outcomes with
`ok` / `fail`, and you must eventually **handle** them. Two ways: `try` propagates a failure to
your caller; `attempt`/`rescue` catches it:

```prism
main : () !console  <-
  attempt
    q  <-  try divide(10, 2)
    show!console "10 / 2 = {q}"
    show!console "10 / 0 = {try divide(10, 0)}"
  rescue
    DivByZero  =>  show!console "10 / 0 = undefined"
```

```sh
$ prism run tutorial/03-failure.prism
10 / 2 = 5
10 / 0 = undefined
```

**Try it:** drop the `?DivByZero` from `divide`'s signature and `prism check` — the failure
"leaks" past the contract, and the checker says so.

## 4. Types — an `or` type, handled exhaustively

[`tutorial/04-types.prism`](tutorial/04-types.prism)

```prism
Shape : Circle{ radius: Num }  or  Square{ side: Num }

area(s: Shape) : Num  <-
  s match
    Circle{radius}  =>  radius * radius * 3
    Square{side}    =>  side * side
```

An `or` type lists alternatives. A `match` over it must cover **every** variant — the dual of
"a record must give every field".

```sh
$ prism run tutorial/04-types.prism
circle r=2 -> 12
square s=3 -> 9
```

**Try it:** delete the `Square` arm and `prism check`. It tells you exactly which variant is
missing, on which line.

## 5. Generics — one function, every shape

[`tutorial/05-generics.prism`](tutorial/05-generics.prism)

```prism
map for T, U, !e, ?g
  (xs: List[T], f: (T) -> U !e ?g) : List[U] !e ?g  <-
    xs match
      []        =>  []
      [h, ..t]  =>  [ try f(h), ..try map(t, f) ]
```

A generic is a **hole**. Here there are four: a type hole `T`/`U`, an effect hole `!e`, and a
failure hole `?g`. The signature reads: "`map`'s effect and failure are exactly those of the
`f` you give me — I add nothing." So one `map` serves pure, effectful, and fallible uses; no
`mapM`, no `tryMap`.

```sh
$ prism run tutorial/05-generics.prism
doubled = [2, 4, 6]
```

## 6. Capabilities — methods that resolve and dispatch

[`tutorial/06-capabilities.prism`](tutorial/06-capabilities.prism)

```prism
capability Show for T
  render(x: T) : Text

Num  provides Show
  render(x)  <-  "a number"
Text provides Show
  render(x)  <-  x

describe for T given T: Show (x: T) : Text  <-  render(x)
```

A **capability** is a set of methods a type can provide. `Num` and `Text` each `provide Show`.
A function that calls `render` must require it: `given T: Show`. The call to `render(x)`
resolves to the capability, checks the receiver provides it, and at runtime **dispatches on
the value's type**.

```sh
$ prism run tutorial/06-capabilities.prism
a number
hello
```

**Try it:** add `Bool provides Show` with `render(x) <- x` and `prism check` — the body returns
`Bool`, not `Text`, and the checker rejects the instance. The contract reaches all the way into
the method body.

---

## Where to go next

- **[REFERENCE.md](REFERENCE.md)** — every feature, the grammar, the error catalog.
- **`examples/`** — 19 fuller programs, including a working expression evaluator (`calc.prism`),
  a traffic-light state machine, higher-kinded `Functor`, and the time voice `~>`.
- `prism reveal <file>` — write a function with **no** signature and let Prism show you the
  contract it infers.
