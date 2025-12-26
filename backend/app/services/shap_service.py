"""
SHAP可解释性分析服务
"""
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import shap
from app.core.logger import logger
from app.core.config import settings
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from algorithms.model_training import ModelTrainer


class SHAPService:
    """SHAP分析服务类"""
    
    def __init__(self):
        self.explainers = {}  # 解释器缓存
        self.results = {}  # SHAP结果存储
    
    def _load_model(self, model_id: str) -> Dict:
        """
        加载模型数据
        
        Parameters:
        -----------
        model_id : str
            模型ID
            
        Returns:
        --------
        dict : 模型数据字典
        """
        try:
            model_data = ModelTrainer.load(model_id)
            return model_data
        except FileNotFoundError:
            raise FileNotFoundError(f"模型不存在: {model_id}")
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            raise ValueError(f"加载模型失败: {str(e)}")
    
    def _get_explainer(self, model_data: Dict, training_data: Optional[np.ndarray] = None):
        """
        根据模型类型获取合适的SHAP解释器
        
        Parameters:
        -----------
        model_data : dict
            模型数据字典
        training_data : np.ndarray, optional
            训练数据（用于TreeExplainer或KernelExplainer）
            
        Returns:
        --------
        shap.Explainer : SHAP解释器实例
        """
        model = model_data['model']
        model_type = model_data.get('model_type', 'unknown')
        
        # 检查缓存
        cache_key = f"{model_type}_{id(model)}"
        if cache_key in self.explainers:
            return self.explainers[cache_key]
        
        try:
            # 根据模型类型选择解释器
            if model_type == 'rf':
                # 随机森林使用TreeExplainer（最快且准确）
                explainer = shap.TreeExplainer(model)
            elif model_type in ['lr', 'svm']:
                # 线性模型使用LinearExplainer
                if model_type == 'lr':
                    explainer = shap.LinearExplainer(model, training_data) if training_data is not None else shap.LinearExplainer(model, np.zeros((1, model.coef_.shape[1])))
                else:
                    # SVM使用KernelExplainer（较慢但通用）
                    if training_data is not None:
                        # 使用训练数据的一个子集作为背景数据（加快计算）
                        background_size = min(100, len(training_data))
                        background_indices = np.random.choice(len(training_data), background_size, replace=False)
                        background = training_data[background_indices]
                    else:
                        background = np.zeros((1, model.n_features_in_))
                    explainer = shap.KernelExplainer(model.predict_proba, background)
            else:
                # 其他模型使用KernelExplainer（通用但较慢）
                if training_data is not None:
                    background_size = min(100, len(training_data))
                    background_indices = np.random.choice(len(training_data), background_size, replace=False)
                    background = training_data[background_indices]
                else:
                    background = np.zeros((1, model.n_features_in_))
                explainer = shap.KernelExplainer(model.predict_proba, background)
            
            # 缓存解释器
            self.explainers[cache_key] = explainer
            
            logger.info(f"创建SHAP解释器: {model_type}")
            return explainer
            
        except Exception as e:
            logger.error(f"创建SHAP解释器失败: {str(e)}")
            raise ValueError(f"创建SHAP解释器失败: {str(e)}")
    
    def explain_instance(self, model_id: str, features: List[float]) -> Dict:
        """
        解释单个样本的预测结果（局部解释）
        
        Parameters:
        -----------
        model_id : str
            模型ID
        features : List[float]
            特征向量
            
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
            # 加载模型
            model_data = self._load_model(model_id)
            model = model_data['model']
            scaler = model_data.get('scaler')
            selected_features = model_data.get('selected_features')
            feature_names = model_data.get('feature_names', [])
            
            # 准备特征向量
            X = np.array(features).reshape(1, -1)
            
            # 处理特征数量不匹配
            if hasattr(model, 'n_features_in_'):
                n_expected = model.n_features_in_
            else:
                n_expected = len(feature_names) if feature_names else X.shape[1]
            
            if X.shape[1] != n_expected:
                if X.shape[1] < n_expected:
                    # 用0填充
                    padding = np.zeros((1, n_expected - X.shape[1]))
                    X = np.hstack([X, padding])
                else:
                    # 截断
                    X = X[:, :n_expected]
            
            # 选择特征
            X_processed = X.copy()
            if selected_features is not None:
                X_processed = X_processed[:, selected_features]
            
            # 标准化（如果需要）
            if scaler is not None:
                X_processed = scaler.transform(X_processed)
            
            # 获取预测结果
            prediction = model.predict(X_processed)[0]
            if hasattr(model, 'predict_proba'):
                probability = model.predict_proba(X_processed)[0].tolist()
            else:
                probability = [0.5, 0.5]
            
            # 创建解释器（使用单个样本作为背景，适用于局部解释）
            explainer = self._get_explainer(model_data, training_data=X_processed)
            
            # 计算SHAP值
            # 注意：TreeExplainer和LinearExplainer可以直接处理，KernelExplainer需要传入预测函数
            shap_values = explainer.shap_values(X_processed)
            
            # 处理SHAP值格式（对于多分类，shap_values可能是列表）
            if isinstance(shap_values, list):
                # 多分类：选择预测类别对应的SHAP值
                class_idx = int(prediction) if prediction < len(shap_values) else 0
                shap_values_instance = shap_values[class_idx][0]  # 取第一个样本
                base_value = explainer.expected_value[class_idx] if isinstance(explainer.expected_value, (list, np.ndarray)) else explainer.expected_value
            else:
                # 二分类：shap_values已经是正确格式
                shap_values_instance = shap_values[0]  # 取第一个样本
                base_value = explainer.expected_value[0] if isinstance(explainer.expected_value, (list, np.ndarray)) and len(explainer.expected_value) > 0 else explainer.expected_value
            
            # 处理特征名称
            if selected_features is not None and feature_names:
                used_feature_names = [feature_names[i] for i in selected_features]
            elif feature_names:
                used_feature_names = feature_names[:len(shap_values_instance)]
            else:
                used_feature_names = [f"特征_{i+1}" for i in range(len(shap_values_instance))]
            
            # 处理特征值
            feature_values = X_processed[0].tolist() if scaler is None else X[0].tolist()
            
            # 构建结果
            result = {
                "base_value": float(base_value) if isinstance(base_value, (np.number, np.ndarray)) else base_value,
                "shap_values": [float(v) for v in shap_values_instance],
                "feature_values": feature_values[:len(shap_values_instance)],
                "feature_names": used_feature_names[:len(shap_values_instance)],
                "prediction": int(prediction),
                "probability": [float(p) for p in probability],
                "model_id": model_id
            }
            
            logger.info(f"SHAP局部解释完成: 模型={model_id}, 预测={prediction}")
            return result
            
        except Exception as e:
            logger.error(f"SHAP局部解释失败: {str(e)}", exc_info=True)
            raise ValueError(f"SHAP局部解释失败: {str(e)}")
    
    def explain_global(self, model_id: str, training_data_file: Optional[str] = None,
                      n_samples: int = 100) -> Dict:
        """
        计算全局特征重要性（全局解释）
        
        Parameters:
        -----------
        model_id : str
            模型ID
        training_data_file : str, optional
            训练数据文件路径（CSV格式）
        n_samples : int
            用于计算SHAP值的样本数（默认100）
            
        Returns:
        --------
        dict : 全局重要性结果
            - feature_importance: 特征重要性字典（特征名 -> 平均绝对SHAP值）
            - feature_ranking: 特征排名列表（按重要性降序）
            - average_shap_values: 每个特征的平均SHAP值
        """
        try:
            # 加载模型
            model_data = self._load_model(model_id)
            model = model_data['model']
            scaler = model_data.get('scaler')
            selected_features = model_data.get('selected_features')
            feature_names = model_data.get('feature_names', [])
            
            # 加载训练数据
            if training_data_file:
                # 规范化文件路径
                if not os.path.isabs(training_data_file):
                    training_data_file = os.path.join(settings.BASE_DIR, training_data_file)
                
                if not os.path.exists(training_data_file):
                    raise FileNotFoundError(f"训练数据文件不存在: {training_data_file}")
                
                df = pd.read_csv(training_data_file)
                training_data = df.values.astype(np.float64)
            else:
                # 如果没有提供训练数据文件，尝试从模型元数据中获取
                # 这里我们使用一个空的数据集，但对于TreeExplainer，我们仍然可以工作
                training_data = None
            
            # 处理特征选择
            if training_data is not None:
                if selected_features is not None:
                    training_data = training_data[:, selected_features]
                
                # 标准化（如果需要）
                if scaler is not None:
                    training_data = scaler.transform(training_data)
                
                # 采样（如果样本数太多）
                if len(training_data) > n_samples:
                    indices = np.random.choice(len(training_data), n_samples, replace=False)
                    training_data = training_data[indices]
                
                logger.info(f"使用 {len(training_data)} 个样本计算全局SHAP值")
            else:
                logger.warning(f"未提供训练数据，全局解释可能不准确")
                # 创建一个小的背景数据集（全0或随机）
                n_features = model.n_features_in_ if hasattr(model, 'n_features_in_') else len(feature_names)
                training_data = np.zeros((min(n_samples, 100), n_features))
            
            # 创建解释器
            explainer = self._get_explainer(model_data, training_data=training_data)
            
            # 计算SHAP值
            shap_values = explainer.shap_values(training_data)
            
            # 处理SHAP值格式（对于多分类，取第一个类别的SHAP值）
            if isinstance(shap_values, list):
                shap_values_matrix = shap_values[0]  # 取第一个类别
            else:
                shap_values_matrix = shap_values
            
            # 计算平均绝对SHAP值（特征重要性）
            mean_abs_shap = np.abs(shap_values_matrix).mean(axis=0)
            
            # 处理特征名称
            if selected_features is not None and feature_names:
                used_feature_names = [feature_names[i] for i in selected_features]
            elif feature_names:
                used_feature_names = feature_names[:len(mean_abs_shap)]
            else:
                used_feature_names = [f"特征_{i+1}" for i in range(len(mean_abs_shap))]
            
            # 计算平均SHAP值（带符号）
            mean_shap = shap_values_matrix.mean(axis=0)
            
            # 构建特征重要性字典
            feature_importance = {
                name: float(importance) for name, importance in zip(used_feature_names, mean_abs_shap)
            }
            
            # 构建特征排名（按重要性降序）
            feature_ranking = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # 构建结果
            result = {
                "feature_importance": feature_importance,
                "feature_ranking": [
                    {"feature": name, "importance": float(importance)}
                    for name, importance in feature_ranking
                ],
                "average_shap_values": {
                    name: float(value) for name, value in zip(used_feature_names, mean_shap)
                },
                "n_samples": len(training_data) if training_data is not None else 0,
                "model_id": model_id
            }
            
            logger.info(f"SHAP全局解释完成: 模型={model_id}, 特征数={len(feature_ranking)}")
            return result
            
        except Exception as e:
            logger.error(f"SHAP全局解释失败: {str(e)}", exc_info=True)
            raise ValueError(f"SHAP全局解释失败: {str(e)}")
