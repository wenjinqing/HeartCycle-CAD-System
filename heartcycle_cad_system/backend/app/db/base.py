"""
数据库基础配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logger import logger

# 创建数据库引擎
# 支持MySQL: mysql+pymysql://user:password@host:port/database
# 支持SQLite: sqlite:///./data/database.db
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_recycle=3600,   # 1小时后回收连接
    echo=settings.DEBUG  # 调试模式下打印SQL
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db():
    """
    获取数据库会话（依赖注入）
    
    Yields:
    -------
    Session : 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_patients_extended_columns():
    """为已有库补充患者体征/HRV 列（可重复执行）"""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(engine)
        if not inspector.has_table("patients"):
            return
        existing = {c["name"] for c in inspector.get_columns("patients")}
    except Exception as e:
        logger.warning("患者表迁移检查跳过: %s", e)
        return

    dialect = engine.dialect.name
    # (列名, sqlite类型, mysql/postgresql 浮点列用 DOUBLE)
    specs = [
        ("height_cm", "REAL", "DOUBLE"),
        ("weight_kg", "REAL", "DOUBLE"),
        ("blood_pressure_systolic", "INTEGER", "INT"),
        ("blood_pressure_diastolic", "INTEGER", "INT"),
        ("resting_heart_rate", "INTEGER", "INT"),
        ("occupation", "VARCHAR(100)", "VARCHAR(100)"),
        ("hrv_mean_rr", "REAL", "DOUBLE"),
        ("hrv_sdnn", "REAL", "DOUBLE"),
        ("hrv_rmssd", "REAL", "DOUBLE"),
        ("hrv_pnn50", "REAL", "DOUBLE"),
        ("hrv_lf_hf_ratio", "REAL", "DOUBLE"),
        ("waist_cm", "REAL", "DOUBLE"),
        ("total_cholesterol", "REAL", "DOUBLE"),
        ("ldl_cholesterol", "REAL", "DOUBLE"),
        ("hdl_cholesterol", "REAL", "DOUBLE"),
        ("triglyceride", "REAL", "DOUBLE"),
        ("fasting_glucose", "REAL", "DOUBLE"),
        ("hba1c", "REAL", "DOUBLE"),
        ("smoke_status", "VARCHAR(20)", "VARCHAR(20)"),
        ("physical_activity", "VARCHAR(20)", "VARCHAR(20)"),
        ("diabetes", "INTEGER", "INT"),
        ("hypertension_dx", "INTEGER", "INT"),
        ("dyslipidemia", "INTEGER", "INT"),
        ("family_history_cad", "INTEGER", "INT"),
        ("chest_pain_symptom", "INTEGER", "INT"),
    ]

    for col, sqlite_t, other_t in specs:
        if col in existing:
            continue
        if dialect == "sqlite":
            sql_t = sqlite_t
        elif dialect == "postgresql" and other_t == "DOUBLE":
            sql_t = "DOUBLE PRECISION"
        else:
            sql_t = other_t
        stmt = f"ALTER TABLE patients ADD COLUMN {col} {sql_t}"
        try:
            if dialect in ("mysql", "postgresql"):
                stmt += " NULL"
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("已添加列 patients.%s", col)
        except Exception as ex:
            logger.warning("添加列 patients.%s 失败: %s", col, ex)


def migrate_patients_drop_id_card_column():
    """删除已废弃的 id_card 列（ORM 与 API 已不再使用；SQLite 3.35+ / MySQL / PostgreSQL）"""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(engine)
        if not inspector.has_table("patients"):
            return
        existing = {c["name"] for c in inspector.get_columns("patients")}
        if "id_card" not in existing:
            return
    except Exception as e:
        logger.warning("检查 patients.id_card 列跳过: %s", e)
        return

    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE patients DROP COLUMN id_card"))
        logger.info("已删除列 patients.id_card")
    except Exception as ex:
        logger.warning("删除 patients.id_card 失败（可手动执行 ALTER 或升级 SQLite）: %s", ex)


def migrate_patients_linked_user_id():
    """为患者表增加 linked_user_id（患者账号绑定档案）"""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(engine)
        if not inspector.has_table("patients"):
            return
        existing = {c["name"] for c in inspector.get_columns("patients")}
    except Exception as e:
        logger.warning("检查 patients.linked_user_id 跳过: %s", e)
        return

    if "linked_user_id" in existing:
        return

    dialect = engine.dialect.name
    col_sql = "INTEGER" if dialect == "sqlite" else "INT"
    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE patients ADD COLUMN linked_user_id {col_sql} NULL"))
        logger.info("已添加列 patients.linked_user_id")
    except Exception as ex:
        logger.warning("添加 patients.linked_user_id 失败: %s", ex)


def migrate_patient_doctor_bindings_from_doctor_id():
    """将原 patients.doctor_id 同步到 patient_doctor_bindings（幂等）。"""
    from sqlalchemy import inspect
    from app.models.user import Patient, PatientDoctorBinding

    try:
        inspector = inspect(engine)
        if not inspector.has_table("patients"):
            return
        if not inspector.has_table("patient_doctor_bindings"):
            return
    except Exception as e:
        logger.warning("检查 patient_doctor_bindings 迁移跳过: %s", e)
        return

    db = SessionLocal()
    try:
        for p in db.query(Patient).filter(Patient.doctor_id.isnot(None)).all():
            exists = (
                db.query(PatientDoctorBinding)
                .filter(
                    PatientDoctorBinding.patient_id == p.id,
                    PatientDoctorBinding.doctor_id == p.doctor_id,
                )
                .first()
            )
            if not exists:
                db.add(
                    PatientDoctorBinding(patient_id=p.id, doctor_id=p.doctor_id)
                )
        db.commit()
        logger.info("已从 patients.doctor_id 同步患者-医生绑定")
    except Exception as ex:
        db.rollback()
        logger.warning("同步 patient_doctor_bindings 失败: %s", ex)
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(bind=engine)
    migrate_patients_extended_columns()
    migrate_patients_drop_id_card_column()
    migrate_patients_linked_user_id()
    migrate_patient_doctor_bindings_from_doctor_id()
    logger.info("数据库表已创建")


def check_db_connection():
    """检查数据库连接"""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        logger.info("数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return False

