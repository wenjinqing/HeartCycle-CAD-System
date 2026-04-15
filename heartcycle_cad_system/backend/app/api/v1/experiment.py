"""
论文实验API - 集成所有新实现的功能
"""
import io

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
import logging

from app.algorithms.advanced_preprocessing import AdvancedPreprocessor
from app.algorithms.advanced_feature_engineering import AdvancedFeatureEngineer
from app.algorithms.experiment_evaluation import ExperimentEvaluator
from app.algorithms.enhanced_shap_analysis import EnhancedSHAPAnalyzer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
)
import xgboost as xgb
import lightgbm as lgb

logger = logging.getLogger(__name__)
router = APIRouter()

# 全局变量存储实验结果
experiment_results = {}


class ExperimentConfig(BaseModel):
    """实验配置"""
    knn_neighbors: int = 5
    contamination: float = 0.05
    variance_threshold: float = 0.01
    mi_percentile: float = 0.8
    n_features_rfe: int = 38
    train_size: float = 0.7
    val_size: float = 0.15
    test_size: float = 0.15


class PreprocessResponse(BaseModel):
    """预处理响应"""
    success: bool
    message: str
    train_samples: int
    val_samples: int
    test_samples: int
    train_positive: int
    val_positive: int
    test_positive: int
    missing_handled: bool
    outliers_detected: bool
    standardized: bool
    balanced: bool


class FeatureEngineeringResponse(BaseModel):
    """特征工程响应"""
    success: bool
    message: str
    original_features: int
    core_features: int
    final_features: int
    steps: List[Dict]


class ModelTrainingResponse(BaseModel):
    """模型训练响应"""
    success: bool
    message: str
    models_trained: List[str]
    models_failed: List[str] = []
    best_model: str
    best_auc: float


@router.post("/experiment/preprocess", response_model=PreprocessResponse)
async def preprocess_data(
    file: UploadFile = File(...),
    config: ExperimentConfig = ExperimentConfig()
):
    """
    数据预处理

    实现论文第5.2节的数据预处理流程：
    - KNN插补
    - 孤立森林异常检测
    - Z-score标准化
    - SMOTE过采样
    - 分层数据集划分
    """
    try:
        logger.info("开始数据预处理")

        # 异步路由中应 await 读取上传内容，再用 BytesIO 解析（直接 pd.read_csv(file.file) 在部分环境下会失败或读到空表）
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="未收到文件内容，请确认使用 multipart 字段名 file 上传 CSV")

        try:
            df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(raw), encoding="gbk")

        logger.info(f"数据集形状: {df.shape}")

        # 分离特征和标签
        if "CAD_risk" not in df.columns:
            raise HTTPException(status_code=400, detail="数据集必须包含'CAD_risk'列")

        X = df.drop(columns=["CAD_risk"])
        y = pd.to_numeric(df["CAD_risk"], errors="coerce")
        valid = y.notna()
        if not valid.all():
            n_bad = int((~valid).sum())
            raise HTTPException(
                status_code=400,
                detail=f"标签列 CAD_risk 存在 {n_bad} 个无法解析为数值的行，请检查数据",
            )
        y = y.astype(int)

        # 特征列需为数值（论文实验管线使用 sklearn / SMOTE）
        X = X.apply(pd.to_numeric, errors="coerce")
        if X.isna().all().any():
            bad_cols = X.columns[X.isna().all()].tolist()
            raise HTTPException(
                status_code=400,
                detail=f"以下特征列无法转为数值（全为缺失/非数字），请处理后再试: {bad_cols[:10]}",
            )

        # 执行预处理
        preprocessor = AdvancedPreprocessor()
        result = preprocessor.preprocess_pipeline(
            X, y,
            handle_missing=True,
            detect_outliers_flag=True,
            standardize=True,
            balance=True,
            split=True,
            knn_neighbors=config.knn_neighbors,
            contamination=config.contamination,
            train_size=config.train_size,
            val_size=config.val_size,
            test_size=config.test_size
        )

        # 保存结果到全局变量
        experiment_results['preprocessed_data'] = result
        experiment_results['preprocessor'] = preprocessor

        return PreprocessResponse(
            success=True,
            message="数据预处理完成",
            train_samples=int(len(result["X_train"])),
            val_samples=int(len(result["X_val"])),
            test_samples=int(len(result["X_test"])),
            train_positive=int((result["y_train"] == 1).sum()),
            val_positive=int((result["y_val"] == 1).sum()),
            test_positive=int((result["y_test"] == 1).sum()),
            missing_handled=result.get("missing_handled", False),
            outliers_detected=result.get("outliers_detected", False),
            standardized=result.get("standardized", False),
            balanced=result.get("balanced", False),
        )

    except HTTPException:
        raise
    except ValueError as e:
        msg = str(e)
        logger.warning("预处理参数/数据问题: %s", msg)
        raise HTTPException(
            status_code=400,
            detail=f"预处理无法完成（样本量是否过少、类别是否单一？）: {msg}",
        )
    except Exception as e:
        logger.error(f"预处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预处理失败: {str(e)}")


