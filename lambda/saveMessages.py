import boto3
import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta

def parse_timestamp(ts):
    try:
        # Converte string ISO para datetime em UTC
        dt_utc = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        # Define o fuso horário de Brasília (UTC-3)
        brasil_tz = timezone(timedelta(hours=-3))
        # Converte para o horário de Brasília
        dt_brasil = dt_utc.astimezone(brasil_tz)
        # Retorna no formato aceito pelo SQLite
        return dt_brasil.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

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
                # Identifica o tipo de payload pelo conteúdo
                if "ids" in body and "convidados" in body and "presenca" in body:
                    ids = body["ids"]
                    presencas = body["presenca"]
                    timestamp = body.get("timestamp")
                    timestamp_sqlite = parse_timestamp(timestamp) if timestamp else None

                    if timestamp_sqlite:
                        for convidado_id, presenca in zip(ids, presencas):
                            cursor.execute(
                                """
                                INSERT INTO confirmacoes (convidado_id, presenca, timestamp) 
                                VALUES (?, ?, ?)
                                """,
                                (convidado_id, presenca, timestamp_sqlite)
                            )
                    else:
                        for convidado_id, presenca in zip(ids, presencas):
                            cursor.execute(
                                """
                                INSERT INTO confirmacoes (convidado_id, presenca) 
                                VALUES (?, ?)
                                """,
                                (convidado_id, presenca)
                            )

                    conn.commit()

                elif "amount" in body and "item_title" in body:
                    titulo = body.get("item_title", "Presente de Casamento")
                    valor = body.get("amount", 0)
                    tipo_pagamento = body.get("payment_type", "Não Informado")
                    transaction_id = body.get("transaction_id", "")
                    nome = body.get("name", "Não Informado")
                    mensagem = body.get("message", "Não Informado")
                    timestamp = body.get("timestamp")
                    timestamp_sqlite = parse_timestamp(timestamp) if timestamp else None

                    if timestamp_sqlite:
                        cursor.execute(
                            """
                            INSERT INTO compras (titulo, valor, tipo_pagamento, transaction_id, nome, mensagem, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (titulo, valor, tipo_pagamento, transaction_id, nome, mensagem, timestamp_sqlite)
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO compras (titulo, valor, tipo_pagamento, transaction_id, nome, mensagem)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (titulo, valor, tipo_pagamento, transaction_id, nome, mensagem)
                        )

                    conn.commit()
                else:
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"message": "Payload inválido."})
                    }
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