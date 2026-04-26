# PTB-XL 多模态 CAD 检测：完整流程

> 这是为解决「HeartCycle 数据集没有 CAD 阳性样本，不能做二分类」问题而引入的
> **公开数据集替代方案**。流程基于 PhysioNet PTB-XL v1.0.3 (CC-BY 4.0)，
> 21,799 条 12 导联静息 ECG，含医生标注的 5 大诊断超类。

---

## 0. 为什么要做这个

| 数据集 | 规模 | CAD 阳/阴 | 模态 | 论文价值 |
|---|---|---|---|---|
| HeartCycle（私有） | 4 受试者 / 37 录音 | **0 / 37** | ECG/PCG/PPG/ECHO | ⚠️ 仅适合自监督预训练 |
| Z-Alizadeh Sani | 303 患者 | 216 / 87 | 仅表格 | ⭐⭐⭐ 已接入 ``zalizadeh_best.joblib`` |
| **PTB-XL** | 21,799 / 18,869 | **5,469 (MI) / 9,514 (NORM)** | 12 导联 ECG | ⭐⭐⭐⭐⭐ 直接对标 SOTA |

PTB-XL 是当前 ECG 深度学习论文的**事实标准基准**。

> 完整论文叙述链：
> *"采用 PTB-XL 公开数据集训练 1D-ResNet ECG 分支，在 strat-fold 9/10 上验证；
> 与 Z-Alizadeh Sani 真实临床表格分支做 late fusion，
> 同时利用 HeartCycle 健康人 ECG 数据做 mask-reconstruction 自监督预训练
> 提升表征质量。"*

---

## 1. 流程总览

```text
            ┌──────────────────────────┐
            │ download_ptbxl.py        │  (1.7 GB, 一次性)
            │   --mode python          │
            └────────────┬─────────────┘
                         ▼
            ┌──────────────────────────┐
            │ preprocess_ptbxl.py      │  scp_codes → MI/CAD 二分类
            │   生成 train/val/test    │
            └────────────┬─────────────┘
                         ▼
   ┌─────────────────────┴───────────────────────┐
   ▼                                             ▼
[可选] pretrain_heartcycle_ssl.py        train_ptbxl_ecg.py
       自监督预训练编码器  ─────────────►  --pretrained <ckpt> 迁移
       (HeartCycle 健康人)                       │
                                                 ▼
                                  data/models/ptbxl_ecg_resnet1d_best.h5
                                                 │
                                                 ▼
                              backend/app/services/ptbxl_multimodal_service.py
                              backend/app/api/v1/ptbxl_multimodal.py
                                  /api/v1/ptbxl-multimodal/predict
```

---

## 2. 一键起步（推荐顺序）

```bash
# 0. 进入项目根
cd heartcycle_cad_system

# 1. 装依赖（新增 wfdb / requests）
pip install -r requirements.txt

# 2. 下载 PTB-XL（约 1.7 GB；只下 100 Hz 子集 ≈ 800 MB 也够用）
python scripts/download_ptbxl.py --mode python --resolution 100

# 3. 预处理：MI/CAD 二分类标签 + 推荐 split
python scripts/preprocess_ptbxl.py --label-strategy mi_vs_norm

# 4.（可选）HeartCycle 自监督预训练
#    没有 H5 时也可用 PTB-XL NORM 子集冒充
python scripts/pretrain_heartcycle_ssl.py --use-ptbxl-norm \
    --epochs 30 --steps-per-epoch 100

# 5. 监督训练 ECG → CAD
python scripts/train_ptbxl_ecg.py --epochs 30 \
    --pretrained data/models/ssl_heartcycle_encoder.h5 \
    --freeze-backbone-epochs 5

# 6. 启动后端，验证多模态推理 API
python scripts/start_backend.py

# 7. 调用：
curl -X GET http://localhost:8000/api/v1/ptbxl-multimodal/status
```

---

## 3. 各步骤详解

### 3.1 download_ptbxl.py

四种下载模式：

| 模式 | 命令 | 说明 |
|---|---|---|
| `python` | `--mode python --resolution 100` | **跨平台首选**，断点续传，多线程 |
| `wget` | `--mode wget` | Linux/macOS 习惯 |
| `aws` | `--mode aws` | 走 PhysioNet 在 AWS S3 的镜像（最快） |
| `mock` | `--mode mock --mock-records 8` | 仅 8 条假数据，给 CI 用 |

下载完后建议 `--verify` 抽 50 个文件做 SHA256 校验。

### 3.2 preprocess_ptbxl.py

把每条记录的 ``scp_codes`` 字典聚合到 5 个 superclass，再按策略二分类：

| `--label-strategy` | 阳性 | 阴性 | 说明 |
|---|---|---|---|
| `mi_vs_norm` (默认) | MI | NORM | 最经典 CAD 检测 |
| `cad_vs_norm` | MI ∪ STTC | NORM | 含心肌缺血迹象 |
| `abnormal_vs_norm` | 所有异常 | NORM | 最宽 |

输出三个 CSV + 一个 ``summary.json``，记录每个策略下的样本统计供论文复盘。

### 3.3 train_ptbxl_ecg.py

