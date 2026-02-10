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
    model_type: Literal["lr", "svm", "rf", "xgb", "lgb", "stacking", "voting"] = Field("rf", description="模型类型")
    cv_folds: int = Field(5, ge=2, le=10, description="交叉验证折数")
    random_state: int = Field(42, description="随机种子")
    use_smote: bool = Field(True, description="是否使用SMOTE处理数据不平衡")
    optimize_hyperparams: bool = Field(False, description="是否进行超参数优化")


class TrainFromH5Request(BaseModel):
    """从H5文件训练模型请求"""
    data_dir: str = Field(..., description="数据目录路径（包含H5文件）")
    metadata_file: Optional[str] = Field(None, description="元数据CSV文件路径（可选）")
    label_file: Optional[str] = Field(None, description="标签CSV文件路径（可选，优先于元数据）")
    model_type: Literal["lr", "svm", "rf", "xgb", "lgb", "stacking", "voting"] = Field("rf", description="模型类型")
    cv_folds: int = Field(5, ge=2, le=10, description="交叉验证折数")
    random_state: int = Field(42, description="随机种子")
    use_smote: bool = Field(True, description="是否使用SMOTE处理数据不平衡")
    optimize_hyperparams: bool = Field(False, description="是否进行超参数优化")
    use_existing_rpeaks: bool = Field(True, description="是否使用已有R波标注")
    extract_hrv: bool = Field(True, description="是否提取HRV特征")
    extract_clinical: bool = Field(True, description="是否提取临床特征")


class TrainFromH5AutoRequest(BaseModel):
    """从H5文件训练模型请求（自动识别标签）"""
    h5_files: List[str] = Field(..., description="H5文件路径列表")
    auto_detect_labels: bool = Field(True, description="是否自动识别标签")
    metadata_file: Optional[str] = Field(None, description="元数据CSV文件路径（可选，留空则自动查找）")
    model_type: Literal["lr", "svm", "rf", "xgb", "lgb", "stacking", "voting"] = Field("rf", description="模型类型")
    cv_folds: int = Field(5, ge=2, le=10, description="交叉验证折数")
    random_state: int = Field(42, description="随机种子")
    use_smote: bool = Field(True, description="是否使用SMOTE处理数据不平衡")
    optimize_hyperparams: bool = Field(False, description="是否进行超参数优化")
    use_existing_rpeaks: bool = Field(True, description="是否使用已有R波标注")
    extract_hrv: bool = Field(True, description="是否提取HRV特征")
    extract_clinical: bool = Field(True, description="是否提取临床特征")


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
            random_state=request.random_state,
            use_smote=request.use_smote,
            optimize_hyperparams=request.optimize_hyperparams
        )

        logger.info(f"模型训练完成: {result['model_id']}")
        return ModelTrainingResponse(**result)
        
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"模型训练失败: {str(e)}")
        raise ModelTrainingError(str(e))


