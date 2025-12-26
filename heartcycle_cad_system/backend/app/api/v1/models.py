"""
模型训练API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from app.services.model_service import ModelService
from app.models.response import ModelTrainingResponse, ModelInfoResponse, PredictionResponse, BaseResponse
from app.core.exceptions import ModelTrainingError, InvalidParameterError
from app.core.logger import logger

router = APIRouter()
model_service = ModelService()


class TrainModelRequest(BaseModel):
    """模型训练请求"""
    feature_file: str = Field(..., description="特征文件路径")
    label_file: str = Field(..., description="标签文件路径")
    selected_features: Optional[List[int]] = Field(None, description="特征索引列表")
    model_type: Literal["lr", "svm", "rf"] = Field("rf", description="模型类型")
    cv_folds: int = Field(5, ge=2, le=10, description="交叉验证折数")
    random_state: int = Field(42, description="随机种子")


class PredictRequest(BaseModel):
    """预测请求"""
    model_id: str = Field(..., description="模型ID")
    features: List[float] = Field(..., description="特征向量", min_items=1)


@router.post("/train", response_model=ModelTrainingResponse)
async def train_model(request: TrainModelRequest):
    """
    训练模型
    
    Parameters:
    -----------
    request : TrainModelRequest
        训练参数
        
    Returns:
    --------
    ModelTrainingResponse : 训练结果
    """
    try:
        logger.info(f"开始训练模型: {request.model_type}, 特征文件: {request.feature_file}")
        
        result = model_service.train_model(
            feature_file=request.feature_file,
            label_file=request.label_file,
            selected_features=request.selected_features,
            model_type=request.model_type,
            cv_folds=request.cv_folds,
            random_state=request.random_state
        )
        
        logger.info(f"模型训练完成: {result['model_id']}")
        return ModelTrainingResponse(**result)
        
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"模型训练失败: {str(e)}")
        raise ModelTrainingError(str(e))


@router.get("/models", response_model=BaseResponse)
async def list_models():
    """
    获取模型列表
    
    Returns:
    --------
    dict : 模型列表
    """
    try:
        models = model_service.list_models()
        return {
            "success": True,
            "message": "获取模型列表成功",
            "data": {"models": models, "count": len(models)}
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", response_model=ModelInfoResponse)
async def get_model_info(model_id: str):
    """
    获取模型详细信息
    
    Parameters:
    -----------
    model_id : str
        模型ID
        
    Returns:
    --------
    ModelInfoResponse : 模型信息
    """
    try:
        info = model_service.get_model_info(model_id)
        if "error" in info:
            raise HTTPException(status_code=404, detail=info["error"])
        return ModelInfoResponse(**info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictRequest):
    """
    单样本预测
    
    Parameters:
    -----------
    request : PredictRequest
        预测请求（包含model_id和features）
        
    Returns:
    --------
    PredictionResponse : 预测结果
    """
    try:
        if not request.features or len(request.features) == 0:
            raise InvalidParameterError("特征向量不能为空")
        
        result = model_service.predict(request.model_id, request.features)
        return PredictionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class EnsemblePredictRequest(BaseModel):
    """集成预测请求"""
    model_ids: List[str] = Field(..., description="模型ID列表", min_items=1)
    features: List[float] = Field(..., description="特征向量", min_items=1)
    method: Literal["voting", "weighted"] = Field("voting", description="集成方法：voting（投票）或weighted（加权平均）")
    weights: Optional[List[float]] = Field(None, description="权重列表（用于加权平均）")


@router.post("/predict/ensemble", response_model=BaseResponse)
async def predict_ensemble(request: EnsemblePredictRequest):
    """
    集成预测（使用多个模型）
    
    Parameters:
    -----------
    request : EnsemblePredictRequest
        集成预测请求
        
    Returns:
    --------
    BaseResponse : 集成预测结果
    """
    try:
        from app.services.ensemble_service import EnsembleService
        
        if not request.features or len(request.features) == 0:
            raise InvalidParameterError("特征向量不能为空")
        
        if not request.model_ids or len(request.model_ids) == 0:
            raise InvalidParameterError("模型ID列表不能为空")
        
        ensemble_service = EnsembleService()
        result = ensemble_service.predict_ensemble(
            model_ids=request.model_ids,
            features=request.features,
            method=request.method,
            weights=request.weights
        )
        
        return {
            "success": True,
            "message": "集成预测成功",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"集成预测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class EnsembleInfoRequest(BaseModel):
    """集成模型信息请求"""
    model_ids: List[str] = Field(..., description="模型ID列表", min_items=1)


@router.post("/ensemble/info", response_model=BaseResponse)
async def get_ensemble_info(request: EnsembleInfoRequest):
    """
    获取集成模型信息
    
    Parameters:
    -----------
    request : EnsembleInfoRequest
        包含model_ids的请求
        
    Returns:
    --------
    BaseResponse : 集成模型信息
    """
    try:
        from app.services.ensemble_service import EnsembleService
        
        if not request.model_ids:
            raise InvalidParameterError("模型ID列表不能为空")
        
        ensemble_service = EnsembleService()
        info = ensemble_service.get_ensemble_info(request.model_ids)
        
        return {
            "success": True,
            "message": "获取集成模型信息成功",
            "data": info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取集成模型信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