主架构：1D-ResNet18 风格

```text
Input(1000, 12) → Conv1D(64, 15, /2) → BN → ReLU → MaxPool(2)
                → 4× ResBlock (64 → 128 → 256 → 512), 每块 stride=2
                → GlobalAvgPool → Dropout → Dense(1, sigmoid)
```

关键回调：

- ``ModelCheckpoint`` ：`val_auc` 最大时保存
- ``EarlyStopping`` ：8 epoch 无提升提前停
- ``ReduceLROnPlateau``：4 epoch 无下降折半 LR
- 自动 `class_weight` 处理类别不平衡

输出在 ``data/models/ptbxl_ecg_resnet1d_best.h5`` 和元信息 JSON。

### 3.4 pretrain_heartcycle_ssl.py（可选）

任务：**Mask Reconstruction**——随机遮盖 ECG 15% 片段（每段 50 samples），让模型重构。

预训练后用 ``--pretrained <encoder.h5>`` 迁移到监督任务，配合
``--freeze-backbone-epochs 5`` 做"线性 probe + 全量微调"两段式。

### 3.5 推理 API

```
GET  /api/v1/ptbxl-multimodal/status
GET  /api/v1/ptbxl-multimodal/fusion-methods
POST /api/v1/ptbxl-multimodal/predict
```

请求体：

```json
{
  "ecg": {
    "signal": [[v_t1_lead1, ..., v_t1_lead12], ..., [v_t1000_lead1, ..., v_t1000_lead12]],
    "fs": 100
  },
  "tabular": {
    "Age": 55, "Weight": 70, ... ,
    "Typical Chest Pain": 1
  },
  "fusion": "weighted"
}
```

ECG 与 tabular 至少提供一个。响应：

```json
{
  "success": true,
  "data": {
    "branches": {
      "ecg":     {"p_positive": 0.812, "model": "PTBXL_ECG_ResNet1D", ...},
      "tabular": {"p_positive": 0.734, "model": "RandomForest", ...}
    },
    "fusion_method": "weighted",
    "fusion_weights": {"w_ecg": 0.41, "w_tab": 0.40, ...},
    "p_positive": 0.781,
    "prediction": 1,
    "risk_level": "中-高风险"
  }
}
```

---

## 4. 论文里的可写实验（建议章节）

| 章节 | 表/图 | 内容 |
|---|---|---|
| 4.1 数据集 | Table 1 | PTB-XL 标签策略对比（mi_vs_norm / cad_vs_norm / abnormal_vs_norm） |
| 4.2 单模态 baseline | Table 2 | ECG-only (1D-ResNet) AUC vs Tabular-only (RandomForest) AUC |
| 4.3 自监督收益 | Figure | with/without HeartCycle SSL 预训练的 val_auc 收敛曲线对比 |
| 4.4 多模态融合 | Table 3 | mean / weighted / logit_mean / max / min 五种 late fusion 策略 |
| 4.5 消融 | Table 4 | 去掉某些 SCP 码（如 STTC）对 AUC 的影响 |
| 4.6 临床可解释 | Figure | Saliency / Grad-CAM 在 12 导联上的关注热图 |

---

## 5. 学术诚信声明（论文必须写）

1. **不再使用 ``np.random.randint`` 生成标签**——这是 ``multimodal_service.py``
   ``strict_labels=True`` 默认行为强制保证的。
2. PTB-XL 数据来源、版本、DOI、许可证（CC-BY 4.0）必须在论文 Data Availability 章节注明。
3. HeartCycle 数据仅用作**无监督预训练**，不参与 CAD 阳/阴判定，
   论文中应明确这一点。
4. 三个数据集（PTB-XL、Z-Alizadeh、HeartCycle）**没有患者重叠**，
   late fusion 的输入是同一名患者的两类**特征空间**而非"配对样本"——
   论文里应清楚区分 *paired multimodal* 和 *score-level late fusion* 两个概念。

---

## 6. 故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `wfdb.io.record._FmtError: cannot read .dat` | 文件损坏 / 部分下载 | `python scripts/download_ptbxl.py --verify` |
| `OOM during model.fit` | batch 太大 | `--batch-size 32` 或 `--resolution 100` |
| GPU 占满但 CPU 闲置 | TF data 瓶颈 | 把数据预加载到内存（`cache_in_memory=True`，默认开） |
| `ImportError: wfdb` | 依赖未装 | `pip install wfdb` |
| Windows 下中文输出乱码 | `PYTHONIOENCODING` 没设 | `set PYTHONIOENCODING=utf-8` 或用 PowerShell `chcp 65001` |

---

## 7. 引用

```bibtex
@article{Wagner2020,
  author  = {Wagner, Patrick and Strodthoff, Nils and Bousseljot, Ralf-Dieter and
             Kreiseler, Dieter and Lunze, Fatima I. and Samek, Wojciech and Schaeffter, Tobias},
  title   = {{PTB-XL}, a large publicly available electrocardiography dataset},
  journal = {Scientific Data},
  volume  = {7},
  pages   = {154},
  year    = {2020},
  doi     = {10.1038/s41597-020-0495-6}
}
```
