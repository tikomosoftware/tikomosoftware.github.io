# Prism — 関数型グラフィクス言語への発展計画 (GRAPHICS_PLAN)

> 目的: Prism を「四声のペダゴジー」を魂に残したまま、**関数型・宣言的グラフィクスの旗艦**へ育てる。
> 方針: 言語コアは原則いじらない。発展は **(1) 描画コントラクトの明文化 → (2) Prism で書く標準ライブラリ → (3) 描画器/playground** の順。
> 基準線: 何を変えても `python cli.py test` が緑（現 310 passed）であること。各フェーズは単独で出荷可能。

---

## 0. 結論（最初に読む）

- **言語コアの練り直しはほぼ不要。** `over`/`beside`/`above`/`rotate`/`frame(t)` は全部「ただの Prism コード」。HANDOFF の「設計は CLOSED、ライブラリで拡張、ドッグフードで穴を見つける」をそのまま適用する。
- **唯一やる価値のある検査器改善は1つだけ**（§6: レコードのフィールド型を深く検査）。グラフィクスはレコードだらけなので、「緑のチェックは嘘をつかない」という核の原則を守るためにここだけ閉じる。
- **小さな言語拡張が要るかもしれない箇所は1つ**（§7: capability の nullary 値メンバ `empty : T`）。要否は実装時に判定。
- 当初やろうとしていた **playground の入力UX強化は最後（フェーズ6）**。言語が「それに値する」状態にしてから磨く。

---

## 1. 二層アーキテクチャ（これが全体の背骨）

```
[ Layer B: Picture 代数 ]   ← 新設。合成可能・再帰的。アート/フラクタル/L-system 向き
        │  render : Picture -> List[Shape]   （純粋に「降ろす」）
        ▼
[ Layer A: List[Shape] ]    ← 既存。絶対座標。プロット/アトラクタ/物理 向き（120枚はここ）
        │  描画コントラクト（§2）
        ▼
[ 描画器: playground canvas / CLI picture 抽出 ]
```

- **Layer A はそのまま。** `picture : List[Shape]`（+ 色相 `h`）を解釈する今の canvas は無傷。既存例は1本も壊れない。
- **Layer B は純粋な Prism ライブラリ。** `Picture` を組み立て、最後に `render` で `List[Shape]` に変換。描画器から見れば出力は常に `List[Shape]`。
- 利点: 後方互換・追加のみ・テーゼと整合（合成＝flowに順序なし、再帰＝フラクタル、`render` は純粋関数）。

---

## 2. 描画コントラクトの明文化（言語ではなくルール）

「言語と描画器の間の契約」を REFERENCE に1節足して固定する。これ自体が Prism らしい（＝契約）。

- **静止画コントラクト**: プログラムは `picture : List[Shape]` という値を定義する。
- **アニメコントラクト**: プログラムは `frame(t: Num) : Picture`（または `List[Shape]`）という**純粋関数**を定義する。描画器が `t` を時間で与える。`!` を持たない＝アニメは純粋、という教育点。
- **Shape の語彙**（描画器が知る唯一の具体形）を明示的な `or` 型として確定する:

```prism
Shape : Line{ x1: Num, y1: Num, x2: Num, y2: Num }
     or Dot{ x: Num, y: Num }
     or Circle{ x: Num, y: Num, r: Num }
     or Rect{ x: Num, y: Num, w: Num, h: Num }
     or Poly{ pts: List[Point] }          -- ★新規候補（§フェーズ6）。曲線/L-system が安く豪華に
```

> ねらい: 「描けるのはこの語彙だけ」を契約として書く。AI に絵を書かせるときも、この契約を渡せば外さない。

---

## フェーズ計画

各フェーズ: **目的 / 触るもの（言語かライブラリか）/ テスト追加 / ドッグフード**。

### フェーズ0 — 土台（唯一の「コアに近い」作業）
- **目的**: Shape を明示型に確定（§2）。`Point : { x: Num and y: Num }` を定義。§6 のレコード検査改善をここで入れる。
- **触るもの**: `check.py`（レコードのフィールド型を深く合成。現状 `acc.field` は `?`）。`REFERENCE.md` に描画コントラクト節。
- **テスト**: `acc.field` の型不一致を弾く新ケースを `examples/` に追加（`mistyped` 系）。`test.py` の `CHECK`/`LINES` に。
- **ドッグフード**: 既存 `lib/physics2d.prism` の `Vec`/`Body` がフィールド型まで通るか確認（通らなければ #5/#16 の隠れ穴を1つ閉じたことになる）。

### フェーズ1 — Picture 代数の中核（純粋ライブラリ）
- **目的**: `lib/picture.prism` を新設。`Picture` 型 ＋ 中核結合子。**言語変更ゼロ**。
- **触るもの**: `lib/picture.prism`（Prismコードのみ）, `render` を Layer A に降ろす関数。
- **API スケッチ**:

