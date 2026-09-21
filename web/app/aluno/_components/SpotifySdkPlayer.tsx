"use client";

import { useEffect, useRef, useState } from "react";
import { renovarTokenSpotify, spotifyPlayback } from "@/lib/api";
import SpotifyPlayer, { type SpotifySelection } from "../jukebox/SpotifyPlayer";
import SpotifyConnect, {
  SPOTIFY_ACCESS_TOKEN_KEY,
  SPOTIFY_AUTH_EVENT,
  SPOTIFY_EXPIRES_AT_KEY,
  SPOTIFY_REFRESH_TOKEN_KEY,
  spotifyConnected,
} from "./SpotifyConnect";
import s from "../jukebox/jukebox.module.css";

type SpotifySdkPlayer = {
  connect: () => Promise<boolean>;
  disconnect: () => void;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  previousTrack: () => Promise<void>;
  nextTrack: () => Promise<void>;
  togglePlay: () => Promise<void>;
  addListener: (event: string, callback: (payload: unknown) => void) => boolean;
  removeListener: (event: string, callback: (payload: unknown) => void) => boolean;
};

type SpotifySdk = {
  Player: new (options: {
    name: string;
    volume: number;
    getOAuthToken: (callback: (token: string) => void) => void;
  }) => SpotifySdkPlayer;
};

declare global {
  interface Window {
    Spotify?: SpotifySdk;
    onSpotifyWebPlaybackSDKReady?: () => void;
  }
}

const SDK_READY_EVENT = "treino-express:spotify-sdk-ready";
const SDK_URL = "https://sdk.scdn.co/spotify-player.js";

function readToken() {
  return typeof window === "undefined" ? null : sessionStorage.getItem(SPOTIFY_ACCESS_TOKEN_KEY);
}

async function currentToken(): Promise<string> {
  const token = readToken();
  const expires = Number(sessionStorage.getItem(SPOTIFY_EXPIRES_AT_KEY) || 0);
  const refresh = sessionStorage.getItem(SPOTIFY_REFRESH_TOKEN_KEY);
  if (token && expires > Date.now() + 30_000) return token;
  if (!refresh) throw new Error("Sessão do Spotify expirada. Conecte novamente.");
  const renewed = await renovarTokenSpotify(refresh);
  sessionStorage.setItem(SPOTIFY_ACCESS_TOKEN_KEY, renewed.access_token);
  if (renewed.refresh_token) sessionStorage.setItem(SPOTIFY_REFRESH_TOKEN_KEY, renewed.refresh_token);
  sessionStorage.setItem(SPOTIFY_EXPIRES_AT_KEY, String(Date.now() + renewed.expires_in * 1000));
  return renewed.access_token;
}

async function playbackWithRefresh(path: string, body?: object) {
  let token = await currentToken();
  let response = await spotifyPlayback(token, body ?? null, "PUT", path);
  if (response.status === 401) {
    const refresh = sessionStorage.getItem(SPOTIFY_REFRESH_TOKEN_KEY);
    if (!refresh) throw new Error("Sessão do Spotify expirou. Conecte novamente.");
    const renewed = await renovarTokenSpotify(refresh);
    token = renewed.access_token;
    sessionStorage.setItem(SPOTIFY_ACCESS_TOKEN_KEY, token);
    if (renewed.refresh_token) sessionStorage.setItem(SPOTIFY_REFRESH_TOKEN_KEY, renewed.refresh_token);
    sessionStorage.setItem(SPOTIFY_EXPIRES_AT_KEY, String(Date.now() + renewed.expires_in * 1000));
    response = await spotifyPlayback(token, body ?? null, "PUT", path);
  }
  if (!response.ok && response.status !== 204) {
    throw new Error(`Spotify não iniciou a reprodução (${response.status}).`);
  }
}

function ensureSdk() {
  if (typeof window === "undefined") return;
  if (window.Spotify) {
    window.dispatchEvent(new Event(SDK_READY_EVENT));
    return;
  }
  const existing = document.querySelector<HTMLScriptElement>('script[data-treino-express-spotify-sdk="true"]');
  if (!existing) {
    const script = document.createElement("script");
    script.src = SDK_URL;
    script.async = true;
    script.dataset.treinoExpressSpotifySdk = "true";
    document.body.appendChild(script);
  }
  const previous = window.onSpotifyWebPlaybackSDKReady;
  window.onSpotifyWebPlaybackSDKReady = () => {
    previous?.();
    window.dispatchEvent(new Event(SDK_READY_EVENT));
  };
}

