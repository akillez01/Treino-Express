"use client";

import type { ReactNode } from "react";
import PanelShell from "@/app/_components/PanelShell";
import s from "@/app/_components/panel.module.css";
import { telasAcademia, useApi } from "@/lib/api";

const ABAS = [
  { href: "/academia", label: "Visão geral", exact: true },
  { href: "/academia/alunos", label: "Alunos" },
  { href: "/academia/financeiro", label: "Financeiro" },
  { href: "/academia/telas", label: "Telas" },
];

function TelasOnline() {
  const { data } = useApi("telas-online", telasAcademia);
  if (!data) return null;
  const pareadas = data.telas.filter((t) => t.pareada_em);
  const online = pareadas.filter((t) => t.status === "online").length;
  return (
    <div className={s.live}>
      <span className={s.dotLive} />
      {online} DE {pareadas.length} TELAS ONLINE
    </div>
  );
}

export default function AcademiaLayout({ children }: { children: ReactNode }) {
  return (
    <PanelShell logo="IF" titulo="Iron Factory" subtitulo="Painel da academia" abas={ABAS} status={<TelasOnline />}>
      {children}
    </PanelShell>
  );
}
