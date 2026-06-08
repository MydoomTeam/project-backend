from sqlalchemy.orm import Session

from app.domain.models.admin import Administrador
from datetime import date


class AdminRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, admin_id: int) -> Administrador | None:
        return (
            self.db.query(Administrador).filter(Administrador.id == admin_id).first()
        )

    def update_password(self, admin: Administrador, password_hash: str) -> Administrador:
        admin.contrasena_hash = password_hash
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def ensure_system_admin(self, admin_id: int) -> Administrador:
        admin = self.get_by_id(admin_id)
        if admin:
            return admin

        admin = Administrador(
            id=admin_id,
            nombre_usuario="system_admin",
            correo_electronico="system@localhost",
            contrasena_hash="",
            rol="administrador",
            fecha_ultimo_acceso=date.today(),
        )
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin
