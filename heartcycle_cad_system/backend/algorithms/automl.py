"""
AutoML - 自动机器学习
自动选择最佳模型和超参数
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, GridSearchCV, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
from typing import Dict, List, Tuple, Optional
import logging
import time

logger = logging.getLogger(__name__)


class AutoML:
    """自动机器学习"""

    def __init__(
        self,
        time_budget: int = 300,
        cv_folds: int = 5,
        random_state: int = 42
    ):
        """
        初始化

        Parameters:
        -----------
        time_budget : int
            时间预算（秒）
        cv_folds : int
            交叉验证折数
        random_state : int
            随机种子
        """
        self.time_budget = time_budget
        self.cv_folds = cv_folds
        self.random_state = random_state

        # 候选模型和超参数空间
        self.model_space = self._define_model_space()

    def _define_model_space(self) -> Dict:
        """定义模型和超参数搜索空间"""
        return {
            'logistic_regression': {
                'model': LogisticRegression(random_state=self.random_state, max_iter=1000),
                'params': {
                    'C': [0.001, 0.01, 0.1, 1, 10, 100],
                    'penalty': ['l1', 'l2'],
                    'solver': ['liblinear', 'saga']
                }
            },
            'random_forest': {
                'model': RandomForestClassifier(random_state=self.random_state),
                'params': {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 10, 20, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4]
                }
            },
            'svm': {
                'model': SVC(random_state=self.random_state, probability=True),
                'params': {
                    'C': [0.1, 1, 10],
                    'kernel': ['rbf', 'linear'],
                    'gamma': ['scale', 'auto', 0.001, 0.01]
                }
            },
            'knn': {
                'model': KNeighborsClassifier(),
                'params': {
                    'n_neighbors': [3, 5, 7, 9, 11],
                    'weights': ['uniform', 'distance'],
                    'metric': ['euclidean', 'manhattan']
                }
            },
            'gradient_boosting': {
                'model': GradientBoostingClassifier(random_state=self.random_state),
                'params': {
                    'n_estimators': [50, 100, 200],
                    'learning_rate': [0.01, 0.1, 0.2],
                    'max_depth': [3, 5, 7],
                    'subsample': [0.8, 1.0]
                }
            },
            'xgboost': {
                'model': XGBClassifier(random_state=self.random_state, eval_metric='logloss'),
                'params': {
                    'n_estimators': [50, 100, 200],
                    'learning_rate': [0.01, 0.1, 0.2],
                    'max_depth': [3, 5, 7],
                    'subsample': [0.8, 1.0],
                    'colsample_bytree': [0.8, 1.0]
                }
            },
            'lightgbm': {
                'model': LGBMClassifier(random_state=self.random_state, verbose=-1),
                'params': {
                    'n_estimators': [50, 100, 200],
                    'learning_rate': [0.01, 0.1, 0.2],
                    'max_depth': [3, 5, 7],
                    'num_leaves': [31, 50, 100],
                    'subsample': [0.8, 1.0]
                }
            }
        }

    def auto_select_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        metric: str = 'roc_auc',
        search_method: str = 'random'
    ) -> Dict:
        """
        自动选择最佳模型

        Parameters:
        -----------
        X_train : 训练数据
        y_train : 训练标签
        X_val : 验证数据（可选）
        y_val : 验证标签（可选）
        metric : 评估指标 ('accuracy', 'roc_auc', 'f1')
        search_method : 搜索方法 ('grid', 'random')

        Returns:
        --------
        最佳模型和结果
        """
        logger.info(f"开始 AutoML，时间预算: {self.time_budget}秒")
        start_time = time.time()

        results = []

        for model_name, model_config in self.model_space.items():
            # 检查时间预算
            elapsed_time = time.time() - start_time
            if elapsed_time >= self.time_budget:
                logger.warning(f"达到时间预算，停止搜索")
                break

            logger.info(f"评估模型: {model_name}")

            try:
                # 超参数搜索
                if search_method == 'grid':
                    search = GridSearchCV(
                        model_config['model'],
                        model_config['params'],
                        cv=self.cv_folds,
                        scoring=metric,
                        n_jobs=-1,
                        verbose=0
                    )
                else:  # random
                    search = RandomizedSearchCV(
                        model_config['model'],
                        model_config['params'],
                        n_iter=10,
                        cv=self.cv_folds,
                        scoring=metric,
                        n_jobs=-1,
                        random_state=self.random_state,
                        verbose=0
                    )

                # 训练
                search.fit(X_train, y_train)

                # 最佳模型
                best_model = search.best_estimator_

                # 评估
                train_score = search.best_score_

                if X_val is not None and y_val is not None:
                    y_pred = best_model.predict(X_val)
                    y_pred_proba = best_model.predict_proba(X_val)[:, 1]

                    val_accuracy = accuracy_score(y_val, y_pred)
                    val_auc = roc_auc_score(y_val, y_pred_proba)
                    val_f1 = f1_score(y_val, y_pred)

                    val_score = {
                        'accuracy': val_accuracy,
                        'roc_auc': val_auc,
                        'f1': val_f1
                    }[metric]
                else:
                    val_score = train_score

                results.append({
                    'model_name': model_name,
                    'model': best_model,
                    'best_params': search.best_params_,
                    'train_score': float(train_score),
                    'val_score': float(val_score),
                    'cv_results': search.cv_results_
                })

                logger.info(f"{model_name}: 训练分数={train_score:.4f}, 验证分数={val_score:.4f}")

            except Exception as e:
                logger.error(f"评估模型 {model_name} 失败: {e}")
                continue

        if not results:
            raise ValueError("没有成功评估任何模型")

        # 选择最佳模型
        results.sort(key=lambda x: x['val_score'], reverse=True)
        best_result = results[0]

        total_time = time.time() - start_time

        logger.info(f"AutoML 完成，总耗时: {total_time:.2f}秒")
        logger.info(f"最佳模型: {best_result['model_name']}, 分数: {best_result['val_score']:.4f}")

        return {
            'best_model': best_result['model'],
            'best_model_name': best_result['model_name'],
            'best_params': best_result['best_params'],
            'best_score': best_result['val_score'],
            'all_results': results,
            'total_time': total_time
        }

    def auto_feature_selection(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        method: str = 'importance',
        n_features: Optional[int] = None
    ) -> Tuple[List[str], Dict]:
        """
        自动特征选择

        Parameters:
        -----------
        X : 特征数据
        y : 标签
        method : 方法 ('importance', 'recursive', 'mutual_info')
        n_features : 选择的特征数量（None 表示自动）

        Returns:
        --------
        selected_features, selection_info
        """
        logger.info(f"开始自动特征选择，方法: {method}")

        feature_names = X.columns.tolist()

        if method == 'importance':
            # 基于随机森林特征重要性
            rf = RandomForestClassifier(n_estimators=100, random_state=self.random_state)
            rf.fit(X, y)
            importances = rf.feature_importances_

            # 排序
            indices = np.argsort(importances)[::-1]

            # 自动确定特征数量（累积重要性达到95%）
            if n_features is None:
                cumsum = np.cumsum(importances[indices])
                n_features = np.argmax(cumsum >= 0.95) + 1

            selected_indices = indices[:n_features]
            selected_features = [feature_names[i] for i in selected_indices]

            selection_info = {
                'method': method,
                'n_features': n_features,
                'feature_importance': {
                    feature_names[i]: float(importances[i])
                    for i in selected_indices
                }
            }

        elif method == 'recursive':
            # 递归特征消除
            from sklearn.feature_selection import RFE

            rf = RandomForestClassifier(n_estimators=100, random_state=self.random_state)

            if n_features is None:
                n_features = max(5, len(feature_names) // 2)

            rfe = RFE(rf, n_features_to_select=n_features)
            rfe.fit(X, y)

            selected_features = [
                feature_names[i]
                for i in range(len(feature_names))
                if rfe.support_[i]
            ]

            selection_info = {
                'method': method,
                'n_features': n_features,
                'ranking': {
                    feature_names[i]: int(rfe.ranking_[i])
                    for i in range(len(feature_names))
                }
            }

        elif method == 'mutual_info':
            # 互信息
            from sklearn.feature_selection import mutual_info_classif

            mi_scores = mutual_info_classif(X, y, random_state=self.random_state)

            # 排序
            indices = np.argsort(mi_scores)[::-1]

            if n_features is None:
                # 选择互信息大于平均值的特征
                n_features = np.sum(mi_scores > np.mean(mi_scores))

            selected_indices = indices[:n_features]
            selected_features = [feature_names[i] for i in selected_indices]

            selection_info = {
                'method': method,
                'n_features': n_features,
                'mutual_info_scores': {
                    feature_names[i]: float(mi_scores[i])
                    for i in selected_indices
                }
            }

        else:
            raise ValueError(f"不支持的方法: {method}")

        logger.info(f"选择了 {len(selected_features)} 个特征")

        return selected_features, selection_info

    def auto_pipeline(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[np.ndarray] = None,
        feature_selection: bool = True,
        model_selection: bool = True
    ) -> Dict:
        """
        自动化完整流程

        Parameters:
        -----------
        X_train : 训练特征
        y_train : 训练标签
        X_val : 验证特征
        y_val : 验证标签
        feature_selection : 是否进行特征选择
        model_selection : 是否进行模型选择

        Returns:
        --------
        完整的 AutoML 结果
        """
        logger.info("开始 AutoML 完整流程")

        results = {}

        # 1. 特征选择
        if feature_selection:
            selected_features, selection_info = self.auto_feature_selection(
                X_train, y_train, method='importance'
            )
            X_train_selected = X_train[selected_features]
            if X_val is not None:
                X_val_selected = X_val[selected_features]
            else:
                X_val_selected = None

            results['feature_selection'] = {
                'selected_features': selected_features,
                'selection_info': selection_info
            }
        else:
            X_train_selected = X_train
            X_val_selected = X_val
            results['feature_selection'] = None

        # 2. 模型选择
        if model_selection:
            model_results = self.auto_select_model(
                X_train_selected.values,
                y_train,
                X_val_selected.values if X_val_selected is not None else None,
                y_val,
                metric='roc_auc'
            )
            results['model_selection'] = model_results
        else:
            results['model_selection'] = None

        logger.info("AutoML 完整流程完成")

        return results
