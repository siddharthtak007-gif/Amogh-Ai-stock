"use client";

import type { PredictionOverlay } from "@/types/market";

interface Props {
  prediction: PredictionOverlay | null;
  underlying: string;
  spot: number;
}

export default function LiveTradePlan({ prediction, underlying, spot }: Props) {
  if (!prediction) {
    return (
      <div className="rounded-sm border border-surface-border bg-surface p-4 font-mono text-sm text-slate-500">
        Prediction load ho rahi hai…
      </div>
    );
  }

  const bull = prediction.direction_bias === "BULLISH" || prediction.side === "BUY";
  const bear = prediction.direction_bias === "BEARISH" || prediction.side === "SELL";
  const active = prediction.active;

  const tone = active
    ? bull
      ? "border-long/40 bg-long/5"
      : bear
        ? "border-short/40 bg-short/5"
        : "border-surface-border bg-surface"
    : "border-warn/30 bg-warn/5";

  return (
    <section className={`border p-4 ${tone}`}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
            Live Trade Indication · {underlying}
          </p>
          <h2
            className={`mt-1 font-display text-lg font-semibold md:text-xl ${
              active ? (bull ? "text-long" : "text-short") : "text-warn"
            }`}
          >
            {prediction.headline || "Analyzing…"}
          </h2>
          <p className="mt-1 font-mono text-xs text-slate-400">
            {prediction.spot_line}
          </p>
        </div>
        <div className="text-right font-mono">
          <p className="text-[10px] uppercase text-slate-500">Confidence</p>
          <p
            className={`text-2xl font-semibold tabular-nums ${
              active ? (bull ? "text-long" : "text-short") : "text-slate-300"
            }`}
          >
            {(prediction.confidence * 100).toFixed(0)}%
          </p>
          <p className="text-[10px] text-slate-500">
            Score {prediction.score?.toFixed(2) ?? "—"} · RR{" "}
            {prediction.rr_ratio?.toFixed(2) ?? "—"}
          </p>
        </div>
      </div>

      {active ? (
        <>
          <div className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <Level
              label="BUY / ENTRY"
              hint="Itne pe entry lo"
              value={prediction.entry}
              className="text-accent"
            />
            <Level
              label="STOP LOSS (EXIT)"
              hint="Yahan pe position band / cut karo"
              value={prediction.stop_loss}
              className="text-short"
            />
            <Level
              label="TARGET 1"
              hint="Pehla book profit"
              value={prediction.target}
              className="text-long"
            />
            <Level
              label="TARGET 2 / 3"
              hint="Extend trail"
              value={prediction.target_2}
              extra={prediction.target_3}
              className="text-long"
            />
          </div>

          <div className="grid gap-3 border-t border-surface-border/80 pt-3 md:grid-cols-2">
            <div className="font-mono text-xs">
              <p className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">
                F&O Option Leg
              </p>
              <p className="text-sm text-slate-100">{prediction.action_text}</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-slate-300">
                <span>
                  Type{" "}
                  <b className={bull ? "text-long" : "text-short"}>
                    {prediction.option_type ?? "—"}
                  </b>
                </span>
                <span>
                  Strike <b>{prediction.option_strike ?? "—"}</b>
                </span>
                <span>
                  Premium BUY @ <b className="text-accent">{fmt(prediction.option_entry)}</b>
                </span>
                <span>
                  Premium EXIT (SL) <b className="text-short">{fmt(prediction.option_sl)}</b>
                </span>
                <span>
                  Prem T1 <b className="text-long">{fmt(prediction.option_target)}</b>
                </span>
                <span>
                  Prem T2 <b className="text-long">{fmt(prediction.option_target_2)}</b>
                </span>
              </div>
            </div>
            <div className="font-mono text-xs text-slate-300">
              <p className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">
                Exit plan
              </p>
              <p className="leading-relaxed text-slate-200">
                {prediction.exit_text ||
                  "Stop Loss pe EXIT (cut) karo, Target pe profit BOOK karo. Trailing SL use karo."}
              </p>
              <p className="mt-2 text-[11px] text-slate-500">
                Live spot {spot.toLocaleString("en-IN", { maximumFractionDigits: 2 })} ·{" "}
                {bear
                  ? "Market down = PE se profit"
                  : "Market up = CE se profit"}
              </p>
              {prediction.reason && (
                <p className="mt-1 truncate text-[10px] text-slate-600">
                  Why: {prediction.reason}
                </p>
              )}
            </div>
          </div>
        </>
      ) : (
        <p className="font-mono text-xs text-slate-400">
          High-probability setup wait — PCR / VWAP / trend align hone pe clear BUY CE
          ya BUY PE dikhega. Niche market me bhi PE se profit plan ready rahega.
        </p>
      )}
    </section>
  );
}

function Level({
  label,
  hint,
  value,
  extra,
  className,
}: {
  label: string;
  hint: string;
  value: number | null | undefined;
  extra?: number | null;
  className?: string;
}) {
  return (
    <div className="border border-surface-border/70 bg-black/20 px-3 py-2">
      <p className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className={`font-mono text-lg font-semibold tabular-nums ${className ?? ""}`}>
        {fmt(value)}
        {extra != null ? ` / ${fmt(extra)}` : ""}
      </p>
      <p className="font-mono text-[10px] text-slate-600">{hint}</p>
    </div>
  );
}

function fmt(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}
