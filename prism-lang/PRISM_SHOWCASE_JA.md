# Prism らしさショーケース

これはアルゴリズム集の次に読む、小さな Prism 実験集です。目的は「この言語なら何が書けるか」より、
**同じプログラムを読んだときに何が先に分かるか**を体で掴むことです。

## まず3本を動かす

```sh
python cli.py check showcase/01-contracts.prism
python cli.py run   showcase/01-contracts.prism

python cli.py check showcase/02-failure-as-data.prism
python cli.py run   showcase/02-failure-as-data.prism

python cli.py check showcase/03-capability-contract.prism
python cli.py run   showcase/03-capability-contract.prism
```

| 例 | 見る場所 | 分かること |
|---|---|---|
| `01-contracts` | `couponRate : Num ?UnknownCoupon` | クーポンが無いことは例外的な裏事情ではなく、関数の契約に出る。`quote` は `match` で処理したので失敗を外へ漏らさない。 |
| `01-contracts` | `Plan : Free or Pro` | `monthlyFee` は両方のケースを扱う。`Pro` の分岐を消すと静的チェッカーに止められる。 |
| `01-contracts` | `main : () !console` | 画面に表示することも契約に現れる。計算だけの関数 `quote` には `!console` がない。 |
| `02-failure-as-data` | `ok score` / `fail _` | 失敗を握りつぶすのでなく、通常の分岐として表示文に変えている。 |
| `03-capability-contract` | `given T: Ord` | ジェネリック関数が「比較できる型だけ欲しい」と署名で要求できる。 |

## 01 を行ごとに読む

`couponRate` の署名は次のように読めます。

```prism
couponRate(code: Text) : Num ?UnknownCoupon
```

「文字列を受け取り、数値を返す。ただし `UnknownCoupon` で失敗するかもしれない」です。
`quote` はその結果を `match` で `ok` と `fail` に分けています。そのため `quote` 自身は
`?UnknownCoupon` を宣言しません。ここが Prism の一番おもしろい所です。呼び出し側は `quote` が
必ず文章を返すと、署名だけで判断できます。

## アルゴリズムと結ぶと

アルゴリズム集にも同じ形があります。

- [Dijkstra](algorithms/shortest_path.prism) は、道がない可能性を `?NoPath` として宣言し、表示側で `no path` に変換します。
- [トポロジカルソート](algorithms/topo_sort.prism) は、循環を `?Cycle` として宣言し、表示側で `cycle` に変換します。
- [Trie](algorithms/trie.prism) は、子ノードが無い可能性を `?Missing` として局所的に処理します。

つまり Prism では、アルゴリズムの「失敗条件」も実装の端に追いやられず、関数の表札に残ります。

## 次にやる小さな改造

1. `01-contracts.prism` の `monthlyFee` から `Pro` の行を消して `check` する。
2. `couponRate` の `?UnknownCoupon` を消して `check` する。
3. `main` の `!console` を消して `check` する。

どれも実行する前に止まります。なぜ止まるかは [ERROR_MUSEUM_JA](ERROR_MUSEUM_JA.md) で対応する展示を読めます。
