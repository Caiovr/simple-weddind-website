import boto3
import sqlite3
import json
import os

def lambda_handler(event, context):
    # Configurações
    s3_bucket = os.environ['S3_BUCKET']
    db_name = os.environ['DB_NAME']
    db_file = f"/tmp/{db_name}"

    # Baixa o arquivo do S3
    s3 = boto3.client('s3')
    s3.download_file(s3_bucket, f'database/{db_name}', db_file)

    # Conecta ao banco de dados
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Busca os convidados
    cursor.execute("SELECT id, name FROM convidados")
    convidados = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]

    conn.close()

    return {
        "statusCode": 200,
        "body": json.dumps(convidados),
        "headers": {
            "Content-Type": "application/json"
        }
    }
