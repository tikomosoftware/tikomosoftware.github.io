# Prism 言語リファレンス（v0）

これは `prism.py`（インタプリタ）と `check.py`（静的チェッカー）が実装する Prism v0 の完全リファレンスです。考え方は [README.md](README.md)、手を動かす導線は [TUTORIAL_JA.md](TUTORIAL_JA.md) を参照してください。

Prism に**ビルド工程はありません**。プログラムは `.prism` のテキストファイルであり、`run`（実行）または `check`（静的チェック）、あるいは両方を行います。チェッカーは任意かつ別建てなので、静的チェックしていないコードも実行できます。

---

## 1. 字句構造

- **コメント** は `--` から行末までです。
- **数値**: `42`、`3.14`（整数または小数）。
- **テキスト**: `"..."`。`\` によるエスケープと `{expr}` 補間が使えます（§10）。
- **真偽値**: `true`、`false`。
- **識別子**: `[A-Za-z_][A-Za-z0-9_]*`。
  - **小文字始まり** → 変数・関数・メソッド名（`divide`、`xs`）。
  - **大文字始まり** → コンストラクタ・バリアント・capability・型名（`Circle`、`DivByZero`、`Ord`）。
- **レイアウト**: ブロックは Python と同様に**インデント**で決まります。深いインデントがブロックを開き、戻すと閉じます。`(` `)` `[` `]` `{` `}` の内側では改行とインデントを無視するため、式は括弧内で自由に改行できます。

## 2. 4つの声（概観）

すべての計算は4つの問いに答えます。Prism は各次元に専用の記号を与え、混ぜません。

| 声 | 問い | 記号 |
|---|---|---|
| **事実（fact）** | それは何か（型／データ） | `:` `and` `or` |
| **変換（flow）** | 何から導かれるか | `<-` `=>` |
| **作用（effect）** | 世界の何を変えるか | `!world` |
| **失敗（failure）** | どう失敗しうるか | `?Error` `try` `match` |
| （**時間（time）**） | どの順番で起きるか | `~>` |

関数の署名はこれらをすべて書く、嘘のつけない契約です。

```prism
f(x: A) : B  !world  ?Error  <-  body
--      ^型    ^作用    ^失敗     ^導出
```

## 3. 定義

プログラムは定義の列です。**定義の順番に意味はありません**。導出は行順ではなく `<-` 矢印で決まり、インタプリタは遅延 thunk を使います。実行するプログラムには `main` の定義が必要です。

トップレベルの `include "path"` は、別ファイルの定義を**同じグローバル空間**へ併合します。名前空間を持たないのは、順序に依存しないグローバル定義と整合するためです。パスは現在の作業ディレクトリから解決されるため、**プロジェクトルートで実行**してください。循環 include と二重 include は無視されます。ファイル相対の解決は、ファイルパスを持たない文字列から実行するブラウザ版と CLI の挙動を一致させるため、v0 では採用していません。

```prism
include "lib/physics2d.prism"
```

> **名前空間はないが、衝突は検出します。** `include` は一つの平坦なグローバル空間へ併合するため、同名のトップレベル定義は衝突します。片方がもう片方を黙って隠すのではなく、静的チェッカーが重複名を拒否します（[`examples/collision.prism`](examples/collision.prism)）。ライブラリが提供する名前を再定義せず、領域固有のヘルパーには接頭辞を付けてください。本格的な修飾名つきモジュール／名前空間は v0 の対象外です。

```prism
celsius    : Num  <-  30
fahrenheit : Num  <-  celsius * 9 / 5 + 32     -- `celsius` より前に書いてよい
```

定義には3つの形があります。

```prism
greet(name: Text) : () !console  <-  show!console "hi {name}"   -- 署名つき関数
answer : Num  <-  42                                            -- 署名つき値
double(n)  <-  n * 2                                            -- 署名なし（推論／漸進的）
```

名前と `<-` の間にある署名は任意です。省略時は漸進的にチェックされ（§11）、`reveal` で契約を推論できます（§14）。

### 本体とブロック

本体は `<-` の後の1行式、または次行からのインデントブロックです。ブロック内の `name <- expr` は**ローカル束縛**、それ以外の行は文であり、ブロックの値は最後の式になります。

```prism
area(r: Num) : Num  <-
  pi   <-  3
  pi * r * r
