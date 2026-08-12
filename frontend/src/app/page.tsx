"use client";

import AuthForm from "@/components/AuthForm";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const metrics = [
  { label: "Historical Accuracy", value: "85%" },
  { label: "Live Signals", value: "< 80ms" },
  { label: "Risk Filters", value: "RR 1:2+" },
];

const features = [
  {
    title: "Real-Time Option Chain Analysis",
    description:
      "Monitor volatility, open interest, and premium decay with a live desk that surfaces high-conviction setups before the crowd reacts.",
    accent: "from-cyan-400/25 to-sky-600/5",
  },
  {
    title: "ML-Powered Trade Trajectory",
    description:
      "Receive entry, target, and stop-loss guidance backed by predictive modeling that adapts to real market momentum.",
    accent: "from-violet-400/25 to-fuchsia-600/5",
  },
  {
    title: "Strict Risk Management",
    description:
      "Only the highest-quality opportunities pass through our risk framework, so your capital is protected by design.",
    accent: "from-emerald-400/25 to-teal-600/5",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const storedTheme = window.localStorage.getItem("theme") as "dark" | "light" | null;
    const nextTheme = storedTheme ?? "dark";
    setTheme(nextTheme);
    document.documentElement.classList.toggle("light", nextTheme === "light");
    document.documentElement.classList.toggle("dark", nextTheme === "dark");
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("theme", theme);
  }, [theme]);

  const scrollToAuth = useCallback(() => {
    document.getElementById("auth-section")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, []);

  const handleLogout = () => {
    document.cookie = "custom_auth=; path=/; max-age=0";
    router.push("/");
  };

  const isDark = theme === "dark";

  return (
    <main className={`min-h-screen ${isDark ? "bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(168,85,247,0.16),_transparent_28%),linear-gradient(135deg,_#030712_0%,_#050816_45%,_#0f172a_100%)] text-slate-100" : "bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.15),_transparent_28%),linear-gradient(135deg,_#f8fbff_0%,_#eef6ff_45%,_#f8fafc_100%)] text-slate-900"}`}>
      <div className="mx-auto flex max-w-7xl flex-col px-6 py-6 sm:px-8 lg:px-12">
        <header className={`flex flex-wrap items-center justify-between gap-3 rounded-full border px-5 py-3 backdrop-blur-xl ${isDark ? "border-white/10 bg-slate-900/70" : "border-slate-300/70 bg-white/80"}`}>
          <div>
            <p className={`text-[10px] uppercase tracking-[0.35em] ${isDark ? "text-cyan-300/90" : "text-cyan-600"}`}>
              AetherFO
            </p>
            <p className={`text-sm ${isDark ? "text-slate-400" : "text-slate-600"}`}>
              Predictive F&O Intelligence
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${isDark ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-200 hover:bg-cyan-400/20" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"}`}
            >
              {isDark ? "☀️ Day Mode" : "🌙 Dark Mode"}
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${isDark ? "border-white/10 bg-white/5 text-slate-100 hover:bg-white/10" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"}`}
            >
              Logout
            </button>
            <a
              href="#auth-section"
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${isDark ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-200 hover:bg-cyan-400/20" : "border-cyan-400/30 bg-cyan-500/10 text-cyan-700 hover:bg-cyan-500/20"}`}
            >
              Open Desk
            </a>
          </div>
        </header>

        <section className="relative mt-8 overflow-hidden rounded-[32px] border border-white/10 bg-slate-950/70 p-8 shadow-[0_0_90px_rgba(34,211,238,0.16)] backdrop-blur-2xl sm:p-12 lg:p-16">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.22),_transparent_34%),radial-gradient(circle_at_bottom_right,_rgba(167,139,250,0.18),_transparent_34%)]" />
          <div className="relative grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-sm text-cyan-200">
                <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.9)]" />
                Live Market Signal Engine
              </div>
              <h1 className="mt-6 max-w-3xl text-4xl font-semibold leading-tight text-white sm:text-5xl lg:text-6xl">
                Dominate the F&O market with predictive analytics built for
                <span className="block bg-gradient-to-r from-cyan-300 via-sky-400 to-violet-400 bg-clip-text text-transparent">
                  high-probability setups.
                </span>
              </h1>
              <p className="mt-6 max-w-2xl text-lg text-slate-300 sm:text-xl">
                Move from reactive trading to a disciplined edge with real-time option chain analysis, ML-guided guidance, and strict risk filters that only let the smartest opportunities through.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={scrollToAuth}
                  className="rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-violet-500 px-6 py-3 text-sm font-semibold text-slate-950 shadow-[0_0_35px_rgba(34,211,238,0.35)] transition hover:brightness-110"
                >
                  Start Winning Today
                </button>
                <span className="text-sm text-slate-400">
                  Secure onboarding • Instant access to the live desk
                </span>
              </div>

              <div className="mt-8 grid gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur md:grid-cols-3">
                {metrics.map((item) => (
                  <div key={item.label} className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                    <p className="text-2xl font-semibold text-white">{item.value}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.25em] text-slate-400">
                      {item.label}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] border border-cyan-400/20 bg-slate-900/80 p-6 shadow-2xl">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                    Live Desk Snapshot
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-white">
                    Precision at every tick
                  </h2>
                </div>
                <div className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-sm text-emerald-300">
                  Online
                </div>
              </div>

              <div className="mt-6 space-y-3">
                {[
                  ["NIFTY 50", "+1.24%", "Momentum breakout"],
                  ["BANKNIFTY", "+0.86%", "Volatility compression"],
                  ["CE Premiums", "Cooling", "RR window improving"],
                ].map(([symbol, move, detail]) => (
                  <div key={symbol} className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3">
                    <div>
                      <p className="font-medium text-white">{symbol}</p>
                      <p className="text-sm text-slate-400">{detail}</p>
                    </div>
                    <span className="rounded-full bg-cyan-400/10 px-3 py-1 text-sm font-medium text-cyan-300">
                      {move}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-10 grid gap-6 lg:grid-cols-3">
          {features.map((feature) => (
            <article
              key={feature.title}
              className={`rounded-[24px] border border-white/10 bg-gradient-to-br ${feature.accent} p-[1px]`}
            >
              <div className="h-full rounded-[23px] bg-slate-950/90 p-6">
                <h3 className="text-xl font-semibold text-white">{feature.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-300">{feature.description}</p>
              </div>
            </article>
          ))}
        </section>

        <section
          id="auth-section"
          className="mt-12 rounded-[32px] border border-white/10 bg-slate-950/70 p-6 shadow-[0_0_70px_rgba(14,165,233,0.12)] backdrop-blur-2xl sm:p-8 lg:p-12"
        >
          <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
            <div>
              <p className="text-[10px] uppercase tracking-[0.35em] text-cyan-300/90">
                Secure Access
              </p>
              <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">
                Join the premium desk and unlock your edge.
              </h2>
              <p className="mt-4 max-w-xl text-lg text-slate-300">
                Sign in with Google or create a password-protected account to access your dashboard and trade intelligence.
              </p>
              <div className="mt-6 space-y-3 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400" />
                  Zero-friction onboarding for new traders
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400" />
                  Supabase-backed authentication and profile storage
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400" />
                  Protected access to your personalized dashboard
                </div>
              </div>
            </div>

            <AuthForm />
          </div>
        </section>
      </div>
    </main>
  );
}
