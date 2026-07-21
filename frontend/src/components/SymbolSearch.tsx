"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface InstrumentHit {
  symbol: string;
  name: string;
  segment: string;
  base_spot: number;
  lot_size: number;
  exchange: string;
}

interface Props {
  activeSymbol: string;
  onSelect: (symbol: string) => void;
  disabled?: boolean;
}

const API =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function SymbolSearch({ activeSymbol, onSelect, disabled }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<InstrumentHit[]>([]);
  const boxRef = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchHits = useCallback(async (q: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/instruments?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setResults(data.results ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHits("");
  }, [fetchHits]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const onChange = (value: string) => {
    setQuery(value);
    setOpen(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => fetchHits(value), 180);
  };

  const pick = (sym: string) => {
    setQuery("");
    setOpen(false);
    onSelect(sym);
  };

  return (
    <div ref={boxRef} className="relative w-full max-w-md">
      <label className="mb-1 block font-mono text-[10px] uppercase tracking-widest text-slate-500">
        Search symbol / company → get prediction
      </label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            value={query}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setOpen(true)}
            disabled={disabled}
            placeholder="Type NIFTY, BANKNIFTY, RELIANCE, TCS…"
            className="w-full border border-surface-border bg-surface px-3 py-2.5 font-mono text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-accent"
          />
          {open && (
            <ul className="absolute z-50 mt-1 max-h-72 w-full overflow-auto border border-surface-border bg-surface-raised shadow-xl">
              {loading && (
                <li className="px-3 py-2 font-mono text-xs text-slate-500">Searching…</li>
              )}
              {!loading && results.length === 0 && (
                <li className="px-3 py-2 font-mono text-xs text-slate-500">
                  No match — try NIFTY / RELIANCE
                </li>
              )}
              {results.map((r) => (
                <li key={r.symbol}>
                  <button
                    type="button"
                    onClick={() => pick(r.symbol)}
                    className={`flex w-full items-center justify-between px-3 py-2 text-left font-mono text-xs hover:bg-accent/15 ${
                      r.symbol === activeSymbol ? "bg-accent/10 text-accent" : "text-slate-200"
                    }`}
                  >
                    <span>
                      <span className="font-semibold">{r.symbol}</span>
                      <span className="ml-2 text-slate-500">{r.name}</span>
                    </span>
                    <span className="text-[10px] uppercase text-slate-500">
                      {r.segment} · lot {r.lot_size}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex items-center border border-surface-border bg-surface px-3 font-mono text-sm text-accent">
          {activeSymbol}
        </div>
      </div>
      <p className="mt-1 font-mono text-[10px] text-slate-600">
        Select a name → live chart, option chain & AI prediction switch instantly
      </p>
    </div>
  );
}
