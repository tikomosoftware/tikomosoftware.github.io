# Getting started with Prism

Prism is a tiny, pedagogy-first programming language. There is **no build or compile
step** — programs run directly through a tree-walking interpreter, and a separate
static checker reads your "contract" (types, effects, failures, …) on demand.

You only need **Python 3.8+**. There are **no third-party dependencies**.

---

## 1. Get the code

```sh
git clone <this-repo> prism
cd prism
python --version          # 3.8 or newer
```

That's the whole install. Nothing to compile.

## 2. Run your first program

```sh
python cli.py run examples/statemachine.prism
# red
# green
# yellow
```

`cli.py` is the single entry point. Four subcommands:

| Command | What it does |
|---|---|
| `python cli.py run    <file>` | run a program (interpreter) |
| `python cli.py check  <file>` | statically check it (types / effects / failures / exhaustiveness / capabilities) |
| `python cli.py reveal <file>` | infer and print the full contract of each definition |
| `python cli.py test`          | run the regression suite |

Each engine is also runnable on its own: `python prism.py <file>`, `python check.py <file>`,
`python check.py --reveal <file>`.

## 3. (Optional) type `prism` instead of `python cli.py`

Put the project folder on your `PATH` and use the bundled launcher:

- **Windows:** `prism.cmd` is provided — `prism run examples/calc.prism`
- **macOS / Linux:** `./prism run examples/calc.prism` (or symlink `prism` into a bin dir)

The rest of the docs write `prism <cmd>`; read that as `python cli.py <cmd>` if you skip this step.

## 4. Write a program

Create `hello.prism`:

```prism
main : () !console  <-
  show!console "hello, Prism"
```

Then:

```sh
prism run hello.prism      # hello, Prism
prism check hello.prism    # OK
```

Note the signature `main : () !console`. The `!console` says "this touches the console."
Try removing it and run `prism check` — the checker will tell you the effect is undeclared,
**with the line number**. That is the whole idea of Prism: the signature is a contract, and
the checker holds you to it.

## 4b. Run it in the browser (same engine)

There is a zero-install playground that runs **the exact same `prism.py` / `check.py`** in
your browser via [Pyodide](https://pyodide.org) (CPython compiled to WebAssembly) — no port,
no second implementation.

```sh
prism serve                # starts a local server, prints the URL
# open http://localhost:8000/playground.html
```

Pick an example, then **Run / Check / Reveal** — or **Draw**. The playground **highlights the
button that fits** your code (and shows a `→` hint): a program with a `picture` value suggests
**Draw**, one with `main` suggests **Run**, otherwise **Check / Reveal**. Press **Ctrl/Cmd+Enter**
to run the highlighted action. If your program defines a `picture` (a list of shapes like
`Line{…}` / `Dot{…}` / `Circle{…}` / `Rect{…}`), **Draw** renders it on a canvas — and the
figure **draws itself**, in colour (a rainbow along the draw order). A shape can also carry
its own hue with an `h` field (0–360), e.g. `Dot{x: 0, y: 0, h: 120}` — see
`physics/colorwheel.prism`. Try the ★ examples and press Draw. The `stdin` box feeds
`read!console`.

Some examples use **`slider(default, min, max)`** in place of a number (e.g. the ★ de Jong /
rose / Lissajous "live" ones). The playground turns each into a **drag control** — move it
and the picture updates live. (On the CLI, `slider` just returns its default, so the program
still runs.)
(It must be *served* over HTTP — opening the file directly with `file://` is blocked, because
the page fetches the engine files. `prism serve` handles that. The first run downloads Pyodide,
which takes a few seconds.)

### Offline (self-hosted Pyodide)

By default the playground pulls Pyodide from a CDN (needs internet). To run **fully offline**,
download Pyodide once into the project:

```sh
prism fetch-pyodide        # ~5 MB download -> ./pyodide/ (~14 MB on disk; git-ignored)
prism serve                # the playground now prefers the local copy
```

The page checks for `./pyodide/pyodide.js` and uses it when present (the status bar shows
`ready (Pyodide: local)`), otherwise falls back to the CDN (`ready (Pyodide: CDN)`). The
`pyodide/` folder is in `.gitignore`, so the large binaries are never committed.

## 4c. The docs as web pages, and publishing the site

The Markdown docs also render as HTML in the browser — **`docs.html`** fetches a `.md` and
renders it (the `.md` files stay the single source, no build step):

```sh
prism serve     # then open http://localhost:8000/        (index.html — the landing page)
                #              http://localhost:8000/docs.html?p=REFERENCE.md
```

- **`index.html`** — a landing page (Playground / Docs buttons).
- **`docs.html?p=NAME.md`** — renders any doc (Overview, Getting started, Tutorial, Algorithms,
  Reference, README), with a nav bar; intra-doc `.md` links stay inside `docs.html`.
- **`playground.html`** — the live editor + canvas.

**Publishing.** The whole folder is *static* — drop it on any static host (GitHub Pages,
Netlify, …). No build. The engine (`prism.py`, `check.py`), the gallery `.prism` files, and
the docs `.md` are all fetched at runtime; Pyodide and the Markdown renderer come from a CDN
(so the published site needs internet). For a fully offline/self-contained deploy, run
`prism fetch-pyodide` first so the playground prefers the bundled copy. (`pyodide/` is
git-ignored, so on a typical static host the playground just uses the CDN.)

## 5. Let the tool reveal a contract

Write code with **no** signature and ask Prism what it inferred:

```prism
ask  <-  try parseNum(read!console)
```

```sh
prism reveal ask.prism
#   ask : Num !{console} ?{BadNumber}   [inferred]
```

## Where to go next

- **[TUTORIAL.md](TUTORIAL.md)** — a guided path from "hello" to capabilities, in small steps.
- **[REFERENCE.md](REFERENCE.md)** — the complete language reference (syntax, the four voices,
  generics, capabilities, higher-kinded types, the time voice, grammar, errors).
- **[README.md](README.md)** — the philosophy and a tour of why Prism exists.
- **`examples/`** — 19 runnable / checkable programs (the same files the test suite pins down).
