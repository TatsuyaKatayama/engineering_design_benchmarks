# Precision Arm Benchmark 公開実行パッケージ

精密計測アームの基本設計ベンチマークに取り組むための公開実行パッケージです。
公開されたレギュレーション、計算ツール、疑似RAGデータを使い、要求制約を満たす最小材料コストの設計案を検討してください。

## すぐ始める

このディレクトリをカレントディレクトリにして実行します。

```bash
python3 -m armbench_public.cli examples/design_260mm.json
python3 -m armbench_public.cli examples/doe_5level.json
python3 -m armbench_public.knowledge_cli search "アルミ 社内基準 許容応力" --top-k 5
python3 -m armbench_public.knowledge_cli specs --generation gen2
python3 -m armbench_public.public_mcp_server
```

## 公開ドキュメント

- [ベンチマークを解くためのレギュレーション](docs/benchmark_regulation.md)
- [ツール計算理論](docs/calculation_theory.md)

## 公開データ

- `knowledge/public_past_failures.jsonl`: 過去トラ知識の疑似RAGデータ
- `knowledge/public_generation_specs.json`: 世代仕様DB
- `examples/strategy_report_template.json`: 戦略レポートひな形
- `examples/result_report_template.json`: 結果レポートひな形

## 公開MCPツール

- `calculate_section`
- `calculate_bending`
- `calculate_torsion`
- `calculate_cost`
- `calculate_thermal_displacement`
- `calculate_accelerance`
- `run_doe`
- `search_failure_knowledge`
- `get_generation_specs`

## 提出物

以下の2つのJSONを提出してください。

- 戦略レポート: `examples/strategy_report_template.json` の形式
- 結果レポート: `examples/result_report_template.json` の形式

回答には、採用した基準値、出典、使用ツール、候補比較、棄却理由、採用理由を含めてください。
