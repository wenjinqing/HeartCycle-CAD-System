"""
特征提取API
"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.feature_service import FeatureService

router = APIRouter()
feature_service = FeatureService()


class ExtractFeaturesRequest(BaseModel):
    """特征提取请求"""
    file_path: str
    use_existing_rpeaks: bool = True
    extract_hrv: bool = True
    extract_clinical: bool = True


@router.post("/extract-features")
async def extract_features(request: ExtractFeaturesRequest, background_tasks: BackgroundTasks):
    """
    触发特征提取任务
    
    Parameters:
    -----------
    request : ExtractFeaturesRequest
        特征提取请求参数
        
    Returns:
    --------
    dict : 任务信息
    """
    # TODO: 实现异步任务队列
    task_id = feature_service.start_extraction(
        file_path=request.file_path,
        use_existing_rpeaks=request.use_existing_rpeaks,
        extract_hrv=request.extract_hrv,
        extract_clinical=request.extract_clinical
    )
    
    return {
        "message": "特征提取任务已启动",
        "task_id": task_id
    }


@router.get("/features/{task_id}")
async def get_feature_extraction_status(task_id: str):
    """
    查询特征提取任务状态
    
    Parameters:
    -----------
    task_id : str
        任务ID
        
    Returns:
    --------
    dict : 任务状态和结果
    """
    status = feature_service.get_task_status(task_id)
    return status


@router.get("/features")
async def list_features():
    """
    获取已提取的特征列表
    
    Returns:
    --------
    dict : 特征列表
    """
    features = feature_service.list_features()
    return {"features": features}


