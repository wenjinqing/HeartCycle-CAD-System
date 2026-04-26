# HeartCycle CAD System

<div align="center">

![HeartCycle Logo](docs/images/logo.png)

**基于机器学习与深度学习的冠心病风险预测智能平台**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.3-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.13+-FF6F00?logo=tensorflow&logoColor=white)](https://www.tensorflow.org/)
[![License](https://img.shields.io/badge/License-Academic-yellow)](LICENSE)

[在线演示](#) | [快速开始](#快速开始) | [文档](docs/README.md) | [API文档](#api文档)

</div>

---

## 📖 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [功能展示](#功能展示)
- [快速开始](#快速开始)
- [Docker部署](#docker部署)
- [项目结构](#项目结构)
- [API文档](#api文档)
- [开发指南](#开发指南)
- [性能指标](#性能指标)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 🎯 项目简介

HeartCycle CAD System 是一个**全栈医疗AI平台**，专注于冠状动脉疾病（Coronary Artery Disease, CAD）的智能风险预测与辅助诊断。系统整合了经典机器学习、深度学习和多模态融合技术，支持从临床表格特征和原始心电图（ECG）信号进行智能分析。

### 🎓 项目背景

- **应用场景**：临床辅助诊断、医学科研、健康管理、医学教育
- **项目类型**：毕业设计 / 医疗AI科研平台
- **开发规模**：~60,000行代码，20+功能页面，23个API模块
- **技术亮点**：多模态融合、可解释AI、异步任务队列、模型版本管理

### 🌟 为什么选择 HeartCycle？

✅ **完整的医疗AI工作流**：数据上传 → 特征提取 → 模型训练 → 预测分析 → 可解释性 → 报告生成  
✅ **多模态融合**：表格临床特征 + 原始ECG信号深度融合  
✅ **可解释性优先**：SHAP/LIME让AI决策透明化，符合医疗场景需求  
✅ **企业级工程实践**：异步任务、版本管理、系统监控、安全认证  
✅ **开箱即用**：Docker一键部署，完整的文档和示例数据

---

## ✨ 核心特性

### 🔐 用户管理与权限
- **JWT认证**：访问令牌 + 刷新令牌双重机制
- **四级权限**：管理员 / 医生 / 研究员 / 患者
- **安全防护**：IP限流（200次/分钟）+ 用户限流（1000次/小时）
- **审计日志**：完整的用户操作记录

### 🤖 智能预测
- **单样本预测**：实时风险评估，秒级响应
- **批量预测**：支持CSV文件批量处理
- **多模态预测**：表格特征 + ECG信号融合
- **风险分层**：低/中/高风险智能分级

### 🧠 模型训练
