# `scripts/` — 命令行脚本索引与启动指南

本目录包含所有**脱离 FastAPI 服务**也能跑的命令行工具，按用途分组。

> 法定运行目录：**项目根 `heartcycle_cad_system/`**（不是 `scripts/` 内部）。
> 所有 `python scripts/xxx.py` 都假设你在根目录敲。

---

## 1. 启动后端服务（最常用）

| 脚本 | 用途 |
| --- | --- |
| `start_backend.py` | Python 启动器：自动检测端口（8000 起 / 自动跳到 8001-8009）、附带热重载 |
| `start_backend.bat` (Windows) | 双击运行的 Windows 包装 |

```powershell
python scripts/start_backend.py
# → http://localhost:8000/docs
```

---

## 2. 模型训练（**真实数据 ⭐**）

| 脚本 | 数据源 | 输出 |
| --- | --- | --- |
| **`train_zalizadeh.py`** | Z-Alizadeh Sani 真实临床数据集（303×78） | `data/models/zalizadeh_best.joblib`<br>`results/zalizadeh_results.{json,md}`<br>`results/zalizadeh_{roc,confusion,shap_top15}.png` |
| **`train_ptbxl_ecg.py`** ⭐ 多模态 | PTB-XL 公开 12 导联 ECG (21,799 条) | `data/models/ptbxl_ecg_resnet1d_best.h5` + meta JSON |
| **`pretrain_heartcycle_ssl.py`** | HeartCycle 健康人 ECG（自监督预训练源） | `data/models/ssl_heartcycle_encoder.h5` |
| **`download_ptbxl.py`** | PhysioNet 在线 → 本地缓存 | `data/ptbxl/{ptbxl_database.csv,records100/,records500/}` |
| **`preprocess_ptbxl.py`** | `data/ptbxl/` → 标签聚合 + split | `data/ptbxl_processed/{train,val,test}.csv` + `summary.json` |
| `train_from_h5.py` | HeartCycle H5 ECG 信号 | `data/models/h5_*.joblib` |
| `train_model.py` | 通用 CSV 特征 → 任意模型类型（lr / rf / xgb / lgb 等） | `data/models/<model_type>_*.joblib` |
| `thesis_full_experiment.py` | 论文全套实验流水线（HRV+ECG 多模型对比） | `results/thesis_*.{json,md,png}` |
| `repro_thesis_metrics.py` | 锁种子复现论文表格 | `results/thesis_repro_*.json` |
| `build_thesis_v4.py` | 论文最终版本结果汇总图表 | `results/thesis_v4*` |

### 推荐：用真实数据训练

```powershell
python scripts/train_zalizadeh.py
# 输出：RandomForest 测试集 AUC ≈ 0.9044, 灵敏度 ≈ 0.97
```

跑完后，FastAPI 端的 `/api/v1/clinical-cad/predict` 会**自动**加载这份模型——不需要重启服务（懒加载）。

### 多模态：PTB-XL ECG 公开数据集流程

完整流程见 [docs/PTBXL_PIPELINE.md](../docs/PTBXL_PIPELINE.md)：

```powershell
# 一次性下载（1.7 GB；只要 100 Hz 子集 ≈ 800 MB）
python scripts/download_ptbxl.py --mode python --resolution 100

# 标签策略（mi_vs_norm 是 PTB-XL 上最经典的 CAD 设置）
python scripts/preprocess_ptbxl.py --label-strategy mi_vs_norm

# 训练 1D-ResNet ECG → CAD（≈30 epochs，自动 EarlyStopping）
python scripts/train_ptbxl_ecg.py --epochs 30
```

> 训练完毕后 `/api/v1/ptbxl-multimodal/predict` 会懒加载，
> 与 Z-Alizadeh 表格分支做 late fusion（mean / weighted / logit_mean / max / min 五种）。

---

## 3. 数据预处理 / 特征工程

| 脚本 | 用途 |
| --- | --- |
| `extract_all_h5_features.py` | 批量从 H5 提取 HRV + 临床特征 → CSV |
| `generate_complete_features.py` | 给定 H5 列表生成完整特征矩阵 |
| `analyze_h5_quality.py` | H5 文件信号质量统计（采样率、缺失通道、SNR） |
| `analyze_feature_importance.py` | 离线 SHAP / 排列重要性分析 |
| `check_h5_structure.py` | 打印某个 H5 的内部 group/dataset 树 |
| `convert_matlab_h5.py` | MATLAB v7.3 .mat → .h5 |
| `export_cad_xlsx_for_training.py` | 把 SQLite 内的患者数据导出为可训练 Excel |
| `generate_training_data.py` / `generate_test_data.py` | 占位用合成数据生成器（**已弃用**：现在请用 `train_zalizadeh.py` 跑真实数据） |

---

## 4. 验证 / 冒烟测试

| 脚本 | 用途 |
| --- | --- |
| **`smoke_import_all.py`** | 一键校验：FastAPI 主应用 + 算法兼容 shim + 真实数据推理服务全可用 |
| **`smoke_test_zalizadeh_inference.py`** | 单独验证 `zalizadeh_best.joblib` 推理服务（用真实样本走预测，命中率应是 5/5） |
| **`smoke_test_ptbxl_pipeline.py`** | PTB-XL 端到端管线（mock 数据，不联网，几秒）：下载→预处理→数据加载→模型构建→SSL→融合服务→路由 |
| `verify_optimizations.py` | 验证一系列模型优化项是否生效 |
| `test_h5_extraction.py` | 验证 H5 → 特征提取流水线 |
| `quick_test.py` | 最简单的「能不能 import 主要模块」测试 |

```powershell
# 改完代码后强烈建议先跑这三个：
python scripts/smoke_import_all.py
python scripts/smoke_test_zalizadeh_inference.py
python scripts/smoke_test_ptbxl_pipeline.py
```

---

## 5. legacy/

`scripts/legacy/` 存放历史遗留、已被新脚本替代的脚本，仅作参考、**不再维护**：

- `check_alignment.sh` — 早期目录一致性检查（已由新结构淘汰）
- `verify_cleanup.py` — 一次性清理脚本
- `frontend/clean_shap.py` — 前端 SHAP 缓存清理脚本

---

## 端口被占用？

启动器会自动从 8000 → 8009 顺次试。全部被占的话：

```powershell
# Windows
netstat -ano | findstr :8000
taskkill /F /PID <PID>

# 或手动指定端口
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

启动后入口：

| 服务 | 地址 |
| --- | --- |
| Swagger 交互文档 | <http://localhost:8000/docs> |
| ReDoc 文档 | <http://localhost:8000/redoc> |
| 健康检查 | <http://localhost:8000/health> |
| 性能指标 | <http://localhost:8000/metrics> |
| **真实数据 CAD 推理** | <http://localhost:8000/api/v1/clinical-cad/predict> |
| **PTB-XL 多模态** | <http://localhost:8000/api/v1/ptbxl-multimodal/predict> |

---

## 生产部署

```bash
# Gunicorn + Uvicorn worker
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

或参考 `docker-compose.yml` 直接 `docker compose up`。

---

## 相关文档

- 顶层说明：[`../README.md`](../README.md)
- 项目审计 / 优化报告：[`../OPTIMIZATION_REPORT.md`](../OPTIMIZATION_REPORT.md)
- 部署 / API 详细说明：[`../docs/`](../docs/)
