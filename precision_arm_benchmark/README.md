# Precision Arm Benchmark

精密計測アーム設計ベンチマークの開発用リポジトリです。
ベンチマーク利用者へ提供する情報と、評価運用に使う情報を分離しています。

## 配布物

- `public/`: ベンチマーク利用者へ提供する公開実行パッケージ
- `private/`: 評価運用者向けの評価運用パッケージ
- `dist/precision_arm_benchmark_public/`: 生成される配布用ディレクトリ

配布用ディレクトリを作るには以下を実行します。

```bash
python3 scripts/build_public_dist.py
```

生成後、ベンチマーク利用者は `dist/precision_arm_benchmark_public/README.md` の手順だけで開始できます。

## 開発

外部依存はPython標準ライブラリのみです。

```bash
python3 -m unittest discover -s tests
python3 scripts/build_public_dist.py
python3 scripts/build_public_dist.py --check-only
```
