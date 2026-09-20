"use client";

import { useState } from "react";
import Carga from "@/app/_components/Estado";
import Kpi from "@/app/_components/Kpi";
import s from "@/app/_components/panel.module.css";
import { financeiroAcademia, useApi } from "@/lib/api";
import { brl, brlShort, cx, dataCurta, rotuloMes, ultimosMeses } from "@/lib/format";

const ORIGEM: Record<string, string> = { mensalidade: "Mensalidade", anuncio: "Anúncio", jukebox: "Jukebox" };
const STATUS_MOV: Record<string, string> = { liquidado: "liquidado", a_receber: "a receber", recusado: "recusado" };
const STATUS_REPASSE: Record<string, string> = { pendente: "PENDENTE", em_transito: "EM TRÂNSITO", pago: "PAGO", falhou: "FALHOU" };

export default function Financeiro() {
  const meses = ultimosMeses(3);
  const [mes, setMes] = useState(meses[0]);
  const fin = useApi(`fin-${mes}`, () => financeiroAcademia(mes));

  return (
    <Carga estado={fin}>
      {(d) => {
        const r = d.receita_centavos;
        const total = r.mensalidade + r.anuncio + r.jukebox;
        const partes = [
          { label: "Mensalidades", valor: r.mensalidade, cor: "var(--accent)" },
          { label: "Anúncios na TV", valor: r.anuncio, cor: "var(--ad)" },
          { label: "Jukebox", valor: r.jukebox, cor: "#4f5560" },
        ];
        return (
          <>
            <div className={s.headRow}>
              <div>
                <h1 className={s.h1}>Financeiro</h1>
                <div className={s.sub}>Mensalidades, anúncios e repasses de {rotuloMes(d.mes)}</div>
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
              <Kpi label="Recebido no mês" value={brlShort(d.recebido_centavos)} note="lançamentos liquidados" />
              <Kpi label="A receber" value={brlShort(d.a_receber_centavos)} note="faturas em aberto e em trânsito" />
              <Kpi label="Repasse Stripe" value={brlShort(d.repasse_liquido_centavos)} color="#ff9d6e" note="split automático dos anunciantes" />
              <Kpi label="Taxas do período" value={brlShort(d.taxas_centavos)} note="plataforma + processamento" />
            </div>

            <div className={s.two}>
              <div className={s.card}>
                <div className={s.cardTitle}>Repasses do Stripe Connect</div>
                <div className={s.cardSub}>Split automático da verba dos anunciantes</div>
                <div className={s.payouts}>
                  {d.repasses.length === 0 && <div className={s.vazio}>Sem repasses neste mês.</div>}
                  {d.repasses.map((p, i) => (
                    <div key={p.anunciante + i} className={s.payout}>
                      <div className={s.payTop}>
                        <div className={s.payName}>{p.anunciante}</div>
                        <div className={s.payNet}>{brlShort(p.liquido_centavos)}</div>
                      </div>
                      <div className={s.payMeta}>
                        <span>{dataCurta(p.data)}</span>
                        <span>
                          Bruto {brlShort(p.bruto_centavos)} · taxa {brlShort(p.taxa_centavos)}
                        </span>
                        <span className={cx(s.mini, p.status === "pago" && s.miniOk)}>{STATUS_REPASSE[p.status]}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

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
                      <div className={s.legT}>{p.label}</div>
                      <div className={s.legV}>{brlShort(p.valor)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Movimentações de {rotuloMes(d.mes)}</div>
              </div>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, s.colMov)}>
                  <div>Data</div>
                  <div>Descrição</div>
                  <div>Origem</div>
                  <div>Valor</div>
                  <div style={{ textAlign: "right" }}>Status</div>
                </div>
                {d.movimentacoes.length === 0 && <div className={s.vazio}>Sem movimentações neste mês.</div>}
                {d.movimentacoes.map((t, i) => (
                  <div key={t.descricao + i} className={cx(s.row, s.colMov)}>
                    <div className={s.cell}>{dataCurta(t.data)}</div>
                    <div className={s.pName}>{t.descricao}</div>
                    <div>
                      <span className={cx(s.origin, t.origem === "mensalidade" && s.oMens, t.origem === "anuncio" && s.oAd)}>{ORIGEM[t.origem]}</span>
                    </div>
                    <div className={s.strong} style={t.status === "recusado" ? { color: "var(--ad-alert)" } : undefined}>
                      {brl(t.valor_centavos)}
                    </div>
                    <div className={cx(s.badge, t.status === "liquidado" && s.ok, t.status === "recusado" && s.bad)}>{STATUS_MOV[t.status]}</div>
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
