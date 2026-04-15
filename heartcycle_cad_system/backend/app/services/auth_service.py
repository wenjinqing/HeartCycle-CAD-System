"""
认证服务 - JWT Token 管理
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.settings import settings
from ..models.user import User, UserRole, AuditLog, Patient, role_type_id_for
from ..models.auth import TokenPayload, UserCreate, UserResponse
from ..core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidTokenError
)

# 密码加密上下文 - 使用pbkdf2_sha256（稳定且无依赖问题）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT 配置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8小时（原来是30分钟）
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30天（原来是7天）


class AuthService:
    """认证服务"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 密码处理 ====================

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)

    # ==================== Token 处理 ====================

    @staticmethod
    def create_access_token(
        user_id: int,
        username: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        user_id: int,
        username: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> TokenPayload:
        """解码令牌"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            return TokenPayload(
                sub=payload.get("sub"),
                username=payload.get("username"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(payload.get("exp")),
                iat=datetime.fromtimestamp(payload.get("iat")),
                type=payload.get("type", "access")
            )
        except JWTError as e:
            raise InvalidTokenError(f"无效的令牌: {str(e)}")

    def create_tokens(self, user: User, remember_me: bool = False) -> Tuple[str, str, int]:
        """创建访问令牌和刷新令牌"""
        # 根据 remember_me 设置过期时间
        if remember_me:
            access_expires = timedelta(days=1)
            refresh_expires = timedelta(days=30)
        else:
            access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        access_token = self.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role.value,
            expires_delta=access_expires
        )

        refresh_token = self.create_refresh_token(
            user_id=user.id,
            username=user.username,
            role=user.role.value,
            expires_delta=refresh_expires
        )

        expires_in = int(access_expires.total_seconds())

        return access_token, refresh_token, expires_in

    # ==================== 用户管理 ====================

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()

    def user_payload_for_client(self, user: User) -> dict:
        """返回给前端的用户对象：含 users.id、角色类型编号、患者账号关联的 patients.id。"""
        data = UserResponse.model_validate(user).model_dump(mode="json")
        data["role_type_id"] = role_type_id_for(user.role)
        p = self.db.query(Patient).filter(Patient.linked_user_id == user.id).first()
        data["linked_patient_id"] = p.id if p else None
        return data

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        """根据用户名或邮箱获取用户"""
        return self.db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

    def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        if self.get_user_by_username(user_data.username):
            raise UserAlreadyExistsError(f"用户名 '{user_data.username}' 已存在")

        # 检查邮箱是否已存在
        if self.get_user_by_email(user_data.email):
            raise UserAlreadyExistsError(f"邮箱 '{user_data.email}' 已被注册")

        # 创建用户
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            phone=user_data.phone,
            role=UserRole(user_data.role.value),
            department=user_data.department,
            hospital=user_data.hospital,
            is_active=True,
            is_verified=False
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        if db_user.role == UserRole.PATIENT:
            self.ensure_patient_self_profile(db_user)

        return db_user

    def ensure_patient_self_profile(self, user: User) -> None:
        """为 role=patient 的用户自动创建并绑定一条患者档案（幂等）。"""
        if user.role != UserRole.PATIENT:
            return
        exists = self.db.query(Patient).filter(Patient.linked_user_id == user.id).first()
        if exists:
            return
        from ..services.patient_service import PatientService

        ps = PatientService(self.db)
        patient_no = ps.generate_patient_no()
        row = Patient(
            patient_no=patient_no,
            name=user.full_name or user.username,
            phone=user.phone,
            linked_user_id=user.id,
            doctor_id=None,
        )
        self.db.add(row)
        self.db.commit()

    def authenticate_user(self, username: str, password: str) -> User:
        """验证用户"""
        user = self.get_user_by_username_or_email(username)

        if not user:
            raise AuthenticationError("用户名或密码错误")

        if not self.verify_password(password, user.hashed_password):
            raise AuthenticationError("用户名或密码错误")

        if not user.is_active:
            raise AuthenticationError("用户已被禁用")

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        self.db.commit()

        return user

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError("用户不存在")

        if not self.verify_password(old_password, user.hashed_password):
            raise AuthenticationError("原密码错误")

        user.hashed_password = self.get_password_hash(new_password)
        self.db.commit()

        return True

    def update_user(self, user_id: int, **kwargs) -> User:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError("用户不存在")

        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)

        return user

    def deactivate_user(self, user_id: int) -> bool:
        """禁用用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError("用户不存在")

        user.is_active = False
        self.db.commit()

        return True

    def activate_user(self, user_id: int) -> bool:
        """启用用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError("用户不存在")

        user.is_active = True
        self.db.commit()

        return True

    def reset_user_password(self, user_id: int, new_password: str) -> str:
        """重置用户密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError("用户不存在")

        user.hashed_password = self.get_password_hash(new_password)
        self.db.commit()

        return new_password

    def get_all_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None
    ) -> Tuple[list, int]:
        """获取所有用户"""
        query = self.db.query(User)

        if role:
            query = query.filter(User.role == role)

        total = query.count()
        users = query.offset(skip).limit(limit).all()

        return users, total

    # ==================== 审计日志 ====================

    def log_action(
        self,
        user_id: Optional[int],
        action: str,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录操作日志"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(log)
        self.db.commit()

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[list, int]:
        """获取审计日志"""
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)

        total = query.count()
        logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

        return logs, total
