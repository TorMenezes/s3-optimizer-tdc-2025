#!/usr/bin/env python3
"""
Script para testar o S3 Optimizer fazendo upload de arquivos de teste
"""

import boto3
import json
import time
from datetime import datetime

def create_test_files():
    """Cria arquivos de teste com diferentes características"""
    
    test_files = [
        {
            'name': 'documento.pdf',
            'content': b'%PDF-1.4 Documento de teste para arquivamento',
            'description': 'Documento PDF para teste'
        },
        {
            'name': 'backup.zip',
            'content': b'PK\x03\x04 Arquivo de backup compactado',
            'description': 'Arquivo de backup'
        },
        {
            'name': 'log_aplicacao.txt',
            'content': b'2024-01-01 10:00:00 INFO Aplicacao iniciada\n' * 100,
            'description': 'Log de aplicação'
        },
        {
            'name': 'imagem.jpg',
            'content': b'\xff\xd8\xff\xe0 JFIF Imagem de teste',
            'description': 'Imagem JPEG'
        }
    ]
    
    return test_files

def upload_test_files(bucket_name):
    """Faz upload dos arquivos de teste"""
    
    s3_client = boto3.client('s3')
    test_files = create_test_files()
    
    print(f"📤 Fazendo upload de {len(test_files)} arquivos de teste...")
    
    for file_info in test_files:
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_info['name'],
                Body=file_info['content'],
                Metadata={
                    'description': file_info['description'],
                    'test-file': 'true'
                }
            )
            print(f"✅ Upload: {file_info['name']}")
            time.sleep(2)  # Aguardar processamento
            
        except Exception as e:
            print(f"❌ Erro no upload {file_info['name']}: {e}")

def check_insights(table_name):
    """Verifica os insights gerados no DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    print(f"\n📊 Verificando insights na tabela {table_name}...")
    
    try:
        response = table.scan()
        items = response['Items']
        
        if not items:
            print("❌ Nenhum insight encontrado")
            return
        
        print(f"✅ Encontrados {len(items)} insights:")
        
        for item in items:
            print(f"\n📁 Arquivo: {item['object_key']}")
            print(f"   Tamanho: {item['file_size']} bytes")
            print(f"   Classe original: {item['original_storage_class']}")
            print(f"   Classe recomendada: {item['recommended_storage_class']}")
            print(f"   Confiança: {item['confidence']}")
            print(f"   Razão: {item['reasoning']}")
            
    except Exception as e:
        print(f"❌ Erro ao verificar insights: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python test_upload.py <bucket-name> [table-name]")
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    table_name = sys.argv[2] if len(sys.argv) > 2 else "s3-optimizer-insights"
    
    print(f"🧪 Testando S3 Optimizer")
    print(f"📦 Bucket: {bucket_name}")
    print(f"📊 Tabela: {table_name}")
    
    # Upload dos arquivos
    upload_test_files(bucket_name)
    
    # Aguardar processamento
    print("\n⏳ Aguardando processamento (30 segundos)...")
    time.sleep(30)
    
    # Verificar insights
    check_insights(table_name)