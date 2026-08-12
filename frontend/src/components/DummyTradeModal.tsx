"use client";

import { useEffect, useState } from "react";

export type DummyTradeModalProps = {
  open: boolean;
  onComplete: () => void;
};

export default function DummyTradeModal({ open, onComplete }: DummyTradeModalProps) {
  const [state, setState] = useState<"pending" | "executing" | "success">("pending");

  useEffect(() => {
    if (!open) {
      setState("pending");
    }
  }, [open]);

  if (!open) return null;

  const handleExecute = () => {
    setState("executing");
    window.setTimeout(() => {
      setState("success");
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-[12000] flex items-center justify-center bg-slate-950/70 px-4 backdrop-blur-md">
      <div className="relative w-full max-w-lg overflow-hidden rounded-[28px] border border-cyan-400/20 bg-slate-900/90 shadow-[0_0_80px_rgba(34,211,238,0.2)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.22),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(168,85,247,0.22),_transparent_30%)]" />

        <div className="relative p-6 sm:p-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.35em] text-cyan-300/90">
                Paper Trade
              </p>
              <h3 className="mt-2 text-2xl font-semibold text-white">
                🚨 Live Prediction Detected!
              </h3>
            </div>
            <div className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-sm text-emerald-300">
              Demo Mode
            </div>
          </div>

          <div className="mt-6 rounded-[24px] border border-white/10 bg-slate-950/70 p-5">
            <div className="flex items-center justify-between text-sm text-slate-400">
              <span>Instrument</span>
              <span className="font-semibold text-white">Nifty 24,000 CE</span>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {[
                ["Entry", "₹100"],
                ["Target", "₹130"],
                ["SL", "₹80"],
                ["Probability", "88%"],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-slate-900/70 p-3">
                  <p className="text-[10px] uppercase tracking-[0.25em] text-slate-500">{label}</p>
                  <p className="mt-1 text-lg font-semibold text-white">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {state === "pending" && (
            <button
              type="button"
              onClick={handleExecute}
              className="mt-6 w-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-violet-500 px-4 py-3 text-sm font-semibold text-slate-950 shadow-[0_0_35px_rgba(34,211,238,0.35)] transition hover:brightness-110"
            >
              Execute Paper Trade
            </button>
          )}

          {state === "executing" && (
            <div className="mt-6 flex flex-col items-center justify-center rounded-[24px] border border-cyan-400/20 bg-cyan-400/10 p-8 text-center">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-cyan-300 border-t-transparent" />
              <p className="mt-4 text-sm font-medium text-cyan-100">Simulating execution…</p>
            </div>
          )}

          {state === "success" && (
            <div className="mt-6 rounded-[24px] border border-emerald-400/20 bg-emerald-400/10 p-6 text-center">
              <div className="text-5xl">🎉</div>
              <p className="mt-3 text-2xl font-semibold text-white">+₹1,500 paper profit</p>
              <p className="mt-2 text-sm text-emerald-100">The simulated trade completed successfully.</p>
              <button
                type="button"
                onClick={onComplete}
                className="mt-5 rounded-full border border-emerald-400/30 bg-emerald-400/20 px-4 py-2 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/30"
              >
                Finish Tour
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
