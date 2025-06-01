import base64
import boto3
import os
import uuid

s3 = boto3.client('s3')
BUCKET = 'fotos-casamento'  # Substitua pelo nome do seu bucket

def lambda_handler(event, context):
    try:
        # Recebe o arquivo via multipart/form-data do API Gateway
        # API Gateway envia o body como base64-encoded
        if event.get("isBase64Encoded"):
            body = base64.b64decode(event["body"])
        else:
            body = event["body"].encode()

        # Extrai o nome do arquivo do header (exemplo simples)
        content_type = event["headers"].get("content-type") or event["headers"].get("Content-Type")
        boundary = content_type.split("boundary=")[-1]
        parts = body.split(("--" + boundary).encode())

        for part in parts:
            if b'filename="' in part:
                # Extrai o nome do arquivo
                header, file_content = part.split(b'\r\n\r\n', 1)
                file_content = file_content.rsplit(b'\r\n', 1)[0]
                filename = str(uuid.uuid4()) + ".jpg"  # Nome único para evitar sobrescrita

                # Salva no S3
                s3.put_object(
                    Bucket=BUCKET,
                    Key=filename,
                    Body=file_content,
                    ContentType='image/jpeg',
                    ACL='public-read'
                )

                return {
                    "statusCode": 200,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": '{"message": "Upload realizado com sucesso!"}'
                }

        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": '{"message": "Arquivo não encontrado no corpo da requisição."}'
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": '{"message": "Erro ao processar o upload: %s"}' % str(e)
        }