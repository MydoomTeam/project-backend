import unittest
from datetime import date
from unittest.mock import Mock

from fastapi import HTTPException

from app.services.alert_service import AlertService


class TestAlertServiceValidation(unittest.TestCase):
    def setUp(self):
        self.mock_alert_repo = Mock()
        self.mock_audit_repo = Mock()
        self.service = AlertService(self.mock_alert_repo, self.mock_audit_repo)

    def test_get_alerts_empty_list(self):
        self.mock_alert_repo.get_all.return_value = []

        result = self.service.get_alerts()

        self.assertEqual(len(result), 0)
        self.mock_alert_repo.get_all.assert_called_once()

    def test_get_alerts_with_data(self):
        mock_alert = Mock()
        mock_alert.id = 1
        mock_alert.event_type = "match_overdue"
        mock_alert.message = "Match vencido"
        mock_alert.datetime = date.today()
        mock_alert.read_status = "no_leido"

        self.mock_alert_repo.get_all.return_value = [mock_alert]

        result = self.service.get_alerts()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].event_type, "match_overdue")

    def test_acknowledge_alert_success(self):
        admin_id = 1
        alert_id = 1
        mock_alert = Mock()
        mock_alert.id = alert_id

        self.mock_alert_repo.get_by_id.return_value = mock_alert

        result = self.service.acknowledge_alert(admin_id, alert_id)

        self.assertEqual(result["message"], "acknowledged")
        self.mock_alert_repo.get_by_id.assert_called_once_with(alert_id)
        self.mock_alert_repo.acknowledge.assert_called_once_with(mock_alert)

    def test_acknowledge_alert_not_found(self):
        admin_id = 1
        alert_id = 999

        self.mock_alert_repo.get_by_id.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            self.service.acknowledge_alert(admin_id, alert_id)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("no encontrada", str(ctx.exception.detail).lower())

    def test_acknowledge_alert_logs_audit_action(self):
        admin_id = 1
        alert_id = 1
        mock_alert = Mock()
        mock_alert.id = alert_id

        self.mock_alert_repo.get_by_id.return_value = mock_alert

        self.service.acknowledge_alert(admin_id, alert_id)

        self.mock_audit_repo.log_action.assert_called_once()
        call_args = self.mock_audit_repo.log_action.call_args
        self.assertEqual(call_args.kwargs["actor_id"], admin_id)
        self.assertEqual(call_args.kwargs["action"], "ACK_ALERTA")

    def test_acknowledge_alert_passes_alert_to_repo(self):
        admin_id = 1
        alert_id = 1
        mock_alert = Mock()
        mock_alert.id = alert_id

        self.mock_alert_repo.get_by_id.return_value = mock_alert

        self.service.acknowledge_alert(admin_id, alert_id)

        self.mock_alert_repo.acknowledge.assert_called_once_with(mock_alert)

    def test_get_alerts_converts_to_response_schema(self):
        mock_alert = Mock()
        mock_alert.id = 1
        mock_alert.event_type = "match_overdue"
        mock_alert.message = "Test alert"
        mock_alert.datetime = date.today()
        mock_alert.read_status = "leido"

        self.mock_alert_repo.get_all.return_value = [mock_alert]

        result = self.service.get_alerts()

        self.assertEqual(len(result), 1)
        self.assertTrue(hasattr(result[0], "id"))
        self.assertTrue(hasattr(result[0], "event_type"))
        self.assertTrue(hasattr(result[0], "message"))

    def test_acknowledge_alert_with_multiple_alerts(self):
        admin_id = 1
        alert_id_1 = 1
        alert_id_2 = 2

        mock_alert_1 = Mock()
        mock_alert_1.id = alert_id_1
        mock_alert_2 = Mock()
        mock_alert_2.id = alert_id_2

        self.mock_alert_repo.get_by_id.side_effect = [mock_alert_1, mock_alert_2]

        result_1 = self.service.acknowledge_alert(admin_id, alert_id_1)
        result_2 = self.service.acknowledge_alert(admin_id, alert_id_2)

        self.assertEqual(result_1["message"], "acknowledged")
        self.assertEqual(result_2["message"], "acknowledged")
        self.assertEqual(self.mock_alert_repo.acknowledge.call_count, 2)


if __name__ == "__main__":
    unittest.main()
