from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.api.v1 import auth
from app.core.config import settings


@pytest.fixture
def google_settings(monkeypatch):
    monkeypatch.setattr(settings, "google_login_enabled", True)
    monkeypatch.setattr(settings, "google_client_id", "google-client-id")
    monkeypatch.setattr(settings, "google_allowed_hosted_domain", "")
    monkeypatch.setattr(settings, "google_default_academia_id", str(uuid4()))


def claims(**overrides):
    value = {
        "aud": "google-client-id",
        "iss": "https://accounts.google.com",
        "email": "aluno@example.com",
        "email_verified": "true",
        "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
    }
    value.update(overrides)
    return value


def patch_tokeninfo(monkeypatch, payload, status_code=200):
    real_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload, request=request)

    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.asyncio
async def test_google_credential_rejeita_audience_invalida(monkeypatch, google_settings):
    patch_tokeninfo(monkeypatch, claims(aud="outro-app"))
    with pytest.raises(auth.HTTPException) as error:
        await auth._verify_google_credential("id-token")
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_google_credential_rejeita_email_nao_verificado(monkeypatch, google_settings):
    patch_tokeninfo(monkeypatch, claims(email_verified="false"))
    with pytest.raises(auth.HTTPException) as error:
        await auth._verify_google_credential("id-token")
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_google_credential_rejeita_expirada(monkeypatch, google_settings):
    patch_tokeninfo(monkeypatch, claims(exp=1))
    with pytest.raises(auth.HTTPException) as error:
        await auth._verify_google_credential("id-token")
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_google_login_emite_token_para_aluno_correspondente(monkeypatch, google_settings):
    aluno = SimpleNamespace(id=uuid4(), academia_id=settings.google_default_academia_id)
    patch_tokeninfo(monkeypatch, claims())

    class ScalarResult:
        def all(self):
            return [aluno]

    class FakeDb:
        async def execute(self, _query):
            return None

        async def scalars(self, _query):
            return ScalarResult()

    @asynccontextmanager
    async def fake_tenant_session(_academia_id):
        yield FakeDb()

    monkeypatch.setattr(auth, "tenant_session", fake_tenant_session)
    response = await auth.login_google(auth.GoogleCredentialIn(credential="id-token"))
    assert response.access_token
    assert response.aluno_id == str(aluno.id)


@pytest.mark.asyncio
async def test_google_login_rejeita_aluno_ausente(monkeypatch, google_settings):
    patch_tokeninfo(monkeypatch, claims())

    class ScalarResult:
        def all(self):
            return []

    class FakeDb:
        async def execute(self, _query):
            return None

        async def scalars(self, _query):
            return ScalarResult()

    @asynccontextmanager
    async def fake_tenant_session(_academia_id):
        yield FakeDb()

    monkeypatch.setattr(auth, "tenant_session", fake_tenant_session)
    with pytest.raises(auth.HTTPException) as error:
        await auth.login_google(auth.GoogleCredentialIn(credential="id-token"))
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_google_login_rejeita_alunos_ambiguos(monkeypatch, google_settings):
    patch_tokeninfo(monkeypatch, claims())
    alunos = [
        SimpleNamespace(id=uuid4(), academia_id=settings.google_default_academia_id)
        for _ in range(2)
    ]

    class ScalarResult:
        def all(self):
            return alunos

    class FakeDb:
        async def execute(self, _query):
            return None

        async def scalars(self, _query):
            return ScalarResult()

    @asynccontextmanager
    async def fake_tenant_session(_academia_id):
        yield FakeDb()

    monkeypatch.setattr(auth, "tenant_session", fake_tenant_session)
    with pytest.raises(auth.HTTPException) as error:
        await auth.login_google(auth.GoogleCredentialIn(credential="id-token"))
    assert error.value.status_code == 409
