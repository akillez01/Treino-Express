import { cx } from "@/lib/format";
import s from "./panel.module.css";

export default function Kpi({
  label,
  value,
  note,
  delta,
  ad,
  color,
}: {
  label: string;
  value: string;
  note: string;
  delta?: string;
  ad?: boolean;
  color?: string;
}) {
  return (
    <div className={s.kpi}>
      <div className={s.kpiLabel}>{label}</div>
      <div className={s.kpiValue} style={color ? { color } : undefined}>
        {value}
      </div>
      <div className={s.kpiNote}>
        {delta && <span className={cx(s.delta, ad && s.deltaAd)}>{delta}</span>}
        {note}
      </div>
    </div>
  );
}

export const variacao = (atual: number, anterior: number) => {
  if (!anterior) return undefined;
  const v = ((atual - anterior) / anterior) * 100;
  return `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(1).replace(".", ",")}%`;
};
