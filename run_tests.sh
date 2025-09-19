#!/bin/bash

echo "🧪 Executando testes do S3 Optimizer..."

# Instalar dependências de teste se necessário
if ! python -c "import pytest" 2>/dev/null; then
    echo "📦 Instalando dependências de teste..."
    pip install -r requirements-test.txt
fi

echo ""
echo "🔍 Teste mocado simples:"
python test_mock.py

echo ""
echo "🔬 Testes unitários completos:"
python -m pytest test_unit.py -v

echo ""
echo "📊 Cobertura de código:"
python -m coverage run -m pytest test_unit.py
python -m coverage report -m

echo ""
echo "✅ Testes concluídos!"