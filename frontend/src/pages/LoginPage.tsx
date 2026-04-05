import { AlertCircle, LockKeyhole, Mail } from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from = (location.state as { from?: string } | null)?.from ?? "/";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (submissionError) {
      setError(
        submissionError instanceof Error ? submissionError.message : "Unable to sign in right now.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(245,158,11,0.2),_transparent_30%),linear-gradient(180deg,_#020617_0%,_#0f172a_50%,_#111827_100%)] px-4 py-10 text-slate-100">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[minmax(0,1.1fr)_480px]">
        <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-8 shadow-2xl shadow-black/20">
          <p className="text-xs uppercase tracking-[0.3em] text-amber-200/70">Amazon Seller Ops</p>
          <h1 className="mt-5 max-w-xl text-4xl font-semibold leading-tight text-white">
            Secure admin access for inventory, listing, and A+ workflows.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300">
            Sign in to access the seller operations dashboard, inventory workflows, listing controls,
            Slack-connected notifications, and Amazon A+ content tools.
          </p>
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-8 shadow-2xl shadow-black/30 backdrop-blur">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.26em] text-slate-500">Admin login</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">Sign in</h2>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Email</span>
              <div className="flex items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3">
                <Mail className="h-4 w-4 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                  placeholder="Enter your admin email"
                  autoComplete="email"
                />
              </div>
            </label>

            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Password</span>
              <div className="flex items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3">
                <LockKeyhole className="h-4 w-4 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                />
              </div>
            </label>

            {error ? (
              <div className="flex items-start gap-3 rounded-[1.25rem] border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-[1.25rem] bg-amber-300 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isSubmitting ? "Signing in..." : "Sign in to dashboard"}
            </button>
          </form>

          <div className="mt-6 rounded-[1.25rem] border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
            Use the admin account configured for your environment. For local development, set the
            credentials in <code className="font-mono text-xs text-slate-300">.env</code>.
          </div>
        </section>
      </div>
    </div>
  );
}
