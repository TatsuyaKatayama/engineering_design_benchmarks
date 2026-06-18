# Precision Arm Benchmark Forward Tools

第3世代精密計測アームのベンチマークで使う、決定論的な順問題ツール群です。
この実装は高忠実度CAEではなく、隠し正解セットと自動採点器を安定して作るための一貫した簡易物理モデルです。

## モデル範囲

- 形状: 矩形中空の片持ち梁
- 入力単位: `mm`, `g`, `MPa`, `JPY`
- 出力単位: `mm`, `MPa`, `Hz`, `g`, `JPY`
- 外部依存: Python標準ライブラリのみ

## 実行例

```bash
cd precision_arm_benchmark
python3 -m armbench.cli examples/design_260mm.json
```

## 提供ソルバー

- `solve_structural`: 先端変形量、最大曲げ応力、安全係数
- `solve_vibration`: 1次固有振動数、50Hz時振幅伝達率
- `solve_economics`: アーム自重、材料コスト、加工込み概算コスト
- `solve_thermal`: 先端熱変位量
- `check_manufacturability`: 製造可能性チェック
- `evaluate_design`: 上記をまとめて実行

