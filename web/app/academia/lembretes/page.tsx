"use client";

import { useState } from "react";
import Carga from "@/app/_components/Estado";
import s from "@/app/_components/panel.module.css";
import { enviarLembretes, lembretesAcademia, useApi, type CandidatoLembrete } from "@/lib/api";
import { cx, quando } from "@/lib/format";

const BLOQUEIO: Record<string, string> = {
  sem_consentimento: "Não aceitou lembretes",
  sem_telefone: "Sem telefone",
  enviado_recentemente: "Lembrado há menos de 7 dias",
};
const STATUS: Record<string, string> = { enviado: "ENVIADO", simulado: "SIMULADO", falhou: "FALHOU" };

export default function Lembretes() {
  const dados = useApi("lembretes", lembretesAcademia);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string } | null>(null);

  async function enviar(ids: string[] | null) {
    setBusy(true);
    setAviso(null);
    try {
      const r = await enviarLembretes(ids);
      const falhas = r.resultados.filter((x) => x.status === "falhou").length;
      setAviso({
        ok: falhas === 0,
        texto: r.resultados.length
          ? `${r.resultados.length} lembrete(s) ${r.simulado ? "simulado(s) (WhatsApp não configurado)" : "enviado(s)"}${falhas ? `, ${falhas} com falha` : ""}.`
          : "Nenhum lembrete elegível para enviar agora.",
      });
      setSel(new Set());
      dados.recarregar();
    } catch (e) {
      setAviso({ ok: false, texto: e instanceof Error ? e.message : "Não foi possível enviar" });
    } finally {
      setBusy(false);
    }
  }

  const alternar = (id: string) =>
    setSel((atual) => {
      const n = new Set(atual);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <Carga estado={dados}>
      {(d) => {
        const elegiveis = d.candidatos.filter((c) => c.pode_enviar);
        return (
          <>
            <div className={s.headRow}>
              <div>
                <h1 className={s.h1}>Lembretes</h1>
                <div className={s.sub}>
                  Alunos que vinham treinando e quebraram a sequência · {d.candidatos.length} candidatos, {elegiveis.length} podem receber
                </div>
              </div>
              <div className={s.headActions}>
                <button className={s.btnGhost} disabled={busy || sel.size === 0} onClick={() => enviar([...sel])}>
                  Enviar aos selecionados ({sel.size})
                </button>
                <button className={s.btnPrimary} disabled={busy || elegiveis.length === 0} onClick={() => enviar(null)}>
                  {busy ? "Enviando..." : `Enviar a todos (${elegiveis.length})`}
                </button>
              </div>
            </div>

            <div className={cx(s.banner, d.whatsapp_configurado ? s.bannerOk : s.bannerAviso)} role="status">
              {d.whatsapp_configurado
                ? "WhatsApp Business conectado: os lembretes são enviados de verdade."
                : "WhatsApp ainda não configurado neste servidor: os lembretes ficam registrados como SIMULADOS (nada é enviado). Defina WHATSAPP_TOKEN e WHATSAPP_PHONE_NUMBER_ID."}
            </div>
            {aviso && (
              <div className={cx(s.banner, aviso.ok ? s.bannerOk : s.bannerErro)} role="status">
                {aviso.texto}
              </div>
            )}

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Quebraram a sequência</div>
                <div className={s.gymSub}>Só recebem mensagem alunos que aceitaram, no máximo 1 a cada 7 dias</div>
              </div>
              <div className={s.scroll}>
                <div className={cx(s.row, s.rowHead, s.colLemb)}>
                  <div />
                  <div>Aluno</div>
                  <div>Parado há</div>
                  <div>Sequência</div>
                  <div>Telefone</div>
                  <div style={{ textAlign: "right" }}>Situação</div>
                </div>
                {d.candidatos.length === 0 && <div className={s.vazio}>Ninguém quebrou a sequência agora. 🎉</div>}
                {d.candidatos.map((c) => (
                  <Linha key={c.aluno_id} c={c} marcado={sel.has(c.aluno_id)} onMarcar={() => alternar(c.aluno_id)} />
                ))}
              </div>
            </div>

            <div className={s.tableCard}>
              <div className={s.tableHead}>
                <div className={s.cardTitle}>Histórico de envios</div>
              </div>
              <div className={s.scroll}>
                {d.historico.length === 0 && <div className={s.vazio}>Nenhum lembrete enviado ainda.</div>}
                {d.historico.map((h) => (
                  <div key={h.id} className={cx(s.row, s.colHist)}>
                    <div className={s.cell}>{quando(h.criado_em)}</div>
                    <div className={s.pName}>{h.nome}</div>
                    <div className={s.cell} title={h.mensagem} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {h.erro ?? h.mensagem}
                    </div>
                    <div className={cx(s.badge, h.status === "enviado" && s.ok, h.status === "falhou" && s.bad)}>{STATUS[h.status]}</div>
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

function Linha({ c, marcado, onMarcar }: { c: CandidatoLembrete; marcado: boolean; onMarcar: () => void }) {
  return (
    <div className={cx(s.row, s.colLemb)}>
      <input type="checkbox" checked={marcado} disabled={!c.pode_enviar} onChange={onMarcar} aria-label={`Selecionar ${c.nome}`} />
      <div style={{ minWidth: 0 }}>
        <div className={s.pName}>{c.nome}</div>
        <div className={s.pMail}>{c.dias_ativos_30d} dias ativos no mês anterior</div>
      </div>
      <div className={s.cell}>{c.dias_sem_treinar} dias</div>
      <div className={s.cell}>{c.sequencia_perdida} dias seguidos</div>
      <div className={s.cell}>
        {c.telefone ?? "—"}
        {c.wa_link && (
          <>
            {" · "}
            <a href={c.wa_link} target="_blank" rel="noreferrer" className={s.link} title="Abre a conversa no seu WhatsApp para enviar manualmente">
              abrir
            </a>
          </>
        )}
      </div>
      <div className={cx(s.badge, c.pode_enviar && s.ok)}>{c.pode_enviar ? "pode receber" : BLOQUEIO[c.bloqueio ?? ""]}</div>
    </div>
  );
}
