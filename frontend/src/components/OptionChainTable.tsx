"use client";

import type { OptionContract, ChainMetrics } from "@/types/market";

interface Props {
  chain: OptionContract[];
  metrics: ChainMetrics | null;
  spot: number;
}

export default function OptionChainTable({ chain, metrics, spot }: Props) {
  const strikes = Array.from(new Set(chain.map((c) => c.strike))).sort(
    (a, b) => a - b
  );

  const byKey = new Map(
    chain.map((c) => [`${c.strike}-${c.option_type}`, c] as const)
  );

  const atm = strikes.reduce(
    (best, s) => (Math.abs(s - spot) < Math.abs(best - spot) ? s : best),
    strikes[0] ?? 0
  );

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-sm border border-surface-border bg-surface">
      <div className="flex flex-wrap items-center gap-3 border-b border-surface-border px-3 py-2 font-mono text-[11px] text-slate-400">
        <span className="uppercase tracking-widest text-slate-300">
          Option Chain
        </span>
        {metrics && (
          <>
            <span>PCR {metrics.pcr_oi.toFixed(2)}</span>
            <span>MaxPain {metrics.max_pain}</span>
            <span>VWAP {metrics.vwap.toFixed(1)}</span>
            <span>ATM IV {(metrics.atm_iv * 100).toFixed(1)}%</span>
            {metrics.volume_breakout && (
              <span className="text-warn">VOL BREAKOUT</span>
            )}
          </>
        )}
      </div>

      <div className="overflow-auto">
        <table className="w-full min-w-[640px] border-collapse font-mono text-[11px]">
          <thead className="sticky top-0 bg-surface-raised text-slate-400">
            <tr>
              <th className="px-2 py-1.5 text-right">CE OI</th>
              <th className="px-2 py-1.5 text-right">CE ΔOI</th>
              <th className="px-2 py-1.5 text-right">CE LTP</th>
              <th className="px-2 py-1.5 text-right">IV</th>
              <th className="px-2 py-1.5 text-center text-slate-200">Strike</th>
              <th className="px-2 py-1.5 text-right">IV</th>
              <th className="px-2 py-1.5 text-right">PE LTP</th>
              <th className="px-2 py-1.5 text-right">PE ΔOI</th>
              <th className="px-2 py-1.5 text-right">PE OI</th>
            </tr>
          </thead>
          <tbody>
            {strikes.map((strike) => {
              const ce = byKey.get(`${strike}-CE`);
              const pe = byKey.get(`${strike}-PE`);
              const isAtm = strike === atm;
              const ceBuild = (ce?.oi_change ?? 0) > 0;
              const peBuild = (pe?.oi_change ?? 0) > 0;
              return (
                <tr
                  key={strike}
                  className={`border-t border-surface-border/60 ${
                    isAtm ? "bg-accent/10" : "hover:bg-white/[0.02]"
                  }`}
                >
                  <td
                    className={`px-2 py-1 text-right ${
                      ceBuild ? "text-long" : "text-slate-300"
                    }`}
                  >
                    {fmtOi(ce?.oi)}
                  </td>
                  <td
                    className={`px-2 py-1 text-right ${
                      (ce?.oi_change ?? 0) >= 0 ? "text-long" : "text-short"
                    }`}
                  >
                    {fmtSigned(ce?.oi_change)}
                  </td>
                  <td className="px-2 py-1 text-right text-slate-200">
                    {ce?.ltp?.toFixed(1) ?? "—"}
                  </td>
                  <td className="px-2 py-1 text-right text-slate-400">
                    {ce ? (ce.iv * 100).toFixed(1) : "—"}
                  </td>
                  <td
                    className={`px-2 py-1 text-center font-semibold ${
                      isAtm ? "text-accent" : "text-slate-100"
                    }`}
                  >
                    {strike}
                  </td>
                  <td className="px-2 py-1 text-right text-slate-400">
                    {pe ? (pe.iv * 100).toFixed(1) : "—"}
                  </td>
                  <td className="px-2 py-1 text-right text-slate-200">
                    {pe?.ltp?.toFixed(1) ?? "—"}
                  </td>
                  <td
                    className={`px-2 py-1 text-right ${
                      (pe?.oi_change ?? 0) >= 0 ? "text-long" : "text-short"
                    }`}
                  >
                    {fmtSigned(pe?.oi_change)}
                  </td>
                  <td
                    className={`px-2 py-1 text-right ${
                      peBuild ? "text-short" : "text-slate-300"
                    }`}
                  >
                    {fmtOi(pe?.oi)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function fmtOi(n?: number) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtSigned(n?: number) {
  if (n == null) return "—";
  const sign = n > 0 ? "+" : "";
  return sign + fmtOi(Math.abs(n));
}