```

## 4. 事実: 型（`:`）

型注釈は `:` で始めます。組み込み型は `Num`、`Text`、`Bool`、`()`（Unit）、`List[T]`。型適用には角括弧を使います: `List[Num]`、`F[A, B]`。

関数型は `(A, B) -> C !e ?g` です。

### レコード — `and` 型

積（すべてのフィールドを持つ）は `and` で書きます。

```prism
Account : { name: Text  and  balance: Num }
```

レコード値にはコンストラクタ構文を使い、フィールドは `.` で読みます。

```prism
acc  <-  Account{ name: "Ada", balance: 100 }
acc.balance
```

フィールドの**宣言型は `.` を通じて伝播**します。値の型が既知のレコードなら（型注釈された `b: Box`、`Box{…}` のようなコンストラクタ、`p.bbox` の連鎖など）、`b.w` は `Box` に宣言された `w` の型になり、不一致は後段で検出されます（[`examples/mistyped-field.prism`](examples/mistyped-field.prism)）。

**レコードは開いています。** 未宣言フィールド、型が分からない値のフィールド、またはバリアントが曖昧な複数バリアント `or` 型のフィールドは、漸進的な `_` のままです。そのため図形に追加の色相 `h` を持たせられます。`match` の束縛（`Circle{radius} => …`）からフィールドを読む方法もあります。

**構築は完全でなければなりません。** 宣言済みレコードを、宣言されたフィールドの一部なしで構築するとエラーです。たとえば `Point` が `Pt{ x, y }` と宣言している場合、`Pt{ x: 3 }` は拒否されます（[`examples/incomplete-record.prism`](examples/incomplete-record.prism)）。これは `and` の「すべてのフィールドを持つ」の裏返しです。追加フィールドは許され、未宣言コンストラクタ（例: `Cell{u, v}`）には必須フィールドはありません。

### バリアント — `or` 型（和型）

和（複数のうち一つ）は `or` で書き、複数行にまたがれます。

```prism
Shape : Circle{ radius: Num }
     or Square{ side: Num }
     or Triangle{ base: Num, height: Num }
```

各 `Tag{...}` はコンストラクタです。大文字名だけの `DivByZero` は引数なしコンストラクタです。`Circle{...}` で作った値の型は、所属する和型 `Shape` です。

> **学びのポイント:** `and` 型は「すべてのフィールドを与える」ことを求め、その双対である `or` 型は「すべてのバリアントを扱う」ことを求めます（網羅性は§7）。

## 5. 作用: `!world`

作用は世界の変更を表します。v0 に実装された世界は `console` だけです。

```prism
show!console expr        -- stdout に1行書き、() を返す
read!console             -- stdin から1行読み、Text を返す
```

署名中の `!world` は関数が行う作用を宣言します。**純粋性は `!` が無いことです。** 作用は**伝播**します。`f` が `!console` の `g` を呼ぶなら、`f` も `!console` であり、署名にその宣言が必要です。

**粒度:** 粗い作用は細かい作用を包含します。`!io` は包括作用であり、関数は `!io` と宣言して `!console`（将来用に予約された `!file`／`!net`／`!random`／`!time` も）を実行できます。これは**一方向**です。`!io` の署名は `!console` 本体を覆えますが、`!console` の署名は `!io` 本体を覆えません。粗い作用が無宣言で漏れるためです（[`examples/effect-narrow.prism`](examples/effect-narrow.prism)）。v0 で実在する作用は `console` だけなので、`!io` は将来への備えです。

```prism
greetAll(names: List[Text]) : () !console  <-
  map(names, n -> show!console "hi {n}")
  ()
```

作用はラベル集合である**行（row）**として蓄積します。作用は追跡されますが、値自体は変えません。値を変える失敗（§6）と対照的です。

## 6. 失敗: `?Error`

> エラーは特別なものではありません。「成功 **または** 失敗」という `or` 型を flow に持ち上げたものです。`: Num ?DivByZero` は「`Num`、または `DivByZero`」を意味します。
>
> `?` は**失敗**の声であり、型ではありません。漸進的な Unknown 型は `_` と書きます（§11）。

結果を作るには次を使います。

```prism
ok expr        -- expr を運ぶ成功
fail Tag       -- エラー Tag を運ぶ失敗
```

結果を消費する方法は、正確に二つです。

```prism
try expr       -- 伝播: expr が失敗なら、呼び出し元の ? 行へ失敗を上げる
               -- （強く結合する。try f(x) は try (f(x)) であり、try (f(x) + ...) ではない）
