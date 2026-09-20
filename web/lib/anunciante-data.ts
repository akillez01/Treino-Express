// Dados de exemplo do painel do anunciante (espelham o protótipo do handoff).
// Trocar por /anunciante/* (docs/05-api-e-websocket.md) quando existir no backend.

export const CAMPAIGNS = [
  { name: "15% OFF linha de whey", gym: "Iron Factory", window: "Descanso · 06h–22h", impressions: 18420, scans: 1204, spend: 1480, active: true },
  { name: "Combo creatina + coqueteleira", gym: "Iron Factory", window: "Descanso · 17h–21h", impressions: 9860, scans: 731, spend: 940, active: true },
  { name: "Frete grátis acima de R$ 150", gym: "Power House", window: "Intervalo entre séries", impressions: 12250, scans: 508, spend: 1120, active: false },
  { name: "Pré-treino 20% OFF", gym: "Studio Alta", window: "Descanso · 06h–10h", impressions: 6740, scans: 392, spend: 610, active: true },
];

export const SERIES = {
  "7 dias": [
    ["Seg", 148, 46], ["Ter", 192, 61], ["Qua", 171, 52], ["Qui", 210, 74],
    ["Sex", 244, 88], ["Sáb", 138, 41], ["Dom", 96, 27],
  ],
  "30 dias": [
    ["S1", 812, 244], ["S2", 934, 291], ["S3", 1102, 358], ["S4", 1289, 421],
  ],
} as Record<string, [string, number, number][]>;
export type Periodo = "7 dias" | "30 dias";

export const HOURS: [string, number][] = [
  ["06–09", 312], ["09–12", 168], ["12–15", 204], ["15–18", 241], ["18–21", 398], ["21–23", 127],
];

export const CREATIVES = [
  { name: "15% OFF linha de whey", scans: 1204, redeems: 421, spend: 1480 },
  { name: "Pré-treino 20% OFF", scans: 392, redeems: 118, spend: 610 },
  { name: "Combo creatina + coqueteleira", scans: 731, redeems: 197, spend: 940 },
  { name: "Frete grátis acima de R$ 150", scans: 508, redeems: 96, spend: 1120 },
];

export const GYMS = [
  { name: "Iron Factory", district: "Vila Prudente · 2 unidades", screens: "6 telas", impressions: 28280, scans: 1935, redeems: 618, spend: 2420 },
  { name: "Power House", district: "Mooca", screens: "3 telas", impressions: 12250, scans: 508, redeems: 96, spend: 1120 },
  { name: "Studio Alta", district: "Tatuapé", screens: "2 telas", impressions: 6740, scans: 392, redeems: 118, spend: 610 },
];

export const INVOICES = [
  { date: "15/09", desc: "Recarga de crédito · Stripe", amount: 2000, doc: "NF 1042", status: "pago" },
  { date: "08/09", desc: "Consumo de impressões · 1ª quinzena", amount: 1284, doc: "NF 1031", status: "pago" },
  { date: "01/09", desc: "Recarga de crédito · Stripe", amount: 1500, doc: "NF 1018", status: "pago" },
  { date: "24/08", desc: "Consumo de impressões · 2ª quinzena", amount: 1106, doc: "NF 0994", status: "pago" },
  { date: "17/08", desc: "Recarga de crédito · boleto", amount: 1000, doc: "—", status: "expirado" },
];

export const TOPUPS = [500, 1000, 2000, 5000];

export const fmt = (n: number) => n.toLocaleString("pt-BR");
export const pct = (n: number) => (n * 100).toFixed(1).replace(".", ",") + "%";
