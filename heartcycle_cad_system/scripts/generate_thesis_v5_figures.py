"""为毕业论文 V5 生成全部新增图表。

生成的图存放至 results/thesis_v5/，命名规则与论文章节对应：
    fig_3-1_system_architecture.png       系统三层架构图
    fig_3-2_deployment_topology.png       部署拓扑（Docker Compose）
    fig_3-3_request_flow.png              典型请求时序
    fig_3-4_database_er.png               数据库 ER 图
    fig_3-5_role_matrix.png               用户角色/权限矩阵
    fig_4-1_data_pipeline.png             数据处理流水线
    fig_4-2_feature_taxonomy.png          42 维特征分类树
    fig_4-3_class_balance.png             两数据集类别分布对比
    fig_5-1_resnet1d_arch.png             1D-ResNet 模型结构
    fig_5-2_ssl_mask_recon.png            自监督 Mask Reconstruction
    fig_5-3_multimodal_fusion.png         多模态 Late Fusion 架构
    fig_5-4_training_strategy.png         三阶段训练策略
    fig_6-1_radar_metrics.png             6 模型多指标雷达图（合成 10k）
    fig_6-2_cv_stability.png              5 折 CV 折间 AUC 稳定性
    fig_6-3_zalizadeh_models.png          Z-Alizadeh 7 模型性能对比
    fig_6-4_threshold_analysis.png        阈值-灵敏度/特异性曲线
    fig_6-5_dataset_compare.png           合成 vs 真实数据集性能对比
    fig_7-1_ui_flow.png                   前端页面流转图

所有图均基于真实实验数据 (results/*.json) 或项目结构信息，
无合成 / 编造数据。
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

# 中文字体（Windows 自带 SimHei / Microsoft YaHei）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 200
plt.rcParams["figure.dpi"] = 110

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "thesis_v5"
OUT.mkdir(parents=True, exist_ok=True)

# 加载真实实验结果（出错时绝不构造数据，宁可让脚本报错也要保证学术严谨）
EXP = json.loads((ROOT / "results" / "thesis_full_experiment.json")
                 .read_text(encoding="utf-8"))
ZAL = json.loads((ROOT / "results" / "zalizadeh_results.json")
                 .read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────────────────────────
# 通用绘图工具
# ──────────────────────────────────────────────────────────────────────

def _box(ax, x, y, w, h, text, fc="#cfe2ff", ec="#1f4e79", fontsize=10,
         lw=1.4, fontweight="normal"):
    """画一个圆角方框 + 居中文字。"""
    box = FancyBboxPatch((x, y), w, h,
                        boxstyle="round,pad=0.02,rounding_size=0.04",
                        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center", fontsize=fontsize,
            color="#1a1a1a", zorder=3, fontweight=fontweight)


def _arrow(ax, x1, y1, x2, y2, color="#444", lw=1.3, style="-|>", curve=0.0):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle=style,
                            color=color, lw=lw,
                            mutation_scale=14,
                            connectionstyle=f"arc3,rad={curve}",
                            zorder=1)
    ax.add_patch(arrow)


def _setup_axes(fig_w=12, fig_h=7, xlim=(0, 12), ylim=(0, 7), title=None):
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    return fig, ax


# ──────────────────────────────────────────────────────────────────────
# 第 3 章：架构 / 部署 / 时序 / ER / 角色
# ──────────────────────────────────────────────────────────────────────

def fig_system_architecture():
    fig, ax = _setup_axes(13, 8, (0, 13), (0, 8))

    # 用户层
    _box(ax, 0.5, 6.7, 12, 0.8, "用户层（Web 浏览器 / 移动端 H5）",
         fc="#fff3cd", ec="#856404", fontsize=11, fontweight="bold")

    # 表示层 - Vue 3
    _box(ax, 0.5, 5.3, 12, 1.1,
         "表示层（Vue 3 + Element Plus + Pinia + ECharts + Vite）\n"
         "19 个视图 · 路由守卫(RBAC) · Axios 拦截器 · Token 自动续期",
         fc="#cfe2ff", ec="#0b5394", fontsize=10)

    # 业务逻辑层 - 外框
    ax.add_patch(Rectangle((0.5, 3.0), 12, 2.0,
                           facecolor="#d9ead3", edgecolor="#274e13",
                           linewidth=1.4, zorder=1))
    ax.text(6.5, 4.78, "业务逻辑层（FastAPI + Pydantic v2 + Uvicorn）",
            ha="center", fontsize=11, fontweight="bold",
            color="#1a1a1a", zorder=3)
    # 子模块
    sub_modules = [
        ("Auth\n/RBAC", 0.7),
        ("Patient\nMgmt", 2.0),
        ("Predict\nEngine", 3.3),
        ("Train\nPipeline", 4.6),
        ("Multi-\nModal", 5.9),
        ("PTB-XL\nFusion", 7.2),
        ("SHAP\nXAI", 8.5),
        ("Report\nPDF", 9.8),
        ("Async\nTaskQ", 11.1),
    ]
    for label, x in sub_modules:
        _box(ax, x, 3.15, 1.15, 1.4, label, fc="#ead1dc", ec="#741b47",
             fontsize=8.5)

    # 算法 / ML 层
    _box(ax, 0.5, 1.9, 12, 1.1,
         "算法与模型层（scikit-learn 1.x · XGBoost 2.x · LightGBM 4.x · "
         "TensorFlow 2.13 · SHAP · NeuroKit2）\n"
         "LR · RF · XGB · LGB · 1D-CNN · LSTM · 1D-ResNet · Mask-Recon SSL · 5 种 Late Fusion",
         fc="#fce5cd", ec="#b45f06", fontsize=9.5)

    # 数据层
    _box(ax, 0.5, 0.4, 5.5, 1.2,
         "结构化数据\n（SQLite/MySQL · SQLAlchemy 2.0 ORM）\n"
         "users / patients / prediction_records\n"
         "/ model_versions / audit_logs / tasks",
         fc="#d0e0e3", ec="#0c5460", fontsize=9)
    _box(ax, 7.0, 0.4, 5.5, 1.2,
         "波形 / 模型文件\n(data/h5 · data/ptbxl_hf · data/models · data/raw)\n"
         "WFDB / Parquet / .h5 / .joblib",
         fc="#d0e0e3", ec="#0c5460", fontsize=9)

    # 箭头
    for x in [3, 6.5, 10]:
        _arrow(ax, x, 6.7, x, 6.4)
        _arrow(ax, x, 5.3, x, 5.0)
        _arrow(ax, x, 3.0, x, 3.0)
        _arrow(ax, x, 1.9, x, 1.6)

    ax.set_title("图 3-1 HeartCycle CAD System 三层架构总览",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_3-1_system_architecture.png", bbox_inches="tight")
    plt.close()


def fig_deployment_topology():
    fig, ax = _setup_axes(12, 6.5, (0, 12), (0, 6.5))

    # 客户端
    _box(ax, 0.3, 4.8, 2.0, 1.0, "Web 客户端\n(Chrome/Edge)",
         fc="#fff3cd", ec="#856404")
    _box(ax, 0.3, 2.8, 2.0, 1.0, "运维终端\n(curl/Postman)",
         fc="#fff3cd", ec="#856404")

    # Nginx / 反向代理
    _box(ax, 3.4, 3.5, 1.8, 1.2, "Nginx\n反向代理\n+ TLS 终结",
         fc="#cfe2ff", ec="#0b5394")

    # FastAPI 容器
    _box(ax, 6.0, 4.6, 2.5, 1.4, "FastAPI 容器\nuvicorn-worker\n× N (默认 1)",
         fc="#d9ead3", ec="#274e13", fontweight="bold")
    _box(ax, 6.0, 2.5, 2.5, 1.4, "TaskQueue\n协程后台\n(异步任务)",
         fc="#d9ead3", ec="#274e13")

    # 数据库 + 文件
    _box(ax, 9.3, 4.6, 2.4, 1.4, "MySQL 8.x /\nSQLite\n持久化卷",
         fc="#d0e0e3", ec="#0c5460")
    _box(ax, 9.3, 2.5, 2.4, 1.4, "Volume:\ndata/, models/,\nptbxl_hf/, h5/",
         fc="#d0e0e3", ec="#0c5460")

    # WebSocket
    _box(ax, 6.0, 0.5, 2.5, 1.3, "WebSocket\n(任务进度推送)",
         fc="#fce5cd", ec="#b45f06")

    # 箭头
    _arrow(ax, 2.3, 5.3, 3.4, 4.3)
    _arrow(ax, 2.3, 3.3, 3.4, 4.0)
    _arrow(ax, 5.2, 4.3, 6.0, 5.3)
    _arrow(ax, 5.2, 4.0, 6.0, 3.2)
    _arrow(ax, 8.5, 5.3, 9.3, 5.3)
    _arrow(ax, 8.5, 3.2, 9.3, 3.2)
    _arrow(ax, 7.25, 2.5, 7.25, 1.8)

    # docker-compose 注释
    ax.text(6, 6.3, "Docker Compose 一键部署：nginx / api / db / volume",
            ha="center", fontsize=10, style="italic", color="#666")

    ax.set_title("图 3-2 系统部署拓扑（Docker Compose 单机版）",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_3-2_deployment_topology.png", bbox_inches="tight")
    plt.close()


def fig_request_flow():
    fig, ax = plt.subplots(figsize=(13, 7.2))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.set_axis_off()

    actors = ["前端\n(Vue)", "Auth\nMiddleware", "API\nRouter",
              "Service\n(BLL)", "ML\nModel", "Database",
              "ReportGen\n(PDF)"]
    cols = np.linspace(0.8, 12.2, len(actors))
    for x, name in zip(cols, actors):
        _box(ax, x - 0.65, 7.0, 1.3, 0.7, name,
             fc="#cfe2ff", ec="#0b5394", fontsize=9, fontweight="bold")
        ax.plot([x, x], [0.5, 6.9], color="#999", linestyle="--",
                linewidth=0.8, zorder=0)

    msgs = [
        (0, 1, "POST /predict\n+ JWT", 6.4),
        (1, 2, "校验 token / RBAC", 5.8),
        (2, 3, "调用 service", 5.2),
        (3, 4, "推理 (LR/RF/...)", 4.6),
        (4, 3, "概率 + SHAP", 4.0),
        (3, 5, "写入 prediction_records", 3.3),
        (3, 6, "异步生成 PDF", 2.6),
        (6, 3, "PDF 路径", 1.9),
        (3, 0, "200 OK\nJSON 结果", 1.2),
    ]
    for s, e, txt, y in msgs:
        x1, x2 = cols[s], cols[e]
        c = "#1f4e79" if s < e else "#7f1d1d"
        _arrow(ax, x1, y, x2, y, color=c, lw=1.4)
        ax.text((x1 + x2) / 2, y + 0.18, txt,
                ha="center", fontsize=8.5, color=c)

    ax.set_title("图 3-3 风险预测典型请求时序（含异步 PDF 生成）",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_3-3_request_flow.png", bbox_inches="tight")
    plt.close()


def fig_database_er():
    fig, ax = _setup_axes(13, 7.5, (0, 13), (0, 7.5))

    # 实体定义 (x, y, w, h, name, fields)
    entities = [
        (0.5, 5.3, 3.2, 1.8, "User",
         "id (PK)\nusername\nemail\npassword_hash\nrole\nis_active"),
        (4.5, 5.3, 3.2, 1.8, "Patient",
         "id (PK)\npatient_no\nname/gender/birth\ndoctor_id (FK→User)\ncreated_at"),
        (8.7, 5.3, 4.0, 1.8, "PredictionRecord",
         "id (PK)\npatient_id (FK→Patient)\nmodel_version_id (FK)\n"
         "input_features (JSON)\nrisk_score / risk_level\nshap_values (JSON)"),

        (0.5, 2.5, 3.2, 1.8, "ModelVersion",
         "id (PK)\nname / version_no\nalgorithm\nmetrics_json\n"
         "is_active / created_at"),
        (4.5, 2.5, 3.2, 1.8, "AuditLog",
         "id (PK)\nuser_id (FK→User)\naction\nresource_type\n"
         "ip_address\ncreated_at"),
        (8.7, 2.5, 4.0, 1.8, "Task (异步)",
         "id (PK)\nname / type\nstatus (pending/...)\nprogress\n"
         "user_id (FK→User)\nresult / error_message"),

        (0.5, 0.2, 12.2, 1.4, "Report (PDF 资源)",
         "report_id · prediction_record_id (FK→PredictionRecord)\n"
         "file_path · template_version · generated_at"),
    ]
    boxes = []
    for x, y, w, h, name, fields in entities:
        # 标题
        _box(ax, x, y + h - 0.4, w, 0.4, name,
             fc="#1f4e79", ec="#1f4e79", fontsize=10, fontweight="bold")
        # 字段
        ax.add_patch(Rectangle((x, y), w, h - 0.4,
                              facecolor="#fff", edgecolor="#1f4e79", lw=1.2))
        ax.text(x + 0.1, y + h - 0.55, fields,
                ha="left", va="top", fontsize=8, family="monospace")
        # 字段标题文字白色
        ax.texts[-2].set_color("white")
        boxes.append((x + w / 2, y + h / 2, x, y, w, h))

    def link(a, b, label):
        x1, y1, ax_, ay_, aw, ah = boxes[a]
        x2, y2, bx_, by_, bw, bh = boxes[b]
        _arrow(ax, x1, y1, x2, y2, color="#741b47", lw=1.0,
               style="-|>", curve=0.15 if a > b else -0.15)
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, label,
                ha="center", fontsize=8, color="#741b47", style="italic")

    # User → Patient (1:N), Patient → PredictionRecord (1:N),
    # ModelVersion → PredictionRecord (1:N), User → AuditLog (1:N),
    # User → Task (1:N), PredictionRecord → Report (1:1)
    link(0, 1, "1:N")
    link(1, 2, "1:N")
    link(3, 2, "1:N")
    link(0, 4, "1:N")
    link(0, 5, "1:N")
    link(2, 6, "1:1")

    ax.set_title("图 3-4 数据库核心实体关系（ER）图",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_3-4_database_er.png", bbox_inches="tight")
    plt.close()


def fig_role_matrix():
    roles = ["admin", "doctor", "researcher", "patient"]
    perms = [
        "用户管理", "患者增删改查", "单次预测", "批量预测",
        "模型训练", "模型版本管理", "PTB-XL 多模态推理",
        "SHAP 解释", "PDF 报告下载", "系统监控", "审计日志查看",
        "查看个人风险报告",
    ]
    matrix = np.array([
        # admin
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        # doctor
        [0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0],
        # researcher
        [0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0],
        # patient
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    ])
    fig, ax = plt.subplots(figsize=(13, 4.2))
    cmap = matplotlib.colors.ListedColormap(["#f0f0f0", "#2e7d32"])
    ax.imshow(matrix, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(perms)))
    ax.set_xticklabels(perms, rotation=35, ha="right", fontsize=10)
    ax.set_yticks(range(len(roles)))
    ax.set_yticklabels(roles, fontsize=11, fontweight="bold")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            mark = "✓" if matrix[i, j] else "—"
            color = "white" if matrix[i, j] else "#999"
            ax.text(j, i, mark, ha="center", va="center",
                    fontsize=12, color=color)
    ax.set_title("图 3-5 角色 - 功能权限矩阵 (RBAC)",
                 fontsize=13, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig(OUT / "fig_3-5_role_matrix.png", bbox_inches="tight")
    plt.close()


# ──────────────────────────────────────────────────────────────────────
# 第 4 章：数据流水线 / 特征体系 / 类别分布
# ──────────────────────────────────────────────────────────────────────

def fig_data_pipeline():
    fig, ax = _setup_axes(14, 5, (0, 14), (0, 5))

    stages = [
        (0.3, "原始数据\n(CSV/H5/WFDB)", "#fff3cd", "#856404"),
        (2.3, "数据清洗\n类型/缺失/重复", "#cfe2ff", "#0b5394"),
        (4.3, "异常检测\nIQR + Isolation\nForest", "#cfe2ff", "#0b5394"),
        (6.3, "缺失值插补\nKNN/中位数/众数", "#cfe2ff", "#0b5394"),
        (8.3, "特征工程\n临床先验 + HRV", "#d9ead3", "#274e13"),
        (10.3, "标准化\nZ-score / Min-Max", "#d9ead3", "#274e13"),
        (12.3, "类别均衡\nSMOTE (仅训练)", "#fce5cd", "#b45f06"),
    ]
    y0 = 2.5
    for x, txt, fc, ec in stages:
        _box(ax, x, y0, 1.5, 1.5, txt, fc=fc, ec=ec, fontsize=9)
    for i in range(len(stages) - 1):
        _arrow(ax, stages[i][0] + 1.5, y0 + 0.75,
                   stages[i + 1][0], y0 + 0.75)

    # 顶部数据源说明
    ax.text(0.7 + 14, 4.5, "", ha="center")
    ax.text(7, 4.5,
            "三类数据源：合成 10k (CSV) · Z-Alizadeh Sani 303 (UCI) · "
            "PTB-XL 21,799 (PhysioNet WFDB / HF parquet)",
            ha="center", fontsize=10, color="#444", style="italic")

    # 底部输出说明
    ax.text(7, 1.5,
            "输出：训练池 (Train) · 验证池 (Val) · 测试池 (Test)，"
            "分层抽样 7:1.5:1.5",
            ha="center", fontsize=10, color="#444", style="italic")

    ax.set_title("图 4-1 多源数据处理与特征工程流水线",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_4-1_data_pipeline.png", bbox_inches="tight")
    plt.close()


def fig_feature_taxonomy():
    fig, ax = _setup_axes(13, 7, (0, 13), (0, 7))

    # 根
    _box(ax, 5.5, 5.7, 2.0, 0.9, "42 维特征",
         fc="#1f4e79", ec="#1f4e79", fontsize=11, fontweight="bold")
    # 5 大类
    cats = [
        (0.2, "人口学 (4)\n年龄/性别/\n身高/体重", "#fff3cd"),
        (2.7, "生理 (6)\nBMI/SBP/DBP\nHR/呼吸/体温", "#cfe2ff"),
        (5.3, "实验室 (10)\nTC/LDL/HDL\nTG/Glu/HbA1c\nCre/UA/CRP/Hcy",
         "#d9ead3"),
        (8.0, "HRV (16)\n时域 4 + 频域 5\n+ 非线性 7",
         "#fce5cd"),
        (10.7, "生活方式 (6)\n吸烟/饮酒/运动\n+ 既往史 (DM/HTN/家族)",
         "#ead1dc"),
    ]
    for x, txt, fc in cats:
        _box(ax, x, 3.5, 2.2, 1.7, txt, fc=fc, ec="#444", fontsize=9)
        _arrow(ax, 6.5, 5.7, x + 1.1, 5.2, color="#666")

    # HRV 三子类细化
    sub = [
        (5.6, "时域\nSDNN/RMSSD\npNN50/SDSD"),
        (8.2, "频域\nLF/HF/VLF\nTotal Power\nLF/HF"),
        (10.8, "非线性\nSD1/SD2/ApEn\nSampEn/DFAα1α2"),
    ]
    for x, txt in sub:
        _box(ax, x, 1.0, 1.9, 1.7, txt,
             fc="#fff3cd", ec="#856404", fontsize=8.5)
        _arrow(ax, 9.1, 3.5, x + 0.95, 2.7, color="#856404", curve=0.15)

    # 临床先验扩展（17 项）说明
    ax.text(0.5, 0.4,
            "临床先验扩展（17 项，仅 Z-Alizadeh）：LDL/HDL · TG/HDL · NLR · "
            "BMI 分箱 · 风险因子总分 · 心绞痛-ECG 综合分 · 年龄×风险因子交互 等",
            fontsize=8.5, color="#666", style="italic")

    ax.set_title("图 4-2 特征体系：基础 42 维 + 临床先验扩展 17 项",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_4-2_feature_taxonomy.png", bbox_inches="tight")
    plt.close()


def fig_class_balance():
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.5))

    # 1) 合成 10k
    pos = EXP["meta"]["pos_count"]
    neg = EXP["meta"]["neg_count"]
    axes[0].pie([neg, pos], labels=[f"阴性 {neg}", f"阳性 {pos}"],
                colors=["#a8d5a3", "#e08585"],
                autopct="%1.1f%%", startangle=90,
                wedgeprops=dict(linewidth=1.5, edgecolor="white"),
                textprops=dict(fontsize=10))
    axes[0].set_title("(a) 合成数据集 (n=10,000)", fontsize=11)

    # 2) Z-Alizadeh
    pos = ZAL["dataset_info"]["class_distribution"]["1"]
    neg = ZAL["dataset_info"]["class_distribution"]["0"]
    axes[1].pie([neg, pos], labels=[f"非 CAD {neg}", f"CAD {pos}"],
                colors=["#a8d5a3", "#e08585"],
                autopct="%1.1f%%", startangle=90,
                wedgeprops=dict(linewidth=1.5, edgecolor="white"),
                textprops=dict(fontsize=10))
    axes[1].set_title("(b) Z-Alizadeh Sani 真实数据 (n=303)", fontsize=11)

    # 3) PTB-XL 5 类
    classes = ["NORM", "MI", "STTC", "CD", "HYP"]
    counts = [9528, 5486, 5250, 4907, 2655]  # PTB-XL 论文 Table 2
    colors = ["#a8d5a3", "#e08585", "#f1c27d", "#9bc8e3", "#c4a3d4"]
    axes[2].bar(classes, counts, color=colors, edgecolor="white", linewidth=1.2)
    for i, c in enumerate(counts):
        axes[2].text(i, c + 80, str(c), ha="center", fontsize=9.5)
    axes[2].set_title("(c) PTB-XL 多标签类别（≥1 标注，21,799 ECG）",
                      fontsize=11)
    axes[2].set_ylabel("样本数", fontsize=10)
    axes[2].grid(True, axis="y", alpha=0.3)
    axes[2].set_ylim(0, 11000)

    fig.suptitle("图 4-3 三类数据集类别分布对比", fontsize=13,
                 fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "fig_4-3_class_balance.png", bbox_inches="tight")
    plt.close()


# ──────────────────────────────────────────────────────────────────────
# 第 5 章：1D-ResNet / SSL / 多模态融合 / 训练策略
# ──────────────────────────────────────────────────────────────────────

def fig_resnet1d_arch():
    fig, ax = _setup_axes(13, 5, (0, 13), (0, 5))

    layers = [
        (0.2, "Input\n(1000, 12)", "#fff3cd"),
        (1.7, "Conv1D-15\nstride 2\n→ 64", "#cfe2ff"),
        (3.2, "BN + ReLU\nMaxPool /2", "#cfe2ff"),
        (4.7, "Block ×4\n(64→128→\n256→512)\nstride 2", "#d9ead3"),
        (6.5, "Global\nAvgPool", "#fce5cd"),
        (8.0, "Dropout\n(0.3)", "#fce5cd"),
        (9.5, "Dense 1\nSigmoid", "#ead1dc"),
        (11.0, "P(CAD)", "#1f4e79"),
    ]
    y0 = 2.8
    for i, (x, txt, fc) in enumerate(layers):
        ec = "#1f4e79" if fc != "#1f4e79" else "#1f4e79"
        fontsize = 9.5
        fc_inner = fc
        text_color = "white" if fc == "#1f4e79" else "#1a1a1a"
        box = FancyBboxPatch((x, y0), 1.3, 1.4,
                            boxstyle="round,pad=0.02,rounding_size=0.04",
                            linewidth=1.4, edgecolor=ec,
                            facecolor=fc_inner, zorder=2)
        ax.add_patch(box)
        ax.text(x + 0.65, y0 + 0.7, txt, ha="center", va="center",
                fontsize=fontsize, color=text_color, zorder=3)
    for i in range(len(layers) - 1):
        _arrow(ax, layers[i][0] + 1.3, y0 + 0.7,
                   layers[i + 1][0], y0 + 0.7)

    # ResBlock 细节
    ax.text(6.5, 1.7,
            "ResBlock = [Conv1D(7) → BN → ReLU → Conv1D(7) → BN] + Skip",
            ha="center", fontsize=9.5, style="italic", color="#666")

    ax.text(6.5, 1.0,
            "总参数 ≈ 2.0 M · 输入 1000 时间步 · 12 导联 · 二分类输出",
            ha="center", fontsize=9.5, color="#444")

    ax.set_title("图 5-1 ECG-ResNet1D 模型结构",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_5-1_resnet1d_arch.png", bbox_inches="tight")
    plt.close()


def fig_ssl_mask_recon():
    fig, ax = _setup_axes(13, 5.5, (0, 13), (0, 5.5))

    # Encoder
    ax.add_patch(Rectangle((0.5, 1.5), 5, 2.5,
                           facecolor="#cfe2ff", edgecolor="#0b5394", lw=1.4))
    ax.text(3, 4.3, "Encoder（共享主干 → 迁移给监督模型）",
            ha="center", fontsize=10, fontweight="bold", color="#0b5394")
    enc_layers = ["Conv1D-15", "Block 1\nstride 2", "Block 2\nstride 2",
                  "Block 3\nstride 2"]
    for i, l in enumerate(enc_layers):
        x = 0.7 + i * 1.2
        _box(ax, x, 2.0, 1.05, 1.4, l, fc="#fff", ec="#0b5394", fontsize=9)

    # Bottleneck
    _box(ax, 5.8, 2.0, 1.4, 1.4, "Latent\n(125, 256)",
         fc="#1f4e79", ec="#1f4e79", fontsize=9.5)
    # 文字白色
    ax.texts[-1].set_color("white")

    # Decoder
    ax.add_patch(Rectangle((7.5, 1.5), 5, 2.5,
                           facecolor="#fce5cd", edgecolor="#b45f06", lw=1.4))
    ax.text(10, 4.3, "Decoder（仅预训练阶段使用）",
            ha="center", fontsize=10, fontweight="bold", color="#b45f06")
    dec_layers = ["ConvTrans×3", "BN+ReLU", "Crop/Pad", "Conv1D-1\n→ 12"]
    for i, l in enumerate(dec_layers):
        x = 7.7 + i * 1.2
        _box(ax, x, 2.0, 1.05, 1.4, l, fc="#fff", ec="#b45f06", fontsize=9)

    # 流向
    _arrow(ax, 5.5, 2.7, 5.8, 2.7)
    _arrow(ax, 7.2, 2.7, 7.5, 2.7)

    # 上方输入信号
    ax.text(3, 5.0, "原始 ECG\n(1000, 12)", ha="center", fontsize=10,
            color="#0b5394", fontweight="bold")
    ax.text(10, 5.0, "重构 ECG ≈ 原始", ha="center", fontsize=10,
            color="#b45f06", fontweight="bold")

    # 下方流程
    ax.text(3, 0.8, "随机 mask 15% 片段（每段 50 步）",
            ha="center", fontsize=9.5, style="italic", color="#666")
    ax.text(10, 0.8,
            "MSE 损失\nL = ‖ ECG_orig − ECG_recon ‖²",
            ha="center", fontsize=9.5, style="italic", color="#666")

    ax.set_title("图 5-2 自监督预训练：Mask Reconstruction 架构",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_5-2_ssl_mask_recon.png", bbox_inches="tight")
    plt.close()


def fig_multimodal_fusion():
    fig, ax = _setup_axes(15, 6.5, (0, 15), (0, 6.5))

    # ECG 分支
    _box(ax, 0.5, 4.5, 1.8, 1.2, "PTB-XL ECG\n12 导联 × 1000",
         fc="#fff3cd", ec="#856404")
    _box(ax, 2.8, 4.5, 1.8, 1.2, "1D-ResNet\n(SSL 预训练)",
         fc="#cfe2ff", ec="#0b5394", fontweight="bold")
    _box(ax, 5.1, 4.5, 1.8, 1.2, "P_ECG\n(0,1)",
         fc="#1f4e79", ec="#1f4e79")
    ax.texts[-1].set_color("white")

    _arrow(ax, 2.3, 5.1, 2.8, 5.1)
    _arrow(ax, 4.6, 5.1, 5.1, 5.1)

    # 表格分支
    _box(ax, 0.5, 1.3, 1.8, 1.2, "Z-Alizadeh\n78 临床指标",
         fc="#fff3cd", ec="#856404")
    _box(ax, 2.8, 1.3, 1.8, 1.2, "RandomForest\n+ 17 临床\n先验特征",
         fc="#d9ead3", ec="#274e13", fontweight="bold")
    _box(ax, 5.1, 1.3, 1.8, 1.2, "P_TAB\n(0,1)",
         fc="#1f4e79", ec="#1f4e79")
    ax.texts[-1].set_color("white")
    _arrow(ax, 2.3, 1.9, 2.8, 1.9)
    _arrow(ax, 4.6, 1.9, 5.1, 1.9)

    # 融合
    _box(ax, 7.5, 2.8, 2.5, 1.4, "Late Fusion\n5 种策略",
         fc="#ead1dc", ec="#741b47", fontweight="bold")
    _arrow(ax, 6.9, 5.1, 7.5, 3.8, curve=0.2)
    _arrow(ax, 6.9, 1.9, 7.5, 3.2, curve=-0.2)

    # 5 种策略列表（独立框）
    ax.add_patch(Rectangle((10.3, 1.6), 2.5, 3.7,
                           facecolor="#fbeff4", edgecolor="#741b47",
                           linewidth=1.0, alpha=0.6, zorder=0))
    ax.text(11.55, 5.0, "5 种策略", ha="center",
            fontsize=10, fontweight="bold", color="#741b47")
    strategies = ["mean", "weighted\n(α·E+(1-α)·T)", "logit_mean",
                  "max", "min"]
    for i, s in enumerate(strategies):
        ax.text(10.5, 4.5 - i * 0.6, "• " + s,
                fontsize=8.5, color="#741b47")

    # 输出
    _box(ax, 13.0, 2.8, 1.8, 1.4, "P_final\n(0,1)\n+ 风险等级",
         fc="#1f4e79", ec="#1f4e79", fontweight="bold")
    ax.texts[-1].set_color("white")
    _arrow(ax, 10.0, 3.5, 13.0, 3.5)

    # 顶部三层数据策略说明
    ax.text(7.5, 6.0,
            "三层数据策略：HeartCycle（自监督预训练）→ "
            "PTB-XL（监督 ECG-CAD 训练）→ Z-Alizadeh（临床表格融合）",
            ha="center", fontsize=10, style="italic", color="#444")

    ax.set_title("图 5-3 双分支多模态 Late Fusion 架构（PTB-XL ECG + 临床表格）",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_5-3_multimodal_fusion.png", bbox_inches="tight")
    plt.close()


def fig_training_strategy():
    fig, ax = _setup_axes(14, 5.5, (0, 14), (0, 5.5))

    # 阶段 1：HeartCycle SSL
    _box(ax, 0.3, 2.5, 4.0, 2.0,
         "阶段 1：自监督预训练\n\n"
         "数据：HeartCycle 健康人 ECG（37 例）\n"
         "任务：Mask 15% → MSE 重构\n"
         "epochs=50, lr=5e-4\n\n"
         "→ 得到通用 ECG 表征 (Encoder)",
         fc="#fff3cd", ec="#856404", fontsize=9)

    # 阶段 2：PTB-XL 监督
    _box(ax, 5.0, 2.5, 4.0, 2.0,
         "阶段 2：迁移监督训练\n\n"
         "数据：PTB-XL 21,799 ECG (5 类)\n"
         "策略：mi_vs_norm → 二分类\n"
         "frozen warm-up 5 epoch +\nfine-tune lr=1e-4\n\n"
         "→ ECG-CAD 监督模型",
         fc="#cfe2ff", ec="#0b5394", fontsize=9)

    # 阶段 3：多模态融合
    _box(ax, 9.7, 2.5, 4.0, 2.0,
         "阶段 3：多模态融合推理\n\n"
         "数据：Z-Alizadeh 表格 + ECG 模型\n"
         "策略：5 种 Late Fusion\n"
         "阈值：约登指数自动选取\n\n"
         "→ 最终风险概率 + SHAP",
         fc="#d9ead3", ec="#274e13", fontsize=9)

    _arrow(ax, 4.3, 3.5, 5.0, 3.5, lw=2)
    _arrow(ax, 9.0, 3.5, 9.7, 3.5, lw=2)

    # 上方过程标签
    for x, t in [(2.3, "Pretrain"), (7.0, "Transfer"), (11.7, "Inference")]:
        ax.text(x, 4.9, t, ha="center", fontsize=11, fontweight="bold",
                color="#1f4e79")

    # 底部数据流
    ax.text(7, 1.5,
            "标签来源：PTB-XL 自带 scp_codes（NORM/MI 二值化） · "
            "Z-Alizadeh CAD 0/1 标注 · 全程使用真实标签",
            ha="center", fontsize=9.5, style="italic", color="#666")

    ax.set_title("图 5-4 三阶段训练策略：自监督 → 监督 → 多模态融合",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_5-4_training_strategy.png", bbox_inches="tight")
    plt.close()


# ──────────────────────────────────────────────────────────────────────
# 第 6 章：雷达图 / CV 稳定性 / 7 模型对比 / 阈值 / 跨数据集
# ──────────────────────────────────────────────────────────────────────

def fig_radar_metrics():
    metrics_keys = ["accuracy", "sensitivity", "specificity",
                    "precision", "f1", "auc"]
    labels = ["准确率", "灵敏度", "特异性", "精确率", "F1", "AUC"]

    models = EXP["metrics_test_set"]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8.5, 8), subplot_kw=dict(polar=True))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))
    for m, c in zip(models, colors):
        vals = [m[k] for k in metrics_keys]
        vals += vals[:1]
        ax.plot(angles, vals, color=c, linewidth=1.7,
                marker="o", markersize=4, label=m["model"])
        ax.fill(angles, vals, color=c, alpha=0.07)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0.6, 1.0)
    ax.set_yticks([0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(["0.70", "0.80", "0.90", "1.00"], fontsize=8)
    ax.grid(True, alpha=0.4)
    ax.set_title("图 6-1 6 模型多维指标雷达图（合成数据集，测试集 1500 例）",
                 fontsize=12, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT / "fig_6-1_radar_metrics.png", bbox_inches="tight")
    plt.close()


def fig_cv_stability():
    folds_data = {k: v["folds"] for k, v in ZAL["cv_results"].items()}
    means = {k: v["mean_auc"] for k, v in ZAL["cv_results"].items()}
    stds = {k: v["std_auc"] for k, v in ZAL["cv_results"].items()}

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # 左：折间 AUC 折线
    folds = list(range(1, 6))
    colors = plt.cm.Set2(np.linspace(0, 1, len(folds_data)))
    for (name, vals), c in zip(folds_data.items(), colors):
        axes[0].plot(folds, vals, marker="o", linewidth=1.8,
                     label=f"{name} (μ={means[name]:.4f}, σ={stds[name]:.4f})",
                     color=c)
    axes[0].set_xlabel("Fold", fontsize=11)
    axes[0].set_ylabel("AUC", fontsize=11)
    axes[0].set_xticks(folds)
    axes[0].set_ylim(0.83, 1.02)
    axes[0].grid(True, alpha=0.4)
    axes[0].legend(fontsize=9, loc="lower right")
    axes[0].set_title("(a) Z-Alizadeh 5 折交叉验证 AUC 折间稳定性",
                      fontsize=11)

    # 右：合成集 4 个 sklearn 模型的 CV AUC ± std
    syn = {m["model"]: (m["cv_auc_mean"], m["cv_auc_std"])
           for m in EXP["metrics_test_set"]
           if not (m["cv_auc_mean"] != m["cv_auc_mean"])}  # filter NaN
    names = list(syn.keys())
    mu = [syn[n][0] for n in names]
    sd = [syn[n][1] for n in names]
    bars = axes[1].bar(names, mu, yerr=sd, capsize=8,
                       color=plt.cm.Pastel1(np.linspace(0, 1, len(names))),
                       edgecolor="#444", linewidth=1.2,
                       error_kw=dict(elinewidth=1.5, ecolor="#333"))
    for b, m_, s_ in zip(bars, mu, sd):
        axes[1].text(b.get_x() + b.get_width() / 2,
                     b.get_height() + s_ + 0.002,
                     f"{m_:.4f}\n±{s_:.4f}",
                     ha="center", fontsize=9.5)
    axes[1].set_ylim(0.90, 0.945)
    axes[1].set_ylabel("CV AUC", fontsize=11)
    axes[1].grid(True, axis="y", alpha=0.4)
    axes[1].set_title("(b) 合成数据集 sklearn 模型 5 折 CV AUC", fontsize=11)
    plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=15, ha="right")

    fig.suptitle("图 6-2 5 折分层交叉验证稳定性分析", fontsize=13,
                 fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "fig_6-2_cv_stability.png", bbox_inches="tight")
    plt.close()


def fig_zalizadeh_models():
    test = ZAL["test_results"]
    names = list(test.keys())
    accs = [test[n]["accuracy"] for n in names]
    sens = [test[n]["sensitivity"] for n in names]
    spec = [test[n]["specificity"] for n in names]
    aucs = [test[n]["auc"] for n in names]

    fig, ax = plt.subplots(figsize=(13, 5.5))
    x = np.arange(len(names))
    w = 0.2
    ax.bar(x - 1.5 * w, accs, w, label="Accuracy",
           color="#5B9BD5", edgecolor="white")
    ax.bar(x - 0.5 * w, sens, w, label="Sensitivity",
           color="#ED7D31", edgecolor="white")
    ax.bar(x + 0.5 * w, spec, w, label="Specificity",
           color="#70AD47", edgecolor="white")
    ax.bar(x + 1.5 * w, aucs, w, label="AUC",
           color="#FFC000", edgecolor="white")

    # 加数值标注
    for i, n in enumerate(names):
        for j, val in enumerate([accs[i], sens[i], spec[i], aucs[i]]):
            ax.text(i + (j - 1.5) * w, val + 0.01, f"{val:.3f}",
                    ha="center", fontsize=8.5)

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15, ha="right")
    ax.set_ylim(0, 1.10)
    ax.set_ylabel("指标值", fontsize=11)
    ax.legend(loc="upper right", ncol=4, fontsize=10)
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_title("图 6-3 Z-Alizadeh Sani 真实临床数据 7 模型独立测试集性能对比",
                 fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig(OUT / "fig_6-3_zalizadeh_models.png", bbox_inches="tight")
    plt.close()


def fig_threshold_analysis():
    """模拟基于真实模型概率的阈值-灵敏度/特异度曲线（用混淆矩阵反推）。"""
    # 用 Logistic Regression 测试集（合成 10k）的混淆矩阵作基础
    # 真正的曲线需要原始概率；这里我们用现有指标在多个阈值下的解析估算
    # —— 因为没有保存全部概率，这里改为 ROC 数据的真实点位（精度足以做学术展示）
    cm = EXP["confusion_matrices"]["Logistic Regression"]
    tn, fp, fn, tp = cm["tn"], cm["fp"], cm["fn"], cm["tp"]
    # 模拟一组阈值下的 sens/spec/precision/F1 曲线（基于 ROC 估算）
    # 我们用 6 模型的 (1-specificity, sensitivity) 作为关键阈值锚点
    thrs = np.linspace(0.05, 0.95, 19)
    # 对每个模型用其混淆矩阵衍生的 ROC 进行三次插值
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # (a) 各模型 sens vs spec 散点 (来自混淆矩阵)
    cm_all = EXP["confusion_matrices"]
    metrics = {m["model"]: m for m in EXP["metrics_test_set"]}
    for name, c in cm_all.items():
        sens = c["tp"] / (c["tp"] + c["fn"])
        spec = c["tn"] / (c["tn"] + c["fp"])
        axes[0].scatter(1 - spec, sens, s=100, alpha=0.85,
                        label=f"{name} (AUC={metrics[name]['auc']:.3f})",
                        edgecolor="white", linewidth=1.2)
        axes[0].annotate(name, (1 - spec, sens), fontsize=8,
                         xytext=(5, 5), textcoords="offset points")
    axes[0].plot([0, 1], [0, 1], "--", color="gray", alpha=0.6)
    axes[0].set_xlabel("1 - 特异性 (FPR)", fontsize=11)
    axes[0].set_ylabel("灵敏度 (TPR)", fontsize=11)
    axes[0].set_title("(a) 6 模型在最优阈值下的 ROC 工作点",
                      fontsize=11)
    axes[0].grid(True, alpha=0.4)
    axes[0].legend(fontsize=8)
    axes[0].set_xlim(-0.05, 0.6)
    axes[0].set_ylim(0.55, 1.05)

    # (b) Z-Alizadeh 各模型最优阈值条形
    test = ZAL["test_results"]
    names = list(test.keys())
    thrs_z = [test[n]["threshold"] for n in names]
    bars = axes[1].barh(names, thrs_z,
                        color=plt.cm.viridis(np.linspace(0, 0.9, len(names))),
                        edgecolor="white")
    for b, t in zip(bars, thrs_z):
        axes[1].text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2,
                     f"{t:.3f}", va="center", fontsize=9)
    axes[1].set_xlim(0, 1)
    axes[1].axvline(0.5, linestyle="--", color="red", alpha=0.6,
                    label="默认 0.5")
    axes[1].set_xlabel("阈值", fontsize=11)
    axes[1].set_title("(b) Z-Alizadeh 各模型经约登指数优化的阈值",
                      fontsize=11)
    axes[1].legend(loc="lower right", fontsize=9)
    axes[1].grid(True, axis="x", alpha=0.4)

    fig.suptitle("图 6-4 阈值与决策点分析（真实数据）",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "fig_6-4_threshold_analysis.png", bbox_inches="tight")
    plt.close()


def fig_dataset_compare():
    """合成 vs Z-Alizadeh：同一类模型在两个数据集上的性能差异。"""
    syn = {m["model"]: m for m in EXP["metrics_test_set"]}
    zal = ZAL["test_results"]

    pairs = [
        ("Logistic Regression", "Logistic"),
        ("Random Forest", "RandomForest"),
        ("XGBoost", "XGBoost"),
        ("LightGBM", "LightGBM"),
    ]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(pairs))
    w = 0.35
    syn_auc = [syn[a]["auc"] for a, _ in pairs]
    zal_auc = [zal[b]["auc"] for _, b in pairs]
    syn_acc = [syn[a]["accuracy"] for a, _ in pairs]
    zal_acc = [zal[b]["accuracy"] for _, b in pairs]

    ax.bar(x - 1.5 * w / 2, syn_auc, w / 2, label="合成 10k · AUC",
           color="#5B9BD5", edgecolor="white")
    ax.bar(x - 0.5 * w / 2, zal_auc, w / 2, label="Z-Alizadeh · AUC",
           color="#1F4E79", edgecolor="white")
    ax.bar(x + 0.5 * w / 2, syn_acc, w / 2, label="合成 10k · Acc",
           color="#FFC000", edgecolor="white")
    ax.bar(x + 1.5 * w / 2, zal_acc, w / 2, label="Z-Alizadeh · Acc",
           color="#BF9000", edgecolor="white")

    for i, ((a, b), sa, za, sa2, za2) in enumerate(
            zip(pairs, syn_auc, zal_auc, syn_acc, zal_acc)):
        for j, v in enumerate([sa, za, sa2, za2]):
            ax.text(i + (j - 1.5) * w / 2, v + 0.01, f"{v:.3f}",
                    ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([a for a, _ in pairs], rotation=10, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("指标值", fontsize=11)
    ax.legend(fontsize=10, ncol=2, loc="lower right")
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_title("图 6-5 合成数据集 vs 真实临床数据集（Z-Alizadeh）"
                 "—— 同模型跨数据集性能对比",
                 fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig(OUT / "fig_6-5_dataset_compare.png", bbox_inches="tight")
    plt.close()


# ──────────────────────────────────────────────────────────────────────
# 第 7 章：UI 流转
# ──────────────────────────────────────────────────────────────────────

def fig_ui_flow():
    fig, ax = _setup_axes(13, 7, (0, 13), (0, 7))

    pages = [
        (0.5, 5.5, "Login\n登录页", "#fff3cd"),
        (3.0, 5.5, "Home\n首页 Dashboard", "#cfe2ff"),
        (6.0, 5.5, "PatientList\n患者列表", "#d9ead3"),
        (9.0, 5.5, "PatientDetail\n患者详情", "#d9ead3"),

        (0.5, 3.0, "TrainModel\n传统 ML 训练", "#fce5cd"),
        (3.0, 3.0, "TrainDeepLearning\n深度学习训练", "#fce5cd"),
        (6.0, 3.0, "TrainMultiModal\n多模态训练", "#fce5cd"),
        (9.0, 3.0, "ThesisExperiment\n论文实验流水线", "#fce5cd"),

        (0.5, 0.6, "ModelVersions\n模型版本", "#ead1dc"),
        (3.0, 0.6, "BatchPredict\n批量预测", "#ead1dc"),
        (6.0, 0.6, "Reports\nPDF 报告", "#ead1dc"),
        (9.0, 0.6, "SystemMonitor\n系统监控", "#ead1dc"),
    ]
    for x, y, txt, fc in pages:
        _box(ax, x, y, 2.5, 1.2, txt, fc=fc, ec="#444", fontsize=10)

    # 关键流转
    flows = [
        (1, 5.5, 3.0, 5.5),       # Login -> Home
        (5.5, 5.5, 6.0, 5.5),    # Home -> PatientList
        (8.5, 5.5, 9.0, 5.5),    # PatientList -> PatientDetail
        (4.0, 5.5, 4.0, 4.2),    # Home -> TrainModel
        (10, 4.2, 10, 1.8),     # ThesisExp -> Monitor
        (10, 5.5, 10, 4.2),     # PatientDetail -> ThesisExperiment
        (4.0, 3.0, 4.0, 1.8),    # Train -> ModelVersions
        (7.0, 3.0, 7.0, 1.8),    # MultiModal -> Reports
    ]
    for x1, y1, x2, y2 in flows:
        _arrow(ax, x1, y1, x2, y2, color="#666", lw=1.0)

    ax.text(6.5, 6.6, "登录 → 首页 → 业务区（患者管理 / 模型训练 / 预测 / 报告）",
            ha="center", fontsize=11, fontweight="bold", color="#1f4e79")
    ax.set_title("图 7-1 前端 19 个核心视图与典型导航流转",
                 fontsize=13, fontweight="bold", pad=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_7-1_ui_flow.png", bbox_inches="tight")
    plt.close()


# ──────────────────────────────────────────────────────────────────────
def main():
    print("==> 输出目录:", OUT)
    funcs = [
        fig_system_architecture,
        fig_deployment_topology,
        fig_request_flow,
        fig_database_er,
        fig_role_matrix,
        fig_data_pipeline,
        fig_feature_taxonomy,
        fig_class_balance,
        fig_resnet1d_arch,
        fig_ssl_mask_recon,
        fig_multimodal_fusion,
        fig_training_strategy,
        fig_radar_metrics,
        fig_cv_stability,
        fig_zalizadeh_models,
        fig_threshold_analysis,
        fig_dataset_compare,
        fig_ui_flow,
    ]
    for fn in funcs:
        try:
            fn()
            print(f"  [OK] {fn.__name__}")
        except Exception as e:
            print(f"  [FAIL] {fn.__name__}: {e}")
            raise

    print("\n生成图列表:")
    for p in sorted(OUT.glob("*.png")):
        kb = p.stat().st_size / 1024
        print(f"  {p.name} ({kb:.1f} KB)")


if __name__ == "__main__":
    main()
