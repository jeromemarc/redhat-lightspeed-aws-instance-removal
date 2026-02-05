import json
import os
import urllib.request
import urllib.parse
import urllib.error
import boto3

INVENTORY_API_URL = os.environ["INVENTORY_API_URL"]
AUTH_URL = os.environ.get("AUTH_URL")
HCC_CLIENT_ID = os.environ["HCC_CLIENT_ID"]
HCC_CLIENT_SECRET = os.environ["HCC_CLIENT_SECRET"]

SECRET_NAME = "redhatlightspeed/serviceaccount/pm_jmarc"
REGION_NAME = "us-east-2"

# skipping for now: aws permissions issues for getting Secret Manager
def get_hcc_credentials(secret_name, region_name):
    client = boto3.client("secretsmanager", region_name=region_name)

    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])

    return secret["HCC_CLIENT_ID"], secret["HCC_CLIENT_SECRET"]

def get_access_token():
    #hcc_client_id, hcc_client_secret = get_hcc_credentials(SECRET_NAME, REGION_NAME)
    hcc_client_id = HCC_CLIENT_ID
    hcc_client_secret = HCC_CLIENT_SECRET

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": hcc_client_id,
        "client_secret": hcc_client_secret
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    request = urllib.request.Request(
        AUTH_URL,
        data=data,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            token_response = json.loads(body)
            return token_response["access_token"]

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print("Token request failed:", e.code, error_body)
        raise

def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    try:
        instance_id = event["detail"]["EC2InstanceId"]
    except KeyError:
        raise Exception("EC2InstanceId not found in event")
    
    token = get_access_token()

    query = urllib.parse.urlencode({
        "provider_type": "aws",
        "provider_id": instance_id
    })
    
    url = f"{INVENTORY_API_URL}/hosts?{query}" 

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    request = urllib.request.Request(
        url,
        headers=headers,
        method="DELETE"
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print("Inventory delete OK:", response.status)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print("Inventory delete failed:", e.code, error_body)
        raise

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Host removed from inventory",
            "provider_id": instance_id
        })
    }