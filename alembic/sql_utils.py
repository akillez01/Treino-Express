"""Splitter de statements SQL respeitando dollar-quoting (`$$...$$`,
`$tag$...$tag$`), aspas simples e comentários `--`.

Necessário porque o dialeto asyncpg do SQLAlchemy sempre prepara o statement
(protocolo estendido) mesmo via `exec_driver_sql` — ele não cai para o
protocolo simples do Postgres, que é o único que aceita múltiplos comandos
numa só mensagem. Sem isso, `bind.exec_driver_sql(sql_com_varios_comandos)`
falha com `cannot insert multiple commands into a prepared statement`.
"""

import re

_DOLLAR_TAG_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(sql)
    dollar_tag: str | None = None  # None = fora de bloco $$; senão guarda a tag

    while i < n:
        ch = sql[i]

        if dollar_tag is not None:
            close = f"${dollar_tag}$"
            end = sql.find(close, i)
            if end == -1:
                buf.append(sql[i:])
                i = n
                break
            buf.append(sql[i : end + len(close)])
            i = end + len(close)
            dollar_tag = None
            continue

        if ch == "-" and sql[i : i + 2] == "--":
            end = sql.find("\n", i)
            end = n if end == -1 else end
            buf.append(sql[i:end])
            i = end
            continue

        if ch == "'":
            end = i + 1
            while end < n:
                if sql[end] == "'" and sql[end : end + 2] != "''":
                    break
                end += 2 if sql[end : end + 2] == "''" else 1
            end = min(end + 1, n)
            buf.append(sql[i:end])
            i = end
            continue

        if ch == "$":
            m = _DOLLAR_TAG_RE.match(sql, i)
            if m:
                dollar_tag = m.group(1) or ""
                buf.append(m.group(0))
                i = m.end()
                continue

        if ch == ";":
            buf.append(ch)
            stmt = "".join(buf).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)

    return statements
