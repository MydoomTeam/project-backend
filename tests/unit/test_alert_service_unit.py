import unittest
from unittest.mock import Mock
from fastapi import HTTPException
from datetime import date

from app.services.alert_service import AlertService


class TestAlertServiceValidation(unittest.TestCase):
    def setUp(self):
        self.mock_alerta_repo = Mock()
        self.mock_audit_repo = Mock()
        self.service = AlertService(self.mock_alerta_repo, self.mock_audit_repo)

    def test_get_alerts_empty_list(self):
        self.mock_alerta_repo.get_all.return_value = []
        
        result = self.service.get_alerts()
        
        self.assertEqual(len(result), 0)
        self.mock_alerta_repo.get_all.assert_called_once()

    def test_get_alerts_with_data(self):
        mock_alerta = Mock()
        mock_alerta.id = 1
        mock_alerta.tipo_evento = "match_overdue"
        mock_alerta.mensaje = "Match vencido"
        mock_alerta.fecha_hora = date.today()
        mock_alerta.estado_lectura = "no_leido"
        
        self.mock_alerta_repo.get_all.return_value = [mock_alerta]
        
        result = self.service.get_alerts()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].tipo, "match_overdue")

    def test_acknowledge_alert_success(self):
        admin_id = 1
        alerta_id = 1
        mock_alerta = Mock()
        mock_alerta.id = alerta_id
        
        self.mock_alerta_repo.get_by_id.return_value = mock_alerta
        
        result = self.service.acknowledge_alert(admin_id, alerta_id)
        
        self.assertEqual(result["message"], "acknowledged")
        self.mock_alerta_repo.get_by_id.assert_called_once_with(alerta_id)
        self.mock_alerta_repo.acknowledge.assert_called_once_with(mock_alerta)

    def test_acknowledge_alert_not_found(self):
        admin_id = 1
        alerta_id = 999
        
        self.mock_alerta_repo.get_by_id.return_value = None
        
        with self.assertRaises(HTTPException) as ctx:
            self.service.acknowledge_alert(admin_id, alerta_id)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("no encontrada", str(ctx.exception.detail).lower())

    def test_acknowledge_alert_logs_audit_action(self):
        admin_id = 1
        alerta_id = 1
        mock_alerta = Mock()
        mock_alerta.id = alerta_id
        
        self.mock_alerta_repo.get_by_id.return_value = mock_alerta
        
        self.service.acknowledge_alert(admin_id, alerta_id)
        
        self.mock_audit_repo.log_action.assert_called_once()
        call_args = self.mock_audit_repo.log_action.call_args
        self.assertEqual(call_args.kwargs["actor_id"], admin_id)
        self.assertEqual(call_args.kwargs["accion"], "ACK_ALERTA")

    def test_acknowledge_alert_passes_alert_to_repo(self):
        admin_id = 1
        alerta_id = 1
        mock_alerta = Mock()
        mock_alerta.id = alerta_id
        
        self.mock_alerta_repo.get_by_id.return_value = mock_alerta
        
        self.service.acknowledge_alert(admin_id, alerta_id)
        
        self.mock_alerta_repo.acknowledge.assert_called_once_with(mock_alerta)

    def test_get_alerts_converts_to_response_schema(self):
        mock_alerta = Mock()
        mock_alerta.id = 1
        mock_alerta.tipo_evento = "match_overdue"
        mock_alerta.mensaje = "Test alert"
        mock_alerta.fecha_hora = date.today()
        mock_alerta.estado_lectura = "leido"
        
        self.mock_alerta_repo.get_all.return_value = [mock_alerta]
        
        result = self.service.get_alerts()
        
        self.assertEqual(len(result), 1)
        self.assertTrue(hasattr(result[0], "id"))
        self.assertTrue(hasattr(result[0], "tipo"))
        self.assertTrue(hasattr(result[0], "mensaje"))

    def test_acknowledge_alert_with_multiple_alerts(self):
        admin_id = 1
        alerta_id_1 = 1
        alerta_id_2 = 2
        
        mock_alerta_1 = Mock()
        mock_alerta_1.id = alerta_id_1
        mock_alerta_2 = Mock()
        mock_alerta_2.id = alerta_id_2
        
        self.mock_alerta_repo.get_by_id.side_effect = [mock_alerta_1, mock_alerta_2]
        
        result_1 = self.service.acknowledge_alert(admin_id, alerta_id_1)
        result_2 = self.service.acknowledge_alert(admin_id, alerta_id_2)
        
        self.assertEqual(result_1["message"], "acknowledged")
        self.assertEqual(result_2["message"], "acknowledged")
        self.assertEqual(self.mock_alerta_repo.acknowledge.call_count, 2)


if __name__ == "__main__":
    unittest.main()
