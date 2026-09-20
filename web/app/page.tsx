import Link from "next/link";
import s from "./hub.module.css";

const AREAS = [
  {
    href: "/aluno",
    tag: "Aluno",
    titulo: "App do aluno",
    texto: "Escolha o tempo e o foco, gere o treino e use o descanso entre as séries com ofertas e jukebox.",
    icone: "▶",
  },
  {
    href: "/academia",
    tag: "Gestor",
    titulo: "Painel da academia",
    texto: "Alunos, financeiro, repasses dos anunciantes e o controle das telas da unidade.",
    icone: "▦",
  },
  {
    href: "/anunciante",
    tag: "Comércio parceiro",
    titulo: "Painel do anunciante",
    texto: "Campanhas, funil de escaneamentos e resgates, e o crédito para anunciar nas academias.",
    icone: "◎",
  },
  {
    href: "/tv",
    tag: "Kiosk",
    titulo: "Painel da TV",
    texto: "Tela da academia: anúncio do parceiro de um lado, fila da jukebox do outro.",
    icone: "▭",
  },
];

export default function Inicio() {
  return (
    <main className={s.page}>
      <div className={s.wrap}>
        <header className={s.head}>
          <div className={s.logo}>TE</div>
          <div>
            <h1 className={s.title}>Treino Express</h1>
            <p className={s.lead}>
              Treino rápido para o aluno, receita extra para a academia e clientes novos para o comércio local.
            </p>
          </div>
        </header>

        <div className={s.grid}>
          {AREAS.map((a) => (
            <Link key={a.href} href={a.href} className={s.card}>
              <span className={s.icon} aria-hidden>
                {a.icone}
              </span>
              <span className={s.tag}>{a.tag}</span>
              <span className={s.cardTitle}>{a.titulo}</span>
              <span className={s.cardText}>{a.texto}</span>
              <span className={s.go}>Abrir →</span>
            </Link>
          ))}
        </div>

        <p className={s.foot}>Ambiente de demonstração com dados de exemplo.</p>
      </div>
    </main>
  );
}
