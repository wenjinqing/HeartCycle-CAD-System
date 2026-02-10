"""
训练模型的快速脚本
用于创建初始模型供前端使用
"""
import sys
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))


def create_dummy_data() -> Tuple[str, str]:
    """创建示例数据用于训练"""
    print("正在生成示例训练数据...")
    
    # 使用generate_training_data生成数据
    try:
        # 导入同目录下的generate_training_data模块
        script_dir = Path(__file__).parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        
        from generate_training_data import generate_training_data
        
        output_dir = script_dir.parent / 'data' / 'features'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        features_file, labels_file = generate_training_data(
            n_samples=200,
            output_dir=str(output_dir)
        )
        
        print(f"\n示例数据已保存:")
        print(f"  特征文件: {features_file}")
        print(f"  标签文件: {labels_file}")
        
        return features_file, labels_file
        
    except (ImportError, Exception) as e:
        print(f"警告: 无法使用generate_training_data ({e})，使用简单的随机数据生成方法")
        return _create_simple_dummy_data()


def _create_simple_dummy_data() -> Tuple[str, str]:
    """创建简单的示例数据（备用方法）"""
    n_samples = 200
    n_features = 10  # 5个临床特征 + 5个HRV特征
    
    # 生成特征数据
    np.random.seed(42)
    X = np.random.rand(n_samples, n_features)
    
    # 生成标签（模拟二分类问题）
    y = np.random.binomial(1, 0.3 + 0.4 * X[:, 0], n_samples)  # 更真实的标签分布
    
    # 创建DataFrame
    feature_names = [
        'age', 'gender', 'height', 'weight', 'bmi',
        'mean_rr', 'sdnn', 'rmssd', 'pnn50', 'lf_hf_ratio'
    ]
    
    df_features = pd.DataFrame(X, columns=feature_names)
    df_labels = pd.DataFrame(y, columns=['label'])
    
    # 保存到文件
    script_dir = Path(__file__).parent
    features_file = script_dir.parent / 'data' / 'features' / 'train_features.csv'
    labels_file = script_dir.parent / 'data' / 'features' / 'train_labels.csv'
    
    features_file.parent.mkdir(parents=True, exist_ok=True)
    
    df_features.to_csv(features_file, index=False)
    df_labels.to_csv(labels_file, index=False)
    
    print(f"示例数据已保存:")
    print(f"  特征文件: {features_file}")
    print(f"  标签文件: {labels_file}")
    print(f"  样本数: {n_samples}, 特征数: {n_features}")
    
    return str(features_file), str(labels_file)


def train_via_api(features_file: str, labels_file: str) -> Optional[str]:
    """通过API训练模型"""
    try:
        import requests
    except ImportError:
        print("\nrequests库未安装，跳过API训练")
        print("安装: pip install requests")
        return None
    
    print("\n通过API训练模型...")
    
    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("后端服务未运行，请先启动后端: python scripts/start_backend.py")
            return None
    except (requests.RequestException, ConnectionError):
        print("后端服务未运行，请先启动后端: python scripts/start_backend.py")
        return None
        
        # 训练模型
        response = requests.post(
            "http://localhost:8000/api/v1/train",
            json={
                "feature_file": features_file,
                "label_file": labels_file,
                "model_type": "rf",
                "cv_folds": 5,
                "random_state": 42
            },
            timeout=300  # 5分钟超时
        )
        
        if response.status_code == 200:
            result = response.json()
            model_id = result.get('model_id') or result.get('data', {}).get('model_id')
            print(f"\n模型训练成功!")
            print(f"  模型ID: {model_id}")
            
            # 获取模型详情
            detail_response = requests.get(f"http://localhost:8000/api/v1/models/{model_id}")
            if detail_response.status_code == 200:
                detail = detail_response.json()
                detail_data = detail.get('data') or detail
                metrics = detail_data.get('metrics', {})
                if metrics:
                    auc = metrics.get('roc_auc', {})
                    if isinstance(auc, dict):
                        auc_value = auc.get('mean', auc.get('roc_auc', 'N/A'))
                    else:
                        auc_value = auc
                    print(f"  AUC: {auc_value:.4f}" if isinstance(auc_value, (int, float)) else f"  AUC: {auc_value}")
            
            return model_id
        else:
            print(f"训练失败: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"\nAPI训练失败: {e}")
        return None


def train_via_code(features_file: str, labels_file: str) -> Optional[str]:
    """直接使用代码训练模型"""
    print("\n直接使用代码训练模型...")
    
    try:
        from algorithms.model_training import ModelTrainer
        
        # 加载数据
        features_path = Path(features_file)
        labels_path = Path(labels_file)
        
        if not features_path.exists():
            raise FileNotFoundError(f"特征文件不存在: {features_file}")
        if not labels_path.exists():
            raise FileNotFoundError(f"标签文件不存在: {labels_file}")
        
        df_features = pd.read_csv(features_path)
        df_labels = pd.read_csv(labels_path)
        
        X = df_features.values
        y = df_labels.values.ravel()
        
        print(f"加载数据: {len(X)}个样本, {X.shape[1]}个特征")
        
        # 训练模型
        trainer = ModelTrainer(random_state=42)
        result = trainer.train(
            X=X,
            y=y,
            model_type="rf",
            cv_folds=5,
            feature_names=df_features.columns.tolist()
        )
        
        print(f"\n模型训练成功!")
        auc = result['metrics']['roc_auc']['mean']
        accuracy = result['metrics']['accuracy']['mean']
        print(f"  CV AUC: {auc:.4f}")
        print(f"  CV Accuracy: {accuracy:.4f}")
        
        # 保存模型
        model_id = "default_cad_model"
        model_path = trainer.save(model_id, metadata={
            "description": "默认CAD预测模型",
            "feature_names": df_features.columns.tolist(),
            "n_samples": len(X),
            "n_features": X.shape[1],
            "metrics": result['metrics']
        })
        
        print(f"  模型已保存: {model_path}")
        print(f"  模型ID: {model_id}")
        
        return model_id
        
    except Exception as e:
        print(f"代码训练失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("HeartCycle CAD System - 模型训练脚本")
    print("=" * 60)
    
    # 1. 创建示例数据
    features_file, labels_file = create_dummy_data()
    
    # 转换为绝对路径
    features_file = str(Path(features_file).absolute())
    labels_file = str(Path(labels_file).absolute())
    
    print(f"\n使用以下文件训练模型:")
    print(f"  特征: {features_file}")
    print(f"  标签: {labels_file}")
    
    # 2. 尝试通过API训练
    model_id = train_via_api(features_file, labels_file)
    
    # 3. 如果API失败，使用代码训练
    if not model_id:
        model_id = train_via_code(features_file, labels_file)
    
    if model_id:
        print("\n" + "=" * 60)
        print("模型训练完成！")
        print("=" * 60)
        print(f"\n现在可以在前端使用模型ID: {model_id}")
        print("\n或者前端会自动使用第一个可用模型")
        print("\n如果使用API训练的模型，请确保后端服务正在运行")
    else:
        print("\n模型训练失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()


