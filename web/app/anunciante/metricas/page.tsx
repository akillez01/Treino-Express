"use client";

import { useState } from "react";
import Carga from "@/app/_components/Estado";
import s from "@/app/_components/panel.module.css";
import { metricasAnunciante, useApi, type Periodo } from "@/lib/api";
import { brl, cx, fmt, pct } from "@/lib/format";
import x from "../anunciante.module.css";

export default function Metricas() {
  const [periodo, setPeriodo] = useState<Periodo>("7d");
  const dados = useApi(`met-${periodo}`, () => metricasAnunciante(periodo));

  return (
    <Carga estado={dados}>
      {(d) => {
        const t = d.totais;
        const rotulo = periodo === "7d" ? "Últimos 7 dias" : "Últimos 30 dias";
        const hourMax = Math.max(1, ...d.horas.map((h) => h.scans));
        const totalHoras = d.horas.reduce((a, h) => a + h.scans, 0);
        const melhor = d.horas.reduce((a, b) => (b.scans > a.scans ? b : a), d.horas[0]);
        const criativos = [...d.criativos]
          .filter((c) => c.scans > 0)
          .sort((a, b) => b.resgates / b.scans - a.resgates / a.scans);
        const funil = [
          { label: "Impressões na TV", valor: fmt(t.impressoes), rate: "100%", cor: "#4f5560", w: 100, corRate: "rgba(244,245,243,.6)", note: "Anúncio exibido durante o descanso do aluno" },
          { label: "QR escaneados", valor: fmt(t.scans), rate: t.impressoes ? pct(t.scans / t.impressoes) : "—", cor: "var(--accent)", w: t.impressoes ? Math.min((t.scans / t.impressoes) * 600, 100) : 0, corRate: "var(--accent)", note: "Aluno apontou o celular para a tela da academia" },
          { label: "Cupons resgatados", valor: fmt(t.resgates), rate: t.scans ? pct(t.resgates / t.scans) : "—", cor: "var(--ad)", w: t.scans ? (t.resgates / t.scans) * 100 : 0, corRate: "#ff9d6e", note: "Compra concluída na loja com o cupom" },
        ];
        return (
          <>
            <div className={s.headRow}>
              <div>
                <div className={x.eyebrow}>Métricas</div>
                <h1 className={s.h1}>Funil e desempenho</h1>
                <div className={s.sub}>
                  {rotulo} · {d.academias.length} academias · {d.criativos.length} criativos
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
                  <span style={{ fontSize: 16 }}>↓</span>Exportar relatório
                </button>
              </div>
            </div>

            <div className={s.card} style={{ marginTop: 26 }}>
              <div className={s.cardTitle}>Funil de conversão</div>
              <div className={s.cardSub}>{rotulo} · todas as academias</div>
              <div className={x.funnel}>
                {funil.map((f) => (
                  <div key={f.label}>
                    <div className={x.fTop}>
                      <div className={x.fLabel}>{f.label}</div>
                      <div className={x.fVal}>
                        <div className={x.fNum}>{f.valor}</div>
                        <div className={x.fRate} style={{ color: f.corRate }}>
                          {f.rate}
                        </div>
                      </div>
                    </div>
                    <div className={x.fTrack}>
                      <div className={x.fFill} style={{ width: `${f.w}%`, background: f.cor }} />
                    </div>
                    <div className={x.fNote}>{f.note}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className={s.two}>
              <div className={s.card}>
                <div className={s.cardTitle}>Melhores horários</div>
                <div className={s.cardSub}>Escaneamentos por faixa de horário</div>
                <div className={x.hours}>
                  {d.horas.map((h) => (
                    <div key={h.faixa} className={x.hCol}>
                      <div className={x.hVal}>{fmt(h.scans)}</div>
                      <div className={x.hBarBox}>
                        <div className={x.hBar} style={{ height: `${(h.scans / hourMax) * 100}%`, background: h.scans === hourMax ? "var(--accent)" : "#3a4048" }} />
                      </div>
                      <div className={x.axis} style={{ fontSize: 10 }}>
                        {h.faixa}
                      </div>
                    </div>
                  ))}
                </div>
                {totalHoras > 0 && (
                  <div className={x.insight}>
                    A faixa {melhor.faixa}h concentra {pct(melhor.scans / totalHoras)} dos escaneamentos. Vale concentrar verba nesse intervalo.
                  </div>
                )}
              </div>

              <div className={s.card}>
                <div className={s.cardTitle}>Desempenho por criativo</div>
                <div className={s.cardSub}>Ordenado por taxa de resgate</div>
                <div className={x.crList}>
                  {criativos.length === 0 && <div className={s.vazio}>Sem escaneamentos no período.</div>}
                  {criativos.map((c) => {
                    const rate = c.resgates / c.scans;
                    const cor = rate > 0.3 ? "var(--accent)" : "var(--ad)";
                    return (
                      <div key={c.nome} className={x.cr}>
                        <div className={s.payTop}>
                          <div className={s.payName}>{c.nome}</div>
                          <div style={{ fontSize: 15, fontWeight: 800, color: cor, flex: "none" }}>{pct(rate)}</div>
                        </div>
                        <div className={x.crTrack}>
                          <div style={{ height: "100%", width: `${Math.min(rate * 240, 100)}%`, background: cor }} />
                        </div>
                        <div className={x.crDetail}>
                          {fmt(c.scans)} escaneados · {fmt(c.resgates)} resgates · {c.resgates ? brl(c.gasto / c.resgates) : "—"} por resgate
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Desempenho por academia</div>
              </div>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, x.colGym)}>
                  <div>Academia</div>
                  <div>Telas</div>
                  <div>Impressões</div>
                  <div>Escaneados</div>
                  <div>Taxa de resgate</div>
                  <div>Custo/resgate</div>
                </div>
                {d.academias.map((g) => (
                  <div key={g.nome} className={cx(s.row, x.colGym)}>
                    <div style={{ minWidth: 0 }}>
                      <div className={s.pName}>{g.nome}</div>
                      <div className={s.pMail}>{g.bairro}</div>
                    </div>
                    <div className={s.cell}>{g.telas} {g.telas === 1 ? "tela" : "telas"}</div>
                    <div className={s.strong}>{fmt(g.impressoes)}</div>
                    <div className={x.accentNum}>{fmt(g.scans)}</div>
                    <div className={x.miniBar}>
                      <div className={x.miniTrack}>
                        <div className={x.miniFill} style={{ width: `${g.scans ? Math.min((g.resgates / g.scans) * 240, 100) : 0}%` }} />
                      </div>
                      {g.scans ? pct(g.resgates / g.scans) : "—"}
                    </div>
                    <div className={s.strong}>{g.resgates ? brl(g.gasto / g.resgates) : "—"}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        );
      }}
    </Carga>
  );
}