export default function SpotifySdkPlayer({
  selection,
}: {
  selection: SpotifySelection | null;
}) {
  const playerRef = useRef<SpotifySdkPlayer | null>(null);
  const deviceRef = useRef<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [ready, setReady] = useState(false);
  const [paused, setPaused] = useState(true);
  const [status, setStatus] = useState("Conecte uma conta Spotify Premium para tocar durante o treino.");
  const [sdkReady, setSdkReady] = useState(false);

  useEffect(() => {
    setConnected(spotifyConnected());
    const update = () => setConnected(spotifyConnected());
    window.addEventListener(SPOTIFY_AUTH_EVENT, update);
    return () => window.removeEventListener(SPOTIFY_AUTH_EVENT, update);
  }, []);

  useEffect(() => {
    if (!connected) {
      playerRef.current?.disconnect();
      playerRef.current = null;
      deviceRef.current = null;
      setReady(false);
      return;
    }
    ensureSdk();
    const update = () => setSdkReady(Boolean(window.Spotify));
    window.addEventListener(SDK_READY_EVENT, update);
    update();
    return () => window.removeEventListener(SDK_READY_EVENT, update);
  }, [connected]);

  useEffect(() => {
    if (!connected || !sdkReady || !window.Spotify || playerRef.current) return;
    const player = new window.Spotify.Player({
      name: "Treino Express",
      volume: 0.8,
      getOAuthToken: (callback) => {
        currentToken().then(callback).catch(() => callback(""));
      },
    });
    const onReady = (payload: unknown) => {
      const id = (payload as { device_id?: unknown })?.device_id;
      if (typeof id === "string") {
        deviceRef.current = id;
        setReady(true);
        setStatus("Pronto para tocar.");
      }
    };
    const onNotReady = () => {
      deviceRef.current = null;
      setReady(false);
      setStatus("O dispositivo Spotify ficou indisponível.");
    };
    const onState = (payload: unknown) => {
      const state = payload as { paused?: boolean } | null;
      if (typeof state?.paused === "boolean") setPaused(state.paused);
    };
    const onError = (payload: unknown) => {
      const message = (payload as { message?: unknown })?.message;
      setStatus(typeof message === "string" ? message : "O Spotify não conseguiu tocar.");
    };
    player.addListener("ready", onReady);
    player.addListener("not_ready", onNotReady);
    player.addListener("player_state_changed", onState);
    player.addListener("initialization_error", onError);
    player.addListener("authentication_error", onError);
    player.addListener("account_error", onError);
    player.addListener("playback_error", onError);
    playerRef.current = player;
    player.connect().catch(() => setStatus("Não foi possível conectar ao player do Spotify."));
    return () => {
      player.disconnect();
      playerRef.current = null;
      deviceRef.current = null;
    };
  }, [connected, sdkReady]);

  useEffect(() => {
    if (!connected || !selection || !deviceRef.current) return;
    const device = deviceRef.current;
    const body =
      selection.tipo === "playlist"
        ? { context_uri: `spotify:playlist:${selection.id}` }
        : { uris: [`spotify:track:${selection.id}`] };
    playbackWithRefresh(`/v1/me/player/play?device_id=${encodeURIComponent(device)}`, body).catch((err: unknown) => {
      if (err instanceof Error) setStatus(err.message);
    });
  }, [connected, selection, ready]);

  async function control(action: () => Promise<void>) {
    try {
      await action();
    } catch (err) {
      if (err instanceof Error) setStatus(err.message);
    }
  }

  return (
    <section className={s.playerCompact}>
      <div className={s.playerHead}>
        <div>
          <div className={s.playerEyebrow}>SPOTIFY NO TREINO</div>
          <div className={s.playerTitle}>{selection?.titulo || "Player oficial"}</div>
        </div>
        <SpotifyConnect compact />
      </div>
      {connected ? (
        <>
          <div className={s.spotifyControls}>
            <button type="button" onClick={() => control(() => playerRef.current?.previousTrack() || Promise.resolve())} disabled={!ready}>
              Anterior
            </button>
            <button type="button" onClick={() => control(() => playerRef.current?.togglePlay() || Promise.resolve())} disabled={!ready}>
              {paused ? "Tocar" : "Pausar"}
            </button>
            <button type="button" onClick={() => control(() => playerRef.current?.nextTrack() || Promise.resolve())} disabled={!ready}>
              Próxima
            </button>
          </div>
          <p className={s.playerNote}>{status} O Web Playback SDK exige Spotify Premium.</p>
        </>
      ) : (
        <>
          {selection && (
            <SpotifyPlayer
              spotifyId={selection.id}
              titulo={selection.titulo}
              tipo={selection.tipo}
              compacto
            />
          )}
          <p className={s.playerNote}>
            Sem conexão, o player é apenas uma prévia/embed. Conecte o Spotify Premium para ouvir faixas completas.
          </p>
        </>
      )}
      {connected && !selection && <p className={s.playerNote}>Escolha uma faixa ou playlist na sua biblioteca.</p>}
    </section>
  );
}
