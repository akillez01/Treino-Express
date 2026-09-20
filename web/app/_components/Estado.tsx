"use client";

import type { ReactNode } from "react";
import type { Estado } from "@/lib/api";
import s from "./panel.module.css";

/** Renderiza carregando / erro (com "Tentar de novo") / conteúdo. */
export default function Carga<T>({
  estado,
  children,
}: {
  estado: Estado<T>;
  children: (dados: T) => ReactNode;
}) {
  if (estado.data) return <>{children(estado.data)}</>;
  if (estado.erro)
    return (
      <div className={s.erroBox} role="alert">
        <div className={s.erroTitulo}>Não foi possível carregar os dados</div>
        <div className={s.erroTexto}>{estado.erro}</div>
        <button className={s.erroBtn} onClick={estado.recarregar}>
          Tentar de novo
        </button>
      </div>
    );
  return (
    <div className={s.skeleton} aria-busy="true" aria-label="Carregando">
      <div className={s.skRow}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={s.skKpi} />
        ))}
      </div>
      <div className={s.skBlock} />
    </div>
  );
}
