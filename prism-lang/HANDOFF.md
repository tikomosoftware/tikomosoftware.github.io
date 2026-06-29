# Prism — 引き継ぎドキュメント (HANDOFF)

> **別のPC・別のAI（または人間）がこのプロジェクトを引き継いで開発を続けるための、唯一の手引き**です。
> 別AIは Claude の永続メモリを読めないので、**このファイルが真実の源**です。まずこれを通読 →
> `OVERVIEW.md`（思想）→ `AI_GUIDE.md`（最小仕様）→ `REFERENCE.md`（完全仕様）→ `NOTES.md`（設計日誌）の順が早いです。

作業ディレクトリ: プロジェクトのルート（例 `C:\Users\100440\prism\`）/ 依存: **Python 3.8+ のみ、サードパーティ依存ゼロ**。Bash でも PowerShell でも可。

**振る舞いの約束（このプロジェクトの流儀）**：
- ユーザーへの応答は **日本語**。**言語デザイナー／言語学者（Hejlsberg 的な立場）**として、率直に・設計の一貫性を最優先で。
- **何か変えたら必ず `python cli.py test` を緑のまま保つ**こと。各変更は小さくコミット（1機能=1コミット、メッセージは実態に正直に）。
- **ドキュメントに載せる検査器の出力・数値は、必ず実機から取って貼る**（推測で書かない＝過去に陳腐化/捏造を繰り返した教訓）。

---

## 0. まず動作確認（30秒）

```sh
cd <プロジェクトのルート>
python cli.py test          # => ALL GREEN [all]: 824 passed, 0 failed   ← これが基準線
```

緑が基準線。件数は増えるので数字自体は気にせず **`0 failed`** を見る。

```sh
python cli.py run    examples/calc.prism            # 実行（ツリーウォーク・インタプリタ）
python cli.py check  examples/broken.prism           # 静的検査（わざと失敗する例）
python cli.py reveal examples/infer.prism            # 型・効果・失敗の契約を推論して表示
python cli.py serve                                  # http://localhost:8000/ で playground
python cli.py fetch-pyodide                          # （任意）Pyodideをローカルに落として完全オフライン化
```

git: `master` に一直線でコミット済み。タグ **`v0.3`**（グラフィクス層＋ドキュメント整理）, **`v0.4`**（`?` を失敗専用に純化）。リモートは未設定（GitHub に出さない方針）。

---

## 1. Prism とは（30秒）

**AI時代の「考えるための」教育用言語**（Smalltalk / Logo / Scheme の系譜）。実用性ではなく*学ぶ価値*が核。
**初心者の最初の言語ではない**（効果・失敗・能力・高階型を扱う本格的な型システム）。ビルド/コンパイルは**無い**。

中心思想 = **計算の4つの声（voices）**。各声は専用の記号を持ち、**決して混ざらない**（これが教育的価値の核）：

| 声 | 記号 | 意味 |
|---|---|---|
| 事実 (fact) | `:` `and` `or` | 型・データ。`and`=積/レコード, `or`=和/バリアント |
| 流れ (flow) | `<-` `=>` | 依存関係。**行順ではない**（純粋な流れに順序は無い、遅延評価） |
| 作用 (effect)| `!world` | 副作用。`!console` など。純粋さ = `!` が無いこと |
| 失敗 (failure)| `?Error` | 失敗は「flowに持ち上げた`or`型」。`try`で伝播、`match`/`rescue`で消費 |
| 時間 (time) | `~>` | 順序付け。非末尾の各ステップは時間に触れねば（`!`か`?`）ならない |

関数シグネチャ = **「正直な契約」**：`f(x: A) : B !world ?Error <- ...`。**AIが本体を書き、人間が契約を読み、検査器が契約を守らせる。**
契約が保証するのは**「何に触れ・どう失敗しうるか」の輪郭**であって、**計算の正しさそのものではない**（README/AI_GUIDE の表現はこの線で正直に書いてある）。

**最重要の結論**: Prism の価値は新奇な構文ではなく**型システム（検査器）**にある。検査器なしの記法はただの飾り。

> ⚠️ **記号の最新ルール**：`?` は**失敗専用**（`?Error` / `?{..}` / `?g`）。**未知の型（gradual）は `_`** で表す（`reveal` も `_` を表示、`f(x: _) : _` と明示も可）。`?` を型の位置に書くとパースエラー。これは「1声=1記号」を守るための純化（タグ `v0.4`）。

---

## 2. ファイル地図

### 言語コア（これだけが「言語」。他は全部ツール/ドキュメント/サンプル）
- **`prism.py`** — インタプリタ。字句解析（インデント認識）＋再帰下降/Prattパーサ＋ツリーウォーカ＋能力メソッドの実行時ディスパッチ。`parse_program_with_includes(src)` が AST を返す入口。
- **`check.py`** — 静的検査器。式を **(型, 効果集合, 失敗集合)** に合成。型単一化＋行多相＋網羅性＋能力＋高階種＋時間＋補間＋**レコードのフィールド型**。`--reveal` で契約推論。

### ツール
- **`cli.py`** — 統一エントリ。`run` / `check` / `reveal` / `test` / `serve [port] [--host H]` / `fetch-pyodide`。
- **`prism.cmd`**(Windows) / **`prism`**(POSIX) — PATH に置けば `prism run foo.prism`。
- **`test.py`** — 回帰ハーネス。check.py/prism.py を**モジュールとして import** し stdout を捕捉して期待値と照合。dict: `CHECK`/`LINES`/`RUN`/`TUT`/`ALG`/`PATHED`/`FRAMES`/`VIS`/`PHYS`/`FRACTALS`。

### Web（静的サイト。ビルド不要、`.md`/`.py`/`.prism` は実行時 fetch）
- **`index.html`** — ランディング。**`docs.html`** — `?p=NAME.md` を marked@12(CDN) で描画（ナビに OVERVIEW/GETTING_STARTED/TUTORIAL/ALGORITHMS/REFERENCE/AI_GUIDE/NOTES/README）。
- **`playground.html`** — ライブエディタ＋キャンバス。**Pyodide が同じ prism.py/check.py をブラウザで実行**（移植なし）。機能：Run/Check/Reveal/**Draw**/**▶Animate**、**🔗Share**（`#code=` URL共有）、**🌈vivid**（彩度UP＋虹色サイクル）、**絞り込み検索ボックス**、ライブ`slider`、自動保存、✚new スターター、遅延ギャラリー読込。

