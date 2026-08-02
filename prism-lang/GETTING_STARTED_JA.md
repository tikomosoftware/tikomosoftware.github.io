# Prism をはじめる

Prism は、学ぶことを最優先にした小さなプログラミング言語です。**ビルドやコンパイルは不要**で、プログラムはツリーウォーク型のインタプリタでそのまま動きます。必要なときに別建ての静的チェッカーが「契約」（型・副作用・失敗など）を確認します。

必要なのは **Python 3.8以降**だけです。**外部依存はありません。**

---

## 1. コードを取得する

```sh
git clone <this-repo> prism
cd prism
python --version          # 3.8 以降
```

これで導入は完了です。コンパイルするものはありません。

## 2. 最初のプログラムを動かす

```sh
python cli.py run examples/statemachine.prism
# red
# green
# yellow
```

入口は `cli.py` だけです。サブコマンドは4つあります。

| コマンド | 内容 |
|---|---|
| `python cli.py run    <file>` | プログラムを実行する（インタプリタ） |
| `python cli.py check  <file>` | 静的チェックをする（型／副作用／失敗／網羅性／能力） |
| `python cli.py reveal <file>` | 各定義の完全な契約を推論して表示する |
| `python cli.py test`          | 回帰テストを実行する |

各エンジンは単体でも実行できます: `python prism.py <file>`、`python check.py <file>`、
`python check.py --reveal <file>`。

## 3. （任意）`python cli.py` の代わりに `prism` と打つ

プロジェクトのフォルダを `PATH` に追加し、同梱のランチャを使います。

- **Windows:** `prism.cmd` を同梱しています — `prism run examples/calc.prism`
- **macOS / Linux:** `./prism run examples/calc.prism`（または `prism` を bin ディレクトリへシンボリックリンク）

以降のドキュメントでは `prism <cmd>` と書きます。この手順を省く場合は、`python cli.py <cmd>` と読み替えてください。

## 4. プログラムを書く

`hello.prism` を作ります。

```prism
main : () !console  <-
  show!console "hello, Prism"
```

続けて実行します。

```sh
prism run hello.prism      # hello, Prism
prism check hello.prism    # OK
```

署名 `main : () !console` に注目してください。`!console` は「このプログラムはコンソールに触れる」という宣言です。これを消して `prism check` を実行すると、**行番号つき**で「副作用が宣言されていない」と指摘されます。これが Prism の考え方です。署名は契約書であり、静的チェックは本体が契約を守ることを確かめます。

## 4b. ブラウザで動かす（同じエンジン）

導入不要の遊び場では、[Pyodide](https://pyodide.org)（WebAssembly にコンパイルされた CPython）を通して、**まったく同じ `prism.py` / `check.py`** をブラウザで動かします。移植版でも別実装でもありません。

```sh
prism serve                # ローカルサーバを起動し、URL を表示
# http://localhost:8000/playground.html を開く
```

例を選んでから **Run / Check / Reveal**、または **Draw** を押してください。遊び場はコードに合うボタンをハイライトし（`→` のヒントも表示）、`picture` 値を含むプログラムには **Draw**、`main` を含むプログラムには **Run**、それ以外には **Check / Reveal** を案内します。ハイライトされた操作は **Ctrl/Cmd+Enter** で実行できます。`picture`（`Line{…}` / `Dot{…}` / `Circle{…}` / `Rect{…}` のような図形のリスト）を定義すると、**Draw** がキャンバスに描画します。図形は描画順に沿った虹色で自動描画されます。各図形に `h` フィールド（0〜360）を付けて色相を指定することもできます。例: `Dot{x: 0, y: 0, h: 120}`。`physics/colorwheel.prism` を参照してください。★付きの例を選び、Draw を押してみましょう。`stdin` 欄は `read!console` に渡されます。

一部の例では数値の代わりに **`slider(default, min, max)`** を使います（たとえば ★ の de Jong / rose / Lissajous の「ライブ」例）。遊び場では各スライダが**ドラッグ操作**になり、動かすと図が即座に更新されます。（CLI では `slider` は既定値を返すだけなので、プログラムは変わらず動きます。）

このページは HTTP で配信する必要があります。`file://` で直接開くと、エンジンのファイルを取得できないためブロックされます。`prism serve` がその役割を果たします。初回実行では Pyodide のダウンロードに数秒かかります。

### オフライン（Pyodide をローカル配置）

既定では、遊び場は CDN から Pyodide を取得します（インターネット接続が必要です）。完全にオフラインで動かすには、一度だけプロジェクト内に Pyodide をダウンロードします。

```sh
prism fetch-pyodide        # 約5 MBをダウンロード -> ./pyodide/（ディスク上では約14 MB、Git管理外）
prism serve                # 遊び場はローカルコピーを優先する
```

ページは `./pyodide/pyodide.js` を検出して存在すれば利用します（ステータスバーに `ready (Pyodide: local)` と表示）。なければ CDN にフォールバックします（`ready (Pyodide: CDN)`）。`pyodide/` は `.gitignore` に含まれるため、大きなバイナリがコミットされることはありません。

## 4c. ドキュメントをWebページとして開く・サイトを公開する

Markdown のドキュメントもブラウザで HTML として表示できます。**`docs.html`** が `.md` ファイルを取得して表示するため、Markdown ファイルが唯一の情報源のままでビルドは不要です。

```sh
prism serve     # 起動後に開く:
                # http://localhost:8000/        （ランディングページ: index.html）
                # http://localhost:8000/docs.html?p=REFERENCE.md
```

- **`index.html`** — ランディングページ（遊び場／概要への導線、英日切替）。
- **`docs.html?p=NAME.md`** — ナビゲーション付きでドキュメントを表示。概要・Getting started・Tutorial・Reference は英日を切り替えられ、文書内の `.md` リンクも `docs.html` 内で開きます。
- **`playground.html`** — ライブエディタとキャンバス。

**公開方法。** フォルダ全体は静的です。GitHub Pages や Netlify など、任意の静的ホストに置けます。ビルドはありません。エンジン（`prism.py`、`check.py`）、ギャラリーの `.prism` ファイル、ドキュメントの `.md` は実行時に取得されます。Pyodide と Markdown レンダラは CDN から来るため、公開サイトにはインターネット接続が必要です。完全オフライン・自己完結の配布にするなら、先に `prism fetch-pyodide` を実行して遊び場が同梱コピーを優先するようにします。（`pyodide/` は Git 管理外なので、通常の静的ホストでは遊び場は CDN を使います。）

## 5. ツールに契約を推論させる

**署名なし**のコードを書き、Prism が何を推論するかを尋ねてみます。

```prism
ask  <-  try parseNum(read!console)
```

```sh
prism reveal ask.prism
#   ask : Num !{console} ?{BadNumber}   [inferred]
```

## 次に読むもの

- **[TUTORIAL_JA.md](TUTORIAL_JA.md)** — hello から capability までを小さな手順で辿るガイド。
- **[REFERENCE.md](REFERENCE.md)** — 完全な言語リファレンス（構文、4つの声、ジェネリクス、capability、高階型、時間の声、文法、エラー）。
- **[README.md](README.md)** — Prism の考え方と、なぜ存在するかの案内。
- **`examples/`** — 実行・静的チェックできる19本のプログラム（テストスイートが固定している同じファイル）。
