import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.schemas.admin import AdminPasswordUpdate
from app.repositories.admin_repository import AdminRepository
from app.repositories.audit_log_repository import AuditLogRepository

_PASSWORD_RULES = [
    (lambda password: len(password) >= 8, "La contraseña debe tener al menos 8 caracteres"),
    (lambda password: any(char.isupper() for char in password), "La contraseña debe contener al menos una mayúscula"),
    (lambda password: any(char.islower() for char in password), "La contraseña debe contener al menos una minúscula"),
    (lambda password: any(char.isdigit() for char in password), "La contraseña debe contener al menos un número"),
]


class AdminService:
    def __init__(self, admin_repo: AdminRepository, audit_repo: AuditLogRepository):
        self.admin_repo = admin_repo
        self.audit_repo = audit_repo

    @classmethod
    def from_session(cls, db: Session) -> "AdminService":
        return cls(AdminRepository(db), AuditLogRepository(db))

    def _validate_password(self, password: str):
        for is_valid, message in _PASSWORD_RULES:
            if not is_valid(password):
                raise HTTPException(
                    status_code=400,
                    detail={"error": "validation_error", "details": [message]},
                )

    def update_password(self, admin_id: int, schema: AdminPasswordUpdate):
        if schema.password != schema.password_confirm:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "details": ["Las contraseñas no coinciden"],
                },
            )

        self._validate_password(schema.password)

        admin = self.admin_repo.get_by_id(admin_id)
        if not admin:
            raise HTTPException(status_code=404, detail="Administrador no encontrado")

        password_bytes = schema.password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

        try:
            self.admin_repo.update_password(admin, password_hash)
            self.audit_repo.log_action(
                administrador_id=admin_id,
                accion="UPDATE_PASSWORD",
                descripcion_cambio="Administrador",
            )
        except Exception:
            self.audit_repo.log_action(
                administrador_id=admin_id,
                accion="UPDATE_PASSWORD_FAILED",
                descripcion_cambio="Administrador",
            )
            raise HTTPException(
                status_code=500,
                detail="Error al persistir en la base de datos",
            )

        return {"message": "password_updated"}
