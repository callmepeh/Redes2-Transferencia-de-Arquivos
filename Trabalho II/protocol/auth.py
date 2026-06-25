import hashlib

# Dados do aluno — usados para gerar o campo X-Custom-Auth
# SHA-256(Matrícula + Nome), conforme exigido pelo PDF da avaliação.
MATRICULA = "20239017876"
NOME = "Pedro Henrique de Carvalho Sousa"

def get_auth_hash() -> str:
    """Gera o Hash SHA-256 de (Matrícula + Nome), conforme o enunciado."""
    data = MATRICULA + NOME
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
