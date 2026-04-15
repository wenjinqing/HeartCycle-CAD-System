"""
用户数据库模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..db.base import Base
import enum


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"          # 管理员
    DOCTOR = "doctor"        # 医生
    PATIENT = "patient"      # 患者
    RESEARCHER = "researcher"  # 研究人员


def role_type_id_for(role) -> int:
    """
    系统级「角色类型」编号，与具体用户主键 users.id 独立，便于展示与策略配置。
    admin=1, doctor=2, researcher=3, patient=4
    """
    v = role.value if hasattr(role, "value") else str(role)
    return {"admin": 1, "doctor": 2, "researcher": 3, "patient": 4}.get(v, 0)


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.PATIENT, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    avatar_url = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    department = Column(String(100), nullable=True)  # 科室（医生）
    hospital = Column(String(200), nullable=True)    # 医院（医生）

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # 关系
    patients = relationship("Patient", back_populates="doctor", foreign_keys="Patient.doctor_id")
    patient_bindings = relationship(
        "PatientDoctorBinding",
        back_populates="doctor",
        foreign_keys="PatientDoctorBinding.doctor_id",
    )
    patient_profile = relationship(
        "Patient",
        back_populates="linked_user",
        foreign_keys="Patient.linked_user_id",
        uselist=False,
    )
    predictions = relationship("PredictionRecord", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Patient(Base):
    """患者模型"""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_no = Column(String(50), unique=True, index=True, nullable=False)  # 患者编号
    name = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=True)  # male/female
    age = Column(Integer, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    medical_history = Column(Text, nullable=True)  # 病史（JSON格式）
    allergies = Column(Text, nullable=True)  # 过敏史
    notes = Column(Text, nullable=True)

    # 监测分析用体征（可选，用于从患者进入监测页时预填）
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    resting_heart_rate = Column(Integer, nullable=True)
    occupation = Column(String(100), nullable=True)
    hrv_mean_rr = Column(Float, nullable=True)
    hrv_sdnn = Column(Float, nullable=True)
    hrv_rmssd = Column(Float, nullable=True)
    hrv_pnn50 = Column(Float, nullable=True)
    hrv_lf_hf_ratio = Column(Float, nullable=True)

    waist_cm = Column(Float, nullable=True)
    total_cholesterol = Column(Float, nullable=True)
    ldl_cholesterol = Column(Float, nullable=True)
    hdl_cholesterol = Column(Float, nullable=True)
    triglyceride = Column(Float, nullable=True)
    fasting_glucose = Column(Float, nullable=True)
    hba1c = Column(Float, nullable=True)
    smoke_status = Column(String(20), nullable=True)
    physical_activity = Column(String(20), nullable=True)
    diabetes = Column(Integer, nullable=True)
    hypertension_dx = Column(Integer, nullable=True)
    dyslipidemia = Column(Integer, nullable=True)
    family_history_cad = Column(Integer, nullable=True)
    chest_pain_symptom = Column(Integer, nullable=True)

    # 关联医生
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor = relationship("User", back_populates="patients", foreign_keys=[doctor_id])

    # 患者端账号（注册用户 role=patient）绑定到本档案；仅本人可经 API 访问该患者数据
    linked_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    linked_user = relationship("User", back_populates="patient_profile", foreign_keys=[linked_user_id])

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    predictions = relationship("PredictionRecord", back_populates="patient")
    doctor_bindings = relationship(
        "PatientDoctorBinding",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Patient(id={self.id}, patient_no={self.patient_no}, name={self.name})>"


class PatientDoctorBinding(Base):
    """
    患者与医生多对多绑定：仅已绑定医生可查看该患者病历（管理员/科研除外）。
    保留 patients.doctor_id 作为「主诊/建档医生」展示字段，与绑定表并存。
    """

    __tablename__ = "patient_doctor_bindings"
    __table_args__ = (
        UniqueConstraint("patient_id", "doctor_id", name="uq_patient_doctor_binding"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="doctor_bindings")
    doctor = relationship("User", back_populates="patient_bindings", foreign_keys=[doctor_id])

    def __repr__(self):
        return f"<PatientDoctorBinding(patient_id={self.patient_id}, doctor_id={self.doctor_id})>"


class PredictionRecord(Base):
    """预测记录模型"""
    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True, index=True)

    # 关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    model_id = Column(String(100), nullable=False)

    # 预测结果
    prediction = Column(Integer, nullable=False)  # 0 或 1
    probability = Column(String(50), nullable=False)  # 概率值
    risk_level = Column(String(20), nullable=False)  # low/medium/high

    # 输入特征（JSON格式）
    input_features = Column(Text, nullable=True)

    # SHAP 解释（JSON格式）
    shap_values = Column(Text, nullable=True)

    # 医生建议
    doctor_notes = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="predictions")
    patient = relationship("Patient", back_populates="predictions")

    def __repr__(self):
        return f"<PredictionRecord(id={self.id}, prediction={self.prediction}, risk_level={self.risk_level})>"


class AuditLog(Base):
    """操作审计日志"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # login/logout/predict/train/etc.
    resource = Column(String(100), nullable=True)  # 操作的资源
    resource_id = Column(String(100), nullable=True)  # 资源ID
    details = Column(Text, nullable=True)  # 详细信息（JSON）
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action})>"
