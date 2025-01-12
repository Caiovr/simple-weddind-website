import boto3
import sqlite3
import json
import os

def lambda_handler(event, context):
    # Configurações
    s3_bucket = os.environ['S3_BUCKET']
    db_file = "/tmp/confirmations.db"

    # Baixa o arquivo do S3
    s3 = boto3.client('s3')
    s3.download_file(s3_bucket, 'database/confirmations.db', db_file)

    # Parseia os dados da requisição
    body = json.loads(event['body'])
    convidados = body['convidados']
    presenca = body['presenca']

    # Conecta ao banco de dados e salva a confirmação
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for convidado_id in convidados:
        cursor.execute(
            "INSERT INTO confirmacoes (convidado_id, presenca) VALUES (?, ?)",
            (convidado_id, presenca)
        )

    conn.commit()
    conn.close()

    # Atualiza o arquivo no S3
    s3.upload_file(db_file, s3_bucket, 'database/confirmations.db')

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Confirmação salva com sucesso!"}),
        "headers": {
            "Content-Type": "application/json"
        }
    }
