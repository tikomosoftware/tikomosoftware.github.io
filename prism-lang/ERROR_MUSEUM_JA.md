# Prism エラー博物館

ここは「Prism がうるさい」と感じたときに来る場所です。展示品はすべて意図的に失敗するプログラムで、
`python cli.py check <ファイル>` を実行すると静的チェッカーの指摘を見られます。実行時にたまたま動くかどうかではなく、
**契約と本体の食い違い**を先に見つけます。

理由と直し方も一緒に読みたい場合は、診断表示を使えます。検査規則は通常時とまったく同じです。

```sh
python cli.py check --explain examples/broken.prism
```

ブラウザの遊び場では `診断` にチェックを入れてから `Check` を押します。

## 展示一覧

| 展示 | ファイル | 静的チェッカーが止めること | 成功例 |
|---|---|---|---|
| 副作用の書き忘れ | [broken.prism](examples/broken.prism) | `show!console` を呼ぶのに `!console` を署名へ書いていない | [01-contracts](showcase/01-contracts.prism) |
| 失敗の書き忘れ | [broken.prism](examples/broken.prism) | `fail DivByZero` の可能性を `?DivByZero` として出していない | [02-failure-as-data](showcase/02-failure-as-data.prism) |
| 失敗の未処理 | [effect-arg-fail.prism](examples/effect-arg-fail.prism) | 失敗しうる値を表示の途中で使い、失敗が外へ漏れる | [Trie](algorithms/trie.prism) |
| OR型の分岐漏れ | [nonexhaustive.prism](examples/nonexhaustive.prism) | `Circle or Square or Triangle` の一部しか `match` していない | [01-contracts](showcase/01-contracts.prism) |
| capability の未充足 | [incapable.prism](examples/incapable.prism) | `given T: Ord` を満たさない型を渡す、または要求を伝播していない | [03-capability-contract](showcase/03-capability-contract.prism) |
| 効果の粒度リーク | [effect-narrow.prism](examples/effect-narrow.prism) | `!io` を行う本体を、より狭い `!console` と偽っている | [effects.prism](examples/effects.prism) |
| 型・フィールドの違い | [mistyped.prism](examples/mistyped.prism) | 型に合わない値、存在しないフィールドを使っている | [shapes.prism](examples/shapes.prism) |
| include の名前衝突 | [collision.prism](examples/collision.prism) | 読み込んだ定義を、同じ名前で上書きしようとしている | [collide.prism](examples/collide.prism) |

## 見方

まずは一つだけ、`broken.prism` を見ます。

```sh
python cli.py check examples/broken.prism
```

3つの問題が出ます。副作用、失敗の宣言漏れ、失敗の未処理です。ここで大事なのは、静的チェッカーが
「この処理は危険」と曖昧に言うのではなく、**どの契約が不足しているか**を行番号とともに言うことです。

次に [showcase/01-contracts.prism](showcase/01-contracts.prism) を `check` します。同じように表示・分岐・
失敗があるのに、こちらは通ります。違いは複雑な防御コードではなく、署名と `match` が本体と揃っている点です。

## この博物館が示す範囲

Prism は「プログラムが数学的に正しい」ことまでは保証しません。Dijkstra の実装を間違えれば、契約が正しくても
答えは間違えられます。一方で、何に触れるか、どこで失敗するか、全ケースを処理したか、必要な能力があるかは、
実行前にかなり厳密に確認できます。

この分担が Prism の個性です。人間はアルゴリズムの意味をレビューし、静的チェッカーは契約からはみ出した部分を見張ります。
