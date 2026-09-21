"use client";

import { useState } from "react";
import {
  buscarMusicas,
  buscarPlaylists,
  bibliotecaJukebox,
  filaJukebox,
  pedirMusica,
  removerBiblioteca,
  salvarBiblioteca,
  statusJukebox,
  useApi,
  type FaixaBiblioteca,
  type FaixaSpotify,
  type PlaylistSpotify,
} from "@/lib/api";
import AlunoTabs from "../_components/AlunoTabs";
import SpotifyPlayer, { selecionarFaixaSpotify } from "./SpotifyPlayer";
import s from "./jukebox.module.css";

const mmss = (n: number) => `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`;

export default function Jukebox() {
  const status = useApi("jb-status", statusJukebox);
  const fila = useApi("jb-fila", filaJukebox);
  const biblioteca = useApi("jb-biblioteca", bibliotecaJukebox);
  const [q, setQ] = useState("");
  const [modo, setModo] = useState<"musicas" | "playlists">("musicas");
  const [faixas, setFaixas] = useState<FaixaSpotify[] | null>(null);
  const [playlists, setPlaylists] = useState<PlaylistSpotify[] | null>(null);
  const [playlistAberta, setPlaylistAberta] = useState<string | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [pedindo, setPedindo] = useState<string | null>(null);
  const [salvando, setSalvando] = useState<string | null>(null);
  const [removendo, setRemovendo] = useState<string | null>(null);
  const [selecionada, setSelecionada] = useState<FaixaBiblioteca | null>(null);

  async function buscar(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setBuscando(true);
    setMsg(null);
    try {
      if (modo === "musicas") {
        setPlaylists(null);
        setFaixas((await buscarMusicas(q.trim())).faixas);
      } else {
        setFaixas(null);
        setPlaylists((await buscarPlaylists(q.trim())).playlists);
      }
    } catch (err) {
      setFaixas(null);
      setPlaylists(null);
      setMsg({ tipo: "erro", texto: err instanceof Error ? err.message : "Falha na busca" });
    } finally {
      setBuscando(false);
    }
  }

  function abrirPlaylist(p: PlaylistSpotify) {
    if (playlistAberta === p.id) {
      setPlaylistAberta(null);
    } else {
      setPlaylistAberta(p.id);
    }
  }

  async function pedir(f: FaixaSpotify) {
    setPedindo(f.id);
    setMsg(null);
    try {
      const r = await pedirMusica(f.id);
      setMsg({ tipo: "ok", texto: `"${r.titulo}" entrou na fila (posição ${r.posicao}).` });
      fila.recarregar();
    } catch (err) {
      setMsg({ tipo: "erro", texto: err instanceof Error ? err.message : "Não foi possível pedir" });
    } finally {
      setPedindo(null);
    }
  }

  async function salvar(f: FaixaSpotify) {
    setSalvando(f.id);
    setMsg(null);
    try {
      const faixa = await salvarBiblioteca(f.id);
      setSelecionada(faixa);
      selecionarFaixaSpotify(faixa.spotify_id);
      biblioteca.recarregar();
      setMsg({ tipo: "ok", texto: `"${faixa.titulo}" foi salva na sua biblioteca.` });
    } catch (err) {
      setMsg({ tipo: "erro", texto: err instanceof Error ? err.message : "Não foi possível salvar" });
    } finally {
      setSalvando(null);
    }
  }

  async function remover(f: FaixaBiblioteca) {
    setRemovendo(f.spotify_id);
    setMsg(null);
    try {
      await removerBiblioteca(f.spotify_id);
      if (selecionada?.spotify_id === f.spotify_id) setSelecionada(null);
      biblioteca.recarregar();
      setMsg({ tipo: "ok", texto: `"${f.titulo}" foi removida da sua biblioteca.` });
    } catch (err) {
      setMsg({ tipo: "erro", texto: err instanceof Error ? err.message : "Não foi possível remover" });
    } finally {
      setRemovendo(null);
    }
  }

  function escolherResultado(f: FaixaSpotify) {
    selecionarFaixaSpotify(f.id);
    setSelecionada({
      spotify_id: f.id,
      titulo: f.titulo,
      artista: f.artista,
      duracao_segundos: f.duracao_segundos,
      capa_url: f.capa_url,
      adicionada_em: "",
    });
  }

  const salvos = new Set((biblioteca.data?.faixas ?? []).map((f) => f.spotify_id));
  const naoConfigurado = status.data && !status.data.spotify_configurado;

  function renderFaixa(f: FaixaSpotify) {
    return (
      <li key={f.id} className={s.item}>
        {f.capa_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={f.capa_url} alt="" className={s.capa} />
        ) : (
          <div className={s.capa} />
        )}
        <div className={s.info}>
          <div className={s.nome}>{f.titulo}</div>
          <div className={s.artista}>
            {f.artista} · {mmss(f.duracao_segundos)}
          </div>
        </div>
        <div className={s.acoes}>
          <button className={s.ouvir} onClick={() => escolherResultado(f)}>
            Ouvir
          </button>
          <button className={s.salvar} disabled={salvando === f.id || salvos.has(f.id)} onClick={() => salvar(f)}>
            {salvando === f.id ? "Salvando..." : salvos.has(f.id) ? "Na biblioteca" : "＋ Salvar na biblioteca"}
          </button>
          <button className={s.pedir} disabled={pedindo === f.id} onClick={() => pedir(f)}>
            {pedindo === f.id ? "..." : "Pedir"}
          </button>
        </div>
      </li>
    );
  }

  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <h1 className={s.title}>Jukebox</h1>
        <p className={s.sub}>Peça a próxima música da TV da academia.</p>

        {naoConfigurado && (
          <div className={s.aviso} role="status">
            O Spotify ainda não está configurado neste servidor (defina <code>SPOTIFY_CLIENT_ID</code> e{" "}
            <code>SPOTIFY_CLIENT_SECRET</code>).
          </div>
        )}

        <div className={s.segmented} role="tablist" aria-label="Fonte da busca">
          <button
            type="button"
            role="tab"
            aria-selected={modo === "musicas"}
            className={modo === "musicas" ? s.segmentOn : s.segment}
            onClick={() => {
              setModo("musicas");
              setFaixas(null);
              setPlaylists(null);
              setPlaylistAberta(null);
            }}
          >
            Músicas
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={modo === "playlists"}
            className={modo === "playlists" ? s.segmentOn : s.segment}
            onClick={() => {
              setModo("playlists");
              setFaixas(null);
              setPlaylists(null);
              setPlaylistAberta(null);
            }}
          >
            Playlists do Spotify
          </button>
        </div>

        <form className={s.search} onSubmit={buscar}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={modo === "musicas" ? "Buscar música ou artista" : "Buscar playlist no Spotify"}
            aria-label={modo === "musicas" ? "Buscar música" : "Buscar playlist"}
            maxLength={100}
          />
          <button disabled={buscando || q.trim().length < 2}>{buscando ? "..." : "Buscar"}</button>
        </form>

        {msg && (
          <div className={msg.tipo === "ok" ? s.ok : s.erro} role="status">
            {msg.texto}
          </div>
        )}

        {modo === "musicas" && faixas && (
          <ul className={s.list}>
            {faixas.length === 0 && <li className={s.vazio}>Nada encontrado.</li>}
            {faixas.map(renderFaixa)}
          </ul>
        )}

        {modo === "playlists" && playlists && (
          <ul className={s.list}>
            {playlists.length === 0 && <li className={s.vazio}>Nenhuma playlist encontrada.</li>}
            {playlists.map((p) => (
              <li key={p.id} className={s.playlistItem}>
                {p.cover_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={p.cover_url} alt="" className={s.capa} />
                ) : (
                  <div className={s.capa} />
                )}
                <div className={s.info}>
                  <div className={s.nome}>{p.name}</div>
                  <div className={s.artista}>
                    {p.owner || "Spotify"} · {p.tracks_total} {p.tracks_total === 1 ? "faixa" : "faixas"}
                  </div>
                </div>
                <button className={s.abrirPlaylist} onClick={() => abrirPlaylist(p)}>
                  {playlistAberta === p.id ? "Fechar" : "Ouvir playlist"}
                </button>
                {playlistAberta === p.id && (
                  <div className={s.playlistPlayer}>
                    <SpotifyPlayer spotifyId={p.id} titulo={p.name} tipo="playlist" />
                    <p className={s.librarySub}>
                      Para salvar uma música individual, pesquise por ela na aba Músicas e toque em
                      “Salvar na biblioteca”.
                    </p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        <section className={s.library}>
          <h2 className={s.h2}>Minha biblioteca</h2>
          <p className={s.librarySub}>Suas músicas para ouvir com fones durante o treino.</p>
          {selecionada && <SpotifyPlayer spotifyId={selecionada.spotify_id} titulo={selecionada.titulo} />}
          {!selecionada && biblioteca.data?.faixas[0] && (
            <SpotifyPlayer spotifyId={biblioteca.data.faixas[0].spotify_id} titulo={biblioteca.data.faixas[0].titulo} />
          )}
          <ul className={s.list}>
            {biblioteca.data?.faixas.length === 0 && <li className={s.vazio}>Sua biblioteca está vazia.</li>}
            {biblioteca.data?.faixas.map((f) => (
              <li key={f.spotify_id} className={selecionada?.spotify_id === f.spotify_id ? `${s.item} ${s.itemOn}` : s.item}>
                {f.capa_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={f.capa_url} alt="" className={s.capa} />
                ) : (
                  <div className={s.capa} />
                )}
                <div className={s.info}>
                  <div className={s.nome}>{f.titulo}</div>
                  <div className={s.artista}>
                    {f.artista} · {mmss(f.duracao_segundos)}
                  </div>
                </div>
                <div className={s.acoes}>
                  <button className={s.ouvir} onClick={() => setSelecionada(f)}>
                    Ouvir
                  </button>
                  <button className={s.remover} disabled={removendo === f.spotify_id} onClick={() => remover(f)}>
                    {removendo === f.spotify_id ? "..." : "Remover"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <h2 className={s.h2}>Na fila</h2>
        <ul className={s.list}>
          {fila.data?.fila.length === 0 && <li className={s.vazio}>Ninguém pediu música ainda.</li>}
          {fila.data?.fila.map((f, i) => (
            <li key={f.id} className={s.item}>
              <div className={s.pos}>{String(i + 1).padStart(2, "0")}</div>
              <div className={s.info}>
                <div className={s.nome}>{f.titulo}</div>
                <div className={s.artista}>
                  {f.artista} · pedida por {f.solicitante}
                </div>
              </div>
              <div className={s.dur}>{mmss(f.duracao_segundos)}</div>
            </li>
          ))}
        </ul>
      </div>
      <AlunoTabs />
    </main>
  );
}
