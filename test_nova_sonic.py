import os
import boto3
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print AWS credentials (redacted for security)
access_key = os.getenv("AWS_ACCESS_KEY_ID")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region = os.getenv("AWS_REGION")

print(f"Using AWS credentials:")
print(f"  Access Key: {access_key[:4]}...{access_key[-4:]}")
print(f"  Secret Key: {secret_key[:4]}...{secret_key[-4:]}")
print(f"  Region: {region}")

# Create a Bedrock client
try:
    bedrock_client = boto3.client(
        service_name='bedrock-runtime',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )
    print("Successfully created Bedrock client")
except Exception as e:
    print(f"Error creating Bedrock client: {e}")
    exit(1)

# Try to invoke the Nova Sonic model
try:
    print("Attempting to invoke Nova Sonic model...")
    response = bedrock_client.invoke_model(
        modelId='amazon.nova-sonic-v1:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "inputText": "Hello, how are you?",
            "textToSpeechConfig": {
                "voiceId": "matthew"
            }
        })
    )
    print("Successfully invoked Nova Sonic model")
    print(f"Response status code: {response['ResponseMetadata']['HTTPStatusCode']}")
except Exception as e:
    print(f"Error invoking Nova Sonic model: {e}")
    print("This could indicate a permissions issue or that the service is not enabled for your account")

print("\nTest complete")
