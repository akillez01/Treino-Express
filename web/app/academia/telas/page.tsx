"use client";

import { useState } from "react";
import Carga from "@/app/_components/Estado";
import s from "@/app/_components/panel.module.css";
import { parearTela, pausarTela, telasAcademia, useApi, type Tela } from "@/lib/api";
import { cx, fmt, segundosAtras } from "@/lib/format";

const mmss = (n: number) => `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`;

export default function Telas() {
  const dados = useApi("telas", telasAcademia);
  const [codigo, setCodigo] = useState<string | null>(null);
  const [gerando, setGerando] = useState(false);

  async function gerarCodigo() {
    setGerando(true);
    try {
      const r = await parearTela();
      setCodigo(r.codigo);
      dados.recarregar();
    } finally {
      setGerando(false);
    }
  }

  return (
    <Carga estado={dados}>
      {(d) => {
        const pareadas = d.telas.filter((t) => t.pareada_em);
        const aguardando = d.telas.filter((t) => !t.pareada_em);
        const online = pareadas.filter((t) => t.status === "online").length;
        const totalFila = d.fila.reduce((a, f) => a + f.duracao_segundos, 0);
        return (
          <>
            <div className={s.headRow}>
              <div>
                <h1 className={s.h1}>Telas</h1>
                <div className={s.sub}>
                  {pareadas.length} telas pareadas · {online} transmitindo agora
                </div>
              </div>
            </div>

            <div className={s.scrGrid}>
              {pareadas.map((t) => (
                <TelaCard key={t.id} tela={t} onChange={dados.recarregar} />
              ))}

              <div className={s.pair}>
                <div className={s.plus}>+</div>
                <div className={s.cardTitle}>Adicionar tela</div>
                <div className={s.pairTxt}>Abra o navegador da TV em modo kiosk e pareie com o código de 6 dígitos.</div>
                {(codigo || aguardando[0]?.codigo_pareamento) && (
                  <div className={s.code}>{codigo ?? aguardando[0]?.codigo_pareamento}</div>
                )}
                <button className={s.btnGhost} disabled={gerando} onClick={gerarCodigo}>
                  {gerando ? "Gerando..." : codigo || aguardando.length ? "Gerar novo código" : "Gerar código de pareamento"}
                </button>
              </div>
            </div>

            <div className={s.card} style={{ marginTop: 14 }}>
              <div className={s.spread}>
                <div className={s.cardTitle}>Fila da Jukebox</div>
                <div className={s.footAcc}>
                  {d.fila.length} pedidos · {Math.round(totalFila / 60)} min
                </div>
              </div>
              <div className={s.queue}>
                {d.fila.length === 0 && <div className={s.vazio}>Ninguém pediu música ainda.</div>}
                {d.fila.map((q, i) => (
                  <div key={q.titulo + i} className={s.q}>
                    <div className={s.qPos}>{String(i + 1).padStart(2, "0")}</div>
                    <div className={s.grow1}>
                      <div className={s.pName}>{q.titulo}</div>
                      <div className={s.pMail}>{q.artista}</div>
                    </div>
                    <div className={s.qWho}>{q.solicitante.split(" ")[0]}</div>
                    <div className={s.qDur}>{mmss(q.duracao_segundos)}</div>
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

function TelaCard({ tela, onChange }: { tela: Tela; onChange: () => void }) {
  const [ocupada, setOcupada] = useState(false);
  const on = tela.status === "online";
  return (
    <div className={cx(s.scrCard, on && s.scrCardOn)}>
      <div className={s.scrHead}>
        <div className={s.scrTitle}>
          <span className={cx(s.dot, !on && s.dotOff)} />
          {tela.sala}
        </div>
        <span className={cx(s.state, !on && s.stateOff)}>{on ? "ONLINE" : tela.status === "pausada" ? "PAUSADA" : "OFFLINE"}</span>
      </div>
      <div className={s.now}>
        <div className={s.tiny}>Situação</div>
        <div className={s.nowT}>{on ? "Transmitindo anúncios e jukebox" : "Exibição pausada pela academia"}</div>
      </div>
      <div className={s.stats}>
        {[
          ["Última sync", on ? segundosAtras(tela.ultimo_heartbeat) : "pausada"],
          ["Resolução", tela.resolucao],
          ["QR no mês", fmt(tela.qr_mes)],
          ["Pareada", tela.pareada_em ? new Date(tela.pareada_em).toLocaleDateString("pt-BR") : "—"],
        ].map(([l, v]) => (
          <div key={l}>
            <div className={s.tiny}>{l}</div>
            <div className={s.statV}>{v}</div>
          </div>
        ))}
      </div>
      <button
        className={cx(s.toggle, !on && s.toggleResume)}
        disabled={ocupada}
        onClick={async () => {
          setOcupada(true);
          try {
            await pausarTela(tela.id);
            onChange();
          } finally {
            setOcupada(false);
          }
        }}
      >
        <span style={{ fontSize: 11 }}>{on ? "❚❚" : "▶"}</span>
        {on ? "Pausar exibição" : "Retomar exibição"}
      </button>
    </div>
  );
}
