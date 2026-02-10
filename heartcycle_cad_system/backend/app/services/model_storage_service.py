"""
模型存储服务 - 负责模型的存储、加载和管理
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from app.core.logger import logger
from app.core.config import settings
from algorithms.model_training import ModelTrainer


class ModelStorageService:
    """模型存储服务"""

    def __init__(self):
        """初始化存储服务"""
        self.models_dir = settings.MODELS_DIR
        self.models = {}  # 模型元数据缓存

    def list_models(self) -> List[Dict]:
        """
        列出所有模型（包括内存中的和文件系统中的）

        Returns:
        --------
        List[Dict] : 模型列表
        """
        models = []

        # 从文件系统加载模型
        if os.path.exists(self.models_dir):
            files = os.listdir(self.models_dir)
            for filename in files:
                if filename.endswith('.pkl'):
                    model_id = filename[:-4]
                    try:
                        model_data = ModelTrainer.load(model_id)
                        model_info = {
                            'model_id': model_id,
                            'model_type': model_data.get('model_type', 'unknown'),
                            'created_at': model_data.get('created_at', 'unknown'),
                            'metrics': model_data.get('metrics', {}),
                            'n_features': len(model_data.get('feature_names', [])),
                            'feature_names': model_data.get('feature_names', [])
                        }
                        models.append(model_info)
                    except Exception as e:
                        logger.error(f"加载模型 {model_id} 失败: {str(e)}")

        return models

    def get_model_info(self, model_id: str) -> Dict:
        """
        获取模型信息

        Parameters:
        -----------
        model_id : str
            模型ID

        Returns:
        --------
        Dict : 模型信息
        """
        try:
            model_data = ModelTrainer.load(model_id)
            return {
                'model_id': model_id,
                'model_type': model_data.get('model_type', 'unknown'),
                'created_at': model_data.get('created_at', 'unknown'),
                'metrics': model_data.get('metrics', {}),
                'n_features': len(model_data.get('feature_names', [])),
                'feature_names': model_data.get('feature_names', []),
                'selected_features': model_data.get('selected_features'),
                'metadata': model_data.get('metadata', {})
            }
        except FileNotFoundError:
            raise FileNotFoundError(f"模型 {model_id} 不存在")
        except Exception as e:
            logger.error(f"获取模型信息失败: {str(e)}")
            raise

    def delete_model(self, model_id: str) -> Dict:
        """
        删除模型

        Parameters:
        -----------
        model_id : str
            模型ID

        Returns:
        --------
        Dict : 删除结果
        """
        try:
            model_path = os.path.join(self.models_dir, f"{model_id}.pkl")

            if not os.path.exists(model_path):
                return {
                    "success": False,
                    "error": f"模型 {model_id} 不存在"
                }

            # 删除模型文件
            os.remove(model_path)

            # 从缓存中删除
            if model_id in self.models:
                del self.models[model_id]

            logger.info(f"模型 {model_id} 已删除")
            return {
                "success": True,
                "message": f"模型 {model_id} 已删除"
            }

        except Exception as e:
            logger.error(f"删除模型失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除模型失败: {str(e)}"
            }

    def model_exists(self, model_id: str) -> bool:
        """
        检查模型是否存在

        Parameters:
        -----------
        model_id : str
            模型ID

        Returns:
        --------
        bool : 模型是否存在
        """
        model_path = os.path.join(self.models_dir, f"{model_id}.pkl")
        return os.path.exists(model_path)

    def get_model_path(self, model_id: str) -> str:
        """
        获取模型文件路径

        Parameters:
        -----------
        model_id : str
            模型ID

        Returns:
        --------
        str : 模型文件路径
        """
        return os.path.join(self.models_dir, f"{model_id}.pkl")