@router.post("/experiment/feature-engineering", response_model=FeatureEngineeringResponse)
async def feature_engineering(config: ExperimentConfig = ExperimentConfig()):
    """
    特征工程

    实现论文第5.3节的特征工程流程：
    - 方差阈值选择
    - 互信息选择
    - RFE递归特征消除
    - 临床特征交叉
    """
    try:
        logger.info("开始特征工程")

        # 检查是否已完成预处理
        if 'preprocessed_data' not in experiment_results:
            raise HTTPException(status_code=400, detail="请先完成数据预处理")

        result = experiment_results['preprocessed_data']
        X_train = result['X_train']
        y_train = result['y_train']

        # 执行特征工程
        engineer = AdvancedFeatureEngineer()
        X_train_eng, report = engineer.feature_engineering_pipeline(
            X_train, y_train,
            variance_threshold=config.variance_threshold,
            mi_percentile=config.mi_percentile,
            n_features_rfe=config.n_features_rfe,
            create_poly=False,
            create_interactions=True,
            remove_correlated=True
        )

        # 验证/测试集需走与训练相同的变换（交互项等不在原始列中，不能按列名直接子集）
        X_val_eng = engineer.transform_pipeline(result['X_val'])
        X_test_eng = engineer.transform_pipeline(result['X_test'])

        # 保存结果
        experiment_results['engineered_data'] = {
            'X_train': X_train_eng,
            'X_val': X_val_eng,
            'X_test': X_test_eng,
            'y_train': result['y_train'],
            'y_val': result['y_val'],
            'y_test': result['y_test']
        }
        experiment_results['engineer'] = engineer
        experiment_results['feature_report'] = report

        return FeatureEngineeringResponse(
            success=True,
            message="特征工程完成",
            original_features=report['original_features'],
            core_features=report['core_features'],
            final_features=report['final_features'],
            steps=report['steps']
        )

    except Exception as e:
        logger.error(f"特征工程失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"特征工程失败: {str(e)}")


def _build_thesis_experiment_models():
    """
    论文实验对比模型集合（ sklearn + XGBoost + LightGBM ）。
    单个失败不影响其余模型；树模型为主，另含逻辑回归与决策树基线。
    """
    return [
        (
            "Logistic Regression",
            lambda: LogisticRegression(
                max_iter=3000, random_state=42, class_weight="balanced", solver="lbfgs"
            ),
        ),
        (
            "Decision Tree",
            lambda: DecisionTreeClassifier(
                max_depth=12, min_samples_leaf=4, random_state=42, class_weight="balanced"
            ),
        ),
        (
            "HistGradientBoosting",
            lambda: HistGradientBoostingClassifier(
                max_iter=200, max_depth=10, random_state=42, learning_rate=0.06
            ),
        ),
        (
            "Gradient Boosting",
            lambda: GradientBoostingClassifier(
                n_estimators=120, max_depth=4, learning_rate=0.08, random_state=42
            ),
        ),
        (
            "Extra Trees",
            lambda: ExtraTreesClassifier(
                n_estimators=120, random_state=42, n_jobs=-1, class_weight="balanced"
            ),
        ),
        (
            "Random Forest",
            lambda: RandomForestClassifier(
                n_estimators=120, random_state=42, n_jobs=-1, class_weight="balanced"
            ),
        ),
        (
            "XGBoost",
            lambda: xgb.XGBClassifier(
                n_estimators=150,
                max_depth=6,
                learning_rate=0.08,
                random_state=42,
                n_jobs=-1,
                eval_metric="logloss",
            ),
        ),
        (
            "LightGBM",
            lambda: lgb.LGBMClassifier(
                n_estimators=150,
                max_depth=8,
                learning_rate=0.08,
                random_state=42,
                verbose=-1,
                n_jobs=-1,
            ),
        ),
    ]


@router.post("/experiment/train-models", response_model=ModelTrainingResponse)
async def train_models(background_tasks: BackgroundTasks):
    """
    训练多模型并对比：逻辑回归、决策树、HistGB、GBDT、极端随机树、随机森林、XGBoost、LightGBM。
    任一模型训练失败会跳过并记入 models_failed。
    """
    try:
        logger.info("开始训练模型")

        # 检查是否已完成特征工程
        if 'engineered_data' not in experiment_results:
            raise HTTPException(status_code=400, detail="请先完成特征工程")

        data = experiment_results['engineered_data']
        X_train = data['X_train']
        y_train = data['y_train']
        X_test = data['X_test']
        y_test = data['y_test']

        trained_models: Dict[str, object] = {}
        failures: List[str] = []

        for name, factory in _build_thesis_experiment_models():
            try:
                logger.info("训练 %s ...", name)
                model = factory()
                model.fit(X_train, y_train)
                trained_models[name] = model
            except Exception as ex:
                logger.warning("模型 %s 训练失败: %s", name, ex)
                failures.append(name)

        if not trained_models:
            raise HTTPException(
                status_code=500,
                detail="全部模型训练失败，请检查数据或依赖。失败项: " + ", ".join(failures),
            )

        evaluator = ExperimentEvaluator()
        best_auc = 0.0
        best_model_name: Optional[str] = None

        for name, model in trained_models.items():
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            metrics = evaluator.evaluate_model(name, y_test, y_pred, y_prob)
            auc_v = metrics.get("auc")
            if auc_v is not None and auc_v > best_auc:
                best_auc = float(auc_v)
                best_model_name = name

        if best_model_name is None:
            best_model_name = next(iter(trained_models.keys()))
            best_auc = 0.0

        experiment_results['trained_models'] = trained_models
        experiment_results['evaluator'] = evaluator
        experiment_results['best_model_name'] = best_model_name

        msg = "模型训练完成"
        if failures:
            msg += f"（已跳过 {len(failures)} 个失败模型）"

        return ModelTrainingResponse(
            success=True,
            message=msg,
            models_trained=list(trained_models.keys()),
            models_failed=failures,
            best_model=best_model_name,
            best_auc=float(best_auc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模型训练失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"模型训练失败: {str(e)}")


@router.get("/experiment/results")
async def get_experiment_results():
    """获取实验结果"""
    try:
        if 'evaluator' not in experiment_results:
            raise HTTPException(status_code=400, detail="请先完成模型训练")

        evaluator = experiment_results['evaluator']

        # 生成对比表
        comparison_df = evaluator.create_comparison_table()

        return {
            "success": True,
            "comparison_table": comparison_df.to_dict('records'),
            "best_model": experiment_results.get('best_model_name'),
            "models": evaluator.model_names
        }

    except Exception as e:
        logger.error(f"获取结果失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")


@router.get("/experiment/shap-analysis")
async def shap_analysis(sample_idx: int = 0):
    """
    SHAP可解释性分析

    实现论文第5.5节的SHAP分析
    """
    try:
        if 'trained_models' not in experiment_results:
            raise HTTPException(status_code=400, detail="请先完成模型训练")

        best_model_name = experiment_results['best_model_name']
        best_model = experiment_results['trained_models'][best_model_name]

        data = experiment_results['engineered_data']
        X_train = data['X_train']
        X_test = data['X_test']

        # 创建SHAP分析器（最佳模型可能为逻辑回归等非树模型）
        analyzer = EnhancedSHAPAnalyzer(best_model, X_train)
        if isinstance(best_model, LogisticRegression):
            analyzer.create_explainer(explainer_type="linear")
        else:
            try:
                analyzer.create_explainer(explainer_type="tree")
            except Exception as tree_err:
                logger.warning(
                    "TreeExplainer 不可用 (%s)，回退 KernelExplainer（较慢）",
                    tree_err,
                )
                n_bg = min(60, max(20, len(X_train) // 8))
                analyzer.create_explainer(explainer_type="kernel", n_background=n_bg)
        analyzer.compute_shap_values(X_test)

        # 全局特征重要性
        importance = analyzer.get_global_feature_importance(X_test, top_k=10)

        # 解释单个预测
        explanation = analyzer.explain_prediction(X_test, sample_idx=sample_idx, top_k=10)

        # 生成临床解读
        interpretation = analyzer.generate_clinical_interpretation(explanation)

        return {
            "success": True,
            "model": best_model_name,
            "feature_importance": importance.to_dict('records'),
            "sample_explanation": {
                "sample_idx": explanation['sample_idx'],
                "prediction": float(explanation['prediction']),
                "base_value": float(explanation['base_value']),
                "top_positive": explanation['top_positive_features'][:5],
                "top_negative": explanation['top_negative_features'][:3]
            },
            "clinical_interpretation": interpretation
        }

    except Exception as e:
        logger.error(f"SHAP分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SHAP分析失败: {str(e)}")


def _unlink_report_file(path: str) -> None:
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


@router.get("/experiment/download-report")
async def download_report(background_tasks: BackgroundTasks):
    """下载实验报告（PDF）"""
    try:
        if 'evaluator' not in experiment_results:
            raise HTTPException(status_code=400, detail="请先完成模型训练")

        evaluator = experiment_results['evaluator']

        report_path = os.path.abspath(
            f"experiment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        evaluator.generate_report_pdf(output_path=report_path)

        download_name = f"heartcycle_experiment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        background_tasks.add_task(_unlink_report_file, report_path)

        return FileResponse(
            report_path,
            media_type='application/pdf',
            filename=download_name,
        )

    except Exception as e:
        logger.error(f"下载报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载报告失败: {str(e)}")


@router.post("/experiment/reset")
async def reset_experiment():
    """重置实验"""
    global experiment_results
    experiment_results = {}
    return {"success": True, "message": "实验已重置"}


@router.get("/experiment/status")
async def get_experiment_status():
    """获取实验状态"""
    return {
        "success": True,
        "status": {
            "preprocessed": 'preprocessed_data' in experiment_results,
            "feature_engineered": 'engineered_data' in experiment_results,
            "models_trained": 'trained_models' in experiment_results,
            "results_available": 'evaluator' in experiment_results
        }
    }
