"use client";

import { useState } from "react";
import {
  minhasPreferencias,
  removerMetaExercicio,
  salvarMetaExercicio,
  salvarPreferencias,
  useApi,
  type MetaExercicio,
} from "@/lib/api";
import { cx, dataCurta } from "@/lib/format";
import s from "./progresso.module.css";

const kg = (v: number) => v.toString().replace(".", ",");

/** 5511999990000 -> (11) 99999-0000 */
const formatarTelefone = (bruto: string | null) => {
  const d = (bruto ?? "").replace(/\D/g, "");
  const local = d.startsWith("55") && d.length >= 12 ? d.slice(2) : d;
  if (local.length === 11) return `(${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7)}`;
  if (local.length === 10) return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  return bruto ?? "";
};

export function Metas({ metas, opcoes, recarregar }: { metas: MetaExercicio[]; opcoes: string[]; recarregar: () => void }) {
  const [abrir, setAbrir] = useState(false);
  const [exercicio, setExercicio] = useState("");
  const [alvo, setAlvo] = useState("");
  const [prazo, setPrazo] = useState("");
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    const valor = parseFloat(alvo.replace(",", "."));
    if (!exercicio || !(valor > 0)) return setErro("Escolha o exercício e um peso maior que zero.");
    setBusy(true);
    setErro(null);
    try {
      await salvarMetaExercicio(exercicio, valor, prazo || null);
      setAbrir(false);
      setExercicio("");
      setAlvo("");
      setPrazo("");
      recarregar();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar");
    } finally {
      setBusy(false);
    }
  }

  async function remover(nome: string) {
    await removerMetaExercicio(nome);
    recarregar();
  }

  return (
    <section className={s.card}>
      <div className={s.cardHead}>
        <div className={s.cardTitle}>Minhas metas</div>
        <button className={s.mini} onClick={() => setAbrir((v) => !v)}>
          {abrir ? "Cancelar" : "+ Nova meta"}
        </button>
      </div>

      {abrir && (
        <form className={s.form} onSubmit={salvar}>
          <label>
            Exercício
            <select value={exercicio} onChange={(e) => setExercicio(e.target.value)}>
              <option value="">Escolha...</option>
              {opcoes.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>
          <div className={s.formRow}>
            <label>
              Meta (kg)
              <input inputMode="decimal" value={alvo} onChange={(e) => setAlvo(e.target.value)} placeholder="60" maxLength={6} />
            </label>
            <label>
              Prazo (opcional)
              <input type="date" value={prazo} onChange={(e) => setPrazo(e.target.value)} min={new Date().toISOString().slice(0, 10)} />
            </label>
          </div>
          {erro && <p className={s.erro}>{erro}</p>}
          <button className={s.salvar} disabled={busy}>
            {busy ? "Salvando..." : "Salvar meta"}
          </button>
        </form>
      )}

      {metas.length === 0 && !abrir && <p className={s.hint}>Defina um peso-alvo para um exercício e acompanhe o quanto falta.</p>}

      <ul className={s.list}>
        {metas.map((m) => (
          <li key={m.exercicio} className={s.meta}>
            <div className={s.metaTop}>
              <div>
                <div className={s.recNome}>{m.exercicio}</div>
                <div className={s.recSub}>
                  {kg(m.atual_kg)} de {kg(m.alvo_kg)} kg
                  {m.prazo && ` · até ${dataCurta(m.prazo)}`}
                </div>
              </div>
              <button className={s.x} onClick={() => remover(m.exercicio)} aria-label={`Remover meta de ${m.exercicio}`}>
                ✕
              </button>
            </div>
            <div className={s.track}>
              <div className={cx(s.fill, m.atingida && s.fillOk)} style={{ width: `${m.pct}%` }} />
            </div>
            <div className={s.metaFoot}>
              {m.atingida ? (
                <span className={s.up}>Meta atingida!</span>
              ) : (
                <>
                  <span>{m.pct}% concluído</span>
                  <span>
                    {m.previsao_dias !== null
                      ? `No ritmo atual: ~${m.previsao_dias} dias`
                      : "Treine este exercício para ver a previsão"}
                    {m.dias_restantes !== null && m.previsao_dias !== null && m.previsao_dias > m.dias_restantes && (
                      <b className={s.down}> · além do prazo</b>
                    )}
                  </span>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Preferencias() {
  const prefs = useApi("prefs", minhasPreferencias);
  const [tel, setTel] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; texto: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const p = prefs.data;
  if (!p) return null;
  const telefone = tel ?? formatarTelefone(p.telefone);

  async function salvar(dados: Parameters<typeof salvarPreferencias>[0]) {
    setBusy(true);
    setMsg(null);
    try {
      await salvarPreferencias(dados);
      setMsg({ ok: true, texto: "Preferências salvas." });
      setTel(null);
      prefs.recarregar();
    } catch (e) {
      setMsg({ ok: false, texto: e instanceof Error ? e.message : "Não foi possível salvar" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={s.card}>
      <div className={s.cardTitle}>Privacidade e lembretes</div>

      <label className={s.opt}>
        <input type="checkbox" checked={p.ranking_visivel} disabled={busy} onChange={(e) => salvar({ ranking_visivel: e.target.checked })} />
        <span>
          <b>Aparecer no ranking da academia</b>
          <small>Outros alunos veem só seu primeiro nome e a inicial do sobrenome.</small>
        </span>
      </label>

      <label className={s.opt}>
        <input
          type="checkbox"
          checked={p.lembretes_whatsapp}
          disabled={busy}
          onChange={(e) => salvar({ lembretes_whatsapp: e.target.checked, ...(telefone ? { telefone } : {}) })}
        />
        <span>
          <b>Receber lembretes no WhatsApp</b>
          <small>Um aviso se você ficar alguns dias sem treinar. No máximo 1 por semana. Você pode desligar quando quiser.</small>
        </span>
      </label>

      <label className={s.tel}>
        Telefone (com DDD)
        <div className={s.formRow}>
          <input inputMode="tel" value={telefone} onChange={(e) => setTel(e.target.value)} placeholder="(11) 99999-0000" maxLength={20} />
          <button className={s.mini} disabled={busy || telefone === formatarTelefone(p.telefone)} onClick={() => salvar({ telefone })} type="button">
            Salvar
          </button>
        </div>
      </label>

      {msg && <p className={msg.ok ? s.hint : s.erro}>{msg.texto}</p>}
    </section>
  );
}
