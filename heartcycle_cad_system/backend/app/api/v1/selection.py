"""
特征选择API
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal, Optional
from app.services.selection_service import SelectionService

router = APIRouter()
selection_service = SelectionService()


class FeatureSelectionRequest(BaseModel):
    """特征选择请求"""
    feature_file: str
    label_file: str
    algorithm: Literal["ga", "pso", "hybrid"] = "ga"
    n_features: Optional[int] = None  # 目标特征数，None表示由算法决定
    population_size: int = 50  # GA种群大小 / PSO粒子数
    n_iterations: int = 100  # 迭代次数
    crossover_rate: float = 0.8  # GA交叉率
    mutation_rate: float = 0.1  # GA变异率
    w: float = 0.9  # PSO惯性权重
    c1: float = 2.0  # PSO个体学习因子
    c2: float = 2.0  # PSO社会学习因子


@router.post("/feature-selection")
async def start_feature_selection(request: FeatureSelectionRequest):
    """
    启动特征选择任务
    
    Parameters:
    -----------
    request : FeatureSelectionRequest
        特征选择参数
        
    Returns:
    --------
    dict : 任务信息
    """
    task_id = selection_service.start_selection(
        feature_file=request.feature_file,
        label_file=request.label_file,
        algorithm=request.algorithm,
        **request.dict(exclude={'feature_file', 'label_file', 'algorithm'})
    )
    
    return {
        "message": "特征选择任务已启动",
        "task_id": task_id
    }


@router.get("/selection/{task_id}")
async def get_selection_status(task_id: str):
    """
    查询特征选择任务状态
    
    Parameters:
    -----------
    task_id : str
        任务ID
        
    Returns:
    --------
    dict : 任务状态和结果
    """
    status = selection_service.get_task_status(task_id)
    return status

