"use client";

import Link from "next/link";
import { useState } from "react";
import Carga from "@/app/_components/Estado";
import Kpi, { variacao } from "@/app/_components/Kpi";
import s from "@/app/_components/panel.module.css";
import { pausarTela, resumoAcademia, useApi } from "@/lib/api";
import { brlShort, cx, fmt, initials, quando, rotuloMes, ultimosMeses } from "@/lib/format";

const PLANOS: Record<string, string> = { mensal: "Mensal", trimestral: "Trimestral", anual: "Anual" };

export default function VisaoGeral() {
  const meses = ultimosMeses(3);
  const [mes, setMes] = useState(meses[0]);
  const resumo = useApi(`resumo-${mes}`, () => resumoAcademia(mes));

  return (
    <Carga estado={resumo}>
      {(d) => {
        const r = d.receita_centavos;
        const ant = d.receita_anterior_centavos;
        const total = r.mensalidade + r.anuncio + r.jukebox;
        const partes = [
          { label: "Mensalidades", note: `${fmt(d.alunos_ativos)} alunos ativos`, valor: r.mensalidade, cor: "var(--accent)" },
          { label: "Anúncios na TV", note: "Repasse dos anunciantes locais", valor: r.anuncio, cor: "var(--ad)" },
          { label: "Jukebox", note: "Pedidos avulsos de música", valor: r.jukebox, cor: "#4f5560" },
        ];
        const minFila = Math.round(d.jukebox.segundos / 60);

        return (
          <>
            <div className={s.headRow}>
              <div>
                <h1 className={s.h1}>Visão geral</h1>
                <div className={s.sub}>
                  {rotuloMes(d.mes)} · fechamento em {d.fechamento.split("-").reverse().slice(0, 2).join("/")}
                </div>
              </div>
              <div className={s.seg} role="tablist" aria-label="Mês">
                {meses.map((m) => (
                  <button key={m} role="tab" aria-selected={m === mes} className={cx(s.segBtn, m === mes && s.segOn)} onClick={() => setMes(m)}>
                    {rotuloMes(m)}
                  </button>
                ))}
              </div>
            </div>

            <div className={s.kpis}>
              <Kpi label="Alunos ativos" value={fmt(d.alunos_ativos)} delta={`+${d.novos_no_mes}`} note="novos no mês" />
              <Kpi label="Mensalidades" value={brlShort(r.mensalidade)} delta={variacao(r.mensalidade, ant.mensalidade)} note="vs. mês anterior" />
              <Kpi label="Receita de anúncios" value={brlShort(r.anuncio)} delta={variacao(r.anuncio, ant.anuncio)} ad note="repasse dos parceiros" />
              <Kpi label="Inadimplência" value={`${d.inadimplencia_pct.toFixed(1).replace(".", ",")}%`} note="alunos com pagamento atrasado" />
            </div>

            <div className={s.two}>
              <div className={s.card}>
                <div className={s.cardTitle}>Composição da receita</div>
                <div className={s.big}>{brlShort(total)}</div>
                <div className={s.stack}>
                  {partes.map((p) => (
                    <div key={p.label} style={{ width: `${total ? (p.valor / total) * 100 : 0}%`, background: p.cor }} />
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
              </div>

              <div className={s.card}>
                <div className={s.spread}>
                  <div className={s.cardTitle}>Telas da academia</div>
                  <Link href="/academia/telas" className={s.link}>
                    Gerenciar →
                  </Link>
                </div>
                <div className={s.scrList}>
                  {d.telas.length === 0 && <div className={s.vazio}>Nenhuma tela pareada.</div>}
                  {d.telas.map((t) => (
                    <TelaLinha key={t.id} tela={t} onChange={resumo.recarregar} />
                  ))}
                </div>
                <div className={s.foot}>
                  <span>Fila da Jukebox</span>
                  <span className={s.footAcc}>
                    {d.jukebox.pedidos} pedidos · {minFila} min
                  </span>
                </div>
              </div>
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Últimos check-ins</div>
                <Link href="/academia/alunos" className={s.link}>
                  Ver todos os alunos →
                </Link>
              </div>
              <div className={s.scroll}>
                {d.ultimos_checkins.length === 0 && <div className={s.vazio}>Sem check-ins recentes.</div>}
                {d.ultimos_checkins.map((c, i) => (
                  <div key={c.nome + i} className={cx(s.row, s.colRecent)}>
                    <div className={s.person}>
                      <div className={s.av}>{initials(c.nome)}</div>
                      <div className={s.pName}>{c.nome}</div>
                    </div>
                    <div className={s.cell}>{PLANOS[c.plano] ?? c.plano}</div>
                    <div className={s.cell}>{quando(c.entrada_em)}</div>
                    <div className={cx(s.badge, c.situacao === "em_dia" && s.ok, c.situacao === "atrasado" && s.bad)}>
                      {c.situacao.replace("_", " ")}
                    </div>
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

function TelaLinha({
  tela,
  onChange,
}: {
  tela: { id: string; sala: string; status: string };
  onChange: () => void;
}) {
  const [ocupada, setOcupada] = useState(false);
  const on = tela.status === "online";
  return (
    <button
      className={s.scrRow}
      disabled={ocupada}
      onClick={async () => {
        setOcupada(true);
        try {
          await pausarTela(tela.id);
          onChange();
        } finally {
          setOcupada(false);
        }
      }}
    >
      <span className={cx(s.dot, !on && s.dotOff)} />
      <span className={s.grow1}>
        <div className={s.room}>{tela.sala}</div>
        <div className={s.playing}>{on ? "Exibindo conteúdo · toque para pausar" : "Exibição pausada · toque para retomar"}</div>
      </span>
      <span className={cx(s.state, !on && s.stateOff)}>{on ? "ONLINE" : tela.status === "pausada" ? "PAUSADA" : "OFFLINE"}</span>
    </button>
  );
}
