"""
H5文件格式转换API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
import h5py
import numpy as np
from pathlib import Path
import tempfile
import shutil
from app.core.logger import logger
from app.core.settings import settings
from app.core.utils import ensure_dir

router = APIRouter()


class H5ConvertRequest(BaseModel):
    """H5转换请求"""
    input_files: List[str]
    output_dir: Optional[str] = None


class H5FormatCheckResponse(BaseModel):
    """H5格式检查响应"""
    file_path: str
    format_type: str  # 'simple', 'matlab', 'unknown'
    needs_conversion: bool
    details: dict


class H5ConvertResponse(BaseModel):
    """H5转换响应"""
    success: bool
    message: str
    converted_files: List[str]
    failed_files: List[str]
    statistics: dict


def detect_h5_format(file_path: str) -> dict:
    """
    检测H5文件格式类型

    Returns:
    --------
    dict: {
        'format': 'simple' | 'matlab' | 'unknown',
        'needs_conversion': bool,
        'details': {...}
    }
    """
    try:
        with h5py.File(file_path, 'r') as f:
            keys = list(f.keys())

            # 检查是否为简单格式（直接包含ecg数据集）
            if 'ecg' in keys:
                ecg_data = f['ecg']
                return {
                    'format': 'simple',
                    'needs_conversion': False,
                    'details': {
                        'keys': keys,
                        'ecg_shape': ecg_data.shape,
                        'ecg_size': ecg_data.size
                    }
                }

            # 检查是否为MATLAB格式（包含measure组）
            elif 'measure' in keys:
                measure_group = f['measure']
                if 'value' in measure_group:
                    value_group = measure_group['value']
                    beat_keys = [k for k in value_group.keys() if k.startswith('_')]

                    return {
                        'format': 'matlab',
                        'needs_conversion': True,
                        'details': {
                            'keys': keys,
                            'beat_count': len(beat_keys),
                            'structure': 'measure/value/_XXX/value/data/value'
                        }
                    }

            # 未知格式
            return {
                'format': 'unknown',
                'needs_conversion': False,
                'details': {
                    'keys': keys,
                    'message': '无法识别的H5文件格式'
                }
            }

    except Exception as e:
        return {
            'format': 'error',
            'needs_conversion': False,
            'details': {
                'error': str(e)
            }
        }


def convert_matlab_to_simple(input_path: str, output_path: str) -> dict:
    """
    将MATLAB格式转换为简单格式

    Returns:
    --------
    dict: 转换统计信息
    """
    try:
        with h5py.File(input_path, 'r') as f_in:
            # 收集所有心拍周期的数据
            all_data = []
            measure_group = f_in['measure']['value']

            # 遍历所有心拍周期 (_000, _001, _002, ...)
            beat_keys = [k for k in measure_group.keys() if k.startswith('_')]
            beat_keys.sort()

            for beat_key in beat_keys:
                try:
                    beat_data = f_in[f'measure/value/{beat_key}/value/data/value'][:]

                    # 检查数据是否有效
                    if beat_data.size > 0:
                        beat_data = beat_data.flatten()

                        # 跳过全零数据
                        if not np.all(beat_data == 0):
                            all_data.append(beat_data)
                except:
                    continue

            if len(all_data) == 0:
                raise ValueError("没有找到有效数据")

            # 合并所有心拍周期
            ecg_data = np.concatenate(all_data)

            # 保存为简单格式
            with h5py.File(output_path, 'w') as f_out:
                f_out.create_dataset('ecg', data=ecg_data, compression='gzip')

            return {
                'success': True,
                'beat_count': len(all_data),
                'total_points': ecg_data.size,
                'data_range': [float(ecg_data.min()), float(ecg_data.max())]
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/check-format", response_model=H5FormatCheckResponse)
async def check_h5_format(file_path: str):
    """检查H5文件格式"""
    try:
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        result = detect_h5_format(file_path)

        return H5FormatCheckResponse(
            file_path=file_path,
            format_type=result['format'],
            needs_conversion=result['needs_conversion'],
            details=result['details']
        )

    except Exception as e:
        logger.error(f"检查H5格式失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert", response_model=H5ConvertResponse)
async def convert_h5_files(request: H5ConvertRequest):
    """批量转换H5文件格式"""
    try:
        # 确定输出目录
        if request.output_dir:
            output_dir = Path(request.output_dir)
        else:
            output_dir = Path(settings.DATA_ROOT) / "converted_h5"

        ensure_dir(output_dir)

        converted_files = []
        failed_files = []
        statistics = {
            'total': len(request.input_files),
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        for input_file in request.input_files:
            input_path = Path(input_file)

            if not input_path.exists():
                failed_files.append({
                    'file': input_file,
                    'error': '文件不存在'
                })
                statistics['failed'] += 1
                continue

            # 检测格式
            format_info = detect_h5_format(str(input_path))

            # 如果不需要转换，跳过
            if not format_info['needs_conversion']:
                if format_info['format'] == 'simple':
                    statistics['skipped'] += 1
                    converted_files.append({
                        'original': input_file,
                        'converted': input_file,
                        'skipped': True,
                        'reason': '已是标准格式'
                    })
                else:
                    failed_files.append({
                        'file': input_file,
                        'error': f"未知格式: {format_info['format']}"
                    })
                    statistics['failed'] += 1
                continue

            # 转换文件
            output_path = output_dir / input_path.name
            result = convert_matlab_to_simple(str(input_path), str(output_path))

            if result['success']:
                converted_files.append({
                    'original': input_file,
                    'converted': str(output_path),
                    'statistics': {
                        'beat_count': result['beat_count'],
                        'total_points': result['total_points'],
                        'data_range': result['data_range']
                    }
                })
                statistics['success'] += 1
            else:
                failed_files.append({
                    'file': input_file,
                    'error': result['error']
                })
                statistics['failed'] += 1

        return H5ConvertResponse(
            success=statistics['failed'] == 0,
            message=f"转换完成：成功{statistics['success']}个，失败{statistics['failed']}个，跳过{statistics['skipped']}个",
            converted_files=[f['converted'] for f in converted_files if not f.get('skipped')],
            failed_files=[f['file'] for f in failed_files],
            statistics=statistics
        )

    except Exception as e:
        logger.error(f"批量转换H5文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert-single")
async def convert_single_h5(file: UploadFile = File(...)):
    """上传并转换单个H5文件"""
    try:
        # 保存上传的文件到临时目录
        temp_dir = Path(tempfile.mkdtemp())
        input_path = temp_dir / file.filename

        with open(input_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        # 检测格式
        format_info = detect_h5_format(str(input_path))

        if not format_info['needs_conversion']:
            if format_info['format'] == 'simple':
                # 已是标准格式，直接移动到数据目录
                output_dir = Path(settings.UPLOAD_DIR)
                ensure_dir(output_dir)
                output_path = output_dir / file.filename
                shutil.move(str(input_path), str(output_path))

                return {
                    'success': True,
                    'message': '文件已是标准格式，无需转换',
                    'file_path': str(output_path),
                    'format': 'simple'
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件格式: {format_info['format']}"
                )

        # 转换文件
        output_dir = Path(settings.UPLOAD_DIR)
        ensure_dir(output_dir)
        output_path = output_dir / file.filename

        result = convert_matlab_to_simple(str(input_path), str(output_path))

        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

        if result['success']:
            return {
                'success': True,
                'message': '转换成功',
                'file_path': str(output_path),
                'format': 'matlab_converted',
                'statistics': {
                    'beat_count': result['beat_count'],
                    'total_points': result['total_points'],
                    'data_range': result['data_range']
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转换单个H5文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