```

```prism
expr match               -- match で処理: 失敗を消費し、型から ? を取り除く
  ok v   =>  ...
  fail e =>  ...
```

```prism
attempt                  -- attempt/rescue で処理: ブロックを実行し、宣言済み失敗を捕捉
  a  <-  try askNumber("x?")
  show!console "got {a}"
rescue
  BadNumber  =>  show!console "not a number"
```

失敗しうる値を、処理せずに通常値が必要な場所（演算項・引数・リスト要素・`"{...}"` の中）で使うと、**未処理の失敗**エラーになります。失敗も `?{BadNumber, DivByZero}` のような行として蓄積します。

`rescue` は意図的に部分的です。処理しない失敗は外へ伝播し、外側の関数で宣言されなければなりません。

## 7. パターンマッチと網羅性

`scrutinee match` の後に、インデントした `pattern => body` 分岐を書きます。

```prism
classify(n: Num) : Text  <-
  n match
    0  =>  "zero"
    _  =>  "nonzero"
```

パターンには数値／テキストリテラル、`true`／`false`（`Bool` は2バリアントの `or` 型）、`_`（ワイルドカード）、小文字名（束縛）、`Tag{field: pat, ...}` または裸の `Tag`、`ok pat`、`fail pat`、リスト `[a, b]`／`[head, ..tail]` があります。計算した条件による分岐は `true`／`false` のマッチで書けます。

```prism
max(a: Num, b: Num) : Num  <-
  (a < b) match
    true   =>  b
    false  =>  a
```

よくあるケースには **`if cond then a else b`** もあります。これは上の Bool マッチへ脱糖される式です。両方の分岐が必要で、`else if` は自然に連鎖できます。

```prism
sign(n: Num) : Text  <-  if n < 0 then "neg" else if n == 0 then "zero" else "pos"
```

`match` は**網羅的**でなければなりません。ワイルドカード `_` または裸の変数パターンはすべてを覆います。それ以外では、静的チェッカーが次を要求します。

| 対象値 | 網羅的となる条件 |
|---|---|
| `or` 型 | すべてのバリアントを覆う（存在しないバリアント名の分岐もエラー） |
| `List[T]` | `[]` と `[h, ..t]` の両方、または単一の `[..t]` を覆う |
| 失敗しうる値 | `ok` と `fail` の両パターンがある |
| `Bool` | `true` と `false` の両方、または `_` がある |
| `Num`／`Text` | 無限に取りうるため、全体を受ける `_` がある |
| 注釈なし（`_`） | 常に寛容（漸進的） |

## 8. 時間: `~>`

`<-` による導出に**順序はありません**（遅延評価です）。順序が意味を持つなら時間の次元に入り、`~>` を使います。

```prism
greet(name: Text) : () !console  <-
  show!console "hello, {name}"  ~>  show!console "welcome"  ~>  show!console "bye"
```

規則: **`~>` が順序づける各ステップは時間に触れなければなりません。** つまり作用（`!`）または失敗（`?`）を持つ必要があります。純粋なステップを連結すると「純粋な導出に順序はない。`<-` を使え」というエラーになります。失敗したステップは列を中断し、失敗は伝播します。v0 の `~>` は単一行演算子で、すべての演算子より弱く結合します。

## 9. ジェネリクス — 次元に空けた穴

ジェネリクスは各次元の*穴*であり、`for` 節で宣言します。穴には次元の記号が付きます。

| 穴 | 形 | 意味 |
|---|---|---|
| 型 | `T` | 型変数 |
| flow | `(T) -> U` | 関数（高階） |
| 作用 | `!e` | 作用行変数 |
| 失敗 | `?g` | 失敗行変数 |
| **コンテナ** | `F[_]`（または `F[_, _]`） | 高階型コンストラクタ変数 |

一つの多相的な `map` で、純粋・作用つき・失敗しうる使用をすべて覆えます。

```prism
map for T, U, !e, ?g
  (xs: List[T], f: (T) -> U !e ?g) : List[U] !e ?g  <-
    xs match
      []        =>  []
      [h, ..t]  =>  [ try f(h), ..try map(t, f) ]
