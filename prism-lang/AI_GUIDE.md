# AI_GUIDE — LLM に Prism を書かせるための最小ガイド

このファイルは **LLM のコンテキストに丸ごと貼る**ことを想定した、Prism を書かせるための最小仕様・例・
禁止事項・進め方です。Prism は新しい言語なので、AI は学習データを持ちません。**このページ＋例を数本**を
渡せば、署名先行で正しく書かせられます。完全仕様は [REFERENCE.md](REFERENCE.md)。

---

## 1. Prism とは（30秒）

- ビルド/コンパイル不要のツリーウォーク型インタプリタ（`prism.py`）＋別建ての静的検査器（`check.py`）。
- 関数の**署名が契約**で、検査器がそれを強制する。計算は4つの「声」に分かれ、**混ぜない**:

| 声 | 意味 | 記号 |
|---|---|---|
| 事実 | 型・データ | `:`、`and`（レコード）、`or`（バリアント） |
| 変換 | 依存（**行順は無意味**） | `<-`、match の腕は `=>` |
| 作用 | 副作用 | `!console`（純粋＝`!` が無い） |
| 失敗 | エラー（= ok/fail の or 型を flow に持ち上げたもの） | `?Error`、`try`、`match`/`rescue` |
| 時間（上級） | 順序付け | `~>` |

## 2. 検査器が強制する「掟」（これを破ると落ちる）

1. **作用は宣言せよ。** 本体が `!console` するなら署名に `!console` が要る。
2. **失敗は処理せよ。** 可謬な値は `try`（伝播）か `match`/`rescue`（消費）で扱う。さもなくば署名に `?E` を宣言。
3. **match は網羅せよ。** `or` 型は全ヴァリアント、List は `[]` と `[h, ..t]`、可謬値は `ok`/`fail`、Num/Text は `_` 必須。
4. **制約は成就せよ。** `given T: Cap` で呼ぶ型は `provides Cap` を持つこと。

## 3. 構文チートシート

```prism
-- コメントは -- 。値の束縛・関数定義（名前は小文字始まり。大文字始まりはコンストラクタ/タグ）
x       <-  42
add(a, b)  <-  a + b

-- 型（fact）: and = レコード, or = バリアント。コンストラクタは大文字 Tag{...}
Account : { name: Text and balance: Num }
Shape   : Circle{ radius: Num } or Square{ side: Num }

-- 署名 = 型 + 作用 + 失敗
greet(name: Text) : ()  !console  <-  show!console "hi {name}"
divide(a: Num, b: Num) : Num ?DivByZero  <-
  b match
    0  =>  fail DivByZero
    _  =>  ok (a / b)

-- 失敗の扱い: try で伝播、attempt/rescue で消費
main : () !console  <-
  attempt
    q  <-  try divide(10, 2)
    show!console "answer: {q}"
  rescue
    DivByZero  =>  show!console "cannot divide by zero"

-- match（網羅必須）、リスト（[]・[h, ..t]）、文字列補間 "{expr}"
area(s: Shape) : Num  <-
  s match
    Circle{radius}  =>  radius * radius * 3
    Square{side}    =>  side * side

-- 条件は inline if（1行）または Bool の match
sign(n: Num) : Num  <-  if n < 0 then 0 - 1 else 1

-- ジェネリクス: for 句で穴を空ける（型 T / 関数 (T)->U / 作用 !e / 失敗 ?g / 容器 F[_]）
map for T, U, !e, ?g (xs: List[T], f: (T) -> U !e ?g) : List[U] !e ?g  <-
  xs match
    []        =>  []
    [h, ..t]  =>  [ try f(h), ..try map(t, f) ]
```

数学組み込み: `sin cos sqrt abs floor` : `(Num)->Num`、定数 `pi`。`parseNum(Text) : Num ?BadNumber`。
ファイル取り込み: `include "lib/foo.prism"`（グローバル併合・名前空間なし）。
小さな標準ライブラリ（include して使う）: `lib/math.prism`（minN/maxN/clamp/sign/lerp/frac/mod）,
`lib/list.prism`（length/concat/concatAll/reverse/map/filter/foldl/times/range）。
使用例＝[`examples/lib-check.prism`](examples/lib-check.prism)。Option/Result は無い（失敗の声 `?` が担う）。

## 4. 禁止事項・落とし穴（生成でよく外す所）

- **値の束縛は必ず小文字始まり。** `MAX <- 28` は不可 —— 大文字始まりは**コンストラクタ/タグ**扱いになり、
  `MAX` は値ではなく nullary タグとして解釈される。`maxIter <- 28` と書く。
