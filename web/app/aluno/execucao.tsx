"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  avaliarTreino,
  concluirExercicio,
  iniciarDescanso,
  resumoTreino,
  type Anuncio,
  type Exercicio,
  type ResumoTreino,
  type Treino,
} from "@/lib/api";
import { fmt } from "@/lib/format";
import AjusteSheet from "./ajuste";
import s from "./execucao.module.css";

const CIRC = 496.4; // 2 * PI * 79 (raio do anel do cronômetro)
const mmss = (t: number) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
const ESFORCO = ["Muito leve", "Leve", "Moderado", "Intenso", "Exaustivo"];

export default function Execucao({ treino, onSair }: { treino: Treino; onSair: () => void }) {
  const [exs, setExs] = useState<Exercicio[]>(treino.exercicios);
  const [idx, setIdx] = useState(0);
  const [total, setTotal] = useState(treino.descanso_segundos);
  const [resto, setResto] = useState(treino.descanso_segundos);
  const [rodando, setRodando] = useState(true);
  const [anuncio, setAnuncio] = useState<Anuncio | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [ajustando, setAjustando] = useState(false);
  const [final, setFinal] = useState(false);

  const ex = exs[Math.min(idx, exs.length - 1)];
  const exRef = useRef(ex);
  exRef.current = ex;
  const ultimo = idx >= exs.length - 1;

  // O descanso corre desde que o exercício aparece (como no design). Ao entrar
  // em cada exercício avisamos a API: ela escolhe o anúncio e atualiza a TV.
  useEffect(() => {
    if (final) return;
    let vivo = true;
    const seg = exRef.current.descanso_segundos;
    setAnuncio(null);
    setTotal(seg);
    setResto(seg);
    setRodando(true);
    iniciarDescanso(treino.treino_id, exRef.current.ordem)
      .then((d) => {
        if (!vivo) return;
        setAnuncio(d.campanha);
        if (d.descanso_segundos !== seg) {
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
  }, [treino.treino_id, ex.ordem, final]);

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
      if (r.treino_concluido) setFinal(true);
      else setIdx((i) => i + 1);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao falar com a API");
    } finally {
      setOcupado(false);
    }
  }, [treino.treino_id, ex.ordem]);

  function aplicarTreino(t: Treino, descansoMudou: boolean) {
    const ordemAtual = ex.ordem;
    setExs(t.exercicios);
    const novoIdx = t.exercicios.findIndex((e) => e.ordem === ordemAtual);
    // exercício removido: o próximo assume o lugar
    const alvo = novoIdx >= 0 ? novoIdx : Math.min(idx, t.exercicios.length - 1);
    setIdx(alvo);
    const atual = t.exercicios[alvo];
    if (descansoMudou && atual) {
      setTotal(atual.descanso_segundos);
      setResto(atual.descanso_segundos);
      setRodando(true);
    }
  }

  if (final) return <Resumo treino={treino} onSair={onSair} />;

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
              {treino.minutos} min · {exs.length} exercícios
            </div>
          </div>
          <div className={s.pos}>
            {idx + 1} / {exs.length}
          </div>
        </header>

        <div className={s.bars} aria-hidden>
          {exs.map((e, i) => (
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
            <button className={s.ajustar} onClick={() => setAjustando(true)}>
              ⚙ Ajustar
            </button>
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

      {ajustando && (
        <AjusteSheet
          treinoId={treino.treino_id}
          ex={ex}
          podeRemover={exs.length > 1}
          onTreino={aplicarTreino}
          onFechar={() => setAjustando(false)}
        />
      )}
    </main>
  );
}

function Resumo({ treino, onSair }: { treino: Treino; onSair: () => void }) {
  const [r, setR] = useState<ResumoTreino | null>(null);
  const [esforco, setEsforco] = useState<number | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    resumoTreino(treino.treino_id)
      .then((d) => {
        setR(d);
        setEsforco(d.esforco);
      })
      .catch(() => setErro("Não foi possível carregar o resumo."));
  }, [treino.treino_id]);

  async function avaliar(v: number) {
    setEsforco(v);
    try {
      await avaliarTreino(treino.treino_id, v);
    } catch {
      setErro("Não foi possível salvar a avaliação.");
    }
  }

  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <div className={s.fim}>
          <div className={s.fimIcone} aria-hidden>
            ✓
          </div>
          <h1 className={s.fimTitulo}>Treino concluído!</h1>
          <p className={s.fimSub}>Bom trabalho. Veja como foi.</p>
        </div>

        {r && (
          <>
            <div className={s.stats}>
              <div className={s.stat}>
                <b>{r.duracao_min}</b>
                <span>minutos</span>
              </div>
              <div className={s.stat}>
                <b>
                  {r.exercicios_concluidos}/{r.exercicios_total}
                </b>
                <span>exercícios</span>
              </div>
              <div className={s.stat}>
                <b>{fmt(r.volume_kg)}</b>
                <span>kg de volume</span>
              </div>
            </div>

            {r.recordes.length > 0 && (
              <section className={s.recs}>
                <div className={s.recsTitulo}>🏆 Novos recordes</div>
                {r.recordes.map((p) => (
                  <div key={p.exercicio} className={s.rec}>
                    <span>{p.exercicio}</span>
                    <b>
                      {p.kg.toString().replace(".", ",")} kg <small>(antes {p.anterior_kg.toString().replace(".", ",")})</small>
                    </b>
                  </div>
                ))}
              </section>
            )}
          </>
        )}

        <section className={s.esforco}>
          <div className={s.recsTitulo}>Como foi o esforço?</div>
          <div className={s.esforcoBtns}>
            {ESFORCO.map((nome, i) => (
              <button key={nome} className={esforco === i + 1 ? s.esforcoOn : s.esforcoBtn} onClick={() => avaliar(i + 1)}>
                <b>{i + 1}</b>
                <span>{nome}</span>
              </button>
            ))}
          </div>
        </section>

        {erro && <p className={s.erro}>{erro}</p>}

        <Link href="/aluno/progresso" className={s.cta} style={{ display: "grid", placeItems: "center", textDecoration: "none" }}>
          Ver meu progresso
        </Link>
        <button className={s.ghost} onClick={onSair}>
          Novo treino
        </button>
      </div>
    </main>
  );
}
