# HeartCycle CAD System

<p align="center">
  <strong>基于机器学习的冠心病风险预测系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.3-green.svg" alt="Vue">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-red.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-Academic-yellow.svg" alt="License">
</p>

---

## 项目简介

HeartCycle CAD System 是一个基于 HeartCycle 数据集的智能冠心病（CAD）风险评估平台。系统采用前后端分离架构，集成机器学习模型训练、预测和 SHAP 可解释性分析功能。

### 核心特性

- **多种机器学习算法**：支持 LR、SVM、RF、XGBoost、LightGBM、Stacking、Voting 等 7 种算法
- **HRV 特征提取**：自动从 ECG 信号提取时域、频域、非线性特征
- **SHAP 可解释性**：基于 SHAP 的模型解释，直观展示特征贡献度
- **灵活的数据输入**：支持 CSV 特征文件或 H5 原始 ECG 数据
- **批量预测**：支持单样本和批量数据预测
- **PDF 报告导出**：一键生成预测报告

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + Element Plus + ECharts |
| **后端** | FastAPI + SQLAlchemy |
| **机器学习** | scikit-learn + XGBoost + LightGBM |
| **可解释性** | SHAP + LIME |
| **信号处理** | NeuroKit2 + SciPy + PyWavelets |

---

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- npm 或 yarn

### 1. 克隆项目

```bash
git clone https://github.com/your-username/heartcycle-cad-system.git
cd heartcycle-cad-system
```

### 2. 安装后端依赖

```bash
pip install -r requirements.txt
```

### 3. 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 启动前端服务

```bash
npm run serve
```

### 6. 访问系统

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:8080 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| API 文档 (ReDoc) | http://localhost:8000/redoc |

---

## 项目结构

```
heartcycle_cad_system/
├── backend/                    # 后端服务 (FastAPI)
│   ├── algorithms/             # 核心算法模块
│   │   ├── data_processing.py  # ECG 信号预处理
│   │   ├── feature_extraction.py # HRV 特征提取
│   │   └── model_training.py   # 模型训练与评估
│   ├── app/
│   │   ├── api/v1/             # REST API 接口
│   │   ├── core/               # 核心配置
│   │   ├── services/           # 业务逻辑层
│   │   └── main.py             # 应用入口
│   └── tests/                  # 单元测试
├── frontend/                   # 前端应用 (Vue 3)
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   ├── components/         # 通用组件
│   │   ├── services/           # API 服务
│   │   └── utils/              # 工具函数
│   └── public/                 # 静态资源
├── scripts/                    # 工具脚本
├── docs/                       # 文档
└── requirements.txt            # Python 依赖
```

---

## 主要功能

### 1. 模型训练

支持两种训练模式：

- **CSV 模式**：上传预处理好的特征 CSV 文件
- **H5 模式**：上传原始 ECG 数据（H5 格式），系统自动提取 HRV 特征

### 2. 风险预测

输入患者体征信息，系统返回：
- 冠心病风险概率
- 风险等级（低/中/高）
- SHAP 特征贡献度分析
- 健康建议

### 3. 可解释性分析

基于 SHAP 的模型解释：
- 单样本解释（瀑布图）
- 全局特征重要性
- 特征交互分析

---

## 支持的模型

| 模型 | 代码 | 说明 |
|------|------|------|
| 逻辑回归 | `lr` | 线性分类，可解释性强 |
| 支持向量机 | `svm` | 核方法，适合小样本 |
| 随机森林 | `rf` | Bagging 集成，稳定性好 |
| XGBoost | `xgb` | 梯度提升，性能优秀 |
| LightGBM | `lgb` | 轻量级提升，训练快速 |
| Stacking | `stacking` | 堆叠集成，精度高 |
| Voting | `voting` | 投票集成，鲁棒性强 |

---

## HRV 特征说明

### 时域特征

| 特征 | 说明 |
|------|------|
| `mean_rr` | 平均 RR 间期 (ms) |
| `sdnn` | RR 间期标准差 (ms) |
| `rmssd` | 连续 RR 间期差值均方根 (ms) |
| `pnn50` | RR 间期差异 >50ms 的百分比 (%) |
| `pnn20` | RR 间期差异 >20ms 的百分比 (%) |

### 频域特征

| 特征 | 说明 |
|------|------|
| `lf_power` | 低频功率 (0.04-0.15 Hz) |
| `hf_power` | 高频功率 (0.15-0.4 Hz) |
| `lf_hf_ratio` | LF/HF 比值 |

### 非线性特征

| 特征 | 说明 |
|------|------|
| `sd1`, `sd2` | Poincaré 图参数 |
| `sample_entropy` | 样本熵 |
| `approximate_entropy` | 近似熵 |

---

## API 接口

### 数据管理

```
POST   /api/v1/data/upload     # 上传文件
GET    /api/v1/data/files      # 获取文件列表
```

### 模型训练

```
POST   /api/v1/models/train    # 训练模型 (CSV)
POST   /api/v1/models/train/h5 # 训练模型 (H5)
GET    /api/v1/models/list     # 获取模型列表
```

### 预测

```
POST   /api/v1/models/predict       # 单样本预测
POST   /api/v1/models/predict/batch # 批量预测
```

### SHAP 解释

```
POST   /api/v1/shap/explain/instance # 单样本解释
POST   /api/v1/shap/explain/global   # 全局解释
```

---

## 配置说明

复制 `.env.example` 为 `.env` 并根据需要修改：

```bash
cp .env.example .env
```

主要配置项：

```env
# 数据库配置 (可选，默认使用 SQLite)
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/heartcycle_cad

# 应用配置
SECRET_KEY=your-secret-key-here
DEBUG=false
```

---

## 开发指南

### 运行测试

```bash
cd backend
pytest tests/ -v --cov=app
```

### 代码规范

- 后端：遵循 PEP 8 规范
- 前端：使用 ESLint 检查

---

## 许可证

本项目仅供学术研究使用。

---

## 致谢

- [HeartCycle Dataset](https://physionet.org/) - 数据来源
- [SHAP](https://github.com/slundberg/shap) - 可解释性分析
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Vue.js](https://vuejs.org/) - 前端框架

---

<p align="center">
  毕业设计项目 · 2025
</p>
