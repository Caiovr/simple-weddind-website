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
    s3.download_file(s3_bucket, db_name, db_file)

    # Parseia os dados da requisição
    body = event
    ids = body["ids"]
    presencas = body["presenca"]
    timestamps = body["timestamp"]

    # Conecta ao banco de dados e salva a confirmação
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for convidado_id, presenca, timestamp in zip(ids, presencas, timestamps):
        print(convidado_id, presenca, timestamp)
        cursor.execute(
            """
            INSERT INTO confirmacoes (convidado_id, presenca, timestamp) 
            VALUES (?, ?, ?)
            """,
            (convidado_id, presenca, timestamp),
        )

    conn.commit()
    conn.close()

    # Atualiza o arquivo no S3
    s3.upload_file(db_file, s3_bucket, db_name)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Confirmação salva com sucesso!"}),
        "headers": {
            "Content-Type": "application/json"
        }
    }