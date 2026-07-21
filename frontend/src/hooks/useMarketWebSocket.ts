"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ChainMetrics,
  OptionContract,
  PredictionOverlay,
  Signal,
  StreamPayload,
  Candle,
} from "@/types/market";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/market";
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface MarketState {
  connected: boolean;
  spot: number;
  underlying: string;
  instrumentName: string;
  candles: Candle[];
  chain: OptionContract[];
  metrics: ChainMetrics | null;
  prediction: PredictionOverlay | null;
  signals: Signal[];
  lastTs: number;
  switching: boolean;
}

const initial: MarketState = {
  connected: false,
  spot: 0,
  underlying: "NIFTY",
  instrumentName: "Nifty 50",
  candles: [],
  chain: [],
  metrics: null,
  prediction: null,
  signals: [],
  lastTs: 0,
  switching: false,
};

function decodePayload(data: ArrayBuffer | Blob | string): Promise<StreamPayload> {
  if (typeof data === "string") {
    return Promise.resolve(JSON.parse(data) as StreamPayload);
  }
  if (data instanceof Blob) {
    return data.arrayBuffer().then((buf) => {
      const text = new TextDecoder().decode(buf);
      return JSON.parse(text) as StreamPayload;
    });
  }
  const text = new TextDecoder().decode(data);
  return Promise.resolve(JSON.parse(text) as StreamPayload);
}

export function useMarketWebSocket() {
  const [state, setState] = useState<MarketState>(initial);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const alive = useRef(true);

  const apply = useCallback((msg: StreamPayload) => {
    setState((prev) => {
      const next: MarketState = {
        ...prev,
        connected: true,
        spot: msg.spot || prev.spot,
        underlying: msg.underlying || prev.underlying,
        lastTs: msg.ts || prev.lastTs,
        switching: msg.type === "symbol_switch" ? false : prev.switching,
      };

      if (msg.instrument?.name) {
        next.instrumentName = msg.instrument.name;
      }

      if (msg.type === "symbol_switch") {
        next.candles = msg.candles?.length ? msg.candles : [];
        next.chain = [];
        next.metrics = null;
        next.prediction = null;
        next.signals = [];
        return next;
      }

      if (msg.candles && msg.candles.length) {
        next.candles = msg.candles;
      } else if (msg.candle) {
        const copy = [...prev.candles];
        const last = copy[copy.length - 1];
        if (last && last.time === msg.candle.time) {
          copy[copy.length - 1] = msg.candle;
        } else {
          copy.push(msg.candle);
          if (copy.length > 300) copy.shift();
        }
        next.candles = copy;
      }

      if (msg.chain && msg.chain.length) next.chain = msg.chain;
      if (msg.metrics) next.metrics = msg.metrics;
      if (msg.prediction) next.prediction = msg.prediction;

      if (msg.signal) {
        const exists = prev.signals.some((s) => s.id === msg.signal!.id);
        if (!exists) {
          next.signals = [msg.signal, ...prev.signals].slice(0, 40);
        } else {
          next.signals = prev.signals.map((s) =>
            s.id === msg.signal!.id ? msg.signal! : s
          );
        }
      }

      return next;
    });
  }, []);

  useEffect(() => {
    alive.current = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (!alive.current) return;
      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setState((p) => ({ ...p, connected: true }));
      };

      ws.onmessage = async (ev) => {
        try {
          const msg = await decodePayload(ev.data);
          apply(msg);
        } catch {
          /* ignore malformed */
        }
      };

      ws.onclose = () => {
        setState((p) => ({ ...p, connected: false }));
        const delay = Math.min(8_000, 500 * 2 ** retryRef.current);
        retryRef.current += 1;
        timer = setTimeout(connect, delay);
      };

      ws.onerror = () => ws.close();
    };

    connect();
    const ping = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 20_000);

    return () => {
      alive.current = false;
      clearInterval(ping);
      if (timer) clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [apply]);

  const selectSymbol = useCallback(async (symbol: string) => {
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;
    setState((p) => ({ ...p, switching: true }));

    // Prefer REST so switch works even if WS is mid-reconnect
    try {
      const res = await fetch(`${API_URL}/api/instruments/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: sym }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Symbol not found");
      }
      const data = await res.json();
      setState((p) => ({
        ...p,
        underlying: data.instrument?.symbol ?? sym,
        instrumentName: data.instrument?.name ?? sym,
        spot: data.instrument?.spot ?? p.spot,
        candles: [],
        chain: [],
        metrics: null,
        prediction: null,
        signals: [],
        switching: false,
      }));
    } catch (e) {
      // Fallback: WS subscribe command
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "subscribe", symbol: sym }));
      } else {
        setState((p) => ({ ...p, switching: false }));
        console.error(e);
      }
    }
  }, []);

  return { ...state, selectSymbol };
}
