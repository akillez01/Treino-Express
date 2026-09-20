"use client";

import Link from "next/link";
import QRCode from "qrcode";
import { useCallback, useEffect, useRef, useState } from "react";
import { parearTv, telaDemo, tvSocketUrl, type TvAuth } from "@/lib/api";
import s from "./tv.module.css";

type Criativo = { marca: string; categoria: string; desconto: string; manchete: string; corpo: string; cupom: string; qr_url: string };
type Anuncio = { campanha_id: string; nonce: string; duracao_s: number; criativo: Criativo; posicao: { atual: number; total: number }; recebido: number };
type Faixa = { titulo: string; artista: string; duracao_s: number; posicao_s: number; pedida_por: string; capa_url: string | null; recebido: number };
type ItemFila = { titulo: string; artista: string; pedida_por: string; duracao: string; capa_url: string | null };
type Info = { academia: { nome: string; unidade: string | null }; sala: string };

const STORAGE = "tv_auth";
const pad = (n: number) => String(n).padStart(2, "0");
const mmss = (n: number) => `${Math.floor(n / 60)}:${pad(Math.max(0, Math.floor(n % 60)))}`;
const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const iniciais = (nome: string) => nome.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

function useQr(text: string) {
  const [svg, setSvg] = useState("");
  useEffect(() => {
    let vivo = true;
    if (!text) return;
    QRCode.toString(text, { type: "svg", margin: 0, color: { dark: "#0d0e10", light: "#0000" } }).then((r) => vivo && setSvg(r));
    return () => {
      vivo = false;
    };
  }, [text]);
  return text ? svg : "";
}

