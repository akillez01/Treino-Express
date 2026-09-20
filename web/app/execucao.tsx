"use client";

import { useEffect, useState } from "react";
import { concluirExercicio, iniciarDescanso, type Treino } from "@/lib/api";
import s from "./execucao.module.css";

const fmt = (t: number) =>
  `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;

export default function Execucao({ treino, onSair }: { treino: Treino; onSair: () => void }) {
  const [idx, setIdx] = useState(0);
  const [resto, setResto] = useState<number | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const ex = treino.exercicios[idx];

  useEffect(() => {
    if (resto === null || resto <= 0) return;
    const t = setTimeout(() => setResto((r) => (r === null ? r : r - 1)), 1000);
    return () => clearTimeout(t);
  }, [resto]);

  async function proximo() {
    setErro(null);
    try {
      const r = await concluirExercicio(treino.treino_id, ex.ordem);
      if (r.treino_concluido) return onSair();
      setIdx((i) => i + 1);
      const d = await iniciarDescanso(treino.treino_id, ex.ordem);
      setResto(d.descanso_segundos);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao falar com a API");
    }
  }

  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <header className={s.head}>
          <button className={s.back} onClick={onSair} aria-label="Voltar">
            ←
          </button>
          <div>
            <div className={s.title}>Treino Express</div>
            <div className={s.sub}>
              {treino.minutos} min · {treino.exercicios.length} exercícios
            </div>
          </div>
          <div className={s.pos}>
            {idx + 1} / {treino.exercicios.length}
          </div>
        </header>

        <div className={s.bars}>
          {treino.exercicios.map((e, i) => (
            <span key={e.ordem} className={i < idx ? s.done : i === idx ? s.cur : s.todo} />
          ))}
        </div>

        <section className={s.card}>
          <div className={s.eyebrow}>EXERCÍCIO ATUAL</div>
          <h2 className={s.name}>{ex.nome}</h2>
          <div className={s.badges}>
            <span className={s.series}>{ex.series}</span>
            {ex.carga && <span className={s.carga}>{ex.carga}</span>}
          </div>
        </section>

        <section className={s.timer}>
          <div className={s.eyebrow}>
            {resto === null ? "PRONTO PARA COMEÇAR" : resto > 0 ? "DESCANSO ATIVO" : "DESCANSO CONCLUÍDO"}
          </div>
          <div className={s.time}>{resto === null ? "--:--" : resto > 0 ? fmt(resto) : "Hora de voltar!"}</div>
        </section>

        {erro && <p className={s.erro}>{erro}</p>}

        <button className={s.cta} onClick={proximo}>
          {idx === treino.exercicios.length - 1 ? "Finalizar" : "Concluir e descansar"}
        </button>
      </div>
    </main>
  );
}
