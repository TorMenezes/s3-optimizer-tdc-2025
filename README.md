# AWS S3 Orquestrador e Otimizador

Sistema serverless que monitora uploads em buckets S3 e usa Amazon Bedrock para analisar arquivos e recomendar a classe de armazenamento ideal.

## 🧪 Testes Disponíveis

### 1. Demo Simples (Sem AWS)
```bash
python3 demo_test.py
```
Demonstra o funcionamento completo sem precisar de conta AWS.

### 2. Testes Mocados
```bash
python3 test_mock.py
```
Testes com mocks das APIs AWS.

### 3. Testes Unitários
```bash
python3 test_unit.py
```
Testes automatizados completos com unittest.

### 4. Executar Todos os Testes
```bash
./run_tests.sh
```

## ✅ Funcionalidades Testadas

- ✅ **Extração de metadados** do S3
- ✅ **Análise com Bedrock** para recomendação
- ✅ **Salvamento de insights** no DynamoDB  
- ✅ **Aplicação automática** da classe recomendada
- ✅ **Tratamento de erros** e casos extremos
- ✅ **Conversão de tamanhos** (bytes → MB/GB)
- ✅ **Metadados enriquecidos** com tamanho do arquivo

## Arquitetura

```
S3 Bucket → Lambda → Bedrock → DynamoDB + S3 (nova classe)
```

## Deploy Rápido

```bash
./deploy.sh meu-bucket-s3
```

## Estrutura do Projeto

```
s3-optimizer/
├── src/
│   └── lambda_function.py      # Função Lambda principal
├── infrastructure/
│   └── template.yaml           # CloudFormation template
├── deploy.sh                   # Script de deploy
├── demo_test.py               # Demo sem AWS
├── test_mock.py               # Testes mocados
├── test_unit.py               # Testes unitários
├── run_tests.sh               # Executar todos os testes
└── README.md                  # Este arquivo
```

## Recursos Criados

- **S3 Bucket**: Para monitoramento de uploads
- **Lambda Function**: Processamento de eventos
- **DynamoDB Table**: Armazenamento de insights
- **IAM Role**: Permissões necessárias
- **CloudWatch Logs**: Monitoramento e debug

## Funcionamento

1. **Upload**: Arquivo é enviado para o bucket S3
2. **Evento**: S3 dispara evento `ObjectCreated:Put`
3. **Lambda**: Função é executada automaticamente
4. **Análise**: Bedrock analisa o arquivo e recomenda classe
5. **Armazenamento**: Insight é salvo no DynamoDB
6. **Aplicação**: Classe de armazenamento é alterada automaticamente
7. **Metadados**: Tamanho do arquivo é adicionado aos metadados

## Exemplo de Recomendação

```json
{
  "storage_class": "STANDARD_IA",
  "reasoning": "Documento PDF de 2.0 MB, acesso infrequente esperado",
  "confidence": "alta"
}
```

## Tag

'''q-developer-quest-tdc-2025'''
    
## Monitoramento

- **CloudWatch Logs**: `/aws/lambda/s3-optimizer-function`
- **DynamoDB**: Tabela `s3-optimizer-insights`
- **S3 Tags**: Metadados da otimização nos objetos
