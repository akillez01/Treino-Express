// Dados de exemplo do painel da academia (espelham o protótipo do handoff).
// Trocar por chamadas a /academia/* (docs/05-api-e-websocket.md) quando o
// backend do gestor existir.

export type Pay = "em dia" | "pendente" | "atrasado";

export const STUDENTS: {
  name: string;
  email: string;
  plan: string;
  since: string;
  freq: number;
  checkin: string;
  fee: number;
  pay: Pay;
}[] = [
  { name: "Marina Rodrigues", email: "marina.r@email.com", plan: "Anual", since: "Mar 2024", freq: 5, checkin: "Hoje, 07h12", fee: 129.9, pay: "em dia" },
  { name: "Diego Santana", email: "diego.s@email.com", plan: "Mensal", since: "Jan 2026", freq: 4, checkin: "Hoje, 06h40", fee: 159.9, pay: "em dia" },
  { name: "Camila Teixeira", email: "camila.t@email.com", plan: "Trimestral", since: "Ago 2025", freq: 3, checkin: "Ontem, 19h05", fee: 139.9, pay: "atrasado" },
  { name: "Rafael Lima", email: "rafa.lima@email.com", plan: "Mensal", since: "Mai 2026", freq: 4, checkin: "Ontem, 20h48", fee: 159.9, pay: "em dia" },
  { name: "Júlia Prado", email: "julia.p@email.com", plan: "Anual", since: "Fev 2023", freq: 2, checkin: "3 dias atrás", fee: 129.9, pay: "pendente" },
  { name: "Lucas Moraes", email: "lucas.m@email.com", plan: "Mensal", since: "Jul 2026", freq: 6, checkin: "Hoje, 12h20", fee: 159.9, pay: "em dia" },
  { name: "Beatriz Alencar", email: "bia.alencar@email.com", plan: "Trimestral", since: "Set 2025", freq: 3, checkin: "Hoje, 08h55", fee: 139.9, pay: "em dia" },
  { name: "Thiago Nunes", email: "thiago.n@email.com", plan: "Mensal", since: "Abr 2026", freq: 1, checkin: "8 dias atrás", fee: 159.9, pay: "atrasado" },
  { name: "Renata Vasques", email: "renata.v@email.com", plan: "Anual", since: "Nov 2024", freq: 4, checkin: "Ontem, 07h30", fee: 129.9, pay: "em dia" },
  { name: "Paulo Bastos", email: "paulo.b@email.com", plan: "Mensal", since: "Ago 2026", freq: 2, checkin: "4 dias atrás", fee: 159.9, pay: "pendente" },
];

export const SCREENS = [
  { room: "Sala de musculação", playing: "Nutri Prime · 15% OFF na linha de whey", uptime: "99,4%", sync: "há 3s", res: "1920×1080", scans: "412" },
  { room: "Área de cardio", playing: "Jukebox · Ritmo de Ferro — Banda Alta Carga", uptime: "98,1%", sync: "há 5s", res: "1920×1080", scans: "268" },
  { room: "Sala de funcional", playing: "Açaí do Ponto · 20% OFF na tigela pós-treino", uptime: "96,8%", sync: "há 2s", res: "1366×768", scans: "151" },
];

export const QUEUE = [
  { title: "Não Vou Parar", artist: "Bloco do Ritmo", requester: "Marina R.", dur: "3:12" },
  { title: "Peso Morto", artist: "Trio Cadência", requester: "Diego S.", dur: "2:58" },
  { title: "Meia Noite no Cardio", artist: "Áurea Base", requester: "Camila T.", dur: "3:44" },
  { title: "Série Final", artist: "Coletivo Norte", requester: "Rafa L.", dur: "4:02" },
  { title: "Sem Intervalo", artist: "Mila Duarte", requester: "Júlia P.", dur: "3:21" },
];

export type Origem = "Mensalidade" | "Anúncio" | "Jukebox";
export type StatusMov = "liquidado" | "a receber" | "recusado";

export const TRANSACTIONS: { date: string; desc: string; origin: Origem; amount: number; status: StatusMov }[] = [
  { date: "15/09", desc: "Mensalidades · lote diário (38 cobranças)", origin: "Mensalidade", amount: 5236.2, status: "liquidado" },
  { date: "14/09", desc: "Nutri Prime Suplementos · campanha whey", origin: "Anúncio", amount: 1480.0, status: "liquidado" },
  { date: "12/09", desc: "Jukebox · pedidos avulsos da semana", origin: "Jukebox", amount: 312.0, status: "liquidado" },
  { date: "10/09", desc: "Açaí do Ponto · campanha tigela pós-treino", origin: "Anúncio", amount: 860.0, status: "a receber" },
  { date: "08/09", desc: "Mensalidades · retentativa de cobrança", origin: "Mensalidade", amount: 479.7, status: "recusado" },
  { date: "05/09", desc: "Fisio Movimento · avaliação postural", origin: "Anúncio", amount: 640.0, status: "liquidado" },
];

export const PAYOUTS = [
  { advertiser: "Nutri Prime Suplementos", date: "15/09", gross: 1480, status: "pago" },
  { advertiser: "Açaí do Ponto", date: "10/09", gross: 860, status: "em trânsito" },
  { advertiser: "Fisio Movimento", date: "05/09", gross: 640, status: "pago" },
  { advertiser: "Loja Iron Wear", date: "02/09", gross: 1120, status: "pago" },
];

export const MONTHS = {
  "Set 2026": { students: 412, mrr: 58940, ads: 7310, overdue: 4.2, closing: "30/09" },
  "Ago 2026": { students: 398, mrr: 56120, ads: 6480, overdue: 5.1, closing: "31/08" },
  "Jul 2026": { students: 381, mrr: 53870, ads: 5210, overdue: 6.4, closing: "31/07" },
} as const;
export type Mes = keyof typeof MONTHS;

export const JUKEBOX_RECEITA = 1240;
export const PAIRING_CODE = "4K7-92B";

export const brl = (n: number) =>
  "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const brlShort = (n: number) => "R$ " + n.toLocaleString("pt-BR");
export const initials = (name: string) =>
  name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("");