### ドキュメント (.md)
- `README.md` — **短い案内板**（3デモ hook ＋ 保証/非保証表 ＋ 索引）。`OVERVIEW.md` — 思想と使い方。`GETTING_STARTED.md` — 導入。`TUTORIAL.md` — 6課。`ALGORITHMS.md` — アルゴリズム＋全ギャラリー目録（絵・アニメ）。`REFERENCE.md` — 完全仕様（文法EBNF・エラーカタログ・描画/アニメ契約）。**`AI_GUIDE.md`** — LLM に貼る最小仕様＋禁止事項＋実演。**`NOTES.md`** — 設計日誌（検査器の思想・18の発見・ロードマップ）。`LICENSE`(MIT)。

### サンプル（.prism、合計多数。完全な目録は ALGORITHMS.md）
- `examples/` — 検査の効くフィクスチャ（divide/map/poly/broken/mistyped/**mistyped-field**/shapes/capable/hkt/time/traits/calc/infer…）＋ `picture-basics`/`picture-transforms`/**`lib-check`**（stdlib検証）/conditionals/statemachine/projectile。
- `tutorial/`(6) — 01-hello → 06-capabilities（各「壊してみよう」付き）。
- `algorithms/`(9) — recursion/lists/sorting/tree/sierpinski/bounce/draw/koch/pythagoras。
- `fractals/`(~35) — 木・植物（L-system）/曲線/空間充填、**Picture代数**（htree-pic, square-limit, koch-lsys, plant-lsys, poly-vortex）、**マンデルブロ系**（mandelbrot, multibrot, burning-ship, julia）。
- `physics/`(~115) — シミュ＋アトラクタ約20＋曲線多数＋**21種の純粋 `frame(t)` アニメ**（振り子・二重振り子・重力・噴水・花火・雪・波/干渉/海面/太鼓膜/乱流・3D立方体/トーラス/球・銀河・ワープ・万華鏡 …）。
- `lib/`（include 可能・8本） — `math`(minN/maxN/clamp/sign/lerp/frac/mod), `list`(length/concat/concatAll/reverse/map/filter/foldl/times/range), `picture`(Picture代数; math・list を include), `physics2d`(Vec/Body/Euler), `draw2d`(polyline), `turtle`(fwd/turn/restore=L-system), `lsystem`(データ駆動L-system), `escape`(マンデルブロ系: 複素数=`Pt{x,y}`)。

---

## 3. アーキテクチャ要点（コードに触る前に）

- **2フェーズ独立**: `prism.py`(実行) と `check.py`(検査) は別物。両方 `parse_program_with_includes` で AST を得る。
- **gradual typing**: 型注釈が**無い**箇所だけ未知型 `_` ＝契約境界として何にでも一致。注釈が**ある**既知型同士の食い違いは黙らせない。「注釈が無い＝まだ契約していない」。
- **レコードのフィールド型**（タグ `v0.4` 以降）: 宣言済みレコードの値（注釈付き引数・コンストラクタ литерال・`p.bbox` のような連鎖）に対し、`.field` は**宣言された型を返す**（`box.w` は Num → `box.w + "x"` を検出）。**開いたまま**: 未宣言フィールド・型不明・多バリアント `or`（変種が曖昧）は `_` のまま ⇒ 色相 `h` も構造的追加も壊れない。`check.py` の `record_fields` / `fields_of` / `synth(Field)`、パーサの `parse_braced_fields`（旧 `skip_braced` を置換＝以前はフィールド型を捨てていた）。
- **ジェネリクス = 穴(holes)**: 型`T` / flow`(T)->U` / 効果`!e` / 失敗`?g` / コンテナ`F[_]`。`for`節で宣言。制約は事実なので `:` 再利用 → `given T: Ord`。
- **能力(capability)**: `capability Ord for T`＝トレイト, `Num provides Ord`＝インスタンス。検査器は (1)制約 discharge (2)インスタンス完全性 (3)coherence(型×能力で1つ) (4)メソッド本体の契約。実行時は第1引数の型タグで単一ディスパッチ。
- **時間 `~>`**: 順序付けではなく**順序の正当性チェック**（非末尾ステップが純粋ならエラー）。「純粋な流れに順序なし」の鏡像。
- **グラフィクス（Layer A / B、ほぼ言語変更ゼロで実現）**:
  - Layer A = `picture : List[Shape]`（絶対座標）。キャンバスが描けるのは **Line / Dot / Circle / Rect / Poly{pts:[Pt{x,y}]}** の5種。任意で色相 `h`(0–360)。
  - Layer B = `lib/picture.prism` の **Picture 代数**（over/beside/above/scale/rotate/quartet/cycle/render、`Box`/`Picture`/`Pt` レコード）。純粋値の合成＝flowの声。
  - **アニメ** = 純粋関数 `frame(t) : Picture`。playground の ▶Animate が `t`(秒)を進めて毎フレーム再描画。**`!` が無い＝検査器がアニメの純粋性を保証**（裏で `show!console` すると弾かれる）。`frac`/`mod`（＋組み込み `floor`）で寿命をループ。
  - **エスケープタイム** = 複素数を `Pt{x,y}` で表し `z→z^d+c` を反復、色付き Dot のグリッド、内部点は描かない。`lib/escape.prism`。
- **エラーに行番号**: `Node.line` をパーサがスタンプ、`err()` が `line N:` を前置。
- **設計は CLOSED**: 4声テーゼに対して言語は概念的に完成。新機能はむやみに足さず、**ドッグフーディングで本物の穴が出たときだけ**既存機構の再利用で埋める（過去 `if`・Boolパターン・複数行`or`型・フィールド型などをこの流儀で埋めた）。グラフィクス工程での言語変更は **`floor` 組み込み1つだけ**。

---

## 4. お作法と地雷（過去に踏んだもの。必ず守ること）

### 言語（.prism）を書くとき
- **値の束縛は必ず小文字始まり。** `MAX <- 28` は不可 ── 大文字始まりは**コンストラクタ/タグ**扱いになり、値ではなく nullary タグと解釈される（マンデルブロで実際に踏んだ：`.x` が無い/比較に型が来る）。`maxIter <- 28`。
- **`?` は失敗専用、未知の型は `_`。** 型の位置に `?` を書かない。
- ~~文字列リテラル内に `--` を書かない~~ → **修正済み**：`--` を含む文字列は今は普通に書ける
  （`"a -- b"` でOK。レキサが文字列を尊重する。NOTES 所見#26）。
- **リストのスプレッドは末尾に1つだけ**（`[h, ..t]` 可、`[..a, ..b]` 不可 ⇒ 連結は `lib/list` の `concat` か再帰）。
- **`if ... then ... else ...` は1行（インライン）のみ。** 複数行分岐は `match`。
- **`~>` の各手順は作用か失敗を持つこと**（純粋な式を並べると型エラー）。
- **`include` は実行時 CWD 相対**（プロジェクトルートから実行）。グローバル併合・**名前空間なし**＝同名の最上位定義は衝突する（名前を分ける運用。これは意図した割り切りで、直さない）。
- 深い逐次再帰（シミュ）はPythonスタックを食う。`build_env` が `setrecursionlimit(40000)` 済みだが **N ≤ 約340** に抑える。フラクタルは**アキュムレータ**（`[edges, ..acc]`）でスタック深さ=木の深さに。
- 文字列補間 `"{expr}"` の中の効果/失敗も検査される。

### シェル / git の地雷
- **`git commit -m "...\`...\`..."` のバッククォートは、bash のダブルクォート内でコマンド置換され単語が消える**（"now \`include\`s" → "now s"）。**バッククォートを含むメッセージは `-F` でファイル/ヒアドキュメントから渡す**。
- **`git commit -m @'...'@` は PowerShell のヒアストリング構文。Bash では解釈されず `@` がメッセージに混入する**。Bash では使わない（`-F -` ＋ヒアドキュメントが安全）。

### playground.html を編集したら
- **必ず `node --check` で構文検証**：
  ```sh
  python - <<'PY'
  import re
  html=open('playground.html',encoding='utf-8').read()
  app=max(re.findall(r'<script>(.*?)</script>', html, re.S), key=len)
  open('_app.js','w',encoding='utf-8').write(app)
  PY
  node --check _app.js && echo "JS OK"; rm -f _app.js
  ```
- **GLUE（Pyodideに渡す Python 文字列）は JS のテンプレートリテラル \` \` の中**。中に**リテラルのバックティックを書くと文字列が早期終了してページ全体が壊れる**（実際に踏んだ）。シングルクォートを使う。
- **スライダー引数に `0 - 3` を書かない**（`SLIDER_RE` は `-?[\d.]+` のみ）。`slider(1.4, -3, 3)`。
- 主要アンカー（grep可）: `SAVE_KEY`/`saveCode`/`loadSaved`/`fillExamples`（保存・URL復元）, `SLIDER_RE`/`refreshSliders`/`currentSource`/`scheduleLiveDraw`, `drawShapes`/`drawPrim`/`accBounds`/`viewOf`/`paintShapes`（描画）, `animate`/`stopFrameAnim`（アニメ）, `colorStr`/`VIVID`, `renderOptions`/`addGalleryOptions`/`galleryPaths`（検索・遅延ギャラリー）, `recommend`/`updateRecommend`, GLUE関数 `pz_run`/`pz_check`/`pz_reveal`/`pz_picture`/`pz_frame`/`_shapes_json`。新ギャラリー追加時は `GALLERY` 配列に、lib 追加時は boot の `engineFiles` 配列に。

### ギャラリーに絵を1枚足す手順（最頻タスク）
1. `.prism` を `fractals/` か `physics/` に作る。**`picture`**（List[Shape]）または純粋 **`frame(t) : Picture`**（アニメ）を定義。
2. **有限・有界か検証**（キャンバスは bbox 自動フィット＝座標スケールは無関係、有限性だけが要件）:
   `python -c "import prism; print(len(prism.value_of(open('physics/foo.prism',encoding='utf-8').read(),'picture')))"`
   アニメは `prism.apply_fn(prism.force(prism.build_env(prism.parse_program_with_includes(src)).get('frame')), [1.5])` で確認。
3. `python cli.py check ...` が OK か。
4. `test.py` の該当リスト（`PHYS`/`FRACTALS`、アニメは `FRAMES`、include 使用は `PATHED`）に追加。
5. `playground.html` の `GALLERY` に追加（include する lib は boot の `engineFiles` にも）。
6. `python cli.py test` 緑を確認、`ALGORITHMS.md` 目録更新。
- L-system は `lib/lsystem.prism`（公理＋規則をデータで `expand` → turtle で `draw`）。セグメント数が既知の公式と一致するか検証。

### 言語機能を足すとき（慎重に）
順序は必ず **(1)パーサが読めるように → (2)意味づけ**（「パースできないものは契約に書けない」）。過去の追加は全部既存機構の再利用で済んだ。新スケルトンが要る設計はテーゼと矛盾しないか疑う。

---

## 5. 残っている作業・次の一手

直近のレビュー指摘（名前/初心者表現/信頼の表現/入口の重さ/AI_GUIDE/共有URL/stdlib整理/`?`二義性/フィールド型）は**全て対応済み**。残りは：

### 監査で挙げた #3（リモート公開と対で効く・GitHub に出さないなら低優先）
- **CI**: GitHub Actions で `python cli.py test`（リモート設定後）。
- **ブラウザ・スモークテスト**: headless で playground を1回ロード→Run（実 Pyodide 実行は現状テストされていない＝素の Python グルーのみ検証）。
- **ドキュメントを実機出力から生成する規律**（既に README の3デモは実出力）。

### 言語の地平線（本 v0 の外。「Prism が何であるか」を変えない）
- レコードの**構築完全性**検査（`Box{x:1}` のフィールド欠落は現状未検出。アクセス側の型は検査済み）。← 型システムの次の一歩として自然。
- 効果の粒度（`!console` vs 粗い `!io`）、能力メソッドの多重ディスパッチ、`~>` の値パイプ糖衣、本物のモジュール/名前空間（include は意図的に flat-global のまま）。
- 着手前に必ず `OVERVIEW.md` の思想・`NOTES.md` の設計判断と整合チェック。

### 新ビジュアル・アプリ（いくらでも増やせる）
§4 の手順で。**次に何を作るかの候補は [IDEAS.md](IDEAS.md) にまとめてある**（重力スリングショット／
ボロノイ図／3D地形／反応拡散… 各々の作り方・実現可否・難易度つき）。sin系2Dマップ・アトラクタや
純粋 `frame(t)` アニメは安く豪華。

> **既知の小さな限界**：Layer B の変換（shiftShape/rotShape/scaleShape）は図形を作り直す際に**任意の色相 `h` を落とす**（万華鏡等は rainbow-by-index にフォールバック）。許容範囲として未修正。

---

## 6. セキュリティ/方針メモ（引き継ぐ判断）
- **CDNスクリプト（Pyodide, marked@12）に SRI ハッシュは意図的に付けていない**（オフライン計算不可・誤ハッシュで読込破綻するため）。`crossorigin` ＋「堅牢デプロイでは self-host / SRI pin 推奨」コメントで代替。堅牢化するなら：ピン留めSRI＋DOMPurify＋CSP。
- `prism serve` は既定で **127.0.0.1（ループバック）のみ**。LAN公開は `--host 0.0.0.0`（警告つき）。
- `fetch-pyodide` の tar 展開は path-traversal/シンボリックリンクを拒否、バージョンを `^\d+\.\d+\.\d+$` で検証済み。

---

## 7. 引き継ぎ後の最初の一手（推奨）
1. `python cli.py test` で `0 failed` を確認（基準線）。
2. `python cli.py serve` → playground を触る（例を検索→Draw、`frame`系を選んで ▶Animate、🌈vivid、🔗Share、自動保存）。
3. `OVERVIEW.md`（思想）→ `AI_GUIDE.md`（最小仕様・禁止事項）→ `REFERENCE.md`（仕様）→ `NOTES.md`（なぜそう作ったか）。
4. ユーザーに方向を確認して着手（新ビジュアル / 型システムの次の一歩 / それ以外）。**変更は小さく、ハーネス緑を保ち、ドキュメントの数値・出力は実機から貼る。**
