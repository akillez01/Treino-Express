"use client";

import Link from "next/link";
import { useState } from "react";
import {
  JUKEBOX_RECEITA,
  MONTHS,
  PAIRING_CODE,
  PAYOUTS,
  QUEUE,
  SCREENS,
  STUDENTS,
  TRANSACTIONS,
  brl,
  brlShort,
  initials,
  type Mes,
  type Pay,
} from "@/lib/academia-data";
import s from "./academia.module.css";

const NAV = ["Visão geral", "Alunos", "Financeiro", "Telas"] as const;
type Aba = (typeof NAV)[number];
type Filtro = "Todos" | "Em dia" | "Pendente" | "Atrasado";

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");
const payClass = (p: Pay) => (p === "em dia" ? s.ok : p === "atrasado" ? s.bad : "");

export default function PainelAcademia() {
  const [aba, setAba] = useState<Aba>("Visão geral");
  const [mes, setMes] = useState<Mes>("Set 2026");
  const [filtro, setFiltro] = useState<Filtro>("Todos");
  const [pausadas, setPausadas] = useState<Record<number, boolean>>({});

  const m = MONTHS[mes];
  const total = m.mrr + m.ads + JUKEBOX_RECEITA;
  const online = SCREENS.filter((_, i) => !pausadas[i]).length;
  const contagem: Record<Filtro, number> = {
    Todos: STUDENTS.length,
    "Em dia": STUDENTS.filter((x) => x.pay === "em dia").length,
    Pendente: STUDENTS.filter((x) => x.pay === "pendente").length,
    Atrasado: STUDENTS.filter((x) => x.pay === "atrasado").length,
  };
  const alunos = filtro === "Todos" ? STUDENTS : STUDENTS.filter((x) => x.pay === filtro.toLowerCase());
  const alternar = (i: number) => setPausadas((p) => ({ ...p, [i]: !p[i] }));

  const titulos: Record<Aba, [string, string]> = {
    "Visão geral": ["Visão geral", `${mes} · fechamento em ${m.closing}`],
    Alunos: ["Alunos", `${STUDENTS.length} cadastrados nesta unidade · ${contagem["Em dia"]} com pagamento em dia`],
    Financeiro: ["Financeiro", `Mensalidades, anúncios e repasses de ${mes}`],
    Telas: ["Telas", `${SCREENS.length} telas pareadas · ${online} transmitindo agora`],
  };

  const partes = [
    { label: "Mensalidades", note: `${m.students} alunos ativos`, valor: m.mrr, cor: "var(--accent)" },
    { label: "Anúncios na TV", note: "6 anunciantes locais", valor: m.ads, cor: "var(--ad)" },
    { label: "Jukebox", note: "Pedidos avulsos de música", valor: JUKEBOX_RECEITA, cor: "#4f5560" },
  ];

  const Composicao = (
    <div className={s.card}>
      <div className={s.cardTitle}>Composição da receita</div>
      <div className={s.big}>{brlShort(total)}</div>
      <div className={s.stack}>
        {partes.map((p) => (
          <div key={p.label} style={{ width: `${(p.valor / total) * 100}%`, background: p.cor }} />
        ))}
      </div>
      <div className={s.legend}>
        {partes.map((p) => (
          <div key={p.label} className={s.leg}>
            <span className={s.sw} style={{ background: p.cor }} />
            <div className={s.legT}>
              {p.label}
              <div className={s.legN}>{p.note}</div>
            </div>
            <div className={s.legV}>{brlShort(p.valor)}</div>
          </div>
        ))}
      </div>
      {aba === "Financeiro" && (
        <div className={s.foot}>
          <span>Próximo payout</span>
          <span className={s.footStrong}>18/09 · {brlShort(2340)}</span>
        </div>
      )}
    </div>
  );

  const Kpi = ({ label, value, note, delta, ad }: { label: string; value: string; note: string; delta?: string; ad?: boolean }) => (
    <div className={s.kpi}>
      <div className={s.kpiLabel}>{label}</div>
      <div className={s.kpiValue}>{value}</div>
      <div className={s.kpiNote}>
        {delta && <span className={cx(s.delta, ad && s.deltaAd)}>{delta}</span>}
        {note}
      </div>
    </div>
  );

  return (
    <div className={s.root}>
      <header className={s.top}>
        <div className={s.topIn}>
          <div className={s.brand}>
            <div className={s.logo}>IF</div>
            <div>
              <div className={s.gym}>Iron Factory</div>
              <div className={s.gymSub}>Painel da academia</div>
            </div>
          </div>
          <nav className={s.nav} aria-label="Seções">
            {NAV.map((n) => (
              <button key={n} className={cx(s.navBtn, n === aba && s.navOn)} onClick={() => setAba(n)}>
                {n}
              </button>
            ))}
          </nav>
          <div className={s.grow} />
          <div className={s.switcher}>
            <Link href="/">App</Link>
            <Link href="/academia">Academia</Link>
            <Link href="/anunciante">Anunciante</Link>
            <Link href="/tv">TV</Link>
          </div>
          <div className={s.live}>
            <span className={s.dotLive} />
            {online} DE {SCREENS.length} TELAS ONLINE
          </div>
        </div>
      </header>

      <main className={s.main}>
        <div className={s.headRow}>
          <div>
            <h1 className={s.h1}>{titulos[aba][0]}</h1>
            <div className={s.sub}>{titulos[aba][1]}</div>
          </div>
          {(aba === "Visão geral" || aba === "Financeiro") && (
            <div className={s.seg}>
              {(Object.keys(MONTHS) as Mes[]).map((k) => (
                <button key={k} className={cx(s.segBtn, k === mes && s.segOn)} onClick={() => setMes(k)}>
                  {k}
                </button>
              ))}
            </div>
          )}
          {aba === "Alunos" && (
            <div className={s.chips}>
              {(Object.keys(contagem) as Filtro[]).map((f) => (
                <button key={f} className={cx(s.chip, f === filtro && s.chipOn)} onClick={() => setFiltro(f)}>
                  {f}
                  <span className={s.chipCount}>{contagem[f]}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {aba === "Visão geral" && (
          <>
            <div className={s.kpis}>
              <Kpi label="Alunos ativos" value={String(m.students)} delta="+14" note="novos no mês" />
              <Kpi label="Mensalidades" value={brlShort(m.mrr)} delta="+5,0%" note="vs. mês anterior" />
              <Kpi label="Receita de anúncios" value={brlShort(m.ads)} delta="+12,8%" ad note="repasse dos parceiros" />
              <Kpi label="Inadimplência" value={`${m.overdue.toFixed(1).replace(".", ",")}%`} delta="−0,9 p.p." note="queda no mês" />
            </div>

            <div className={s.two}>
              {Composicao}
              <div className={s.card}>
                <div className={s.tableHead} style={{ padding: 0, border: 0 }}>
                  <div className={s.cardTitle}>Telas da academia</div>
                  <div className={s.gymSub}>Toque para pausar</div>
                </div>
                <div className={s.scrList}>
                  {SCREENS.map((sc, i) => {
                    const on = !pausadas[i];
                    return (
                      <button key={sc.room} className={s.scrRow} onClick={() => alternar(i)}>
                        <span className={cx(s.dot, !on && s.dotOff)} />
                        <span className={s.grow1}>
                          <div className={s.room}>{sc.room}</div>
                          <div className={s.playing}>{on ? sc.playing : "Exibição pausada pela academia"}</div>
                        </span>
                        <span className={cx(s.state, !on && s.stateOff)}>{on ? "ONLINE" : "PAUSADA"}</span>
                      </button>
                    );
                  })}
                </div>
                <div className={s.foot}>
                  <span>Fila da Jukebox</span>
                  <span className={s.footAcc}>{QUEUE.length} pedidos · 18 min</span>
                </div>
              </div>
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Últimos check-ins</div>
                <button className={s.link} onClick={() => setAba("Alunos")}>
                  Ver todos os alunos →
                </button>
              </div>
              <div className={s.scroll}>
                {STUDENTS.slice(0, 5).map((st) => (
                  <div key={st.email} className={cx(s.row, s.colRecent)}>
                    <div className={s.person}>
                      <div className={s.av}>{initials(st.name)}</div>
                      <div className={s.pName}>{st.name}</div>
                    </div>
                    <div className={s.cell}>{st.plan}</div>
                    <div className={s.cell}>{st.checkin}</div>
                    <div className={cx(s.badge, payClass(st.pay))}>{st.pay}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {aba === "Alunos" && (
          <>
            <div className={s.kpis}>
              <Kpi label="Cadastrados" value={String(STUDENTS.length)} note="nesta unidade" />
              <Kpi
                label="Frequência média"
                value={`${(STUDENTS.reduce((a, x) => a + x.freq, 0) / STUDENTS.length).toFixed(1).replace(".", ",")}x`}
                note="treinos por semana"
              />
              <Kpi label="Ticket médio" value={brl(STUDENTS.reduce((a, x) => a + x.fee, 0) / STUDENTS.length)} note="mensalidade média" />
              <Kpi label="Em risco" value={String(contagem.Atrasado + contagem.Pendente)} note="pagamento pendente ou atrasado" />
            </div>
            <div className={s.tableCard}>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, s.colStudents)}>
                  <div>Aluno</div>
                  <div>Plano</div>
                  <div>Desde</div>
                  <div>Freq. semanal</div>
                  <div>Último check-in</div>
                  <div>Mensalidade</div>
                  <div style={{ textAlign: "right" }}>Pagamento</div>
                </div>
                {alunos.map((st) => (
                  <div key={st.email} className={cx(s.row, s.colStudents)}>
                    <div className={s.person}>
                      <div className={s.av}>{initials(st.name)}</div>
                      <div style={{ minWidth: 0 }}>
                        <div className={s.pName}>{st.name}</div>
                        <div className={s.pMail}>{st.email}</div>
                      </div>
                    </div>
                    <div className={s.cell}>{st.plan}</div>
                    <div className={s.cell}>{st.since}</div>
                    <div className={s.freq}>
                      <div className={s.freqBar}>
                        <div className={cx(s.freqFill, st.freq < 3 && s.freqLow)} style={{ width: `${(st.freq / 6) * 100}%` }} />
                      </div>
                      {st.freq}x
                    </div>
                    <div className={s.cell}>{st.checkin}</div>
                    <div className={s.strong}>{brl(st.fee)}</div>
                    <div className={cx(s.badge, payClass(st.pay))}>{st.pay}</div>
                  </div>
                ))}
              </div>
              {alunos.length === 0 && <div className={s.empty}>Nenhum aluno neste filtro.</div>}
            </div>
          </>
        )}

        {aba === "Financeiro" && (
          <>
            <div className={s.kpis}>
              <Kpi label="Recebido no mês" value={brlShort(m.mrr + m.ads)} note="mensalidades + anúncios liquidados" />
              <Kpi label="A receber" value={brlShort(2340)} note="faturas em aberto e em trânsito" />
              <Kpi label="Repasse Stripe" value={brlShort(m.ads)} note="split automático dos anunciantes" />
              <Kpi label="Taxas do período" value={brlShort(1462)} note="plataforma + processamento" />
            </div>

            <div className={s.two}>
              <div className={s.card}>
                <div className={s.cardTitle}>Repasses do Stripe Connect</div>
                <div className={s.cardSub}>Split automático da verba dos anunciantes</div>
                <div className={s.payouts}>
                  {PAYOUTS.map((p) => (
                    <div key={p.advertiser} className={s.payout}>
                      <div className={s.payTop}>
                        <div className={s.payName}>{p.advertiser}</div>
                        <div className={s.payNet}>{brlShort(Math.round(p.gross * 0.6))}</div>
                      </div>
                      <div className={s.payMeta}>
                        <span>{p.date}</span>
                        <span>
                          Bruto {brlShort(p.gross)} · taxa {brlShort(Math.round(p.gross * 0.4))}
                        </span>
                        <span className={cx(s.mini, p.status === "pago" && s.miniOk)}>{p.status.toUpperCase()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {Composicao}
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Movimentações de {mes}</div>
              </div>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, s.colMov)}>
                  <div>Data</div>
                  <div>Descrição</div>
                  <div>Origem</div>
                  <div>Valor</div>
                  <div style={{ textAlign: "right" }}>Status</div>
                </div>
                {TRANSACTIONS.map((t) => (
                  <div key={t.date + t.desc} className={cx(s.row, s.colMov)}>
                    <div className={s.cell}>{t.date}</div>
                    <div className={s.pName}>{t.desc}</div>
                    <div>
                      <span className={cx(s.origin, t.origin === "Mensalidade" && s.oMens, t.origin === "Anúncio" && s.oAd)}>
                        {t.origin}
                      </span>
                    </div>
                    <div className={s.strong} style={t.status === "recusado" ? { color: "var(--ad-alert)" } : undefined}>
                      {brl(t.amount)}
                    </div>
                    <div className={cx(s.badge, t.status === "liquidado" && s.ok, t.status === "recusado" && s.bad)}>
                      {t.status}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {aba === "Telas" && (
          <>
            <div className={s.scrGrid}>
              {SCREENS.map((sc, i) => {
                const on = !pausadas[i];
                return (
                  <div key={sc.room} className={cx(s.scrCard, on && s.scrCardOn)}>
                    <div className={s.scrHead}>
                      <div className={s.scrTitle}>
                        <span className={cx(s.dot, !on && s.dotOff)} />
                        {sc.room}
                      </div>
                      <span className={cx(s.state, !on && s.stateOff)}>{on ? "ONLINE" : "PAUSADA"}</span>
                    </div>
                    <div className={s.now}>
                      <div className={s.tiny}>Exibindo agora</div>
                      <div className={s.nowT}>{on ? sc.playing : "Exibição pausada pela academia"}</div>
                    </div>
                    <div className={s.stats}>
                      {[
                        ["Uptime 30d", sc.uptime],
                        ["Última sync", on ? sc.sync : "pausada"],
                        ["Resolução", sc.res],
                        ["QR no mês", sc.scans],
                      ].map(([l, v]) => (
                        <div key={l}>
                          <div className={s.tiny}>{l}</div>
                          <div className={s.statV}>{v}</div>
                        </div>
                      ))}
                    </div>
                    <button className={cx(s.toggle, !on && s.toggleResume)} onClick={() => alternar(i)}>
                      <span style={{ fontSize: 11 }}>{on ? "❚❚" : "▶"}</span>
                      {on ? "Pausar exibição" : "Retomar exibição"}
                    </button>
                  </div>
                );
              })}
              <div className={s.pair}>
                <div className={s.plus}>+</div>
                <div className={s.cardTitle}>Adicionar tela</div>
                <div className={s.pairTxt}>Abra o navegador da TV em modo kiosk e pareie com o código de 6 dígitos.</div>
                <div className={s.code}>{PAIRING_CODE}</div>
              </div>
            </div>

            <div className={s.card} style={{ marginTop: 14 }}>
              <div className={s.tableHead} style={{ padding: 0, border: 0 }}>
                <div className={s.cardTitle}>Fila da Jukebox</div>
                <div className={s.footAcc}>{QUEUE.length} pedidos · 18 min</div>
              </div>
              <div className={s.queue}>
                {QUEUE.map((q, i) => (
                  <div key={q.title} className={s.q}>
                    <div className={s.qPos}>{String(i + 1).padStart(2, "0")}</div>
                    <div className={s.grow1}>
                      <div className={s.pName}>{q.title}</div>
                      <div className={s.pMail}>{q.artist}</div>
                    </div>
                    <div className={s.qWho}>{q.requester}</div>
                    <div className={s.qDur}>{q.dur}</div>
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
