"use client";

import Link from "next/link";
import { useState } from "react";
import Carga from "@/app/_components/Estado";
import { definirMeta, meuProgresso, useApi, type Progresso } from "@/lib/api";
import { cx, dataCurta, fmt } from "@/lib/format";
import AlunoTabs from "../_components/AlunoTabs";
import s from "./progresso.module.css";

const FOCOS: Record<string, string> = {
  peito_triceps: "Peito e Tríceps",
  costas_biceps: "Costas e Bíceps",
  pernas: "Pernas",
  ombros: "Ombros",
  bracos: "Braços",
  fullbody: "Fullbody",
  cardio: "Cardio",
  superiores: "Superiores",
};
const CIRC = 2 * Math.PI * 54;
const ICONES: Record<string, string> = {
  primeiro_treino: "★",
  sequencia_3: "🔥",
  sequencia_7: "⚡",
  dez_treinos: "10",
  vinte_cinco_treinos: "25",
  volume_1t: "🏋",
  meta_semana: "🎯",
  novo_recorde: "🏆",
};

const horas = (min: number) => (min >= 60 ? `${Math.floor(min / 60)}h ${String(min % 60).padStart(2, "0")}min` : `${min} min`);
const toneladas = (kg: number) => (kg >= 1000 ? `${(kg / 1000).toFixed(1).replace(".", ",")} t` : `${fmt(kg)} kg`);

export default function ProgressoPage() {
  const dados = useApi("progresso", meuProgresso);
  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <Link href="/" className={s.back}>
          ← Início
        </Link>
        <Carga estado={dados}>{(p) => <Conteudo p={p} recarregar={dados.recarregar} />}</Carga>
      </div>
      <AlunoTabs />
    </main>
  );
}

