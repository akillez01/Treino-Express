"use client";

import QRCode from "qrcode";
import { useEffect, useRef, useState } from "react";
import s from "./tv.module.css";

// Placeholder até o gateway WebSocket existir (docs/05): hoje a rotação de
// anúncio e o progresso da música são simulados por um timer local.
const ADS = [
  { brand: "Nutri Prime Suplementos", mark: "NP", category: "Suplementos · 300 m da academia", discount: "15%", headline: "OFF em toda a linha de whey", body: "Aproveite o descanso! Ganhe 15% OFF na Loja de Suplementos parceira. Olhe para a TV da academia para escanear o QR Code.", coupon: "PRIME15" },
  { brand: "Açaí do Ponto", mark: "AP", category: "Alimentação · Mesmo quarteirão", discount: "20%", headline: "OFF na tigela pós-treino", body: "Recupere as energias com 20% OFF em qualquer tigela de 500 ml. Escaneie o QR Code e apresente no caixa até as 22h.", coupon: "ACAI20" },
  { brand: "Fisio Movimento", mark: "FM", category: "Saúde · Avaliação gratuita", discount: "1ª", headline: "sessão de avaliação sem custo", body: "Dor no joelho ou no ombro? Agende uma avaliação postural gratuita com a clínica parceira da academia.", coupon: "MOVE01" },
  { brand: "Loja Iron Wear", mark: "IW", category: "Vestuário esportivo", discount: "25%", headline: "OFF na coleção de treino", body: "Camisetas dry-fit e leggings com 25% OFF para alunos. Escaneie o QR Code e receba o cupom no seu celular.", coupon: "IRON25" },
];

const QUEUE = [
  { title: "Não Vou Parar", artist: "Bloco do Ritmo", requester: "Marina R.", dur: "3:12" },
  { title: "Peso Morto", artist: "Trio Cadência", requester: "Diego S.", dur: "2:58" },
  { title: "Meia Noite no Cardio", artist: "Áurea Base", requester: "Camila T.", dur: "3:44" },
  { title: "Série Final", artist: "Coletivo Norte", requester: "Rafa L.", dur: "4:02" },
  { title: "Sem Intervalo", artist: "Mila Duarte", requester: "Júlia P.", dur: "3:21" },
];

const AD_SECONDS = 24;
const SONG_TOTAL = 212;
const ORIGIN = "https://treinoexpress.vercel.app";
const QUEUE_ROWS = 4;

const pad = (n: number) => String(n).padStart(2, "0");
const mmss = (n: number) => `${Math.floor(n / 60)}:${pad(n % 60)}`;
const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

function useQr(text: string) {
  const [svg, setSvg] = useState("");
  useEffect(() => {
    let vivo = true;
    QRCode.toString(text, { type: "svg", margin: 0, color: { dark: "#0d0e10", light: "#0000" } }).then(
      (r) => vivo && setSvg(r),
    );
    return () => {
      vivo = false;
    };
  }, [text]);
  return svg;
}

export default function PainelTV() {
  const [ad, setAd] = useState(0);
  const [adLeft, setAdLeft] = useState(AD_SECONDS);
  const [songAt, setSongAt] = useState(74);
  const [now, setNow] = useState<Date | null>(null);
  const [scale, setScale] = useState(1);
  const ref = useRef<HTMLDivElement>(null);

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
      setSongAt((v) => (v + 1) % SONG_TOTAL);
      setAdLeft((left) => {
        if (left <= 1) {
          setAd((a) => (a + 1) % ADS.length);
          return AD_SECONDS;
        }
        return left - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const a = ADS[ad];
  const qrAd = useQr(`${ORIGIN}/r/demo/${a.coupon}`);
  const qrJuke = useQr(`${ORIGIN}/jukebox`);

  return (
    <div className={s.viewport}>
      <div ref={ref} className={s.stage} style={{ transform: `scale(${scale})` }}>
        <div className={s.bar}>
          <div className={s.logo}>IF</div>
          <div>
            <div className={s.gym}>Iron Factory</div>
            <div className={s.unit}>Unidade Vila Prudente · Sala de musculação</div>
          </div>
          <div className={s.grow} />
          <div className={s.live}>
            <span className={s.liveDot} />
            AO VIVO
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
              <div className={s.count}>
                Anúncio {ad + 1} de {ADS.length}
              </div>
            </div>

            <div className={s.adCard}>
              <div className={s.brand}>
                <div className={s.mark}>{a.mark}</div>
                <div>
                  <div className={s.brandName}>{a.brand}</div>
                  <div className={s.brandCat}>{a.category}</div>
                </div>
              </div>
              <div className={s.offer}>
                <div className={s.discount}>{a.discount}</div>
                <div className={s.headline}>{a.headline}</div>
              </div>
              <div className={s.copy}>{a.body}</div>
              <div className={s.spacer} />
              <div className={s.redeem}>
                <div className={s.qrBig} dangerouslySetInnerHTML={{ __html: qrAd }} />
                <div>
                  <div className={s.redeemTitle}>Escaneie para resgatar</div>
                  <div className={s.redeemSub}>
                    Válido hoje na {a.brand} · Cupom {a.coupon}
                  </div>
                  <div className={s.swap}>
                    <span className={s.swapDot} />
                    Troca em 00:{pad(adLeft)}
                  </div>
                </div>
              </div>
            </div>

            <div className={s.adBars}>
              {ADS.map((x, i) => (
                <span key={x.coupon} className={i === ad ? s.on : undefined} />
              ))}
            </div>
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
              <div className={s.count}>{QUEUE.length} pedidos na fila</div>
            </div>

            <div className={s.now}>
              <div className={s.nowRow}>
                <div className={s.cover}>capa do álbum</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className={s.label}>Tocando agora</div>
                  <div className={s.song}>Ritmo de Ferro</div>
                  <div className={s.artist}>Banda Alta Carga</div>
                </div>
              </div>
              <div className={s.progress}>
                <div className={s.track}>
                  <div className={s.fill} style={{ width: `${(songAt / SONG_TOTAL) * 100}%` }} />
                </div>
                <div className={s.times}>
                  <span>{mmss(songAt)}</span>
                  <span>Pedida por Lucas M.</span>
                  <span>{mmss(SONG_TOTAL)}</span>
                </div>
              </div>
            </div>

            <div className={`${s.label} ${s.queueLabel}`}>Na fila</div>
            <div className={s.queue}>
              {QUEUE.slice(0, QUEUE_ROWS).map((t, i) => (
                <div key={t.title} className={s.item}>
                  <div className={s.pos}>{pad(i + 1)}</div>
                  <div className={s.itemMain}>
                    <div className={s.itemTitle}>{t.title}</div>
                    <div className={s.itemArtist}>{t.artist}</div>
                  </div>
                  <div className={s.who}>{t.requester}</div>
                  <div className={s.dur}>{t.dur}</div>
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
