#!/bin/bash

# Script de deploy do S3 Optimizer

set -e

echo "🚀 Iniciando deploy do S3 Optimizer..."

# Verificar se AWS CLI está configurado
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI não configurado. Execute: aws configure"
    exit 1
fi

# Verificar se SAM CLI está instalado
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI não encontrado. Instale: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Parâmetros
STACK_NAME="s3-optimizer-stack"
BUCKET_NAME="${1:-my-s3-optimizer-bucket-$(date +%s)}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo "📦 Bucket: $BUCKET_NAME"
echo "🌍 Região: $REGION"

# Build da aplicação
echo "🔨 Building aplicação..."
sam build -t infrastructure/template.yaml

# Deploy
echo "🚀 Fazendo deploy..."
sam deploy \
    --stack-name $STACK_NAME \
    --parameter-overrides BucketName=$BUCKET_NAME \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --no-confirm-changeset

echo "✅ Deploy concluído!"
echo ""
echo "📋 Informações do deploy:"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "🧪 Para testar, faça upload de um arquivo:"
echo "aws s3 cp arquivo.txt s3://$BUCKET_NAME/"
echo ""
echo "📊 Para ver os insights salvos:"
echo "aws dynamodb scan --table-name s3-optimizer-insights --region $REGION"