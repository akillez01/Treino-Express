"use client";

import { useEffect, useState } from "react";
import Carga from "@/app/_components/Estado";
import Kpi from "@/app/_components/Kpi";
import s from "@/app/_components/panel.module.css";
import { alunosAcademia, useApi, type Aluno, type Situacao } from "@/lib/api";
import { brl, cx, desde, fmt, initials, quando } from "@/lib/format";

const PLANOS: Record<string, string> = { mensal: "Mensal", trimestral: "Trimestral", anual: "Anual" };
const FILTROS: { id: Situacao | null; label: string; chave: "todos" | Situacao }[] = [
  { id: null, label: "Todos", chave: "todos" },
  { id: "em_dia", label: "Em dia", chave: "em_dia" },
  { id: "pendente", label: "Pendente", chave: "pendente" },
  { id: "atrasado", label: "Atrasado", chave: "atrasado" },
];
const POR_PAGINA = 25;

export default function Alunos() {
  const [filtro, setFiltro] = useState<Situacao | null>(null);
  const [extra, setExtra] = useState<Aluno[]>([]);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const lista = useApi(`alunos-${filtro}`, () => alunosAcademia(filtro, 0, POR_PAGINA));

  useEffect(() => setExtra([]), [filtro]);

  async function mostrarMais(atuais: number) {
    setCarregandoMais(true);
    try {
      const prox = await alunosAcademia(filtro, atuais, POR_PAGINA);
      setExtra((e) => [...e, ...prox.itens]);
    } finally {
      setCarregandoMais(false);
    }
  }

  return (
    <Carga estado={lista}>
      {(d) => {
        const itens = [...d.itens, ...extra];
        const total = filtro ? d.contagem[filtro] : d.contagem.todos;
        return (
          <>
            <div className={s.headRow}>
              <div>
                <h1 className={s.h1}>Alunos</h1>
                <div className={s.sub}>
                  {fmt(d.contagem.todos)} cadastrados nesta unidade · {fmt(d.contagem.em_dia)} com pagamento em dia
                </div>
              </div>
              <div className={s.chips} role="tablist" aria-label="Filtrar por situação">
                {FILTROS.map((f) => (
                  <button key={f.label} role="tab" aria-selected={f.id === filtro} className={cx(s.chip, f.id === filtro && s.chipOn)} onClick={() => setFiltro(f.id)}>
                    {f.label}
                    <span className={s.chipCount}>{fmt(d.contagem[f.chave])}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className={s.kpis}>
              <Kpi label="Cadastrados" value={fmt(d.contagem.todos)} note="nesta unidade" />
              <Kpi label="Frequência média" value={`${d.frequencia_media.toFixed(1).replace(".", ",")}x`} note="treinos por aluno na semana" />
              <Kpi label="Ticket médio" value={brl(d.contagem.ticket)} note="mensalidade média" />
              <Kpi label="Em risco" value={fmt(d.contagem.pendente + d.contagem.atrasado)} note="pagamento pendente ou atrasado" />
            </div>

            <div className={s.tableCard}>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, s.colStudents)}>
                  <div>Aluno</div>
                  <div>Plano</div>
                  <div>Desde</div>
                  <div>Freq. semanal</div>
                  <div>Último check-in</div>
                  <div>Mensalidade</div>
                  <div style={{ textAlign: "right" }}>Pagamento</div>
                </div>
                {itens.map((a) => (
                  <div key={a.id} className={cx(s.row, s.colStudents)}>
                    <div className={s.person}>
                      <div className={s.av}>{initials(a.nome)}</div>
                      <div style={{ minWidth: 0 }}>
                        <div className={s.pName}>{a.nome}</div>
                        <div className={s.pMail}>{a.email}</div>
                      </div>
                    </div>
                    <div className={s.cell}>{PLANOS[a.plano] ?? a.plano}</div>
                    <div className={s.cell}>{desde(a.matriculado_em)}</div>
                    <div className={s.freq}>
                      <div className={s.freqBar}>
                        <div className={cx(s.freqFill, a.freq_semanal < 3 && s.freqLow)} style={{ width: `${Math.min(a.freq_semanal / 6, 1) * 100}%` }} />
                      </div>
                      {a.freq_semanal}x
                    </div>
                    <div className={s.cell}>{quando(a.ultimo_checkin)}</div>
                    <div className={s.strong}>{brl(a.mensalidade_centavos)}</div>
                    <div className={cx(s.badge, a.situacao === "em_dia" && s.ok, a.situacao === "atrasado" && s.bad)}>
                      {a.situacao.replace("_", " ")}
                    </div>
                  </div>
                ))}
              </div>
              {itens.length === 0 && <div className={s.vazio}>Nenhum aluno neste filtro.</div>}
              {itens.length < total && (
                <div className={s.more}>
                  <button className={s.btnGhost} disabled={carregandoMais} onClick={() => mostrarMais(itens.length)}>
                    {carregandoMais ? "Carregando..." : `Mostrar mais (${fmt(total - itens.length)} restantes)`}
                  </button>
                </div>
              )}
            </div>
          </>
        );
      }}
    </Carga>
  );
}