- 文字列リテラル内の `--` は**OK**（`"a -- b"` で全部出る。以前は途中で切れたが修正済み）。
- **リストのスプレッドは末尾に1つだけ。** `[h, ..t]` は可、`[..a, ..b]`（二重）は不可 —— 連結は再帰 `concat` で。
- **`if ... then ... else ...` は1行（インライン）のみ。** 複数行の分岐は `match` を使う。
- **`~>`（時間）の各手順は作用か失敗を持つこと。** 純粋な式を `~>` で並べると型エラー（`<-` を使う）。
- **`include` は実行時 CWD 相対。** プロジェクトルートから実行する前提で書く。
- **`?` は失敗専用。** `?Error` / `?{E1,E2}` / `?g`（失敗の行）だけ。**型ではない。** 未知の型（注釈の無い所・推論結果）は **`_`** で表す（`reveal` も `_` を表示。`f(x: _) : _` のように明示も可）。
- Result / Option を別に作らない —— **失敗の声 `?Error`（`ok`/`fail`）がそれに当たる**。

## 5. 進め方 —— 人間=署名 / AI=本体 / 検査器=審判

Prism の使い方の核心はこのループです（エージェント・ループ）:

```
人間  →  署名（契約）を書く        例:  divide(a: Num, b: Num) : Num ?DivByZero  <-
AI    →  本体（<- の右）を書く
ツール →  prism check で照合し、行番号つきエラーを返す
AI    →  エラーを読んで本体を直す（contract は変えない）
... OK になるまで回す
```

### 実演（このまま AI に渡せるシナリオ）

**人間が署名だけ与える:**
```prism
-- 与えられた契約。本体だけ書いて。
clamp(x: Num, lo: Num, hi: Num) : Num  <-  ???
```

**AI の最初の試み（よくある間違い: 複数行 if）:**
```prism
clamp(x: Num, lo: Num, hi: Num) : Num  <-
  if x < lo
    then lo
    else if x > hi then hi else x
```
**`prism check` →**
```
[parse error] line 2: expected 'then', got NEWLINE:None
```
（`if` は1行のインライン式。改行して書けないので落ちる。複数行に分けたいなら `match` を使う。）
**AI の修正（インライン if にする）:**
```prism
clamp(x: Num, lo: Num, hi: Num) : Num  <-
  if x < lo then lo else if x > hi then hi else x
```
**`prism check` → `OK`。** 契約（署名）は一度も変えず、本体だけを検査器の指摘で直した。

もう一例 —— **作用の宣言漏れ**:
```prism
shout(msg: Text) : ()  <-  show!console msg     -- 署名は純粋だが本体は !console
```
```
line 1: shout: performs effect !console but its signature declares no effects (pure)
```
直し方は2つ:(a) 契約を正直にする `… : () !console`、(b) 本体から副作用を除く。**どちらにするかは人間が決める** ——
これが「契約を読んでレビュー範囲を絞る」の実体。

> 現実的な射程:Prism は実用言語ではないので「AIと実アプリ開発」ではなく、**小さく契約の濃いプログラムを
> AIと作り、署名先行＋ check ループの流儀を体験・訓練し、その方法論を実務の言語に持ち帰る**使い方が中心。

## 6. 渡すと良い例（コンテキストに添付）

- `examples/divide.prism`（4声そろい・対話入力）、`examples/calc.prism`（or型+網羅+失敗の式評価器）
- `examples/rpn.prism`（**この流儀で実際に作った RPN 電卓** ── 人間が5つの失敗を含む契約を書き、AI が
  本体を書き、検査器が審判。`rescue` の一句を AI が忘れると検査器が `main` の失敗漏れとして弾く。
  この実演中に検査器の実バグ（effect 引数の失敗が追跡漏れ）まで露見・修正された ── [NOTES](NOTES.md) 所見#25）
- `examples/rps.prism`（**多重ディスパッチの実演** ── じゃんけん。勝敗を `Beats for A, B` の9インスタンスで
  決める。インスタンスが2つの型を名指さないと検査器が arity で弾く。同じく AI協働で作った例）
- `examples/vending.prism`（**時間の声 `~>` ＋ 状態機械の実演** ── 自販機。投入額を再帰で持ち回り、
  `表示 ~> 読む ~> 処理` で順序付け。AI協働で作り、文字列内 `--` のレキサバグを露見させた例 ── NOTES 所見#26）
- `examples/guess.prism`（**対話ループ＋勝敗の実演** ── 数当てゲーム。試行回数を再帰で持ち回り、非数字入力は
  その場で `parseNum` の失敗を握って再プロンプト。AI協働で作った例）
- `examples/leaderboard.prism`（**レコード＋ジェネリクス＋ `given T: Ord` の実演** ── スコア順ランキング。
  `Player` レコードの `.field` でソート、`given T: Ord` を呼び出しで discharge。AI協働で作った例）
- `examples/broken.prism` / `examples/mistyped.prism`（**わざと落ちる**例 → 検査器が何を嫌うか分かる）
- `examples/shapes.prism`（網羅 match）、`examples/capable.prism`（capability/given）

これらと本ページを渡し、**署名を先に固定 → 本体生成 → `prism check` の出力をそのまま返す**、を回してください。
