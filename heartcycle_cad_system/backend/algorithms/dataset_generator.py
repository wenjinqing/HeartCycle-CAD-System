"""
实验数据集生成器
生成符合论文要求的模拟冠心病风险预测数据集
"""
import numpy as np
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class CADDatasetGenerator:
    """冠心病数据集生成器"""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        np.random.seed(random_state)

    def generate_dataset(self, n_samples: int = 10000,
                        positive_ratio: float = 0.3) -> Tuple[pd.DataFrame, pd.Series]:
        """
        生成冠心病风险预测数据集

        论文要求：
        - 10,000例患者样本（阳性3000例，阴性7000例）
        - 52个临床特征（人口统计学、生理指标、实验室检查、HRV特征）

        Parameters:
        -----------
        n_samples : int
            样本数量，默认10000
        positive_ratio : float
            阳性样本比例，默认0.3

        Returns:
        --------
        X : pd.DataFrame
            特征数据
        y : pd.Series
            标签数据（0=阴性，1=阳性）
        """
        logger.info(f"开始生成数据集: n_samples={n_samples}, positive_ratio={positive_ratio}")

        # 生成标签
        n_positive = int(n_samples * positive_ratio)
        n_negative = n_samples - n_positive
        y = np.concatenate([np.ones(n_positive), np.zeros(n_negative)])
        np.random.shuffle(y)

        # 初始化特征字典
        features = {}

        # 1. 人口统计学特征
        features.update(self._generate_demographic_features(n_samples, y))

        # 2. 生理指标
        features.update(self._generate_physiological_features(n_samples, y))

        # 3. 实验室检查指标
        features.update(self._generate_laboratory_features(n_samples, y))

        # 4. HRV特征
        features.update(self._generate_hrv_features(n_samples, y))

        # 5. 生活方式因素
        features.update(self._generate_lifestyle_features(n_samples, y))

        # 创建DataFrame
        X = pd.DataFrame(features)
        y = pd.Series(y, name='CAD_risk')

        logger.info(f"数据集生成完成: {X.shape}")
        logger.info(f"特征数量: {X.shape[1]}")
        logger.info(f"阳性样本: {(y == 1).sum()} ({(y == 1).sum() / len(y) * 100:.1f}%)")
        logger.info(f"阴性样本: {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")

        return X, y

    def _generate_demographic_features(self, n_samples: int, y: np.ndarray) -> dict:
        """生成人口统计学特征"""
        features = {}

        # 年龄（冠心病风险随年龄增加，但增加噪声和重叠）
        age_mean = np.where(y == 1, 58, 52)  # 减小差异
        features['age'] = np.clip(
            np.random.normal(age_mean, 12) + np.random.normal(0, 3),  # 增加噪声
            18, 90
        )

        # 性别（男性风险更高，但减小差异）
        male_prob = np.where(y == 1, 0.58, 0.52)  # 减小差异
        features['gender_male'] = np.random.binomial(1, male_prob)

        # 身高（cm）- 添加随机噪声
        features['height_cm'] = np.random.normal(
            np.where(features['gender_male'] == 1, 172, 160),
            10  # 增加方差
        )

        # 体重（kg）- 减小与标签的关联
        weight_mean = np.where(y == 1, 73, 68)  # 减小差异
        features['weight_kg'] = np.clip(
            np.random.normal(weight_mean, 15) + np.random.normal(0, 5),  # 增加噪声
            40, 150
        )

        # BMI
        features['bmi'] = features['weight_kg'] / (features['height_cm'] / 100) ** 2

        return features

    def _generate_physiological_features(self, n_samples: int, y: np.ndarray) -> dict:
        """生成生理指标"""
        features = {}

        # 收缩压（mmHg）- 减小差异，增加重叠
        sbp_mean = np.where(y == 1, 138, 128)  # 减小差异
        features['sbp'] = np.clip(
            np.random.normal(sbp_mean, 18) + np.random.normal(0, 5),  # 增加噪声
            90, 200
        )

        # 舒张压（mmHg）
        dbp_mean = np.where(y == 1, 85, 80)  # 减小差异
        features['dbp'] = np.clip(
            np.random.normal(dbp_mean, 12) + np.random.normal(0, 3),
            60, 120
        )

        # 心率（次/分钟）
        hr_mean = np.where(y == 1, 76, 73)  # 减小差异
        features['heart_rate'] = np.clip(
            np.random.normal(hr_mean, 12) + np.random.normal(0, 3),
            50, 120
        )

        # 呼吸频率（次/分钟）- 与标签无关
        features['respiratory_rate'] = np.clip(
            np.random.normal(16, 3),  # 增加方差
            12, 24
        )

        # 体温（°C）- 与标签无关
        features['temperature'] = np.random.normal(36.5, 0.4)

        return features

    def _generate_laboratory_features(self, n_samples: int, y: np.ndarray) -> dict:
        """生成实验室检查指标"""
        features = {}

        # 总胆固醇（mmol/L）- 减小差异
        chol_mean = np.where(y == 1, 5.4, 4.9)
        features['cholesterol'] = np.clip(
            np.random.normal(chol_mean, 1.0) + np.random.normal(0, 0.3),
            3.0, 9.0
        )

        # LDL胆固醇（mmol/L）- 减小差异
        ldl_mean = np.where(y == 1, 3.4, 3.0)
        features['ldl'] = np.clip(
            np.random.normal(ldl_mean, 0.8) + np.random.normal(0, 0.2),
            1.0, 6.0
        )

        # HDL胆固醇（mmol/L）- 减小差异
        hdl_mean = np.where(y == 1, 1.2, 1.35)
        features['hdl'] = np.clip(
            np.random.normal(hdl_mean, 0.35) + np.random.normal(0, 0.1),
            0.5, 2.5
        )

        # 甘油三酯（mmol/L）
        tg_mean = np.where(y == 1, 1.9, 1.6)
        features['triglycerides'] = np.clip(
            np.random.normal(tg_mean, 0.9) + np.random.normal(0, 0.3),
            0.5, 5.0
        )

        # 空腹血糖（mmol/L）
        glucose_mean = np.where(y == 1, 6.0, 5.4)
        features['glucose'] = np.clip(
            np.random.normal(glucose_mean, 1.4) + np.random.normal(0, 0.4),
            3.5, 12.0
        )

        # 糖化血红蛋白（%）
        hba1c_mean = np.where(y == 1, 5.9, 5.5)
        features['hba1c'] = np.clip(
            np.random.normal(hba1c_mean, 0.9) + np.random.normal(0, 0.3),
            4.0, 10.0
        )

        # 肌酐（μmol/L）- 与标签关联较弱
        creatinine_mean = np.where(y == 1, 82, 78)
        features['creatinine'] = np.clip(
            np.random.normal(creatinine_mean, 18),
            40, 150
        )

        # 尿酸（μmol/L）
        uric_acid_mean = np.where(y == 1, 360, 330)
        features['uric_acid'] = np.clip(
            np.random.normal(uric_acid_mean, 70) + np.random.normal(0, 20),
            150, 600
        )

        # C反应蛋白（mg/L）- 减小差异
        crp_mean = np.where(y == 1, 3.5, 2.5)
        features['crp'] = np.clip(
            np.random.lognormal(np.log(crp_mean), 1.0),
            0.1, 20.0
        )

        # 同型半胱氨酸（μmol/L）
        hcy_mean = np.where(y == 1, 13, 11)
        features['homocysteine'] = np.clip(
            np.random.normal(hcy_mean, 5) + np.random.normal(0, 2),
            5, 30
        )

        return features

    def _generate_hrv_features(self, n_samples: int, y: np.ndarray) -> dict:
        """生成HRV特征（心率变异性）"""
        features = {}

        # 时域特征
        # SDNN（ms）- 减小差异，增加重叠
        sdnn_mean = np.where(y == 1, 42, 50)  # 减小差异
        features['sdnn'] = np.clip(
            np.random.normal(sdnn_mean, 18) + np.random.normal(0, 5),
            10, 150
        )

        # RMSSD（ms）- 减小差异
        rmssd_mean = np.where(y == 1, 30, 38)
        features['rmssd'] = np.clip(
            np.random.normal(rmssd_mean, 15) + np.random.normal(0, 4),
            5, 100
        )

        # pNN50（%）- 减小差异
        pnn50_mean = np.where(y == 1, 12, 16)
        features['pnn50'] = np.clip(
            np.random.normal(pnn50_mean, 10) + np.random.normal(0, 3),
            0, 50
        )

        # SDSD（ms）- 连续RR间期差值的标准差
        features['sdsd'] = features['rmssd'] * np.sqrt(2)

        # 频域特征
        # LF功率（ms²）- 减小差异
        lf_mean = np.where(y == 1, 520, 620)
        features['lf_power'] = np.clip(
            np.random.lognormal(np.log(lf_mean), 0.8),  # 增加方差
            50, 3000
        )

        # HF功率（ms²）- 减小差异
        hf_mean = np.where(y == 1, 350, 450)
        features['hf_power'] = np.clip(
            np.random.lognormal(np.log(hf_mean), 0.8),
            50, 2000
        )

        # LF/HF比值
        features['lf_hf_ratio'] = features['lf_power'] / (features['hf_power'] + 1e-10)

        # VLF功率（ms²）- 减小差异
        vlf_mean = np.where(y == 1, 380, 460)
        features['vlf_power'] = np.clip(
            np.random.lognormal(np.log(vlf_mean), 0.8),
            50, 2000
        )

        # 总功率
        features['total_power'] = features['vlf_power'] + features['lf_power'] + features['hf_power']

        # 非线性特征
        # SD1（ms）- 减小差异
        sd1_mean = np.where(y == 1, 22, 28)
        features['sd1'] = np.clip(
            np.random.normal(sd1_mean, 12) + np.random.normal(0, 3),
            5, 80
        )

        # SD2（ms）- 减小差异
        sd2_mean = np.where(y == 1, 55, 65)
        features['sd2'] = np.clip(
            np.random.normal(sd2_mean, 22) + np.random.normal(0, 6),
            10, 150
        )

        # SD1/SD2比值
        features['sd1_sd2_ratio'] = features['sd1'] / (features['sd2'] + 1e-10)

        # 样本熵 - 减小差异
        sampen_mean = np.where(y == 1, 1.35, 1.50)
        features['sample_entropy'] = np.clip(
            np.random.normal(sampen_mean, 0.5) + np.random.normal(0, 0.15),
            0.5, 3.0
        )

        # 近似熵 - 减小差异
        apen_mean = np.where(y == 1, 1.05, 1.20)
        features['approximate_entropy'] = np.clip(
            np.random.normal(apen_mean, 0.4) + np.random.normal(0, 0.12),
            0.3, 2.5
        )

        # DFA α1（短期波动指数）- 减小差异
        dfa_alpha1_mean = np.where(y == 1, 1.02, 0.98)
        features['dfa_alpha1'] = np.clip(
            np.random.normal(dfa_alpha1_mean, 0.25) + np.random.normal(0, 0.08),
            0.5, 1.5
        )

        # DFA α2（长期波动指数）- 减小差异
        dfa_alpha2_mean = np.where(y == 1, 0.98, 0.96)
        features['dfa_alpha2'] = np.clip(
            np.random.normal(dfa_alpha2_mean, 0.18) + np.random.normal(0, 0.06),
            0.6, 1.3
        )

        return features

    def _generate_lifestyle_features(self, n_samples: int, y: np.ndarray) -> dict:
        """生成生活方式因素"""
        features = {}

        # 吸烟状态（0=不吸烟，1=曾经吸烟，2=当前吸烟）- 减小差异
        features['smoking_status'] = np.array([
            np.random.choice([0, 1, 2], p=[0.4, 0.3, 0.3] if label == 1 else [0.5, 0.25, 0.25])
            for label in y
        ])

        # 饮酒状态（0=不饮酒，1=适量，2=过量）- 减小差异
        features['alcohol_status'] = np.array([
            np.random.choice([0, 1, 2], p=[0.45, 0.35, 0.20] if label == 1 else [0.50, 0.35, 0.15])
            for label in y
        ])

        # 运动频率（次/周）- 减小差异
        exercise_mean = np.where(y == 1, 2.2, 3.0)
        features['exercise_frequency'] = np.clip(
            np.random.poisson(exercise_mean) + np.random.randint(-1, 2, size=n_samples),
            0, 7
        )

        # 糖尿病史（0=无，1=有）- 减小差异
        diabetes_prob = np.where(y == 1, 0.28, 0.15)
        features['diabetes_history'] = np.random.binomial(1, diabetes_prob)

        # 高血压史（0=无，1=有）- 减小差异
        hypertension_prob = np.where(y == 1, 0.48, 0.32)
        features['hypertension_history'] = np.random.binomial(1, hypertension_prob)

        # 家族史（0=无，1=有）- 减小差异
        family_history_prob = np.where(y == 1, 0.38, 0.28)
        features['family_history'] = np.random.binomial(1, family_history_prob)

        return features

    def save_dataset(self, X: pd.DataFrame, y: pd.Series,
                    output_path: str = 'cad_dataset.csv'):
        """保存数据集到CSV文件"""
        df = pd.concat([X, y], axis=1)
        df.to_csv(output_path, index=False)
        logger.info(f"数据集已保存到: {output_path}")

    def generate_and_save(self, n_samples: int = 10000,
                         positive_ratio: float = 0.3,
                         output_path: str = 'cad_dataset.csv') -> Tuple[pd.DataFrame, pd.Series]:
        """生成并保存数据集"""
        X, y = self.generate_dataset(n_samples, positive_ratio)
        self.save_dataset(X, y, output_path)
        return X, y


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 生成数据集
    generator = CADDatasetGenerator(random_state=42)

    # 确保data目录存在
    import os
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    os.makedirs(data_dir, exist_ok=True)

    output_path = os.path.join(data_dir, 'cad_dataset_10k.csv')
    X, y = generator.generate_and_save(
        n_samples=10000,
        positive_ratio=0.3,
        output_path=output_path
    )

    print("\n数据集统计信息:")
    print(f"样本数量: {len(X)}")
    print(f"特征数量: {X.shape[1]}")
    print(f"\n特征列表:")
    for i, col in enumerate(X.columns, 1):
        print(f"{i:2d}. {col}")

    print(f"\n标签分布:")
    print(y.value_counts())
    print(f"\n数据集前5行:")
    print(pd.concat([X.head(), y.head()], axis=1))
