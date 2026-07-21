"use client";

import type { Signal } from "@/types/market";

interface Props {
  signals: Signal[];
}

export default function SignalFeed({ signals }: Props) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-sm border border-surface-border bg-surface">
      <div className="border-b border-surface-border px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-slate-300">
        Live Signal Feed
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-2">
        {signals.length === 0 && (
          <p className="px-2 py-6 text-center font-mono text-xs text-slate-500">
            Waiting for high-probability setups…
          </p>
        )}
        {signals.map((s) => {
          const rejected = s.discarded;
          const sideColor =
            s.side === "BUY"
              ? "text-long"
              : s.side === "SELL"
                ? "text-short"
                : "text-slate-400";
          return (
            <article
              key={s.id}
              className={`border px-3 py-2 font-mono text-[11px] ${
                rejected
                  ? "border-surface-border/50 bg-surface-raised/40 opacity-60"
                  : "border-surface-border bg-surface-raised"
              }`}
            >
              <div className="mb-1 flex items-center justify-between">
                <span className={`font-semibold ${sideColor}`}>
                  {s.side} {s.underlying}
                </span>
                <span className="text-slate-400">
                  {(s.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-slate-300">
                <span>Entry {s.entry.toFixed(1)}</span>
                <span>RR {s.rr_ratio.toFixed(2)}</span>
                <span className="text-short">SL {s.stop_loss.toFixed(1)}</span>
                <span className="text-long">TGT {s.target.toFixed(1)}</span>
                {s.option_type && (
                  <span className="col-span-2 text-accent">
                    {s.option_type} {s.option_strike} @ {s.option_entry?.toFixed(1)}
                  </span>
                )}
                {s.trailing_sl != null && (
                  <span className="text-warn col-span-2">
                    Trail {s.trailing_sl.toFixed(1)}
                  </span>
                )}
              </div>
              <p className="mt-1 truncate text-slate-500">
                {rejected
                  ? `DISCARD · ${s.discard_reason ?? "gate"}`
                  : s.action_text || s.reason}
              </p>
            </article>
          );
        })}
      </div>
    </div>
  );
}
