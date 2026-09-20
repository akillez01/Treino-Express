"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { cx } from "@/lib/format";
import s from "./panel.module.css";

export type Aba = { href: string; label: string; exact?: boolean };

const AREAS = [
  { href: "/aluno", label: "App" },
  { href: "/academia", label: "Academia" },
  { href: "/anunciante", label: "Anunciante" },
  { href: "/tv", label: "TV" },
];

export default function PanelShell({
  logo,
  titulo,
  subtitulo,
  abas,
  status,
  children,
}: {
  logo: string;
  titulo: string;
  subtitulo?: string;
  abas: Aba[];
  status?: ReactNode;
  children: ReactNode;
}) {
  const path = usePathname();
  const ativa = (a: Aba) => (a.exact ? path === a.href : path === a.href || path.startsWith(a.href + "/"));

  return (
    <div className={s.root}>
      <header className={s.top}>
        <div className={s.topIn}>
          <Link href="/" className={s.brand} aria-label="Voltar ao início">
            <span className={s.logo}>{logo}</span>
            <span>
              <span className={s.gym}>{titulo}</span>
              {subtitulo && <span className={s.gymSub}>{subtitulo}</span>}
            </span>
          </Link>

          <nav className={s.nav} aria-label="Seções do painel">
            {abas.map((a) => (
              <Link key={a.href} href={a.href} className={cx(s.navBtn, ativa(a) && s.navOn)} aria-current={ativa(a) ? "page" : undefined}>
                {a.label}
              </Link>
            ))}
          </nav>

          <div className={s.grow} />
          {status}
          <div className={s.switcher} aria-label="Trocar de área">
            <Link href="/">Início</Link>
            {AREAS.map((a) => (
              <Link key={a.href} href={a.href} className={cx(path.startsWith(a.href) && s.switchOn)}>
                {a.label}
              </Link>
            ))}
          </div>
        </div>
      </header>
      <main className={s.main}>{children}</main>
    </div>
  );
}
