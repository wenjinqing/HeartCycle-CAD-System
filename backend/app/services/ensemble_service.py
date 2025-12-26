"""
模型集成服务
支持多个模型的投票集成和加权平均
"""
from typing import Dict, List, Optional
import numpy as np
from app.core.logger import logger
from algorithms.model_training import ModelTrainer


class EnsembleService:
    """模型集成服务类"""
    
    def __init__(self):
        self.ensemble_models = {}  # 存储集成模型配置
    
    def predict_ensemble(self, 
                        model_ids: List[str], 
                        features: List[float],
                        method: str = "voting",
                        weights: Optional[List[float]] = None) -> Dict:
        """
        使用多个模型进行集成预测
        
        Parameters:
        -----------
        model_ids : List[str]
            模型ID列表
        features : List[float]
            特征向量
        method : str
            集成方法：'voting'（投票）或'weighted'（加权平均）
        weights : List[float], optional
            权重列表（用于加权平均），如果为None则使用等权重
            
        Returns:
        --------
        dict : 集成预测结果
        """
        if not model_ids or len(model_ids) == 0:
            raise ValueError("模型ID列表不能为空")
        
        if len(model_ids) == 1:
            # 只有一个模型，直接使用
            logger.info(f"只有一个模型，直接使用: {model_ids[0]}")
            from app.services.model_service import ModelService
            model_service = ModelService()
            return model_service.predict(model_ids[0], features)
        
        # 加载所有模型并获取预测结果
        predictions = []
        probabilities_list = []
        confidences = []
        
        logger.info(f"开始集成预测，使用 {len(model_ids)} 个模型: {model_ids}")
        
        for model_id in model_ids:
            try:
                # 加载模型
                model_data = ModelTrainer.load(model_id)
                model = model_data['model']
                scaler = model_data.get('scaler')
                selected_features = model_data.get('selected_features')
                feature_names = model_data.get('feature_names', [])
                
                # 转换特征向量
                X = np.array(features).reshape(1, -1)
                
                # 处理特征数量不匹配
                n_expected_features = None
                if hasattr(model, 'n_features_in_'):
                    n_expected_features = model.n_features_in_
                elif 'n_features' in model_data:
                    n_expected_features = model_data['n_features']
                elif feature_names:
                    n_expected_features = len(feature_names)
                
                if n_expected_features is not None and X.shape[1] != n_expected_features:
                    if X.shape[1] < n_expected_features:
                        padding = np.zeros((1, n_expected_features - X.shape[1]))
                        X = np.hstack([X, padding])
                    elif X.shape[1] > n_expected_features:
                        X = X[:, :n_expected_features]
                
                # 选择特征
                if selected_features is not None:
                    X = X[:, selected_features]
                
                # 标准化
                if scaler is not None:
                    X = scaler.transform(X)
                
                # 预测
                pred = model.predict(X)[0]
                # 确保pred是Python int类型（不是numpy.int64）
                pred = int(pred)
                
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(X)[0]
                    conf = float(np.max(proba))
                else:
                    proba = np.array([0.5, 0.5])
                    conf = 1.0
                
                predictions.append(pred)
                probabilities_list.append(proba)
                confidences.append(conf)
                
                logger.debug(f"模型 {model_id} 预测: {pred}, 置信度: {conf:.4f}")
                
            except Exception as e:
                logger.error(f"模型 {model_id} 预测失败: {str(e)}")
                # 跳过失败的模型
                continue
        
        if len(predictions) == 0:
            raise ValueError("所有模型预测都失败")
        
        # 根据方法进行集成
        if method == "voting":
            return self._voting_ensemble(predictions, probabilities_list, confidences, model_ids)
        elif method == "weighted":
            if weights is None:
                weights = [1.0 / len(probabilities_list)] * len(probabilities_list)
            elif len(weights) != len(probabilities_list):
                logger.warning(f"权重数量({len(weights)})与模型数量({len(probabilities_list)})不匹配，使用等权重")
                weights = [1.0 / len(probabilities_list)] * len(probabilities_list)
            return self._weighted_ensemble(predictions, probabilities_list, confidences, weights, model_ids)
        else:
            raise ValueError(f"不支持的集成方法: {method}")
    
    def _voting_ensemble(self, 
                        predictions: List[int], 
                        probabilities_list: List[np.ndarray],
                        confidences: List[float],
                        model_ids: List[str]) -> Dict:
        """
        投票集成（软投票）
        
        Parameters:
        -----------
        predictions : List[int]
            各模型的预测类别
        probabilities_list : List[np.ndarray]
            各模型的预测概率
        confidences : List[float]
            各模型的置信度
        model_ids : List[str]
            模型ID列表
            
        Returns:
        --------
        dict : 集成预测结果
        """
        # 软投票：平均概率
        avg_proba = np.mean(probabilities_list, axis=0)
        ensemble_prediction = int(np.argmax(avg_proba))
        ensemble_confidence = float(np.max(avg_proba))
        
        # 硬投票：统计类别投票
        vote_counts = {}
        for pred in predictions:
            vote_counts[pred] = vote_counts.get(pred, 0) + 1
        
        hard_vote = max(vote_counts, key=vote_counts.get)
        agreement = vote_counts.get(ensemble_prediction, 0) / len(predictions)
        
        logger.info(f"投票集成结果: 预测={ensemble_prediction}, 置信度={ensemble_confidence:.4f}, "
                   f"一致性={agreement:.2%}, 使用模型数={len(model_ids)}")
        
        # 确保所有值都是Python原生类型（可JSON序列化）
        return {
            "prediction": int(ensemble_prediction),
            "probability": [float(p) for p in avg_proba.tolist()],
            "confidence": float(ensemble_confidence),
            "method": "voting",
            "model_count": int(len(model_ids)),
            "model_ids": [str(mid) for mid in model_ids],
            "hard_vote": int(hard_vote),
            "agreement": float(agreement),
            "individual_predictions": [int(p) for p in predictions],
            "individual_confidences": [float(c) for c in confidences]
        }
    
    def _weighted_ensemble(self,
                          predictions: List[int],
                          probabilities_list: List[np.ndarray],
                          confidences: List[float],
                          weights: List[float],
                          model_ids: List[str]) -> Dict:
        """
        加权平均集成
        
        Parameters:
        -----------
        predictions : List[int]
            各模型的预测类别
        probabilities_list : List[np.ndarray]
            各模型的预测概率
        confidences : List[float]
            各模型的置信度
        weights : List[float]
            权重列表
        model_ids : List[str]
            模型ID列表
            
        Returns:
        --------
        dict : 集成预测结果
        """
        # 归一化权重
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        # 加权平均概率
        weighted_proba = np.zeros_like(probabilities_list[0])
        for proba, weight in zip(probabilities_list, normalized_weights):
            weighted_proba += proba * weight
        
        ensemble_prediction = int(np.argmax(weighted_proba))
        ensemble_confidence = float(np.max(weighted_proba))
        
        # 加权平均置信度
        weighted_confidence = sum(c * w for c, w in zip(confidences, normalized_weights))
        
        logger.info(f"加权集成结果: 预测={ensemble_prediction}, 置信度={ensemble_confidence:.4f}, "
                   f"使用模型数={len(model_ids)}")
        
        # 确保所有值都是Python原生类型（可JSON序列化）
        return {
            "prediction": int(ensemble_prediction),
            "probability": [float(p) for p in weighted_proba.tolist()],
            "confidence": float(ensemble_confidence),
            "weighted_confidence": float(weighted_confidence),
            "method": "weighted",
            "model_count": int(len(model_ids)),
            "model_ids": [str(mid) for mid in model_ids],
            "weights": [float(w) for w in normalized_weights],
            "individual_predictions": [int(p) for p in predictions],
            "individual_confidences": [float(c) for c in confidences]
        }
    
    def get_ensemble_info(self, model_ids: List[str]) -> Dict:
        """
        获取集成模型信息
        
        Parameters:
        -----------
        model_ids : List[str]
            模型ID列表
            
        Returns:
        --------
        dict : 集成模型信息
        """
        models_info = []
        
        for model_id in model_ids:
            try:
                model_data = ModelTrainer.load(model_id)
                info = {
                    "model_id": model_id,
                    "model_type": model_data.get('model_type', 'unknown'),
                    "n_features": model_data.get('n_features', 0),
                    "created_at": model_data.get('created_at', 'unknown')
                }
                models_info.append(info)
            except Exception as e:
                logger.warning(f"无法加载模型 {model_id} 的信息: {str(e)}")
                models_info.append({
                    "model_id": model_id,
                    "error": str(e)
                })
        
        return {
            "model_count": len(model_ids),
            "models": models_info
        }

