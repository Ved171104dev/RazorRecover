"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Brand } from "@/components/brand";
export function AuthForm({ kind }: { kind: "login" | "signup" | "forgot" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [waking, setWaking] = useState(false);
  const [done, setDone] = useState("");
  const [email, setEmail] = useState("");
  const [remember, setRemember] = useState(true);
  const [online, setOnline] = useState(true);
  useEffect(() => {
    if (kind === "login") setEmail(window.localStorage.getItem("rr_login_email") || "");
    const updateOnline = () => setOnline(window.navigator.onLine);
    updateOnline();
    window.addEventListener("online", updateOnline);
    window.addEventListener("offline", updateOnline);
    return () => {
      window.removeEventListener("online", updateOnline);
      window.removeEventListener("offline", updateOnline);
    };
  }, [kind]);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!window.navigator.onLine) {
      setError("You are offline. Your account is safe; reconnect to sign in.");
      return;
    }
    setBusy(true);
    const wakingTimer = window.setTimeout(() => setWaking(true), 2500);
    setError("");
    const fd = new FormData(e.currentTarget);
    const body: Record<string, FormDataEntryValue | boolean> = Object.fromEntries(fd.entries());
    if (typeof body.email === "string")
      body.email = body.email.trim().toLowerCase();
    if (kind === "login") body.remember_me = remember;
    try {
      const path =
        kind === "forgot" ? "/api/auth/forgot-password" : "/api/auth/" + kind;
      const result = await api<any>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (kind === "forgot") setDone(result.message);
      else {
        if (kind === "login") {
          if (remember) window.localStorage.setItem("rr_login_email", String(body.email));
          else window.localStorage.removeItem("rr_login_email");
        }
        router.replace("/dashboard");
      }
    } catch (x) {
      setError(x instanceof Error ? x.message : "Request failed");
    } finally {
      window.clearTimeout(wakingTimer);
      setWaking(false);
      setBusy(false);
    }
  }
  return (
    <div className="auth">
      <div className="card authCard">
        <Link href="/" className="brand" style={{ textDecoration: "none" }}>
          <Brand />
        </Link>
        <div className="eyebrow" style={{ marginTop: 28 }}>
          {kind === "login"
            ? "Secure merchant access"
            : kind === "signup"
              ? "Create merchant workspace"
              : "Account recovery"}
        </div>
        <h1>
          {kind === "login"
            ? "Welcome back"
            : kind === "signup"
              ? "Start recovering revenue"
              : "Reset password"}
        </h1>
        <p className="muted">
          {kind === "login"
            ? "Sign in to your protected recovery command center."
            : kind === "signup"
              ? "Your merchant workspace starts empty. Connect Razorpay or import payment history after signup."
              : "We return the same response whether or not an account exists."}
        </p>
        <form className="form" onSubmit={submit}>
          {kind === "signup" && (
            <>
              <Field name="name" label="Your name" />
              <Field name="merchant_name" label="Merchant name" />
            </>
          )}
          <Field
            name="email"
            label="Email address"
            type="email"
            placeholder="yourname@gmail.com"
            hint="Use a valid Gmail or business email address."
            value={email}
            onChange={setEmail}
          />
          {kind !== "forgot" && (
            <Field
              name="password"
              label="Password"
              type="password"
              autoComplete={
                kind === "signup" ? "new-password" : "current-password"
              }
            />
          )}
          {kind === "login" && (
            <label className="rememberRow">
              <input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />
              <span><strong>Keep me signed in</strong><small>Remember this account on this device for 30 days.</small></span>
            </label>
          )}
          {!online && <div className="notice">You are offline. Your saved account is not lost; reconnect to continue.</div>}
          {error && <div className="error">{error}</div>}
          {done && <div className="notice">{done}</div>}
          <button className="btn" disabled={busy || !online}>
            {busy
              ? waking ? "WAKING SECURE SERVICE…" : "SIGNING IN…"
              : kind === "login"
                ? "LOGIN"
                : kind === "signup"
                  ? "CREATE ACCOUNT"
                  : "SEND INSTRUCTIONS"}
          </button>
        </form>
        <p className="metricSub" style={{ marginTop: 18 }}>
          {kind === "login" ? (
            <>
              New here? <Link href="/signup">Create an account</Link> ·{" "}
              <Link href="/forgot-password">Forgot password?</Link>
            </>
          ) : kind === "signup" ? (
            <>
              Already registered? <Link href="/login">Login</Link>
            </>
          ) : (
            <Link href="/login">Back to login</Link>
          )}
        </p>
      </div>
    </div>
  );
}
function Field({
  name,
  label,
  type = "text",
  placeholder,
  hint,
  autoComplete,
  value,
  onChange,
}: {
  name: string;
  label: string;
  type?: string;
  placeholder?: string;
  hint?: string;
  autoComplete?: string;
  value?: string;
  onChange?: (value: string) => void;
}) {
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <input
        className="input"
        id={name}
        name={name}
        type={type}
        placeholder={placeholder}
        autoComplete={autoComplete || (name === "email" ? "email" : "off")}
        inputMode={type === "email" ? "email" : undefined}
        spellCheck={type === "email" ? false : undefined}
        value={value}
        onChange={onChange ? (event) => onChange(event.target.value) : undefined}
        required
        minLength={type === "password" ? 10 : 2}
      />
      {hint && <div className="metricSub">{hint}</div>}
    </div>
  );
}
