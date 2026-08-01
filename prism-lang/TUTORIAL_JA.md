# Prism チュートリアル

hello から capability までを、6つの小さな手順で辿るガイドです。各手順は [`tutorial/`](tutorial/) にある実行可能なファイルです。どれも次のように動かせます。

```sh
prism run   tutorial/01-hello.prism      # または: python cli.py run tutorial/01-hello.prism
prism check tutorial/01-hello.prism
```

まだ `prism` を `PATH` に設定していない場合は、[GETTING_STARTED_JA.md](GETTING_STARTED_JA.md) を参照してください。以降の `prism` は `python cli.py` と読み替えられます。

このチュートリアルを通す考え方は一つです。**署名は契約書であり、静的チェックは本体が契約を守ることを確かめます。** 各ステップでプログラムを少し壊してから `prism check` を実行してみてください。行番号つきのエラーそのものが学びになります。

---

## 1. Hello — プログラムは契約から始まる

[`tutorial/01-hello.prism`](tutorial/01-hello.prism)

```prism
main : () !console  <-
  show!console "hello, Prism"
```

`main : () !console` は「`()`（何も返さない）を返し、**コンソールに触れる**」と読みます。`<-` から本体が始まります。ここで使う副作用は `show!console` の一つだけで、署名中の `!console` がそれを宣言しています。

```sh
$ prism run tutorial/01-hello.prism
hello, Prism
```

**試してみる:** 署名から `!console` を消して `prism check` を実行します。静的チェックが、宣言した行の位置で未宣言の副作用を指摘します。この拒否こそが主題です。

## 2. 値 — 導出には順序がない

[`tutorial/02-values.prism`](tutorial/02-values.prism)

```prism
fahrenheit : Num  <-  celsius * 9 / 5 + 32
celsius    : Num  <-  30
```

`<-` は、ほかの値から値を導きます。**行の順番には意味がありません。** `fahrenheit` は使っている `celsius` より上に書かれていますが問題ありません。上から下への手順ではなく、依存関係で考えることになります。（`"... {celsius} ..."` は文字列補間です。`{expr}` の位置に値を埋め込みます。）

```sh
$ prism run tutorial/02-values.prism
celsius 30 = fahrenheit 86
```

## 3. 失敗 — エラーは扱う必要がある値

[`tutorial/03-failure.prism`](tutorial/03-failure.prism)

```prism
divide(a: Num, b: Num) : Num ?DivByZero  <-
  b match
    0  =>  fail DivByZero
    _  =>  ok (a / b)
```

署名の `?DivByZero` は「この関数は `DivByZero` で失敗しうる」という意味です。結果は `ok` / `fail` で作り、最後には必ず**扱う**必要があります。方法は二つです。`try` は失敗を呼び出し元へ伝播し、`attempt`/`rescue` は受け止めます。

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

**試してみる:** `divide` の署名から `?DivByZero` を消し、`prism check` を実行します。失敗が契約の外へ漏れたことを、静的チェックが指摘します。

## 4. 型 — `or` 型を網羅して扱う

[`tutorial/04-types.prism`](tutorial/04-types.prism)

```prism
Shape : Circle{ radius: Num }  or  Square{ side: Num }

area(s: Shape) : Num  <-
  s match
    Circle{radius}  =>  radius * radius * 3
    Square{side}    =>  side * side
```

`or` 型は選択肢を列挙します。その型に対する `match` は**すべての**バリアントを扱わなければなりません。これは「レコードを作るなら、すべてのフィールドを与える」の双対です。

```sh
$ prism run tutorial/04-types.prism
circle r=2 -> 12
square s=3 -> 9
```

**試してみる:** `Square` の分岐を消して `prism check` を実行します。どの行で、どのバリアントが不足しているかを正確に知らせてくれます。

## 5. ジェネリクス — 一つの関数で、すべての形を扱う

[`tutorial/05-generics.prism`](tutorial/05-generics.prism)

```prism
map for T, U, !e, ?g
  (xs: List[T], f: (T) -> U !e ?g) : List[U] !e ?g  <-
    xs match
      []        =>  []
      [h, ..t]  =>  [ try f(h), ..try map(t, f) ]
```

ジェネリクスは**次元に空けた穴**です。ここには4つあります。型の穴 `T`/`U`、副作用の穴 `!e`、失敗の穴 `?g` です。署名は「`map` の副作用と失敗は、渡された `f` とまったく同じであり、余計なものを加えない」と読めます。だから一つの `map` が純粋・副作用つき・失敗しうる処理をすべて扱えます。`mapM` も `tryMap` も要りません。

```sh
$ prism run tutorial/05-generics.prism
doubled = [2, 4, 6]
```

## 6. Capability — 解決され、ディスパッチされるメソッド

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

**capability** は、型が提供できるメソッドの組です。`Num` と `Text` はそれぞれ `Show` を `provide` します。`render` を呼ぶ関数は `given T: Show` と要求を宣言します。`render(x)` の呼び出しは capability に解決され、受け取り側の型がそれを提供するかを確認し、実行時には**値の型でディスパッチ**します。

```sh
$ prism run tutorial/06-capabilities.prism
a number
hello
```

**試してみる:** `Bool provides Show` を追加し、`render(x) <- x` と書いて `prism check` を実行します。本体は `Text` ではなく `Bool` を返すため、静的チェックがこのインスタンスを拒否します。契約はメソッド本体の奥まで届きます。

---

## 次に読むもの

- **[REFERENCE.md](REFERENCE.md)** — すべての機能、文法、エラーカタログ（英語）。
- **`examples/`** — 動く式評価器（`calc.prism`）、信号機ステートマシン、高階型 `Functor`、時間の声 `~>` を含む19本の詳しいプログラム。
- `prism reveal <file>` — **署名なし**の関数を書き、Prism に推論した契約を見せてもらえます。
