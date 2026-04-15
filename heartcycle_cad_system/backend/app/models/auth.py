"""
认证相关的 Pydantic 模型
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"
    RESEARCHER = "researcher"


# ==================== 用户相关 ====================

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")


class UserCreate(UserBase):
    """用户注册模型"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    role: UserRole = Field(default=UserRole.PATIENT, description="角色")
    department: Optional[str] = Field(None, description="科室")
    hospital: Optional[str] = Field(None, description="医院")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('两次输入的密码不一致')
        return v

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v


class UserUpdate(BaseModel):
    """用户更新模型"""
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None
    department: Optional[str] = None
    hospital: Optional[str] = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    department: Optional[str] = None
    hospital: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """数据库中的用户模型"""
    hashed_password: str


# ==================== 认证相关 ====================

class Token(BaseModel):
    """Token 响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="过期时间（秒）")


class TokenPayload(BaseModel):
    """Token 载荷"""
    sub: str  # 用户ID
    username: str
    role: str
    exp: datetime
    iat: datetime
    type: str = "access"  # access 或 refresh


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(default=False, description="记住我")


class PasswordChange(BaseModel):
    """修改密码"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v


class PasswordReset(BaseModel):
    """重置密码"""
    email: EmailStr = Field(..., description="邮箱")


class PasswordResetConfirm(BaseModel):
    """确认重置密码"""
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=6, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")


# ==================== 患者相关 ====================

class PatientBase(BaseModel):
    """患者基础模型"""
    name: str = Field(..., max_length=100, description="姓名")
    gender: Optional[str] = Field(None, description="性别")
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")


class PatientCreate(PatientBase):
    """创建患者"""
    patient_no: Optional[str] = Field(None, description="患者编号（自动生成）")
    birth_date: Optional[datetime] = None

    @field_validator("birth_date", mode="before")
    @classmethod
    def birth_date_empty_as_none(cls, v):
        """前端常以空字符串表示未填；Pydantic 无法将 '' 解析为 datetime。"""
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    notes: Optional[str] = None
    height_cm: Optional[float] = Field(None, ge=0, le=300, description="身高 cm")
    weight_kg: Optional[float] = Field(None, ge=0, le=500, description="体重 kg")
    blood_pressure_systolic: Optional[int] = Field(None, ge=0, le=300, description="收缩压 mmHg")
    blood_pressure_diastolic: Optional[int] = Field(None, ge=0, le=200, description="舒张压 mmHg")
    resting_heart_rate: Optional[int] = Field(None, ge=0, le=300, description="静息心率 次/分")
    occupation: Optional[str] = Field(None, max_length=100, description="职业")
    hrv_mean_rr: Optional[float] = Field(None, description="平均RR间期 ms，对应监测页")
    hrv_sdnn: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    hrv_pnn50: Optional[float] = None
    hrv_lf_hf_ratio: Optional[float] = None
    waist_cm: Optional[float] = Field(None, ge=0, le=300, description="腰围 cm")
    total_cholesterol: Optional[float] = Field(None, ge=0, description="总胆固醇 mmol/L")
    ldl_cholesterol: Optional[float] = Field(None, ge=0, description="LDL-C mmol/L")
    hdl_cholesterol: Optional[float] = Field(None, ge=0, description="HDL-C mmol/L")
    triglyceride: Optional[float] = Field(None, ge=0, description="甘油三酯 mmol/L")
    fasting_glucose: Optional[float] = Field(None, ge=0, description="空腹血糖 mmol/L")
    hba1c: Optional[float] = Field(None, ge=0, description="糖化血红蛋白 %")
    smoke_status: Optional[str] = Field(None, max_length=20, description="吸烟: never/former/current")
    physical_activity: Optional[str] = Field(None, max_length=20, description="体力活动强度")
    diabetes: Optional[int] = Field(None, ge=0, le=1)
    hypertension_dx: Optional[int] = Field(None, ge=0, le=1, description="高血压诊断")
    dyslipidemia: Optional[int] = Field(None, ge=0, le=1)
    family_history_cad: Optional[int] = Field(None, ge=0, le=1, description="冠心病家族史")
    chest_pain_symptom: Optional[int] = Field(None, ge=0, le=1, description="胸痛/心绞痛症状")


class PatientUpdate(BaseModel):
    """更新患者"""
    name: Optional[str] = Field(None, max_length=100)
    gender: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    birth_date: Optional[datetime] = None

    @field_validator("birth_date", mode="before")
    @classmethod
    def birth_date_empty_as_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    notes: Optional[str] = None
    height_cm: Optional[float] = Field(None, ge=0, le=300)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    blood_pressure_systolic: Optional[int] = Field(None, ge=0, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=0, le=200)
    resting_heart_rate: Optional[int] = Field(None, ge=0, le=300)
    occupation: Optional[str] = Field(None, max_length=100)
    hrv_mean_rr: Optional[float] = None
    hrv_sdnn: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    hrv_pnn50: Optional[float] = None
    hrv_lf_hf_ratio: Optional[float] = None
    waist_cm: Optional[float] = Field(None, ge=0, le=300)
    total_cholesterol: Optional[float] = None
    ldl_cholesterol: Optional[float] = None
    hdl_cholesterol: Optional[float] = None
    triglyceride: Optional[float] = None
    fasting_glucose: Optional[float] = None
    hba1c: Optional[float] = None
    smoke_status: Optional[str] = Field(None, max_length=20)
    physical_activity: Optional[str] = Field(None, max_length=20)
    diabetes: Optional[int] = Field(None, ge=0, le=1)
    hypertension_dx: Optional[int] = Field(None, ge=0, le=1)
    dyslipidemia: Optional[int] = Field(None, ge=0, le=1)
    family_history_cad: Optional[int] = Field(None, ge=0, le=1)
    chest_pain_symptom: Optional[int] = Field(None, ge=0, le=1)


class PatientResponse(PatientBase):
    """患者响应"""
    id: int
    patient_no: str
    birth_date: Optional[datetime] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    notes: Optional[str] = None
    doctor_id: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    occupation: Optional[str] = None
    hrv_mean_rr: Optional[float] = None
    hrv_sdnn: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    hrv_pnn50: Optional[float] = None
    hrv_lf_hf_ratio: Optional[float] = None
    waist_cm: Optional[float] = None
    total_cholesterol: Optional[float] = None
    ldl_cholesterol: Optional[float] = None
    hdl_cholesterol: Optional[float] = None
    triglyceride: Optional[float] = None
    fasting_glucose: Optional[float] = None
    hba1c: Optional[float] = None
    smoke_status: Optional[str] = None
    physical_activity: Optional[str] = None
    diabetes: Optional[int] = None
    hypertension_dx: Optional[int] = None
    dyslipidemia: Optional[int] = None
    family_history_cad: Optional[int] = None
    chest_pain_symptom: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PatientList(BaseModel):
    """患者列表响应"""
    total: int
    items: List[PatientResponse]
    page: int
    page_size: int


# ==================== 预测记录相关 ====================

class PredictionRecordCreate(BaseModel):
    """创建预测记录"""
    patient_id: Optional[int] = None
    model_id: str
    prediction: int
    probability: str
    risk_level: str
    input_features: Optional[str] = None
    shap_values: Optional[str] = None


class PredictionRecordResponse(BaseModel):
    """预测记录响应"""
    id: int
    user_id: Optional[int] = None
    patient_id: Optional[int] = None
    model_id: str
    prediction: int
    probability: str
    risk_level: str
    doctor_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PredictionRecordList(BaseModel):
    """预测记录列表"""
    total: int
    items: List[PredictionRecordResponse]
    page: int
    page_size: int
