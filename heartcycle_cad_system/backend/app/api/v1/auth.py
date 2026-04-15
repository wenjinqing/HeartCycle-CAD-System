"""
认证 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..deps import (
    get_current_user,
    get_current_active_user,
    get_client_ip,
    get_user_agent,
    require_admin
)
from ...db.base import get_db
from ...services.auth_service import AuthService
from ...models.auth import (
    UserCreate,
    UserUpdate,
    Token,
    LoginRequest,
    PasswordChange,
    PasswordReset
)
from ...models.user import User, UserRole
from ...models.response import APIResponse
from ...core.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserNotFoundError
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=APIResponse, summary="用户注册")
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户注册

    - **username**: 用户名（3-50字符）
    - **email**: 邮箱
    - **password**: 密码（至少6位）
    - **role**: 角色（patient/doctor/researcher）
    """
    auth_service = AuthService(db)

    try:
        user = auth_service.create_user(user_data)

        # 记录审计日志
        auth_service.log_action(
            user_id=user.id,
            action="register",
            resource="user",
            resource_id=str(user.id),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return APIResponse(
            success=True,
            message="注册成功",
            data=auth_service.user_payload_for_client(user)
        )

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=APIResponse, summary="用户登录")
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登录

    - **username**: 用户名或邮箱
    - **password**: 密码
    - **remember_me**: 记住我（延长token有效期）
    """
    auth_service = AuthService(db)

    try:
        user = auth_service.authenticate_user(
            login_data.username,
            login_data.password
        )

        auth_service.ensure_patient_self_profile(user)

        access_token, refresh_token, expires_in = auth_service.create_tokens(
            user,
            remember_me=login_data.remember_me
        )

        # 记录审计日志
        auth_service.log_action(
            user_id=user.id,
            action="login",
            resource="user",
            resource_id=str(user.id),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return APIResponse(
            success=True,
            message="登录成功",
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": expires_in,
                "user": auth_service.user_payload_for_client(user)
            }
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=APIResponse, summary="刷新令牌")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    使用刷新令牌获取新的访问令牌
    """
    auth_service = AuthService(db)

    try:
        payload = auth_service.decode_token(refresh_token)

        if payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的刷新令牌"
            )

        user = auth_service.get_user_by_id(int(payload.sub))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )

        access_token, new_refresh_token, expires_in = auth_service.create_tokens(user)

        return APIResponse(
            success=True,
            message="令牌刷新成功",
            data={
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": expires_in
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"令牌刷新失败: {str(e)}"
        )


@router.post("/logout", response_model=APIResponse, summary="用户登出")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    用户登出（记录日志）
    """
    auth_service = AuthService(db)

    # 记录审计日志
    auth_service.log_action(
        user_id=current_user.id,
        action="logout",
        resource="user",
        resource_id=str(current_user.id),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return APIResponse(
        success=True,
        message="登出成功"
    )


@router.get("/me", response_model=APIResponse, summary="获取当前用户信息")
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取当前登录用户的信息
    """
    auth_service = AuthService(db)
    return APIResponse(
        success=True,
        message="获取成功",
        data=auth_service.user_payload_for_client(current_user)
    )


@router.put("/me", response_model=APIResponse, summary="更新当前用户信息")
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    """
    auth_service = AuthService(db)

    update_data = user_data.model_dump(exclude_unset=True)
    user = auth_service.update_user(current_user.id, **update_data)

    return APIResponse(
        success=True,
        message="更新成功",
        data=auth_service.user_payload_for_client(user)
    )


@router.post("/change-password", response_model=APIResponse, summary="修改密码")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改当前用户密码
    """
    auth_service = AuthService(db)

    try:
        auth_service.change_password(
            current_user.id,
            password_data.old_password,
            password_data.new_password
        )

        # 记录审计日志
        auth_service.log_action(
            user_id=current_user.id,
            action="change_password",
            resource="user",
            resource_id=str(current_user.id),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return APIResponse(
            success=True,
            message="密码修改成功"
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== 管理员接口 ====================

@router.get("/users", response_model=APIResponse, summary="获取用户列表（管理员）")
async def get_users(
    skip: int = 0,
    limit: int = 20,
    role: str = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取所有用户列表（仅管理员）
    """
    auth_service = AuthService(db)

    role_filter = UserRole(role) if role else None
    users, total = auth_service.get_all_users(skip=skip, limit=limit, role=role_filter)

    return APIResponse(
        success=True,
        message="获取成功",
        data={
            "total": total,
            "items": [auth_service.user_payload_for_client(u) for u in users],
            "page": skip // limit + 1,
            "page_size": limit
        }
    )


@router.put("/users/{user_id}/deactivate", response_model=APIResponse, summary="禁用用户（管理员）")
async def deactivate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    禁用指定用户（仅管理员）
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己"
        )

    auth_service = AuthService(db)

    try:
        auth_service.deactivate_user(user_id)

        # 记录审计日志
        auth_service.log_action(
            user_id=current_user.id,
            action="deactivate_user",
            resource="user",
            resource_id=str(user_id),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return APIResponse(
            success=True,
            message="用户已禁用"
        )

    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/users/{user_id}/activate", response_model=APIResponse, summary="启用用户（管理员）")
async def activate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    启用指定用户（仅管理员）
    """
    auth_service = AuthService(db)

    try:
        auth_service.activate_user(user_id)

        # 记录审计日志
        auth_service.log_action(
            user_id=current_user.id,
            action="activate_user",
            resource="user",
            resource_id=str(user_id),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return APIResponse(
            success=True,
            message="用户已启用"
        )

    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/users/{user_id}/reset-password", response_model=APIResponse, summary="重置用户密码（管理员）")
async def reset_user_password(
    user_id: int,
    request: Request,
    password_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    重置指定用户密码（仅管理员）

    请求体:
    - new_password: 新密码（至少6位）
    """
    auth_service = AuthService(db)

    # 获取新密码
    new_password = password_data.get('new_password')

    if not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能为空"
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少6位"
        )

    try:
        auth_service.reset_user_password(user_id, new_password)

        # 记录审计日志
        auth_service.log_action(
            user_id=current_user.id,
            action="reset_user_password",
            resource="user",
            resource_id=str(user_id),
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return APIResponse(
            success=True,
            message=f"密码已重置",
            data={"new_password": new_password}
        )

    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/audit-logs", response_model=APIResponse, summary="获取审计日志（管理员）")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    user_id: int = None,
    action: str = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取审计日志（仅管理员）
    """
    auth_service = AuthService(db)

    logs, total = auth_service.get_audit_logs(
        user_id=user_id,
        action=action,
        skip=skip,
        limit=limit
    )

    return APIResponse(
        success=True,
        message="获取成功",
        data={
            "total": total,
            "items": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource": log.resource,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ],
            "page": skip // limit + 1,
            "page_size": limit
        }
    )