```prism
include "lib/picture.prism"

Box : { x: Num and y: Num and w: Num and h: Num }
Picture : { shapes: List[Shape] and bbox: Box }

empty : Picture  <-  Picture{ shapes: [], bbox: Box{x:0,y:0,w:0,h:0} }

over(a: Picture, b: Picture) : Picture  <-           -- 重ね合わせ
  Picture{ shapes: concat(a.shapes, b.shapes), bbox: union(a.bbox, b.bbox) }

beside(a: Picture, b: Picture) : Picture  <-          -- a の右に b
  over(a, translate(a.bbox.w, 0, b))

above(a: Picture, b: Picture) : Picture  <-           -- a の下に b
  over(a, translate(0, a.bbox.h, b))

render(p: Picture) : List[Shape]  <-  p.shapes        -- Layer A へ降ろす
picture : List[Shape]  <-  render( beside(square, circle) )
```

- **注意**: リスト連結 `concat` は再帰で自前定義（スプレッド `[..xs, ..ys]` が通るか未確認なら recursion で安全に）。深い再帰は HANDOFF の N≤約340・アキュムレータ規則に従う。
- **テスト**: `examples/picture-basics.prism`（check OK ＋ render が非空）。`test.py` の新リスト `PIC`。
- **ドッグフード**: 既存フラクタル1本（例: `fractals/htree.prism`）を Picture 代数で書き直す。**ここで必ず本物のバグが出る**（finding #18 と同じ。小さな本物のプログラムは18個のマイクロ例より雄弁）。

### フェーズ2 — アフィン変換（純粋ライブラリ）
- **目的**: `translate` / `scale` / `rotate` を Picture に対して定義（各 Shape に map）。
- **触るもの**: `lib/picture.prism` 追記。
- **スケッチ**:

```prism
translate(dx: Num, dy: Num, p: Picture) : Picture  <-  mapShapes(p, s -> shiftShape(dx, dy, s))
scale(k: Num, p: Picture) : Picture                <-  mapShapes(p, s -> scaleShape(k, s))
rotate(deg: Num, p: Picture) : Picture             <-  mapShapes(p, s -> rotShape(deg, s))
```

- **テスト**: 変換後の bbox/座標を既知値と照合（決定的）。
- **ドッグフード**: `quartet(a,b,c,d)`（2×2 配置）と `cycle(p)`（90°回転で4枚）を定義 → エッシャー風 square-limit が書けるか試す。

### フェーズ3 — over = Monoid（能力で型クラスを「絵で」教える）
- **目的**: `over` が Monoid だと示し、`overAll(pics)` を fold で。型クラス章の例が「数値の足し算」ではなく**見える絵**になる。
- **触るもの**: `lib/picture.prism`（capability/provides）。§7 の要否判定もここ。
- **スケッチ**:

```prism
capability Monoid for T
  empty : T                       -- ★nullary 値メンバ（§7: 言語側の対応要否を要確認）
  combine(a: T, b: T) : T

Picture provides Monoid
  empty       <-  Picture{ shapes: [], bbox: Box{x:0,y:0,w:0,h:0} }
  combine(a, b)  <-  over(a, b)

overAll for T given T: Monoid (xs: List[T]) : T  <-
  xs match
    []        =>  empty
    [h, ..t]  =>  combine(h, overAll(t))
```

- **テスト**: `examples/picture-monoid.prism`（capable 系）＋ わざと不完全な `provides` を弾く `badpicture.prism`（incapable 系）。
- **ドッグフード**: フラクタルの「全枝を重ねる」処理を `overAll` に置換。

### フェーズ4 — アニメーション（描画器＋コントラクト。言語変更ほぼゼロ）
- **目的**: `frame(t: Num) : Picture` を純粋関数として描画器が時間駆動。**状態の書き換えなしで動く**＝時間の声の最高のデモ。
- **触るもの**: `playground.html`（時間ループ ＋ `frame` 呼び出し）。`REFERENCE.md` アニメコントラクト節。**playground 編集後は `node --check` 必須**（HANDOFF の地雷）。
- **既存資産との接続**: ライブスライダー（`SLIDER_RE`/`scheduleLiveDraw`/`*-live.prism`）は既に「束縛した値で再描画」する基盤。`t` を内部で進めるだけ。
- **スケッチ**:

```prism
frame(t: Num) : Picture  <-  rotate(t * 6, base)     -- 純粋。! が無い＝アニメは純粋
```

