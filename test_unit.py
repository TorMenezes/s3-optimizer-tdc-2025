#!/usr/bin/env python3
"""
Testes unitários automatizados para S3 Optimizer
"""

import unittest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Configurar AWS fake
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'fake'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'fake'

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class TestS3Optimizer(unittest.TestCase):
    
    def setUp(self):
        """Setup para cada teste"""
        self.sample_metadata = {
            'file_name': 'test.pdf',
            'file_size': 1048576,  # 1MB
            'file_type': 'pdf',
            'content_type': 'application/pdf',
            'storage_class': 'STANDARD'
        }
        
        self.sample_recommendation = {
            'storage_class': 'STANDARD_IA',
            'reasoning': 'Arquivo PDF de tamanho médio',
            'confidence': 'alta'
        }

    @patch('src.lambda_function.s3_client')
    def test_get_file_metadata(self, mock_s3):
        """Testa extração de metadados"""
        
        mock_response = {
            'ContentLength': 1048576,
            'ContentType': 'application/pdf',
            'LastModified': datetime.now(),
            'StorageClass': 'STANDARD'
        }
        mock_s3.head_object.return_value = mock_response
        
        from src.lambda_function import get_file_metadata
        
        result = get_file_metadata('bucket', 'test.pdf')
        
        self.assertEqual(result['file_name'], 'test.pdf')
        self.assertEqual(result['file_size'], 1048576)
        self.assertEqual(result['file_type'], 'pdf')
        self.assertEqual(result['content_type'], 'application/pdf')

    @patch('src.lambda_function.bedrock_client')
    def test_analyze_with_bedrock_success(self, mock_bedrock):
        """Testa análise com Bedrock - sucesso"""
        
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{
                    'text': json.dumps(self.sample_recommendation)
                }]
            }).encode())
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        from src.lambda_function import analyze_with_bedrock
        
        result = analyze_with_bedrock(self.sample_metadata)
        
        self.assertEqual(result['storage_class'], 'STANDARD_IA')
        self.assertEqual(result['confidence'], 'alta')

    @patch('src.lambda_function.bedrock_client')
    def test_analyze_with_bedrock_fallback(self, mock_bedrock):
        """Testa análise com Bedrock - fallback"""
        
        mock_response = {
            'body': Mock(read=lambda: b'invalid json')
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        from src.lambda_function import analyze_with_bedrock
        
        result = analyze_with_bedrock(self.sample_metadata)
        
        self.assertEqual(result['storage_class'], 'STANDARD_IA')
        self.assertEqual(result['confidence'], 'baixa')

    @patch('src.lambda_function.dynamodb')
    def test_save_insight_to_dynamodb(self, mock_dynamodb):
        """Testa salvamento no DynamoDB"""
        
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        from src.lambda_function import save_insight_to_dynamodb
        
        with patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'}):
            save_insight_to_dynamodb('bucket', 'key', self.sample_metadata, self.sample_recommendation)
        
        mock_table.put_item.assert_called_once()
        
        # Verificar estrutura do item
        call_args = mock_table.put_item.call_args[1]['Item']
        self.assertEqual(call_args['file_id'], 'bucket/key')
        self.assertEqual(call_args['recommended_storage_class'], 'STANDARD_IA')

    @patch('src.lambda_function.dynamodb')
    def test_save_insight_no_table(self, mock_dynamodb):
        """Testa salvamento sem tabela configurada"""
        
        from src.lambda_function import save_insight_to_dynamodb
        
        with patch.dict(os.environ, {}, clear=True):
            # Não deve gerar erro
            save_insight_to_dynamodb('bucket', 'key', self.sample_metadata, self.sample_recommendation)

    @patch('src.lambda_function.s3_client')
    def test_apply_storage_class(self, mock_s3):
        """Testa aplicação da classe de armazenamento"""
        
        from src.lambda_function import apply_storage_class
        
        apply_storage_class('bucket', 'key', self.sample_recommendation, 1048576)
        
        # Verificar copy_object
        mock_s3.copy_object.assert_called_once()
        copy_args = mock_s3.copy_object.call_args[1]
        self.assertEqual(copy_args['StorageClass'], 'STANDARD_IA')
        self.assertEqual(copy_args['Metadata']['file-size-bytes'], '1048576')
        
        # Verificar tagging
        mock_s3.put_object_tagging.assert_called_once()
        tag_args = mock_s3.put_object_tagging.call_args[1]
        tags = {tag['Key']: tag['Value'] for tag in tag_args['Tagging']['TagSet']}
        self.assertEqual(tags['RecommendedClass'], 'STANDARD_IA')
        self.assertEqual(tags['FileSizeBytes'], '1048576')

    @patch('src.lambda_function.s3_client')
    @patch('src.lambda_function.bedrock_client')
    @patch('src.lambda_function.dynamodb')
    def test_lambda_handler_complete(self, mock_dynamodb, mock_bedrock, mock_s3):
        """Teste completo do handler"""
        
        # Setup mocks
        mock_s3.head_object.return_value = {
            'ContentLength': 1048576,
            'ContentType': 'application/pdf',
            'LastModified': datetime.now(),
            'StorageClass': 'STANDARD'
        }
        
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{
                    'text': json.dumps(self.sample_recommendation)
                }]
            }).encode())
        }
        
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Evento de teste
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test.pdf'}
                }
            }]
        }
        
        from src.lambda_function import lambda_handler
        
        with patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'}):
            result = lambda_handler(event, {})
        
        self.assertEqual(result['statusCode'], 200)
        
        # Verificar todas as chamadas
        mock_s3.head_object.assert_called_once()
        mock_bedrock.invoke_model.assert_called_once()
        mock_table.put_item.assert_called_once()
        mock_s3.copy_object.assert_called_once()
        mock_s3.put_object_tagging.assert_called_once()

    def test_size_conversion_logic(self):
        """Testa lógica de conversão de tamanho"""
        
        # Teste com arquivo pequeno (KB)
        small_metadata = self.sample_metadata.copy()
        small_metadata['file_size'] = 50000  # ~49KB
        
        # Teste com arquivo grande (GB)
        large_metadata = self.sample_metadata.copy()
        large_metadata['file_size'] = 2147483648  # 2GB
        
        # Verificar se não gera erro (teste indireto via prompt)
        from src.lambda_function import analyze_with_bedrock
        
        with patch('src.lambda_function.bedrock_client') as mock_bedrock:
            mock_bedrock.invoke_model.return_value = {
                'body': Mock(read=lambda: json.dumps({
                    'content': [{'text': json.dumps(self.sample_recommendation)}]
                }).encode())
            }
            
            # Não deve gerar erro
            analyze_with_bedrock(small_metadata)
            analyze_with_bedrock(large_metadata)

