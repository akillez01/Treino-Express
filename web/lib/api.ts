"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export type Perfil = "aluno" | "gestor" | "anunciante";

// Enquanto não há login real (usuário e senha), cada perfil usa o token demo.
const tokens: Partial<Record<Perfil, string>> = {};

async function obterToken(perfil: Perfil): Promise<string> {
  const guardado = tokens[perfil];
  if (guardado) return guardado;
  const res = await fetch(`${API_BASE}/v1/auth/demo?perfil=${perfil}`, { method: "POST" });
  if (!res.ok) throw new Error(`Login indisponível (${res.status})`);
  const { access_token } = (await res.json()) as { access_token: string };
  tokens[perfil] = access_token;
  return access_token;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
  }
}

export async function api<T>(perfil: Perfil, path: string, init: RequestInit = {}): Promise<T> {
  for (let tentativa = 0; tentativa < 2; tentativa++) {
    let res: Response;
    try {
      const token = await obterToken(perfil);
      res = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...init.headers,
        },
      });
    } catch (e) {
      if (e instanceof ApiError) throw e;
      throw new ApiError("Não foi possível conectar à API. Verifique se o servidor está no ar.");
    }
    if (res.status === 401 && tentativa === 0) {
      delete tokens[perfil];
      continue;
    }
    if (!res.ok) {
      let detalhe = "";
      try {
        const corpo = (await res.json()) as { detail?: unknown };
        if (typeof corpo.detail === "string") detalhe = corpo.detail;
      } catch {
        /* corpo não é JSON */
      }
      throw new ApiError(detalhe || `Erro ${res.status} em ${path}`, res.status);
    }
    return res.json() as Promise<T>;
  }
  throw new ApiError("Sessão expirada");
}

export type Estado<T> = {
  data: T | null;
  erro: string | null;
  carregando: boolean;
  recarregar: () => void;
  mutar: (fn: (atual: T) => T) => void;
};

/** Busca dados e refaz a busca quando `chave` muda. */
export function useApi<T>(chave: string, buscar: () => Promise<T>): Estado<T> {
  const [data, setData] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [tick, setTick] = useState(0);
  const fn = useRef(buscar);
  fn.current = buscar;

  useEffect(() => {
    let vivo = true;
    setCarregando(true);
    setErro(null);
    fn
      .current()
      .then((d) => vivo && setData(d))
      .catch((e: unknown) => vivo && setErro(e instanceof Error ? e.message : "Erro inesperado"))
      .finally(() => vivo && setCarregando(false));
    return () => {
      vivo = false;
    };
  }, [chave, tick]);

  const recarregar = useCallback(() => setTick((t) => t + 1), []);
  const mutar = useCallback((f: (atual: T) => T) => setData((d) => (d === null ? d : f(d))), []);
  return { data, erro, carregando, recarregar, mutar };
}

// ---------------- App do aluno ----------------
export type Exercicio = { ordem: number; nome: string; series: string; carga: string | null };
export type Treino = {
  treino_id: string;
  minutos: number;
  foco: string;
  exercicios: Exercicio[];
  descanso_segundos: number;
};
export type Concluido = { proximo_ordem: number | null; treino_concluido: boolean };
export type Descanso = { descanso_segundos: number };

export const gerarTreino = (minutos: number, foco: string) =>
  api<Treino>("aluno", "/v1/treinos/gerar", { method: "POST", body: JSON.stringify({ minutos, foco }) });

export const iniciarDescanso = (treinoId: string, ordem: number) =>
  api<Descanso>("aluno", `/v1/treinos/${treinoId}/descanso`, {
    method: "POST",
    body: JSON.stringify({ ordem }),
  });

export const concluirExercicio = (treinoId: string, ordem: number) =>
  api<Concluido>("aluno", `/v1/treinos/${treinoId}/exercicio/${ordem}/concluir`, { method: "POST" });

// ---------------- Painel da academia ----------------
export type Origem = "mensalidade" | "anuncio" | "jukebox";
export type Receita = Record<Origem, number>;

export type TelaResumo = {
  id: string;
  sala: string;
  status: "online" | "pausada" | "offline";
  resolucao: string;
  ultimo_heartbeat: string | null;
};

export type ResumoAcademia = {
  academia: { nome: string; unidade: string | null };
  mes: string;
  fechamento: string;
  alunos_ativos: number;
  novos_no_mes: number;
  inadimplencia_pct: number;
  receita_centavos: Receita;
  receita_anterior_centavos: Receita;
  telas: TelaResumo[];
  jukebox: { pedidos: number; segundos: number };
  ultimos_checkins: { nome: string; plano: string; situacao: Situacao; entrada_em: string }[];
};

export type Situacao = "em_dia" | "pendente" | "atrasado";

export type Aluno = {
  id: string;
  nome: string;
  email: string;
  plano: string;
  matriculado_em: string;
  mensalidade_centavos: number;
  situacao: Situacao;
  freq_semanal: number;
  ultimo_checkin: string | null;
};

export type ListaAlunos = {
  itens: Aluno[];
  contagem: { todos: number; em_dia: number; pendente: number; atrasado: number; ticket: number };
  frequencia_media: number;
  limit: number;
  offset: number;
};

export type Financeiro = {
  mes: string;
  receita_centavos: Receita;
  recebido_centavos: number;
  a_receber_centavos: number;
  repasse_liquido_centavos: number;
  taxas_centavos: number;
  movimentacoes: {
    data: string;
    descricao: string;
    origem: Origem;
    valor_centavos: number;
    status: "liquidado" | "a_receber" | "recusado";
  }[];
  repasses: {
    data: string;
    anunciante: string;
    bruto_centavos: number;
    taxa_centavos: number;
    liquido_centavos: number;
    status: "pendente" | "em_transito" | "pago" | "falhou";
  }[];
};

