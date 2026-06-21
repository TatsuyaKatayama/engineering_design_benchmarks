# ツール計算理論

## 位置づけ

本ツール群は、片持ち梁の基礎式、単自由度振動近似、材料体積コスト計算を組み合わせた簡易・決定論モデルである。

材料DBの `yield_strength_mpa` は物性情報として保持するが、計算式には直接使わない。

## 共通記号

- `L`: アーム長さ
- `A`: 断面積
- `I`: 曲げ方向の断面二次モーメント
- `Z`: 曲げ断面係数
- `J`: ねじり定数
- `Zt`: ねじり断面係数
- `E`: ヤング率
- `G`: せん断弾性係数
- `rho`: 密度
- `F`: 先端静荷重
- `T`: 先端ねじりモーメント
- `m_tip`: 動的先端質量
- `zeta`: 減衰比

単位系は入力では主に `mm`, `g`, `MPa` を使い、曲げ・振動計算の内部では必要に応じてSI単位へ変換する。

## 材料

せん断弾性係数はポアソン比から計算する。

```text
G = E / (2 * (1 + nu))
```

材料コストはアーム体積から求めた自重に、材料単価を掛ける。

```text
volume = A * L
mass = volume * rho
cost = mass / 1000 * cost_per_kg
```

## 断面特性

### 中実丸棒

```text
A  = pi * d^2 / 4
I  = pi * d^4 / 64
Z  = I / (d / 2)
J  = pi * d^4 / 32
Zt = J / (d / 2)
```

### 中実矩形

曲げは高さ方向を強軸として扱う。

```text
A = b * h
I = b * h^3 / 12
Z = I / (h / 2)
```

ねじり定数は矩形断面の近似式を使う。`a` を長辺、`b` を短辺とする。

```text
r = b / a
J = a * b^3 * (1/3 - 0.21 * r * (1 - r^4 / 12))
Zt = J / (max(width, height) / 2)
```

### 中空丸棒

```text
di = do - 2t
A  = pi * (do^2 - di^2) / 4
I  = pi * (do^4 - di^4) / 64
Z  = I / (do / 2)
J  = pi * (do^4 - di^4) / 32
Zt = J / (do / 2)
```

### 中空矩形

```text
bi = bo - 2t
hi = ho - 2t
A  = bo * ho - bi * hi
I  = (bo * ho^3 - bi * hi^3) / 12
Z  = I / (ho / 2)
```

閉断面ねじりは薄肉閉断面の近似を使う。

```text
bm = bo - t
hm = ho - t
Am = bm * hm
J  = 4 * Am^2 / (2 * (bm + hm) / t)
Zt = J / (max(bo, ho) / 2)
```

### H型断面

フランジ2枚とウェブ1枚の合成断面として計算する。

```text
hw = h - 2 * tf
A  = 2 * bf * tf + tw * hw
y  = h / 2 - tf / 2
I  = 2 * (bf * tf^3 / 12 + bf * tf * y^2) + tw * hw^3 / 12
Z  = I / (h / 2)
```

開断面ねじりは板要素の和として近似する。

```text
J  = (2 * bf * tf^3 + hw * tw^3) / 3
Zt = J / max(tf, tw)
```

## 曲げ計算

片持ち梁に先端荷重 `F` と自重による等分布荷重 `w` がかかるモデルとする。

```text
w = arm_mass * g / L
delta_tip = F * L^3 / (3 * E * I) + w * L^4 / (8 * E * I)
M_max = F * L + w * L^2 / 2
sigma_max = M_max / Z
```

出力は以下。

- `tip_bending_deflection_mm`
- `max_bending_stress_mpa`

## ねじり計算

先端ねじりモーメント `T` を受ける一様断面棒として計算する。

```text
theta = T * L / (G * J)
tau_max = T / Zt
```

出力は以下。

- `twist_angle_rad`
- `twist_angle_deg`
- `max_shear_stress_mpa`

## 熱変位計算

一様温度変化による自由熱膨張のみを扱う。

```text
delta_thermal = L * alpha * delta_T
```

拘束熱応力、温度分布、他部品の熱ドリフトとの合成は計算しない。

## アクセレランス計算

片持ち梁先端の1次曲げを単自由度系として近似する。

```text
k = 3 * E * I / L^3
m_modal = m_tip + 0.236 * m_arm
c = 2 * zeta * sqrt(k * m_modal)
f1 = sqrt(k / m_modal) / (2 * pi)
```

各周波数 `f` で動剛性を計算し、変位コンプライアンスに `omega^2` を掛けてアクセレランスを求める。

```text
omega = 2 * pi * f
dynamic_stiffness = (k - m_modal * omega^2) + i * c * omega
displacement_per_force = 1 / abs(dynamic_stiffness)
accelerance = omega^2 * displacement_per_force
```

評価周波数範囲内で最大となる値と、そのピーク周波数を返す。

- `max_tip_accelerance_m_per_s2_per_n`
- `peak_frequency_hz`
- `first_bending_frequency_hz`

## DOE計算

`run_doe` は指定範囲を水準数で等分割し、全組み合わせを生成して各候補の計算結果を返す。

```text
value_i = lower + i * (upper - lower) / (levels - 1)
```

`run_doe` は候補生成と順問題計算だけを行う。

## モデル外の扱い

以下は計算モデル外としている。

- 根元締結部の局所応力集中
- 固定境界の柔らかさ
- センサー重心位置やケーブル取り回しのばらつき
- 加工後の反り、内角R、寸法ばらつき
- 熱変位と他部品ドリフトの合成
- 材料異方性、接着、疲労、座屈