@router.post("/train/h5/auto")
async def train_from_h5_auto(request: TrainFromH5AutoRequest):
    """
    从H5文件训练模型（自动识别标签）

    该API支持直接上传H5文件列表，系统会自动：
    1. 查找同目录或父目录的SubjectMetadata.csv文件
    2. 从元数据文件中提取Disease_Status并生成标签
    3. 自动创建临时标签文件
    4. 启动训练任务

    Parameters:
    -----------
    request : TrainFromH5AutoRequest
        训练参数，包含H5文件列表

    Returns:
    --------
    dict : 包含task_id和标签统计信息的响应
    """
    try:
        from app.utils.h5_label_extractor import H5LabelExtractor
        import tempfile
        import os

        logger.info(f"启动H5自动标签训练: 收到 {len(request.h5_files)} 个H5文件")

        # 1. 验证H5文件存在
        missing_files = [f for f in request.h5_files if not os.path.exists(f)]
        if missing_files:
            raise HTTPException(
                status_code=400,
                detail=f"以下文件不存在: {missing_files[:5]}"  # 最多显示5个
            )

        # 2. 自动提取标签
        if request.auto_detect_labels:
            try:
                # 创建临时标签文件
                temp_label_file = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.csv',
                    delete=False,
                    dir=os.path.join(os.path.dirname(__file__), '../../../data/processed')
                )
                temp_label_path = temp_label_file.name
                temp_label_file.close()

                # 提取标签
                label_file_path, stats = H5LabelExtractor.create_label_file(
                    h5_files=request.h5_files,
                    output_path=temp_label_path,
                    metadata_file=request.metadata_file
                )

                logger.info(f"自动提取标签成功: {stats}")

            except Exception as e:
                logger.error(f"自动提取标签失败: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"自动提取标签失败: {str(e)}。请确保H5文件目录包含SubjectMetadata.csv文件，且包含File_Name和Disease_Status列。"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="auto_detect_labels必须为True"
            )

        # 3. 使用第一个H5文件所在目录作为data_dir
        data_dir = os.path.dirname(request.h5_files[0])

        # 4. 启动训练任务
        task_id = model_service.start_h5_training_task(
            data_dir=data_dir,
            metadata_file=request.metadata_file,
            label_file=label_file_path,
            model_type=request.model_type,
            cv_folds=request.cv_folds,
            random_state=request.random_state,
            use_smote=request.use_smote,
            optimize_hyperparams=request.optimize_hyperparams,
            use_existing_rpeaks=request.use_existing_rpeaks,
            extract_hrv=request.extract_hrv,
            extract_clinical=request.extract_clinical
        )

        logger.info(f"H5自动标签训练任务 {task_id} 已启动")

        return {
            "success": True,
            "message": "H5训练任务已启动（自动识别标签）",
            "data": {
                "task_id": task_id,
                "label_stats": stats,
                "h5_file_count": len(request.h5_files)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动H5自动标签训练失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动训练失败: {str(e)}")


@router.post("/train/h5")
async def start_h5_training(request: TrainFromH5Request):
    """
    启动从H5文件训练模型任务（异步）
    
    Parameters:
    -----------
    request : TrainFromH5Request
        训练参数
        
    Returns:
    --------
    dict : 包含task_id的响应
    """
    try:
        logger.info(f"启动H5文件训练任务: {request.model_type}, 数据目录: {request.data_dir}")
        
        task_id = model_service.start_h5_training_task(
            data_dir=request.data_dir,
            metadata_file=request.metadata_file,
            label_file=request.label_file,
            model_type=request.model_type,
            cv_folds=request.cv_folds,
            random_state=request.random_state,
            use_smote=request.use_smote,
            optimize_hyperparams=request.optimize_hyperparams,
            use_existing_rpeaks=request.use_existing_rpeaks,
            extract_hrv=request.extract_hrv,
            extract_clinical=request.extract_clinical
        )
        
        # 验证任务是否已创建
        status = model_service.get_h5_training_status(task_id)
        if status.get("status") == "not_found":
            logger.error(f"任务创建后立即查询失败: {task_id}")
            raise HTTPException(status_code=500, detail="任务创建失败，请重试")
        
        logger.info(f"H5训练任务 {task_id} 已成功启动，当前状态: {status.get('status')}")
        
        return {
            "success": True,
            "message": "H5训练任务已启动",
            "data": {
                "task_id": task_id
            }
        }
        
    except Exception as e:
        logger.error(f"启动H5训练任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动训练任务失败: {str(e)}")


@router.get("/train/h5/{task_id}")
async def get_h5_training_status(task_id: str):
    """
    查询H5训练任务状态
    
    Parameters:
    -----------
    task_id : str
        任务ID
        
    Returns:
    --------
    dict : 任务状态和结果
    """
    try:
        status = model_service.get_h5_training_status(task_id)
        
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        return {
            "success": True,
            "data": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询训练任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.delete("/models/{model_id}", response_model=BaseResponse)
async def delete_model(model_id: str):
    """
    删除模型
    
    Parameters:
    -----------
    model_id : str
        模型ID
        
    Returns:
    --------
    BaseResponse : 删除结果
    """
    try:
        result = model_service.delete_model(model_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "删除模型失败"))
        
        return {
            "success": True,
            "message": result.get("message", f"模型 {model_id} 已成功删除"),
            "data": {}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型失败: {str(e)}")
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

