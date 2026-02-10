"""
H5文件标签自动提取工具
从H5文件目录自动查找SubjectMetadata.csv并提取标签信息
"""
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.core.logger import logger


class H5LabelExtractor:
    """H5文件标签提取器"""

    # 标签映射规则
    LABEL_MAPPING = {
        'healthy': 0,
        'normal': 0,
        'cad': 1,
        'coronary artery disease': 1,
        'disease': 1,
        'patient': 1
    }

    @staticmethod
    def find_metadata_file(h5_file_path: str) -> Optional[str]:
        """
        查找SubjectMetadata.csv文件

        Parameters:
        -----------
        h5_file_path : str
            H5文件路径

        Returns:
        --------
        Optional[str] : 元数据文件路径，未找到返回None
        """
        h5_path = Path(h5_file_path)

        # 在同级目录和父目录查找
        search_dirs = [
            h5_path.parent,  # 同级目录
            h5_path.parent.parent,  # 父目录
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            # 查找SubjectMetadata.csv文件
            for file in search_dir.glob('*SubjectMetadata.csv'):
                logger.info(f"找到元数据文件: {file}")
                return str(file)

        logger.warning(f"未找到元数据文件，搜索路径: {search_dirs}")
        return None

    @staticmethod
    def extract_filename_from_path(file_path: str) -> str:
        """
        从路径中提取文件名（不含扩展名）

        Parameters:
        -----------
        file_path : str
            文件路径

        Returns:
        --------
        str : 文件名（不含扩展名）
        """
        return Path(file_path).stem

    @staticmethod
    def normalize_label(disease_status: str) -> int:
        """
        将疾病状态标准化为0/1标签

        Parameters:
        -----------
        disease_status : str
            疾病状态描述

        Returns:
        --------
        int : 0=健康，1=疾病
        """
        status_lower = str(disease_status).lower().strip()

        # 查找映射表
        for key, value in H5LabelExtractor.LABEL_MAPPING.items():
            if key in status_lower:
                return value

        # 默认：如果包含数字1，视为疾病；否则视为健康
        if '1' in status_lower:
            return 1
        return 0

    @classmethod
    def extract_labels_from_h5_files(
        cls,
        h5_files: List[str],
        metadata_file: Optional[str] = None
    ) -> Tuple[Dict[str, int], Optional[pd.DataFrame]]:
        """
        从H5文件列表自动提取标签

        Parameters:
        -----------
        h5_files : List[str]
            H5文件路径列表
        metadata_file : Optional[str]
            手动指定的元数据文件路径（可选）

        Returns:
        --------
        Tuple[Dict[str, int], Optional[pd.DataFrame]]
            - 文件名到标签的映射字典
            - 元数据DataFrame（如果找到）
        """
        # 1. 查找元数据文件
        if metadata_file is None:
            # 自动查找：从第一个H5文件开始搜索
            if not h5_files:
                raise ValueError("H5文件列表为空")
            metadata_file = cls.find_metadata_file(h5_files[0])

        if metadata_file is None:
            logger.warning("未找到元数据文件，无法自动提取标签")
            return {}, None

        # 2. 读取元数据
        try:
            metadata_df = pd.read_csv(metadata_file)
            logger.info(f"成功读取元数据文件: {metadata_file}, 包含 {len(metadata_df)} 条记录")
        except Exception as e:
            logger.error(f"读取元数据文件失败: {e}")
            return {}, None

        # 3. 检查必需的列
        required_columns = ['File_Name', 'Disease_Status']
        missing_columns = [col for col in required_columns if col not in metadata_df.columns]

        if missing_columns:
            logger.error(f"元数据文件缺少必需列: {missing_columns}")
            logger.info(f"可用列: {metadata_df.columns.tolist()}")
            return {}, metadata_df

        # 4. 创建文件名到标签的映射
        label_map = {}

        for h5_file in h5_files:
            filename = cls.extract_filename_from_path(h5_file)

            # 在元数据中查找匹配的记录
            matching_rows = metadata_df[metadata_df['File_Name'] == filename]

            if matching_rows.empty:
                logger.warning(f"在元数据中未找到文件 {filename} 的记录")
                # 默认标签：假设为健康
                label_map[filename] = 0
            else:
                disease_status = matching_rows.iloc[0]['Disease_Status']
                label = cls.normalize_label(disease_status)
                label_map[filename] = label
                logger.debug(f"{filename}: {disease_status} -> {label}")

        # 5. 统计标签分布
        label_counts = pd.Series(label_map.values()).value_counts().to_dict()
        logger.info(f"标签分布: {label_counts}")

        return label_map, metadata_df

    @classmethod
    def create_label_file(
        cls,
        h5_files: List[str],
        output_path: str,
        metadata_file: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        自动创建标签文件

        Parameters:
        -----------
        h5_files : List[str]
            H5文件路径列表
        output_path : str
            输出标签文件路径
        metadata_file : Optional[str]
            手动指定的元数据文件路径（可选）

        Returns:
        --------
        Tuple[str, Dict]
            - 标签文件路径
            - 统计信息字典
        """
        # 提取标签
        label_map, metadata_df = cls.extract_labels_from_h5_files(h5_files, metadata_file)

        if not label_map:
            raise ValueError("无法提取标签信息")

        # 创建标签DataFrame（保持与H5文件顺序一致）
        labels = []
        for h5_file in h5_files:
            filename = cls.extract_filename_from_path(h5_file)
            labels.append(label_map.get(filename, 0))

        label_df = pd.DataFrame({'label': labels})

        # 保存标签文件
        label_df.to_csv(output_path, index=False)
        logger.info(f"标签文件已保存: {output_path}")

        # 统计信息
        stats = {
            'total_files': len(h5_files),
            'label_0_count': sum(1 for l in labels if l == 0),
            'label_1_count': sum(1 for l in labels if l == 1),
            'metadata_found': metadata_df is not None,
            'label_file': output_path
        }

        return output_path, stats
