"""
模型训练与评估模块
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report
)
import joblib
import os
from datetime import datetime
from app.core.config import settings
from app.core.utils import ensure_dir, get_model_file_path
from app.core.logger import logger


class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, random_state: int = 42):
        """
        初始化模型训练器
        
        Parameters:
        -----------
        random_state : int
            随机种子
        """
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = None
        self.model_type = None
        self.feature_names = None
        self.selected_features = None
        
    def _create_model(self, model_type: str, **kwargs):
        """
        创建模型实例
        
        Parameters:
        -----------
        model_type : str
            模型类型（lr/svm/rf）
        **kwargs : dict
            模型超参数
        """
        if model_type == "lr":
            self.model = LogisticRegression(
                random_state=self.random_state,
                max_iter=1000,
                **kwargs
            )
        elif model_type == "svm":
            self.model = SVC(
                probability=True,
                random_state=self.random_state,
                **kwargs
            )
        elif model_type == "rf":
            self.model = RandomForestClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', None),
                random_state=self.random_state,
                n_jobs=-1
            )
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
        
        self.model_type = model_type
    
    def train(self, 
              X: np.ndarray, 
              y: np.ndarray,
              model_type: str = "rf",
              cv_folds: int = 5,
              selected_features: Optional[List[int]] = None,
              feature_names: Optional[List[str]] = None,
              **model_params) -> Dict[str, Any]:
        """
        训练模型
        
        Parameters:
        -----------
        X : np.ndarray
            特征矩阵
        y : np.ndarray
            标签
        model_type : str
            模型类型（lr/svm/rf）
        cv_folds : int
            交叉验证折数
        selected_features : List[int], optional
            选择的特征索引
        feature_names : List[str], optional
            特征名称
        **model_params : dict
            模型超参数
            
        Returns:
        --------
        dict : 训练结果和评估指标
        """
        # 选择特征
        if selected_features is not None:
            X = X[:, selected_features]
            self.selected_features = selected_features
            if feature_names:
                self.feature_names = [feature_names[i] for i in selected_features]
        else:
            self.feature_names = feature_names
        
        # 数据标准化（SVM和LR需要）
        if model_type in ["lr", "svm"]:
            X = self.scaler.fit_transform(X)
        
        # 创建模型
        self._create_model(model_type, **model_params)
        
        # 交叉验证
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        cv_scores_accuracy = cross_val_score(self.model, X, y, cv=cv, scoring='accuracy', n_jobs=-1)
        cv_scores_precision = cross_val_score(self.model, X, y, cv=cv, scoring='precision', n_jobs=-1)
        cv_scores_recall = cross_val_score(self.model, X, y, cv=cv, scoring='recall', n_jobs=-1)
        cv_scores_f1 = cross_val_score(self.model, X, y, cv=cv, scoring='f1', n_jobs=-1)
        cv_scores_roc_auc = cross_val_score(self.model, X, y, cv=cv, scoring='roc_auc', n_jobs=-1)
        
        # 训练最终模型
        self.model.fit(X, y)
        
        # 计算最终评估指标
        y_pred = self.model.predict(X)
        y_pred_proba = self.model.predict_proba(X)[:, 1] if hasattr(self.model, 'predict_proba') else None
        
        metrics = {
            'accuracy': {
                'mean': float(np.mean(cv_scores_accuracy)),
                'std': float(np.std(cv_scores_accuracy)),
                'scores': cv_scores_accuracy.tolist()
            },
            'precision': {
                'mean': float(np.mean(cv_scores_precision)),
                'std': float(np.std(cv_scores_precision)),
                'scores': cv_scores_precision.tolist()
            },
            'recall': {
                'mean': float(np.mean(cv_scores_recall)),
                'std': float(np.std(cv_scores_recall)),
                'scores': cv_scores_recall.tolist()
            },
            'f1': {
                'mean': float(np.mean(cv_scores_f1)),
                'std': float(np.std(cv_scores_f1)),
                'scores': cv_scores_f1.tolist()
            },
            'roc_auc': {
                'mean': float(np.mean(cv_scores_roc_auc)),
                'std': float(np.std(cv_scores_roc_auc)),
                'scores': cv_scores_roc_auc.tolist()
            }
        }
        
        # 混淆矩阵
        cm = confusion_matrix(y, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        
        # 计算最终准确率
        metrics['final_accuracy'] = float(accuracy_score(y, y_pred))
        metrics['final_precision'] = float(precision_score(y, y_pred))
        metrics['final_recall'] = float(recall_score(y, y_pred))
        metrics['final_f1'] = float(f1_score(y, y_pred))
        
        if y_pred_proba is not None:
            metrics['final_roc_auc'] = float(roc_auc_score(y, y_pred_proba))
        
        logger.info(f"模型训练完成: {model_type}, CV AUC: {metrics['roc_auc']['mean']:.4f}")
        
        return {
            'model_type': model_type,
            'metrics': metrics,
            'cv_folds': cv_folds,
            'n_features': X.shape[1],
            'n_samples': X.shape[0]
        }
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测
        
        Parameters:
        -----------
        X : np.ndarray
            特征矩阵
            
        Returns:
        --------
        predictions : np.ndarray
            预测类别
        probabilities : np.ndarray
            预测概率
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用train方法")
        
        # 选择特征
        if self.selected_features is not None:
            X = X[:, self.selected_features]
        
        # 标准化
        if self.model_type in ["lr", "svm"]:
            X = self.scaler.transform(X)
        
        predictions = self.model.predict(X)
        
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X)
        else:
            probabilities = None
        
        return predictions, probabilities
    
    def save(self, model_id: str, metadata: Optional[Dict] = None) -> str:
        """
        保存模型
        
        Parameters:
        -----------
        model_id : str
            模型ID
        metadata : dict, optional
            模型元数据
            
        Returns:
        --------
        str : 模型文件路径
        """
        model_path = get_model_file_path(model_id)
        ensure_dir(model_path)
        
        # 保存模型对象
        model_data = {
            'model': self.model,
            'scaler': self.scaler if self.model_type in ["lr", "svm"] else None,
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'selected_features': self.selected_features,
            'n_features': self.model.n_features_in_ if hasattr(self.model, 'n_features_in_') else (len(self.feature_names) if self.feature_names else None),
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, model_path)
        logger.info(f"模型已保存: {model_path}")
        
        return model_path
    
    @staticmethod
    def load(model_id: str) -> Dict[str, Any]:
        """
        加载模型
        
        Parameters:
        -----------
        model_id : str
            模型ID
            
        Returns:
        --------
        dict : 模型数据字典
        """
        model_path = get_model_file_path(model_id)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        model_data = joblib.load(model_path)
        logger.info(f"模型已加载: {model_path}")
        
        return model_data


