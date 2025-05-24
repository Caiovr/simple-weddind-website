import boto3
import json
import os

# SQS client
sqs = boto3.client('sqs')

# SQS Queue URLs from environment variables
WRITE_QUEUE_URL = os.environ['SQS_WRITE_QUEUE']

def lambda_handler(event, context):
    try:
        print(event)
        body = json.loads(event["body"])

        # Identifica o tipo de payload pelo conteúdo
        if "ids" in body and "convidados" in body and "presenca" in body:
            # Payload de confirmação de presença
            message = {
                "ids": body["ids"],
                "convidados": body["convidados"],
                "presenca": body["presenca"],
                "timestamp": body.get("timestamp")  # Opcional
            }
        elif "amount" in body and "item_title" in body:
            # Payload de compra/presente
            message = {
                "amount": body["amount"],
                "item_title": body["item_title"],
                "currency": body.get("currency"),
                "payment_type": body.get("payment_type"),
                "name": body.get("name"),
                "message": body.get("message"),
                "timestamp": body.get("timestamp")
            }
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Payload inválido."})
            }

        print(message)
        # Envia para a fila correta
        sqs.send_message(
            QueueUrl=WRITE_QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Mensagem recebida com sucesso."})
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Ocorreu um erro ao processar a requisição."})
        }