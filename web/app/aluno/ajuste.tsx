"use client";

import { useEffect, useState } from "react";
import {
  ajustarExercicio,
  alternativasExercicio,
  removerExercicio,
  trocarExercicio,
  type Alternativa,
  type Exercicio,
  type Treino,
} from "@/lib/api";
import s from "./ajuste.module.css";

const KG = /(\d+(?:[.,]\d+)?)\s*kg/i;
const SERIES = /^\s*(\d+)\s*x\s*(\d+)/;

const num = (v: number) => v.toString().replace(".", ",");
const kgDe = (carga: string | null) => {
  const m = KG.exec(carga ?? "");
  return m ? parseFloat(m[1].replace(",", ".")) : null;
};
const comKg = (carga: string, kg: number) => carga.replace(KG, `${num(kg)} kg`);

export default function AjusteSheet({
  treinoId,
  ex,
  podeRemover,
  onTreino,
  onFechar,
}: {
  treinoId: string;
  ex: Exercicio;
  podeRemover: boolean;
  onTreino: (t: Treino, descansoMudou: boolean) => void;
  onFechar: () => void;
}) {
  const [carga, setCarga] = useState(ex.carga ?? "");
  const [series, setSeries] = useState(ex.series);
  const [descanso, setDescanso] = useState(ex.descanso_segundos);
  const [todos, setTodos] = useState(false);
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [alternativas, setAlternativas] = useState<Alternativa[] | null>(null);
  const [confirmaRemover, setConfirmaRemover] = useState(false);

  const kg = kgDe(carga);
  const sr = SERIES.exec(series);
  const sets = sr ? parseInt(sr[1], 10) : null;
  const reps = sr ? parseInt(sr[2], 10) : null;

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onFechar();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onFechar]);

  async function executar(fn: () => Promise<Treino>, descansoMudou = false) {
    setBusy(true);
    setErro(null);
    try {
      onTreino(await fn(), descansoMudou);
      onFechar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível salvar");
      setBusy(false);
    }
  }

  const salvar = () => {
    const ajuste: Parameters<typeof ajustarExercicio>[2] = {};
    if (series.trim() !== ex.series) ajuste.series = series.trim();
    if (carga.trim() !== (ex.carga ?? "")) ajuste.carga = carga.trim();
    if (descanso !== ex.descanso_segundos || todos) {
      ajuste.descanso_segundos = descanso;
      ajuste.aplicar_descanso_a_todos = todos;
    }
    if (Object.keys(ajuste).length === 0) return onFechar();
    void executar(() => ajustarExercicio(treinoId, ex.ordem, ajuste), ajuste.descanso_segundos !== undefined);
  };

  async function abrirTroca() {
    setErro(null);
    try {
      setAlternativas(await alternativasExercicio(treinoId, ex.ordem));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível carregar as opções");
    }
  }

  return (
    <div className={s.overlay} onClick={onFechar} role="presentation">
      <div className={s.sheet} role="dialog" aria-modal="true" aria-label={`Ajustar ${ex.nome}`} onClick={(e) => e.stopPropagation()}>
        <div className={s.grab} />
        <div className={s.head}>
          <div>
            <div className={s.eyebrow}>AJUSTAR EXERCÍCIO</div>
            <div className={s.nome}>{ex.nome}</div>
          </div>
          <button className={s.x} onClick={onFechar} aria-label="Fechar">
            ✕
          </button>
        </div>

        {alternativas ? (
          <div className={s.body}>
            <div className={s.sec}>Trocar por outro exercício do mesmo foco</div>
            {alternativas.length === 0 && <p className={s.vazio}>Não há outras opções para este foco.</p>}
            <ul className={s.alts}>
              {alternativas.map((a) => (
                <li key={a.exercicio_id}>
                  <button className={s.alt} disabled={busy} onClick={() => executar(() => trocarExercicio(treinoId, ex.ordem, a.exercicio_id), true)}>
                    <span className={s.altImg}>
                      {a.imagem_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={a.imagem_url} alt="" />
                      ) : null}
                    </span>
                    <span className={s.altTxt}>
                      <b>{a.nome}</b>
                      <small>
                        {a.series}
                        {a.carga ? ` · ${a.carga}` : ""}
                      </small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <button className={s.ghost} onClick={() => setAlternativas(null)}>
              ← Voltar aos ajustes
            </button>
          </div>
        ) : (
          <div className={s.body}>
            <div className={s.sec}>Peso</div>
            <div className={s.row}>
              <button className={s.step} disabled={kg === null || kg <= 0} onClick={() => kg !== null && setCarga(comKg(carga, Math.max(0, kg - 2.5)))} aria-label="Diminuir 2,5 kg">
                −
              </button>
              <input className={s.input} value={carga} onChange={(e) => setCarga(e.target.value)} maxLength={40} aria-label="Carga" placeholder="Ex.: Barra 40 kg" />
              <button className={s.step} disabled={kg === null} onClick={() => kg !== null && setCarga(comKg(carga, kg + 2.5))} aria-label="Aumentar 2,5 kg">
                +
              </button>
            </div>
            <p className={s.dica}>{kg === null ? "Sem número em kg: edite o texto livremente." : "Os botões mudam de 2,5 em 2,5 kg."}</p>

            <div className={s.sec}>Séries e repetições</div>
            {sets !== null && reps !== null ? (
              <div className={s.duo}>
                <Stepper rotulo="Séries" valor={sets} min={1} max={10} onChange={(v) => setSeries(`${v}x${reps}`)} />
                <Stepper rotulo="Repetições" valor={reps} min={1} max={50} onChange={(v) => setSeries(`${sets}x${v}`)} />
              </div>
            ) : (
              <input className={s.input} value={series} onChange={(e) => setSeries(e.target.value)} maxLength={30} aria-label="Séries" />
            )}

            <div className={s.sec}>Descanso</div>
            <Stepper rotulo="Segundos" valor={descanso} min={15} max={180} passo={5} onChange={setDescanso} sufixo="s" />
            <label className={s.check}>
              <input type="checkbox" checked={todos} onChange={(e) => setTodos(e.target.checked)} />
              Usar este descanso em todos os exercícios
            </label>

            {erro && <p className={s.erro}>{erro}</p>}

            <button className={s.salvar} disabled={busy} onClick={salvar}>
              {busy ? "Salvando..." : "Salvar ajustes"}
            </button>

            <div className={s.acoes}>
              <button className={s.ghost} onClick={abrirTroca} disabled={busy}>
                ⇄ Trocar exercício
              </button>
              {podeRemover &&
                (confirmaRemover ? (
                  <button className={s.perigo} disabled={busy} onClick={() => executar(() => removerExercicio(treinoId, ex.ordem), true)}>
                    Confirmar remoção
                  </button>
                ) : (
                  <button className={s.ghost} onClick={() => setConfirmaRemover(true)} disabled={busy}>
                    Remover do treino
                  </button>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Stepper({
  rotulo,
  valor,
  min,
  max,
  passo = 1,
  sufixo = "",
  onChange,
}: {
  rotulo: string;
  valor: number;
  min: number;
  max: number;
  passo?: number;
  sufixo?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className={s.stepper}>
      <span className={s.stepLbl}>{rotulo}</span>
      <div className={s.stepCtl}>
        <button className={s.step} disabled={valor <= min} onClick={() => onChange(Math.max(min, valor - passo))} aria-label={`Diminuir ${rotulo}`}>
          −
        </button>
        <span className={s.stepVal}>
          {valor}
          {sufixo}
        </span>
        <button className={s.step} disabled={valor >= max} onClick={() => onChange(Math.min(max, valor + passo))} aria-label={`Aumentar ${rotulo}`}>
          +
        </button>
      </div>
    </div>
  );
}
