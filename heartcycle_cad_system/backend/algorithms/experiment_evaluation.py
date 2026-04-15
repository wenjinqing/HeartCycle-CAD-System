"""
实验评估系统
实现论文第5.6节要求的实验结果分析功能
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, auc, confusion_matrix,
    precision_recall_curve, average_precision_score,
    classification_report
)
from typing import Dict, List, Tuple, Optional
import logging
import os

logger = logging.getLogger(__name__)


def _pdf_matplotlib_fontproperties():
    """PDF 文本优先使用系统中文字体文件，避免 DejaVu 缺字。"""
    from matplotlib import font_manager

    win = os.environ.get("WINDIR", r"C:\Windows")
    for path in (
        os.path.join(win, "Fonts", "msyh.ttc"),
        os.path.join(win, "Fonts", "msyhbd.ttc"),
        os.path.join(win, "Fonts", "simhei.ttf"),
        os.path.join(win, "Fonts", "simsun.ttc"),
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ):
        if path and os.path.isfile(path):
            try:
                return font_manager.FontProperties(fname=path)
            except Exception:
                continue
    return font_manager.FontProperties(family="sans-serif")

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style('whitegrid')


class ExperimentEvaluator:
    """实验评估器"""

    def __init__(self):
        self.results = {}
        self.model_names = []

    def evaluate_model(self, model_name: str, y_true: np.ndarray,
                      y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> Dict:
        """
        评估单个模型

        Parameters:
        -----------
        model_name : str
            模型名称
        y_true : np.ndarray
            真实标签
        y_pred : np.ndarray
            预测标签
        y_prob : np.ndarray, optional
            预测概率

        Returns:
        --------
        metrics : dict
            评估指标
        """
        logger.info(f"评估模型: {model_name}")

        metrics = {
            'model_name': model_name,
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1': f1_score(y_true, y_pred, zero_division=0),
        }

        # 计算特异性
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
        metrics['sensitivity'] = metrics['recall']  # 灵敏度=召回率

        # 如果有概率预测，计算AUC
        if y_prob is not None:
            metrics['auc'] = roc_auc_score(y_true, y_prob)
            metrics['ap'] = average_precision_score(y_true, y_prob)  # Average Precision
        else:
            metrics['auc'] = None
            metrics['ap'] = None

        # 保存结果
        self.results[model_name] = {
            'metrics': metrics,
            'y_true': y_true,
            'y_pred': y_pred,
            'y_prob': y_prob
        }

        if model_name not in self.model_names:
            self.model_names.append(model_name)

        # 打印结果
        logger.info(f"  准确率: {metrics['accuracy']:.4f}")
        logger.info(f"  精确率: {metrics['precision']:.4f}")
        logger.info(f"  召回率: {metrics['recall']:.4f}")
        logger.info(f"  F1分数: {metrics['f1']:.4f}")
        logger.info(f"  特异性: {metrics['specificity']:.4f}")
        if metrics['auc'] is not None:
            logger.info(f"  AUC: {metrics['auc']:.4f}")

        return metrics

    def create_comparison_table(self, save_path: Optional[str] = None) -> pd.DataFrame:
        """
        创建模型性能对比表

        论文要求：表5-1 各模型性能指标对比表

        Returns:
        --------
        comparison_df : pd.DataFrame
            对比表
        """
        logger.info("创建模型性能对比表")

        if not self.results:
            raise ValueError("没有可用的评估结果")

        # 收集所有模型的指标
        data = []
        for model_name in self.model_names:
            metrics = self.results[model_name]['metrics']
            data.append({
                '模型': model_name,
                '准确率': f"{metrics['accuracy']:.1%}",
                '精确率': f"{metrics['precision']:.1%}",
                '召回率': f"{metrics['recall']:.1%}",
                'F1': f"{metrics['f1']:.3f}",
                '灵敏度': f"{metrics['sensitivity']:.1%}",
                '特异性': f"{metrics['specificity']:.1%}",
                'AUC': f"{metrics['auc']:.3f}" if metrics['auc'] else 'N/A',
            })

        comparison_df = pd.DataFrame(data)

        # 保存为CSV
        if save_path:
            comparison_df.to_csv(save_path, index=False, encoding='utf-8-sig')
            logger.info(f"对比表已保存: {save_path}")

        return comparison_df

    def plot_roc_curves(self, save_path: Optional[str] = None):
        """
        绘制ROC曲线对比图

        论文要求：图5-1 各模型ROC曲线对比图
        """
        logger.info("绘制ROC曲线对比图")

        plt.figure(figsize=(10, 8))

        for model_name in self.model_names:
            result = self.results[model_name]
            if result['y_prob'] is not None:
                fpr, tpr, _ = roc_curve(result['y_true'], result['y_prob'])
                roc_auc = auc(fpr, tpr)
                plt.plot(fpr, tpr, lw=2,
                        label=f'{model_name} (AUC = {roc_auc:.3f})')

        # 绘制对角线
        plt.plot([0, 1], [0, 1], 'k--', lw=2, label='随机猜测')

        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('假阳性率 (False Positive Rate)', fontsize=12)
        plt.ylabel('真阳性率 (True Positive Rate)', fontsize=12)
        plt.title('ROC曲线对比', fontsize=14, pad=20)
        plt.legend(loc='lower right', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"ROC曲线已保存: {save_path}")

        plt.show()

    def plot_confusion_matrix(self, model_name: str,
                             save_path: Optional[str] = None):
        """
        绘制混淆矩阵

        论文要求：表5-2 LSTM模型混淆矩阵

        Parameters:
        -----------
        model_name : str
            模型名称
        save_path : str, optional
            保存路径
        """
        logger.info(f"绘制 {model_name} 的混淆矩阵")

        if model_name not in self.results:
            raise ValueError(f"模型 {model_name} 的结果不存在")

        result = self.results[model_name]
        cm = confusion_matrix(result['y_true'], result['y_pred'])

        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['预测阴性', '预测阳性'],
                   yticklabels=['实际阴性', '实际阳性'],
                   cbar_kws={'label': '样本数量'})
        plt.title(f'{model_name} 混淆矩阵', fontsize=14, pad=20)
        plt.ylabel('实际类别', fontsize=12)
        plt.xlabel('预测类别', fontsize=12)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"混淆矩阵已保存: {save_path}")

        plt.show()

        # 打印混淆矩阵统计
        tn, fp, fn, tp = cm.ravel()
        logger.info(f"真阴性(TN): {tn}")
        logger.info(f"假阳性(FP): {fp}")
        logger.info(f"假阴性(FN): {fn}")
        logger.info(f"真阳性(TP): {tp}")

    def plot_pr_curves(self, save_path: Optional[str] = None):
        """
        绘制PR曲线（Precision-Recall）

        Parameters:
        -----------
        save_path : str, optional
            保存路径
        """
        logger.info("绘制PR曲线")

        plt.figure(figsize=(10, 8))

        for model_name in self.model_names:
            result = self.results[model_name]
            if result['y_prob'] is not None:
                precision, recall, _ = precision_recall_curve(
                    result['y_true'], result['y_prob']
                )
                ap = average_precision_score(result['y_true'], result['y_prob'])
                plt.plot(recall, precision, lw=2,
                        label=f'{model_name} (AP = {ap:.3f})')

        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('召回率 (Recall)', fontsize=12)
        plt.ylabel('精确率 (Precision)', fontsize=12)
        plt.title('PR曲线对比', fontsize=14, pad=20)
        plt.legend(loc='lower left', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"PR曲线已保存: {save_path}")

        plt.show()

    def plot_metrics_comparison(self, save_path: Optional[str] = None):
        """
        绘制指标对比柱状图

        Parameters:
        -----------
        save_path : str, optional
            保存路径
        """
        logger.info("绘制指标对比图")

        # 准备数据
        metrics_data = []
        for model_name in self.model_names:
            metrics = self.results[model_name]['metrics']
            metrics_data.append({
                '模型': model_name,
                '准确率': metrics['accuracy'],
                '精确率': metrics['precision'],
                '召回率': metrics['recall'],
                'F1分数': metrics['f1']
            })

        df = pd.DataFrame(metrics_data)

        # 绘制分组柱状图
        fig, ax = plt.subplots(figsize=(12, 6))
        x = np.arange(len(self.model_names))
        width = 0.2

        metrics_to_plot = ['准确率', '精确率', '召回率', 'F1分数']
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for i, metric in enumerate(metrics_to_plot):
            values = df[metric].values
            ax.bar(x + i * width, values, width, label=metric, color=colors[i])

        ax.set_xlabel('模型', fontsize=12)
        ax.set_ylabel('分数', fontsize=12)
        ax.set_title('模型性能指标对比', fontsize=14, pad=20)
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(self.model_names, rotation=45, ha='right')
        ax.legend(loc='lower right', fontsize=10)
        ax.set_ylim([0, 1.1])
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"指标对比图已保存: {save_path}")

        plt.show()

    def _compile_report_lines(self) -> List[str]:
        """与 TXT/PDF 共用的报告正文行（纯文本）。"""
        report: List[str] = []
        report.append("=" * 60)
        report.append("冠心病风险预测系统 - 实验评估报告")
        report.append("=" * 60)
        report.append("")

        report.append("一、模型性能对比")
        report.append("-" * 60)
        comparison_df = self.create_comparison_table()
        report.append(comparison_df.to_string(index=False))
        report.append("")

        report.append("二、详细性能指标")
        report.append("-" * 60)
        for model_name in self.model_names:
            metrics = self.results[model_name]['metrics']
            report.append("")
            report.append(f"{model_name}:")
            report.append(f"  准确率 (Accuracy):    {metrics['accuracy']:.4f}")
            report.append(f"  精确率 (Precision):   {metrics['precision']:.4f}")
            report.append(f"  召回率 (Recall):      {metrics['recall']:.4f}")
            report.append(f"  F1分数 (F1-Score):    {metrics['f1']:.4f}")
            report.append(f"  灵敏度 (Sensitivity): {metrics['sensitivity']:.4f}")
            report.append(f"  特异性 (Specificity): {metrics['specificity']:.4f}")
            if metrics['auc'] is not None:
                report.append(f"  AUC:                  {metrics['auc']:.4f}")
                report.append(f"  AP:                   {metrics['ap']:.4f}")

        report.append("")
        report.append("三、最佳模型")
        report.append("-" * 60)
        best_model = max(
            self.model_names,
            key=lambda x: self.results[x]["metrics"]["auc"] or 0,
        )
        report.append(f"根据AUC指标，最佳模型为: {best_model}")
        auc_bm = self.results[best_model]["metrics"]["auc"]
        report.append(f"AUC: {auc_bm:.4f}" if auc_bm is not None else "AUC: N/A")
        return report

    def generate_report(self, output_path: str = 'experiment_report.txt'):
        """
        生成实验报告（TXT）

        Parameters:
        -----------
        output_path : str
            报告保存路径
        """
        logger.info("生成实验报告(TXT)")
        report_text = "\n".join(self._compile_report_lines())
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        logger.info(f"实验报告已保存: {output_path}")

        return report_text

    @staticmethod
    def _wrap_report_lines_for_pdf(lines: List[str], max_chars: int = 96) -> str:
        """将过长行按固定宽度折断（附录等纯文本页用）。"""
        out: List[str] = []
        for line in lines:
            s = line if isinstance(line, str) else str(line)
            while len(s) > max_chars:
                out.append(s[:max_chars])
                s = s[max_chars:]
            out.append(s)
        return "\n".join(out)

    def generate_report_pdf(self, output_path: str) -> None:
        """
        导出多页 PDF（统一 A4 竖版、固定画布，避免 tight 裁切导致每页尺寸不一致）。

        仅使用 matplotlib.figure.Figure，避免 pyplot 与项目目录名 backend 冲突。
        """
        from datetime import datetime as dt
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.lines import Line2D
        from matplotlib.patches import FancyBboxPatch, Rectangle

        # ISO A4 portrait (inch) — 所有页相同，且不使用 bbox_inches='tight'
        a4_w, a4_h = 8.27, 11.69
        dpi = 120
        C = {
            "bg": "#f8fafc",
            "paper": "#ffffff",
            "primary": "#0f172a",
            "muted": "#64748b",
            "line": "#e2e8f0",
            "head": "#334155",
            "stripe": ("#ffffff", "#f1f5f9"),
        }

        logger.info("生成实验报告(PDF)")
        font_prop = _pdf_matplotlib_fontproperties()
        now_str = dt.now().strftime("%Y-%m-%d %H:%M")
        comparison_df = self.create_comparison_table()
        best_model = max(
            self.model_names,
            key=lambda x: self.results[x]["metrics"]["auc"] or 0,
        )
        best_auc = self.results[best_model]["metrics"]["auc"]

        page_counter = [0]

        def _footer(fig: Figure) -> None:
            page_counter[0] += 1
            fig.text(
                0.5,
                0.024,
                f"HeartCycle CAD  ·  {now_str[:10]}  ·  第 {page_counter[0]} 页",
                ha="center",
                fontsize=6.5,
                color="#94a3b8",
                fontproperties=font_prop,
                transform=fig.transFigure,
            )

        def _save(fig: Figure) -> None:
            _footer(fig)
            pdf.savefig(fig, dpi=dpi)

        def _section_title(fig: Figure, y: float, title: str, subtitle: str = "") -> float:
            """在页面顶部画章节标题，返回内容区起始 y（figure 坐标）。"""
            fig.text(
                0.09,
                y,
                title,
                fontsize=13,
                fontweight="bold",
                color=C["primary"],
                fontproperties=font_prop,
                transform=fig.transFigure,
                va="top",
            )
            if subtitle:
                fig.text(
                    0.09,
                    y - 0.028,
                    subtitle,
                    fontsize=8,
                    color=C["muted"],
                    fontproperties=font_prop,
                    transform=fig.transFigure,
                    va="top",
                )
            line_y = y - 0.038 if subtitle else y - 0.018
            fig.add_artist(
                Line2D(
                    [0.09, 0.91],
                    [line_y, line_y],
                    transform=fig.transFigure,
                    color=C["line"],
                    linewidth=0.9,
                    clip_on=False,
                )
            )
            return line_y - 0.02

        with PdfPages(output_path) as pdf:
            meta = pdf.infodict()
            meta["Title"] = "HeartCycle CAD 实验评估报告"
            meta["Author"] = "HeartCycle CAD System"

            # ----- 封面（简洁） -----
            fig = Figure(figsize=(a4_w, a4_h), dpi=dpi)
            fig.patch.set_facecolor(C["paper"])
            fig.add_artist(
                Rectangle(
                    (0.09, 0.78),
                    0.82,
                    0.12,
                    transform=fig.transFigure,
                    facecolor=C["primary"],
                    clip_on=False,
                )
            )
            fig.text(
                0.5,
                0.84,
                "实验评估报告",
                ha="center",
                va="center",
                fontsize=18,
                color="white",
                fontweight="bold",
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            fig.text(
                0.5,
                0.68,
                "HeartCycle CAD · 论文实验",
                ha="center",
                fontsize=11,
                color=C["primary"],
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            fig.text(
                0.5,
                0.62,
                "模型对比与测试集指标",
                ha="center",
                fontsize=9,
                color=C["muted"],
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            fig.text(
                0.5,
                0.18,
                f"{now_str}",
                ha="center",
                fontsize=9,
                color=C["muted"],
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            fig.text(
                0.5,
                0.14,
                f"{len(self.model_names)} 个模型",
                ha="center",
                fontsize=9,
                color=C["muted"],
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            _save(fig)

            # ----- 一、总览表（竖版；不加副标题，避免与表头列名视觉重复） -----
            fig = Figure(figsize=(a4_w, a4_h), dpi=dpi)
            fig.patch.set_facecolor(C["paper"])
            y0 = _section_title(fig, 0.94, "一、模型性能总览", "")
            ax = fig.add_axes([0.07, 0.09, 0.86, y0 - 0.06])
            ax.set_axis_off()
            ncols = len(comparison_df.columns)
            cols_list = list(comparison_df.columns)
            if ncols <= 1:
                col_w = [1.0]
            elif str(cols_list[0]).strip() == "模型":
                ml = int(comparison_df.iloc[:, 0].astype(str).str.len().max())
                w0 = min(0.46, max(0.30, 0.018 * ml + 0.14))
                rest = max(1.0 - w0, 0.01)
                col_w = [w0] + [rest / (ncols - 1)] * (ncols - 1)
            else:
                w0 = min(0.22, 0.9 / ncols)
                col_w = [w0] + [(1.0 - w0) / (ncols - 1)] * (ncols - 1)
            fs_tbl = 6.8 if ncols >= 9 else 7.6
            tbl = ax.table(
                cellText=comparison_df.values.tolist(),
                colLabels=cols_list,
                loc="upper center",
                cellLoc="center",
                colWidths=col_w,
                bbox=[0, 0.02, 1, 0.98],
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(fs_tbl)
            tbl.scale(1.0, 2.45)
            for (row, col), cell in tbl.get_celld().items():
                cell.set_edgecolor(C["line"])
                cell.set_linewidth(0.35)
                if row == 0:
                    cell.set_facecolor(C["head"])
                    cell.get_text().set_color("white")
                    cell.get_text().set_fontweight("bold")
                    if col == 0:
                        cell.get_text().set_ha("center")
                else:
                    cell.set_facecolor(C["stripe"][row % 2])
                    if col == 0:
                        cell.get_text().set_ha("left")
                        cell.get_text().set_wrap(True)
                cell.get_text().set_fontproperties(font_prop)
            _save(fig)

            # ----- 二、详细性能指标（均分整页内容区） -----
            models = list(self.model_names)
            # 每页条数随模型数变化，使单卡高度尽量落在 0.11–0.20 之间
            n_all = len(models)
            per_page = max(4, min(8, (n_all + 2) // 3 or 4))
            for start in range(0, n_all, per_page):
                chunk = models[start : start + per_page]
                fig = Figure(figsize=(a4_w, a4_h), dpi=dpi)
                fig.patch.set_facecolor(C["bg"])
                title = "二、详细性能指标" if start == 0 else "二、详细性能指标（续）"
                y_content_top = _section_title(fig, 0.94, title, "各模型在测试集上的主要指标")
                gap = 0.014
                bottom = 0.09
                n = len(chunk)
                usable = max(y_content_top - bottom - (n - 1) * gap, 0.05)
                card_h = usable / max(n, 1)
                fs_card = min(11.0, max(8.5, card_h * 52))

                for i, name in enumerate(chunk):
                    y_top = y_content_top - i * (card_h + gap)
                    y_bot = y_top - card_h
                    fig.add_artist(
                        FancyBboxPatch(
                            (0.09, y_bot),
                            0.82,
                            card_h,
                            transform=fig.transFigure,
                            boxstyle="round,pad=0.008,rounding_size=0.01",
                            facecolor=C["paper"],
                            edgecolor=C["line"],
                            linewidth=0.85,
                            clip_on=False,
                        )
                    )
                    m = self.results[name]["metrics"]
                    auc_s = f"{m['auc']:.4f}" if m["auc"] is not None else "N/A"
                    ap_s = f"{m['ap']:.4f}" if m["auc"] is not None else "N/A"
                    block = (
                        f"{name}\n"
                        f"准确率 {m['accuracy']:.4f}   精确率 {m['precision']:.4f}   召回率 {m['recall']:.4f}   F1 {m['f1']:.4f}\n"
                        f"灵敏度 {m['sensitivity']:.4f}   特异性 {m['specificity']:.4f}   AUC {auc_s}   AP {ap_s}"
                    )
                    fig.text(
                        0.11,
                        y_bot + card_h * 0.5,
                        block,
                        ha="left",
                        va="center",
                        fontsize=fs_card,
                        fontproperties=font_prop,
                        linespacing=1.35,
                        color=C["primary"],
                        transform=fig.transFigure,
                    )
                _save(fig)

            # ----- 三、最佳模型（居中留白） -----
            fig = Figure(figsize=(a4_w, a4_h), dpi=dpi)
            fig.patch.set_facecolor(C["paper"])
            _section_title(fig, 0.94, "三、最佳模型", "按测试集 AUC 选取")
            auc_txt = f"{best_auc:.4f}" if best_auc is not None else "N/A"
            fig.text(
                0.5,
                0.52,
                best_model,
                ha="center",
                va="center",
                fontsize=16,
                fontweight="bold",
                color=C["primary"],
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            fig.text(
                0.5,
                0.40,
                "AUC",
                ha="center",
                va="center",
                fontsize=10,
                color=C["muted"],
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            fig.text(
                0.5,
                0.30,
                auc_txt,
                ha="center",
                va="center",
                fontsize=28,
                fontweight="bold",
                color=C["head"],
                fontproperties=font_prop,
                transform=fig.transFigure,
            )
            _save(fig)

            # ----- 附录（正文区垂直居中、水平居中；略窄折行以配合居中版心） -----
            text = self._wrap_report_lines_for_pdf(self._compile_report_lines(), max_chars=56)
            line_chunks = text.split("\n")
            max_lines = 34
            for i in range(0, len(line_chunks), max_lines):
                chunk = "\n".join(line_chunks[i : i + max_lines])
                fig = Figure(figsize=(a4_w, a4_h), dpi=dpi)
                fig.patch.set_facecolor(C["paper"])
                y0 = _section_title(fig, 0.94, "附录", "")
                top_y = y0 - 0.06
                bot_y = 0.11
                mid_y = (top_y + bot_y) / 2
                fig.text(
                    0.5,
                    mid_y,
                    chunk,
                    ha="center",
                    va="center",
                    fontsize=9.4,
                    fontproperties=font_prop,
                    linespacing=1.32,
                    color="#334155",
                    transform=fig.transFigure,
                )
                _save(fig)

        logger.info("实验报告(PDF)已保存: %s", output_path)


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000

    y_true = np.random.randint(0, 2, n_samples)

    # 模拟不同模型的预测结果
    models = {
        'Logistic Regression': (0.78, 0.82),
        'Random Forest': (0.86, 0.90),
        'XGBoost': (0.89, 0.94),
        'LightGBM': (0.89, 0.94),
        'CNN': (0.91, 0.96),
        'LSTM': (0.92, 0.96)
    }

    evaluator = ExperimentEvaluator()

    for model_name, (acc, auc_score) in models.items():
        # 生成模拟预测
        y_prob = np.random.beta(2, 2, n_samples)
        y_prob = y_prob * (y_true * 0.7 + 0.3)  # 使预测与真实标签相关
        y_pred = (y_prob > 0.5).astype(int)

        # 调整以匹配目标准确率
        correct_mask = np.random.rand(n_samples) < acc
        y_pred[~correct_mask] = 1 - y_true[~correct_mask]

        # 评估模型
        evaluator.evaluate_model(model_name, y_true, y_pred, y_prob)

    # 创建对比表
    print("\n模型性能对比表:")
    print(evaluator.create_comparison_table())

    # 生成报告
    report = evaluator.generate_report()
    print("\n" + report)
