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

    # Conecta ao banco de dados
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    endpoint = event["rawPath"]

    match endpoint:
        case  "/get-convidados":
            # Busca os convidados
            cursor.execute("SELECT id, convidado FROM convidados ORDER BY id ASC")
            table = [{"id": row[0], "convidado": row[1]} for row in cursor.fetchall()]
            conn.close()
        case "/get-confirmacoes":
            # Busca as confirmações
            cursor.execute("""
            SELECT 
                t.convidado_id, 
                t2.convidado, 
                t.presenca, 
                t.timestamp 
            FROM confirmacoes as t 
                INNER JOIN (
                    SELECT 
                        convidado_id, 
                        MAX(timestamp) as max_timestamp 
                    FROM confirmacoes 
                    GROUP BY convidado_id
                ) as t_max ON t.convidado_id = t_max.convidado_id AND t.timestamp = t_max.max_timestamp
                LEFT JOIN convidados as t2 ON t.convidado_id = t2.id
            WHERE t.presenca = 'sim'
            """)
            results = cursor.fetchall()
            table = [{"convidado_id": row[0], "convidado": row[1], "presenca": row[2], "timestamp": row[3]} for row in results]
            conn.close()
        case "/get-compras":
            # Busca as compras
            cursor.execute("""
                        SELECT 
                            t.id,
                            t.titulo,
                            t.valor,
                            t.tipo_pagamento,
                            t.nome,
                            t.mensagem,
                            t.timestamp
                        FROM compras AS t
            """)
            results = cursor.fetchall()
            table = [{
                "id": row[0], 
                "titulo": row[1], 
                "valor": row[2], 
                "tipo_pagamento": row[3], 
                "nome": row[4], 
                "mensagem": row[5], 
                "timestamp": row[6]
                } for row in results]
            conn.close()
        case "/get-pending-confirmations":
            # Busca as confirmações pendentes
            cursor.execute("""
                with confs as (
                    SELECT 
                        t.convidado_id,  
                        t.presenca, 
                        t.timestamp 
                        FROM confirmacoes as t 
                            inner join (
                                SELECT 
                                    convidado_id, 
                                    MAX(timestamp) as max_timestamp 
                                FROM confirmacoes 
                                GROUP BY convidado_id
                            ) as t_max on t.convidado_id = t_max.convidado_id and t.timestamp = t_max.max_timestamp
                    )
                    select
                        t.convidado,
                        t.origem,
                        t.telefone,
                        t2.presenca
                    from convidados as t
                    left join confs as t2 on t2.convidado_id = t.id
                    where t2.presenca is null
                """)
            results = cursor.fetchall()
            table = [{"convidado": row[0], "origem": row[1], "telefone": row[2], "presenca": row[3]} for row in results]
            conn.close()

    return {
        "statusCode": 200,
        "body": json.dumps(table),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    }