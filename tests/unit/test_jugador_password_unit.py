import unittest
from unittest.mock import Mock

import bcrypt
from fastapi import HTTPException

from app.domain.schemas.jugador import PasswordUpdate
from app.services.jugador_service import JugadorService


def _service_with_mocks() -> JugadorService:
    service = object.__new__(JugadorService)  # sin __init__ (sin DB real)
    service.repo = Mock()
    service.audit_repo = Mock()
    return service


def _update(password: str, confirm: str | None = None) -> PasswordUpdate:
    return PasswordUpdate(password=password, password_confirm=confirm if confirm is not None else password)


class TestJugadorPasswordValidation(unittest.TestCase):
    def setUp(self):
        self.service = _service_with_mocks()

    def test_password_validation_insufficient_length(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password("Short1!")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("al menos 8 caracteres", str(ctx.exception.detail))

    def test_password_validation_missing_uppercase(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password("lowercase1!")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("mayúscula", str(ctx.exception.detail))

    def test_password_validation_missing_lowercase(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password("UPPERCASE1!")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("minúscula", str(ctx.exception.detail))

    def test_password_validation_missing_digit(self):
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password("NoDigitPass!")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("número", str(ctx.exception.detail))

    def test_password_validation_success(self):
        try:
            self.service._validate_password("ValidPass123!")
        except HTTPException:
            self.fail("Valid password should not raise HTTPException")


class TestJugadorCambiarPassword(unittest.TestCase):
    def setUp(self):
        self.service = _service_with_mocks()

    def test_cambiar_password_mismatch_confirmation(self):
        schema = _update("ValidPass123!", confirm="DifferentPass123!")
        with self.assertRaises(HTTPException) as ctx:
            self.service.change_password(1, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("no coinciden", str(ctx.exception.detail))

    def test_cambiar_password_actor_inexistente(self):
        self.service.repo.get_by_id.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            self.service.change_password(9999, _update("ValidPass123!"))
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("no encontrado", str(ctx.exception.detail))

    def test_cambiar_password_success(self):
        jugador = Mock()
        jugador.id = 1
        self.service.repo.get_by_id.return_value = jugador

        result = self.service.change_password(1, _update("ValidPass123!"))

        self.assertEqual(result["message"], "password_updated")
        self.service.repo.update_password.assert_called_once()
        self.service.audit_repo.log_action.assert_called_once()
        call_args = self.service.audit_repo.log_action.call_args
        self.assertEqual(call_args.kwargs["accion"], "UPDATE_PASSWORD")
        self.assertEqual(call_args.kwargs["actor_id"], 1)

    def test_cambiar_password_persistence_failure(self):
        jugador = Mock()
        jugador.id = 1
        self.service.repo.get_by_id.return_value = jugador
        self.service.repo.update_password.side_effect = Exception("DB Error")

        with self.assertRaises(HTTPException) as ctx:
            self.service.change_password(1, _update("ValidPass123!"))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("base de datos", str(ctx.exception.detail))
        call_args = self.service.audit_repo.log_action.call_args
        self.assertEqual(call_args.kwargs["accion"], "UPDATE_PASSWORD_FAILED")


class TestJugadorPasswordHashing(unittest.TestCase):
    def setUp(self):
        self.service = _service_with_mocks()

    def test_hash_uses_bcrypt_rounds_12(self):
        password_hash = self.service._hash_password("ValidPass123!")
        # bcrypt autodescriptivo: prefijo de algoritmo + coste embebido.
        self.assertTrue(password_hash.startswith("$2b$12$"))
        self.assertTrue(
            bcrypt.checkpw("ValidPass123!".encode("utf-8"), password_hash.encode("utf-8"))
        )

    def test_hash_prevents_plaintext_storage(self):
        password = "ValidPass123!"
        password_hash = self.service._hash_password(password)
        self.assertNotEqual(password, password_hash)


if __name__ == "__main__":
    unittest.main()
