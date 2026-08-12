"use client";

import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";

// Workaround for framer-motion TypeScript typings mismatch in this project
const MotionDiv: any = motion.div;
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

type Mode = "register" | "login";

type Message = {
  type: "success" | "error";
  text: string;
};

export default function AuthForm() {
  const router = useRouter();
  const supabase = createClient();
  const [mode, setMode] = useState<Mode>("register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<Message | null>(null);

  function setCustomAuthCookie() {
    document.cookie = "custom_auth=1; path=/; max-age=86400";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage(null);

    if (!supabase) {
      setMessage({ type: "error", text: "Supabase credentials are not configured yet." });
      setLoading(false);
      return;
    }

    if (mode === "register") {
      const { error } = await supabase
        .from("my_users")
        .insert([{ name, email, password, created_at: new Date().toISOString() }]);

      if (error) {
        setMessage({ type: "error", text: error.message });
      } else {
        setCustomAuthCookie();
        setMessage({ type: "success", text: "Registration successful." });
        setName("");
        setEmail("");
        setPassword("");
        router.replace("/dashboard");
      }
    } else {
      const { data, error } = await supabase
        .from("my_users")
        .select("*")
        .eq("email", email)
        .maybeSingle();

      if (error) {
        setMessage({ type: "error", text: error.message });
      } else if (!data) {
        setMessage({ type: "error", text: "No account found with that email." });
      } else if (data.password === password) {
        setCustomAuthCookie();
        setMessage({ type: "success", text: "Login successful." });
        setPassword("");
        router.replace("/dashboard");
      } else {
        setMessage({ type: "error", text: "Invalid email or password." });
      }
    }

    setLoading(false);
  }

  return (
    <MotionDiv className="w-full max-w-xl rounded-[24px] border border-white/10 bg-slate-900/70 p-6 shadow-2xl backdrop-blur-xl">
      <div className="text-center">
        <p className="text-[10px] uppercase tracking-[0.35em] text-cyan-300/90">
          Custom Supabase Auth
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-white">
          {mode === "register" ? "Create your account" : "Welcome back"}
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Register or log in using the my_users table in Supabase.
        </p>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-2 rounded-2xl border border-white/10 bg-black/20 p-1">
        <button
          type="button"
          onClick={() => {
            setMode("register");
            setMessage(null);
          }}
          className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
            mode === "register"
              ? "bg-cyan-400 text-slate-950"
              : "text-slate-300 hover:bg-white/5"
          }`}
        >
          Register
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("login");
            setMessage(null);
          }}
          className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
            mode === "login"
              ? "bg-cyan-400 text-slate-950"
              : "text-slate-300 hover:bg-white/5"
          }`}
        >
          Login
        </button>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {mode === "register" && (
          <Field
            label="Name"
            type="text"
            value={name}
            onChange={setName}
            placeholder="Your name"
            autoComplete="name"
            required
          />
        )}

        <Field
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="you@email.com"
          autoComplete="email"
          required
        />

        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder="••••••••"
          autoComplete={mode === "register" ? "new-password" : "current-password"}
          required
        />

        {message && (
          <p
            className={`rounded-xl px-3 py-2 text-sm ${
              message.type === "success"
                ? "bg-emerald-500/10 text-emerald-300"
                : "bg-rose-500/10 text-rose-300"
            }`}
          >
            {message.text}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-gradient-to-r from-cyan-400 via-sky-400 to-violet-500 py-3 text-sm font-semibold text-slate-950 shadow-[0_0_25px_rgba(34,211,238,0.25)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Please wait…" : mode === "register" ? "Register" : "Login"}
        </button>
      </form>
    </MotionDiv>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
  required,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-[10px] uppercase tracking-[0.25em] text-slate-500">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={required}
        className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/40"
      />
    </label>
  );
}
