# Engineering Design Benchmarks

工学設計タスクにおけるエージェントの設計判断、ツール選択、探索戦略、DR説明能力を評価するためのベンチマーク集です。

各ベンチマークでは、エージェントがRAG/DBから設計基準を抽出し、公開MCPツール群から必要なものを選び、少ない試行回数で最小コスト成立解に到達し、その根拠を戦略レポートと結果レポートで説明できるかを評価します。

## Benchmarks

- [precision_arm_benchmark](precision_arm_benchmark/README.md): 精密計測アームの断面・材料・長さ設計ベンチマーク

## Development

```bash
cd precision_arm_benchmark
python3 -m unittest discover -s tests
```

## License

MIT
