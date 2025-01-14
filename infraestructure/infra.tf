# Variables
variable "region" {
  default = "us-east-1"
}

provider "aws" {
  region = var.region
}

# S3 Bucket for Static Website
data  "aws_s3_bucket" "static_website" {
  bucket = "project-simple-wedding-website"
}

# S3 Private Bucket for Static Website
resource "aws_s3_bucket" "sqlite_db_bucket" {
  bucket = "sqlite-db-project-sww"
  acl    = "private"
}

resource "random_id" "bucket_id" {
  byte_length = 4
}

# Lambda Role
resource "aws_iam_role" "lambda_role" {
  name = "wedding-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name = "wedding-lambda-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Resource = aws_sqs_queue.confirmation_queue.arn
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:HeadObject",
          "s3:PutObjectAcl",
          "s3:GetObjectAcl"
        ],
        Resource = [
          "${data.aws_s3_bucket.static_website.arn}/*", 
          "${data.aws_s3_bucket.static_website.arn}", 
          "${aws_s3_bucket.sqlite_db_bucket.arn}",
          "${aws_s3_bucket.sqlite_db_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_role_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# SQS Queue
resource "aws_sqs_queue" "confirmation_queue" {
  name = "wedding-confirmation-queue"
}

# Zip Lambda files
data "archive_file" "lambda_save_confirmation_zip" {
  type         = "zip"
  source_file  = "${path.module}/../lambda/saveConfirmations.py"
  output_path  = "${path.module}/../lambda/saveConfirmations.zip"
}

data "archive_file" "lambda_get_convidados_zip" {
  type         = "zip"
  source_file  = "${path.module}/../lambda/getConvidados.py"
  output_path  = "${path.module}/../lambda/getConvidados.zip"
}

data "archive_file" "lambda_send_to_sqs" {
  type         = "zip"
  source_file  = "${path.module}/../lambda/sendToSQS.py"
  output_path  = "${path.module}/../lambda/sendToSQS.zip"
}

# data "archive_file" "lambda_options_zip" {
#   type         = "zip"
#   source_file  = "${path.module}/../lambda/optionsLambda.py"
#   output_path  = "${path.module}/../lambda/optionsLambda.zip"
# }

# Lambda Function: get-convidados
resource "aws_lambda_function" "get_convidados" {
  function_name    = "get-convidados"
  role             = aws_iam_role.lambda_role.arn
  handler          = "getConvidados.lambda_handler"
  runtime          = "python3.12"
  timeout          = 10
  filename         = data.archive_file.lambda_get_convidados_zip.output_path
  source_code_hash = data.archive_file.lambda_get_convidados_zip.output_base64sha256

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.sqlite_db_bucket.id
      DB_NAME = "wedding.db"
    }
  }
}

# Lambda Function: post-confirmacao
resource "aws_lambda_function" "post_confirmacao" {
  function_name    = "post-confirmacao"
  role             = aws_iam_role.lambda_role.arn
  handler          = "sendToSQS.lambda_handler"
  runtime          = "python3.12"
  timeout          = 10
  filename         = data.archive_file.lambda_send_to_sqs.output_path
  source_code_hash = data.archive_file.lambda_send_to_sqs.output_base64sha256

  environment {
    variables = {
      SQS_QUEUE = aws_sqs_queue.confirmation_queue.url
    }
  }
}

# Lambda saveConfirmations
resource "aws_lambda_function" "save_confirmations" {
  function_name    = "save-confirmations"
  role             = aws_iam_role.lambda_role.arn
  handler          = "saveConfirmations.lambda_handler"
  runtime          = "python3.12"
  timeout          = 10
  filename         = data.archive_file.lambda_save_confirmation_zip.output_path
  source_code_hash = data.archive_file.lambda_save_confirmation_zip.output_base64sha256

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.sqlite_db_bucket.id
      SQS_QUEUE = aws_sqs_queue.confirmation_queue.url
      DB_NAME = "wedding.db"
    }
  }
}

