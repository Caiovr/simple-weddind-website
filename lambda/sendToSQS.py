import boto3
import json
import os

# SQS client
sqs = boto3.client('sqs')

# SQS Queue URL from environment variable
QUEUE_URL = os.environ['SQS_QUEUE']

def lambda_handler(event, context):
    try:
        # Parse the request body
        print(event)
        body = json.loads(event["body"])
        ids = body["ids"]
        convidados = body["convidados"]
        presenca = body["presenca"]
        #timestamp = body["timestamp"]

        # Create the message to send to SQS
        message = {
            "ids": ids,
            "convidados": convidados,
            "presenca": presenca,
            #"timestamp": timestamp
        }

        # Send the message to the SQS queue
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        # Return a success response
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Confirmation received successfully."})
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "An error occurred while processing the request."})
        }