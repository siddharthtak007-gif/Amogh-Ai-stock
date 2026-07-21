export type Side = "BUY" | "SELL" | "FLAT";

export interface Greeks {
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  rho: number;
  iv: number;
}

export interface OptionContract {
  strike: number;
  option_type: "CE" | "PE";
  ltp: number;
  bid: number;
  ask: number;
  oi: number;
  oi_change: number;
  volume: number;
  iv: number;
  greeks?: Greeks | null;
}

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Signal {
  id: string;
  timestamp: number;
  underlying: string;
  side: Side;
  entry: number;
  stop_loss: number;
  target: number;
  target_2?: number | null;
  target_3?: number | null;
  trailing_sl?: number | null;
  confidence: number;
  rr_ratio: number;
  reason: string;
  predicted_levels: number[];
  discarded: boolean;
  discard_reason?: string | null;
  option_type?: "CE" | "PE" | null;
  option_strike?: number | null;
  option_entry?: number | null;
  option_sl?: number | null;
  option_target?: number | null;
  action_text?: string;
  exit_text?: string;
  direction_bias?: string;
}

export interface ChainMetrics {
  pcr_oi: number;
  pcr_volume: number;
  max_pain: number;
  vwap: number;
  spot: number;
  atm_iv: number;
  oi_buildup_strikes: number[];
  volume_breakout: boolean;
}

export interface PredictionOverlay {
  confidence: number;
  side: Side;
  entry: number | null;
  stop_loss: number | null;
  target: number | null;
  target_2?: number | null;
  target_3?: number | null;
  trailing_sl: number | null;
  predicted_levels: number[];
  active: boolean;
  rr_ratio?: number;
  direction_bias?: string;
  score?: number;
  headline?: string;
  spot_line?: string;
  action_text?: string;
  exit_text?: string;
  option_type?: "CE" | "PE" | null;
  option_strike?: number | null;
  option_ltp?: number | null;
  option_entry?: number | null;
  option_sl?: number | null;
  option_target?: number | null;
  option_target_2?: number | null;
  reason?: string;
  discarded?: boolean;
  discard_reason?: string | null;
}

export interface StreamPayload {
  type: "tick" | "candle" | "signal" | "chain" | "heartbeat" | "symbol_switch";
  ts: number;
  underlying: string;
  spot: number;
  candle?: Candle | null;
  candles?: Candle[];
  signal?: Signal | null;
  prediction?: PredictionOverlay | null;
  chain?: OptionContract[];
  metrics?: ChainMetrics | null;
  instrument?: {
    symbol: string;
    name: string;
    segment?: string;
    lot_size?: number;
    spot?: number;
  } | null;
}
