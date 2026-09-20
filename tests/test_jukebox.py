"""Jukebox + Spotify. O Spotify é simulado: nenhum teste depende de credenciais."""

import httpx
import pytest

from app.integrations.spotify import client as spotify
from tests.conftest import auth_header

ID_A = "4uLU6hMCjMI75M1A2tKUQC"
ID_B = "3n3Ppam7vgaVa1iaRUc9Lp"


def _faixa(spotify_id: str, titulo: str) -> spotify.Faixa:
    return spotify.Faixa(
        id=spotify_id,
        titulo=titulo,
        artista="Artista",
        duracao_segundos=200,
        capa_url=None,
        explicita=False,
    )


@pytest.fixture
def spotify_falso(monkeypatch):
    catalogo = {ID_A: _faixa(ID_A, "Faixa A"), ID_B: _faixa(ID_B, "Faixa B")}

    async def buscar(termo, limite=10):
        return [f for f in catalogo.values() if termo.lower() in f.titulo.lower()][:limite]

    async def obter(spotify_id):
        return catalogo.get(spotify_id)

    monkeypatch.setattr(spotify, "buscar_faixas", buscar)
    monkeypatch.setattr(spotify, "obter_faixa", obter)


async def test_busca_retorna_faixas(client, duas_academias, spotify_falso):
    r = await client.get(
        "/v1/jukebox/busca?q=faixa", headers=auth_header(duas_academias["token_a"])
    )
    assert r.status_code == 200
    assert {f["id"] for f in r.json()["faixas"]} == {ID_A, ID_B}


async def test_busca_exige_token_de_aluno(client):
    assert (await client.get("/v1/jukebox/busca?q=faixa")).status_code == 401


async def test_sem_credenciais_retorna_503(client, duas_academias, monkeypatch):
    monkeypatch.setattr(spotify.settings, "spotify_client_id", "")
    monkeypatch.setattr(spotify.settings, "spotify_client_secret", "")
    r = await client.get(
        "/v1/jukebox/busca?q=faixa", headers=auth_header(duas_academias["token_a"])
    )
    assert r.status_code == 503


async def test_pedido_entra_na_fila_so_da_propria_academia(client, duas_academias, spotify_falso):
    r = await client.post(
        "/v1/jukebox/pedidos",
        json={"spotify_id": ID_A},
        headers=auth_header(duas_academias["token_a"]),
    )
    assert r.status_code == 201 and r.json()["titulo"] == "Faixa A"

    fila_a = await client.get("/v1/jukebox/fila", headers=auth_header(duas_academias["token_a"]))
    fila_b = await client.get("/v1/jukebox/fila", headers=auth_header(duas_academias["token_b"]))
    assert [x["titulo"] for x in fila_a.json()["fila"]] == ["Faixa A"]
    assert fila_b.json()["fila"] == []


async def test_mesma_faixa_pedida_por_duas_academias_nao_duplica(
    client, duas_academias, spotify_falso
):
    for token in (duas_academias["token_a"], duas_academias["token_b"]):
        r = await client.post(
            "/v1/jukebox/pedidos", json={"spotify_id": ID_B}, headers=auth_header(token)
        )
        assert r.status_code == 201


async def test_limite_de_pedidos_pendentes_por_aluno(client, duas_academias, spotify_falso):
    h = auth_header(duas_academias["token_a"])
    for _ in range(3):
        assert (
            await client.post("/v1/jukebox/pedidos", json={"spotify_id": ID_A}, headers=h)
        ).status_code == 201
    assert (
        await client.post("/v1/jukebox/pedidos", json={"spotify_id": ID_A}, headers=h)
    ).status_code == 429


async def test_biblioteca_salva_lista_remove_e_isola_alunos(client, duas_academias, spotify_falso):
    h_a = auth_header(duas_academias["token_a"])
    h_b = auth_header(duas_academias["token_b"])

    salvo = await client.post("/v1/jukebox/biblioteca", json={"spotify_id": ID_A}, headers=h_a)
    assert salvo.status_code == 201
    assert salvo.json()["spotify_id"] == ID_A

    biblioteca_a = await client.get("/v1/jukebox/biblioteca", headers=h_a)
    biblioteca_b = await client.get("/v1/jukebox/biblioteca", headers=h_b)
    assert [f["spotify_id"] for f in biblioteca_a.json()["faixas"]] == [ID_A]
    assert biblioteca_b.json()["faixas"] == []

    removido = await client.delete(f"/v1/jukebox/biblioteca/{ID_A}", headers=h_a)
    assert removido.status_code == 204
    assert (await client.get("/v1/jukebox/biblioteca", headers=h_a)).json()["faixas"] == []


async def test_biblioteca_nao_duplica_faixa(client, duas_academias, spotify_falso):
    h = auth_header(duas_academias["token_a"])
    for _ in range(2):
        assert (
            await client.post("/v1/jukebox/biblioteca", json={"spotify_id": ID_B}, headers=h)
        ).status_code == 201
    faixas = (await client.get("/v1/jukebox/biblioteca", headers=h)).json()["faixas"]
    assert len(faixas) == 1 and faixas[0]["spotify_id"] == ID_B


async def test_biblioteca_rejeita_id_invalido(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    assert (
        await client.post("/v1/jukebox/biblioteca", json={"spotify_id": "../../x"}, headers=h)
    ).status_code == 422
    assert (await client.delete("/v1/jukebox/biblioteca/not-valid", headers=h)).status_code == 422


async def test_biblioteca_retorna_404_sem_metadados(
    client, duas_academias, spotify_falso, monkeypatch
):
    async def ausente(_spotify_id):
        return None

    monkeypatch.setattr(spotify, "obter_faixa", ausente)
    r = await client.post(
        "/v1/jukebox/biblioteca",
        json={"spotify_id": ID_A},
        headers=auth_header(duas_academias["token_a"]),
    )
    assert r.status_code == 404


async def test_id_invalido_e_rejeitado(client, duas_academias, spotify_falso):
    r = await client.post(
        "/v1/jukebox/pedidos",
        json={"spotify_id": "../../x"},
        headers=auth_header(duas_academias["token_a"]),
    )
    assert r.status_code == 422


async def test_cliente_http_do_spotify(monkeypatch):
    """Fluxo real do cliente contra um Spotify simulado no nível HTTP."""
    chamadas = {"token": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "accounts.spotify.com":
            chamadas["token"] += 1
            assert req.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        assert req.headers["authorization"] == "Bearer tok"
        return httpx.Response(
            200,
            json={
                "tracks": {
                    "items": [
                        {
                            "id": ID_A,
                            "name": "Ritmo de Ferro",
                            "duration_ms": 212400,
                            "explicit": False,
                            "artists": [{"name": "Banda Alta Carga"}, {"name": "Convidado"}],
                            "album": {"images": [{"url": "g"}, {"url": "m"}, {"url": "p"}]},
                        }
                    ]
                }
            },
        )

    real = httpx.AsyncClient
    monkeypatch.setattr(
        spotify.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    monkeypatch.setattr(spotify.settings, "spotify_client_id", "id")
    monkeypatch.setattr(spotify.settings, "spotify_client_secret", "secret")
    monkeypatch.setattr(spotify, "_token", None)

    faixas = await spotify.buscar_faixas("ritmo")
    assert faixas[0].titulo == "Ritmo de Ferro"
    assert faixas[0].artista == "Banda Alta Carga, Convidado"
    assert faixas[0].duracao_segundos == 212
    assert faixas[0].capa_url == "m"

    await spotify.buscar_faixas("ritmo")
    assert chamadas["token"] == 1  # token em cache
