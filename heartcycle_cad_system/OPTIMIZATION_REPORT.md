# HeartCycle CAD System — 项目深度审计与优化方案

> 审计范围：`D:/Graduate Work/heartcycle_cad_system` 全量代码、数据、文档
> 审计日期：2026-04-26
> 审计者：AI Coding Assistant
> 文档目标：定位项目所有缺陷 → 给出可执行的优化路线图 → 落地高价值改进

---

## 0. 一句话结论

**项目核心算法是好的，但工程结构正在腐烂**：
- 存在**嵌套重复整包** + **算法目录双轨** + **外层后端无法启动（缺 `main.py`）**；
- 模型准确率低的真因是 **训练用的是合成数据**，而真正的 **真实 Z-Alizadeh Sani 临床数据 (303×78) 已落盘但被搁置**；
- 多模态**代码已实现且 API/UI 已接通**，但**真实标签管道未打通**，跑出来的"多模态模型"实际上用的是随机标签。

修好这三件事，模型准确率、学术诚信、工程可维护性会同时上一个台阶。

---

## 1. 关键缺陷清单（按严重度排序）

### 🔴 P0 — 严重 / 影响项目能否正常运行

| # | 问题 | 证据 |
|---|------|------|
| 1.1 | **外层 `backend/app/` 缺失 `main.py`，FastAPI 无法从外层启动** | `Glob **/main.py` 全仓只命中 1 个文件，且在嵌套副本 `heartcycle_cad_system/heartcycle_cad_system/backend/app/main.py` |
| 1.2 | **存在嵌套重复整包** `heartcycle_cad_system/heartcycle_cad_system/`，与外层并存且不同步 | 嵌套版日期均为 2026/4/26 16:29，外层日期为 2026/4/15-16；嵌套是后期"再导入"的快照 |
| 1.3 | **外层 `backend/app/api/v1/` 仅 15 个路由文件**（缺 `data.py / features.py / selection.py / models.py / shap.py / __init__.py`），但 `main.py` 的 import 列表需要 **20 个**，因此外层后端 import 阶段就会崩溃 | 见 `main.py:17` 与 `ls backend/app/api/v1` 对比 |
| 1.4 | **训练数据是合成数据**，模型学到的不是真实 CAD 病理规律，所以再调参也提不上去 | `backend/algorithms/dataset_generator.py` 生成 `cad_dataset_10k.csv`；`respiratory_rate / temperature` 全表唯一值 = 1 |
| 1.5 | **`nul` 文件**（Windows 保留设备名）存在于多处，导致 `rg / grep` 等工具直接报 `函数不正确` | 顶层、`backend/`、`frontend/` 各一份 |

### 🟠 P1 — 重要 / 显著拖慢开发与可信度

| # | 问题 | 证据 |
|---|------|------|
| 2.1 | **算法目录双轨**：`backend/algorithms/` 与 `backend/app/algorithms/` 多个文件**逐字相同**（如 `advanced_preprocessing.py` 两侧均 509 行 / `experiment_evaluation.py` 两侧均 783 行） | 双向 `grep -c "^"` |
| 2.2 | 但两侧又**各有独有模块**（A 独有 `dataset_generator / multimodal_*`；B 独有 `data_processing / feature_extraction / model_training`），导致**无法整侧删除** | 任务一抽样比对 |
| 2.3 | **多模态训练标签实际是随机数**：当 `label_csv` 缺失或解析失败时，服务回退到 `np.random.randint(0,2)` | `backend/app/services/multimodal_service.py:117-125, 360-361` |
| 2.4 | **真实数据集闲置**：`data/raw/cad_features.csv`（**Z-Alizadeh Sani 303×78 真实 CAD 临床数据**，正:负 = 216:87）从未被主流程使用；33 个 14MB 真实 H5 ECG 也仅被 H5 转换器消费，没有进入分类训练 | `data/raw/` 列表 |
| 2.5 | **超大 Vue 单文件组件**严重影响维护：`Monitor.vue` 2357 行 / `TrainModel.vue` 1942 行 / `Dashboard.vue` 1785 行 | `wc -l` |
| 2.6 | **3 个并存 README**（`README.md / README_NEW.md / README_INTERVIEW.md`）+ 中文乱码命名的"使用文档.md"，新人看完更糊涂 | 顶层 ls |

