"""
SHAP可解释性分析API
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.services.shap_service import SHAPService

router = APIRouter()
shap_service = SHAPService()


class SHAPAnalysisRequest(BaseModel):
    """SHAP分析请求"""
    model_id: str
    test_data_file: Optional[str] = None
    n_samples: int = 100  # 用于计算SHAP值的样本数


@router.post("/shap/analyze")
async def analyze_shap(request: SHAPAnalysisRequest):
    """
    执行SHAP分析
    
    Parameters:
    -----------
    request : SHAPAnalysisRequest
        SHAP分析参数
        
    Returns:
    --------
    dict : 分析结果
    """
    result = shap_service.analyze(
        model_id=request.model_id,
        test_data_file=request.test_data_file,
        n_samples=request.n_samples
    )
    
    return result


@router.get("/shap/{model_id}")
async def get_shap_results(model_id: str):
    """
    获取SHAP分析结果
    
    Parameters:
    -----------
    model_id : str
        模型ID
        
    Returns:
    --------
    dict : SHAP结果
    """
    results = shap_service.get_results(model_id)
    return results


