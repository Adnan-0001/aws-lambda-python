import unittest
from unittest.mock import patch, MagicMock

from query_db_with_email_domain import lambda_handler


class TestLambdaFunction(unittest.TestCase):
    @patch("query_db_with_email_domain.connect_to_table")
    @patch("query_db_with_email_domain.boto3.client")
    def test_lambda_handler(self, mock_boto3_client, mock_connect_to_table):
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {"email": "test@example.com"},
        }

        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [
                {"email": "test@example.com", "password": "encrypted_password"}
            ]
        }

        mock_connect_to_table.return_value = mock_table

        mock_kms = MagicMock()
        mock_kms.decrypt.return_value = {"Plaintext": b"decrypted_password"}
        mock_boto3_client.return_value = mock_kms

        result = lambda_handler(event, None)

        mock_connect_to_table.assert_called_once()
        mock_table.scan.assert_called()
        mock_kms.decrypt.assert_called()

        self.assertEqual(result["statusCode"], 200)
        self.assertIn("data", result["body"])
        self.assertIn("count", result["body"])


if __name__ == "__main__":
    unittest.main()