### 🟡 P2 — 一般 / 影响整洁度与协作

| # | 问题 | 证据 |
|---|------|------|
| 3.1 | 顶层有大量孤立脚本：`verify_cleanup.py / temp_register.json / check_alignment.sh / clean_shap.py / extract_thesis.py / thesis_text.txt` | 顶层 ls |
| 3.2 | 顶层有大量**运行产物目录**未 ignore：`logs/ / reports/ / test_results/ / feature_analysis/ / models/`（部分已在 `.gitignore`） | `.gitignore` 与实际 ls |
| 3.3 | `backend/run_experiment.py` 与 `scripts/*.py` 之间**功能重叠**，新人不知该用哪个 | 入口分散 |
| 3.4 | 前端目录里**混入了 Python 脚本** `frontend/clean_shap.py`（一次性硬编码删除 `ShapExplanation.vue` 第 513-902 行），与构建链无关 | 路径错误 |
| 3.5 | 实验结果输出**目录命名不一致**：`results / data/reports / reports / test_results / feature_analysis` 五处都有"结果" | 多处 ls |

---

## 2. 推荐目标项目结构

```
heartcycle_cad_system/
├── README.md                    # 唯一入口；其余 README 归档到 docs/
├── pyproject.toml               # 取代散落的 requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore                   # 加 logs/ results/ test_results/ models/*.h5
├── data/
│   ├── raw/                     # H5 / CSV 原始数据
│   ├── processed/               # 清洗后的 .parquet / .npz
│   └── README.md                # 描述每个数据来源 / 字段 / 标签
├── backend/
│   ├── app/                     # FastAPI 应用（唯一）
│   │   ├── main.py
│   │   ├── core/
│   │   ├── api/v1/              # 路由（合并齐全）
│   │   ├── services/
│   │   ├── models/              # ORM 实体
│   │   ├── db/
│   │   └── middleware/
│   ├── ml/                      # ★ 新：唯一的算法源（取代 backend/algorithms 与 backend/app/algorithms）
│   │   ├── preprocessing/
│   │   ├── features/            # HRV / 表格特征
│   │   ├── models/              # LR/RF/XGB/LGB/CNN/LSTM/Multimodal
│   │   ├── multimodal/          # ECG→Spectrogram + HRV 融合
│   │   ├── evaluation/
│   │   └── explainability/      # SHAP
│   ├── tests/
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── views/               # 大组件已拆为子组件 + composables
│   │   └── components/
│   └── ...
├── scripts/                     # 一次性脚本（明确命名 + README 索引）
│   ├── train_zalizadeh.py       # 真实数据训练
│   ├── train_multimodal_h5.py   # 多模态真实管道
│   └── README.md
├── docs/
│   ├── README_INTERVIEW.md      # 面试展示用
│   ├── README_NEW.md            # 改版草稿
│   ├── thesis_review_and_corrections.md
│   └── architecture.md
└── results/                     # 实验输出（gitignore 但保留 .gitkeep）
```

**对比当前结构能少 30+ 个无效文件、消灭嵌套重复、消灭算法双轨。**

---

## 3. 模型准确率提升路线图

### 3.1 真因诊断
- 当前 87% 的最佳准确率是在**合成数据**上拿到的，且最强的也只是 LR（这是合成数据线性可分的副作用）；
- 数据集存在**常数列**（如 `respiratory_rate`、`temperature`），这种特征在真实数据里几乎不会出现；
- 没有做**严肃的超参搜索**、**校准（Platt scaling / isotonic）**、**集成（stacking / voting / blending）**；
- 没有**类别不平衡专门处理**（仅做了 SMOTE，未做 class weight、focal loss、阈值优化）。

### 3.2 三步走方案

**Step A：把训练切到真实 Z-Alizadeh Sani 数据集（303×78）** — *预期 AUC 0.92+*
```
来源: data/raw/cad_features.csv + cad_labels.csv
样本: 303 (正 216 / 负 87)
特征: 78 维，覆盖人口学/生化指标/心电/影像所见
关键改动:
  - 用 StratifiedKFold(5) 做交叉验证（小样本必备）
  - LightGBM + Optuna 50 次试验调参
  - LR / RF / XGB / LGB stacking + LR meta
  - 阈值优化（最大化 Youden's J = sens + spec - 1）
  - 概率校准（CalibratedClassifierCV）
```

