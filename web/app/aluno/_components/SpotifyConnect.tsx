"use client";

import { useEffect, useState } from "react";
import { spotifyConfig, type SpotifyConfig } from "@/lib/api";

export const SPOTIFY_ACCESS_TOKEN_KEY = "treino-express:spotify-access-token";
export const SPOTIFY_REFRESH_TOKEN_KEY = "treino-express:spotify-refresh-token";
export const SPOTIFY_EXPIRES_AT_KEY = "treino-express:spotify-expires-at";
export const SPOTIFY_VERIFIER_KEY = "treino-express:spotify-pkce-verifier";
export const SPOTIFY_STATE_KEY = "treino-express:spotify-oauth-state";
export const SPOTIFY_REDIRECT_URI_KEY = "treino-express:spotify-redirect-uri";
export const SPOTIFY_AUTH_EVENT = "treino-express:spotify-auth";

const base64Url = (bytes: Uint8Array) =>
  btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

function randomUrlSafe(bytes = 32): string {
  const data = new Uint8Array(bytes);
  crypto.getRandomValues(data);
  return base64Url(data);
}

async function challenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64Url(new Uint8Array(digest));
}

export function spotifyConnected(): boolean {
  return typeof window !== "undefined" && Boolean(sessionStorage.getItem(SPOTIFY_ACCESS_TOKEN_KEY));
}

export function clearSpotifySession() {
  if (typeof window === "undefined") return;
  for (const key of [
    SPOTIFY_ACCESS_TOKEN_KEY,
    SPOTIFY_REFRESH_TOKEN_KEY,
    SPOTIFY_EXPIRES_AT_KEY,
    SPOTIFY_VERIFIER_KEY,
    SPOTIFY_STATE_KEY,
    SPOTIFY_REDIRECT_URI_KEY,
  ]) {
    sessionStorage.removeItem(key);
  }
  window.dispatchEvent(new Event(SPOTIFY_AUTH_EVENT));
}

export default function SpotifyConnect({ compact = false }: { compact?: boolean }) {
  const [connected, setConnected] = useState(false);
  const [config, setConfig] = useState<SpotifyConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setConnected(spotifyConnected());
    const update = () => setConnected(spotifyConnected());
    window.addEventListener(SPOTIFY_AUTH_EVENT, update);
    return () => window.removeEventListener(SPOTIFY_AUTH_EVENT, update);
  }, []);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const spotify = config ?? (await spotifyConfig());
      setConfig(spotify);
      if (!spotify.configured || !spotify.client_id) {
        throw new Error("Spotify não está configurado neste servidor.");
      }
      const verifier = randomUrlSafe(64);
      const state = randomUrlSafe(32);
      sessionStorage.setItem(SPOTIFY_VERIFIER_KEY, verifier);
      sessionStorage.setItem(SPOTIFY_STATE_KEY, state);
      sessionStorage.setItem(SPOTIFY_REDIRECT_URI_KEY, spotify.redirect_uri);
      const params = new URLSearchParams({
        response_type: "code",
        client_id: spotify.client_id,
        redirect_uri: spotify.redirect_uri,
        code_challenge_method: "S256",
        code_challenge: await challenge(verifier),
        scope: spotify.scopes,
        state,
      });
      window.location.assign(`${spotify.authorize_url}?${params.toString()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível iniciar o login do Spotify.");
      setBusy(false);
    }
  }

  if (connected) {
    return (
      <button
        type="button"
        onClick={clearSpotifySession}
        disabled={busy}
        style={{ fontSize: compact ? 11 : 13 }}
      >
        Desconectar
      </button>
    );
  }
  return (
    <span>
      <button type="button" onClick={connect} disabled={busy} style={{ fontSize: compact ? 11 : 13 }}>
        {busy ? "Conectando..." : "Conectar Spotify"}
      </button>
      {error && <small>{error}</small>}
    </span>
  );
}
