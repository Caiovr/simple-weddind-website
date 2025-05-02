import json
import requests
import boto3
from botocore.exceptions import ClientError

def get_AWS_secrets():

    secret_name = "weddingWebSiteSecrets"
    region_name = 'us-east-1'

    # Create a Secrets Manager client
    session = boto3.session.Session()
   
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
       
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    return json.loads(get_secret_value_response['SecretString'])
    

def lambda_handler(event, context):
    # Parse input from API Gateway
    #body = json.loads(event['body'])
    body = event['body']

    secrets = get_AWS_secrets()
    
    # Prepare Mercado Pago request
    mp_url = 'https://api.mercadopago.com/checkout/preferences'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {secrets.get('MERCADO_PAGO_ACCESS_TOKEN')}'
    }
    
    payload = {
        'items': [{
            'title': body.get('item_title', 'Presente de Casamento'),
            'quantity': 1,
            'currency_id': body.get('currency', 'BRL'),
            'unit_price': float(body['amount'])
        }],
        'back_urls': {
            'success': body.get('success_url'),
            'failure': body.get('failure_url'),
            'pending': body.get('pending_url')
        },
        'auto_return': 'approved'
    }
    
    try:
        # Call Mercado Pago API
        response = requests.post(mp_url, headers=headers, json=payload)
        response.raise_for_status()
        
        return {
            'statusCode': 200,
            'body': json.dumps(response.json())
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
## Test
# print(lambda_handler({'method': 'POST',
#                             'headers': {
#                                 'Content-Type': 'application/json'
#                             },
#                             'body': {
#                                 'amount': 1000,
#                                 'item_title': 'Presente de Casamento',
#                                 'currency': 'BRL',
#                                 'success_url': 'https://jadsmilaecaio.com.br/success',
#                                 'failure_url': 'https://jadsmilaecaio.com.br/failure',
#                                 'pending_url': 'https://jadsmilaecaio.com.br/pending'
#                             }}
#                         , ""
#                     ))