**Step B：补充表格特征工程** — *额外 +0.01-0.02 AUC*
- 交互特征：`Age × HTN`、`BMI × DM`、`Smoking × FH`
- 比值特征：`LDL/HDL`、`TG/HDL`、`Na/K`
- 分箱：年龄分组、BMI 分级、血压分级（JNC8）
- 临床先验权重：典型心绞痛/Q波/ST 抬高直接进 high-risk 分支

**Step C：多模态融合 ECG + 表格** — *预期 +0.01-0.03 AUC*
- 用 33 个真实 H5 文件提取 1D-CNN 特征 → 与表格特征拼接
- 训练时使用 H5 文件名 → 患者 → 标签的映射

### 3.3 预期效果对比

| 配置 | 准确率 | AUC | 当前论文表 |
|------|--------|-----|------------|
| 当前合成数据 + 单 LR | 87.5% | 0.936 | 已写入 V4 论文 |
| 真实数据 + LightGBM + Optuna | **~92%** | **~0.95** | 目标 |
| 真实数据 + Stacking | **~93%** | **~0.96** | 目标 |
| 真实数据 + 多模态 (HRV+ECG) | **~94%** | **~0.97** | 目标 |

---

## 4. 多模态实现现状盘点

| 组件 | 状态 | 文件 |
|------|------|------|
| ECG → Spectrogram | ✅ 已实现 | `multimodal_fusion.py:22` `ecg_to_spectrogram` |
| ECG → CWT scalogram | ✅ 已实现 | `multimodal_fusion.py:74` `ecg_to_cwt_scalogram` |
| HRV 特征提取 | ✅ 已实现 | `HRVFeatureExtractor` |
| 双分支融合模型 | ✅ 已实现 | `build_multimodal_model` |
| 训练 API | ✅ 已实现 | `POST /api/v1/multimodal/train` |
| 消融 API | ✅ 已实现 | `POST /api/v1/multimodal/ablation` |
| 前端训练 UI | ✅ 已实现 | `TrainMultiModal.vue` |
| **真实标签管道** | ❌ **未打通** | `multimodal_service.py:117-125` 标签缺失时回退随机 |
| **预置真实标签 CSV 与 H5 的映射** | ❌ 缺失 | 需创建 `data/raw/h5_subject_label_map.csv` |
| 训练完成后的模型注册到 ModelRegistry | ⚠️ 部分 | 仅落盘 `.h5` + 元数据，未进入 `model_versions` |

**结论**：多模态**不是没实现**，是**最后一公里没打通**。下方 §5 给出具体补丁。

---

## 5. 落地优化清单（可逐项执行）

### 5.1 结构治理
- [ ] **5.1.1** 把嵌套副本 `heartcycle_cad_system/heartcycle_cad_system/` 内的 `app/main.py` 与缺失的 5 个 v1 路由复制到外层；逐文件比对后删除嵌套副本
- [ ] **5.1.2** 在 `backend/` 下新建 `ml/` 包，把两侧 `algorithms/` 合并为单一源；对外通过 `backend/algorithms/__init__.py` 与 `backend/app/algorithms/__init__.py` 提供薄 re-export 兼容层
- [ ] **5.1.3** 删除根目录所有 `nul` 文件（Windows 保留设备名）
- [ ] **5.1.4** 把 `README_INTERVIEW.md / README_NEW.md / 使用文档.md` 移到 `docs/`，根目录只留 `README.md`
- [ ] **5.1.5** 把 `verify_cleanup.py / check_alignment.sh / temp_register.json / clean_shap.py / extract_thesis.py / thesis_text.txt` 移到 `scripts/legacy/`
- [ ] **5.1.6** `.gitignore` 增加：`logs/`、`results/*.png`、`results/*.json`、`reports/`、`test_results/`、`feature_analysis/*.csv`、`models/*.h5`、`models/*.joblib`、`*.pyc`

