"""
患者管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from ...db.base import get_db
from ...services.patient_service import PatientService, patient_response_dict
from ...models.auth import PatientCreate, PatientUpdate
from ...models.response import APIResponse
from ..deps import get_current_user, require_doctor, assert_user_can_access_patient
from ...models.user import User, UserRole, Patient

router = APIRouter(prefix="/patients", tags=["患者管理"])


class BindDoctorBody(BaseModel):
    doctor_id: int = Field(..., description="要绑定的用户 ID（须为医生或管理员）")


@router.post("", response_model=APIResponse, summary="创建患者")
async def create_patient(
    patient_data: PatientCreate,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """
    创建患者（需要医生权限）

    自动生成患者编号（格式：P + 年月日 + 4位序号）
    """
    service = PatientService(db)

    try:
        # 医生创建患者时，自动关联到该医生
        patient = service.create_patient(
            patient_data,
            doctor_id=current_user.id if current_user.role == 'doctor' else None
        )

        return APIResponse(
            success=True,
            message="患者创建成功",
            data=patient_response_dict(patient, db)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建患者失败: {str(e)}"
        )


@router.get("", response_model=APIResponse, summary="获取患者列表")
async def list_patients(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取患者列表

    - 患者：仅返回与本人账号绑定的档案（linked_user_id）
    - 医生：仅已与自己建立绑定的患者
    - 管理员 / 研究员：全部患者
    - 支持搜索（姓名、患者编号、手机号）
    """
    service = PatientService(db)

    try:
        doctor_id = None
        linked_user_id = None
        if current_user.role == UserRole.DOCTOR:
            doctor_id = current_user.id
        elif current_user.role == UserRole.PATIENT:
            linked_user_id = current_user.id

        patients, total = service.list_patients(
            doctor_id=doctor_id,
            linked_user_id=linked_user_id,
            search=search,
            skip=skip,
            limit=limit
        )

        return APIResponse(
            success=True,
            message=f"找到 {total} 个患者",
            data={
                'total': total,
                'items': [patient_response_dict(p, db) for p in patients],
                'page': skip // limit + 1,
                'page_size': limit
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取患者列表失败: {str(e)}"
        )


@router.get("/me/predictions", response_model=APIResponse, summary="患者本人预测历史（仅当前登录用户产生）")
async def get_my_predictions_as_patient(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    仅 **患者** 账号可调：返回与本人 `users.id` 一致且写入本人关联档案 `patients.id` 的预测记录。
    医护/科研请使用「指定患者」的预测列表接口。
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="此接口仅供患者账号查询本人预测历史")

    service = PatientService(db)
    patient = service.get_patient_by_linked_user(current_user.id)
    if not patient:
        return APIResponse(
            success=True,
            message="暂无关联患者档案",
            data={"total": 0, "items": [], "page": 1, "page_size": limit, "viewer_user_id": current_user.id},
        )

    predictions, total = service.get_patient_predictions(
        patient.id,
        skip=skip,
        limit=limit,
        actor_user_id=current_user.id,
    )

    return APIResponse(
        success=True,
        message=f"找到 {total} 条预测记录",
        data={
            "total": total,
            "viewer_user_id": current_user.id,
            "linked_patient_id": patient.id,
            "items": [
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "patient_id": p.patient_id,
                    "model_id": p.model_id,
                    "prediction": p.prediction,
                    "probability": p.probability,
                    "risk_level": p.risk_level,
                    "doctor_notes": p.doctor_notes,
                    "input_features": p.input_features,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in predictions
            ],
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "page_size": limit,
        },
    )


@router.get("/follow-up/list", response_model=APIResponse, summary="获取需要随访的患者")
async def get_follow_up_patients(
    days: int = 30,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    """
    获取需要随访的患者列表（仅统计已与当前医生绑定的患者）

    条件:
    - 距离上次预测超过指定天数
    - 或最近一次预测为高风险

    参数:
    - days: 距离上次预测的天数阈值（默认30天）
    """
    service = PatientService(db)

    try:
        follow_up_list = service.get_follow_up_patients(
            doctor_id=current_user.id,
            days=days,
        )

        return APIResponse(
            success=True,
            message=f"找到 {len(follow_up_list)} 个需要随访的患者",
            data=follow_up_list,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取随访列表失败: {str(e)}",
        )


@router.get(
    "/{patient_id}/bindings/doctors",
    response_model=APIResponse,
    summary="列出已与该患者绑定的医生",
)
async def list_patient_bound_doctors(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    patient = service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    assert_user_can_access_patient(current_user, patient, db)
    items = service.list_bound_doctors(patient_id)
    return APIResponse(success=True, message="获取成功", data={"items": items})


def _can_add_doctor_binding(
    current_user: User, patient: Patient, target_doctor_id: int, service: PatientService
) -> bool:
    r = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if r in ("admin", "researcher"):
        return True
    if r != "doctor":
        return False
    if service.is_doctor_bound_to_patient(patient.id, current_user.id):
        return True
    if target_doctor_id != current_user.id:
        return False
    return patient.doctor_id in (None, current_user.id) and service.count_doctor_bindings(patient.id) == 0


def _can_remove_doctor_binding(current_user: User, target_doctor_id: int) -> bool:
    r = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if r in ("admin", "researcher"):
        return True
    if r == "doctor" and target_doctor_id == current_user.id:
        return True
    return False


@router.post(
    "/{patient_id}/bindings/doctors",
    response_model=APIResponse,
    summary="为患者绑定医生",
)
async def bind_doctor_to_patient(
    patient_id: int,
    body: BindDoctorBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    建立患者-医生绑定。管理员/科研人员可直接绑定任意医生；医生在已与该患者绑定时可为团队增加其他医生；
    尚未有任何绑定时，建档医生（patients.doctor_id 为本人）可将本人加入为第一条绑定。
    """
    service = PatientService(db)
    patient = service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    if not _can_add_doctor_binding(current_user, patient, body.doctor_id, service):
        raise HTTPException(status_code=403, detail="无权为该患者添加此医生绑定")

    try:
        service.add_doctor_binding(patient_id, body.doctor_id, commit=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return APIResponse(
        success=True,
        message="绑定成功",
        data={"patient_id": patient_id, "doctor_id": body.doctor_id},
    )


@router.delete(
    "/{patient_id}/bindings/doctors/{doctor_id}",
    response_model=APIResponse,
    summary="解除患者与医生的绑定",
)
async def unbind_doctor_from_patient(
    patient_id: int,
    doctor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    patient = service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    assert_user_can_access_patient(current_user, patient, db)

    if not _can_remove_doctor_binding(current_user, doctor_id):
        raise HTTPException(status_code=403, detail="无权解除该医生绑定")

    ok = service.remove_doctor_binding(patient_id, doctor_id)
    if not ok:
        raise HTTPException(status_code=404, detail="该绑定不存在")
    return APIResponse(success=True, message="已解除绑定", data={})


@router.get("/{patient_id}", response_model=APIResponse, summary="获取患者详情")
async def get_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取患者详细信息"""
    service = PatientService(db)

    try:
        patient = service.get_patient(patient_id)

        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在")

        assert_user_can_access_patient(current_user, patient, db)

        return APIResponse(
            success=True,
            message="获取成功",
            data=patient_response_dict(patient, db)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取患者失败: {str(e)}"
        )


@router.put("/{patient_id}", response_model=APIResponse, summary="更新患者信息")
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """更新患者信息（需要医生权限）"""
    service = PatientService(db)

    try:
        patient = service.get_patient(patient_id)

        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在")

        assert_user_can_access_patient(current_user, patient, db)

        updated_patient = service.update_patient(patient_id, patient_data)

        return APIResponse(
            success=True,
            message="更新成功",
            data=patient_response_dict(updated_patient, db)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新患者失败: {str(e)}"
        )


@router.delete("/{patient_id}", response_model=APIResponse, summary="删除患者")
async def delete_patient(
    patient_id: int,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """删除患者（需要医生权限）"""
    service = PatientService(db)

    try:
        patient = service.get_patient(patient_id)

        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在")

        assert_user_can_access_patient(current_user, patient, db)

        service.delete_patient(patient_id)

        return APIResponse(
            success=True,
            message="患者已删除"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除患者失败: {str(e)}"
        )


@router.get("/{patient_id}/predictions", response_model=APIResponse, summary="获取患者预测记录")
async def get_patient_predictions(
    patient_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取患者的所有预测记录"""
    service = PatientService(db)

    try:
        patient = service.get_patient(patient_id)

        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在")

        assert_user_can_access_patient(current_user, patient, db)

        actor_user_id = current_user.id if current_user.role == UserRole.PATIENT else None
        predictions, total = service.get_patient_predictions(
            patient_id,
            skip=skip,
            limit=limit,
            actor_user_id=actor_user_id,
        )

        return APIResponse(
            success=True,
            message=f"找到 {total} 条预测记录",
            data={
                'total': total,
                'items': [
                    {
                        'id': p.id,
                        'user_id': p.user_id,
                        'patient_id': p.patient_id,
                        'model_id': p.model_id,
                        'prediction': p.prediction,
                        'probability': p.probability,
                        'risk_level': p.risk_level,
                        'doctor_notes': p.doctor_notes,
                        'input_features': p.input_features,
                        'created_at': p.created_at.isoformat() if p.created_at else None
                    }
                    for p in predictions
                ],
                'page': skip // limit + 1,
                'page_size': limit
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取预测记录失败: {str(e)}"
        )


@router.get("/{patient_id}/statistics", response_model=APIResponse, summary="获取患者统计信息")
async def get_patient_statistics(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取患者统计信息

    包括:
    - 预测次数统计
    - 风险等级分布
    - 最近一次预测
    - 风险趋势
    """
    service = PatientService(db)

    try:
        patient = service.get_patient(patient_id)

        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在")

        assert_user_can_access_patient(current_user, patient, db)

        statistics = service.get_patient_statistics(patient_id)

        return APIResponse(
            success=True,
            message="获取成功",
            data=statistics
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.put("/predictions/{prediction_id}/notes", response_model=APIResponse, summary="更新预测记录备注")
async def update_prediction_notes(
    prediction_id: int,
    doctor_notes: str,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """
    更新预测记录的医生备注

    医生可以为预测记录添加诊断意见和建议
    """
    service = PatientService(db)

    try:
        record = service.get_prediction_record(prediction_id)
        if not record:
            raise HTTPException(status_code=404, detail="预测记录不存在")
        if record.patient_id is not None:
            patient = service.get_patient(record.patient_id)
            if patient:
                assert_user_can_access_patient(current_user, patient, db)

        record = service.update_prediction_notes(prediction_id, doctor_notes)

        return APIResponse(
            success=True,
            message="备注已更新",
            data={
                'id': record.id,
                'doctor_notes': record.doctor_notes
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新备注失败: {str(e)}"
        )
