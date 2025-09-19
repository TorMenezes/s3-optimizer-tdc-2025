import json
import boto3
import urllib.parse
from datetime import datetime
import os

s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

# Variáveis de ambiente
TABLE_NAME = os.environ.get('DYNAMODB_TABLE')

def lambda_handler(event, context):
    """
    Processa eventos S3 e usa Bedrock para recomendar classe de armazenamento
    """
    
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        
        try:
            # Obter metadados do arquivo
            file_metadata = get_file_metadata(bucket_name, object_key)
            
            # Analisar com Bedrock
            recommendation = analyze_with_bedrock(file_metadata)
            
            # Salvar insight no DynamoDB
            save_insight_to_dynamodb(bucket_name, object_key, file_metadata, recommendation)
            
            # Aplicar recomendação automaticamente
            apply_storage_class(bucket_name, object_key, recommendation, file_metadata['file_size'])
            
            print(f"Processado: {object_key} -> {recommendation['storage_class']}")
            
        except Exception as e:
            print(f"Erro processando {object_key}: {str(e)}")
    
    return {'statusCode': 200}

def get_file_metadata(bucket_name, object_key):
    """Coleta metadados do arquivo S3"""
    
    response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
    
    # Determinar tipo de arquivo
    file_extension = object_key.split('.')[-1].lower() if '.' in object_key else 'unknown'
    
    metadata = {
        'file_name': object_key,
        'file_size': response['ContentLength'],
        'file_type': file_extension,
        'content_type': response.get('ContentType', 'unknown'),
        'last_modified': response['LastModified'].isoformat(),
        'storage_class': response.get('StorageClass', 'STANDARD')
    }
    
    return metadata

def analyze_with_bedrock(file_metadata):
    """Usa Bedrock para analisar arquivo e recomendar classe de armazenamento"""
    
    # Converter tamanho para formato legível
    size_mb = file_metadata['file_size'] / (1024 * 1024)
    size_gb = size_mb / 1024
    
    if size_gb >= 1:
        size_display = f"{size_gb:.2f} GB"
    else:
        size_display = f"{size_mb:.2f} MB"
    
    prompt = f"""
    Analise este arquivo S3 e recomende a classe de armazenamento ideal:

    Arquivo: {file_metadata['file_name']}
    Tamanho: {file_metadata['file_size']} bytes ({size_display})
    Tipo: {file_metadata['file_type']}
    Content-Type: {file_metadata['content_type']}

    Classes disponíveis:
    - STANDARD: Acesso frequente, custo alto por GB
    - STANDARD_IA: Acesso infrequente, custo médio, mínimo 128KB
    - GLACIER: Arquivamento, custo baixo, recuperação em minutos/horas
    - DEEP_ARCHIVE: Arquivamento longo prazo, custo muito baixo, recuperação em 12h

    Considere especialmente:
    - Tamanho do arquivo (arquivos pequenos <128KB não se beneficiam de IA)
    - Tipo de arquivo (logs, backups = GLACIER; documentos = IA; imagens ativas = STANDARD)
    - Padrão de acesso esperado baseado no tipo
    - Custo-benefício por tamanho

    Responda APENAS em JSON:
    {{
        "storage_class": "CLASSE_RECOMENDADA",
        "reasoning": "explicação da recomendação",
        "confidence": "alta/média/baixa"
    }}
    """
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    response = bedrock_client.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=body
    )
    
    result = json.loads(response['body'].read())
    content = result['content'][0]['text']
    
    # Extrair JSON da resposta
    try:
        recommendation = json.loads(content)
        return recommendation
    except:
        # Fallback se não conseguir parsear
        return {
            "storage_class": "STANDARD_IA",
            "reasoning": "Análise padrão aplicada",
            "confidence": "baixa"
        }

def save_insight_to_dynamodb(bucket_name, object_key, file_metadata, recommendation):
    """Salva o insight no DynamoDB"""
    
    if not TABLE_NAME:
        print("DynamoDB table não configurada")
        return
    
    table = dynamodb.Table(TABLE_NAME)
    
    item = {
        'file_id': f"{bucket_name}/{object_key}",
        'bucket_name': bucket_name,
        'object_key': object_key,
        'file_size': file_metadata['file_size'],
        'file_type': file_metadata['file_type'],
        'content_type': file_metadata['content_type'],
        'original_storage_class': file_metadata['storage_class'],
        'recommended_storage_class': recommendation['storage_class'],
        'reasoning': recommendation['reasoning'],
        'confidence': recommendation['confidence'],
        'analyzed_at': datetime.now().isoformat(),
        'ttl': int(datetime.now().timestamp()) + (365 * 24 * 60 * 60)  # 1 ano TTL
    }
    
    table.put_item(Item=item)
    print(f"Insight salvo no DynamoDB: {object_key}")



def apply_storage_class(bucket_name, object_key, recommendation, file_size):
    """Aplica a classe de armazenamento recomendada"""
    
    storage_class = recommendation['storage_class']
    
    # Copiar objeto com nova classe de armazenamento e adicionar tamanho nos metadados
    copy_source = {'Bucket': bucket_name, 'Key': object_key}
    
    s3_client.copy_object(
        CopySource=copy_source,
        Bucket=bucket_name,
        Key=object_key,
        StorageClass=storage_class,
        Metadata={
            'file-size-bytes': str(file_size),
            'optimized-by': 'S3Optimizer',
            'recommended-class': storage_class,
            'confidence': recommendation['confidence'],
            'optimized-at': datetime.now().isoformat()
        },
        MetadataDirective='REPLACE'
    )
    
    # Adicionar tags com informações da análise
    s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=object_key,
        Tagging={
            'TagSet': [
                {'Key': 'OptimizedBy', 'Value': 'S3Optimizer'},
                {'Key': 'RecommendedClass', 'Value': storage_class},
                {'Key': 'Confidence', 'Value': recommendation['confidence']},
                {'Key': 'OptimizedAt', 'Value': datetime.now().isoformat()},
                {'Key': 'FileSizeBytes', 'Value': str(file_size)}
            ]
        }
    )
    print(f"Classe de armazenamento aplicada: {storage_class}")