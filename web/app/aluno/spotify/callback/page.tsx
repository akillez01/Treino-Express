"use client";

import { useEffect, useState } from "react";
import { trocarCodigoSpotify } from "@/lib/api";
import {
  SPOTIFY_ACCESS_TOKEN_KEY,
  SPOTIFY_AUTH_EVENT,
  SPOTIFY_EXPIRES_AT_KEY,
  SPOTIFY_REFRESH_TOKEN_KEY,
  SPOTIFY_REDIRECT_URI_KEY,
  SPOTIFY_STATE_KEY,
  SPOTIFY_VERIFIER_KEY,
} from "../../_components/SpotifyConnect";

export default function SpotifyCallbackPage() {
  const [message, setMessage] = useState("Concluindo conexão com o Spotify...");

  useEffect(() => {
    let ativo = true;
    async function finish() {
      const params = new URLSearchParams(window.location.search);
      const error = params.get("error");
      const state = params.get("state");
      const expectedState = sessionStorage.getItem(SPOTIFY_STATE_KEY);
      const verifier = sessionStorage.getItem(SPOTIFY_VERIFIER_KEY);
      if (error) throw new Error(`O Spotify recusou a conexão (${error}).`);
      if (!state || !expectedState || state !== expectedState) throw new Error("Estado OAuth inválido.");
      if (!verifier) throw new Error("Verificador PKCE ausente. Tente conectar novamente.");
      const code = params.get("code");
      if (!code) throw new Error("O Spotify não retornou um código de autorização.");
      const redirectUri =
        sessionStorage.getItem(SPOTIFY_REDIRECT_URI_KEY) ||
        `${window.location.origin}/aluno/spotify/callback`;

      const token = await trocarCodigoSpotify(code, verifier, redirectUri);
      sessionStorage.setItem(SPOTIFY_ACCESS_TOKEN_KEY, token.access_token);
      if (token.refresh_token) sessionStorage.setItem(SPOTIFY_REFRESH_TOKEN_KEY, token.refresh_token);
      sessionStorage.setItem(SPOTIFY_EXPIRES_AT_KEY, String(Date.now() + token.expires_in * 1000));
      sessionStorage.removeItem(SPOTIFY_STATE_KEY);
      sessionStorage.removeItem(SPOTIFY_VERIFIER_KEY);
      window.dispatchEvent(new Event(SPOTIFY_AUTH_EVENT));
      window.location.replace("/aluno");
    }

    finish().catch((err: unknown) => {
      if (ativo) setMessage(err instanceof Error ? err.message : "Não foi possível conectar ao Spotify.");
    });
    return () => {
      ativo = false;
    };
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <p>{message}</p>
      {message !== "Concluindo conexão com o Spotify..." && <a href="/aluno">Voltar ao treino</a>}
    </main>
  );
}
