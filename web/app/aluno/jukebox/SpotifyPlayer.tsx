"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import s from "./jukebox.module.css";

export const SPOTIFY_TRACK_STORAGE_KEY = "treino-express:spotify-track";

export function selecionarFaixaSpotify(spotifyId: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(SPOTIFY_TRACK_STORAGE_KEY, spotifyId);
  }
}

export default function SpotifyPlayer({
  spotifyId,
  titulo,
  compacto = false,
}: {
  spotifyId?: string | null;
  titulo?: string;
  compacto?: boolean;
}) {
  const [id, setId] = useState<string | null>(spotifyId ?? null);

  useEffect(() => {
    if (spotifyId) {
      selecionarFaixaSpotify(spotifyId);
      setId(spotifyId);
      return;
    }
    setId(window.localStorage.getItem(SPOTIFY_TRACK_STORAGE_KEY));
  }, [spotifyId]);

  if (!id) {
    return compacto ? null : <p className={s.playerEmpty}>Escolha uma faixa da sua biblioteca para ouvir.</p>;
  }

  const embedUrl = `https://open.spotify.com/embed/track/${encodeURIComponent(id)}?utm_source=generator&theme=0`;

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
