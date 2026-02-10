"""
模型训练服务
"""
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from algorithms.feature_extraction import HRVFeatureExtractor
from algorithms.model_training import ModelTrainer
from app.core.config import settings
from app.core.logger import logger
from app.core.utils import normalize_file_path, validate_file_path
from app.core.validators import TrainingDataValidator

# 导入任务存储
try:
    from app.utils.mysql_task_storage import get_mysql_task_storage
    TASK_STORAGE_TYPE = "mysql"
except Exception as e:
    logger.warning(f"MySQL任务存储不可用: {e}，将使用内存存储")
    TASK_STORAGE_TYPE = "memory"


class ModelService:
    """模型训练服务类"""

    def __init__(self):
        self.models = {}  # 模型元数据存储
        self._lock = Lock()  # 线程锁保护共享状态

        # 使用MySQL存储任务（如果可用），否则使用内存存储
        if TASK_STORAGE_TYPE == "mysql":
            try:
                self.task_storage = get_mysql_task_storage()
                logger.info("使用MySQL存储训练任务")
            except Exception as e:
                logger.warning(f"MySQL存储初始化失败: {e}，使用内存存储")
                self.training_tasks = {}  # 回退到内存存储
                self.task_storage = None
        else:
            self.training_tasks = {}  # 内存存储
            self.task_storage = None

    def _update_training_task(self, task_id: str, updates: Dict) -> None:
        """线程安全地更新训练任务状态"""
        if self.task_storage:
            self.task_storage.update_task(task_id, updates)
        else:
            with self._lock:
                if task_id in self.training_tasks:
                    self.training_tasks[task_id].update(updates)

    def _create_training_task(self, task_id: str, initial_data: Dict) -> None:
        """线程安全地创建训练任务"""
        if self.task_storage:
            success = self.task_storage.create_task(task_id, initial_data)
            if not success:
                logger.error(f"创建任务 {task_id} 失败，回退到内存存储")
                with self._lock:
                    if not hasattr(self, 'training_tasks'):
                        self.training_tasks = {}
                    self.training_tasks[task_id] = initial_data
        else:
            with self._lock:
                if not hasattr(self, 'training_tasks'):
                    self.training_tasks = {}
                self.training_tasks[task_id] = initial_data

    def _get_training_task(self, task_id: str) -> Optional[Dict]:
        """线程安全地获取训练任务"""
        if self.task_storage:
            return self.task_storage.get_task(task_id)
        else:
            with self._lock:
                return self.training_tasks.get(task_id)

    def _get_training_tasks_count(self) -> int:
        """线程安全地获取训练任务数量"""
        if self.task_storage:
            return 0  # MySQL存储不需要计数
        else:
            with self._lock:
                return len(self.training_tasks) if hasattr(self, 'training_tasks') else 0

    
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
        feature_file = normalize_file_path(feature_file, is_directory=False)
        label_file = normalize_file_path(label_file, is_directory=False)
        
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
    
    def train_model(self, feature_file: str, label_file: str,
                   selected_features: Optional[List[int]] = None,
                   model_type: str = "rf", cv_folds: int = 5,
                   random_state: int = 42, use_smote: bool = True,
                   optimize_hyperparams: bool = False) -> Dict:
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
            模型类型（lr/svm/rf/xgb/lgb/stacking/voting）
        cv_folds : int
            交叉验证折数
        random_state : int
            随机种子
        use_smote : bool
            是否使用SMOTE处理数据不平衡
        optimize_hyperparams : bool
            是否进行超参数优化

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
                feature_names=feature_names,
                use_smote=use_smote,
                optimize_hyperparams=optimize_hyperparams
            )
            
            # 保存模型（包含metrics到metadata中）
            metadata = {
                'feature_file': feature_file,
                'label_file': label_file,
                'selected_features': selected_features,
                'cv_folds': cv_folds,
                'metrics': training_result['metrics']  # 保存metrics到metadata中
            }
            model_path = trainer.save(model_id, metadata)
            
            # 准备返回结果
            # 确保metrics包含cv_folds
            metrics = training_result['metrics'].copy() if training_result.get('metrics') else {}
            if 'cv_folds' not in metrics:
                metrics['cv_folds'] = cv_folds
            
            result = {
                "model_id": model_id,
                "model_type": model_type,
                "status": "completed",
                "metrics": metrics,
                "cv_scores": {
                    'accuracy': metrics.get('accuracy', {}).get('scores', []),
                    'precision': metrics.get('precision', {}).get('scores', []),
                    'recall': metrics.get('recall', {}).get('scores', []),
                    'f1': metrics.get('f1', {}).get('scores', []),
                    'roc_auc': metrics.get('roc_auc', {}).get('scores', [])
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
    
    def start_h5_training_task(
        self,
        data_dir: str,
        metadata_file: Optional[str] = None,
        label_file: Optional[str] = None,
        model_type: str = "rf",
        cv_folds: int = 5,
        random_state: int = 42,
        use_smote: bool = True,
        optimize_hyperparams: bool = False,
        use_existing_rpeaks: bool = True,
        extract_hrv: bool = True,
        extract_clinical: bool = True
    ) -> str:
        """
        启动H5训练任务（异步）
        
        Returns:
        --------
        str : 任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        initial_data = {
            "status": "running",
            "progress": 0.0,
            "message": "任务启动中...",
            "current_file": None,
            "total_files": 0,
            "processed_files": 0,
            "result": None,
            "error": None
        }

        # 使用线程安全的方法创建任务
        self._create_training_task(task_id, initial_data)

        task_count = self._get_training_tasks_count()
        logger.info(f"H5训练任务 {task_id} 已创建并存储，存储方式: {'MySQL' if self.task_storage else '内存'}, 内存任务数: {task_count}")
        logger.debug(f"任务详情: data_dir={data_dir}, model_type={model_type}")
        
        # 在后台线程中执行训练
        import threading
        
        def train_worker():
            try:
                # 定义进度回调
                def progress_callback(progress: float, message: str, filename: Optional[str]):
                    updates = {
                        "progress": progress,
                        "message": message,
                        "current_file": filename
                    }
                    
                    if "正在处理文件" in message:
                        # 从消息中提取文件计数
                        try:
                            parts = message.split(":")[0].split()
                            for i, part in enumerate(parts):
                                if "/" in part:
                                    processed, total = part.split("/")
                                    updates["processed_files"] = int(processed)
                                    updates["total_files"] = int(total)
                                    break
                        except:
                            pass

                    # 更新任务状态
                    self._update_training_task(task_id, updates)
                
                # 执行训练
                result = self.train_model_from_h5(
                    data_dir=data_dir,
                    metadata_file=metadata_file,
                    label_file=label_file,
                    model_type=model_type,
                    cv_folds=cv_folds,
                    random_state=random_state,
                    use_smote=use_smote,
                    optimize_hyperparams=optimize_hyperparams,
                    use_existing_rpeaks=use_existing_rpeaks,
                    extract_hrv=extract_hrv,
                    extract_clinical=extract_clinical,
                    progress_callback=progress_callback
                )

                # 更新任务状态
                self._update_training_task(task_id, {
                    "status": "completed",
                    "progress": 1.0,
                    "message": "训练完成",
                    "result": result
                })
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"H5训练任务 {task_id} 失败: {error_msg}")

                self._update_training_task(task_id, {
                    "status": "failed",
                    "error": error_msg,
                    "message": f"训练失败: {error_msg}"
                })
        
        thread = threading.Thread(target=train_worker, daemon=True)
        thread.start()
        
        return task_id
    
    def get_h5_training_status(self, task_id: str) -> Dict:
        """
        获取H5训练任务状态
        
        Parameters:
        -----------
        task_id : str
            任务ID
            
        Returns:
        --------
        dict : 任务状态
        """
        # 使用线程安全的方法获取任务
        task = self._get_training_task(task_id)
        if task:
            return task
        else:
            logger.warning(f"任务 {task_id} 不存在")
            return {"status": "not_found", "error": f"任务 {task_id} 不存在"}
    
    def train_model_from_h5(
        self,
        data_dir: str,
        metadata_file: Optional[str] = None,
        label_file: Optional[str] = None,
        model_type: str = "rf",
        cv_folds: int = 5,
        random_state: int = 42,
        use_smote: bool = True,
        optimize_hyperparams: bool = False,
        use_existing_rpeaks: bool = True,
        extract_hrv: bool = True,
        extract_clinical: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        从H5文件训练模型

        Parameters:
        -----------
        data_dir : str
            数据目录路径（包含H5文件）
        metadata_file : str, optional
            元数据CSV文件路径
        label_file : str, optional
            标签CSV文件路径（如果提供则优先使用）
        model_type : str
            模型类型（lr/svm/rf/xgb/lgb/stacking/voting）
        cv_folds : int
            交叉验证折数
        random_state : int
            随机种子
        use_smote : bool
            是否使用SMOTE处理数据不平衡
        optimize_hyperparams : bool
            是否进行超参数优化
        use_existing_rpeaks : bool
            是否使用已有R波标注
        extract_hrv : bool
            是否提取HRV特征
        extract_clinical : bool
            是否提取临床特征

        Returns:
        --------
        dict : 训练结果
        """
        try:
            # 导入train_from_h5脚本中的函数
            script_dir = Path(__file__).parent.parent.parent / 'scripts'
            if str(script_dir) not in sys.path:
                sys.path.insert(0, str(script_dir))
            
            from train_from_h5 import train_model_from_h5 as train_from_h5_func
            
            # 规范化目录路径（处理相对路径和绝对路径）
            data_dir_normalized = normalize_file_path(data_dir, is_directory=True)
            
            if not os.path.isdir(data_dir_normalized):
                raise ValueError(f"数据目录不存在: {data_dir_normalized}")
            
            # 规范化文件路径
            metadata_file_normalized = None
            if metadata_file:
                metadata_file_normalized = normalize_file_path(metadata_file, is_directory=False)
            
            label_file_normalized = None
            if label_file:
                label_file_normalized = normalize_file_path(label_file, is_directory=False)
            
            # 调用train_from_h5脚本的函数
            result = train_from_h5_func(
                data_dir=data_dir_normalized,
                metadata_file=metadata_file_normalized,
                label_file=label_file_normalized,
                output_dir=None,  # 使用默认输出目录
                model_type=model_type,
                cv_folds=cv_folds,
                random_state=random_state,
                use_smote=use_smote,
                optimize_hyperparams=optimize_hyperparams,
                use_existing_rpeaks=use_existing_rpeaks,
                extract_hrv=extract_hrv,
                extract_clinical=extract_clinical,
                save_features=True,
                progress_callback=progress_callback
            )
            
            # 生成模型ID并存储元数据
            model_id = result['model_id']
            self.models[model_id] = result
            
            return result
            
        except ImportError as e:
            logger.error(f"无法导入train_from_h5模块: {str(e)}")
            raise ValueError(f"H5训练功能不可用: {str(e)}")
        except Exception as e:
            logger.error(f"从H5文件训练模型失败: {str(e)}")
            raise

    def list_models(self) -> List[Dict]:
        """
        列出所有模型（包括内存中的和文件系统中的）
        
        Returns:
        --------
        list : 模型列表
        """
        models_list = []
        seen_model_ids = set()  # 用于跟踪已处理的模型ID，避免重复
        
        # 1. 添加内存中的模型
        for model_info in self.models.values():
            if isinstance(model_info, dict) and 'model_id' in model_info:
                model_id = model_info['model_id']
                seen_model_ids.add(model_id)
                models_list.append(model_info.copy())
        
        # 2. 扫描文件系统中的模型文件
        models_dir = settings.MODELS_DIR
        if not os.path.exists(models_dir):
            logger.warning(f"模型目录不存在: {models_dir}")
            return models_list
        
        try:
            files = os.listdir(models_dir)
        except Exception as e:
            logger.error(f"读取模型目录失败: {e}")
            return models_list
        
        for filename in files:
            if not filename.endswith('.joblib'):
                continue
            
            model_id = filename[:-7]  # 移除.joblib后缀
            
            # 如果已经在内存中，跳过
            if model_id in seen_model_ids:
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
                
                # 获取特征数量（优先使用n_features，如果没有则使用feature_names的长度）
                n_features = model_data.get('n_features')
                if n_features is None:
                    n_features = len(feature_names) if feature_names else 0
                
                # 构建模型信息
                created_at = model_data.get('created_at') or metadata.get('created_at')
                if created_at and isinstance(created_at, str):
                    pass  # 已经是字符串
                elif created_at:
                    created_at = str(created_at)
                else:
                    created_at = 'unknown'
                
                model_info = {
                    "model_id": model_id,
                    "model_type": model_data.get('model_type', 'unknown'),
                    "model_path": os.path.join(models_dir, filename),
                    "created_at": created_at,
                    "n_features": n_features,
                    "feature_count": n_features,
                    "status": "completed"
                }
                
                # 如果有metrics信息（可能在metadata中，也可能在model_data顶层）
                if 'metrics' in metadata:
                    model_info['metrics'] = metadata['metrics']
                elif 'metrics' in model_data:
                    model_info['metrics'] = model_data['metrics']
                
                # 从metadata中提取cv_folds并添加到metrics中（如果metrics存在）
                if 'cv_folds' in metadata and model_info.get('metrics'):
                    model_info['metrics']['cv_folds'] = metadata['cv_folds']
                elif 'cv_folds' in metadata:
                    # 如果metrics不存在，创建一个包含cv_folds的metrics对象
                    if 'metrics' not in model_info:
                        model_info['metrics'] = {}
                    model_info['metrics']['cv_folds'] = metadata['cv_folds']
                
                models_list.append(model_info)
                seen_model_ids.add(model_id)
                
                # 同时添加到内存中，避免重复加载
                self.models[model_id] = model_info
                
            except Exception as e:
                logger.warning(f"加载模型 {model_id} 信息失败: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
                # 即使加载失败，也记录这个模型ID，避免重复尝试
                seen_model_ids.add(model_id)
                continue
        
        logger.info(f"模型列表扫描完成，共找到 {len(models_list)} 个模型（已处理 {len(seen_model_ids)} 个模型文件）")
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
                metadata = model_data.get('metadata', {})
                
                # 获取metrics（可能在metadata中，也可能在model_data顶层）
                metrics = None
                if 'metrics' in metadata:
                    metrics = metadata['metrics']
                elif 'metrics' in model_data:
                    metrics = model_data['metrics']
                
                # 获取特征数量
                feature_names = model_data.get('feature_names') or []
                n_features = model_data.get('n_features')
                if n_features is None:
                    n_features = len(feature_names) if feature_names else 0
                
                # 如果文件存在但元数据不在内存中，返回基本信息
                created_at = model_data.get('created_at') or metadata.get('created_at')
                if created_at and isinstance(created_at, str):
                    pass  # 已经是字符串
                elif created_at:
                    created_at = str(created_at)
                else:
                    created_at = 'unknown'
                
                # 确保metrics包含cv_folds（如果metadata中有）
                if metrics is None:
                    metrics = {}
                if 'cv_folds' in metadata and 'cv_folds' not in metrics:
                    metrics['cv_folds'] = metadata['cv_folds']
                
                return {
                    "model_id": model_id,
                    "model_type": model_data.get('model_type', 'unknown'),
                    "metrics": metrics,  # 可能为None或空字典
                    "feature_count": n_features,
                    "created_at": created_at
                }
            except FileNotFoundError:
                raise FileNotFoundError(f"模型不存在: {model_id}")
        
        info = self.models[model_id].copy()
        # 确保包含所有必需字段
        if 'feature_count' not in info:
            info['feature_count'] = info.get('n_features', 0)
        # 确保 metrics 字段存在（即使为 None）
        if 'metrics' not in info:
            info['metrics'] = {}
        # 确保 created_at 字段存在且格式正确
        if 'created_at' not in info:
            info['created_at'] = 'unknown'
        elif info['created_at'] and not isinstance(info['created_at'], str):
            info['created_at'] = str(info['created_at'])
        # 如果metrics存在但缺少cv_folds，尝试从其他地方获取
        if info.get('metrics') and 'cv_folds' not in info['metrics']:
            # 尝试从训练结果中获取（如果存在）
            if 'cv_folds' in info:
                info['metrics']['cv_folds'] = info['cv_folds']
        # 尝试从模型文件中获取feature_file路径（用于SHAP全局解释）
        if 'feature_file' not in info:
            try:
                model_data = ModelTrainer.load(model_id)
                metadata = model_data.get('metadata', {})
                if 'feature_file' in metadata:
                    info['feature_file'] = metadata['feature_file']
            except Exception:
                pass  # 如果加载失败，忽略
        return info
    
    def delete_model(self, model_id: str) -> Dict:
        """
        删除模型
        
        Parameters:
        -----------
        model_id : str
            模型ID
            
        Returns:
        --------
        dict : 删除结果
        """
        try:
            from app.core.utils import get_model_file_path
            
            # 1. 检查模型是否存在
            model_file_path = get_model_file_path(model_id)
            metadata_file_path = model_file_path.replace('.joblib', '_metadata.json')
            
            if not os.path.exists(model_file_path):
                return {
                    "success": False,
                    "error": f"模型文件不存在: {model_id}"
                }
            
            # 2. 删除模型文件
            try:
                os.remove(model_file_path)
                logger.info(f"已删除模型文件: {model_file_path}")
            except Exception as e:
                logger.error(f"删除模型文件失败: {e}")
                return {
                    "success": False,
                    "error": f"删除模型文件失败: {str(e)}"
                }
            
            # 3. 删除元数据文件（如果存在）
            if os.path.exists(metadata_file_path):
                try:
                    os.remove(metadata_file_path)
                    logger.info(f"已删除模型元数据文件: {metadata_file_path}")
                except Exception as e:
                    logger.warning(f"删除元数据文件失败: {e}")  # 警告但不影响整体删除
            
            # 4. 从内存中移除
            if model_id in self.models:
                del self.models[model_id]
            
            logger.info(f"模型 {model_id} 已成功删除")
            return {
                "success": True,
                "message": f"模型 {model_id} 已成功删除"
            }
            
        except Exception as e:
            logger.error(f"删除模型失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除模型失败: {str(e)}"
            }
    
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