```

行変数（`!e`、`?g`）は呼び出し地点ごとに引数から具体化され、結果へ流れます。展開 `..` は全次元で共通です。リストは `[h, ..t]`、作用行は `!{console, ..e}`、失敗行は `?{BadNumber, ..g}` と書けます。

### 高階型 `F[_]`

`F[_]` は、値に対する `(T) -> U` と同じく、矢印そのものが穴になった型です。`F` はコンテナの形を表し、`F[T]` はそれを適用します。単一化は `F[T]` と `List[Num]` から `F := List`、`T := Num` を得て、`F[U]` を `List[U]` に再構築します。

```prism
keep for F[_], T (xs: F[T]) : F[T]  <-  xs
nums(xs: List[Num]) : List[Num]  <-  keep(xs)
```

## 10. 文字列補間

`"..."` の中の `{expr}` は `expr` を評価し、そのテキストを埋め込みます。補間は**波括弧の深さを理解する**ため、`"{area(Circle{radius: 2})}"` のようなレコードも入れ子にできます。補間された式は本物のコードです。作用は伝播し、失敗は処理しなければならず、文字列の中に隠れることはありません。

## 11. 漸進的型付け（`_` の境界）

**漸進的な Unknown 型**は `_` で書きます。ワイルドカードパターンと同じ「気にしない／ここを埋める」字形です。これは弱いチェックではなく、漸進的型付けの境界です。型注釈のない場所（署名なし関数、ラムダ引数）では何とでも互換になり、`reveal` は `_` と表示します。`f(x: _) : _` のように明示もできます。ただし、食い違う二つの**既知**型は必ずエラーです。注釈なしは「まだ契約していない」を意味します。

> **一つの字形、一つの声。** `?` は**失敗**の声だけに属し（`?Error`、`?{E1, E2}`、`?g`）、型になることはありません。Unknown **型**は事実の声の `_` を使います。次元ごとに記号を分けることが Prism の規律であり、Unknown 型は失敗の記号を借りません。

## 12. 演算子と優先順位

弱いものから強いものへの順です。

| 水準 | 演算子 | 注記 |
|---|---|---|
| 最弱 | `~>` | 時間の列（単一行・右結合） |
| | `\|>` | パイプ（flow の糖衣・左結合） |
| | `match` | 直前の式に後置 |
| | `==` `!=` `<` `>` `<=` `>=` | 比較 → `Bool` |
| | `+` `-` | `+`: `Num+Num→Num` または `Text+Text→Text`（混在不可）、`-`: Num |
| 最強 | `*` `/` | Num |

**パイプ `|>`** は、内から外ではなく左から右へ読める純粋な flow の糖衣です。`x |> f` は `f(x)`、`x |> f(a)` は `f(x, a)` に脱糖されます。パイプされる値は**第1引数**になります（Prism のライブラリは `clamp`、`nth`、`at`、`length` などデータ先頭です）。左結合であり、`x |> f |> g` は `g(f(x))`。通常の呼び出しになるだけなので、型・作用・失敗は展開して書いた呼び出しと同じように流れます。右辺は関数名か呼び出し（`f(a)`）です。より複雑ならラムダへパイプします: `x |> (v -> f(v) + 1)`。時間の声 `~>` は意図的にパイプと兼用しません。値の受け渡しと、作用または失敗に触れる順序づけを混ぜないためです。

単項マイナス `-x` は `0 - x` として解析されます。`try`、`ok`、`fail` は直後の**後置**式に強く結合します（`try f(x)`）。より広い式は `try (a + b)` のように括弧で囲んでください。作用の引数も強く結合し、`show!console a + b` は1行内でのみ `show!console (a + b)` になります。`~>` をまたぐことはありません。

暗黙の型変換はありません。`1 + "x"` は静的チェッカーとランタイムの両方に拒否されます。テキストは `"{n}x"` のような補間で作ります。

## 13. Capability と制約

**capability** は、型が提供できるメソッドの名前つき集合です（trait / typeclass）。

```prism
capability Ord for T
  compare(a: T, b: T) : Num
