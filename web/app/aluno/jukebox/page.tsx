"use client";

import { useState } from "react";
import {
  buscarMusicas,
  filaJukebox,
  pedirMusica,
  statusJukebox,
  useApi,
  type FaixaSpotify,
} from "@/lib/api";
import AlunoTabs from "../_components/AlunoTabs";
import s from "./jukebox.module.css";

const mmss = (n: number) => `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`;

export default function Jukebox() {
  const status = useApi("jb-status", statusJukebox);
  const fila = useApi("jb-fila", filaJukebox);
  const [q, setQ] = useState("");
  const [faixas, setFaixas] = useState<FaixaSpotify[] | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [pedindo, setPedindo] = useState<string | null>(null);

  async function buscar(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setBuscando(true);
    setMsg(null);
    try {
      setFaixas((await buscarMusicas(q.trim())).faixas);
    } catch (err) {
      setFaixas(null);
      setMsg({ tipo: "erro", texto: err instanceof Error ? err.message : "Falha na busca" });
    } finally {
      setBuscando(false);
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

  const naoConfigurado = status.data && !status.data.spotify_configurado;

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

        <form className={s.search} onSubmit={buscar}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar música ou artista"
            aria-label="Buscar música"
            maxLength={100}
          />
          <button disabled={buscando || q.trim().length < 2}>{buscando ? "..." : "Buscar"}</button>
        </form>

        {msg && (
          <div className={msg.tipo === "ok" ? s.ok : s.erro} role="status">
            {msg.texto}
          </div>
        )}

        {faixas && (
          <ul className={s.list}>
            {faixas.length === 0 && <li className={s.vazio}>Nada encontrado.</li>}
            {faixas.map((f) => (
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
                <button className={s.pedir} disabled={pedindo === f.id} onClick={() => pedir(f)}>
                  {pedindo === f.id ? "..." : "Pedir"}
                </button>
              </li>
            ))}
          </ul>
        )}

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
