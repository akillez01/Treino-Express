"""Gera um JWT de aluno para testes manuais (curl/httpx) — não é um endpoint
de produção, só uma ferramenta de dev enquanto o fluxo de login real não
existe.

Uso:
    uv run python scripts/gerar_token_dev.py <academia_id> <aluno_id>
"""

import sys
import uuid

from app.core.security import create_access_token

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)
    academia_id, aluno_id = uuid.UUID(sys.argv[1]), uuid.UUID(sys.argv[2])
    token = create_access_token(
        subject=str(aluno_id), type="aluno", academia_id=academia_id, aluno_id=aluno_id
    )
    print(token)
