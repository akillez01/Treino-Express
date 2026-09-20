"use client";

import type { ReactNode } from "react";
import PanelShell from "@/app/_components/PanelShell";
import { faturamentoAnunciante, useApi } from "@/lib/api";
import { initials } from "@/lib/format";
import x from "./anunciante.module.css";

const ABAS = [
  { href: "/anunciante", label: "Campanhas", exact: true },
  { href: "/anunciante/metricas", label: "Métricas" },
  { href: "/anunciante/faturamento", label: "Faturamento" },
];

function Conta() {
  const { data } = useApi("conta", faturamentoAnunciante);
  if (!data) return null;
  return (
    <div className={x.account}>
      <span className={x.accountAv}>{initials(data.conta.nome)}</span>
      {data.conta.nome.split(" ").slice(0, 2).join(" ")}
    </div>
  );
}

export default function AnuncianteLayout({ children }: { children: ReactNode }) {
  return (
    <PanelShell logo="IA" titulo="Iron Ads" subtitulo="Painel do anunciante" abas={ABAS} status={<Conta />}>
      {children}
    </PanelShell>
  );
}
