"""
模型训练服务
"""
from typing import Dict, List, Optional
import uuid
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from app.core.logger import logger
from app.core.utils import validate_file_path
from app.core.config import settings
from app.core.validators import TrainingDataValidator
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from algorithms.model_training import ModelTrainer


class ModelService:
    """模型训练服务类"""
    
    def __init__(self):
        self.models = {}  # 模型元数据存储
    
    def _load_data(self, feature_file: str, label_file: str) -> tuple:
        """
        加载特征和标签数据
        
        Parameters:
        -----------
        feature_file : str
            特征文件路径（CSV格式）
        label_file : str
            标签文件路径（CSV格式）
            
        Returns:
        --------
        X : np.ndarray
            特征矩阵
        y : np.ndarray
            标签向量
        feature_names : List[str]
            特征名称列表
        """
        # 规范化文件路径（处理相对路径和绝对路径）
        feature_file = self._normalize_file_path(feature_file)
        label_file = self._normalize_file_path(label_file)
        
        # 加载特征
        if not os.path.exists(feature_file):
            raise FileNotFoundError(f"特征文件不存在: {feature_file}")
        
        logger.info(f"加载特征文件: {feature_file}")
        df_features = pd.read_csv(feature_file)
        feature_names = df_features.columns.tolist()
        X = df_features.values.astype(np.float64)
        
        # 加载标签
        if not os.path.exists(label_file):
            raise FileNotFoundError(f"标签文件不存在: {label_file}")
        
        logger.info(f"加载标签文件: {label_file}")
        df_labels = pd.read_csv(label_file)
        if len(df_labels.columns) != 1:
            raise ValueError("标签文件应只包含一列")
        
        y = df_labels.iloc[:, 0].values
        
        # 使用验证器验证数据
        X, y = TrainingDataValidator.validate_training_data(X, y)
        
        logger.info(f"加载数据: {len(X)}个样本, {len(feature_names)}个特征")
        
        return X, y, feature_names
    
    def _normalize_file_path(self, file_path: str) -> str:
        """
        规范化文件路径
        
        处理相对路径、绝对路径，支持以下路径格式：
        1. 绝对路径（直接使用）
        2. 相对于项目根目录的路径（如 data/features/train_features.csv）
        3. 上传目录中的文件（data/raw/xxx.csv）
        4. 包含 .. 的相对路径（规范化处理）
        
        Parameters:
        -----------
        file_path : str
            文件路径
            
        Returns:
        --------
        str : 规范化的绝对路径
        """
        if not file_path:
            raise ValueError("文件路径不能为空")
        
        # 规范化路径（移除 .. 和 .，转换为标准路径）
        normalized = os.path.normpath(file_path)
        
        # 如果已经是绝对路径且文件存在，直接返回
        if os.path.isabs(normalized) and os.path.exists(normalized):
            return normalized
        
        # 提取文件名（用于在多个目录中查找）
        filename = os.path.basename(normalized)
        
        # 尝试多个可能的路径
        search_paths = []
        
        # 1. 如果是绝对路径但文件不存在，尝试移除多余的部分
        if os.path.isabs(normalized):
            search_paths.append(normalized)
            # 尝试只使用文件名
            search_paths.append(filename)
        
        # 2. 相对于项目根目录
        base_path = os.path.join(settings.BASE_DIR, normalized)
        search_paths.append(base_path)
        
        # 3. 如果是相对路径，尝试直接使用
        if not os.path.isabs(normalized):
            search_paths.append(normalized)
        
        # 4. 在上传目录中查找（只使用文件名）
        upload_path = os.path.join(settings.UPLOAD_DIR, filename)
        search_paths.append(upload_path)
        
        # 5. 在特征目录中查找（只使用文件名）
        features_path = os.path.join(settings.FEATURES_DIR, filename)
        search_paths.append(features_path)
        
        # 6. 尝试从当前工作目录解析
        if os.path.exists(normalized):
            search_paths.append(os.path.abspath(normalized))
        
        # 遍历所有可能的路径，找到存在的文件
        for path in search_paths:
            abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                logger.debug(f"找到文件: {abs_path} (原始路径: {file_path})")
                return abs_path
        
        # 如果所有尝试都失败，返回规范化后的绝对路径（让后续代码抛出错误）
        final_path = os.path.abspath(normalized) if not os.path.isabs(normalized) else normalized
        logger.warning(f"无法找到文件: {file_path} (规范化后: {final_path})")
        return final_path
    
    def train_model(self, feature_file: str, label_file: str,
                   selected_features: Optional[List[int]] = None,
                   model_type: str = "rf", cv_folds: int = 5,
                   random_state: int = 42) -> Dict:
        """
        训练模型
        
        Parameters:
        -----------
        feature_file : str
            特征文件路径
        label_file : str
            标签文件路径
        selected_features : List[int]
            选择的特征索引
        model_type : str
            模型类型（lr/svm/rf）
        cv_folds : int
            交叉验证折数
        random_state : int
            随机种子
            
        Returns:
        --------
        dict : 训练结果
        """
        # 生成模型ID，使用时间戳和模型类型，便于识别
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"{model_type}_{timestamp}"
        
        try:
            # 加载数据
            X, y, feature_names = self._load_data(feature_file, label_file)
            
            # 创建训练器并训练
            trainer = ModelTrainer(random_state=random_state)
            training_result = trainer.train(
                X=X,
                y=y,
                model_type=model_type,
                cv_folds=cv_folds,
                selected_features=selected_features,
                feature_names=feature_names
            )
            
            # 保存模型
            metadata = {
                'feature_file': feature_file,
                'label_file': label_file,
                'selected_features': selected_features,
                'cv_folds': cv_folds
            }
            model_path = trainer.save(model_id, metadata)
            
            # 准备返回结果
            result = {
                "model_id": model_id,
                "model_type": model_type,
                "status": "completed",
                "metrics": training_result['metrics'],
                "cv_scores": {
                    'accuracy': training_result['metrics']['accuracy']['scores'],
                    'precision': training_result['metrics']['precision']['scores'],
                    'recall': training_result['metrics']['recall']['scores'],
                    'f1': training_result['metrics']['f1']['scores'],
                    'roc_auc': training_result['metrics']['roc_auc']['scores']
                },
                "n_features": training_result['n_features'],
                "n_samples": training_result['n_samples'],
                "model_path": model_path,
                "created_at": datetime.now().isoformat()
            }
            
            # 存储元数据
            self.models[model_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"模型训练失败: {str(e)}")
            raise
    
    def predict(self, model_id: str, features: List[float]) -> Dict:
        """
        预测
        
        Parameters:
        -----------
        model_id : str
            模型ID
        features : List[float]
            特征向量
            
        Returns:
        --------
        dict : 预测结果
        """
        try:
            # 验证特征向量
            validated_features = FeatureVectorValidator.validate_features(features)
            
            # 加载模型
            model_data = ModelTrainer.load(model_id)
            model = model_data['model']
            scaler = model_data.get('scaler')
            model_type = model_data['model_type']
            selected_features = model_data.get('selected_features')
            
            # 转换特征向量
            X = validated_features.reshape(1, -1)
            
            # 选择特征
            if selected_features is not None:
                X = X[:, selected_features]
            
            # 标准化
            if scaler is not None:
                X = scaler.transform(X)
            
            # 预测
            prediction = model.predict(X)[0]
            
            # 预测概率
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(X)[0].tolist()
                confidence = max(probabilities)
            else:
                probabilities = None
                confidence = 1.0
            
            return {
                "prediction": int(prediction),
                "probability": probabilities if probabilities else [0.5, 0.5],
                "confidence": float(confidence)
            }
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"预测失败: {str(e)}")
            raise ValueError(f"预测失败: {str(e)}")
    
    def list_models(self) -> List[Dict]:
        """
        列出所有模型（包括内存中的和文件系统中的）
        
        Returns:
        --------
        list : 模型列表
        """
        models_list = []
        
        # 1. 添加内存中的模型
        models_list.extend(list(self.models.values()))
        
        # 2. 扫描文件系统中的模型文件
        models_dir = settings.MODELS_DIR
        if os.path.exists(models_dir):
            for filename in os.listdir(models_dir):
                if filename.endswith('.joblib'):
                    model_id = filename[:-7]  # 移除.joblib后缀
                    
                    # 如果已经在内存中，跳过
                    if model_id in self.models:
                        continue
                    
                    # 尝试加载模型信息
                    try:
                        model_data = ModelTrainer.load(model_id)
                        metadata = model_data.get('metadata', {})
                        
                        # 安全获取特征名称列表
                        feature_names = model_data.get('feature_names') or []
                        if feature_names is None:
                            feature_names = []
                        elif not isinstance(feature_names, list):
                            feature_names = []
                        
                        # 构建模型信息
                        model_info = {
                            "model_id": model_id,
                            "model_type": model_data.get('model_type', 'unknown'),
                            "model_path": os.path.join(models_dir, filename),
                            "created_at": model_data.get('created_at', metadata.get('created_at', 'unknown')),
                            "n_features": len(feature_names),
                            "feature_count": len(feature_names),
                            "status": "completed"
                        }
                        
                        # 如果有metrics信息，添加
                        if 'metrics' in metadata:
                            model_info['metrics'] = metadata['metrics']
                        
                        models_list.append(model_info)
                        
                        # 同时添加到内存中，避免重复加载
                        self.models[model_id] = model_info
                        
                    except Exception as e:
                        logger.warning(f"加载模型 {model_id} 信息失败: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
                        continue
        
        return models_list
    
    def get_model_info(self, model_id: str) -> Dict:
        """
        获取模型信息
        
        Parameters:
        -----------
        model_id : str
            模型ID
            
        Returns:
        --------
        dict : 模型信息
        """
        if model_id not in self.models:
            # 尝试从文件系统加载
            try:
                model_data = ModelTrainer.load(model_id)
                # 如果文件存在但元数据不在内存中，返回基本信息
                return {
                    "model_id": model_id,
                    "model_type": model_data.get('model_type', 'unknown'),
                    "metrics": {},
                    "feature_count": len(model_data.get('feature_names', [])),
                    "created_at": model_data.get('metadata', {}).get('created_at', 'unknown')
                }
            except FileNotFoundError:
                raise FileNotFoundError(f"模型不存在: {model_id}")
        
        info = self.models[model_id].copy()
        # 确保包含所有必需字段
        if 'feature_count' not in info:
            info['feature_count'] = info.get('n_features', 0)
        return info
    
    def predict(self, model_id: str, features: List[float]) -> Dict:
        """
        预测
        
        Parameters:
        -----------
        model_id : str
            模型ID
        features : List[float]
            特征向量
            
        Returns:
        --------
        dict : 预测结果
        """
        try:
            # 验证特征向量
            from app.core.validators import FeatureVectorValidator
            validated_features = FeatureVectorValidator.validate_features(features)
            
            # 加载模型
            model_data = ModelTrainer.load(model_id)
            model = model_data['model']
            scaler = model_data.get('scaler')
            selected_features = model_data.get('selected_features')
            feature_names = model_data.get('feature_names', [])
            
            # 转换特征向量
            X = np.array(validated_features).reshape(1, -1)
            n_provided_features = X.shape[1]
            
            # 获取模型期望的特征数量（从模型本身获取，更准确）
            if hasattr(model, 'n_features_in_'):
                n_expected_features = model.n_features_in_
            else:
                # 如果模型没有n_features_in_属性，尝试从metadata获取
                metadata = model_data.get('metadata', {})
                n_expected_features = metadata.get('n_features') or len(feature_names) if feature_names else None
            
            # 检查特征数量（在选择特征之前）
            if n_expected_features is not None and n_provided_features != n_expected_features:
                logger.warning(f"特征数量不匹配: 提供了{n_provided_features}个，模型期望{n_expected_features}个")
                
                if n_provided_features < n_expected_features:
                    # 特征不足，用0填充
                    logger.info(f"特征数量不足，将用0填充到{n_expected_features}个特征")
                    padding = np.zeros((1, n_expected_features - n_provided_features))
                    X = np.hstack([X, padding])
                    n_provided_features = n_expected_features
                elif n_provided_features > n_expected_features:
                    # 特征过多，截断
                    logger.info(f"特征数量过多，将截断到{n_expected_features}个特征")
                    X = X[:, :n_expected_features]
                    n_provided_features = n_expected_features
            
            # 选择特征（在特征数量匹配之后）
            if selected_features is not None:
                if n_expected_features is not None and n_provided_features < max(selected_features) + 1:
                    raise ValueError(f"选择的特征索引超出范围: 需要至少{max(selected_features) + 1}个特征，但只有{n_provided_features}个")
                X = X[:, selected_features]
                logger.info(f"使用特征选择: {len(selected_features)}个特征")
            
            # 标准化
            if scaler is not None:
                X = scaler.transform(X)
            
            # 预测
            prediction = model.predict(X)[0]
            
            # 预测概率
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(X)[0].tolist()
                confidence = float(max(probabilities))
            else:
                probabilities = [0.5, 0.5]
                confidence = 1.0
            
            return {
                "prediction": int(prediction),
                "probability": probabilities,
                "confidence": confidence
            }
            
        except FileNotFoundError:
            raise FileNotFoundError(f"模型 {model_id} 不存在")
        except Exception as e:
            logger.error(f"预测失败: {str(e)}")
            raise ValueError(f"预测失败: {str(e)}")

