"""
患者管理服务
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from ..models.user import Patient, PredictionRecord, User, PatientDoctorBinding, UserRole
from ..models.auth import PatientCreate, PatientUpdate, PatientResponse
from ..core.exceptions import UserNotFoundError

logger = logging.getLogger(__name__)


def patient_response_dict(patient: Patient, db: Optional[Session] = None) -> Dict[str, Any]:
    """ORM Patient -> 前端患者 API 字典（含 JSON 可序列化时间与 doctor_name、bound_doctor_ids）"""
    out = PatientResponse.model_validate(patient).model_dump(mode="json")
    doc = patient.doctor
    out["doctor_name"] = (doc.full_name or doc.username) if doc else None
    if db is not None:
        bids = (
            db.query(PatientDoctorBinding.doctor_id)
            .filter(PatientDoctorBinding.patient_id == patient.id)
            .all()
        )
        out["bound_doctor_ids"] = [b[0] for b in bids]
    else:
        out["bound_doctor_ids"] = []
    return out


def patient_to_report_dict(patient: Optional[Patient]) -> Dict[str, Any]:
    """ORM 患者 -> 报告/统计用扁平字典（与前端监测页、患者档案字段对齐）"""
    if patient is None:
        return {}
    return {
        "patient_no": patient.patient_no,
        "name": patient.name,
        "gender": patient.gender,
        "age": patient.age,
        "phone": patient.phone or "",
        "emergency_contact": patient.emergency_contact or "",
        "emergency_phone": patient.emergency_phone or "",
        "occupation": patient.occupation or "",
        "address": patient.address or "",
        "height_cm": patient.height_cm,
        "weight_kg": patient.weight_kg,
        "waist_cm": patient.waist_cm,
        "blood_pressure_systolic": patient.blood_pressure_systolic,
        "blood_pressure_diastolic": patient.blood_pressure_diastolic,
        "resting_heart_rate": patient.resting_heart_rate,
        "total_cholesterol": patient.total_cholesterol,
        "ldl_cholesterol": patient.ldl_cholesterol,
        "hdl_cholesterol": patient.hdl_cholesterol,
        "triglyceride": patient.triglyceride,
        "fasting_glucose": patient.fasting_glucose,
        "hba1c": patient.hba1c,
        "smoke_status": patient.smoke_status or "",
        "physical_activity": patient.physical_activity or "",
        "diabetes": patient.diabetes,
        "hypertension_dx": patient.hypertension_dx,
        "dyslipidemia": patient.dyslipidemia,
        "family_history_cad": patient.family_history_cad,
        "chest_pain_symptom": patient.chest_pain_symptom,
        "hrv_mean_rr": patient.hrv_mean_rr,
        "hrv_sdnn": patient.hrv_sdnn,
        "hrv_rmssd": patient.hrv_rmssd,
        "hrv_pnn50": patient.hrv_pnn50,
        "hrv_lf_hf_ratio": patient.hrv_lf_hf_ratio,
    }


class PatientService:
    """患者管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def generate_patient_no(self) -> str:
        """生成患者编号"""
        # 格式: P + 年月日 + 4位序号
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"P{today}"

        # 查询今天最后一个患者编号
        last_patient = self.db.query(Patient).filter(
            Patient.patient_no.like(f"{prefix}%")
        ).order_by(Patient.patient_no.desc()).first()

        if last_patient:
            # 提取序号并加1
            last_no = int(last_patient.patient_no[-4:])
            new_no = last_no + 1
        else:
            new_no = 1

        return f"{prefix}{new_no:04d}"

    def create_patient(
        self,
        patient_data: PatientCreate,
        doctor_id: Optional[int] = None
    ) -> Patient:
        """
        创建患者

        Parameters:
        -----------
        patient_data : PatientCreate
            患者数据
        doctor_id : Optional[int]
            关联的医生ID

        Returns:
        --------
        Patient
        """
        # 生成患者编号
        if not patient_data.patient_no:
            patient_no = self.generate_patient_no()
        else:
            patient_no = patient_data.patient_no

        # 创建患者
        db_patient = Patient(
            patient_no=patient_no,
            name=patient_data.name,
            gender=patient_data.gender,
            age=patient_data.age,
            birth_date=patient_data.birth_date,
            phone=patient_data.phone,
            address=patient_data.address,
            emergency_contact=patient_data.emergency_contact,
            emergency_phone=patient_data.emergency_phone,
            medical_history=patient_data.medical_history,
            allergies=patient_data.allergies,
            notes=patient_data.notes,
            height_cm=patient_data.height_cm,
            weight_kg=patient_data.weight_kg,
            blood_pressure_systolic=patient_data.blood_pressure_systolic,
            blood_pressure_diastolic=patient_data.blood_pressure_diastolic,
            resting_heart_rate=patient_data.resting_heart_rate,
            occupation=patient_data.occupation,
            hrv_mean_rr=patient_data.hrv_mean_rr,
            hrv_sdnn=patient_data.hrv_sdnn,
            hrv_rmssd=patient_data.hrv_rmssd,
            hrv_pnn50=patient_data.hrv_pnn50,
            hrv_lf_hf_ratio=patient_data.hrv_lf_hf_ratio,
            waist_cm=patient_data.waist_cm,
            total_cholesterol=patient_data.total_cholesterol,
            ldl_cholesterol=patient_data.ldl_cholesterol,
            hdl_cholesterol=patient_data.hdl_cholesterol,
            triglyceride=patient_data.triglyceride,
            fasting_glucose=patient_data.fasting_glucose,
            hba1c=patient_data.hba1c,
            smoke_status=patient_data.smoke_status,
            physical_activity=patient_data.physical_activity,
            diabetes=patient_data.diabetes,
            hypertension_dx=patient_data.hypertension_dx,
            dyslipidemia=patient_data.dyslipidemia,
            family_history_cad=patient_data.family_history_cad,
            chest_pain_symptom=patient_data.chest_pain_symptom,
            doctor_id=doctor_id
        )

        self.db.add(db_patient)
        self.db.commit()
        self.db.refresh(db_patient)

        if doctor_id is not None:
            self.add_doctor_binding(db_patient.id, doctor_id, commit=True)

        logger.info(f"创建患者: {patient_no}")

        return db_patient

    def get_patient(self, patient_id: int) -> Optional[Patient]:
        """获取患者（预加载主治医生，避免 N+1 且便于返回 doctor_name）"""
        return (
            self.db.query(Patient)
            .options(joinedload(Patient.doctor))
            .filter(Patient.id == patient_id)
            .first()
        )

    def get_patient_by_no(self, patient_no: str) -> Optional[Patient]:
        """根据患者编号获取患者"""
        return self.db.query(Patient).filter(Patient.patient_no == patient_no).first()

    def update_patient(
        self,
        patient_id: int,
        patient_data: PatientUpdate
    ) -> Patient:
        """
        更新患者信息

        Parameters:
        -----------
        patient_id : int
            患者ID
        patient_data : PatientUpdate
            更新数据

        Returns:
        --------
        Patient
        """
        patient = self.get_patient(patient_id)
        if not patient:
            raise UserNotFoundError(f"患者不存在: {patient_id}")

        # 更新字段
        update_data = patient_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(patient, key):
                setattr(patient, key, value)

        self.db.commit()
        self.db.refresh(patient)

        logger.info(f"更新患者: {patient.patient_no}")

        return patient

    def delete_patient(self, patient_id: int) -> bool:
        """
        删除患者

        Parameters:
        -----------
        patient_id : int
            患者ID

        Returns:
        --------
        bool
        """
        patient = self.get_patient(patient_id)
        if not patient:
            raise UserNotFoundError(f"患者不存在: {patient_id}")

        self.db.delete(patient)
        self.db.commit()

        logger.info(f"删除患者: {patient.patient_no}")

        return True

    def list_patients(
        self,
        doctor_id: Optional[int] = None,
        linked_user_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Patient], int]:
        """
        获取患者列表

        Parameters:
        -----------
        doctor_id : Optional[int]
            医生ID（筛选该医生的患者）
        search : Optional[str]
            搜索关键词（姓名、患者编号、手机号）
        skip : int
            跳过数量
        limit : int
            返回数量

        Returns:
        --------
        patients, total
        """
        query = self.db.query(Patient).options(joinedload(Patient.doctor))

        # 患者账号：仅本人绑定档案
        if linked_user_id is not None:
            query = query.filter(Patient.linked_user_id == linked_user_id)
        # 医生：仅显示已与自己建立绑定的患者
        elif doctor_id:
            query = query.join(
                PatientDoctorBinding,
                and_(
                    PatientDoctorBinding.patient_id == Patient.id,
                    PatientDoctorBinding.doctor_id == doctor_id,
                ),
            )

        # 搜索
        if search:
            query = query.filter(
                or_(
                    Patient.name.like(f"%{search}%"),
                    Patient.patient_no.like(f"%{search}%"),
                    Patient.phone.like(f"%{search}%")
                )
            )

        total = query.count()
        patients = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()

        return patients, total

    def get_patient_by_linked_user(self, user_id: int) -> Optional[Patient]:
        """患者端账号绑定的唯一患者档案。"""
        return self.db.query(Patient).filter(Patient.linked_user_id == user_id).first()

    def count_doctor_bindings(self, patient_id: int) -> int:
        return (
            self.db.query(PatientDoctorBinding)
            .filter(PatientDoctorBinding.patient_id == patient_id)
            .count()
        )

    def is_doctor_bound_to_patient(self, patient_id: int, doctor_id: int) -> bool:
        return (
            self.db.query(PatientDoctorBinding)
            .filter(
                PatientDoctorBinding.patient_id == patient_id,
                PatientDoctorBinding.doctor_id == doctor_id,
            )
            .first()
            is not None
        )

    def add_doctor_binding(
        self, patient_id: int, doctor_id: int, commit: bool = True
    ) -> PatientDoctorBinding:
        """为患者绑定一名医生（或管理员）；幂等。"""
        du = self.db.query(User).filter(User.id == doctor_id).first()
        if not du:
            raise UserNotFoundError(f"用户不存在: {doctor_id}")
        if du.role not in (UserRole.DOCTOR, UserRole.ADMIN):
            raise ValueError("仅可将医生或管理员类型的账号绑定到患者病历团队")
        existing = (
            self.db.query(PatientDoctorBinding)
            .filter(
                PatientDoctorBinding.patient_id == patient_id,
                PatientDoctorBinding.doctor_id == doctor_id,
            )
            .first()
        )
        if existing:
            return existing
        row = PatientDoctorBinding(patient_id=patient_id, doctor_id=doctor_id)
        self.db.add(row)
        if commit:
            self.db.commit()
            self.db.refresh(row)
        else:
            self.db.flush()
        return row

    def remove_doctor_binding(self, patient_id: int, doctor_id: int) -> bool:
        row = (
            self.db.query(PatientDoctorBinding)
            .filter(
                PatientDoctorBinding.patient_id == patient_id,
                PatientDoctorBinding.doctor_id == doctor_id,
            )
            .first()
        )
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def list_bound_doctors(self, patient_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(PatientDoctorBinding, User)
            .join(User, User.id == PatientDoctorBinding.doctor_id)
            .filter(PatientDoctorBinding.patient_id == patient_id)
            .all()
        )
        out = []
        for b, u in rows:
            out.append(
                {
                    "doctor_id": u.id,
                    "username": u.username,
                    "full_name": u.full_name,
                    "role": u.role.value if hasattr(u.role, "value") else str(u.role),
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
            )
        return out

    def get_patient_predictions(
        self,
        patient_id: int,
        skip: int = 0,
        limit: int = 20,
        actor_user_id: Optional[int] = None,
    ) -> Tuple[List[PredictionRecord], int]:
        """
        获取患者的预测记录

        Parameters:
        -----------
        patient_id : int
            患者ID
        skip : int
            跳过数量
        limit : int
            返回数量
        actor_user_id : Optional[int]
            若指定，仅返回该登录用户产生的记录（患者端仅看本人 user_id 与本人档案一致的数据）

        Returns:
        --------
        predictions, total
        """
        query = self.db.query(PredictionRecord).filter(
            PredictionRecord.patient_id == patient_id
        )
        if actor_user_id is not None:
            query = query.filter(PredictionRecord.user_id == actor_user_id)

        total = query.count()
        predictions = query.order_by(
            PredictionRecord.created_at.desc()
        ).offset(skip).limit(limit).all()

        return predictions, total

    def create_prediction_record(
        self,
        user_id: Optional[int],
        patient_id: Optional[int],
        model_id: str,
        prediction: int,
        probability: str,
        risk_level: str,
        input_features: Optional[str] = None,
        shap_values: Optional[str] = None
    ) -> PredictionRecord:
        """
        创建预测记录

        Parameters:
        -----------
        user_id : Optional[int]
            用户ID
        patient_id : Optional[int]
            患者ID
        model_id : str
            模型ID
        prediction : int
            预测结果
        probability : str
            预测概率
        risk_level : str
            风险等级
        input_features : Optional[str]
            输入特征（JSON）
        shap_values : Optional[str]
            SHAP值（JSON）

        Returns:
        --------
        PredictionRecord
        """
        record = PredictionRecord(
            user_id=user_id,
            patient_id=patient_id,
            model_id=model_id,
            prediction=prediction,
            probability=probability,
            risk_level=risk_level,
            input_features=input_features,
            shap_values=shap_values
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(f"创建预测记录: patient_id={patient_id}, prediction={prediction}")

        return record

    def get_prediction_record(self, prediction_id: int) -> Optional[PredictionRecord]:
        return (
            self.db.query(PredictionRecord)
            .filter(PredictionRecord.id == prediction_id)
            .first()
        )

    def update_prediction_notes(
        self,
        prediction_id: int,
        doctor_notes: str
    ) -> PredictionRecord:
        """
        更新预测记录的医生备注

        Parameters:
        -----------
        prediction_id : int
            预测记录ID
        doctor_notes : str
            医生备注

        Returns:
        --------
        PredictionRecord
        """
        record = self.get_prediction_record(prediction_id)

        if not record:
            raise UserNotFoundError(f"预测记录不存在: {prediction_id}")

        record.doctor_notes = doctor_notes
        self.db.commit()
        self.db.refresh(record)

        return record

    def get_patient_statistics(self, patient_id: int) -> Dict:
        """
        获取患者统计信息

        Parameters:
        -----------
        patient_id : int
            患者ID

        Returns:
        --------
        统计信息
        """
        patient = self.get_patient(patient_id)
        if not patient:
            raise UserNotFoundError(f"患者不存在: {patient_id}")

        # 预测记录统计
        predictions = self.db.query(PredictionRecord).filter(
            PredictionRecord.patient_id == patient_id
        ).all()

        total_predictions = len(predictions)
        high_risk_count = sum(1 for p in predictions if p.risk_level == 'high')
        medium_risk_count = sum(1 for p in predictions if p.risk_level == 'medium')
        low_risk_count = sum(1 for p in predictions if p.risk_level == 'low')

        # 最近一次预测
        latest_prediction = None
        if predictions:
            latest = max(predictions, key=lambda p: p.created_at)
            latest_prediction = {
                'id': latest.id,
                'prediction': latest.prediction,
                'probability': latest.probability,
                'risk_level': latest.risk_level,
                'created_at': latest.created_at.isoformat()
            }

        # 风险趋势（最近10次）
        recent_predictions = sorted(
            predictions,
            key=lambda p: p.created_at,
            reverse=True
        )[:10]

        risk_trend = [
            {
                'date': p.created_at.strftime('%Y-%m-%d'),
                'risk_level': p.risk_level,
                'probability': p.probability
            }
            for p in reversed(recent_predictions)
        ]

        return {
            'patient_info': patient_to_report_dict(patient),
            'prediction_statistics': {
                'total_predictions': total_predictions,
                'high_risk_count': high_risk_count,
                'medium_risk_count': medium_risk_count,
                'low_risk_count': low_risk_count
            },
            'latest_prediction': latest_prediction,
            'risk_trend': risk_trend
        }

    def get_follow_up_patients(
        self,
        doctor_id: int,
        days: int = 30
    ) -> List[Dict]:
        """
        获取需要随访的患者

        Parameters:
        -----------
        doctor_id : int
            医生ID
        days : int
            距离上次预测的天数

        Returns:
        --------
        需要随访的患者列表
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        bound_patient_ids = [
            r[0]
            for r in self.db.query(PatientDoctorBinding.patient_id)
            .filter(PatientDoctorBinding.doctor_id == doctor_id)
            .all()
        ]
        if not bound_patient_ids:
            return []
        patients = self.db.query(Patient).filter(Patient.id.in_(bound_patient_ids)).all()

        follow_up_list = []

        for patient in patients:
            # 获取最近一次预测
            latest_prediction = self.db.query(PredictionRecord).filter(
                PredictionRecord.patient_id == patient.id
            ).order_by(PredictionRecord.created_at.desc()).first()

            if latest_prediction:
                # 如果最近一次预测超过指定天数，或者是高风险
                if (latest_prediction.created_at < cutoff_date or
                    latest_prediction.risk_level == 'high'):

                    days_since_last = (datetime.now() - latest_prediction.created_at).days

                    follow_up_list.append({
                        'patient_id': patient.id,
                        'patient_no': patient.patient_no,
                        'name': patient.name,
                        'phone': patient.phone,
                        'last_prediction_date': latest_prediction.created_at.strftime('%Y-%m-%d'),
                        'days_since_last': days_since_last,
                        'last_risk_level': latest_prediction.risk_level,
                        'reason': 'high_risk' if latest_prediction.risk_level == 'high' else 'overdue'
                    })

        # 按天数排序
        follow_up_list.sort(key=lambda x: x['days_since_last'], reverse=True)

        return follow_up_list
