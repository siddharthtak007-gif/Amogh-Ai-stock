"use client";

import { useMarketWebSocket } from "@/hooks/useMarketWebSocket";
import LiveChartComponent from "@/components/LiveChartComponent";
import OptionChainTable from "@/components/OptionChainTable";
import SignalFeed from "@/components/SignalFeed";
import SymbolSearch from "@/components/SymbolSearch";
import LiveTradePlan from "@/components/LiveTradePlan";

export default function Dashboard() {
  const {
    connected,
    spot,
    underlying,
    instrumentName,
    candles,
    chain,
    metrics,
    prediction,
    signals,
    lastTs,
    switching,
    selectSymbol,
  } = useMarketWebSocket();

  const confPct = prediction ? (prediction.confidence * 100).toFixed(0) : "—";
  const ageMs = lastTs ? Date.now() - lastTs * 1000 : 0;

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_#152033_0%,_#0a0e14_55%)] text-slate-100">
      <header className="border-b border-surface-border px-4 py-4 md:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-display text-2xl font-semibold tracking-tight text-white md:text-3xl">
              Aether<span className="text-accent">FO</span>
            </p>
            <p className="mt-1 max-w-md font-mono text-xs text-slate-400">
              Search any F&O name → live chain + AI prediction (entry / SL / target).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4 font-mono text-sm">
            <StatusDot
              on={connected && !switching}
              label={switching ? "SWITCHING" : connected ? "LIVE" : "RECONNECTING"}
            />
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-500">
                {underlying} · {instrumentName}
              </p>
              <p className="text-xl font-semibold tabular-nums text-white">
                {spot
                  ? spot.toLocaleString("en-IN", { maximumFractionDigits: 2 })
                  : "—"}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-500">
                Confidence
              </p>
              <p
                className={`text-xl font-semibold tabular-nums ${
                  prediction?.side === "BUY"
                    ? "text-long"
                    : prediction?.side === "SELL"
                      ? "text-short"
                      : "text-slate-300"
                }`}
              >
                {confPct}%
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-500">
                Latency
              </p>
              <p className="text-xl font-semibold tabular-nums text-slate-300">
                {lastTs ? `${Math.max(0, ageMs)}ms` : "—"}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <SymbolSearch
            activeSymbol={underlying}
            onSelect={selectSymbol}
            disabled={switching}
          />
        </div>
      </header>

      <main className="grid gap-3 p-3 md:grid-cols-12 md:p-4">
        <section className="md:col-span-9 space-y-3">
          <LiveTradePlan
            prediction={prediction}
            underlying={underlying}
            spot={spot}
          />
          <LiveChartComponent
            candles={candles}
            prediction={prediction}
            height={420}
          />
          <div className="h-[340px]">
            <OptionChainTable chain={chain} metrics={metrics} spot={spot} />
          </div>
        </section>

        <aside className="md:col-span-3 flex flex-col gap-3">
          <MetricsPanel
            metrics={metrics}
            prediction={prediction}
            underlying={underlying}
          />
          <div className="min-h-[420px] flex-1">
            <SignalFeed signals={signals} />
          </div>
        </aside>
      </main>
    </div>
  );
}

function StatusDot({ on, label }: { on: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-sm border border-surface-border bg-surface px-3 py-2">
      <span
        className={`h-2 w-2 rounded-full ${
          on ? "bg-long shadow-[0_0_8px_#22c55e]" : "bg-short"
        }`}
      />
      <span className="text-[11px] tracking-wider text-slate-300">{label}</span>
    </div>
  );
}

function MetricsPanel({
  metrics,
  prediction,
  underlying,
}: {
  metrics: ReturnType<typeof useMarketWebSocket>["metrics"];
  prediction: ReturnType<typeof useMarketWebSocket>["prediction"];
  underlying: string;
}) {
  return (
    <div className="rounded-sm border border-surface-border bg-surface p-3 font-mono text-[11px]">
      <p className="mb-2 uppercase tracking-widest text-slate-300">
        Desk Metrics · {underlying}
      </p>
      <dl className="grid grid-cols-2 gap-2 text-slate-400">
        <div>
          <dt>PCR OI</dt>
          <dd className="text-base text-slate-100">
            {metrics?.pcr_oi?.toFixed(2) ?? "—"}
          </dd>
        </div>
        <div>
          <dt>Max Pain</dt>
          <dd className="text-base text-slate-100">
            {metrics?.max_pain ?? "—"}
          </dd>
        </div>
        <div>
          <dt>VWAP</dt>
          <dd className="text-base text-slate-100">
            {metrics?.vwap?.toFixed(1) ?? "—"}
          </dd>
        </div>
        <div>
          <dt>ATM IV</dt>
          <dd className="text-base text-slate-100">
            {metrics ? `${(metrics.atm_iv * 100).toFixed(1)}%` : "—"}
          </dd>
        </div>
      </dl>

      {prediction?.active && (
        <div className="mt-3 border-t border-surface-border pt-3">
          <p className="mb-1 text-slate-300">Active Plan</p>
          <ul className="space-y-0.5 text-slate-200">
            <li>
              <span className="text-slate-500">Side </span>
              {prediction.side}
            </li>
            <li>
              <span className="text-slate-500">Entry </span>
              {prediction.entry?.toFixed(1)}
            </li>
            <li className="text-short">
              <span className="text-slate-500">SL </span>
              {prediction.stop_loss?.toFixed(1)}
            </li>
            <li className="text-long">
              <span className="text-slate-500">Target </span>
              {prediction.target?.toFixed(1)}
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
