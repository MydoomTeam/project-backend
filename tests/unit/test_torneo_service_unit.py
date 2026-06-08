import unittest
from unittest.mock import Mock
from fastapi import HTTPException

from app.domain.schemas.torneo import TorneoCreate
from app.services.torneo_service import TorneoService


class TestTorneoServiceValidation(unittest.TestCase):
    def setUp(self):
        self.mock_torneo_repo = Mock()
        self.mock_audit_repo = Mock()
        self.service = TorneoService(self.mock_torneo_repo, self.mock_audit_repo)

    def test_create_torneo_valid_data(self):
        admin_id = 1
        schema = TorneoCreate(
            nombre="Torneo Test",
            tipo_eliminacion="simple",
            duracion_ronda_min=60,
            participantes_max=16
        )
        
        mock_torneo = Mock()
        mock_torneo.id = 1
        mock_torneo.nombre = "Torneo Test"
        mock_torneo.estado = "Pendiente"
        self.mock_torneo_repo.create.return_value = mock_torneo
        
        result = self.service.create_torneo(admin_id, schema)
        
        self.assertIsNotNone(result)
        self.mock_torneo_repo.create.assert_called_once()

    def test_create_torneo_missing_nombre(self):
        admin_id = 1
        schema = TorneoCreate(
            nombre="",
            tipo_eliminacion="simple",
            duracion_ronda_min=60,
            participantes_max=16
        )
        
        with self.assertRaises(HTTPException) as ctx:
            self.service.create_torneo(admin_id, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("nombre", str(ctx.exception.detail).lower())

    def test_create_torneo_invalid_participantes_too_few(self):
        admin_id = 1
        schema = TorneoCreate(
            nombre="Torneo Test",
            tipo_eliminacion="simple",
            duracion_ronda_min=60,
            participantes_max=1
        )
        
        with self.assertRaises(HTTPException) as ctx:
            self.service.create_torneo(admin_id, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("participantes", str(ctx.exception.detail).lower())

    def test_create_torneo_invalid_duracion_zero(self):
        admin_id = 1
        schema = TorneoCreate(
            nombre="Torneo Test",
            tipo_eliminacion="simple",
            duracion_ronda_min=0,
            participantes_max=16
        )
        
        with self.assertRaises(HTTPException) as ctx:
            self.service.create_torneo(admin_id, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("duración", str(ctx.exception.detail).lower())

    def test_create_torneo_invalid_tipo_eliminacion(self):
        admin_id = 1
        schema = TorneoCreate(
            nombre="Torneo Test",
            tipo_eliminacion="invalid_type",
            duracion_ronda_min=60,
            participantes_max=16
        )
        
        with self.assertRaises(HTTPException) as ctx:
            self.service.create_torneo(admin_id, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("eliminación", str(ctx.exception.detail).lower())

    def test_create_torneo_valid_tipo_eliminacion_doble(self):
        admin_id = 1
        schema = TorneoCreate(
            nombre="Torneo Test",
            tipo_eliminacion="doble",
            duracion_ronda_min=60,
            participantes_max=16
        )
        
        result = self.service.create_torneo(admin_id, schema)
        self.assertIsNotNone(result)

    def test_create_torneo_valid_tipo_eliminacion_liga(self):
        admin_id = 1
        schema = TorneoCreate(
            nombre="Torneo Test",
            tipo_eliminacion="liga",
            duracion_ronda_min=60,
            participantes_max=16
        )
        
        result = self.service.create_torneo(admin_id, schema)
        self.assertIsNotNone(result)

    def test_get_torneo_success(self):
        torneo_id = 1
        mock_torneo = Mock()
        mock_torneo.id = torneo_id
        mock_torneo.nombre = "Torneo Test"
        mock_torneo.estado = "Pendiente"
        mock_torneo.tipo_eliminacion = "simple"
        mock_torneo.duracion_ronda = 60
        mock_torneo.numero_participantes = 16
        self.mock_torneo_repo.get_by_id.return_value = mock_torneo
        
        result = self.service.get_torneo(torneo_id)
        
        self.assertIsNotNone(result)
        self.mock_torneo_repo.get_by_id.assert_called_once_with(torneo_id)

    def test_get_torneo_not_found(self):
        torneo_id = 999
        self.mock_torneo_repo.get_by_id.return_value = None
        
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_torneo(torneo_id)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
