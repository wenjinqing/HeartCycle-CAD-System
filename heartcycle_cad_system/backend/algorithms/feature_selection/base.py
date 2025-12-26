"""
特征选择算法基类
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Callable, Dict, Any
import numpy as np
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier


class BaseFeatureSelector(ABC):
    """特征选择算法基类"""
    
    def __init__(self, 
                 n_features: int = None,
                 estimator=None,
                 cv: int = 5,
                 scoring: str = 'roc_auc',
                 random_state: int = 42,
                 n_jobs: int = -1):
        """
        初始化特征选择器
        
        Parameters:
        -----------
        n_features : int, optional
            目标特征数量，None表示由算法决定
        estimator : sklearn estimator, optional
            用于评估特征子集的分类器，默认使用RandomForest
        cv : int
            交叉验证折数
        scoring : str
            评分指标
        random_state : int
            随机种子
        n_jobs : int
            并行任务数
        """
        self.n_features = n_features
        self.cv = cv
        self.scoring = scoring
        self.random_state = random_state
        self.n_jobs = n_jobs
        
        # 默认使用随机森林作为评估器
        if estimator is None:
            self.estimator = RandomForestClassifier(
                n_estimators=100,
                random_state=random_state,
                n_jobs=n_jobs
            )
        else:
            self.estimator = estimator
        
        # 结果存储
        self.best_features_ = None
        self.best_score_ = None
        self.history_ = []  # 记录每次迭代的最佳适应度
        
    def _evaluate_features(self, X: np.ndarray, y: np.ndarray, 
                          feature_mask: np.ndarray) -> float:
        """
        评估特征子集的适应度
        
        Parameters:
        -----------
        X : np.ndarray
            特征矩阵
        y : np.ndarray
            标签
        feature_mask : np.ndarray
            特征掩码（布尔数组或二进制数组）
            
        Returns:
        --------
        float : 适应度分数（交叉验证AUC）
        """
        # 转换为布尔掩码
        if feature_mask.dtype != bool:
            feature_mask = feature_mask.astype(bool)
        
        # 检查是否选择了至少一个特征
        if np.sum(feature_mask) == 0:
            return 0.0
        
        # 选择特征子集
        X_selected = X[:, feature_mask]
        
        try:
            # 交叉验证
            scores = cross_val_score(
                self.estimator, X_selected, y,
                cv=self.cv,
                scoring=self.scoring,
                n_jobs=self.n_jobs
            )
            return np.mean(scores)
        except Exception:
            return 0.0
    
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'BaseFeatureSelector':
        """
        执行特征选择
        
        Parameters:
        -----------
        X : np.ndarray
            特征矩阵 (n_samples, n_features)
        y : np.ndarray
            标签 (n_samples,)
            
        Returns:
        --------
        self : BaseFeatureSelector
            返回自身实例
        """
        pass
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        根据选择的特征转换数据
        
        Parameters:
        -----------
        X : np.ndarray
            特征矩阵
            
        Returns:
        --------
        np.ndarray : 转换后的特征矩阵
        """
        if self.best_features_ is None:
            raise ValueError("必须首先调用fit方法")
        
        return X[:, self.best_features_]
    
    def fit_transform(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        执行特征选择并转换数据
        
        Parameters:
        -----------
        X : np.ndarray
            特征矩阵
        y : np.ndarray
            标签
            
        Returns:
        --------
        np.ndarray : 转换后的特征矩阵
        """
        return self.fit(X, y).transform(X)
    
    def get_support(self, indices: bool = False) -> np.ndarray:
        """
        获取选择的特征
        
        Parameters:
        -----------
        indices : bool
            如果True，返回特征索引；如果False，返回布尔掩码
            
        Returns:
        --------
        np.ndarray : 特征选择结果
        """
        if self.best_features_ is None:
            raise ValueError("必须首先调用fit方法")
        
        if indices:
            return np.where(self.best_features_)[0]
        else:
            return self.best_features_
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取优化历史
        
        Returns:
        --------
        list : 历史记录列表
        """
        return self.history_


