import boto3
import sqlite3
import json
import os

def lambda_handler(event, context):
    try:
        # Configurações
        s3_bucket = os.environ['S3_BUCKET']
        db_name = os.environ['DB_NAME']
        db_file = f"/tmp/{db_name}"

        # Baixa o arquivo do S3
        s3 = boto3.client('s3')
        s3.download_file(s3_bucket, db_name, db_file)

        # Conecta ao banco de dados e salva a confirmação
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Parseia os dados da requisição
        failed_messages = []
        print(event)
        for record in event['Records']:
            try:
                message_id = record["messageId"]
                body = json.loads(record['body'])
                ids = body["ids"]
                presencas = body["presenca"]
                #timestamps = body["timestamp"]

                for convidado_id, presenca in zip(ids, presencas):
                    cursor.execute(
                        """
                        INSERT INTO confirmacoes (convidado_id, presenca) 
                        VALUES (?, ?)
                        """,
                        (convidado_id, presenca)
                    )

                conn.commit()
            except Exception as e:
                print(f"Message processing failed: {message_id}, Error: {e}")
                # Add the failed message ID to the failure list
                failed_messages.append({"itemIdentifier": message_id})

        conn.close()
        # Atualiza o arquivo no S3
        s3.upload_file(db_file, s3_bucket, db_name)

        if len(failed_messages) == 0:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Todas as confirmações foram salvas com sucesso!"}),
                "headers": {
                    "Content-Type": "application/json"
                }
            }
        else:
            return {
                "batchItemFailures": failed_messages
            }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "An error occurred while processing the request."})
        }