# Lambda options
# resource "aws_lambda_function" "options_lambda" {
#   function_name = "options_lambda"
#   role             = aws_iam_role.lambda_role.arn
#   handler          = "optionsLambda.lambda_handler"
#   runtime          = "python3.12"
#   filename         = data.archive_file.lambda_options_zip.output_path
#   source_code_hash = data.archive_file.lambda_options_zip.output_base64sha256

# }

# API Gateway
resource "aws_apigatewayv2_api" "wedding_website_api" {
  name          = "Wedding Website API"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"] # Replace "*" with your website domain for stricter security (e.g., "https://your-website.com")
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }
}

resource "aws_iam_role" "apigateway_role" {
  name               = "ApiGatewaySqsRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "apigateway.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "apigateway_sqs_policy" {
  name = "ApiGatewaySQSPolicy"
  role = aws_iam_role.apigateway_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = "sqs:SendMessage",
        Resource = aws_sqs_queue.confirmation_queue.arn
      }
    ]
  })
}

# Routes for API Gateway
resource "aws_apigatewayv2_route" "get_convidados_route" {
  api_id    = aws_apigatewayv2_api.wedding_website_api.id
  route_key = "GET /get-convidados"
  target    = "integrations/${aws_apigatewayv2_integration.get_convidados_integration.id}"
}

resource "aws_apigatewayv2_route" "post_confirmacao_route" {
  api_id    = aws_apigatewayv2_api.wedding_website_api.id
  route_key = "POST /post-confirmacao"
  target    = "integrations/${aws_apigatewayv2_integration.post_confirmacao_integration.id}"
}

resource "aws_apigatewayv2_route" "options_route" {
  api_id    = aws_apigatewayv2_api.wedding_website_api.id
  route_key = "OPTIONS /get-convidados"
  
  target = "integrations/${aws_apigatewayv2_integration.get_convidados_integration.id}"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id          = aws_apigatewayv2_api.wedding_website_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.get_convidados.arn
}

# Integrations for API Gateway (Connect Routes to Lambda Functions)
resource "aws_apigatewayv2_integration" "get_convidados_integration" {
  api_id             = aws_apigatewayv2_api.wedding_website_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.get_convidados.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_integration" "post_confirmacao_integration" {
  api_id             = aws_apigatewayv2_api.wedding_website_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.post_confirmacao.invoke_arn
  integration_method = "POST"
}

# resource "aws_apigatewayv2_integration" "sqs_integration" {
#   api_id                 = aws_apigatewayv2_api.wedding_website_api.id
#   integration_type       = "AWS_PROXY"
#   integration_uri        = "arn:aws:apigateway:${var.region}:sqs:path/${aws_sqs_queue.confirmation_queue.name}"
#   credentials_arn        = aws_iam_role.apigateway_role.arn
#   payload_format_version = "2.0"
# }

# Deployment for API Gateway
resource "aws_apigatewayv2_stage" "api_stage" {
  api_id      = aws_apigatewayv2_api.wedding_website_api.id
  name        = "prod"
  auto_deploy = true

  default_route_settings {
    throttling_rate_limit  = 10    # Maximum number of requests per second
    throttling_burst_limit = 5     # Number of requests in a short time period
  }
}

output "api_gateway_url" {
  value = "https://${aws_apigatewayv2_api.wedding_website_api.api_endpoint}/prod"
}

# Permissions for API Gateway to Invoke Lambda Functions
resource "aws_lambda_permission" "allow_get_convidados" {
  statement_id  = "AllowGetConvidados"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_convidados.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.wedding_website_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "allow_post_confirmacao" {
  statement_id  = "AllowPostConfirmacao"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.post_confirmacao.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.wedding_website_api.execution_arn}/*/*"
}

# Lambda trigger event for sqs
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.confirmation_queue.arn
  function_name    = aws_lambda_function.save_confirmations.arn
  batch_size       = 10
  enabled          = true
}