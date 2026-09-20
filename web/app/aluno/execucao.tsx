"use client";

import { useCallback, useEffect, useState } from "react";
import { concluirExercicio, iniciarDescanso, type Anuncio, type Treino } from "@/lib/api";
import s from "./execucao.module.css";

const CIRC = 496.4; // 2 * PI * 79 (raio do anel do cronômetro)
const mmss = (t: number) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;

export default function Execucao({ treino, onSair }: { treino: Treino; onSair: () => void }) {
  const [idx, setIdx] = useState(0);
  const [total, setTotal] = useState(treino.descanso_segundos);
  const [resto, setResto] = useState(treino.descanso_segundos);
  const [rodando, setRodando] = useState(true);
  const [anuncio, setAnuncio] = useState<Anuncio | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const ex = treino.exercicios[idx];
  const ultimo = idx === treino.exercicios.length - 1;

  // O descanso corre desde que o exercício aparece (como no design). Ao entrar
  // em cada exercício avisamos a API: ela escolhe o anúncio e atualiza a TV.
  useEffect(() => {
    let vivo = true;
    setAnuncio(null);
    setTotal(treino.descanso_segundos);
    setResto(treino.descanso_segundos);
    setRodando(true);
    iniciarDescanso(treino.treino_id, ex.ordem)
      .then((d) => {
        if (!vivo) return;
        setAnuncio(d.campanha);
        if (d.descanso_segundos !== treino.descanso_segundos) {
          setTotal(d.descanso_segundos);
          setResto(d.descanso_segundos);
        }
      })
      .catch(() => {
        /* sem anúncio: o cronômetro segue normalmente */
      });
    return () => {
      vivo = false;
    };
  }, [treino.treino_id, treino.descanso_segundos, ex.ordem]);

  useEffect(() => {
    if (!rodando || resto <= 0) return;
    const t = setTimeout(() => {
      setResto((r) => {
        if (r <= 1) setRodando(false);
        return Math.max(0, r - 1);
      });
    }, 1000);
    return () => clearTimeout(t);
  }, [rodando, resto]);

  const proximo = useCallback(async () => {
    setErro(null);
    setOcupado(true);
    try {
      const r = await concluirExercicio(treino.treino_id, ex.ordem);
      if (r.treino_concluido) onSair();
      else setIdx((i) => i + 1);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao falar com a API");
    } finally {
      setOcupado(false);
    }
  }, [treino.treino_id, ex.ordem, onSair]);

  const terminou = resto === 0;
  const estado = terminou ? "Descanso concluído" : rodando ? "Descanso ativo" : "Pausado";
  const offset = CIRC * (1 - resto / Math.max(total, 1));

  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <header className={s.head}>
          <button className={s.back} onClick={onSair} aria-label="Voltar">
            ←
          </button>
          <div className={s.headTxt}>
            <div className={s.title}>Treino Express</div>
            <div className={s.sub}>
              {treino.minutos} min · {treino.exercicios.length} exercícios
            </div>
          </div>
          <div className={s.pos}>
            {idx + 1} / {treino.exercicios.length}
          </div>
        </header>

        <div className={s.bars} aria-hidden>
          {treino.exercicios.map((e, i) => (
            <span key={e.ordem} className={i < idx ? s.done : i === idx ? s.cur : s.todo} />
          ))}
        </div>

        <section className={s.card}>
          <div className={s.figure}>
            {ex.imagem_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={ex.imagem_url} alt={ex.nome} />
            ) : (
              <span aria-hidden>🏋</span>
            )}
          </div>
          <div className={s.cardBody}>
            <div className={s.eyebrow}>EXERCÍCIO ATUAL</div>
            <h2 className={s.name}>{ex.nome}</h2>
            <div className={s.badges}>
              <span className={s.series}>{ex.series}</span>
              {ex.carga && <span className={s.carga}>{ex.carga}</span>}
            </div>
          </div>
        </section>

        <section className={s.timer} aria-live="polite">
          <div className={s.ring}>
            <svg viewBox="0 0 178 178" width="178" height="178" aria-hidden>
              <circle cx="89" cy="89" r="79" fill="none" stroke="#1e2126" strokeWidth="13" />
              <circle
                cx="89"
                cy="89"
                r="79"
                fill="none"
                stroke="var(--accent)"
                strokeWidth="13"
                strokeLinecap="round"
                strokeDasharray={CIRC}
                strokeDashoffset={offset}
                style={{ transition: "stroke-dashoffset 1s linear" }}
              />
            </svg>
            <div className={s.center}>
              <div className={s.estado}>{estado.toUpperCase()}</div>
              {terminou ? (
                <div className={s.voltar}>
                  Hora de
                  <br />
                  Voltar!
                </div>
              ) : (
                <div className={s.time}>{mmss(resto)}</div>
              )}
            </div>
          </div>
        </section>

        {anuncio && (
          <section className={s.ad}>
            <div className={s.adTop}>
              <span className={s.adLabel}>
                <i className={s.adDot} />
                OFERTA DO PARCEIRO
              </span>
              <span className={s.adTag}>ANÚNCIO</span>
            </div>
            <div className={s.adMain}>
              <div className={s.discount}>
                <b>{anuncio.desconto}</b>
                <small>OFF</small>
              </div>
              <p className={s.adText}>
                <strong>{anuncio.marca}</strong> · {anuncio.corpo}
              </p>
            </div>
            <div className={s.adFoot}>▣ Olhe para a TV da academia para escanear o QR Code.</div>
          </section>
        )}

        {erro && <p className={s.erro}>{erro}</p>}

        <div className={s.controls}>
          <button
            className={s.ghost}
            onClick={() => {
              if (terminou) {
                setResto(total);
                setRodando(true);
              } else setRodando((r) => !r);
            }}
          >
            <span className={s.icon}>{terminou ? "↻" : rodando ? "❚❚" : "▶"}</span>
            {terminou ? "Reiniciar" : rodando ? "Pausar" : "Retomar"}
          </button>
          <button
            className={s.ghost}
            disabled={terminou}
            onClick={() => {
              setResto(0);
              setRodando(false);
            }}
          >
            Pular descanso
          </button>
        </div>
        <button className={s.cta} disabled={ocupado} onClick={proximo}>
          {ocupado ? "Salvando..." : ultimo ? "Finalizar" : "Próximo exercício"}
        </button>
      </div>
    </main>
  );
}