export type Tela = TelaResumo & {
  pareada_em: string | null;
  codigo_pareamento: string | null;
  qr_mes: number;
};
export type TelasPayload = {
  telas: Tela[];
  fila: { titulo: string; artista: string; duracao_segundos: number; solicitante: string }[];
};

export const resumoAcademia = (mes: string) => api<ResumoAcademia>("gestor", `/v1/academia/resumo?mes=${mes}`);
export const alunosAcademia = (situacao: Situacao | null, offset: number, limit = 25) =>
  api<ListaAlunos>(
    "gestor",
    `/v1/academia/alunos?limit=${limit}&offset=${offset}${situacao ? `&situacao=${situacao}` : ""}`,
  );
export const financeiroAcademia = (mes: string) => api<Financeiro>("gestor", `/v1/academia/financeiro?mes=${mes}`);
export const telasAcademia = () => api<TelasPayload>("gestor", "/v1/academia/telas");
export const pausarTela = (id: string) =>
  api<{ id: string; status: Tela["status"] }>("gestor", `/v1/academia/telas/${id}/pausar`, { method: "POST" });
export const parearTela = () =>
  api<{ id: string; codigo: string }>("gestor", "/v1/academia/telas/pareamento", { method: "POST" });

// ---------------- Painel do anunciante ----------------
export type Periodo = "7d" | "30d";
export type Totais = { impressoes: number; gasto: number; scans: number; resgates: number };

export type CampanhasPayload = {
  conta: { nome: string; saldo_centavos: number };
  periodo: Periodo;
  academias: number;
  telas: number;
  totais: Totais;
  anterior: Totais;
  serie: { dia: string; scans: number; resgates: number }[];
  campanhas: {
    id: string;
    nome: string;
    academia: string;
    status: "ativa" | "pausada" | "rascunho" | "encerrada";
    janela: string;
    impressoes: number;
    scans: number;
    gasto: number;
  }[];
  gasto_mes_centavos: number;
};

export type MetricasPayload = {
  conta: { nome: string; saldo_centavos: number };
  periodo: Periodo;
  totais: Totais;
  horas: { faixa: string; scans: number }[];
  criativos: { nome: string; scans: number; resgates: number; gasto: number }[];
  academias: {
    nome: string;
    bairro: string;
    telas: number;
    impressoes: number;
    scans: number;
    resgates: number;
    gasto: number;
  }[];
};

export type FaturamentoPayload = {
  conta: { nome: string; saldo_centavos: number };
  investido_mes_centavos: number;
  resgates_mes: number;
  repassado_centavos: number;
  faturas: { data: string; descricao: string; valor_centavos: number; nota_fiscal: string; status: string }[];
};

export const campanhasAnunciante = (periodo: Periodo) =>
  api<CampanhasPayload>("anunciante", `/v1/anunciante/campanhas?periodo=${periodo}`);
export const metricasAnunciante = (periodo: Periodo) =>
  api<MetricasPayload>("anunciante", `/v1/anunciante/metricas?periodo=${periodo}`);
export const faturamentoAnunciante = () => api<FaturamentoPayload>("anunciante", "/v1/anunciante/faturamento");
export const alterarCampanha = (id: string, ativa: boolean) =>
  api<{ id: string; status: string }>("anunciante", `/v1/anunciante/campanhas/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ ativa }),
  });

// ---------------- Jukebox (Spotify) ----------------
export type FaixaSpotify = {
  id: string;
  titulo: string;
  artista: string;
  duracao_segundos: number;
  capa_url: string | null;
  explicita: boolean;
};
export type ItemFila = {
  id: string;
  titulo: string;
  artista: string;
  duracao_segundos: number;
  capa_url: string | null;
  solicitante: string;
};

export const statusJukebox = () => api<{ spotify_configurado: boolean }>("aluno", "/v1/jukebox/status");
export const buscarMusicas = (q: string) =>
  api<{ faixas: FaixaSpotify[] }>("aluno", `/v1/jukebox/busca?q=${encodeURIComponent(q)}`);
export const pedirMusica = (spotifyId: string) =>
  api<{ pedido_id: string; titulo: string; artista: string; posicao: number }>("aluno", "/v1/jukebox/pedidos", {
    method: "POST",
    body: JSON.stringify({ spotify_id: spotifyId }),
  });
export const filaJukebox = () => api<{ fila: ItemFila[] }>("aluno", "/v1/jukebox/fila");

// ---------------- TV (WebSocket) ----------------
export type TvAuth = { token: string; academia_id: string };

export async function parearTv(codigo: string): Promise<TvAuth> {
  const res = await fetch(`${API_BASE}/v1/tv/parear`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo }),
  });
  const corpo = (await res.json().catch(() => ({}))) as { access_token?: string; academia_id?: string; detail?: string };
  if (!res.ok || !corpo.access_token || !corpo.academia_id) throw new ApiError(corpo.detail || "Código inválido");
  return { token: corpo.access_token, academia_id: corpo.academia_id };
}

/** Só existe com ENABLE_DEMO_LOGIN no servidor. */
export async function telaDemo(): Promise<TvAuth> {
  const res = await fetch(`${API_BASE}/v1/auth/demo?perfil=tela`, { method: "POST" });
  const corpo = (await res.json().catch(() => ({}))) as { access_token?: string; academia_id?: string };
  if (!res.ok || !corpo.access_token || !corpo.academia_id) throw new ApiError("Tela demo indisponível neste servidor");
  return { token: corpo.access_token, academia_id: corpo.academia_id };
}

export const tvSocketUrl = (a: TvAuth) =>
  `${API_BASE.replace(/^http/, "ws")}/ws/tv/${a.academia_id}?token=${encodeURIComponent(a.token)}`;
