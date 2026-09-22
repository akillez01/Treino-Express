"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AUTH_EVENT,
  API_BASE,
  clearAppToken,
  getAppToken,
  obterGoogleConfig,
  setAppToken,
  type GoogleConfig,
} from "@/lib/api";
import s from "../aluno.module.css";

type GoogleCredentialResponse = { credential: string };
type GoogleButtonOptions = {
  type?: "standard" | "icon";
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  text?: "signin_with" | "signup_with" | "continue_with" | "signin";
  shape?: "rectangular" | "pill" | "circle" | "square";
  width?: number;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(options: {
            client_id: string;
            callback(response: GoogleCredentialResponse): void;
          }): void;
          renderButton(element: HTMLElement, options: GoogleButtonOptions): void;
          cancel(): void;
        };
      };
    };
  }
}

function loadGoogleScript(onReady: () => void): () => void {
  if (window.google?.accounts?.id) {
    onReady();
    return () => {};
  }
  const existing = document.querySelector<HTMLScriptElement>("#google-gis-script");
  if (existing) {
    existing.addEventListener("load", onReady);
    return () => existing.removeEventListener("load", onReady);
  }
  const script = document.createElement("script");
  script.id = "google-gis-script";
  script.src = "https://accounts.google.com/gsi/client";
  script.async = true;
  script.defer = true;
  script.onload = onReady;
  document.head.appendChild(script);
  return () => {
    script.onload = null;
  };
}

export default function GoogleLogin(): React.ReactElement | null {
  const router = useRouter();
  const buttonRef = useRef<HTMLDivElement>(null);
  const [config, setConfig] = useState<GoogleConfig | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    setAutenticado(Boolean(getAppToken()));
    const atualizar = () => setAutenticado(Boolean(getAppToken()));
    window.addEventListener(AUTH_EVENT, atualizar);
    obterGoogleConfig().then(setConfig).catch(() => setConfig(null));
    return () => window.removeEventListener(AUTH_EVENT, atualizar);
  }, []);

  useEffect(() => {
    if (!config?.enabled || autenticado || !buttonRef.current) return;
    let ativo = true;
    const ready = () => {
      if (!ativo || !buttonRef.current || !window.google) return;
      buttonRef.current.replaceChildren();
      window.google.accounts.id.initialize({
        client_id: config.client_id,
        callback: async ({ credential }) => {
          setErro(null);
          try {
            const response = await fetch(`${API_BASE}/v1/auth/google`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ credential }),
            });
            const body = (await response.json().catch(() => ({}))) as {
              access_token?: string;
              detail?: string;
            };
            if (!response.ok || !body.access_token) {
              throw new Error(body.detail || "Não foi possível entrar com Google.");
            }
            setAppToken(body.access_token);
            router.push("/aluno");
          } catch (error) {
            setErro(error instanceof Error ? error.message : "Falha no login com Google.");
          }
        },
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        text: "signin_with",
        shape: "pill",
        width: 280,
      });
    };
    const removeListener = loadGoogleScript(ready);
    return () => {
      ativo = false;
      removeListener();
    };
  }, [autenticado, config, router]);

  if (!config?.enabled) return null;
  if (autenticado) {
    return (
      <div className={s.loginRow}>
        <span className={s.loginHint}>Conta Treino Express conectada</span>
        <button type="button" className={s.logout} onClick={clearAppToken}>
          Sair
        </button>
      </div>
    );
  }
  return (
    <div className={s.loginCard}>
      <strong>Entre para acessar seu treino</strong>
      <span className={s.loginHint}>Use a conta Google cadastrada pela sua academia.</span>
      <div ref={buttonRef} className={s.googleButton} />
      {erro && <p className={s.loginError}>{erro}</p>}
      <small>O login do Google é da conta Treino Express. Spotify Connect é separado.</small>
    </div>
  );
}
