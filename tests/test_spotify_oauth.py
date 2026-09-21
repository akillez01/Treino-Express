import httpx

from app.core.config import settings

REDIRECT = "http://localhost:3000/aluno/spotify/callback"


async def test_spotify_config_nao_expoe_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "spotify_client_id", "public-client-id")
    monkeypatch.setattr(settings, "spotify_client_secret", "super-secret")
    monkeypatch.setattr(settings, "spotify_redirect_uri", REDIRECT)
    response = await client.get("/v1/spotify/config")
    assert response.status_code == 200
    assert response.json() == {
        "client_id": "public-client-id",
        "authorize_url": "https://accounts.spotify.com/authorize",
        "redirect_uri": REDIRECT,
        "scopes": settings.spotify_scopes,
        "configured": True,
    }
    assert "super-secret" not in response.text


async def test_spotify_token_pkce_com_mock_transport(client, monkeypatch):
    monkeypatch.setattr(settings, "spotify_client_id", "public-client-id")
    monkeypatch.setattr(settings, "spotify_redirect_uri", REDIRECT)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.api.v1.spotify.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    response = await client.post(
        "/v1/spotify/token",
        json={"code": "code", "code_verifier": "v" * 64, "redirect_uri": REDIRECT},
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == "access-token"
    assert requests[0].content
    assert b"client_secret" not in requests[0].content


async def test_spotify_token_rejeita_redirect_uri(client, monkeypatch):
    monkeypatch.setattr(settings, "spotify_client_id", "public-client-id")
    monkeypatch.setattr(settings, "spotify_redirect_uri", REDIRECT)
    response = await client.post(
        "/v1/spotify/token",
        json={
            "code": "code",
            "code_verifier": "v" * 64,
            "redirect_uri": "https://evil.example/callback",
        },
    )
    assert response.status_code == 400


async def test_spotify_refresh_com_mock_transport(client, monkeypatch):
    monkeypatch.setattr(settings, "spotify_client_id", "public-client-id")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://accounts.spotify.com/api/token")
        return httpx.Response(
            200,
            json={"access_token": "new-access-token", "expires_in": 1800, "token_type": "Bearer"},
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.api.v1.spotify.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    response = await client.post("/v1/spotify/refresh", json={"refresh_token": "refresh-token"})
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "new-access-token",
        "refresh_token": None,
        "expires_in": 1800,
        "token_type": "Bearer",
    }
