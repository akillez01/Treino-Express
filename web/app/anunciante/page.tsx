"use client";

import Link from "next/link";
import { useState } from "react";
import Carga from "@/app/_components/Estado";
import Kpi, { variacao } from "@/app/_components/Kpi";
import s from "@/app/_components/panel.module.css";
import { alterarCampanha, campanhasAnunciante, useApi, type Periodo } from "@/lib/api";
import { brl, brlShort, cx, fmt } from "@/lib/format";
import x from "./anunciante.module.css";

const DIAS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const rotuloDia = (iso: string, periodo: Periodo, i: number) => {
  if (periodo === "7d") return DIAS[new Date(iso + "T12:00:00").getDay()];
  const [, m, d] = iso.split("-");
  return i % 5 === 0 ? `${d}/${m}` : "";
};

export default function Campanhas() {
  const [periodo, setPeriodo] = useState<Periodo>("7d");
  const dados = useApi(`camp-${periodo}`, () => campanhasAnunciante(periodo));
  const [busy, setBusy] = useState<string | null>(null);

  async function alternar(id: string, ativa: boolean) {
    setBusy(id);
    try {
      await alterarCampanha(id, ativa);
      dados.recarregar();
    } finally {
      setBusy(null);
    }
  }

  return (
    <Carga estado={dados}>
      {(d) => {
        const t = d.totais;
        const a = d.anterior;
        const max = Math.max(1, ...d.serie.map((p) => p.scans));
        const custoResgate = t.resgates ? t.gasto / t.resgates : 0;
        const custoAnt = a.resgates ? a.gasto / a.resgates : 0;
        const rotulo = periodo === "7d" ? "Últimos 7 dias" : "Últimos 30 dias";
        const split = [
          { label: "Repasse às academias (60%)", v: t.gasto * 0.6 },
          { label: "Taxa da plataforma (30%)", v: t.gasto * 0.3 },
          { label: "Processamento (10%)", v: t.gasto * 0.1 },
        ];
        const diasSaldo = t.gasto ? Math.floor(d.conta.saldo_centavos / (t.gasto / (periodo === "7d" ? 7 : 30))) : 0;
        return (
          <>
            <div className={s.headRow}>
              <div>
                <div className={x.eyebrow}>Painel do anunciante</div>
                <h1 className={s.h1}>{d.conta.nome}</h1>
                <div className={s.sub}>
                  Anunciando em {d.academias} academias · {d.telas} telas ativas
                </div>
              </div>
              <div className={x.actions}>
                <div className={s.seg} role="tablist" aria-label="Período">
                  {(["7d", "30d"] as Periodo[]).map((p) => (
                    <button key={p} role="tab" aria-selected={p === periodo} className={cx(s.segBtn, p === periodo && s.segOn)} onClick={() => setPeriodo(p)}>
                      {p === "7d" ? "7 dias" : "30 dias"}
                    </button>
                  ))}
                </div>
                <button className={x.ctaBtn} disabled title="Em breve">
                  <span style={{ fontSize: 16 }}>+</span>Nova campanha
                </button>
              </div>
            </div>

            <div className={s.kpis}>
              <Kpi label="Impressões na TV" value={fmt(t.impressoes)} delta={variacao(t.impressoes, a.impressoes)} note="vs. período anterior" />
              <Kpi label="QR escaneados" value={fmt(t.scans)} delta={t.impressoes ? `${((t.scans / t.impressoes) * 100).toFixed(1).replace(".", ",")}%` : undefined} note="taxa de escaneamento" />
              <Kpi label="Cupons resgatados" value={fmt(t.resgates)} delta={t.scans ? `${Math.round((t.resgates / t.scans) * 100)}%` : undefined} ad note="conversão em loja" />
              <Kpi label="Custo por resgate" value={brl(custoResgate)} delta={variacao(custoResgate, custoAnt)} note="vs. período anterior" />
            </div>

            <div className={s.two}>
              <div className={cx(s.card, x.chartSpan)}>
                <div className={s.spread}>
                  <div>
                    <div className={s.cardTitle}>QR escaneados por dia</div>
                    <div className={s.cardSub}>{rotulo} · todas as academias</div>
                  </div>
                  <div className={x.legendRow}>
                    <span className={x.legendItem}>
                      <span className={s.sw} style={{ background: "var(--accent)" }} />
                      Escaneados
                    </span>
                    <span className={x.legendItem}>
                      <span className={s.sw} style={{ background: "var(--ad)" }} />
                      Resgatados
                    </span>
                  </div>
                </div>
                <div className={x.chart}>
                  {d.serie.map((p, i) => (
                    <div key={p.dia} className={x.chartCol} title={`${p.dia}: ${p.scans} escaneados, ${p.resgates} resgatados`}>
                      <div className={x.bars}>
                        <div className={x.bar} style={{ height: `${(p.scans / max) * 100}%`, background: "var(--accent)" }} />
                        <div className={x.bar} style={{ height: `${(p.resgates / max) * 100}%`, background: "var(--ad)" }} />
                      </div>
                      <div className={x.axis}>{rotuloDia(p.dia, periodo, i)}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className={s.card}>
                <div className={s.cardTitle}>Saldo da conta</div>
                <div className={s.big}>{brlShort(d.conta.saldo_centavos)}</div>
                <div className={s.cardSub}>{diasSaldo ? `Rende até ${diasSaldo} dias de exibição no ritmo atual` : "Sem consumo no período"}</div>
                <div className={x.meter}>
                  <div className={x.meterFill} style={{ width: `${Math.min(diasSaldo / 30, 1) * 100}%` }} />
                </div>
                <Link href="/anunciante/faturamento" className={x.secondary}>
                  Adicionar crédito
                </Link>
                <div className={x.splitRows}>
                  {split.map((r) => (
                    <div key={r.label} className={x.splitRow}>
                      <span>{r.label}</span>
                      <b>{brl(r.v)}</b>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Campanhas</div>
                <div className={s.gymSub}>Clique no status para pausar ou reativar</div>
              </div>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, x.colCamp)}>
                  <div>Campanha</div>
                  <div>Academia</div>
                  <div>Impressões</div>
                  <div>Escaneados</div>
                  <div>Investido</div>
                  <div style={{ textAlign: "right" }}>Status</div>
                </div>
                {d.campanhas.map((c) => {
                  const ativa = c.status === "ativa";
                  const editavel = c.status === "ativa" || c.status === "pausada";
                  return (
                    <div key={c.id} className={cx(s.row, x.colCamp)}>
                      <div style={{ minWidth: 0 }}>
                        <div className={s.pName}>{c.nome}</div>
                        <div className={s.pMail}>Descanso · {c.janela}</div>
                      </div>
                      <div className={s.cell}>{c.academia}</div>
                      <div className={s.strong}>{fmt(c.impressoes)}</div>
                      <div className={x.accentNum}>{fmt(c.scans)}</div>
                      <div className={s.strong}>{brl(c.gasto)}</div>
                      <button className={cx(x.statusBtn, ativa && x.statusOn)} disabled={!editavel || busy === c.id} onClick={() => alternar(c.id, !ativa)}>
                        {c.status.toUpperCase()}
                      </button>
                    </div>
                  );
                })}
              </div>
              {d.campanhas.length === 0 && <div className={s.vazio}>Nenhuma campanha ainda.</div>}
            </div>
          </>
        );
      }}
    </Carga>
  );
}
