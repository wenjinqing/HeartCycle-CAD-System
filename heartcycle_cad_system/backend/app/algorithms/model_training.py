"""
模型训练与评估模块
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, StackingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer  # 新增：缺失值处理
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report
)
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
import xgboost as xgb
import lightgbm as lgb
import joblib
import warnings

# 抑制警告信息
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', module='xgboost')
warnings.filterwarnings('ignore', module='lightgbm')
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
        self.imputer = SimpleImputer(strategy='median')  # 缺失值填充器
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
            模型类型（lr/svm/rf/xgb/lgb/stacking/voting）
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
                class_weight='balanced',  # 自动平衡类权重
                random_state=self.random_state,
                n_jobs=-1
            )
        elif model_type == "xgb":
            self.model = xgb.XGBClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                min_child_weight=kwargs.get('min_child_weight', 1),
                gamma=kwargs.get('gamma', 0),
                subsample=kwargs.get('subsample', 0.8),
                colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                reg_alpha=kwargs.get('reg_alpha', 0),
                reg_lambda=kwargs.get('reg_lambda', 1),
                scale_pos_weight=kwargs.get('scale_pos_weight', 2.0),  # 类权重平衡
                objective='binary:logistic',
                eval_metric='auc',
                use_label_encoder=False,
                random_state=self.random_state,
                n_jobs=-1,
                verbosity=0  # 减少输出
            )
        elif model_type == "lgb":
            self.model = lgb.LGBMClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', -1),
                learning_rate=kwargs.get('learning_rate', 0.1),
                num_leaves=kwargs.get('num_leaves', 31),
                min_child_samples=kwargs.get('min_child_samples', 20),
                subsample=kwargs.get('subsample', 0.8),
                colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                class_weight='balanced',  # 类权重平衡
                objective='binary',
                metric='auc',
                random_state=self.random_state,
                n_jobs=-1,
                verbose=-1
            )
        elif model_type == "stacking":
            # Stacking集成学习
            base_models = [
                ('rf', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=self.random_state, n_jobs=-1)),
                ('xgb', xgb.XGBClassifier(n_estimators=100, scale_pos_weight=2.0, use_label_encoder=False, verbosity=0, random_state=self.random_state, n_jobs=-1)),
                ('lgb', lgb.LGBMClassifier(n_estimators=100, class_weight='balanced', random_state=self.random_state, n_jobs=-1, verbose=-1))
            ]
            meta_model = LogisticRegression(random_state=self.random_state, max_iter=1000)
            self.model = StackingClassifier(
                estimators=base_models,
                final_estimator=meta_model,
                cv=5,
                n_jobs=-1
            )
        elif model_type == "voting":
            # Voting集成学习
            base_models = [
                ('rf', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=self.random_state, n_jobs=-1)),
                ('xgb', xgb.XGBClassifier(n_estimators=100, scale_pos_weight=2.0, use_label_encoder=False, verbosity=0, random_state=self.random_state, n_jobs=-1)),
                ('lgb', lgb.LGBMClassifier(n_estimators=100, class_weight='balanced', random_state=self.random_state, n_jobs=-1, verbose=-1))
            ]
            self.model = VotingClassifier(
                estimators=base_models,
                voting='soft',
                n_jobs=-1
            )
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        self.model_type = model_type

    def _get_param_grid(self, model_type: str) -> Dict[str, List]:
        """
        获取模型的超参数搜索空间

        Parameters:
        -----------
        model_type : str
            模型类型

        Returns:
        --------
        dict : 超参数搜索空间
        """
        param_grids = {
            'rf': {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            },
            'xgb': {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.05, 0.1],
                'min_child_weight': [1, 3, 5],
                'gamma': [0, 0.1, 0.2],
                'subsample': [0.8, 0.9, 1.0],
                'colsample_bytree': [0.8, 0.9, 1.0]
            },
            'lgb': {
                'n_estimators': [50, 100, 200],
                'max_depth': [-1, 5, 10],
                'learning_rate': [0.01, 0.05, 0.1],
                'num_leaves': [31, 50, 70],
                'min_child_samples': [20, 30, 50],
                'subsample': [0.8, 0.9, 1.0],
                'colsample_bytree': [0.8, 0.9, 1.0]
            },
            'lr': {
                'C': [0.01, 0.1, 1, 10, 100],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear', 'saga']
            },
            'svm': {
                'C': [0.1, 1, 10, 100],
                'kernel': ['rbf', 'linear'],
                'gamma': ['scale', 'auto', 0.001, 0.01, 0.1]
            }
        }

        return param_grids.get(model_type, {})

    def optimize_hyperparameters(self,
                                 X: np.ndarray,
                                 y: np.ndarray,
                                 model_type: str = "xgb",
                                 cv_folds: int = 5,
                                 param_grid: Optional[Dict] = None,
                                 scoring: str = 'roc_auc',
                                 n_jobs: int = -1) -> Dict[str, Any]:
        """
        超参数优化

        Parameters:
        -----------
        X : np.ndarray
            特征矩阵
        y : np.ndarray
            标签
        model_type : str
            模型类型
        cv_folds : int
            交叉验证折数
        param_grid : dict, optional
            自定义超参数搜索空间，如果为None则使用默认
        scoring : str
            评分指标
        n_jobs : int
            并行任务数

        Returns:
        --------
        dict : 最佳参数和评分
        """
        logger.info(f"开始超参数优化: {model_type}")

        # 获取参数搜索空间
        if param_grid is None:
            param_grid = self._get_param_grid(model_type)

        if not param_grid:
            raise ValueError(f"模型类型 {model_type} 不支持超参数优化或未定义参数空间")

        # 创建基础模型
        self._create_model(model_type)

        # 数据标准化（如果需要）
        X_processed = X.copy()
        if model_type in ["lr", "svm"]:
            X_processed = self.scaler.fit_transform(X)

        # 设置交叉验证
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)

        # 网格搜索
        logger.info(f"参数搜索空间: {param_grid}")
        grid_search = GridSearchCV(
            estimator=self.model,
            param_grid=param_grid,
            cv=cv,
            scoring=scoring,
            n_jobs=n_jobs,
            verbose=1,
            return_train_score=True
        )

        # 执行搜索
        grid_search.fit(X_processed, y)

        # 更新模型为最佳模型
        self.model = grid_search.best_estimator_

        logger.info(f"最佳参数: {grid_search.best_params_}")
        logger.info(f"最佳得分: {grid_search.best_score_:.4f}")

        # 返回结果
        result = {
            'best_params': grid_search.best_params_,
            'best_score': float(grid_search.best_score_),
            'cv_results': {
                'mean_test_score': grid_search.cv_results_['mean_test_score'].tolist(),
                'std_test_score': grid_search.cv_results_['std_test_score'].tolist(),
                'params': [str(p) for p in grid_search.cv_results_['params']]
            }
        }

        return result

    def train(self,
              X: np.ndarray,
              y: np.ndarray,
              model_type: str = "rf",
              cv_folds: int = 5,
              selected_features: Optional[List[int]] = None,
              feature_names: Optional[List[str]] = None,
              use_smote: bool = True,
              optimize_hyperparams: bool = False,
              param_grid: Optional[Dict] = None,
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
            模型类型（lr/svm/rf/xgb/lgb/stacking/voting）
        cv_folds : int
            交叉验证折数
        selected_features : List[int], optional
            选择的特征索引
        feature_names : List[str], optional
            特征名称
        use_smote : bool
            是否使用SMOTE处理数据不平衡（默认True）
        optimize_hyperparams : bool
            是否进行超参数优化（默认False）
        param_grid : dict, optional
            自定义超参数搜索空间
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

        # 检查类别分布
        unique_labels, class_counts = np.unique(y, return_counts=True)
        logger.info(f"类别分布: {dict(zip(unique_labels, class_counts))}")

        # 计算类别不平衡比例
        imbalance_ratio = max(class_counts) / min(class_counts)
        logger.info(f"类别不平衡比例: {imbalance_ratio:.2f}")

        # ========== 缺失值处理 ==========
        # 先检查和清理Inf值（SimpleImputer不接受Inf）
        if np.isinf(X).any():
            inf_count = np.isinf(X).sum()
            logger.warning(f"检测到 {inf_count} 个无穷值，先清理Inf")
            X = np.nan_to_num(X, nan=np.nan, posinf=0.0, neginf=0.0)  # 只清理Inf，保留NaN给imputer处理

        # 检查是否有缺失值
        if np.isnan(X).any():
            nan_count = np.isnan(X).sum()
            nan_percent = (nan_count / X.size) * 100
            logger.warning(f"检测到 {nan_count} 个缺失值 ({nan_percent:.2f}%)")

            # 使用中位数填充缺失值（对异常值更稳健）
            X = self.imputer.fit_transform(X)
            logger.info(f"已使用中位数填充缺失值")

            # 验证填充后是否还有NaN
            if np.isnan(X).any():
                logger.error(f"填充后仍有 {np.isnan(X).sum()} 个NaN，使用0填充")
                X = np.nan_to_num(X, nan=0.0)
        else:
            # 即使没检测到NaN，也fit imputer以便预测时使用
            X = self.imputer.fit_transform(X)
            logger.info("数据完整，无缺失值")

        # 数据标准化（SVM和LR需要）
        # 注意：对于SVM/LR，我们将在Pipeline中处理标准化
        # 这里先准备未标准化的数据用于交叉验证
        X_processed = X.copy()

        # 对于非SVM/LR模型，不需要标准化
        # SVM/LR的标准化将在Pipeline中完成

        # 应用SMOTE处理数据不平衡
        # 先创建副本，避免引用问题
        X_resampled = X_processed.copy()
        y_resampled = y.copy()
        smote_applied = False

        if use_smote and imbalance_ratio > 1.5 and min(class_counts) >= 2:
            try:
                # 计算合适的k_neighbors参数
                k_neighbors = min(5, min(class_counts) - 1)
                if k_neighbors >= 1:
                    smote = SMOTE(random_state=self.random_state, k_neighbors=k_neighbors)
                    X_resampled, y_resampled = smote.fit_resample(X_processed, y)
                    smote_applied = True

                    # 检查SMOTE后是否产生NaN
                    if np.isnan(X_resampled).any():
                        logger.error(f"SMOTE后产生 {np.isnan(X_resampled).sum()} 个NaN，使用0填充")
                        X_resampled = np.nan_to_num(X_resampled, nan=0.0)

                    # 记录SMOTE后的类别分布
                    unique_resampled, counts_resampled = np.unique(y_resampled, return_counts=True)
                    logger.info(f"SMOTE后类别分布: {dict(zip(unique_resampled, counts_resampled))}")
                else:
                    logger.warning(f"样本数太少，无法应用SMOTE (k_neighbors需要>=1)")
            except Exception as e:
                logger.warning(f"SMOTE失败: {str(e)}，使用原始数据")
                X_resampled = X_processed
                y_resampled = y
        elif use_smote:
            logger.info(f"数据平衡良好或样本数不足，跳过SMOTE")

        # ========== 最终验证和强制清理 ==========
        # 无论之前的检查结果如何，都强制执行最终清理
        logger.info(f"最终数据验证: shape={X_resampled.shape}, dtype={X_resampled.dtype}")

        # 检查异常值
        nan_count = np.isnan(X_resampled).sum()
        inf_count = np.isinf(X_resampled).sum()

        if nan_count > 0 or inf_count > 0:
            logger.error(f"发现异常值 - NaN: {nan_count}, Inf: {inf_count}")
        else:
            logger.info("数据验证通过，无异常值")

        # 强制清理（即使没检测到也执行，以防万一）
        X_resampled = np.nan_to_num(X_resampled, nan=0.0, posinf=0.0, neginf=0.0)

        # 确保数据是连续的numpy数组（某些操作可能产生非连续数组）
        if not X_resampled.flags['C_CONTIGUOUS']:
            logger.warning("数据不是连续数组，正在转换...")
            X_resampled = np.ascontiguousarray(X_resampled)

        # 最终验证：断言数据完全干净
        final_nan_count = np.isnan(X_resampled).sum()
        final_inf_count = np.isinf(X_resampled).sum()

        if final_nan_count > 0 or final_inf_count > 0:
            logger.error(f"清理失败！仍有 NaN={final_nan_count}, Inf={final_inf_count}")
            raise ValueError(f"数据清理失败：仍包含 {final_nan_count} 个NaN和 {final_inf_count} 个Inf")
        else:
            logger.info("[成功] 数据清理成功，准备进行交叉验证")

        # 打印数据统计信息用于调试
        logger.info(f"数据统计: min={X_resampled.min():.4f}, max={X_resampled.max():.4f}, "
                   f"mean={X_resampled.mean():.4f}, std={X_resampled.std():.4f}")

        # 超参数优化
        optimization_result = None
        if optimize_hyperparams and model_type not in ['stacking', 'voting']:
            logger.info("开始超参数优化...")
            try:
                optimization_result = self.optimize_hyperparameters(
                    X_resampled, y_resampled,
                    model_type=model_type,
                    cv_folds=cv_folds,
                    param_grid=param_grid,
                    scoring='roc_auc'
                )
                logger.info(f"超参数优化完成，最佳参数: {optimization_result['best_params']}")
                # 模型已在optimize_hyperparameters中更新为最佳模型
            except Exception as e:
                logger.warning(f"超参数优化失败: {str(e)}，使用默认参数")
                self._create_model(model_type, **model_params)
        else:
            # 创建模型（使用默认参数或用户指定参数）
            self._create_model(model_type, **model_params)

        # 根据样本数量和类别分布调整交叉验证折数
        n_samples = len(X_resampled)
        original_cv_folds = cv_folds
        use_stratified = True

        # 检查每个类别的样本数（StratifiedKFold需要）
        unique_labels_resampled, class_counts_resampled = np.unique(y_resampled, return_counts=True)
        min_class_count = int(np.min(class_counts_resampled))

        # 计算最大允许的分层折数
        # StratifiedKFold要求：n_splits <= min(n_samples, min_class_count)
        max_stratified_folds = min(n_samples, min_class_count)

        # 调整折数并决定使用哪种交叉验证方法
        if cv_folds > n_samples:
            if n_samples >= 2:
                cv_folds = n_samples
                logger.warning(
                    f"交叉验证折数 ({original_cv_folds}) 大于样本数 ({n_samples})，"
                    f"已调整为 {cv_folds} 折"
                )
            else:
                raise ValueError(
                    f"样本数量 ({n_samples}) 不足，至少需要 2 个样本才能进行交叉验证"
                )

        # 检查是否可以使用StratifiedKFold
        if cv_folds > max_stratified_folds:
            if max_stratified_folds < 2:
                # 无法使用分层交叉验证，改用普通KFold
                use_stratified = False
                logger.warning(
                    f"无法使用分层交叉验证（最小类别样本数: {min_class_count}），"
                    f"改用普通 {cv_folds} 折交叉验证"
                )
            else:
                # 可以降低折数来使用StratifiedKFold
                cv_folds = max_stratified_folds
                logger.warning(
                    f"交叉验证折数 ({original_cv_folds}) 过大（样本数: {n_samples}, "
                    f"最小类别样本数: {min_class_count}），已自动调整为 {cv_folds} 折分层交叉验证"
                )

        # 交叉验证
        if use_stratified:
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        else:
            cv = KFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)

        logger.info(f"开始交叉验证 (折数: {cv_folds}, 分层: {use_stratified})")

        # 交叉验证前的最后检查
        logger.info(f"交叉验证输入数据: X shape={X_resampled.shape}, y shape={y_resampled.shape}")
        logger.info(f"数据类型: X dtype={X_resampled.dtype}, y dtype={y_resampled.dtype}")

        # 紧急断言：确保没有NaN（如果有就立即报错）
        assert not np.isnan(X_resampled).any(), f"X_resampled仍包含 {np.isnan(X_resampled).sum()} 个NaN！"
        assert not np.isinf(X_resampled).any(), f"X_resampled仍包含 {np.isinf(X_resampled).sum()} 个Inf！"

        # 为SVM和LR模型创建Pipeline，确保交叉验证时每个fold都正确处理数据
        # Pipeline包含完整的预处理流程：imputer → scaler → model
        if model_type in ['svm', 'lr']:
            logger.info(f"为{model_type}创建Pipeline（imputer → scaler → model）")
            # 创建包含完整预处理流程的pipeline
            cv_model = Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler()),
                ('model', self.model)
            ])
        else:
            cv_model = self.model

        cv_scores_accuracy = cross_val_score(cv_model, X_resampled, y_resampled, cv=cv, scoring='accuracy', n_jobs=-1)
        cv_scores_precision = cross_val_score(cv_model, X_resampled, y_resampled, cv=cv, scoring='precision', n_jobs=-1)
        cv_scores_recall = cross_val_score(cv_model, X_resampled, y_resampled, cv=cv, scoring='recall', n_jobs=-1)
        cv_scores_f1 = cross_val_score(cv_model, X_resampled, y_resampled, cv=cv, scoring='f1', n_jobs=-1)
        
        # ROC AUC可能在某些fold中失败（当只有一个类别时）
        # 使用try-except处理可能的异常，如果失败则使用NaN填充
        try:
            cv_scores_roc_auc = cross_val_score(cv_model, X_resampled, y_resampled, cv=cv, scoring='roc_auc', n_jobs=-1)
        except (ValueError, Exception) as e:
            logger.warning(f"计算ROC AUC交叉验证分数时出现错误: {e}，将使用NaN填充")
            # 如果计算失败，创建一个包含NaN的数组
            cv_scores_roc_auc = np.full(cv_folds, np.nan)

        # 训练最终模型（使用重采样后的数据）
        logger.info("训练最终模型...")

        # 对于SVM和LR，需要先标准化数据
        if model_type in ['svm', 'lr']:
            logger.info(f"对{model_type}进行标准化处理...")
            X_final = self.scaler.fit_transform(X_resampled)
            # 检查标准化后是否有NaN
            if np.isnan(X_final).any():
                logger.warning(f"标准化后产生 {np.isnan(X_final).sum()} 个NaN，使用0填充")
                X_final = np.nan_to_num(X_final, nan=0.0)
        else:
            X_final = X_resampled

        self.model.fit(X_final, y_resampled)

        # 计算最终评估指标（在重采样数据上）
        y_pred = self.model.predict(X_final)
        
        # 安全地获取预测概率
        y_pred_proba = None
        if hasattr(self.model, 'predict_proba'):
            try:
                proba = self.model.predict_proba(X_final)
                # 检查概率矩阵的列数，如果是二分类应该有2列
                if proba.shape[1] >= 2:
                    y_pred_proba = proba[:, 1]  # 取正类（类别1）的概率
                elif proba.shape[1] == 1:
                    # 如果只有一列，可能是单分类问题，使用这一列
                    y_pred_proba = proba[:, 0]
                else:
                    logger.warning(f"predict_proba返回了意外的形状: {proba.shape}")
                    y_pred_proba = None
            except Exception as e:
                logger.warning(f"获取预测概率失败: {str(e)}")
                y_pred_proba = None
        
        # 辅助函数：将NaN转换为None，用于JSON序列化
        def nan_to_none(value):
            """将NaN值转换为None（JSON兼容）"""
            if isinstance(value, (float, np.floating)):
                return None if np.isnan(value) else float(value)
            elif isinstance(value, (np.ndarray, list)):
                return [nan_to_none(v) for v in value]
            elif isinstance(value, dict):
                return {k: nan_to_none(v) for k, v in value.items()}
            return value
        
        # 处理ROC AUC分数：计算均值和标准差（忽略NaN）
        roc_auc_mean = np.nanmean(cv_scores_roc_auc) if np.any(~np.isnan(cv_scores_roc_auc)) else None
        roc_auc_std = np.nanstd(cv_scores_roc_auc) if np.any(~np.isnan(cv_scores_roc_auc)) else None
        
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
                'mean': nan_to_none(roc_auc_mean),
                'std': nan_to_none(roc_auc_std),
                'scores': [nan_to_none(score) for score in cv_scores_roc_auc]
            }
        }
        
        # 混淆矩阵（在重采样数据上）
        cm = confusion_matrix(y_resampled, y_pred)
        metrics['confusion_matrix'] = cm.tolist()

        # 以下为「全量重采样训练集」上的样本内指标：易过拟合、常高于 K 折 CV 均值；请以各指标的 CV mean 为准。
        metrics['final_accuracy'] = float(accuracy_score(y_resampled, y_pred))
        metrics['final_precision'] = float(precision_score(y_resampled, y_pred, zero_division=0))
        metrics['final_recall'] = float(recall_score(y_resampled, y_pred, zero_division=0))
        metrics['final_f1'] = float(f1_score(y_resampled, y_pred, zero_division=0))

        # 计算最终ROC AUC（需要至少两个类别）
        if y_pred_proba is not None and len(np.unique(y_resampled)) > 1:
            try:
                metrics['final_roc_auc'] = float(roc_auc_score(y_resampled, y_pred_proba))
            except ValueError as e:
                logger.warning(f"计算最终ROC AUC失败: {e}")
                metrics['final_roc_auc'] = None
        else:
            metrics['final_roc_auc'] = None

        # 添加SMOTE信息
        metrics['smote_applied'] = smote_applied
        if smote_applied:
            metrics['original_samples'] = len(X)
            metrics['resampled_samples'] = len(X_resampled)
            metrics['original_class_distribution'] = dict(zip(unique_labels.tolist(), class_counts.tolist()))
            metrics['resampled_class_distribution'] = dict(zip(unique_labels_resampled.tolist(), class_counts_resampled.tolist()))
        
        auc_str = f"{metrics['roc_auc']['mean']:.4f}" if metrics['roc_auc']['mean'] is not None else "N/A"
        logger.info(f"模型训练完成: {model_type}, CV AUC: {auc_str}")

        result = {
            'model_type': model_type,
            'metrics': metrics,
            'cv_folds': cv_folds,
            'n_features': X.shape[1],
            'n_samples': X.shape[0]
        }

        # 添加超参数优化结果
        if optimization_result:
            result['hyperparameter_optimization'] = optimization_result

        # 确保整个结果字典中所有NaN值都转换为None（JSON兼容）
        result = nan_to_none(result)

        return result
    
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

        # 处理缺失值（使用训练时拟合的imputer）
        if np.isnan(X).any():
            X = self.imputer.transform(X)

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
            'imputer': self.imputer,  # 保存缺失值填充器
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


