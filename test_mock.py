#!/usr/bin/env python3
"""
Teste mocado do S3 Optimizer - não requer conta AWS
"""

import json
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Configurar região AWS para evitar erro
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'fake'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'fake'

# Adicionar src ao path para importar lambda_function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def create_mock_s3_event():
    """Cria evento S3 mocado"""
    return {
        'Records': [
            {
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'documento.pdf'}
                }
            }
        ]
    }

def create_mock_head_object_response():
    """Cria resposta mocada do head_object"""
    return {
        'ContentLength': 2048000,  # 2MB
        'ContentType': 'application/pdf',
        'LastModified': datetime.now(),
        'StorageClass': 'STANDARD'
    }

def create_mock_bedrock_response():
    """Cria resposta mocada do Bedrock"""
    return {
        'body': Mock(read=lambda: json.dumps({
            'content': [{
                'text': json.dumps({
                    "storage_class": "STANDARD_IA",
                    "reasoning": "Documento PDF de 2MB, acesso infrequente esperado",
                    "confidence": "alta"
                })
            }]
        }).encode())
    }

@patch('src.lambda_function.s3_client')
@patch('src.lambda_function.bedrock_client')
@patch('src.lambda_function.dynamodb')
def test_lambda_handler_mock(mock_dynamodb, mock_bedrock, mock_s3):
    """Teste completo da função Lambda com mocks"""
    
    # Configurar mocks
    mock_s3.head_object.return_value = create_mock_head_object_response()
    mock_bedrock.invoke_model.return_value = create_mock_bedrock_response()
    
    mock_table = Mock()
    mock_dynamodb.Table.return_value = mock_table
    
    # Importar após configurar mocks
    from src.lambda_function import lambda_handler
    
    # Executar teste
    event = create_mock_s3_event()
    context = {}
    
    with patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'}):
        result = lambda_handler(event, context)
    
    # Verificar resultado
    assert result['statusCode'] == 200
    
    # Verificar chamadas
    mock_s3.head_object.assert_called_once()
    mock_bedrock.invoke_model.assert_called_once()
    mock_table.put_item.assert_called_once()
    mock_s3.copy_object.assert_called_once()
    mock_s3.put_object_tagging.assert_called_once()
    
    print("✅ Teste lambda_handler passou!")

def test_get_file_metadata_mock():
    """Teste da função get_file_metadata"""
    
    with patch('src.lambda_function.s3_client') as mock_s3:
        mock_s3.head_object.return_value = create_mock_head_object_response()
        
        from src.lambda_function import get_file_metadata
        
        metadata = get_file_metadata('test-bucket', 'documento.pdf')
        
        assert metadata['file_name'] == 'documento.pdf'
        assert metadata['file_size'] == 2048000
        assert metadata['file_type'] == 'pdf'
        assert metadata['content_type'] == 'application/pdf'
        
        print("✅ Teste get_file_metadata passou!")

def test_analyze_with_bedrock_mock():
    """Teste da função analyze_with_bedrock"""
    
    with patch('src.lambda_function.bedrock_client') as mock_bedrock:
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response()
        
        from src.lambda_function import analyze_with_bedrock
        
        file_metadata = {
            'file_name': 'documento.pdf',
            'file_size': 2048000,
            'file_type': 'pdf',
            'content_type': 'application/pdf'
        }
        
        recommendation = analyze_with_bedrock(file_metadata)
        
        assert recommendation['storage_class'] == 'STANDARD_IA'
        assert recommendation['confidence'] == 'alta'
        assert 'reasoning' in recommendation
        
        print("✅ Teste analyze_with_bedrock passou!")

def test_save_insight_to_dynamodb_mock():
    """Teste da função save_insight_to_dynamodb"""
    
    with patch('src.lambda_function.dynamodb') as mock_dynamodb:
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        from src.lambda_function import save_insight_to_dynamodb
        
        file_metadata = {
            'file_name': 'documento.pdf',
            'file_size': 2048000,
            'file_type': 'pdf',
            'content_type': 'application/pdf',
            'storage_class': 'STANDARD'
        }
        
        recommendation = {
            'storage_class': 'STANDARD_IA',
            'reasoning': 'Teste',
            'confidence': 'alta'
        }
        
        # Configurar variável de ambiente antes de importar
        with patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'}):
            # Reimportar para pegar nova variável
            import importlib
            import src.lambda_function
            importlib.reload(src.lambda_function)
            
            src.lambda_function.save_insight_to_dynamodb('test-bucket', 'documento.pdf', file_metadata, recommendation)
        
        mock_table.put_item.assert_called_once()
        
        print("✅ Teste save_insight_to_dynamodb passou!")

def test_apply_storage_class_mock():
    """Teste da função apply_storage_class"""
    
    with patch('src.lambda_function.s3_client') as mock_s3:
        from src.lambda_function import apply_storage_class
        
        recommendation = {
            'storage_class': 'STANDARD_IA',
            'confidence': 'alta'
        }
        
        apply_storage_class('test-bucket', 'documento.pdf', recommendation, 2048000)
        
        mock_s3.copy_object.assert_called_once()
        mock_s3.put_object_tagging.assert_called_once()
        
        # Verificar parâmetros do copy_object
        copy_call = mock_s3.copy_object.call_args
        assert copy_call[1]['StorageClass'] == 'STANDARD_IA'
        assert copy_call[1]['Metadata']['file-size-bytes'] == '2048000'
        
        print("✅ Teste apply_storage_class passou!")

def run_all_tests():
    """Executa todos os testes"""
    
    print("🧪 Executando testes mocados do S3 Optimizer...\n")
    
    try:
        test_get_file_metadata_mock()
        test_analyze_with_bedrock_mock()
        test_save_insight_to_dynamodb_mock()
        test_apply_storage_class_mock()
        test_lambda_handler_mock()
        
        print("\n🎉 Todos os testes passaram!")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)