function Conteudo({ p, recarregar }: { p: Progresso; recarregar: () => void }) {
  const [salvando, setSalvando] = useState(false);
  const [exSel, setExSel] = useState(0);
  const sc = p.pontuacao;
  const maxSemana = Math.max(p.semana.meta, ...p.semanas.map((w) => w.treinos), 1);
  const totalFoco = p.por_foco.reduce((a, f) => a + f.treinos, 0) || 1;

  async function meta(delta: number) {
    const nova = Math.min(7, Math.max(1, p.meta_semanal + delta));
    if (nova === p.meta_semanal) return;
    setSalvando(true);
    try {
      await definirMeta(nova);
      recarregar();
    } finally {
      setSalvando(false);
    }
  }

  const evo = p.evolucao_carga[Math.min(exSel, p.evolucao_carga.length - 1)];

  return (
    <>
      <header>
        <h1 className={s.title}>Meu desempenho</h1>
        <p className={s.sub}>Sua evolução nas últimas semanas</p>
      </header>

      <section className={s.hero}>
        <div className={s.ring}>
          <svg viewBox="0 0 128 128" width="128" height="128" aria-hidden>
            <circle cx="64" cy="64" r="54" fill="none" stroke="#1e2126" strokeWidth="12" />
            <circle
              cx="64"
              cy="64"
              r="54"
              fill="none"
              stroke="var(--accent)"
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={CIRC}
              strokeDashoffset={CIRC * (1 - sc.total / 100)}
              transform="rotate(-90 64 64)"
            />
          </svg>
          <div className={s.ringTxt}>
            <b>{sc.total}</b>
            <span>de 100</span>
          </div>
        </div>
        <div className={s.heroInfo}>
          <div className={s.nivel}>{sc.nivel}</div>
          {[
            ["Consistência", sc.consistencia, 50],
            ["Progressão", sc.progressao, 30],
            ["Conclusão", sc.conclusao, 20],
          ].map(([nome, v, max]) => (
            <div key={nome as string} className={s.comp}>
              <div className={s.compTop}>
                <span>{nome}</span>
                <span>
                  {v}/{max}
                </span>
              </div>
              <div className={s.track}>
                <div className={s.fill} style={{ width: `${((v as number) / (max as number)) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={s.card}>
        <div className={s.cardHead}>
          <div>
            <div className={s.label}>META DA SEMANA</div>
            <div className={s.big}>
              {p.semana.treinos}
              <small> de {p.meta_semanal} treinos</small>
            </div>
          </div>
          <div className={s.stepper} aria-label="Ajustar meta semanal">
            <button onClick={() => meta(-1)} disabled={salvando || p.meta_semanal <= 1} aria-label="Diminuir meta">
              −
            </button>
            <span>{p.meta_semanal}x</span>
            <button onClick={() => meta(1)} disabled={salvando || p.meta_semanal >= 7} aria-label="Aumentar meta">
              +
            </button>
          </div>
        </div>
        <div className={s.dots}>
          {Array.from({ length: p.meta_semanal }, (_, i) => (
            <span key={i} className={cx(s.dot, i < p.semana.treinos && s.dotOn)} />
          ))}
        </div>
        <p className={s.hint}>
          {p.semana.treinos >= p.meta_semanal
            ? "Meta batida! Cada treino a mais é bônus."
            : `Faltam ${p.meta_semanal - p.semana.treinos} treino(s) para bater a meta.`}
        </p>
      </section>

      <section className={s.kpis}>
        <div className={s.kpi}>
          <div className={s.label}>SEQUÊNCIA</div>
          <div className={s.kpiV}>
            {p.sequencia.atual}
            <small> dias</small>
          </div>
          <div className={s.kpiN}>melhor: {p.sequencia.melhor} dias</div>
        </div>
        <div className={s.kpi}>
          <div className={s.label}>TREINOS</div>
          <div className={s.kpiV}>{p.totais.treinos}</div>
          <div className={s.kpiN}>{p.totais.exercicios} exercícios</div>
        </div>
        <div className={s.kpi}>
          <div className={s.label}>TEMPO</div>
          <div className={s.kpiV}>{horas(p.totais.minutos)}</div>
          <div className={s.kpiN}>treinando</div>
        </div>
        <div className={s.kpi}>
          <div className={s.label}>VOLUME</div>
          <div className={s.kpiV}>{toneladas(p.totais.volume_kg)}</div>
          <div className={s.kpiN}>carga total levantada</div>
        </div>
      </section>

      <section className={s.card}>
        <div className={s.cardTitle}>Treinos por semana</div>
        <div className={s.chart}>
          {p.semanas.map((w, i) => (
            <div key={w.inicio} className={s.col}>
              <div className={s.colVal}>{w.treinos || ""}</div>
              <div className={s.colBox}>
                <div
                  className={cx(s.colBar, i === p.semanas.length - 1 && s.colAtual, w.treinos >= p.meta_semanal && s.colMeta)}
                  style={{ height: `${(w.treinos / maxSemana) * 100}%` }}
                />
                <div className={s.metaLine} style={{ bottom: `${(p.meta_semanal / maxSemana) * 100}%` }} />
              </div>
              <div className={s.colLbl}>{dataCurta(w.inicio)}</div>
            </div>
          ))}
        </div>
        <div className={s.legend}>
          <span>
            <i className={s.legDot} /> bateu a meta
          </span>
          <span>
            <i className={cx(s.legDot, s.legOff)} /> abaixo da meta
          </span>
        </div>
      </section>

      {evo && (
        <section className={s.card}>
          <div className={s.cardTitle}>Evolução de carga</div>
          <div className={s.pills}>
            {p.evolucao_carga.map((e, i) => (
              <button key={e.exercicio} className={cx(s.pill, i === exSel && s.pillOn)} onClick={() => setExSel(i)}>
                {e.exercicio}
              </button>
            ))}
          </div>
          <Linha pontos={evo.pontos} />
        </section>
      )}

      {p.recordes.length > 0 && (
        <section className={s.card}>
          <div className={s.cardTitle}>Recordes pessoais</div>
          <ul className={s.list}>
            {p.recordes.map((r) => (
              <li key={r.exercicio} className={s.rec}>
                <div className={s.recTxt}>
                  <div className={s.recNome}>{r.exercicio}</div>
                  <div className={s.recSub}>
                    {r.sessoes} sessões · {dataCurta(r.data)}
                  </div>
                </div>
                <div className={s.recKg}>{r.kg.toString().replace(".", ",")} kg</div>
                {r.evolucao_kg > 0 && <div className={s.recDelta}>+{r.evolucao_kg.toString().replace(".", ",")}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {p.por_foco.length > 0 && (
        <section className={s.card}>
          <div className={s.cardTitle}>Onde você mais treina</div>
          <ul className={s.list}>
            {p.por_foco.map((f) => (
              <li key={f.foco} className={s.foco}>
                <div className={s.focoTop}>
                  <span>{FOCOS[f.foco] ?? f.foco}</span>
                  <span>{f.treinos}x</span>
                </div>
                <div className={s.track}>
                  <div className={s.fill} style={{ width: `${(f.treinos / totalFoco) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className={s.card}>
        <div className={s.cardTitle}>
          Conquistas <small>{p.conquistas.filter((c) => c.conquistada).length}/{p.conquistas.length}</small>
        </div>
        <div className={s.badges}>
          {p.conquistas.map((c) => (
            <div key={c.id} className={cx(s.badge, !c.conquistada && s.badgeOff)} title={c.descricao}>
              <div className={s.badgeIcon}>{ICONES[c.id] ?? "★"}</div>
              <div className={s.badgeNome}>{c.titulo}</div>
              <div className={s.badgeDesc}>{c.descricao}</div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function Linha({ pontos }: { pontos: { data: string; kg: number }[] }) {
  const W = 320;
  const H = 130;
  const pad = 14;
  const kgs = pontos.map((p) => p.kg);
  const min = Math.min(...kgs);
  const max = Math.max(...kgs);
  const span = max - min || 1;
  const x = (i: number) => pad + (pontos.length === 1 ? (W - 2 * pad) / 2 : (i / (pontos.length - 1)) * (W - 2 * pad));
  const y = (kg: number) => H - pad - ((kg - min) / span) * (H - 2 * pad);
  const d = pontos.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.kg).toFixed(1)}`).join(" ");
  const delta = kgs[kgs.length - 1] - kgs[0];
  return (
    <div>
      <div className={s.lineTop}>
        <b>{kgs[kgs.length - 1].toString().replace(".", ",")} kg</b>
        <span className={delta >= 0 ? s.up : s.down}>
          {delta >= 0 ? "+" : "−"}
          {Math.abs(delta).toString().replace(".", ",")} kg desde {dataCurta(pontos[0].data)}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className={s.svg} role="img" aria-label="Gráfico de evolução da carga">
        <path d={d} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {pontos.map((p, i) => (
          <circle key={p.data} cx={x(i)} cy={y(p.kg)} r="3.5" fill="#0d0e10" stroke="var(--accent)" strokeWidth="2" />
        ))}
      </svg>
    </div>
  );
}
