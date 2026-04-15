"""
报告生成服务
"""
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from io import BytesIO
import logging

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from ..core.config import settings

logger = logging.getLogger(__name__)

# ReportLab 全局字体名；避免重复 registerFont 失败
_CJK_FONT_REGISTERED_NAME = "HCReportCJK"
_cjk_font_resolved: Optional[str] = None


def _font_candidates(base_dir: str) -> List[Tuple[str, int]]:
    """
    (路径, subfontIndex)。.ttf 忽略 index；.ttc 需指定子字体索引（常见为 0）。
    """
    out: List[Tuple[str, int]] = []

    def add(path: str, subidx: int = 0) -> None:
        if path and os.path.isfile(path):
            out.append((path, subidx))

    add(os.path.join(base_dir, "fonts", "SimHei.ttf"))
    add(os.path.join(base_dir, "fonts", "NotoSansSC-Regular.ttf"))

    windir = os.environ.get("WINDIR", r"C:\Windows")
    win_fonts = os.path.join(windir, "Fonts")
    for fn in (
        "simhei.ttf",
        "SimHei.ttf",
        "simfang.ttf",
        "SimFang.ttf",
        "simsun.ttc",
        "msyh.ttc",
        "msyhbd.ttc",
        "msyhl.ttc",
    ):
        p = os.path.join(win_fonts, fn)
        if fn.endswith(".ttc"):
            add(p, 0)
        else:
            add(p)

    if sys.platform == "darwin":
        for p, idx in (
            ("/Library/Fonts/Arial Unicode.ttf", 0),
            ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
            ("/System/Library/Fonts/PingFang.ttc", 0),
        ):
            add(p, idx)

    for p, idx in (
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 0),
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttf", 0),
        ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
    ):
        add(p, idx)

    return out


def resolve_report_cjk_font(base_dir: Any) -> str:
    """
    注册并返回可用于中文的 ReportLab 字体名。
    若系统/项目均无可用字体，回退 Helvetica（中文会显示为方块）。
    """
    global _cjk_font_resolved
    if _cjk_font_resolved is not None:
        return _cjk_font_resolved

    if _CJK_FONT_REGISTERED_NAME in pdfmetrics.getRegisteredFontNames():
        _cjk_font_resolved = _CJK_FONT_REGISTERED_NAME
        return _cjk_font_resolved

    root = str(base_dir)
    for path, subidx in _font_candidates(root):
        try:
            low = path.lower()
            if low.endswith(".ttc"):
                pdfmetrics.registerFont(
                    TTFont(_CJK_FONT_REGISTERED_NAME, path, subfontIndex=subidx)
                )
            else:
                pdfmetrics.registerFont(TTFont(_CJK_FONT_REGISTERED_NAME, path))
            logger.info("报告 PDF 使用中文字体: %s", path)
            _cjk_font_resolved = _CJK_FONT_REGISTERED_NAME
            return _cjk_font_resolved
        except Exception as e:
            logger.debug("跳过字体 %s: %s", path, e)

    logger.warning(
        "未找到可用的中文字体（可在项目 fonts/ 下放置 SimHei.ttf 或 NotoSansSC-Regular.ttf），"
        "PDF 中文可能显示为方块"
    )
    _cjk_font_resolved = "Helvetica"
    return _cjk_font_resolved


def _mask_phone_display(phone: Optional[str]) -> str:
    """PDF/展示用脱敏手机号"""
    if not phone or not str(phone).strip():
        return "-"
    s = str(phone).strip()
    if len(s) <= 4:
        return "****"
    if len(s) >= 11:
        return f"{s[:3]}****{s[-4:]}"
    return f"{s[:2]}****{s[-2:]}"


