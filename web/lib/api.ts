const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

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

let token: string | null = null;

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) throw new Error(`Erro ${res.status} em ${path}`);
  return res.json() as Promise<T>;
}

async function garantirLogin() {
  if (token) return;
  const r = await call<{ access_token: string }>("/v1/auth/demo", { method: "POST" });
  token = r.access_token;
}

export async function gerarTreino(minutos: number, foco: string) {
  await garantirLogin();
  return call<Treino>("/v1/treinos/gerar", {
    method: "POST",
    body: JSON.stringify({ minutos, foco }),
  });
}

export async function iniciarDescanso(treinoId: string, ordem: number) {
  await garantirLogin();
  return call<Descanso>(`/v1/treinos/${treinoId}/descanso`, {
    method: "POST",
    body: JSON.stringify({ ordem }),
  });
}

export async function concluirExercicio(treinoId: string, ordem: number) {
  await garantirLogin();
  return call<Concluido>(`/v1/treinos/${treinoId}/exercicio/${ordem}/concluir`, { method: "POST" });
}
