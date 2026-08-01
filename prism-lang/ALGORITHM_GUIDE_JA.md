# Prism アルゴリズム棚の読み方

このページは、`algorithms/` に増やしたサンプルを「アルゴリズム名を知らなくても読める」ようにするための案内です。

Prism では、速さよりも **構造が見えること** が主役です。配列の破壊的更新や `for`/`while` がないので、古典アルゴリズムはだいたい次の形になります。

- リストを `[h, ..t]` に分けて再帰する
- 木やグラフを `or` 型やレコードで表す
- 探索失敗を `?NotFound` / `?NoPath` のように契約へ出す
- 更新は「元の値を書き換える」のではなく「新しい値を返す」

---

## まず読むなら

最初はこの順番が読みやすいです。

1. [`lists.prism`](algorithms/lists.prism)  
   リスト再帰の基本です。ほとんどのサンプルがこの読み方を使います。

2. [`search.prism`](algorithms/search.prism)  
   線形探索、二分木探索、DFS/BFS、失敗つき探索が並びます。

3. [`sorting.prism`](algorithms/sorting.prism) と [`divide_conquer.prism`](algorithms/divide_conquer.prism)  
   insertion sort / quicksort / merge sort / binary search で、分けて戻す感覚が見えます。

4. [`graph.prism`](algorithms/graph.prism)  
   DFS/BFS と `?NoPath` が分かると、グラフ系の読みやすさが上がります。

5. [`dynamic.prism`](algorithms/dynamic.prism)  
   DP の「漸化式そのもの」を Prism で読むサンプルです。

---

## 探索・グラフ系

**DFS / 深さ優先探索**  
一つの枝を奥まで進み、だめなら戻って別の枝を見る探索です。迷路を「とりあえず行けるところまで行く」感じです。  
Prism では、子リストや frontier の先頭を先に処理する再帰として出ます。

**BFS / 幅優先探索**  
近い場所から順番に広げる探索です。最短手数を知りたいときに向きます。  
Prism では、queue の末尾に次の候補を足していく形になります。

**Dijkstra**  
重みつきグラフで「一番安い経路」を探す方法です。毎回、今見えている中で一番距離が短い場所を確定します。  
[`shortest_path.prism`](algorithms/shortest_path.prism) では、ヒープの代わりにソート済みリストを優先度キューとして使っています。

**Bellman-Ford**  
辺を何度も緩和して最短距離を更新する方法です。Dijkstra より遅いですが、負の重みを扱いやすいです。  
[`bellman_ford.prism`](algorithms/bellman_ford.prism) では、距離表をレコードのリストとして持ちます。

**Topological sort / トポロジカルソート**  
依存関係の順番を作る方法です。「A のあとに B」みたいな関係を壊さない並びを作ります。循環があると失敗します。  
[`topo_sort.prism`](algorithms/topo_sort.prism) では `?Cycle` として循環検出を契約に出しています。

**MST / 最小全域木**  
すべての点をつなぎつつ、辺の合計コストを最小にする問題です。ネットワーク配線を安くつなぐようなイメージです。  
[`mst.prism`](algorithms/mst.prism) は Kruskal 法で、Union-Find と組み合わせています。

**Union-Find**  
「この 2 つは同じグループか？」を高速に扱うデータ構造です。Kruskal 法や連結判定でよく使います。  
Prism 版では親テーブルを書き換えず、新しい親テーブルを返します。

---

## 木・データ構造系

**Binary Search Tree / 二分探索木**  
左に小さい値、右に大きい値を置く木です。探索時に左右どちらかだけ見ればよくなります。

**Heap / ヒープ**  
最小値や最大値をすぐ取り出すための構造です。普通は配列で書きますが、Prism では [`heap.prism`](algorithms/heap.prism) の skew heap のように、木の merge として書く方が自然です。

**Trie / トライ木**  
単語やトークン列を共有接頭辞で保存する木です。辞書、補完、前方一致検索で使います。  
[`trie.prism`](algorithms/trie.prism) では、子を `C{key, trie}` のリストとして持ちます。

**Segment Tree / セグメント木**  
区間の合計や最大値などを高速に問い合わせる木です。  
[`segment_tree.prism`](algorithms/segment_tree.prism) では、更新も破壊的に書き換えず、更新後の木を返します。

