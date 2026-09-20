"use client";

import Link from "next/link";
import { useState } from "react";
import Carga from "@/app/_components/Estado";
import { rankingAcademia, salvarPreferencias, useApi, type LinhaRanking, type Metrica } from "@/lib/api";
import { cx, fmt } from "@/lib/format";
import AlunoTabs from "../_components/AlunoTabs";
import s from "./ranking.module.css";

const METRICAS: { id: Metrica; label: string; unidade: (v: number) => string }[] = [
  { id: "treinos", label: "Treinos", unidade: (v) => `${v} ${v === 1 ? "treino" : "treinos"}` },
  { id: "volume", label: "Volume", unidade: (v) => `${fmt(v)} kg` },
  { id: "sequencia", label: "Sequência", unidade: (v) => `${v} ${v === 1 ? "dia" : "dias"}` },
];
const PERIODOS = [
  { dias: 7, label: "7 dias" },
  { dias: 30, label: "30 dias" },
  { dias: 90, label: "90 dias" },
];
const MEDALHA = ["🥇", "🥈", "🥉"];

export default function RankingPage() {
  const [metrica, setMetrica] = useState<Metrica>("treinos");
  const [dias, setDias] = useState(30);
  const dados = useApi(`rank-${metrica}-${dias}`, () => rankingAcademia(metrica, dias));
  const [busy, setBusy] = useState(false);
  const unidade = METRICAS.find((m) => m.id === metrica)!.unidade;

  async function participar() {
    setBusy(true);
    try {
      await salvarPreferencias({ ranking_visivel: true });
      dados.recarregar();
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <Link href="/" className={s.back}>
          ← Início
        </Link>
        <header>
          <h1 className={s.title}>Ranking</h1>
          <p className={s.sub}>Compare-se com os alunos da sua academia</p>
        </header>

        <Carga estado={dados}>
          {(d) =>
            !d.participando ? (
              <section className={s.convite}>
                <div className={s.conviteIcone} aria-hidden>
                  ♛
                </div>
                <h2>Entre no ranking</h2>
                <p>
                  Para ver a classificação você também aparece nela, só com seu primeiro nome e a inicial do sobrenome. Você
                  pode sair quando quiser, em Progresso &gt; Privacidade.
                </p>
                <button className={s.cta} disabled={busy} onClick={participar}>
                  {busy ? "Entrando..." : "Participar do ranking"}
                </button>
              </section>
            ) : (
              <>
                <div className={s.chips} role="tablist" aria-label="Critério">
                  {METRICAS.map((m) => (
                    <button key={m.id} role="tab" aria-selected={m.id === metrica} className={cx(s.chip, m.id === metrica && s.chipOn)} onClick={() => setMetrica(m.id)}>
                      {m.label}
                    </button>
                  ))}
                </div>
                {metrica !== "sequencia" && (
                  <div className={s.periodos} role="tablist" aria-label="Período">
                    {PERIODOS.map((p) => (
                      <button key={p.dias} role="tab" aria-selected={p.dias === dias} className={cx(s.per, p.dias === dias && s.perOn)} onClick={() => setDias(p.dias)}>
                        {p.label}
                      </button>
                    ))}
                  </div>
                )}

                {d.itens.length >= 3 && (
                  <div className={s.podio}>
                    {[d.itens[1], d.itens[0], d.itens[2]].map((x, i) => (
                      <div key={x.posicao} className={cx(s.pod, i === 1 && s.podPrimeiro, x.eu && s.podEu)}>
                        <div className={s.medalha}>{MEDALHA[x.posicao - 1]}</div>
                        <div className={s.podNome}>{x.nome}</div>
                        <div className={s.podValor}>{unidade(x.valor)}</div>
                      </div>
                    ))}
                  </div>
                )}

                <ul className={s.lista}>
                  {d.itens.map((x) => (
                    <Linha key={x.posicao} x={x} unidade={unidade} />
                  ))}
                  {d.eu && (
                    <>
                      <li className={s.reticencias} aria-hidden>
                        ⋯
                      </li>
                      <Linha x={d.eu} unidade={unidade} />
                    </>
                  )}
                </ul>
                <p className={s.rodape}>{d.total} alunos participando · sua posição é atualizada a cada treino concluído</p>
              </>
            )
          }
        </Carga>
      </div>
      <AlunoTabs />
    </main>
  );
}

function Linha({ x, unidade }: { x: LinhaRanking; unidade: (v: number) => string }) {
  return (
    <li className={cx(s.item, x.eu && s.itemEu)}>
      <div className={s.pos}>{x.posicao}</div>
      <div className={s.avatar}>{x.nome[0]}</div>
      <div className={s.info}>
        <div className={s.nome}>
          {x.nome}
          {x.eu && <span className={s.voce}>você</span>}
        </div>
        <div className={s.det}>
          {x.treinos} treinos no período · melhor sequência {x.melhor_sequencia} dias
        </div>
      </div>
      <div className={s.valor}>{unidade(x.valor)}</div>
    </li>
  );
}