- **状態つきシミュ**: 新構文なし。`statemachine.prism` の定石（`or`型の遷移 ＋ 効果ブロック再束縛）で `step(s: State) : State` ＋ `render(s) : Picture` ＋ 初期状態を fold。
- **テスト**: `frame(0)`/`frame(1)` が決定的な非空 Picture を返すことを `VIS` で。
- **ドッグフード**: 振り子か lissajous を `frame(t)` 化。

### フェーズ5 — L-system ライブラリ（再帰＋文法の見せ場）
- **目的**: `lib/lsystem.prism` を新設。公理 ＋ 規則をデータで持ち、n 回展開 → `lib/turtle.prism` で解釈 → Picture。Context Free Art / Structure Synth 路線の旗艦。
- **触るもの**: `lib/lsystem.prism`（Prismコードのみ）。`lib/turtle.prism` の `fwd`/`turn`/`restore` を再利用。
- **スケッチ**:

```prism
Rule : { from: Text and to: Text }
expand(axiom: Text, rules: List[Rule], n: Num) : Text  <-  ...   -- 再帰展開
draw(s: Text, step: Num, angle: Num) : Picture          <-  ...   -- turtle 解釈
```

- **テスト**: セグメント数が既知の公式と一致するか（HANDOFF の検証法）。`FRACTALS` に追加。
- **ドッグフード**: 既存の植物/コッホ系を L-system 表現に統一。

### フェーズ6 — 仕上げ（ここで初めて入力UX）
- **目的**: (a) `Poly` 図形を Shape と描画器に追加（曲線が安く豪華に）。(b) **当初やりたかった playground の入力UX**（URL共有・ギャラリー・スライダー）をここで磨く。HANDOFF §5① の URL 共有はこの段でやると効果的。
- **触るもの**: `prism.py`（`Poly` 評価）, `playground.html`（`Poly` 描画 ＋ UX）, `check.py`（`Poly` の型）。
- **テスト**: 全フェーズ通しで緑。`ALGORITHMS.md` の目録更新。

---

## 6. 唯一やる価値のある検査器改善: レコードのフィールド型

現状 `acc.field` は `?`（gradual）に合成される（REFERENCE §4 v0 note）。グラフィクスは `Shape`/`Picture`/`Vec`/`Box` などレコードだらけなので、ここが `?` のままだと **「緑のチェックが嘘をつく」**（finding #5/#16 の核心）に直接抵触する。

- **やること**: 名目で追跡しているレコード型の宣言済みフィールド型を `synth` が引けるようにし、`.field` をそのフィールド型に合成。未宣言フィールドはエラー。
- **効く例**: `circle.r + "x"`（Num に Text）を弾ける。`p.bbox.w` が `Num` として通る。
- **これだけは Layer B の信頼性の土台**なので、フェーズ0で入れる。

---

## 7. 小さな言語拡張の要否（実装時に判定）

- **capability の nullary 値メンバ `empty : T`**（§フェーズ3）。今の能力メソッドは関数（`compare`/`fmap`）。Haskell の `mempty` 相当の引数なし値メンバがパース・検査・ディスパッチできるか要確認。
  - 通るなら拡張不要。通らないなら **HANDOFF の手順「(1)パーサが読めるように → (2)意味づけ」** で最小拡張。`empty` のディスパッチは「第1引数の型」が無いので、**呼び出し側の期待型から解決**する必要がある（型主導ディスパッチ）。難しければ当面 `Monoid` を `combine` のみ＋別途 `emptyPicture` 値で回避してもよい。

---

## 8. やらないこと（テーゼを濁さないため）

- **副作用で描く命令型 API（`line(x,y,...)` や可変キャンバス）を足さない。** 「ピュアな値としての絵」と二重化し、"声を混ぜるな" が崩れる。描画は常に `picture`/`frame` という値で表す。
- **すべてを結合子に押し込まない。** アトラクタ・パラメトリック曲線・物理は絶対座標（Layer A）が自然。結合子は構造的/再帰的なアート（Escher・L-system・合成フラクタル）に使う。両者は別レジスタで共存。
- **コンパイラ/モジュール/名前空間**は射程外（HANDOFF §5②）。`include` のグローバル併合のままで足りる。

---

## 9. 最初の一手

1. フェーズ0: `Shape`/`Point`/`Box` を明示型化し、§6 のレコード検査を `check.py` に入れる → `test.py` 緑を確認。
2. フェーズ1: `lib/picture.prism` に `over`/`beside`/`above`/`render` を書き、`fractals/htree.prism` を1本だけ移植 → **出てくるバグを記録**（ここが設計の本当の検証）。
3. 出たバグを見て、フェーズ2以降の優先度を再調整。

> 合言葉: **言語は閉じている。育てるのはライブラリと描画器。各フェーズは緑のまま出荷。ドッグフードが真実を語る。**
