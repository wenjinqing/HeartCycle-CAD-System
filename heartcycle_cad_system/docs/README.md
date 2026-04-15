# HeartCycle 文档中心

说明类 Markdown 已按用途归档到本目录，仓库根目录仅保留项目主 `README.md` 与简短的 [`文档导航.md`](../文档导航.md) 入口。

---

## 使用与接口（`guides/`）

| 文档 | 说明 |
|------|------|
| [快速使用指南](guides/快速使用指南.md) | 快速上手与常见问题 |
| [前端操作手册](guides/前端操作手册.md) | 功能与操作说明 |
| [API 接口说明](guides/API.md) | REST API 文档 |
| [部署指南](guides/DEPLOYMENT.md) | 部署与环境 |
| [实验数据位置说明](guides/DATA_LOCATION_GUIDE.md) | 结果文件保存位置 |
| [重要提示（H5 等）](guides/README_重要提示.md) | 必读修复与注意事项 |

---

## 论文与实验（`thesis/`）

| 文档 | 说明 |
|------|------|
| [README_THESIS](thesis/README_THESIS.md) | 论文相关功能总览 |
| [THESIS_COMPLETE_GUIDE](thesis/THESIS_COMPLETE_GUIDE.md) | 完整使用指南 |
| [THESIS_IMPLEMENTATION_SUMMARY](thesis/THESIS_IMPLEMENTATION_SUMMARY.md) | 实现总结 |

---

## 项目历史与总结（`history/`）

| 文档 | 说明 |
|------|------|
| [PROJECT_SUMMARY](history/PROJECT_SUMMARY.md) | 项目总结 |
| [CHANGELOG](history/CHANGELOG.md) | 变更记录 |
| [FRONTEND_BACKEND_ALIGNMENT](history/FRONTEND_BACKEND_ALIGNMENT.md) | 前后端对齐 |
| [OVERFITTING_FIX_SUMMARY](history/OVERFITTING_FIX_SUMMARY.md) | 过拟合相关修复总结 |
| [STAGE1_SUMMARY](history/STAGE1_SUMMARY.md) … [STAGE5_COMPLETE_SUMMARY](history/STAGE5_COMPLETE_SUMMARY.md) | 各阶段总结 |

---

## 问题修复记录（`notes/`）

| 文档 | 说明 |
|------|------|
| [H5 上传问题快速修复](notes/H5上传问题快速修复.md) | H5 上传 |
| [H5 特征提取修复说明](notes/H5特征提取修复说明.md) | 特征提取 |
| [JWT 令牌过期修复说明](notes/JWT令牌过期修复说明.md) | 认证令牌 |
| [用户管理功能修复说明](notes/用户管理功能修复说明.md) | 用户管理 |
| [重置密码功能改进说明](notes/重置密码功能改进说明.md) | 重置密码 |

---

## 开发内部说明（`internal/`）

| 文档 | 说明 |
|------|------|
| [BACKEND_SERVICES_REFACTORING](internal/BACKEND_SERVICES_REFACTORING.md) | 后端 services 重构说明（原 `backend/app/services/README_REFACTORING.md`） |

---

## 其他位置（未移动）

- **测试数据说明**：[`测试数据/README.md`](../测试数据/README.md)
- **脚本说明**：[`scripts/README.md`](../scripts/README.md)

---

## 文档结构（仓库）

```
heartcycle_cad_system/
├── README.md                 # 项目主说明
├── 文档导航.md               # 指向本索引
├── docs/
│   ├── README.md             # 本文件
│   ├── guides/               # 使用、API、部署
│   ├── thesis/               # 论文相关
│   ├── history/              # 阶段总结与变更
│   ├── notes/                # 修复与排障记录
│   └── internal/             # 开发内部文档
├── 测试数据/
└── scripts/
```

---

**最后更新：** 2026-04-10
