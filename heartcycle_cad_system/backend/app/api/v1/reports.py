"""
报告生成 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict
import os

from ...services.report_service import ReportService
from ...services.patient_service import PatientService, patient_to_report_dict
from ...models.response import APIResponse
from ...db.base import get_db
from ..deps import get_current_user, require_doctor_or_researcher, require_staff, assert_user_can_access_patient
from ...models.user import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/reports", tags=["报告生成"])


class PredictionReportRequest(BaseModel):
    """预测报告请求"""
    patient_id: int = Field(..., description="患者ID")
    prediction_id: int = Field(..., description="预测记录ID")
    include_statistics: bool = Field(default=True, description="是否包含统计信息")


class BatchReportRequest(BaseModel):
    """批量报告请求"""
    predictions: list = Field(..., description="预测结果列表")
    summary: Dict = Field(..., description="汇总信息")


@router.post("/prediction", response_model=APIResponse, summary="生成预测报告")
async def generate_prediction_report(
    request: PredictionReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成患者预测报告PDF

    包含:
    - 患者基本信息
    - 预测结果
    - 风险评估
    - 历史统计（可选）
    - 医疗建议
    """
    report_service = ReportService()
    patient_service = PatientService(db)

    try:
        # 获取患者信息
        patient = patient_service.get_patient(request.patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在")

        assert_user_can_access_patient(current_user, patient, db)

        # 获取预测记录
        predictions, _ = patient_service.get_patient_predictions(
            request.patient_id,
            skip=0,
            limit=1000
        )

        prediction_record = next(
            (p for p in predictions if p.id == request.prediction_id),
            None
        )

        if not prediction_record:
            raise HTTPException(status_code=404, detail="预测记录不存在")

        # 准备患者信息（含体征、实验室、危险因素，供 PDF 展示）
        patient_info = patient_to_report_dict(patient)

        # 准备预测数据
        prediction_data = {
            'prediction': prediction_record.prediction,
            'probability': prediction_record.probability,
            'risk_level': prediction_record.risk_level,
            'model_id': prediction_record.model_id,
            'created_at': prediction_record.created_at.strftime('%Y-%m-%d %H:%M:%S') if prediction_record.created_at else None
        }

        # 获取统计信息（如果需要）
        statistics = None
        if request.include_statistics:
            statistics = patient_service.get_patient_statistics(request.patient_id)

        # 生成报告
        report_path = report_service.generate_prediction_report(
            patient_info=patient_info,
            prediction_data=prediction_data,
            statistics=statistics
        )

        filename = os.path.basename(report_path)

        return APIResponse(
            success=True,
            message="报告生成成功",
            data={
                'filename': filename,
                'download_url': f"/api/v1/reports/download/{filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"生成报告失败: {str(e)}"
        )


@router.post("/batch", response_model=APIResponse, summary="生成批量报告")
async def generate_batch_report(
    request: BatchReportRequest,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    生成批量预测报告PDF

    包含:
    - 预测汇总统计
    - 详细预测结果列表
    """
    report_service = ReportService()

    try:
        # 生成报告
        report_path = report_service.generate_batch_report(
            predictions=request.predictions,
            summary=request.summary
        )

        filename = os.path.basename(report_path)

        return APIResponse(
            success=True,
            message="批量报告生成成功",
            data={
                'filename': filename,
                'download_url': f"/api/v1/reports/download/{filename}"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"生成批量报告失败: {str(e)}"
        )


@router.get("/download/{filename}", summary="下载报告")
async def download_report(
    filename: str,
    current_user: User = Depends(require_staff)
):
    """
    下载报告文件
    """
    report_service = ReportService()
    filepath = os.path.join(report_service.reports_dir, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        filepath,
        media_type='application/pdf',
        filename=filename
    )


@router.get("/list", response_model=APIResponse, summary="列出所有报告")
async def list_reports(
    current_user: User = Depends(require_staff)
):
    """
    列出所有报告文件
    """
    report_service = ReportService()

    try:
        reports = report_service.list_reports()

        return APIResponse(
            success=True,
            message=f"找到 {len(reports)} 个报告",
            data=reports
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出报告失败: {str(e)}"
        )


@router.delete("/{filename}", response_model=APIResponse, summary="删除报告")
async def delete_report(
    filename: str,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    删除报告文件
    """
    report_service = ReportService()

    try:
        success = report_service.delete_report(filename)

        if success:
            return APIResponse(
                success=True,
                message="报告已删除"
            )
        else:
            raise HTTPException(status_code=404, detail="报告文件不存在")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除报告失败: {str(e)}"
        )
