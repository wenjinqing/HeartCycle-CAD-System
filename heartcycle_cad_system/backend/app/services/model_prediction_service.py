"""
模型预测服务 - 负责模型预测功能
"""
import numpy as np
from typing import Dict, List
from app.core.logger import logger
from app.core.validators import FeatureVectorValidator
from algorithms.model_training import ModelTrainer


class ModelPredictionService:
    """模型预测服务"""

    def __init__(self):
        """初始化预测服务"""
        pass

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

    def batch_predict(self, model_id: str, features_list: List[List[float]]) -> List[Dict]:
        """
        批量预测

        Parameters:
        -----------
        model_id : str
            模型ID
        features_list : List[List[float]]
            特征向量列表

        Returns:
        --------
        List[Dict] : 预测结果列表
        """
        results = []
        for features in features_list:
            try:
                result = self.predict(model_id, features)
                results.append(result)
            except Exception as e:
                logger.error(f"批量预测中的单个预测失败: {str(e)}")
                results.append({
                    "error": str(e),
                    "prediction": None,
                    "probability": None,
                    "confidence": None
                })
        return results
