#!/usr/bin/env bash
set -euo pipefail

# Instala uma chave SSH a partir da variável de ambiente SSH_PRIVATE_KEY

if [ -z "${SSH_PRIVATE_KEY:-}" ]; then
  echo "ERRO: defina a variável de ambiente SSH_PRIVATE_KEY com sua chave privada (PEM)."
  echo "Ex: export SSH_PRIVATE_KEY=\"$(cat ~/.ssh/id_ed25519 2>/dev/null)\""
  exit 1
fi

SSH_DIR="$HOME/.ssh"
mkdir -p "$SSH_DIR"
umask 077

PRIVATE_KEY_PATH="$SSH_DIR/id_ed25519"
if [ -f "$PRIVATE_KEY_PATH" ]; then
  echo "Aviso: $PRIVATE_KEY_PATH existe. Será feito backup para ${PRIVATE_KEY_PATH}.bak.$(date +%s)"
  mv "$PRIVATE_KEY_PATH" "${PRIVATE_KEY_PATH}.bak.$(date +%s)"
fi

printf '%s\n' "$SSH_PRIVATE_KEY" > "$PRIVATE_KEY_PATH"
chmod 600 "$PRIVATE_KEY_PATH"

# gera a chave pública a partir da privada
ssh-keygen -y -f "$PRIVATE_KEY_PATH" > "${PRIVATE_KEY_PATH}.pub"
chmod 644 "${PRIVATE_KEY_PATH}.pub"

echo "Chave pública instalada em: ${PRIVATE_KEY_PATH}.pub"
echo
cat "${PRIVATE_KEY_PATH}.pub"
echo

# tenta copiar para clipboard se disponível
if command -v xclip >/dev/null 2>&1; then
  cat "${PRIVATE_KEY_PATH}.pub" | xclip -selection clipboard && echo "Chave pública copiada para a área de transferência."
fi

# inicia ssh-agent e adiciona a chave
if ! pgrep -u "$USER" ssh-agent >/dev/null 2>&1; then
  eval "$(ssh-agent -s)" >/dev/null
fi
ssh-add "$PRIVATE_KEY_PATH" >/dev/null 2>&1 || true

echo
echo "Abra https://github.com/settings/ssh/new e cole a chave pública (se não foi copiada)."
echo "Depois execute: git remote set-url origin git@github.com:callmepeh/Redes2-Transferencia-de-Arquivos.git"
echo "Teste com: ssh -T git@github.com"
