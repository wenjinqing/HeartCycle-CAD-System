"""
H5文件信号可视化 API
"""
import os
import h5py
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import tempfile

router = APIRouter(prefix="/h5", tags=["H5可视化"])


def read_h5_signals(file_path: str) -> dict:
    """从H5文件读取ECG、ICG、ECHO信号"""
    result = {}

    with h5py.File(file_path, 'r') as f:
        measure = f.get('measure', {}).get('value', {})
        if not measure:
            raise ValueError("H5文件格式不正确，未找到 measure/value 路径")

        available_keys = list(measure.keys())

        # ECG (_030)
        if '_030' in measure:
            try:
                ecg_data = measure['_030']['value']['data']['value'][0, :]
                ecg_time = measure['_030']['value']['time']['value'][0, :]
                # 降采样到最多2000个点
                step = max(1, len(ecg_data) // 2000)
                result['ecg'] = {
                    'time': ecg_time[::step].tolist(),
                    'data': ecg_data[::step].tolist(),
                    'unit': 'mV',
                    'label': 'ECG'
                }
            except Exception as e:
                result['ecg_error'] = str(e)

        # ICG (_031)
        if '_031' in measure:
            try:
                icg_data = measure['_031']['value']['data']['value'][0, :]
                icg_time = measure['_031']['value']['time']['value'][0, :]
                step = max(1, len(icg_data) // 2000)
                dt = float(np.mean(np.diff(icg_time)))
                dz = np.gradient(icg_data, dt)
                result['icg'] = {
                    'time': icg_time[::step].tolist(),
                    'data': icg_data[::step].tolist(),
                    'dz': dz[::step].tolist(),
                    'unit': 'Ω',
                    'label': 'ICG'
                }
            except Exception as e:
                result['icg_error'] = str(e)

        # ECHO (_091)
        if '_091' in measure:
            try:
                echo = measure['_091']['value']['data']['value'][0, :, :].transpose()
                # 压缩图像数据：降采样
                h, w = echo.shape
                max_w = 200
                step_w = max(1, w // max_w)
                echo_small = echo[:, ::step_w]
                # 归一化到0-255
                mn, mx = float(echo_small.min()), float(echo_small.max())
                if mx > mn:
                    echo_norm = ((echo_small - mn) / (mx - mn) * 255).astype(int)
                else:
                    echo_norm = echo_small.astype(int)
                result['echo'] = {
                    'data': echo_norm.tolist(),
                    'width': echo_norm.shape[1],
                    'height': echo_norm.shape[0],
                    'label': 'Echocardiography'
                }
            except Exception as e:
                result['echo_error'] = str(e)

        result['available_keys'] = available_keys

    return result


@router.post("/visualize", summary="上传H5文件并提取信号数据")
async def visualize_h5(file: UploadFile = File(...)):
    """
    上传H5文件，返回ECG、ICG、dZ/dt、ECHO信号数据用于前端可视化
    """
    if not file.filename.endswith('.h5'):
        raise HTTPException(status_code=400, detail="请上传 .h5 格式的文件")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        signals = read_h5_signals(tmp_path)
        return {
            "success": True,
            "filename": file.filename,
            "signals": signals
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析H5文件失败: {str(e)}")
    finally:
        os.unlink(tmp_path)