export default function PainelTV() {
  const [auth, setAuth] = useState<TvAuth | null | undefined>(undefined);
  const [kiosk, setKiosk] = useState(false);
  const [scale, setScale] = useState(1);
  const [now, setNow] = useState<Date | null>(null);
  const [tick, setTick] = useState(0);

  const [conectado, setConectado] = useState(false);
  const [info, setInfo] = useState<Info | null>(null);
  const [pausada, setPausada] = useState(false);
  const [anuncio, setAnuncio] = useState<Anuncio | null>(null);
  const [agora, setAgora] = useState<Faixa | null>(null);
  const [fila, setFila] = useState<ItemFila[]>([]);
  const [totalFila, setTotalFila] = useState(0);
  const [origem, setOrigem] = useState("");

  useEffect(() => {
    setKiosk(new URLSearchParams(window.location.search).has("kiosk"));
    setOrigem(window.location.origin);
    try {
      const salvo = localStorage.getItem(STORAGE);
      setAuth(salvo ? (JSON.parse(salvo) as TvAuth) : null);
    } catch {
      setAuth(null);
    }
  }, []);

  useEffect(() => {
    const ajustar = () => setScale(Math.min(window.innerWidth / 1920, window.innerHeight / 1080));
    ajustar();
    window.addEventListener("resize", ajustar);
    return () => window.removeEventListener("resize", ajustar);
  }, []);

  useEffect(() => {
    setNow(new Date());
    const t = setInterval(() => {
      setNow(new Date());
      setTick((v) => v + 1);
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const sair = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE);
    } catch {
      /* sem storage */
    }
    setAuth(null);
    setConectado(false);
  }, []);

  // Conexão com reconexão automática (backoff até 10 s). Depois de várias
  // recusas seguidas o token deixou de valer: volta para o pareamento.
  const falhas = useRef(0);
  useEffect(() => {
    if (!auth) return;
    let fechado = false;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout>;

    const abrir = () => {
      ws = new WebSocket(tvSocketUrl(auth));
      let abriu = false;
      ws.onopen = () => {
        abriu = true;
        falhas.current = 0;
        setConectado(true);
      };
      ws.onmessage = (m) => {
        const ev = JSON.parse(m.data as string);
        const t = Date.now();
        switch (ev.type) {
          case "ping":
            ws?.send(JSON.stringify({ type: "pong" }));
            break;
          case "tv.info":
            setInfo({ academia: ev.academia, sala: ev.sala });
            break;
          case "screen.pause":
            setPausada(!!ev.pausada);
            break;
          case "ad.show":
            setAnuncio({ ...ev, recebido: t });
            ws?.send(JSON.stringify({ type: "ad.impression", campanha_id: ev.campanha_id, nonce: ev.nonce }));
            break;
          case "jukebox.now":
            setAgora(ev.faixa ? { ...ev.faixa, recebido: t } : null);
            break;
          case "jukebox.queue":
            setFila(ev.fila);
            setTotalFila(ev.total);
            break;
        }
      };
      ws.onclose = () => {
        setConectado(false);
        if (fechado) return;
        if (!abriu && ++falhas.current >= 4) {
          sair();
          return;
        }
        timer = setTimeout(abrir, Math.min(1000 * 2 ** Math.min(falhas.current, 4), 10000));
      };
    };
    abrir();
    return () => {
      fechado = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [auth, sair]);

  const qrAd = useQr(anuncio?.criativo.qr_url ?? "");
  const qrJuke = useQr(origem ? `${origem}/aluno/jukebox` : "");

  if (auth === undefined) return <div className={s.viewport} />;
  if (auth === null)
    return (
      <Pareamento
        kiosk={kiosk}
        onOk={(a) => {
          localStorage.setItem(STORAGE, JSON.stringify(a));
          falhas.current = 0;
          setAuth(a);
        }}
      />
    );

  void tick;
  const decorrido = anuncio ? (Date.now() - anuncio.recebido) / 1000 : 0;
  const restanteAd = anuncio ? Math.max(0, Math.ceil(anuncio.duracao_s - decorrido)) : 0;
  const posMusica = agora ? Math.min(agora.duracao_s, agora.posicao_s + (Date.now() - agora.recebido) / 1000) : 0;
  const fila4 = fila.slice(0, 4);

  return (
    <div className={s.viewport}>
      {!kiosk && (
        <nav className={s.exit} aria-label="Sair da TV">
          <Link href="/">← Início</Link>
          <Link href="/academia/telas">Telas</Link>
          <button onClick={sair}>Desparear</button>
        </nav>
      )}
      <div className={s.stage} style={{ transform: `scale(${scale})` }}>
        <div className={s.bar}>
          <div className={s.logo}>{info ? iniciais(info.academia.nome) : "TE"}</div>
          <div>
            <div className={s.gym}>{info?.academia.nome ?? "Treino Express"}</div>
            <div className={s.unit}>{info ? [info.academia.unidade, info.sala].filter(Boolean).join(" · ") : "Conectando..."}</div>
          </div>
          <div className={s.grow} />
          <div className={`${s.live} ${conectado ? "" : s.liveOff}`}>
            <span className={s.liveDot} />
            {conectado ? "AO VIVO" : "RECONECTANDO"}
          </div>
          <div className={s.clock}>
            <div className={s.time}>{now ? `${pad(now.getHours())}:${pad(now.getMinutes())}` : "--:--"}</div>
            <div className={s.date}>{now ? `${DIAS[now.getDay()]}, ${now.getDate()}/${pad(now.getMonth() + 1)}` : ""}</div>
          </div>
        </div>

        <div className={s.body}>
          <section className={s.left}>
            <div className={s.sectionHead}>
              <div className={`${s.sectionTag} ${s.adTag}`}>
                <span className={s.adDot} />
                Oferta do parceiro
              </div>
              {anuncio && (
                <div className={s.count}>
                  Anúncio {anuncio.posicao.atual} de {anuncio.posicao.total}
                </div>
              )}
            </div>

            {pausada ? (
              <div className={`${s.adCard} ${s.vazioCard}`}>
                <div className={s.vazioTitulo}>Exibição pausada</div>
                <div className={s.vazioTexto}>A academia pausou esta tela. Ela volta sozinha quando for retomada.</div>
              </div>
            ) : anuncio ? (
              <div className={s.adCard}>
                <div className={s.brand}>
                  <div className={s.mark}>{iniciais(anuncio.criativo.marca)}</div>
                  <div>
                    <div className={s.brandName}>{anuncio.criativo.marca}</div>
                    <div className={s.brandCat}>{anuncio.criativo.categoria}</div>
                  </div>
                </div>
                <div className={s.offer}>
                  <div className={s.discount}>{anuncio.criativo.desconto}</div>
                  <div className={s.headline}>{anuncio.criativo.manchete}</div>
                </div>
                <div className={s.copy}>{anuncio.criativo.corpo}</div>
                <div className={s.spacer} />
                <div className={s.redeem}>
                  <div className={s.qrBig} dangerouslySetInnerHTML={{ __html: qrAd }} />
                  <div>
                    <div className={s.redeemTitle}>Escaneie para resgatar</div>
                    <div className={s.redeemSub}>
                      Válido hoje na {anuncio.criativo.marca} · Cupom {anuncio.criativo.cupom}
                    </div>
                    <div className={s.swap}>
                      <span className={s.swapDot} />
                      Troca em 00:{pad(restanteAd)}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className={`${s.adCard} ${s.vazioCard}`}>
                <div className={s.vazioTitulo}>Aguardando anúncios</div>
                <div className={s.vazioTexto}>Nenhuma campanha ativa neste horário para esta academia.</div>
              </div>
            )}
          </section>

          <section className={s.right}>
            <div className={s.sectionHead}>
              <div className={`${s.sectionTag} ${s.jukeTag}`}>
                <span className={s.eq}>
                  <span />
                  <span />
                  <span />
                </span>
                Jukebox
              </div>
              <div className={s.count}>{totalFila} pedidos na fila</div>
            </div>

            <div className={s.now}>
              {agora ? (
                <>
                  <div className={s.nowRow}>
                    {agora.capa_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img className={s.cover} src={agora.capa_url} alt="" />
                    ) : (
                      <div className={s.cover}>capa do álbum</div>
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className={s.label}>Tocando agora</div>
                      <div className={s.song}>{agora.titulo}</div>
                      <div className={s.artist}>{agora.artista}</div>
                    </div>
                  </div>
                  <div className={s.progress}>
                    <div className={s.track}>
                      <div className={s.fill} style={{ width: `${(posMusica / agora.duracao_s) * 100}%` }} />
                    </div>
                    <div className={s.times}>
                      <span>{mmss(posMusica)}</span>
                      <span>Pedida por {agora.pedida_por}</span>
                      <span>{mmss(agora.duracao_s)}</span>
                    </div>
                  </div>
                </>
              ) : (
                <div className={s.nowRow}>
                  <div className={s.cover}>♪</div>
                  <div>
                    <div className={s.label}>Tocando agora</div>
                    <div className={s.song}>Nenhuma música</div>
                    <div className={s.artist}>Peça a sua pelo QR Code abaixo</div>
                  </div>
                </div>
              )}
            </div>

            <div className={`${s.label} ${s.queueLabel}`}>Na fila</div>
            <div className={s.queue}>
              {fila4.map((t, i) => (
                <div key={t.titulo + i} className={s.item}>
                  <div className={s.pos}>{pad(i + 1)}</div>
                  <div className={s.itemMain}>
                    <div className={s.itemTitle}>{t.titulo}</div>
                    <div className={s.itemArtist}>{t.artista}</div>
                  </div>
                  <div className={s.who}>{t.pedida_por}</div>
                  <div className={s.dur}>{t.duracao}</div>
                </div>
              ))}
            </div>

            <div className={s.request}>
              <div className={s.qrSmall} dangerouslySetInnerHTML={{ __html: qrJuke }} />
              <div>
                <div className={s.requestTitle}>Peça sua música</div>
                <div className={s.requestSub}>Escaneie e escolha a próxima faixa direto do app.</div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function Pareamento({ kiosk, onOk }: { kiosk: boolean; onOk: (a: TvAuth) => void }) {
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErro(null);
    try {
      onOk(await parearTv(codigo.trim()));
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao parear");
    } finally {
      setBusy(false);
    }
  }

  async function demo() {
    setBusy(true);
    setErro(null);
    try {
      onOk(await telaDemo());
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("demo")) void demo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className={s.pair}>
      {!kiosk && (
        <Link href="/" className={s.pairBack}>
          ← Início
        </Link>
      )}
      <form className={s.pairCard} onSubmit={enviar}>
        <div className={s.pairLogo}>TE</div>
        <h1 className={s.pairTitle}>Parear esta TV</h1>
        <p className={s.pairText}>
          No painel da academia, abra <b>Telas → Adicionar tela</b>, gere o código e digite-o aqui.
        </p>
        <input
          className={s.pairInput}
          value={codigo}
          onChange={(e) => setCodigo(e.target.value.toUpperCase())}
          placeholder="ABC-123"
          maxLength={7}
          autoFocus
          aria-label="Código de pareamento"
        />
        {erro && <div className={s.pairErro}>{erro}</div>}
        <button className={s.pairBtn} disabled={busy || codigo.trim().length < 6}>
          {busy ? "Conectando..." : "Parear"}
        </button>
        <button type="button" className={s.pairGhost} onClick={demo} disabled={busy}>
          Usar tela de demonstração
        </button>
      </form>
    </main>
  );
}
