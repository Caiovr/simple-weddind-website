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

# SQS Queue
resource "aws_sqs_queue" "confirmation_queue" {
  name = "wedding-confirmation-queue"
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
          "s3:PutObject"
        ],
        Resource = [
          "${data.aws_s3_bucket.static_website.arn}/*", 
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

data "archive_file" "lambda_save_confirmation_zip" {
  type         = "zip"
  source_file  = "${path.module}/../lambda/saveConfirmation.py"
  output_path  = "${path.module}/../lambda/saveConfirmation.zip"
}

# Lambda Function
resource "aws_lambda_function" "confirmation_handler" {
  function_name = "wedding-confirmation-handler"
  role          = aws_iam_role.lambda_role.arn
  runtime       = "python3.9"
  handler       = "lambda_function.lambda_handler"
  filename      = "../lambda/saveConfirmation.zip" # Replace with your Lambda deployment package

  environment {
    variables = {
      S3_BUCKET = data.aws_s3_bucket.static_website.id
      SQS_QUEUE = aws_sqs_queue.confirmation_queue.url
      DB_NAME = "wedding.db"
    }
  }
}

# API Gateway
resource "aws_apigatewayv2_api" "wedding_website_api" {
  name          = "Wedding Website API"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.wedding_website_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.confirmation_handler.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_confirm" {
  api_id    = aws_apigatewayv2_api.wedding_website_api.id
  route_key = "POST /confirm"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.wedding_website_api.id
  name        = "$default"
  auto_deploy = true
}

# Permissions for API Gateway to invoke Lambda
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.confirmation_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.wedding_website_api.execution_arn}/*/*"
}
