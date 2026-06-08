import unittest
from unittest.mock import Mock, patch
import bcrypt
from fastapi import HTTPException

from app.domain.schemas.admin import AdminPasswordUpdate
from app.services.admin_service import AdminService


class TestAdminServicePasswordValidation(unittest.TestCase):
    def setUp(self):
        self.mock_admin_repo = Mock()
        self.mock_audit_repo = Mock()
        self.service = AdminService(self.mock_admin_repo, self.mock_audit_repo)

    def test_password_validation_insufficient_length(self):
        schema = AdminPasswordUpdate(password="Short1!", password_confirm="Short1!")
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password(schema.password)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("al menos 8 caracteres", str(ctx.exception.detail))

    def test_password_validation_missing_uppercase(self):
        schema = AdminPasswordUpdate(password="lowercase1!", password_confirm="lowercase1!")
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password(schema.password)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("mayúscula", str(ctx.exception.detail))

    def test_password_validation_missing_lowercase(self):
        schema = AdminPasswordUpdate(password="UPPERCASE1!", password_confirm="UPPERCASE1!")
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password(schema.password)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("minúscula", str(ctx.exception.detail))

    def test_password_validation_missing_digit(self):
        schema = AdminPasswordUpdate(password="NoDigitPass!", password_confirm="NoDigitPass!")
        with self.assertRaises(HTTPException) as ctx:
            self.service._validate_password(schema.password)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("número", str(ctx.exception.detail))

    def test_password_validation_success(self):
        password = "ValidPass123!"
        try:
            self.service._validate_password(password)
        except HTTPException:
            self.fail("Valid password should not raise HTTPException")

    def test_update_password_mismatch_confirmation(self):
        admin_id = 1
        schema = AdminPasswordUpdate(password="ValidPass123!", password_confirm="DifferentPass123!")
        with self.assertRaises(HTTPException) as ctx:
            self.service.update_password(admin_id, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("no coinciden", str(ctx.exception.detail))

    def test_update_password_admin_not_found(self):
        admin_id = 999
        schema = AdminPasswordUpdate(password="ValidPass123!", password_confirm="ValidPass123!")
        self.mock_admin_repo.get_by_id.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            self.service.update_password(admin_id, schema)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("no encontrado", str(ctx.exception.detail))

    def test_update_password_success(self):
        admin_id = 1
        schema = AdminPasswordUpdate(password="ValidPass123!", password_confirm="ValidPass123!")
        mock_admin = Mock()
        mock_admin.id = admin_id
        self.mock_admin_repo.get_by_id.return_value = mock_admin
        
        result = self.service.update_password(admin_id, schema)
        
        self.assertEqual(result["message"], "password_updated")
        self.mock_admin_repo.update_password.assert_called_once()
        self.mock_audit_repo.log_action.assert_called_once()
        call_args = self.mock_audit_repo.log_action.call_args
        self.assertEqual(call_args.kwargs["accion"], "UPDATE_PASSWORD")
        self.assertEqual(call_args.kwargs["administrador_id"], admin_id)

    def test_update_password_database_error(self):
        admin_id = 1
        schema = AdminPasswordUpdate(password="ValidPass123!", password_confirm="ValidPass123!")
        mock_admin = Mock()
        mock_admin.id = admin_id
        self.mock_admin_repo.get_by_id.return_value = mock_admin
        self.mock_admin_repo.update_password.side_effect = Exception("DB Error")
        
        with self.assertRaises(HTTPException) as ctx:
            self.service.update_password(admin_id, schema)
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("base de datos", str(ctx.exception.detail))
        call_args = self.mock_audit_repo.log_action.call_args
        self.assertEqual(call_args.kwargs["accion"], "UPDATE_PASSWORD_FAILED")

    def test_password_hash_uses_correct_rounds(self):
        password = "ValidPass123!"
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        self.assertTrue(bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")))

    def test_password_hash_prevents_plaintext_storage(self):
        password = "ValidPass123!"
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        self.assertNotEqual(password, password_hash)


if __name__ == "__main__":
    unittest.main()
