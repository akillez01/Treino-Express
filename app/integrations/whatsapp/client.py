"""Envio de mensagens pela WhatsApp Business Cloud API.

Mensagens iniciadas pela empresa exigem um *template* aprovado pela Meta. O
template esperado (WHATSAPP_TEMPLATE, padrão `lembrete_sequencia`, pt_BR) tem 3
variáveis no corpo, nesta ordem: {{1}} nome, {{2}} dias da sequência, {{3}} link.

Sem WHATSAPP_TOKEN e WHATSAPP_PHONE_NUMBER_ID nada é enviado: o lembrete fica
registrado como "simulado" (útil em desenvolvimento e demonstração)."""

import httpx

from app.core.config import settings

GRAPH = "https://graph.facebook.com/v21.0"


class WhatsAppErro(Exception):
    pass


def configurado() -> bool:
    return bool(settings.whatsapp_token and settings.whatsapp_phone_number_id)


def normalizar_telefone(bruto: str) -> str | None:
    """Só dígitos, com DDI. Aceita BR sem 55 (10 ou 11 dígitos)."""
    d = "".join(c for c in bruto if c.isdigit())
    if len(d) in (10, 11):
        d = "55" + d
    return d if 12 <= len(d) <= 13 and d.startswith("55") else None


async def enviar_template(telefone: str, variaveis: list[str]) -> str:
    """Envia o template e devolve o id da mensagem na Meta."""
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": {
            "name": settings.whatsapp_template,
            "language": {"code": "pt_BR"},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": v} for v in variaveis]}
            ],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.post(
                f"{GRAPH}/{settings.whatsapp_phone_number_id}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
            )
    except httpx.HTTPError as exc:
        raise WhatsAppErro("Não foi possível falar com o WhatsApp") from exc
    if r.status_code >= 400:
        detalhe = r.json().get("error", {}).get("message", r.text[:120]) if r.content else ""
        raise WhatsAppErro(f"WhatsApp recusou ({r.status_code}): {detalhe}")
    return r.json()["messages"][0]["id"]