class TestEdgeCases(unittest.TestCase):
    """Testes para casos extremos"""
    
    @patch('src.lambda_function.s3_client')
    @patch('src.lambda_function.bedrock_client')
    @patch('src.lambda_function.dynamodb')
    def test_error_handling(self, mock_dynamodb, mock_bedrock, mock_s3):
        """Testa tratamento de erros"""
        
        # Simular erro no S3
        mock_s3.head_object.side_effect = Exception("S3 Error")
        
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'test.pdf'}
                }
            }]
        }
        
        from src.lambda_function import lambda_handler
        
        # Não deve gerar exceção
        result = lambda_handler(event, {})
        self.assertEqual(result['statusCode'], 200)

    def test_file_without_extension(self):
        """Testa arquivo sem extensão"""
        
        with patch('src.lambda_function.s3_client') as mock_s3:
            mock_s3.head_object.return_value = {
                'ContentLength': 1000,
                'ContentType': 'application/octet-stream',
                'LastModified': datetime.now(),
                'StorageClass': 'STANDARD'
            }
            
            from src.lambda_function import get_file_metadata
            
            result = get_file_metadata('bucket', 'arquivo_sem_extensao')
            self.assertEqual(result['file_type'], 'unknown')

if __name__ == '__main__':
    # Executar testes
    unittest.main(verbosity=2)