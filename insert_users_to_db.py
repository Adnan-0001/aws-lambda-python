import boto3

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("user_credentials")


def extract_fields_and_insert_into_db(line):
    email = password = username = domain = ""
    separators = [":", ";", ","]
    for separator in separators:
        if separator in line:
            parts = line.split(separator)
            if len(parts) == 2:
                email = parts[0].strip()
                password = parts[1].strip()

                if "@" not in email:
                    username = email
                    email = domain = ""
                else:
                    username, domain = email.split("@")

                try:
                    table.put_item(
                        Item={
                            "username": username,
                            "email": email,
                            "password": password,
                            "domain": domain,
                        }
                    )
                except Exception as e:
                    print("Exception says: ", e)


def lambda_handler(event, context):
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    s3_file_name = event["Records"][0]["s3"]["object"]["key"]
    response = s3_client.get_object(Bucket=bucket_name, Key=s3_file_name)
    data = response["Body"].read().decode("utf-8")
    records = data.split("\n")
    for record in records:
        extract_fields_and_insert_into_db(record.strip())


lambda_handler()
