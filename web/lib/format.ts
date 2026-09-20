export const brl = (centavos: number) =>
  "R$ " + (centavos / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const brlShort = (centavos: number) =>
  "R$ " + Math.round(centavos / 100).toLocaleString("pt-BR");

export const fmt = (n: number) => n.toLocaleString("pt-BR");

export const pct = (razao: number) => (razao * 100).toFixed(1).replace(".", ",") + "%";

export const initials = (nome: string) =>
  nome
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

export const rotuloMes = (aaaamm: string) => {
  const [a, m] = aaaamm.split("-");
  return `${MESES[Number(m) - 1]} ${a}`;
};

/** Últimos `n` meses (AAAA-MM), do mais recente para o mais antigo. */
export const ultimosMeses = (n = 3) => {
  const hoje = new Date();
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
};

export const dataCurta = (iso: string) => {
  const [, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}`;
};

export const desde = (iso: string) => {
  const [a, m] = iso.slice(0, 10).split("-");
  return `${MESES[Number(m) - 1]} ${a}`;
};

/** "Hoje, 07h12", "Ontem, 19h05", "3 dias atrás". */
export const quando = (iso: string | null) => {
  if (!iso) return "—";
  const d = new Date(iso);
  const hoje = new Date();
  const dias = Math.round(
    (new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate()).getTime() -
      new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()) /
      86_400_000,
  );
  const hora = `${String(d.getHours()).padStart(2, "0")}h${String(d.getMinutes()).padStart(2, "0")}`;
  if (dias <= 0) return `Hoje, ${hora}`;
  if (dias === 1) return `Ontem, ${hora}`;
  return `${dias} dias atrás`;
};

export const segundosAtras = (iso: string | null) => {
  if (!iso) return "sem sinal";
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `há ${s}s`;
  if (s < 3600) return `há ${Math.round(s / 60)} min`;
  if (s < 86400) return `há ${Math.round(s / 3600)} h`;
  return `há ${Math.round(s / 86400)} d`;
};

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

export const SITUACAO: Record<string, string> = { em_dia: "em dia", pendente: "pendente", atrasado: "atrasado" };
