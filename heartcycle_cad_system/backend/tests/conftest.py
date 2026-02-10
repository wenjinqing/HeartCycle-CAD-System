"""
Pytest配置和共享fixtures
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_features():
    """示例特征数据"""
    import numpy as np
    return np.random.rand(10, 20)  # 10个样本，20个特征


@pytest.fixture
def sample_labels():
    """示例标签数据"""
    import numpy as np
    return np.random.randint(0, 2, 10)  # 10个二分类标签


@pytest.fixture
def mock_model_data():
    """模拟模型数据"""
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np

    model = RandomForestClassifier(n_estimators=10, random_state=42)
    X = np.random.rand(50, 20)
    y = np.random.randint(0, 2, 50)
    model.fit(X, y)

    return {
        'model': model,
        'model_type': 'rf',
        'feature_names': [f'feature_{i}' for i in range(20)],
        'metadata': {
            'n_features': 20,
            'created_at': '2025-01-01T00:00:00'
        }
    }
