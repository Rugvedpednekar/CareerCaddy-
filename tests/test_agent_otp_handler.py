import base64
import unittest
from unittest.mock import MagicMock

from agent.otp_handler import OTPHandler, extract_numeric_code


def encoded(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


class AgentOTPHandlerTests(unittest.TestCase):
    def test_extracts_latest_portal_code_from_mocked_gmail_message(self):
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.list.return_value.execute.return_value = {"messages": [{"id": "message-1"}]}
        messages.get.return_value.execute.return_value = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "no-reply@jobs.example.com"},
                    {"name": "Subject", "value": "Your verification code"},
                ],
                "body": {"data": encoded("Use 482913 to confirm your login.")},
            }
        }
        handler = OTPHandler(service=service, sleep_fn=MagicMock(), input_fn=MagicMock())

        code = handler.wait_for_code("example.com")

        self.assertEqual(code, "482913")
        handler.input_fn.assert_not_called()

    def test_retries_then_uses_manual_code(self):
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.list.return_value.execute.return_value = {"messages": []}
        sleep = MagicMock()
        manual_input = MagicMock(return_value="Code: 7712")
        handler = OTPHandler(service=service, sleep_fn=sleep, input_fn=manual_input)

        code = handler.wait_for_code("example.com")

        self.assertEqual(code, "7712")
        self.assertEqual(messages.list.return_value.execute.call_count, 5)
        self.assertEqual(sleep.call_count, 4)
        manual_input.assert_called_once()

    def test_code_extractor_rejects_non_numeric_text(self):
        self.assertIsNone(extract_numeric_code("No code is present here."))


if __name__ == "__main__":
    unittest.main()
