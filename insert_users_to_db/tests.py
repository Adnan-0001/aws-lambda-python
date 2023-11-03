import unittest
import boto3
from moto import mock_s3, mock_dynamodb
from unittest.mock import patch, MagicMock
from insert_users_to_db import lambda_handler
from insert_users_to_db import extract_fields_and_insert_into_db


class TestLambdaFunction(unittest.TestCase):
    @mock_s3
    @mock_dynamodb
    def test_lambda_handler(self):
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        test_file_data = (
            "test1@example.com:password1\ntest2@example.com:password2"
        )
        s3_client.put_object(
            Bucket="test-bucket",
            Key="test-file.txt",
            Body=test_file_data.encode("utf-8"),
        )

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test-file.txt"},
                    }
                }
            ]
        }

        with patch(
            "insert_users_to_db.connect_to_table"
        ) as mock_connect_to_table, patch(
            "insert_users_to_db.extract_fields_and_insert_into_db"
        ) as mock_extract_fields_and_insert_into_db:
            lambda_handler(event, None)

        mock_connect_to_table.assert_called_once()
        mock_extract_fields_and_insert_into_db.assert_called()
        assert mock_extract_fields_and_insert_into_db.call_count == 2

    @patch("insert_users_to_db.encrypt_data")
    def test_extract_fields_and_insert_into_db(self, mock_encrypt_data):
        mock_table = MagicMock()
        line = "test@example.com:password123"

        extract_fields_and_insert_into_db(mock_table, line)

        mock_encrypt_data.assert_called_once_with("password123", "master_key")
        mock_table.put_item.assert_called_once_with(
            Item={
                "username": "test",
                "email": "test@example.com",
                "password": mock_encrypt_data.return_value,
                "domain": "example.com",
            }
        )


if __name__ == "__main__":
    unittest.main()
