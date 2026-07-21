"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type IPriceLine,
  type CandlestickData,
  type Time,
  ColorType,
  CrosshairMode,
} from "lightweight-charts";
import type { Candle, PredictionOverlay, Side } from "@/types/market";

interface Props {
  candles: Candle[];
  prediction: PredictionOverlay | null;
  height?: number;
}

function toCandle(c: Candle): CandlestickData {
  return {
    time: c.time as Time,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  };
}

/**
 * LiveChartComponent — Actual OHLCV candlesticks + ML overlay
 * (entry / SL / target / trailing SL price lines + buy/sell markers).
 */
export default function LiveChartComponent({
  candles,
  prediction,
  height = 480,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const linesRef = useRef<IPriceLine[]>([]);
  const lastMarkerSide = useRef<Side | null>(null);
  const lastMarkerTime = useRef<Time | null>(null);

  // Init chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#0c1219" },
        textColor: "#9db0c7",
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
      },
      grid: {
        vertLines: { color: "#15202e" },
        horzLines: { color: "#15202e" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#1e2a3a" },
      timeScale: {
        borderColor: "#1e2a3a",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const series = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const ro = new ResizeObserver(() => {
      if (!containerRef.current) return;
      chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  // Sync candle data
  useEffect(() => {
    const series = seriesRef.current;
    if (!series || candles.length === 0) return;

    const data = candles.map(toCandle);
    series.setData(data);
    chartRef.current?.timeScale().scrollToRealTime();
  }, [candles]);

  // Overlay prediction lines + markers
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    // Clear previous lines
    for (const line of linesRef.current) {
      series.removePriceLine(line);
    }
    linesRef.current = [];

    if (!prediction?.active) {
      series.setMarkers([]);
      lastMarkerSide.current = null;
      return;
    }

    const addLine = (
      price: number | null | undefined,
      color: string,
      title: string,
      style: 0 | 1 | 2 | 3 | 4 = 2
    ) => {
      if (price == null) return;
      const line = series.createPriceLine({
        price,
        color,
        lineWidth: 2,
        lineStyle: style,
        axisLabelVisible: true,
        title,
      });
      linesRef.current.push(line);
    };

    addLine(prediction.entry, "#3d9cf0", "ENTRY", 0);
    addLine(prediction.stop_loss, "#ef4444", "SL", 2);
    addLine(prediction.target, "#22c55e", "T1", 2);
    addLine(prediction.target_2, "#16a34a", "T2", 3);
    addLine(prediction.target_3, "#15803d", "T3", 4);
    addLine(prediction.trailing_sl, "#eab308", "TRAIL", 3);

    // Predicted trajectory levels (fainter)
    prediction.predicted_levels?.forEach((lvl, i) => {
      addLine(lvl, "#7c8ea3", `P${i + 1}`, 4);
    });

    const last = candles[candles.length - 1];
    if (
      last &&
      prediction.side !== "FLAT" &&
      (lastMarkerSide.current !== prediction.side ||
        lastMarkerTime.current !== (last.time as Time))
    ) {
      const isBuy = prediction.side === "BUY";
      series.setMarkers([
        {
          time: last.time as Time,
          position: isBuy ? "belowBar" : "aboveBar",
          color: isBuy ? "#22c55e" : "#ef4444",
          shape: isBuy ? "arrowUp" : "arrowDown",
          text: `${prediction.side} ${(prediction.confidence * 100).toFixed(0)}%`,
        },
      ]);
      lastMarkerSide.current = prediction.side;
      lastMarkerTime.current = last.time as Time;
    }
  }, [prediction, candles]);

  return (
    <div className="relative w-full overflow-hidden rounded-sm border border-surface-border bg-surface">
      <div className="flex items-center justify-between border-b border-surface-border px-3 py-2">
        <span className="font-mono text-xs uppercase tracking-widest text-slate-400">
          Live Price + AI Overlay
        </span>
        {prediction?.active && (
          <span
            className={`font-mono text-xs ${
              prediction.side === "BUY" ? "text-long" : "text-short"
            }`}
          >
            {prediction.side} · RR{" "}
            {prediction.rr_ratio?.toFixed(2) ?? "—"} ·{" "}
            {(prediction.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <div ref={containerRef} style={{ height }} className="w-full" />
    </div>
  );
}