class ReportService:
    """报告生成服务"""

    def __init__(self):
        self.reports_dir = os.path.join(settings.BASE_DIR, 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)
        self.chinese_font = resolve_report_cjk_font(str(settings.BASE_DIR))

    def generate_prediction_report(
        self,
        patient_info: Dict,
        prediction_data: Dict,
        statistics: Optional[Dict] = None
    ) -> str:
        """
        生成预测报告PDF

        Parameters:
        -----------
        patient_info : Dict
            患者信息
        prediction_data : Dict
            预测数据
        statistics : Optional[Dict]
            统计信息

        Returns:
        --------
        str : PDF文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        patient_no = patient_info.get('patient_no', 'unknown')
        filename = f"report_{patient_no}_{timestamp}.pdf"
        filepath = os.path.join(self.reports_dir, filename)

        # 创建PDF文档
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # 构建内容
        story = []
        styles = getSampleStyleSheet()

        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=self.chinese_font
        )

        # 标题
        title = Paragraph("冠心病风险预测报告", title_style)
        story.append(title)
        story.append(Spacer(1, 0.5*cm))

        # 报告信息
        report_info_style = ParagraphStyle(
            'ReportInfo',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_RIGHT,
            fontName=self.chinese_font
        )
        report_info = Paragraph(
            f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            report_info_style
        )
        story.append(report_info)
        story.append(Spacer(1, 0.5*cm))

        # 患者基本信息
        story.append(self._create_section_title("患者基本信息", styles))
        story.append(self._create_patient_info_table(patient_info))
        story.append(Spacer(1, 0.4*cm))
        story.append(self._create_section_title("体征、实验室与危险因素", styles))
        story.append(self._create_patient_clinical_table(patient_info))
        story.append(Spacer(1, 0.5*cm))

        # 预测结果
        story.append(self._create_section_title("预测结果", styles))
        prediction_table = self._create_prediction_table(prediction_data)
        story.append(prediction_table)
        story.append(Spacer(1, 0.5*cm))

        # 风险评估
        story.append(self._create_section_title("风险评估", styles))
        risk_assessment = self._create_risk_assessment(prediction_data)
        story.append(risk_assessment)
        story.append(Spacer(1, 0.5*cm))

        # 统计信息（如果有）
        if statistics:
            story.append(self._create_section_title("历史统计", styles))
            stats_table = self._create_statistics_table(statistics)
            story.append(stats_table)
            story.append(Spacer(1, 0.5*cm))

        # 建议
        story.append(self._create_section_title("医疗建议", styles))
        recommendations = self._create_recommendations(prediction_data)
        story.append(recommendations)
        story.append(Spacer(1, 0.5*cm))

        # 免责声明
        story.append(Spacer(1, 1*cm))
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName=self.chinese_font
        )
        disclaimer = Paragraph(
            "本报告仅供参考，不能替代医生的专业诊断。如有疑问，请咨询专业医生。",
            disclaimer_style
        )
        story.append(disclaimer)

        # 生成PDF
        doc.build(story)
        logger.info(f"生成报告: {filepath}")

        return filepath

    def _create_section_title(self, title: str, styles) -> Paragraph:
        """创建章节标题"""
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=10,
            fontName=self.chinese_font
        )
        return Paragraph(title, section_style)

    def _gender_display(self, g: Any) -> str:
        if g == 'male':
            return '男'
        if g == 'female':
            return '女'
        return '-'

    def _fmt_cell(self, v: Any, suffix: str = '') -> str:
        if v is None or v == '':
            return '-'
        try:
            if isinstance(v, float):
                return f'{v:.2f}{suffix}'
            return f'{v}{suffix}'
        except Exception:
            return str(v)

    def _create_patient_info_table(self, patient_info: Dict) -> Table:
        """身份与联系信息"""
        data = [
            ['患者编号', patient_info.get('patient_no', '-'), '姓名', patient_info.get('name', '-')],
            ['性别', self._gender_display(patient_info.get('gender')), '年龄', f"{patient_info.get('age', '-')} 岁"],
            ['手机号', _mask_phone_display(patient_info.get('phone')), '紧急联系人', patient_info.get('emergency_contact') or '-'],
            ['职业', patient_info.get('occupation') or '-', '地址', patient_info.get('address') or '-'],
        ]
        return self._styled_four_col_table(data)

    def _create_patient_clinical_table(self, patient_info: Dict) -> Table:
        """体征、血脂血糖、生活方式与危险因素"""
        sysv = patient_info.get('blood_pressure_systolic')
        diav = patient_info.get('blood_pressure_diastolic')
        bp = '-'
        if sysv is not None or diav is not None:
            bp = f"{sysv if sysv is not None else '-'}/{diav if diav is not None else '-'} mmHg"

        smoke_map = {'never': '从不', 'former': '已戒', 'current': '目前吸烟', '': '-'}
        act_map = {
            'unknown': '不详', 'sedentary': '久坐少动', 'light': '轻度',
            'moderate': '中度', 'heavy': '重度', '': '-'
        }
        ss = patient_info.get('smoke_status') or ''
        pa = patient_info.get('physical_activity') or ''

        def yn(x):
            if x == 1:
                return '是'
            if x == 0:
                return '否'
            return '-'

        data = [
            ['身高(cm)', self._fmt_cell(patient_info.get('height_cm')), '体重(kg)', self._fmt_cell(patient_info.get('weight_kg'))],
            ['腰围(cm)', self._fmt_cell(patient_info.get('waist_cm')), '静息心率', self._fmt_cell(patient_info.get('resting_heart_rate'), ' 次/分')],
            ['血压', bp, 'HRV平均RR(ms)', self._fmt_cell(patient_info.get('hrv_mean_rr'))],
            ['SDNN', self._fmt_cell(patient_info.get('hrv_sdnn')), 'RMSSD', self._fmt_cell(patient_info.get('hrv_rmssd'))],
            ['pNN50', self._fmt_cell(patient_info.get('hrv_pnn50')), 'LF/HF', self._fmt_cell(patient_info.get('hrv_lf_hf_ratio'))],
            ['总胆固醇', self._fmt_cell(patient_info.get('total_cholesterol'), ' mmol/L'), 'LDL-C', self._fmt_cell(patient_info.get('ldl_cholesterol'), ' mmol/L')],
            ['HDL-C', self._fmt_cell(patient_info.get('hdl_cholesterol'), ' mmol/L'), '甘油三酯', self._fmt_cell(patient_info.get('triglyceride'), ' mmol/L')],
            ['空腹血糖', self._fmt_cell(patient_info.get('fasting_glucose'), ' mmol/L'), 'HbA1c', self._fmt_cell(patient_info.get('hba1c'), ' %')],
            ['吸烟', smoke_map.get(ss, ss or '-'), '体力活动', act_map.get(pa, pa or '-')],
            ['糖尿病', yn(patient_info.get('diabetes')), '高血压(诊断)', yn(patient_info.get('hypertension_dx'))],
            ['血脂异常', yn(patient_info.get('dyslipidemia')), '早发冠心病家族史', yn(patient_info.get('family_history_cad'))],
            ['胸痛/心绞痛症状', yn(patient_info.get('chest_pain_symptom')), '', ''],
        ]
        return self._styled_four_col_table(data)

    def _styled_four_col_table(self, data) -> Table:
        table = Table(data, colWidths=[3 * cm, 5 * cm, 3 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        return table

    def _format_probability_display(self, probability: Any) -> str:
        """prediction_records.probability 可能为 JSON 数组字符串或列表"""
        if probability is None:
            return '-'
        if isinstance(probability, str):
            s = probability.strip()
            if s.startswith('['):
                try:
                    arr = json.loads(s)
                    if isinstance(arr, (list, tuple)) and len(arr) >= 2:
                        return f'{float(arr[1]) * 100:.2f}% (阳性类概率)'
                    if isinstance(arr, (list, tuple)) and len(arr) == 1:
                        return f'{float(arr[0]) * 100:.2f}%'
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            try:
                return f'{float(s) * 100:.2f}%'
            except (ValueError, TypeError):
                return s
        if isinstance(probability, (list, tuple)) and len(probability) >= 2:
            try:
                return f'{float(probability[1]) * 100:.2f}% (阳性类概率)'
            except (ValueError, TypeError):
                return str(probability)
        try:
            return f'{float(probability) * 100:.2f}%'
        except (ValueError, TypeError):
            return str(probability)

    def _positive_class_probability(self, probability: Any) -> float:
        """用于文中叙述的阳性类概率 [0,1]"""
        if probability is None:
            return 0.0
        if isinstance(probability, str):
            s = probability.strip()
            if s.startswith('['):
                try:
                    arr = json.loads(s)
                    if isinstance(arr, (list, tuple)) and len(arr) >= 2:
                        return float(arr[1])
                    if isinstance(arr, (list, tuple)) and len(arr) >= 1:
                        return float(arr[0])
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            try:
                return float(s)
            except (ValueError, TypeError):
                return 0.0
        if isinstance(probability, (list, tuple)) and len(probability) >= 2:
            try:
                return float(probability[1])
            except (ValueError, TypeError):
                return 0.0
        try:
            return float(probability)
        except (ValueError, TypeError):
            return 0.0

    def _create_prediction_table(self, prediction_data: Dict) -> Table:
        """创建预测结果表格"""
        prediction = prediction_data.get('prediction', 0)
        probability = prediction_data.get('probability', '0.0')
        risk_level = prediction_data.get('risk_level', 'unknown')
        model_id = prediction_data.get('model_id', 'unknown')

        # 风险等级文本和颜色
        risk_text = {
            'low': '低风险',
            'medium': '中风险',
            'high': '高风险'
        }.get(risk_level, risk_level)

        risk_color = {
            'low': colors.green,
            'medium': colors.orange,
            'high': colors.red
        }.get(risk_level, colors.grey)

        prob_display = self._format_probability_display(probability)

        data = [
            ['预测结果', '有风险' if prediction == 1 else '无风险'],
            ['风险概率', prob_display],
            ['风险等级', risk_text],
            ['使用模型', model_id],
            ['预测时间', prediction_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))],
        ]

        table = Table(data, colWidths=[4*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('TEXTCOLOR', (1, 2), (1, 2), risk_color),  # 风险等级颜色
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        return table

    def _create_risk_assessment(self, prediction_data: Dict) -> Paragraph:
        """创建风险评估文本"""
        risk_level = prediction_data.get('risk_level', 'unknown')
        probability = self._positive_class_probability(prediction_data.get('probability', 0))

        assessment_text = ""
        if risk_level == 'low':
            assessment_text = f"根据预测模型分析，您的冠心病风险较低（风险概率：{probability*100:.2f}%）。建议保持健康的生活方式，定期体检。"
        elif risk_level == 'medium':
            assessment_text = f"根据预测模型分析，您的冠心病风险处于中等水平（风险概率：{probability*100:.2f}%）。建议加强健康管理，定期监测心血管健康指标。"
        elif risk_level == 'high':
            assessment_text = f"根据预测模型分析，您的冠心病风险较高（风险概率：{probability*100:.2f}%）。强烈建议尽快就医，进行详细的心血管检查。"
        else:
            assessment_text = "无法评估风险等级。"

        style = ParagraphStyle(
            'Assessment',
            fontSize=11,
            leading=16,
            fontName=self.chinese_font
        )

        return Paragraph(assessment_text, style)

    def _create_statistics_table(self, statistics: Dict) -> Table:
        """创建统计信息表格"""
        pred_stats = statistics.get('prediction_statistics', {})

        data = [
            ['统计项', '数值'],
            ['总预测次数', str(pred_stats.get('total_predictions', 0))],
            ['高风险次数', str(pred_stats.get('high_risk_count', 0))],
            ['中风险次数', str(pred_stats.get('medium_risk_count', 0))],
            ['低风险次数', str(pred_stats.get('low_risk_count', 0))],
        ]

        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        return table

    def _create_recommendations(self, prediction_data: Dict) -> Paragraph:
        """创建医疗建议"""
        risk_level = prediction_data.get('risk_level', 'unknown')

        recommendations = {
            'low': [
                "1. 保持健康的饮食习惯，多吃蔬菜水果，少吃高脂肪食物",
                "2. 坚持适量运动，每周至少150分钟中等强度运动",
                "3. 戒烟限酒，保持良好的生活习惯",
                "4. 定期体检，每年至少一次心血管检查",
                "5. 保持心情愉悦，避免过度压力"
            ],
            'medium': [
                "1. 密切监测血压、血脂、血糖等指标",
                "2. 调整饮食结构，减少盐分和脂肪摄入",
                "3. 增加运动量，建议在医生指导下制定运动计划",
                "4. 定期复查，每3-6个月进行一次心血管检查",
                "5. 如有不适症状（胸闷、胸痛等），及时就医",
                "6. 考虑在医生指导下进行药物预防"
            ],
            'high': [
                "1. 立即就医，进行详细的心血管检查（心电图、冠脉造影等）",
                "2. 在医生指导下进行药物治疗",
                "3. 严格控制血压、血脂、血糖",
                "4. 避免剧烈运动和情绪激动",
                "5. 随身携带急救药物（如硝酸甘油）",
                "6. 定期复查，密切监测病情变化",
                "7. 必要时考虑介入治疗或手术治疗"
            ]
        }

        rec_list = recommendations.get(risk_level, ["请咨询专业医生获取建议"])
        rec_text = "<br/>".join(rec_list)

        style = ParagraphStyle(
            'Recommendations',
            fontSize=10,
            leading=14,
            fontName=self.chinese_font
        )

        return Paragraph(rec_text, style)

    def generate_batch_report(
        self,
        predictions: list,
        summary: Dict
    ) -> str:
        """
        生成批量预测报告

        Parameters:
        -----------
        predictions : list
            预测结果列表
        summary : Dict
            汇总信息

        Returns:
        --------
        str : PDF文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_report_{timestamp}.pdf"
        filepath = os.path.join(self.reports_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []
        styles = getSampleStyleSheet()

        # 标题
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=self.chinese_font
        )
        title = Paragraph("批量预测报告", title_style)
        story.append(title)
        story.append(Spacer(1, 0.5*cm))

        # 汇总信息
        story.append(self._create_section_title("预测汇总", styles))
        summary_table = self._create_batch_summary_table(summary)
        story.append(summary_table)
        story.append(Spacer(1, 0.5*cm))

        # 详细结果
        story.append(self._create_section_title("详细结果", styles))
        results_table = self._create_batch_results_table(predictions)
        story.append(results_table)

        # 生成PDF
        doc.build(story)
        logger.info(f"生成批量报告: {filepath}")

        return filepath

    def _create_batch_summary_table(self, summary: Dict) -> Table:
        """创建批量预测汇总表格"""
        data = [
            ['统计项', '数值'],
            ['总预测数', str(summary.get('total', 0))],
            ['有风险', str(summary.get('positive', 0))],
            ['无风险', str(summary.get('negative', 0))],
            ['高风险', str(summary.get('high_risk', 0))],
            ['中风险', str(summary.get('medium_risk', 0))],
            ['低风险', str(summary.get('low_risk', 0))],
        ]

        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        return table

    def _create_batch_results_table(self, predictions: list) -> Table:
        """创建批量预测结果表格"""
        data = [['序号', '预测结果', '风险概率', '风险等级']]

        for i, pred in enumerate(predictions[:50], 1):  # 最多显示50条
            prediction = pred.get('prediction', 0)
            probability = pred.get('probability', '0.0')
            risk_level = pred.get('risk_level', 'unknown')

            risk_text = {
                'low': '低风险',
                'medium': '中风险',
                'high': '高风险'
            }.get(risk_level, risk_level)

            data.append([
                str(i),
                '有风险' if prediction == 1 else '无风险',
                f"{float(probability) * 100:.2f}%",
                risk_text
            ])

        table = Table(data, colWidths=[2*cm, 4*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        return table

    def delete_report(self, filename: str) -> bool:
        """
        删除报告文件

        Parameters:
        -----------
        filename : str
            文件名

        Returns:
        --------
        bool : 是否成功
        """
        filepath = os.path.join(self.reports_dir, filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"删除报告: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除报告失败: {e}")
            return False

    def list_reports(self) -> list:
        """
        列出所有报告

        Returns:
        --------
        list : 报告文件列表
        """
        try:
            files = []
            for filename in os.listdir(self.reports_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(self.reports_dir, filename)
                    stat = os.stat(filepath)
                    files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
            return sorted(files, key=lambda x: x['created_at'], reverse=True)
        except Exception as e:
            logger.error(f"列出报告失败: {e}")
            return []
