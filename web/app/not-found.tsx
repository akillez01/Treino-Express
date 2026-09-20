import Link from "next/link";
import s from "./hub.module.css";

export default function NotFound() {
  return (
    <main className={s.page} style={{ alignItems: "center" }}>
      <div className={s.wrap} style={{ textAlign: "center" }}>
        <h1 className={s.title}>Página não encontrada</h1>
        <p className={s.lead} style={{ margin: "12px auto 24px" }}>
          O endereço não existe ou foi movido.
        </p>
        <Link href="/" className={s.card} style={{ display: "inline-flex", padding: "14px 22px" }}>
          <span className={s.go} style={{ margin: 0 }}>
            ← Voltar ao início
          </span>
        </Link>
      </div>
    </main>
  );
}
