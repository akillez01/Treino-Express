"use client";

import { useState } from "react";
import { gerarTreino, type Treino } from "@/lib/api";
import Execucao from "./execucao";
import s from "./page.module.css";

const FOCOS = [
  { id: "peito_triceps", nome: "Peito e Tríceps", desc: "Peitoral e posterior do braço", img: "supino-com-barra" },
  { id: "costas_biceps", nome: "Costas e Bíceps", desc: "Dorsais e anterior do braço", img: "puxada-frontal" },
  { id: "pernas", nome: "Pernas", desc: "Quadríceps, posterior, panturrilha", img: "maquina-extensora" },
  { id: "ombros", nome: "Ombros", desc: "Deltoides e trapézio", img: "press-militar-halteres" },
  { id: "bracos", nome: "Braços", desc: "Bíceps e tríceps", img: "rosca-direta" },
  { id: "fullbody", nome: "Fullbody", desc: "Corpo inteiro", img: "prensa-de-pernas" },
] as const;

const qtdExercicios = (min: number) => Math.min(Math.max(Math.round(min / 9), 3), 6);

export default function Home() {
  const [minutos, setMinutos] = useState(30);
  const [foco, setFoco] = useState<string>("pernas");
  const [treino, setTreino] = useState<Treino | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const atual = FOCOS.find((f) => f.id === foco)!;
  const data = new Date()
    .toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "short" })
    .replace(".", "");

  async function gerar() {
    setErro(null);
    setCarregando(true);
    try {
      setTreino(await gerarTreino(minutos, foco));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao falar com a API");
    } finally {
      setCarregando(false);
    }
  }

  if (treino) return <Execucao treino={treino} onSair={() => setTreino(null)} />;

  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <header className={s.head}>
          <div>
            <div className={s.eyebrow}>{data}</div>
            <h1 className={s.title}>
              Meu Treino
              <br />
              de Hoje
            </h1>
          </div>
          <div className={s.avatar} aria-hidden>
            TE
          </div>
        </header>

        <section className={s.card}>
          <div className={s.cardRow}>
            <label className={s.label} htmlFor="tempo">
              TEMPO DISPONÍVEL
            </label>
            <div>
              <span className={s.value}>{minutos}</span>
              <span className={s.unit}>min</span>
            </div>
          </div>
          <input
            id="tempo"
            className={s.slider}
            type="range"
            min={15}
            max={60}
            step={5}
            value={minutos}
            onChange={(e) => setMinutos(Number(e.target.value))}
          />
          <div className={s.limits}>
            <span>15 min</span>
            <span>60 min</span>
          </div>
        </section>

        <div className={s.grid} role="radiogroup" aria-label="Foco muscular">
          {FOCOS.map((f) => (
            <button
              key={f.id}
              role="radio"
              aria-checked={f.id === foco}
              className={`${s.focus} ${f.id === foco ? s.focusOn : ""}`}
              onClick={() => setFoco(f.id)}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img className={s.thumb} src={`/exercicios/${f.img}.png`} alt={f.nome} />
              <span>
                <span className={s.focusName}>{f.nome}</span>
                <span className={s.focusDesc}>{f.desc}</span>
              </span>
            </button>
          ))}
        </div>

        <button className={s.cta} onClick={gerar} disabled={carregando}>
          {carregando ? "Gerando..." : "Gerar Treino →"}
        </button>
        {erro && <p className={s.summary}>{erro}</p>}
        <p className={s.summary}>
          {minutos} min · {atual.nome} · {qtdExercicios(minutos)} exercícios
        </p>
      </div>
    </main>
  );
}
