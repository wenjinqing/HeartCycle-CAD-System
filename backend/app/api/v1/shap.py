"""
SHAP可解释性分析API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.shap_service import SHAPService
from app.core.logger import logger
from app.models.response import BaseResponse

router = APIRouter()
shap_service = SHAPService()


class InstanceExplainRequest(BaseModel):
    """单样本解释请求"""
    model_id: str = Field(..., description="模型ID")
    features: List[float] = Field(..., description="特征向量")


class GlobalExplainRequest(BaseModel):
    """全局解释请求"""
    model_id: str = Field(..., description="模型ID")
    training_data_file: Optional[str] = Field(None, description="训练数据文件路径（可选，CSV格式）")
    n_samples: int = Field(100, description="用于计算SHAP值的样本数", ge=1, le=1000)


@router.post("/shap/explain/instance", response_model=BaseResponse)
async def explain_instance(request: InstanceExplainRequest):
    """
    解释单个样本的预测结果（局部解释）
    
    这个端点分析单个预测结果，展示每个特征对该预测的贡献。
    
    Parameters:
    -----------
    request : InstanceExplainRequest
        包含模型ID和特征向量的请求
        
    Returns:
    --------
    dict : 解释结果
        - base_value: 基础值（模型的平均输出）
        - shap_values: SHAP值列表（每个特征一个值）
        - feature_values: 特征值列表
        - feature_names: 特征名称列表
        - prediction: 预测结果
        - probability: 预测概率
    """
    try:
        logger.info(f"SHAP单样本解释请求: 模型={request.model_id}, 特征数={len(request.features)}")
        
        result = shap_service.explain_instance(
            model_id=request.model_id,
            features=request.features
        )
        
        return BaseResponse(
            success=True,
            data=result,
            message="SHAP单样本解释成功"
        )
        
    except FileNotFoundError as e:
        logger.error(f"SHAP单样本解释失败: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"SHAP单样本解释失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"SHAP单样本解释失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SHAP单样本解释失败: {str(e)}")


@router.post("/shap/explain/global", response_model=BaseResponse)
async def explain_global(request: GlobalExplainRequest):
    """
    计算全局特征重要性（全局解释）
    
    这个端点分析模型的所有特征，展示每个特征对模型的整体贡献。
    
    Parameters:
    -----------
    request : GlobalExplainRequest
        包含模型ID和可选训练数据的请求
        
    Returns:
    --------
    dict : 全局重要性结果
        - feature_importance: 特征重要性字典（特征名 -> 平均绝对SHAP值）
        - feature_ranking: 特征排名列表（按重要性降序）
        - average_shap_values: 每个特征的平均SHAP值
    """
    try:
        logger.info(f"SHAP全局解释请求: 模型={request.model_id}, 样本数={request.n_samples}")
        
        result = shap_service.explain_global(
            model_id=request.model_id,
            training_data_file=request.training_data_file,
            n_samples=request.n_samples
        )
        
        return BaseResponse(
            success=True,
            data=result,
            message="SHAP全局解释成功"
        )
        
    except FileNotFoundError as e:
        logger.error(f"SHAP全局解释失败: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"SHAP全局解释失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"SHAP全局解释失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SHAP全局解释失败: {str(e)}")


@router.post("/shap/analyze")
async def analyze_shap(request: GlobalExplainRequest):
    """
    执行SHAP分析（兼容旧接口）
    
    Deprecated: 建议使用 /explain/global 或 /explain/instance
    
    Parameters:
    -----------
    request : GlobalExplainRequest
        SHAP分析参数
        
    Returns:
    --------
    dict : 分析结果
    """
    try:
        logger.warning("使用了已弃用的 /shap/analyze 接口，建议使用 /shap/explain/global")
        result = shap_service.explain_global(
            model_id=request.model_id,
            training_data_file=request.training_data_file,
            n_samples=request.n_samples
        )
        
        return {
            "model_id": request.model_id,
            "status": "completed",
            "shap_values": result.get("average_shap_values"),
            "visualizations": {
                "feature_importance": result.get("feature_importance"),
                "feature_ranking": result.get("feature_ranking")
            }
        }
        
    except Exception as e:
        logger.error(f"SHAP分析失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SHAP分析失败: {str(e)}")


@router.get("/shap/{model_id}")
async def get_shap_results(model_id: str):
    """
    获取SHAP分析结果（兼容旧接口）
    
    Deprecated: 建议直接使用 /explain/global 或 /explain/instance
    
    Parameters:
    -----------
    model_id : str
        模型ID
        
    Returns:
    --------
    dict : SHAP结果
    """
    logger.warning("使用了已弃用的 /shap/{model_id} 接口")
    return {
        "error": "此接口已弃用，请使用 /shap/explain/global 或 /shap/explain/instance"
    }
