"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import s from "./cupom.module.css";

type Cupom = { marca?: string; desconto?: string; manchete?: string; corpo?: string; cupom?: string; erro?: string };

export default function CupomPage() {
  const [c, setC] = useState<Cupom | null>(null);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setC(Object.fromEntries(q.entries()));
  }, []);

  if (!c) return null;
  const invalido = !c.cupom || c.erro;

  return (
    <main className={s.page}>
      <div className={s.card}>
        {invalido ? (
          <>
            <h1 className={s.title}>QR expirado</h1>
            <p className={s.text}>Este código já não é válido. Escaneie o anúncio atual na TV da academia.</p>
          </>
        ) : (
          <>
            <div className={s.tag}>Oferta do parceiro</div>
            <div className={s.brand}>{c.marca}</div>
            <div className={s.offer}>
              <span className={s.discount}>{c.desconto}</span>
              <span className={s.headline}>{c.manchete}</span>
            </div>
            <p className={s.text}>{c.corpo}</p>
            <div className={s.label}>Seu cupom</div>
            <div className={s.code}>{c.cupom}</div>
            <p className={s.hint}>Apresente este código no caixa da loja parceira.</p>
          </>
        )}
        <Link href="/aluno" className={s.link}>
          Ir para o app do aluno →
        </Link>
      </div>
    </main>
  );
}
