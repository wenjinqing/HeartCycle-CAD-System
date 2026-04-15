"""
数据分析服务
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import logging
import json
from datetime import datetime

from ..algorithms.data_quality import DataQualityAnalyzer
from ..algorithms.feature_analysis import FeatureAnalyzer
from ..algorithms.automl import AutoML
from ..core.config import settings

logger = logging.getLogger(__name__)


class DataAnalysisService:
    """数据分析服务"""

    def __init__(self):
        self.data_dir = Path(settings.DATA_ROOT)
        self.results_dir = Path(settings.RESULTS_DIR)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def analyze_data_quality(
        self,
        h5_files: List[str],
        sample_size: Optional[int] = None
    ) -> Dict:
        """
        分析数据质量

        Parameters:
        -----------
        h5_files : List[str]
            H5 文件路径列表
        sample_size : Optional[int]
            采样数量

        Returns:
        --------
        数据质量报告
        """
        logger.info(f"开始数据质量分析，文件数: {len(h5_files)}")

        analyzer = DataQualityAnalyzer()

        try:
            results = analyzer.analyze_dataset(h5_files, sample_size)

            # 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.results_dir / f"data_quality_report_{timestamp}.json"

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"数据质量报告已保存: {report_path}")

            return {
                'success': True,
                'report': results,
                'report_path': str(report_path)
            }

        except Exception as e:
            logger.error(f"数据质量分析失败: {e}")
            raise

    def analyze_features(
        self,
        features_file: str,
        labels_file: str
    ) -> Dict:
        """
        分析特征

        Parameters:
        -----------
        features_file : str
            特征文件路径 (CSV)
        labels_file : str
            标签文件路径 (CSV)

        Returns:
        --------
        特征分析报告
        """
        logger.info(f"开始特征分析")

        try:
            # 加载数据
            X = pd.read_csv(features_file)
            y = pd.read_csv(labels_file).values.ravel()

            # 分析
            analyzer = FeatureAnalyzer()
            report = analyzer.generate_feature_report(X, y)

            # 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.results_dir / f"feature_analysis_report_{timestamp}.json"

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"特征分析报告已保存: {report_path}")

            return {
                'success': True,
                'report': report,
                'report_path': str(report_path)
            }

        except Exception as e:
            logger.error(f"特征分析失败: {e}")
            raise

    def run_automl(
        self,
        features_file: str,
        labels_file: str,
        time_budget: int = 300,
        feature_selection: bool = True,
        test_size: float = 0.2
    ) -> Dict:
        """
        运行 AutoML

        Parameters:
        -----------
        features_file : str
            特征文件路径
        labels_file : str
            标签文件路径
        time_budget : int
            时间预算（秒）
        feature_selection : bool
            是否进行特征选择
        test_size : float
            测试集比例

        Returns:
        --------
        AutoML 结果
        """
        logger.info(f"开始 AutoML，时间预算: {time_budget}秒")

        try:
            # 加载数据
            X = pd.read_csv(features_file)
            y = pd.read_csv(labels_file).values.ravel()

            # 划分数据集
            from sklearn.model_selection import train_test_split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            # AutoML
            automl = AutoML(time_budget=time_budget)
            results = automl.auto_pipeline(
                X_train, y_train,
                X_val, y_val,
                feature_selection=feature_selection,
                model_selection=True
            )

            # 保存最佳模型
            if results['model_selection']:
                import joblib
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                model_id = f"automl_{timestamp}"
                model_path = Path(settings.MODELS_DIR) / f"{model_id}.pkl"

                joblib.dump(results['model_selection']['best_model'], model_path)

                results['model_id'] = model_id
                results['model_path'] = str(model_path)

            # 保存报告
            report_path = self.results_dir / f"automl_report_{timestamp}.json"

            # 移除不可序列化的对象
            report_data = {
                'model_id': results.get('model_id'),
                'model_path': results.get('model_path'),
                'best_model_name': results['model_selection']['best_model_name'],
                'best_params': results['model_selection']['best_params'],
                'best_score': results['model_selection']['best_score'],
                'total_time': results['model_selection']['total_time'],
                'feature_selection': results.get('feature_selection'),
                'all_model_scores': [
                    {
                        'model_name': r['model_name'],
                        'train_score': r['train_score'],
                        'val_score': r['val_score']
                    }
                    for r in results['model_selection']['all_results']
                ]
            }

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"AutoML 报告已保存: {report_path}")

            return {
                'success': True,
                'results': report_data,
                'report_path': str(report_path)
            }

        except Exception as e:
            logger.error(f"AutoML 失败: {e}")
            raise

    def compare_models(
        self,
        features_file: str,
        labels_file: str,
        model_types: List[str]
    ) -> Dict:
        """
        比较多个模型

        Parameters:
        -----------
        features_file : str
            特征文件路径
        labels_file : str
            标签文件路径
        model_types : List[str]
            模型类型列表

        Returns:
        --------
        模型对比结果
        """
        logger.info(f"开始模型对比，模型数: {len(model_types)}")

        try:
            # 加载数据
            X = pd.read_csv(features_file)
            y = pd.read_csv(labels_file).values.ravel()

            # 划分数据集
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # 训练和评估每个模型
            from ..algorithms.model_training import ModelTrainer
            trainer = ModelTrainer()

            results = []
            for model_type in model_types:
                logger.info(f"训练模型: {model_type}")

                try:
                    model, metrics = trainer.train_model(
                        X_train.values, y_train,
                        X_test.values, y_test,
                        model_type=model_type
                    )

                    results.append({
                        'model_type': model_type,
                        'accuracy': metrics['accuracy'],
                        'precision': metrics['precision'],
                        'recall': metrics['recall'],
                        'f1_score': metrics['f1_score'],
                        'roc_auc': metrics['roc_auc']
                    })

                except Exception as e:
                    logger.error(f"训练模型 {model_type} 失败: {e}")
                    continue

            # 排序
            results.sort(key=lambda x: x['roc_auc'], reverse=True)

            # 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.results_dir / f"model_comparison_{timestamp}.json"

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"模型对比报告已保存: {report_path}")

            return {
                'success': True,
                'results': results,
                'report_path': str(report_path)
            }

        except Exception as e:
            logger.error(f"模型对比失败: {e}")
            raise