```

**インスタンス** は具体的な型に capability を提供し、すべてのメソッドを実装します。

```prism
Num provides Ord
  compare(a, b)  <-  a - b
```

関数は `given` で capability を**要求**します。

```prism
larger for T given T: Ord (a: T, b: T) : T  <-  a
```

静的チェッカーは次の4点を保証します。

1. **解決（discharge）** — 呼び出し地点で `given T: Cap` は、具体的な `T` が `provide Cap` することを要求します。呼び出し側が同じ `given` を再宣言して伝播することもできます。失敗処理と対応します。
2. **完全性** — `provides` は capability のメソッドを過不足なく定義しなければなりません。`and` のフィールド／マッチの網羅性と対応します。
3. **整合性（coherence）** — （型の組、capability）ごとにインスタンスは高々一つです。重複は拒否されます。
4. **メソッド本体** — 各インスタンスメソッドは、capability の型変数をインスタンス型へ束縛した宣言署名（返り値型・作用・失敗）に対してチェックされます。

capability メソッド呼び出し（`compare(a, b)`、`fmap(xs, f)`）は capability へ解決され、受け取り側の型がそれを提供することを要求し、宣言された返り値型を返します。実行時には、capability の型変数 `T`／`F[_]` の位置にある**値の実行時型でディスパッチ**します。

### 多重ディスパッチ

capability は**複数の型変数**（`for A, B`）にまたがれます。その場合インスタンスは型の**組**（`A provides Cap for B`）を指定し、メソッドは複数引数の実行時型で同時に選ばれます。一つの「所有者」ではなく両方のオペランドで結果が決まるケースです。インスタンスがない組み合わせは呼び出し地点で拒否されます。[`examples/collide.prism`](examples/collide.prism) を参照してください。

```prism
capability Collide for A, B
  hit(a: A, b: B) : Text

Ship provides Collide for Asteroid               -- (A := Ship, B := Asteroid)
  hit(a, b)  <-  "ship grazes the asteroid"
Bullet provides Collide for Asteroid             -- 別の組 -> 別の `hit`
  hit(a, b)  <-  "bullet shatters the asteroid"

hit(Ship{}, Asteroid{})                          -- (Ship, Asteroid) のインスタンスを選ぶ
```

単一ディスパッチは、型変数が一つのケース（`for T` → 要素一つの組）です。両者は同じ仕組みを共有します。

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

## 14. ツール: check と reveal

- `prism check <file>` はすべての違反を、それぞれ**ソース行**（`line N: ...`）つきで報告します。問題がなければ `OK` と表示します。
- `prism reveal <file>` は各定義の完全な契約を表示します。署名のある定義は宣言契約 `[declared]`、署名のない定義は本体から**推論した**契約 `[inferred]` を表示します。これは「ツールが顕わにする」側です。

```sh
$ prism reveal examples/infer.prism
  ask : Num !{console} ?{BadNumber}      [inferred]
  greet(name) : Unit !{console}          [inferred]