---

## 数列・配列っぽい処理

**Prefix sums / 累積和**  
先頭からの合計を前もって作っておくことで、区間合計をすぐ出す方法です。

**Sliding window / スライディングウィンドウ**  
固定幅の窓をずらしながら見る方法です。連続した 3 個の合計、連続区間の最大値などで使います。

**Quickselect**  
ソート全体はせず、「小さい方から k 番目」だけを探す方法です。quicksort の片側だけを辿る感じです。

**Counting sort / カウントソート**  
値の範囲が小さいときに、各値の出現回数を数えて並べ直す方法です。

**Boyer-Moore majority vote**  
過半数を占める値があるかを少ない状態で探す方法です。候補とカウントだけを持って走査します。

---

## DP・組合せ・バックトラック

**Dynamic Programming / 動的計画法**  
大きい問題を小さい問題に分け、同じ小問題を使い回す考え方です。Prism v0 には mutable table がないので、ここでは「漸化式がそのまま見える」形にしています。

**Knapsack / ナップサック**  
重さ制限の中で価値が最大になる品物の組み合わせを探す問題です。

**Edit distance / 編集距離**  
片方の列をもう片方にするための挿入・削除・置換の最小回数です。

**Backtracking / バックトラック**  
候補を一つ選び、だめなら戻って次を試す方法です。順列、組合せ、N-Queens、グラフ彩色などで使います。

**Graph coloring / グラフ彩色**  
隣り合う点が同じ色にならないように色を割り当てる問題です。制約充足問題の小さな入口です。

---

## 数論・数値計算

**GCD / Euclid**  
最大公約数を求める方法です。Prism では引き算版と `modN` 版の両方の雰囲気が見られます。

**Sieve of Eratosthenes / エラトステネスの篩**  
素数を列挙する方法です。候補リストから倍数を消していきます。

**Extended Euclid / 拡張ユークリッド**  
`a*x + b*y = gcd(a,b)` になる `x,y` まで求めます。mod 逆元の計算に使います。

**Fast exponentiation / 高速累乗**  
指数を半分にしながら累乗を求める方法です。`x^10` を `x*x` の累乗に分けて減らします。

**Newton method / ニュートン法**  
近似値を何度も改善して平方根などを求める方法です。

---

## 文字列・圧縮・オートマトン

**Pattern matching**  
列の先頭がパターンと一致するか、列の中に含まれるかを調べます。Prism v0 は文字単位の Text 操作が弱いので、サンプルでは `List[Num]` をトークン列として使っています。

**RLE / Run-length encoding**  
同じ値の連続を `値 + 回数` に圧縮します。`[1,1,1,2,2]` が `Run{1,3}, Run{2,2}` になるイメージです。

**DFA / 決定性有限オートマトン**  
状態と入力から次の状態を決める機械です。正規表現や字句解析の基礎にあります。

**Balanced parentheses**  
括弧の対応が正しいかを調べる小さな parser です。閉じ括弧が多すぎる場合を `?Underflow` として表しています。

---

## Prism で特に見てほしいところ

**失敗が契約に出る**  
`?NoPath`, `?NotFound`, `?Cycle`, `?Empty`, `?Missing` のように、「見つからない」「道がない」「循環している」が返り値の影に隠れません。

**更新は新しい値を返す**  
Union-Find、Segment Tree、Trie など、本来は更新するデータ構造も、Prism では新しい構造を返します。遅い代わりに、流れは読みやすいです。

**網羅性が効く**  
`Tree : Leaf or Node{...}` のような型では、`Leaf` と `Node` の両方を処理しないと静的チェックで止められます。木のアルゴリズムが読みやすい理由の一つです。

**苦しいところも分かる**  
配列の破壊的更新、巨大な DP table、高速な heap、文字列の低レベル処理は Prism v0 では得意ではありません。だからこそ「この言語の輪郭」を見る教材になります。

---

## 次に読むとよいファイル

- 全体一覧: [`ALGORITHMS.md`](ALGORITHMS.md)
- 言語の基本: [`REFERENCE.md`](REFERENCE.md)
- 実行方法: [`GETTING_STARTED.md`](GETTING_STARTED.md)
- AI に Prism を書かせる最小仕様: [`AI_GUIDE.md`](AI_GUIDE.md)
