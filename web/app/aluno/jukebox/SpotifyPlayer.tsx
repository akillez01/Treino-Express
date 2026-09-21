"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import s from "./jukebox.module.css";

export const SPOTIFY_TRACK_STORAGE_KEY = "treino-express:spotify-track";
const SPOTIFY_SELECTION_EVENT = "treino-express:spotify-selection";

export type SpotifySelection = {
  id: string;
  titulo?: string;
  tipo: "track" | "playlist";
};

function salvarSelecao(selecao: SpotifySelection) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(SPOTIFY_TRACK_STORAGE_KEY, JSON.stringify(selecao));
    window.dispatchEvent(new CustomEvent(SPOTIFY_SELECTION_EVENT, { detail: selecao }));
  }
}

export function selecionarFaixaSpotify(spotifyId: string, titulo?: string) {
  salvarSelecao({ id: spotifyId, titulo, tipo: "track" });
}

export function selecionarPlaylistSpotify(spotifyId: string, titulo?: string) {
  salvarSelecao({ id: spotifyId, titulo, tipo: "playlist" });
}

export function lerSelecaoSpotify(): SpotifySelection | null {
  if (typeof window === "undefined") return null;
  const guardado = window.localStorage.getItem(SPOTIFY_TRACK_STORAGE_KEY);
  if (!guardado) return null;
  try {
    const selecao = JSON.parse(guardado) as Partial<SpotifySelection>;
    if (typeof selecao.id === "string" && (selecao.tipo === "track" || selecao.tipo === "playlist")) {
      return { id: selecao.id, titulo: selecao.titulo, tipo: selecao.tipo };
    }
  } catch {
    return { id: guardado, tipo: "track" };
  }
  return null;
}

export default function SpotifyPlayer({
  spotifyId,
  titulo,
  compacto = false,
  tipo = "track",
}: {
  spotifyId?: string | null;
  titulo?: string;
  compacto?: boolean;
  tipo?: "track" | "playlist";
}) {
  const [id, setId] = useState<string | null>(spotifyId ?? null);

  useEffect(() => {
    if (spotifyId) {
      salvarSelecao({ id: spotifyId, titulo, tipo });
      setId(spotifyId);
      return;
    }
    setId(lerSelecaoSpotify()?.id ?? null);
  }, [spotifyId, tipo, titulo]);

  if (!id) {
    return compacto ? null : <p className={s.playerEmpty}>Escolha uma faixa da sua biblioteca para ouvir.</p>;
  }

  const embedUrl = `https://open.spotify.com/embed/${tipo}/${encodeURIComponent(id)}?utm_source=generator&theme=0`;

  return (
    <section className={compacto ? s.playerCompact : s.player}>
      <div className={s.playerHead}>
        <div>
          <div className={s.playerEyebrow}>{compacto ? "CONTINUAR OUVINDO" : "SEU PLAYER"}</div>
          {titulo && <div className={s.playerTitle}>{titulo}</div>}
        </div>
        {compacto && (
          <Link href="/aluno/jukebox" className={s.playerLink}>
            Biblioteca
          </Link>
        )}
      </div>
      <iframe
        src={embedUrl}
        title={titulo ? `Ouvir ${titulo} no Spotify` : "Player do Spotify"}
        className={s.playerFrame}
        allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
        loading="lazy"
      />
      <p className={s.playerNote}>
        Pressione play para começar. Uma conta Spotify e o Premium podem ser necessários.
      </p>
    </section>
  );
}
