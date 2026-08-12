"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Joyride, type Step } from "react-joyride";
import { createClient } from "@/lib/supabase/client";

type OnboardingTourProps = {
  buttonClassName?: string;
  children?: ReactNode;
};

const steps: Step[] = [
  {
    target: "#tour-search",
    title: "Search & Select",
    content:
      "Search for Nifty or BankNifty strikes and jump straight into a live market view with a single click.",
    placement: "bottom",
  },
  {
    target: "#tour-chart",
    title: "Dual-Plot Chart",
    content:
      "Watch the live price action and the AI prediction overlay side by side to understand momentum and structure.",
    placement: "top",
  },
  {
    target: "#tour-signals",
    title: "High-Probability Signals",
    content:
      "Read the Entry, Target, Stop-Loss, and Confidence score to evaluate whether the setup deserves your attention.",
    placement: "left",
  },
  {
    target: "#tour-chain",
    title: "Live Greeks Data",
    content:
      "Inspect open interest and premium movement in the option chain to validate whether the market is aligning with the signal.",
    placement: "top",
  },
  {
    target: "#tour-execution",
    title: "Take Action",
    content:
      "Use this prediction as your decision framework before placing a trade, combining market context with disciplined risk management.",
    placement: "bottom",
  },
];

const joyrideStyles = {
  options: {
    arrowColor: "#0f172a",
    backgroundColor: "#0f172a",
    overlayColor: "rgba(2, 6, 23, 0.78)",
    primaryColor: "#22d3ee",
    textColor: "#e2e8f0",
    zIndex: 10000,
    beaconSize: 48,
  },
  tooltip: {
    borderRadius: "18px",
    border: "1px solid rgba(34, 211, 238, 0.22)",
    boxShadow: "0 20px 60px rgba(2, 6, 23, 0.65)",
  },
  buttonBack: {
    color: "#e2e8f0",
    borderRadius: "999px",
    border: "1px solid rgba(255,255,255,0.16)",
  },
  buttonNext: {
    backgroundColor: "#22d3ee",
    borderRadius: "999px",
    color: "#020617",
  },
  buttonSkip: {
    color: "#94a3b8",
  },
};

export default function OnboardingTour({ buttonClassName, children }: OnboardingTourProps) {
  const [run, setRun] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [hasSeenTour, setHasSeenTour] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;

    async function initTour() {
      const supabase = createClient();
      if (!supabase) {
        if (active) {
          setLoading(false);
        }
        return;
      }

      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!active) return;

      if (user?.id) {
        setUserId(user.id);
        const { data, error } = await supabase
          .from("users")
          .select("has_seen_tour")
          .eq("id", user.id)
          .maybeSingle();

        if (!active) return;

        if (!error) {
          const seen = Boolean(data?.has_seen_tour);
          setHasSeenTour(seen);
          if (!seen) {
            setRun(true);
          }
        }
      }

      if (active) {
        setLoading(false);
      }
    }

    void initTour();

    return () => {
      active = false;
    };
  }, []);

  const markTourAsSeen = async () => {
    const supabase = createClient();
    if (!supabase || !userId) return;

    const { error } = await supabase.from("users").update({ has_seen_tour: true }).eq("id", userId);

    if (!error) {
      setHasSeenTour(true);
    }
  };

  const handleTourFinish = async () => {
    setRun(false);
    await markTourAsSeen();
  };

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setRun(true);
        }}
        disabled={loading}
        className={
          buttonClassName ||
          "rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-400/20"
        }
      >
        {loading ? "Loading…" : hasSeenTour ? "Replay Guide" : "Setup Guide"}
      </button>

      <Joyride
        run={run}
        steps={steps}
        continuous
        styles={joyrideStyles}
        locale={{ back: "Back", close: "Close", last: "Finish", next: "Next", skip: "Skip" }}
        // @ts-expect-error - `react-joyride` types (v3) may not include `callback` prop
        callback={({ status }) => {
          if (status === "finished" || status === "skipped") {
            void handleTourFinish();
          }
        }}
      />

      {children}
    </>
  );
}