```

## 15. 組み込み

| 名前 | 契約 |
|---|---|
| `parseNum` | `(Text) -> Num ?BadNumber` |
| `show!console` | `(_) -> () !console`（1行書く） |
| `read!console` | `() -> Text !console`（1行読む） |
| `sin` `cos` `sqrt` `abs` `floor` | `(Num) -> Num`（数学） |
| `pi` | `Num`（定数 π） |
| `at` | `(List, Num) -> _` — **O(1)** の添字読み出し（0始まり）。リストは不変で、これは読むだけです。範囲内であることは呼び出し側の契約です（範囲外は負の値への `sqrt` と同じくハードエラー）。 |
| `len` | `(List) -> Num` — **O(1)** の長さ。 |
| `words` | `(Text) -> List` — Text を空白で単語テキストのリストへ分割（空要素は捨てる）。 |

> `at`／`len` は高速なプリミティブです。[`lib/list`](lib/list.prism) の `nth`／`length` は教材用に残した O(n) の構造再帰版です。グリッドやシミュレーションの近傍探索では `at` を使ってください。O(n) のアクセスでは O(n) の走査が O(n²) になってしまいます。

## 描画とアニメーション（キャンバス契約）

Prism という**言語**自体はグラフィクスを知りません。絵は純粋な**値**で、描画はツールの仕事です。これは `check`／`reveal` と同じ姿勢です。ブラウザの遊び場は次の二つの値の形を認識します。

- **静止画（Layer A）**: 絶対座標の図形リスト、`picture : List[Shape]` を定義して **Draw** を押します。キャンバスが知る語彙は次だけです。

  | 図形 | フィールド |
  |---|---|
  | `Line` | `x1, y1, x2, y2` |
  | `Dot` | `x, y` |
  | `Circle` | `x, y, r` |
  | `Rect` | `x, y, w, h` |
  | `Poly` | `pts`（`Pt{x, y}` の `List`）— 折れ線／多角形 |

  どの図形にも任意の追加フィールドを持たせられます（レコードが開いているためです）。**`h`** は色相0〜360（無指定なら描画順の虹色）、**`a`** は不透明度0〜1（半透明の塊／発光／霧）、**`fill`** は `Circle`／`Poly` を線ではなく塗りつぶしにします。

- **アニメーション**: **純粋**関数 `frame(t) : Picture`（または `: List[Shape]`）を定義し、**Animate** を押します。ホストが秒単位で `t` を進め、各 tick で `frame(t)` を描画します。シーン全体は可変状態を持たない*時間の関数*です。`frame` の署名に `!` がないため、静的チェッカーはアニメーションの純粋性を保証します。`show!console` を隠した `frame` は「作用 `!console` を実行するが、署名に作用がない」として拒否されます。滑らかなループには `t ∈ [0, 2π]` で周期的な `frame` を書きます。[`physics/pendulum-anim.prism`](physics/pendulum-anim.prism) を参照してください。

合成可能な **Picture 代数**（`over`／`beside`／`above`／`scale`／`rotate`／`render`）は純粋ライブラリ [`lib/picture.prism`](lib/picture.prism) にあります。`render` は `Picture` をキャンバスが描く `List[Shape]` へ戻します。`rotate` が `Rect` を4隅の `Poly` にするのは、傾いた長方形が軸に平行ではなくなるためです。

**リンクを共有する:** 遊び場の **🔗 Share** は現在のコードをサーバーなしでページURLの `#code=…` フラグメントに符号化します。そのリンクを開くと、エディタはそのプログラムを直接読み込みます。読み込み優先順位は共有 `#code=`、自動保存コード、既定コードの順です。

## 16. 文法（非形式的）

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

## 17. エラーカタログ（静的チェッカーが報告するもの）

すべてのエラーには `line N:` が付きます。

- **type mismatch** — 返り値と宣言型、引数とパラメータ、リスト要素、match 分岐の型が不一致。算術には `Num` が必要で、`+` は `Text` と `Num` を混ぜられません。
- **incomplete record** — 宣言済みレコードを全フィールドなしで構築した（`Pt{ x: 3 }`）。
- **duplicate definition** — `include` による平坦な併合後、二つのトップレベル名が衝突した。
- **unhandled failure** — 失敗しうる値を `try` または `match` なしで使用した（演算項／引数／リスト要素／補間）。
- **effect leak** — 関数が、署名にない作用を実行した。
- **failure leak** — 関数が、署名にない `?` で失敗しうる。
- **non-exhaustive match** — バリアント／リストケース／`ok` または `fail`／全体を受ける分岐が不足。存在しないバリアント名の分岐も含みます。
- **pure step in `~>`** — 作用にも失敗にも触れないステップを順序づけた。
- **capability** — 満たされない `given`、不完全または重複するインスタンス、宣言署名に違反するインスタンスメソッド本体。

## 18. コマンドラインリファレンス

```sh
prism run    <file.prism>     # 実行（別名: python prism.py <file>）
prism check  <file.prism>     # 静的チェック（別名: python check.py <file>）
prism reveal <file.prism>     # 契約を推論・表示（別名: python check.py --reveal <file>）
prism test                    # 回帰テスト（別名: python test.py）
prism help
```

`prism` は同梱ランチャです。どこでも `python cli.py` に置き換えられます。