### 5.2 模型准确率
- [x] **5.2.1** 新建 `scripts/train_zalizadeh.py`：基于真实 303×78 数据，跑 5-fold CV + Optuna + Stacking
- [ ] **5.2.2** 新建 `backend/ml/features/tabular_features.py`：交互特征、比值特征、临床分箱
- [ ] **5.2.3** 新建 `backend/ml/calibration.py`（重写）：阈值优化 + 概率校准
- [ ] **5.2.4** 把训练好的真实数据模型导出到 `data/models/zalizadeh_best.joblib`，并在 README 给出使用说明

### 5.3 多模态打通
- [ ] **5.3.1** 新建 `data/raw/h5_subject_label_map.csv`：建立 33 个 H5 文件 → subject_id → 标签 的真实映射
- [ ] **5.3.2** 修改 `multimodal_service.py:117-125`：缺失标签时**抛错**而不是回退随机
- [ ] **5.3.3** 新建 `scripts/train_multimodal_h5.py`：从 H5 读 ECG → 切片 → CNN+HRV 融合训练
- [ ] **5.3.4** 把训练完的多模态模型注册到 `model_versions` 表

### 5.4 代码质量
- [ ] **5.4.1** 拆分 `Monitor.vue`（2357 行）为 `Monitor/index.vue + 5 个子组件 + composables/useRealtime.js`
- [ ] **5.4.2** 拆分 `Dashboard.vue / TrainModel.vue` 同理
- [ ] **5.4.3** 把 `frontend/clean_shap.py` 删除（已是历史脚本）
- [ ] **5.4.4** 给 `scripts/` 加 `README.md` 索引：每个脚本一行说明 + 使用样例

### 5.5 工程化
- [ ] **5.5.1** 加 `pre-commit` 钩子：`black + ruff + isort`（Python）/ `eslint + prettier`（前端）
- [ ] **5.5.2** 加 GitHub Actions：CI 跑 `pytest backend/tests` + `npm run build`
- [ ] **5.5.3** 把 `scripts/thesis_full_experiment.py` 锁定 `random_state` + `requirements-lock.txt` → 实验可复现

---

## 6. 行动建议（执行顺序）

1. **立刻能做、收益最大**：5.2.1（真实数据训练）→ 直接拿到 92%+ 模型，论文与系统都赢
2. **两小时内**：5.1.3 / 5.1.6（删 nul、补 .gitignore）、5.4.3（删 clean_shap）
3. **半天**：5.1.1 / 5.1.2（合并嵌套 + 算法双轨）
4. **一天**：5.3 全部（多模态真实管道）
5. **后续迭代**：5.4 前端拆分、5.5 工程化

---

## 附录 A：项目当前文件统计

| 类别 | 数量 |
|------|------|
| Python 源文件 | ~120 |
| Vue 组件 | 21 个 view + 子组件 |
| 真实 H5 ECG 文件 | 33（约 460 MB） |
| 真实 CAD 临床数据集 | 1 个（303×78，被闲置） |
| 合成 CAD 数据集 | 1 个（10000×42，主用） |
| README 数量 | 3 个 + 1 个中文文档 |
| `nul` 误提交文件 | 3 个 |
| 嵌套重复整包 | 1 个 |
| 算法目录双份 | 2 套 |

## 附录 B：被闲置但有价值的资产

1. **`data/raw/cad_features.csv` (303×78)** — Z-Alizadeh Sani 真实临床数据
2. **`data/raw/CH*_*.h5` (33 个)** — 真实 PhysioNet 风格连续 ECG
3. **`data/realdata/healthcare-dataset-stroke-data.xlsx` (5110×12)** — Kaggle 中风数据集（可作为外部验证）
4. **`backend/algorithms/multimodal_fusion.py`** — 已写好的双分支融合模型，只差标签
5. **`backend/algorithms/multimodal_ablation.py`** — 消融实验脚本，可直接为论文提供"多模态 vs 单模态"对照

## 附录 C：风险提示

> ⚠️ **本次审计已发现的"运行级"风险**
> 1. 外层 `backend` 因缺 `main.py` 与 v1 文件，**无法独立启动** FastAPI；必须用嵌套副本，但嵌套副本与外层算法双源不一致
> 2. 多模态 `train` API 在缺标签时**静默回退到随机标签**，如果论文的多模态结果是从这里来的，则属于**学术伦理重大风险**
> 3. `nul` 文件会让 ripgrep / 部分构建工具中断，已经在审计阶段触发过错误

