"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { Brand } from "@/components/brand";
export function AuthForm({ kind }: { kind: "login" | "signup" | "forgot" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const fd = new FormData(e.currentTarget);
    const body = Object.fromEntries(fd.entries());
    if (typeof body.email === "string")
      body.email = body.email.trim().toLowerCase();
    try {
      const path =
        kind === "forgot" ? "/api/auth/forgot-password" : "/api/auth/" + kind;
      const result = await api<any>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (kind === "forgot") setDone(result.message);
      else router.replace("/dashboard");
    } catch (x) {
      setError(x instanceof Error ? x.message : "Request failed");
    } finally {
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
          {error && <div className="error">{error}</div>}
          {done && <div className="notice">{done}</div>}
          <button className="btn" disabled={busy}>
            {busy
              ? "PLEASE WAIT…"
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
}: {
  name: string;
  label: string;
  type?: string;
  placeholder?: string;
  hint?: string;
  autoComplete?: string;
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
        required
        minLength={type === "password" ? 10 : 2}
      />
      {hint && <div className="metricSub">{hint}</div>}
    </div>
  );
}
