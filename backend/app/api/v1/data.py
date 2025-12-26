"""
数据管理API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import os
from app.core.config import settings
from app.core.logger import logger
from app.models.response import FileUploadResponse, FileListResponse, BaseResponse
from app.core.utils import validate_file_path

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件（支持HDF5和CSV格式）
    
    Parameters:
    -----------
    file : UploadFile
        上传的文件
        
    Returns:
    --------
    FileUploadResponse : 文件上传结果
    """
    try:
        # 检查文件类型（支持.h5和.csv文件）
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.h5', '.csv']:
            raise HTTPException(status_code=400, detail="只支持.h5和.csv文件")
        
        # 保存文件
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"文件上传成功: {file.filename}, 大小: {len(content)} bytes")
        
        return FileUploadResponse(
            filename=file.filename,
            file_path=file_path,
            size=len(content),
            message="文件上传成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.get("/files", response_model=FileListResponse)
async def list_files():
    """
    获取文件列表
    
    Returns:
    --------
    FileListResponse : 文件列表
    """
    try:
        files = []
        if os.path.exists(settings.UPLOAD_DIR):
            for filename in os.listdir(settings.UPLOAD_DIR):
                if filename.endswith(('.h5', '.csv')):
                    file_path = os.path.join(settings.UPLOAD_DIR, filename)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        files.append({
                            "filename": filename,
                            "size": file_size,
                            "path": file_path
                        })
        
        return FileListResponse(
            files=files,
            count=len(files),
            message="获取文件列表成功"
        )
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}")
async def get_file_info(filename: str):
    """
    获取文件信息
    
    Parameters:
    -----------
    filename : str
        文件名
        
    Returns:
    --------
    dict : 文件详细信息
    """
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_size = os.path.getsize(file_path)
    return {
        "filename": filename,
        "path": file_path,
        "size": file_size
    }

