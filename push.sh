#!/bin/bash
# ==============================================================================
# SCRIPT DE UPLOAD PARA O GITHUB
# ==============================================================================

# 1. Cole o seu token que começa com "ghp_" entre as aspas abaixo:
TOKEN="COLE_O_SEU_TOKEN_AQUI_DENTRO_DAS_ASPAS"

# ==============================================================================
# Não precisa mexer daqui para baixo
# ==============================================================================

if [ "$TOKEN" == "COLE_O_SEU_TOKEN_AQUI_DENTRO_DAS_ASPAS" ]; then
    echo "❌ ERRO: Você esqueceu de colar o token dentro do arquivo push.sh!"
    exit 1
fi

echo "⏳ Preparando envio para o GitHub..."

# Adiciona todas as modificações recentes (caso tenha feito alguma)
git add .
git commit -m "Upload via script push.sh" 2>/dev/null || true

# Configura o repositório para usar o seu token silenciosamente
git remote set-url origin https://callmepeh:${TOKEN}@github.com/callmepeh/Redes2-Transferencia-de-Arquivos.git

# Faz o upload
echo "🚀 Enviando arquivos..."
if git push origin main; then
    echo "✅ UPLOAD CONCLUÍDO COM SUCESSO!"
else
    echo "❌ ERRO AO ENVIAR. Verifique se o token está correto e tem permissão 'repo'."
fi
