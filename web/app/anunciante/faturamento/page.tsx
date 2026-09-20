"use client";

import { useState } from "react";
import Carga from "@/app/_components/Estado";
import Kpi from "@/app/_components/Kpi";
import s from "@/app/_components/panel.module.css";
import { faturamentoAnunciante, useApi } from "@/lib/api";
import { brl, brlShort, cx, dataCurta } from "@/lib/format";
import x from "../anunciante.module.css";

const TOPUPS = [500, 1000, 2000, 5000];
const SPLIT = [
  { label: "Academias parceiras", value: "60%", cor: "var(--accent)", note: "Repassado na hora para a conta Stripe de cada academia que exibiu o anúncio." },
  { label: "Plataforma", value: "30%", cor: "var(--ad)", note: "Operação das telas, medição de QR e suporte às campanhas." },
  { label: "Processamento", value: "10%", cor: "#4f5560", note: "Taxas de cartão e antifraude cobradas pelo Stripe." },
];

export default function Faturamento() {
  const dados = useApi("fatura", faturamentoAnunciante);
  const [recarga, setRecarga] = useState(2000);

  return (
    <Carga estado={dados}>
      {(d) => {
        const consumoDia = d.investido_mes_centavos / Math.max(new Date().getDate(), 1);
        const dias = consumoDia ? Math.floor(d.conta.saldo_centavos / consumoDia) : 0;
        return (
          <>
            <div className={s.headRow}>
              <div>
                <div className={x.eyebrow}>Faturamento</div>
                <h1 className={s.h1}>Crédito e faturas</h1>
                <div className={s.sub}>Saldo de {brlShort(d.conta.saldo_centavos)}{dias ? ` · rende cerca de ${dias} dias` : ""}</div>
              </div>
              <div className={x.actions}>
                <button className={x.ctaBtn} disabled title="Em breve">
                  <span style={{ fontSize: 16 }}>↓</span>Baixar extrato
                </button>
              </div>
            </div>

            <div className={s.kpis}>
              <Kpi label="Saldo disponível" value={brlShort(d.conta.saldo_centavos)} note={dias ? `rende cerca de ${dias} dias de exibição` : "sem consumo no mês"} />
              <Kpi label="Investido no mês" value={brlShort(d.investido_mes_centavos)} note="consumo por impressão entregue" />
              <Kpi label="Repassado às academias" value={brlShort(d.repassado_centavos)} color="#ff9d6e" note="via Stripe Connect" />
              <Kpi label="Custo médio por resgate" value={d.resgates_mes ? brl(d.investido_mes_centavos / d.resgates_mes) : "—"} note={`${d.resgates_mes} resgates no mês`} />
            </div>

            <div className={s.two}>
              <div className={s.card}>
                <div className={s.cardTitle}>Recarregar crédito</div>
                <div className={s.cardSub}>O valor é debitado por impressão entregue</div>
                <div className={x.topups}>
                  {TOPUPS.map((v) => (
                    <button key={v} className={cx(x.topup, v === recarga && x.topupOn)} onClick={() => setRecarga(v)}>
                      <div className={x.topupV}>{brlShort(v * 100)}</div>
                      <div className={x.topupN}>{consumoDia ? Math.round((v * 100) / consumoDia) : "—"} dias de exibição</div>
                    </button>
                  ))}
                </div>
                <button className={x.pay} disabled title="Integração com o Stripe em breve">
                  Pagar {brlShort(recarga * 100)} com Stripe · em breve
                </button>
              </div>

              <div className={s.card}>
                <div className={s.cardTitle}>Para onde vai o seu investimento</div>
                <div className={s.cardSub}>Split executado pelo Stripe Connect em cada cobrança</div>
                <div className={s.stack} style={{ marginTop: 22 }}>
                  {SPLIT.map((b) => (
                    <div key={b.label} style={{ width: b.value, background: b.cor }} />
                  ))}
                </div>
                <div className={x.splitBars}>
                  {SPLIT.map((b) => (
                    <div key={b.label} className={x.splitItem}>
                      <span className={s.sw} style={{ background: b.cor, marginTop: 4 }} />
                      <div className={s.grow1}>
                        <div className={s.payTop}>
                          <div className={s.legT}>{b.label}</div>
                          <div className={s.legV}>{b.value}</div>
                        </div>
                        <div className={x.splitNote}>{b.note}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Histórico de faturas</div>
              </div>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, x.colInv)}>
                  <div>Data</div>
                  <div>Descrição</div>
                  <div>Valor</div>
                  <div>Nota</div>
                  <div style={{ textAlign: "right" }}>Status</div>
                </div>
                {d.faturas.length === 0 && <div className={s.vazio}>Nenhuma fatura ainda.</div>}
                {d.faturas.map((f, i) => (
                  <div key={f.descricao + i} className={cx(s.row, x.colInv)}>
                    <div className={s.cell}>{dataCurta(f.data)}</div>
                    <div className={s.pName}>{f.descricao}</div>
                    <div className={s.strong}>{brl(f.valor_centavos)}</div>
                    <div className={x.accentNum} style={{ fontSize: 12 }}>
                      {f.nota_fiscal}
                    </div>
                    <div className={cx(s.badge, f.status === "pago" && s.ok)}>{f.status}</div>
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
