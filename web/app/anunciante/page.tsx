"use client";

import { useState } from "react";
import { brl, brlShort } from "@/lib/academia-data";
import {
  CAMPAIGNS,
  CREATIVES,
  GYMS,
  HOURS,
  INVOICES,
  SERIES,
  TOPUPS,
  fmt,
  pct,
  type Periodo,
} from "@/lib/anunciante-data";
import base from "../academia/academia.module.css";
import x from "./anunciante.module.css";

const NAV = ["Campanhas", "Métricas", "Faturamento"] as const;
type Aba = (typeof NAV)[number];

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

export default function PainelAnunciante() {
  const [aba, setAba] = useState<Aba>("Campanhas");
  const [periodo, setPeriodo] = useState<Periodo>("7 dias");
  const [pausadas, setPausadas] = useState<Record<number, boolean>>({});
  const [recarga, setRecarga] = useState(2000);

  const serie = SERIES[periodo];
  const maxDia = Math.max(...serie.map((d) => d[1]));
  const scans = serie.reduce((a, d) => a + d[1], 0);
  const redeems = serie.reduce((a, d) => a + d[2], 0);
  const impressoes = periodo === "7 dias" ? 12840 : 47180;
  const gasto = periodo === "7 dias" ? 1284 : 4718;
  const hourMax = Math.max(...HOURS.map((h) => h[1]));
  const bestHour = HOURS.reduce((a, b) => (b[1] > a[1] ? b : a));
  const subtitulo = periodo === "7 dias" ? "Últimos 7 dias · todas as academias" : "Últimas 4 semanas · todas as academias";

  const titulos: Record<Aba, [string, string, string]> = {
    Campanhas: ["Painel do anunciante", "Nutri Prime Suplementos", "Anunciando em 3 academias · 11 telas ativas"],
    Métricas: ["Métricas", "Funil e desempenho", `${periodo === "7 dias" ? "Últimos 7 dias" : "Últimas 4 semanas"} · 3 academias · 4 criativos`],
    Faturamento: ["Faturamento", "Crédito e faturas", `Saldo de ${brlShort(3420)} · próximo débito estimado em 18/09`],
  };
  const cta = aba === "Faturamento" ? ["↓", "Baixar extrato"] : aba === "Métricas" ? ["↓", "Exportar relatório"] : ["+", "Nova campanha"];

  const Kpi = ({ label, value, note, delta, ad, color }: { label: string; value: string; note: string; delta?: string; ad?: boolean; color?: string }) => (
    <div className={base.kpi}>
      <div className={base.kpiLabel}>{label}</div>
      <div className={base.kpiValue} style={color ? { color } : undefined}>
        {value}
      </div>
      <div className={base.kpiNote}>
        {delta && <span className={cx(base.delta, ad && base.deltaAd)}>{delta}</span>}
        {note}
      </div>
    </div>
  );

  const splitBars = [
    { label: "Academias parceiras", value: "60%", cor: "var(--accent)", note: "Repassado na hora para a conta Stripe de cada academia que exibiu o anúncio." },
    { label: "Plataforma", value: "30%", cor: "var(--ad)", note: "Operação das telas, medição de QR e suporte às campanhas." },
    { label: "Processamento", value: "10%", cor: "#4f5560", note: "Taxas de cartão e antifraude cobradas pelo Stripe." },
  ];

  return (
    <div className={base.root}>
      <header className={base.top}>
        <div className={base.topIn}>
          <div className={base.brand}>
            <div className={base.logo}>IF</div>
            <div className={base.gym}>Iron Ads</div>
          </div>
          <nav className={base.nav} aria-label="Seções">
            {NAV.map((n) => (
              <button key={n} className={cx(base.navBtn, n === aba && base.navOn)} onClick={() => setAba(n)}>
                {n}
              </button>
            ))}
          </nav>
          <div className={base.grow} />
          <div className={x.account}>
            <span className={x.accountAv}>NP</span>Nutri Prime
          </div>
        </div>
      </header>

      <main className={base.main}>
        <div className={base.headRow}>
          <div>
            <div className={x.eyebrow}>{titulos[aba][0]}</div>
            <h1 className={base.h1}>{titulos[aba][1]}</h1>
            <div className={base.sub}>{titulos[aba][2]}</div>
          </div>
          <div className={x.actions}>
            {aba !== "Faturamento" && (
              <div className={base.seg}>
                {(Object.keys(SERIES) as Periodo[]).map((p) => (
                  <button key={p} className={cx(base.segBtn, p === periodo && base.segOn)} onClick={() => setPeriodo(p)}>
                    {p}
                  </button>
                ))}
              </div>
            )}
            <button className={x.ctaBtn}>
              <span style={{ fontSize: 16 }}>{cta[0]}</span>
              {cta[1]}
            </button>
          </div>
        </div>

        {aba === "Campanhas" && (
          <>
            <div className={base.kpis}>
              <Kpi label="Impressões na TV" value={fmt(impressoes)} delta="+12,4%" note="vs. período anterior" />
              <Kpi label="QR escaneados" value={fmt(scans)} delta={`${((scans / impressoes) * 100).toFixed(1)}%`} note="taxa de escaneamento" />
              <Kpi label="Cupons resgatados" value={fmt(redeems)} delta={`${((redeems / scans) * 100).toFixed(0)}%`} ad note="conversão em loja" />
              <Kpi label="Custo por resgate" value={brl(gasto / redeems)} delta="−8,1%" note="queda no período" />
            </div>

            <div className={base.two}>
              <div className={cx(base.card, x.chartSpan)}>
                <div className={base.tableHead} style={{ padding: 0, border: 0 }}>
                  <div>
                    <div className={base.cardTitle}>QR escaneados por dia</div>
                    <div className={base.cardSub}>{subtitulo}</div>
                  </div>
                  <div className={x.legendRow}>
                    <span className={x.legendItem}>
                      <span className={base.sw} style={{ background: "var(--accent)" }} />
                      Escaneados
                    </span>
                    <span className={x.legendItem}>
                      <span className={base.sw} style={{ background: "var(--ad)" }} />
                      Resgatados
                    </span>
                  </div>
                </div>
                <div className={x.chart}>
                  {serie.map(([label, sc, rd]) => (
                    <div key={label} className={x.chartCol}>
                      <div className={x.bars}>
                        <div className={x.bar} style={{ height: `${(sc / maxDia) * 100}%`, background: "var(--accent)" }} />
                        <div className={x.bar} style={{ height: `${(rd / maxDia) * 100}%`, background: "var(--ad)" }} />
                      </div>
                      <div className={x.axis}>{label}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className={base.card}>
                <div className={base.cardTitle}>Saldo da conta</div>
                <div className={base.big}>{brlShort(3420)}</div>
                <div className={base.cardSub}>Rende até 18 dias de exibição no ritmo atual</div>
                <div className={x.meter}>
                  <div className={x.meterFill} style={{ width: "62%" }} />
                </div>
                <button className={x.secondary} onClick={() => setAba("Faturamento")}>
                  Adicionar crédito
                </button>
                <div className={x.splitRows}>
                  <div className={x.splitRow}>
                    <span>Repasse às academias (60%)</span>
                    <b>{brl(gasto * 0.6)}</b>
                  </div>
                  <div className={x.splitRow}>
                    <span>Taxa da plataforma (30%)</span>
                    <b>{brl(gasto * 0.3)}</b>
                  </div>
                  <div className={x.splitRow}>
                    <span>Processamento (10%)</span>
                    <b>{brl(gasto * 0.1)}</b>
                  </div>
                </div>
              </div>
            </div>

            <div className={base.tableCard}>
              <div className={base.tableHead}>
                <div className={base.cardTitle}>Campanhas</div>
                <div className={base.gymSub}>Clique no status para pausar ou reativar</div>
              </div>
              <div className={base.scroll}>
                <div className={cx(base.row, base.rowHead, x.colCamp)}>
                  <div>Campanha</div>
                  <div>Academia</div>
                  <div>Impressões</div>
                  <div>Escaneados</div>
                  <div>Investido</div>
                  <div style={{ textAlign: "right" }}>Status</div>
                </div>
                {CAMPAIGNS.map((c, i) => {
                  const ativa = pausadas[i] !== undefined ? !pausadas[i] : c.active;
                  return (
                    <div key={c.name} className={cx(base.row, x.colCamp)}>
                      <div style={{ minWidth: 0 }}>
                        <div className={base.pName}>{c.name}</div>
                        <div className={base.pMail}>{c.window}</div>
                      </div>
                      <div className={base.cell}>{c.gym}</div>
                      <div className={base.strong}>{fmt(c.impressions)}</div>
                      <div className={x.accentNum}>{fmt(c.scans)}</div>
                      <div className={base.strong}>{brl(c.spend)}</div>
                      <button
                        className={cx(x.statusBtn, ativa && x.statusOn)}
                        onClick={() => setPausadas((p) => ({ ...p, [i]: ativa }))}
                      >
                        {ativa ? "ATIVA" : "PAUSADA"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {aba === "Métricas" && (
          <>
            <div className={base.card} style={{ marginTop: 26 }}>
              <div className={base.cardTitle}>Funil de conversão</div>
              <div className={base.cardSub}>{subtitulo}</div>
              <div className={x.funnel}>
                {[
                  { label: "Impressões na TV", valor: fmt(impressoes), rate: "100%", rateCor: "rgba(244,245,243,.6)", w: 100, cor: "#4f5560", note: "Anúncio exibido durante o descanso do aluno" },
                  { label: "QR escaneados", valor: fmt(scans), rate: pct(scans / impressoes), rateCor: "var(--accent)", w: Math.min((scans / impressoes) * 100 * 6, 100), cor: "var(--accent)", note: "Aluno apontou o celular para a tela da academia" },
                  { label: "Cupons resgatados", valor: fmt(redeems), rate: pct(redeems / scans), rateCor: "#ff9d6e", w: (redeems / scans) * 100, cor: "var(--ad)", note: "Compra concluída na loja com o cupom" },
                ].map((f) => (
                  <div key={f.label}>
                    <div className={x.fTop}>
                      <div className={x.fLabel}>{f.label}</div>
                      <div className={x.fVal}>
                        <div className={x.fNum}>{f.valor}</div>
                        <div className={x.fRate} style={{ color: f.rateCor }}>
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

            <div className={base.two}>
              <div className={base.card}>
                <div className={base.cardTitle}>Melhores horários</div>
                <div className={base.cardSub}>Escaneamentos por faixa de horário</div>
                <div className={x.hours}>
                  {HOURS.map(([label, v]) => (
                    <div key={label} className={x.hCol}>
                      <div className={x.hVal}>{fmt(v)}</div>
                      <div className={x.hBarBox}>
                        <div className={x.hBar} style={{ height: `${(v / hourMax) * 100}%`, background: v === hourMax ? "var(--accent)" : "#3a4048" }} />
                      </div>
                      <div className={x.axis} style={{ fontSize: 10 }}>
                        {label}
                      </div>
                    </div>
                  ))}
                </div>
                <div className={x.insight}>
                  A faixa {bestHour[0]}h concentra {pct(bestHour[1] / HOURS.reduce((a, h) => a + h[1], 0))} dos escaneamentos. Vale concentrar verba nesse intervalo.
                </div>
              </div>

              <div className={base.card}>
                <div className={base.cardTitle}>Desempenho por criativo</div>
                <div className={base.cardSub}>Ordenado por taxa de resgate</div>
                <div className={x.crList}>
                  {CREATIVES.map((c) => {
                    const rate = c.redeems / c.scans;
                    const cor = rate > 0.3 ? "var(--accent)" : "var(--ad)";
                    return (
                      <div key={c.name} className={x.cr}>
                        <div className={base.payTop}>
                          <div className={base.payName}>{c.name}</div>
                          <div style={{ fontSize: 15, fontWeight: 800, color: cor, flex: "none" }}>{pct(rate)}</div>
                        </div>
                        <div className={x.crTrack}>
                          <div style={{ height: "100%", width: `${Math.min(rate * 100 * 2.4, 100)}%`, background: cor }} />
                        </div>
                        <div className={x.crDetail}>
                          {fmt(c.scans)} escaneados · {fmt(c.redeems)} resgates · {brl(c.spend / c.redeems)} por resgate
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className={base.tableCard}>
              <div className={base.tableHead}>
                <div className={base.cardTitle}>Desempenho por academia</div>
              </div>
              <div className={base.scroll}>
                <div className={cx(base.row, base.rowHead, x.colGym)}>
                  <div>Academia</div>
                  <div>Telas</div>
                  <div>Impressões</div>
                  <div>Escaneados</div>
                  <div>Taxa de resgate</div>
                  <div>Custo/resgate</div>
                </div>
                {GYMS.map((g) => (
                  <div key={g.name} className={cx(base.row, x.colGym)}>
                    <div style={{ minWidth: 0 }}>
                      <div className={base.pName}>{g.name}</div>
                      <div className={base.pMail}>{g.district}</div>
                    </div>
                    <div className={base.cell}>{g.screens}</div>
                    <div className={base.strong}>{fmt(g.impressions)}</div>
                    <div className={x.accentNum}>{fmt(g.scans)}</div>
                    <div className={x.miniBar}>
                      <div className={x.miniTrack}>
                        <div className={x.miniFill} style={{ width: `${Math.min((g.redeems / g.scans) * 100 * 2.4, 100)}%` }} />
                      </div>
                      {pct(g.redeems / g.scans)}
                    </div>
                    <div className={base.strong}>{brl(g.spend / g.redeems)}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {aba === "Faturamento" && (
          <>
            <div className={base.kpis}>
              <Kpi label="Saldo disponível" value={brlShort(3420)} note="rende cerca de 18 dias de exibição" />
              <Kpi label="Investido no mês" value={brlShort(4150)} note="consumo por impressão entregue" />
              <Kpi label="Repassado às academias" value={brlShort(2490)} color="#ff9d6e" note="60% via Stripe Connect" />
              <Kpi label="Custo médio por resgate" value={brl(4150 / 1029)} note="1.029 resgates no mês" />
            </div>

            <div className={base.two}>
              <div className={base.card}>
                <div className={base.cardTitle}>Recarregar crédito</div>
                <div className={base.cardSub}>O valor é debitado por impressão entregue</div>
                <div className={x.topups}>
                  {TOPUPS.map((v) => (
                    <button key={v} className={cx(x.topup, v === recarga && x.topupOn)} onClick={() => setRecarga(v)}>
                      <div className={x.topupV}>{brlShort(v)}</div>
                      <div className={x.topupN}>{Math.round(v / 190)} dias de exibição</div>
                    </button>
                  ))}
                </div>
                <button className={x.pay}>Pagar {brlShort(recarga)} com Stripe</button>
                <div className={x.cardOnFile}>
                  <div className={x.visa}>VISA</div>
                  <div className={base.grow1}>
                    <div className={base.room}>•••• 4242</div>
                    <div className={base.pMail}>Cartão padrão · vence 09/2028</div>
                  </div>
                  <button className={base.link}>Trocar</button>
                </div>
              </div>

              <div className={base.card}>
                <div className={base.cardTitle}>Para onde vai o seu investimento</div>
                <div className={base.cardSub}>Split executado pelo Stripe Connect em cada cobrança</div>
                <div className={base.stack} style={{ marginTop: 22 }}>
                  {splitBars.map((b) => (
                    <div key={b.label} style={{ width: b.value, background: b.cor }} />
                  ))}
                </div>
                <div className={x.splitBars}>
                  {splitBars.map((b) => (
                    <div key={b.label} className={x.splitItem}>
                      <span className={base.sw} style={{ background: b.cor, marginTop: 4 }} />
                      <div className={base.grow1}>
                        <div className={base.payTop}>
                          <div className={base.legT}>{b.label}</div>
                          <div className={base.legV}>{b.value}</div>
                        </div>
                        <div className={x.splitNote}>{b.note}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className={base.tableCard}>
              <div className={base.tableHead}>
                <div className={base.cardTitle}>Histórico de faturas</div>
              </div>
              <div className={base.scroll}>
                <div className={cx(base.row, base.rowHead, x.colInv)}>
                  <div>Data</div>
                  <div>Descrição</div>
                  <div>Valor</div>
                  <div>Nota</div>
                  <div style={{ textAlign: "right" }}>Status</div>
                </div>
                {INVOICES.map((i) => (
                  <div key={i.date + i.desc} className={cx(base.row, x.colInv)}>
                    <div className={base.cell}>{i.date}</div>
                    <div className={base.pName}>{i.desc}</div>
                    <div className={base.strong}>{brl(i.amount)}</div>
                    <div className={x.accentNum} style={{ fontSize: 12 }}>
                      {i.doc}
                    </div>
                    <div className={cx(base.badge, i.status === "pago" && base.ok)}>{i.status}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
