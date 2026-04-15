"""
认证依赖项 - FastAPI 依赖注入
"""
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..services.auth_service import AuthService
from ..models.user import User, UserRole, Patient, PatientDoctorBinding
from ..models.auth import TokenPayload
from ..core.exceptions import AuthenticationError, AuthorizationError, InvalidTokenError

# HTTP Bearer 认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    auth_service = AuthService(db)

    try:
        payload = auth_service.decode_token(token)

        # 检查是否是访问令牌
        if payload.type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌类型",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 获取用户
        user = auth_service.get_user_by_id(int(payload.sub))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户已被禁用",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取当前用户（可选，不强制登录）"""
    if not credentials:
        return None

    token = credentials.credentials
    auth_service = AuthService(db)

    try:
        payload = auth_service.decode_token(token)
        if payload.type != "access":
            return None

        user = auth_service.get_user_by_id(int(payload.sub))
        if not user or not user.is_active:
            return None

        return user
    except:
        return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    return current_user


class RoleChecker:
    """角色检查器"""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要以下角色之一: {[r.value for r in self.allowed_roles]}"
            )
        return user


# 预定义的角色检查器
require_admin = RoleChecker([UserRole.ADMIN])
require_doctor = RoleChecker([UserRole.ADMIN, UserRole.DOCTOR])
require_researcher = RoleChecker([UserRole.ADMIN, UserRole.RESEARCHER])
require_doctor_or_researcher = RoleChecker([UserRole.ADMIN, UserRole.DOCTOR, UserRole.RESEARCHER])

# 医护与科研（患者账号不可调用后台管理类接口）
require_staff = RoleChecker([UserRole.ADMIN, UserRole.DOCTOR, UserRole.RESEARCHER])


def doctor_has_patient_binding(db: Session, doctor_user_id: int, patient: Patient) -> bool:
    """医生是否已与该患者建立绑定（多对多关系表）。"""
    if patient is None:
        return False
    row = (
        db.query(PatientDoctorBinding)
        .filter(
            PatientDoctorBinding.patient_id == patient.id,
            PatientDoctorBinding.doctor_id == doctor_user_id,
        )
        .first()
    )
    return row is not None


def assert_user_can_access_patient(current_user: User, patient: Patient, db: Session) -> None:
    """
    患者数据隔离：
    - admin / researcher：可访问（科研与系统管理）
    - doctor：须在 patient_doctor_bindings 中与该患者绑定
    - patient：仅 linked_user_id 与当前用户一致的患者档案
    """
    if patient is None:
        raise HTTPException(status_code=404, detail="患者不存在")
    role = current_user.role
    r = role.value if hasattr(role, "value") else str(role)
    if r in ("admin", "researcher"):
        return
    if r == "doctor":
        if doctor_has_patient_binding(db, current_user.id, patient):
            return
        raise HTTPException(
            status_code=403,
            detail="您未与该患者建立医生绑定，无法查看或操作其病历",
        )
    if r == "patient":
        if patient.linked_user_id is None or patient.linked_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="仅能访问本人关联的患者信息")
        return
    raise HTTPException(status_code=403, detail="权限不足")


def get_client_ip(request: Request) -> str:
    """获取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """获取 User-Agent"""
    return request.headers.get("User-Agent", "unknown")
