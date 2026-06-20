# Precision Arm Benchmark

精密計測アーム設計ベンチマーク用の、決定論的な簡易計算ツールと疑似RAGデータです。
高忠実度CAEではなく、エージェントが「設計基準抽出、戦略立案、必要ツール作成、候補評価、DR回答」まで手戻り少なく進められるかを測るための環境です。

このベンチマークでは、エージェントがRAG/DBから設計基準を抽出し、公開MCPツール群から必要なものを選び、少ない試行回数で最小コスト成立解に到達し、その根拠を戦略レポートと結果レポートで説明できるかを評価します。

## ドキュメント

- [ベンチマークを解くためのレギュレーション](docs/benchmark_regulation.md)
- [回答評価・採点側の説明](docs/evaluation_guide.md)
- [ツール計算理論](docs/calculation_theory.md)

## 構成

- `armbench/`: 断面、曲げ、ねじり、熱、アクセレランス、DOE、疑似RAGの実装
- `knowledge/public_past_failures.jsonl`: 解く側に公開する過去トラ知識
- `knowledge/public_generation_specs.json`: 解く側に公開する世代仕様DB
- `knowledge/hidden_oracle.json`: 採点側専用の期待観点
- `examples/`: 計算入力例、戦略レポート/結果レポートJSONひな形
- `scripts/generate_doe_report.py`: 裏DOE確認レポート生成
- `reports/`: DOE確認結果
- `tests/`: ユニットテスト

## 実行例

```bash
python3 -m armbench.cli examples/design_260mm.json
python3 -m armbench.cli examples/doe_5level.json
python3 -m armbench.knowledge_cli search "アルミ 社内基準 170MPa 許容応力" --top-k 5
python3 -m armbench.knowledge_cli specs --generation gen2
python3 -m armbench.evaluation_cli path/to/strategy_report.json
python3 -m armbench.evaluation_cli path/to/result_report.json
python3 -m armbench.evaluation_cli path/to/strategy_report.json path/to/result_report.json
```

## 公開MCP

解く側へ公開するMCPは、評価器の期待ツール名と同じ名前だけを登録する。

```bash
python3 -m armbench.public_mcp_server
```

公開ツール:

- `calculate_section`
- `calculate_bending`
- `calculate_torsion`
- `calculate_cost`
- `calculate_thermal_displacement`
- `calculate_accelerance`
- `run_doe`
- `search_failure_knowledge`
- `get_generation_specs`

評価ツール、裏DOE、`knowledge/hidden_oracle.json` は公開MCPに含めない。

## 開発

外部依存はPython標準ライブラリのみです。

```bash
python3 -m unittest discover -s tests
python3 scripts/generate_doe_report.py
```
