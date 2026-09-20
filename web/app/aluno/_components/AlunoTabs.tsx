"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cx } from "@/lib/format";
import s from "./tabs.module.css";

const ABAS = [
  { href: "/aluno", label: "Treino", icone: "▶", exact: true },
  { href: "/aluno/progresso", label: "Progresso", icone: "↗" },
  { href: "/aluno/ranking", label: "Ranking", icone: "♛" },
  { href: "/aluno/jukebox", label: "Jukebox", icone: "♪" },
];

export default function AlunoTabs() {
  const path = usePathname();
  return (
    <nav className={s.bar} aria-label="Navegação do app">
      <div className={s.inner}>
        {ABAS.map((a) => {
          const on = a.exact ? path === a.href : path.startsWith(a.href);
          return (
            <Link key={a.href} href={a.href} className={cx(s.tab, on && s.on)} aria-current={on ? "page" : undefined}>
              <span className={s.icon} aria-hidden>
                {a.icone}
              </span>
              {a.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
