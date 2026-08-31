"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, inr, label } from "@/lib/api";

const causeColors = ["#e3ad49", "#c89447", "#a97c42", "#876438", "#665031"];

function compactInr(valuePaise: number) {
  const rupees = valuePaise / 100;
  if (rupees >= 100000) {
    const lakhs = rupees / 100000;
    return `₹${lakhs >= 10 ? Math.round(lakhs) : lakhs.toFixed(1)}L`;
  }
  if (rupees >= 1000) return `₹${Math.round(rupees / 1000)}K`;
  return `₹${Math.round(rupees)}`;
}
const nav = [
  "dashboard",
  "risk",
  "decisions",
  "actions",
  "experiments",
  "audit",
  "assistant",
  "data-sources",
  "settings",
];
function useLoad<T>(path: string) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const load = () =>
    api<T>(path)
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void load();
  }, [path]);
  return { data, error, load };
}
function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter(),
    pathname = usePathname();
  const { data: user } = useLoad<any>("/api/auth/me");
  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    router.replace("/login");
  }
  return (
    <main className="shell">
      <nav className="nav">
        <Link
          href="/dashboard"
          className="brand"
          style={{ textDecoration: "none" }}
        >
          RAZOR<span>RECOVER</span>
        </Link>
        <div className="navlinks">
          {nav.map((x) => (
            <Link
              key={x}
              href={"/" + x}
              className={pathname.startsWith("/" + x) ? "active" : undefined}
            >
              {label(x)}
            </Link>
          ))}
        </div>
        <div className="user">
          <div className="avatar">{user?.user.name?.[0] || "M"}</div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700 }}>
              {user?.merchant.name || "Merchant"}
            </div>
            <div className="muted" style={{ fontSize: 10 }}>
              {user?.user.email || "Authenticated"}
            </div>
          </div>
          <button className="btnSecondary" onClick={logout}>
            LOGOUT
          </button>
        </div>
      </nav>
      {children}
    </main>
  );
}
function Title({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="hero">
      <div>
        <div className="eyebrow">RAZORRECOVER</div>
        <h1 style={{ fontSize: 32 }}>{title}</h1>
        <div className="muted">{subtitle}</div>
      </div>
      {action}
    </div>
  );
}
function Metric({
  name,
  value,
  sub,
  gold,
}: {
  name: string;
  value: string;
  sub?: string;
  gold?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="card metricCard"
    >
      <div className="metricLabel">{name}</div>
      <div className={"metricValue " + (gold ? "gold" : "")}>{value}</div>
      {sub && <div className="metricSub">{sub}</div>}
    </motion.div>
  );
}
function Loading() {
  return <div className="card loadingCard">Loading verified recovery data…</div>;
}
function ErrorBox({ text }: { text: string }) {
  return text ? <div className="error">{text}</div> : null;
}

export function Dashboard() {
  const { data, error } = useLoad<any>("/api/dashboard");
  if (!data)
    return (
      <Shell>
        <Title
          title="Revenue Command Center"
          subtitle="Loading merchant intelligence…"
        />
        <ErrorBox text={error} />
        <Loading />
      </Shell>
    );
  const m = data.metrics;
  return (
    <Shell>
      <div className="notice" style={{ marginTop: 18 }}>
        {data.mode}. Metrics use only merchant-imported or Razorpay-synchronized
        records.
      </div>
      <Title
        title="Recover revenue before it disappears."
        subtitle={`${inr(m.recovered_revenue_paise)} actual verified recovery from database attribution.`}
        action={
          !data.onboarding.has_payment_data ? (
            <Link className="btn" href="/data-sources">
              CONNECT PAYMENT DATA
            </Link>
          ) : undefined
        }
      />
      <ErrorBox text={error} />
      {!data.onboarding.has_payment_data && (
        <div className="card" style={{ marginBottom: 13 }}>
          <div className="eyebrow">EMPTY WORKSPACE</div>
          <h2>Connect your payment data</h2>
          <p className="muted">
            This merchant has no seeded transactions. Connect Razorpay Test Mode
            or upload a merchant CSV to begin risk detection.
          </p>
          <Link className="btn" href="/data-sources">
            OPEN DATA SOURCES
          </Link>
        </div>
      )}
      <div className="grid metrics">
        <Metric
          name="Revenue At Risk"
          value={inr(m.revenue_at_risk_paise)}
          sub="open detected opportunities"
        />
        <Metric
          name="Recoverable Revenue"
          value={inr(m.recoverable_revenue_paise)}
          sub="deterministic expected value"
          gold
        />
        <Metric
          name="Recovered Revenue"
          value={inr(m.recovered_revenue_paise)}
          sub="verified attribution only"
        />
        <Metric
          name="Recovery Rate"
          value={`${m.recovery_rate}%`}
          sub="actual / at-risk"
        />
        <Metric
          name="Incremental Revenue"
          value={inr(m.incremental_revenue_paise)}
          sub="measured outcomes"
          gold
        />
      </div>
      <div className="grid metrics" style={{ marginTop: 13 }}>
        <Metric name="AI Actions" value={String(m.ai_actions)} />
        <Metric
          name="Successful"
          value={String(m.successful_actions)}
          sub="verified"
        />
        <Metric
          name="Blocked"
          value={String(m.blocked_actions)}
          sub="policy enforced"
        />
        <Metric name="Pending Approval" value={String(m.pending_approvals)} />
        <Metric
          name="Experiments"
          value={String(m.active_experiments)}
          sub="active"
        />
      </div>
      {m.recovery_circuit_breaker_active && (
        <div className="error" style={{ marginTop: 13 }}>
          Recovery workflows paused by safety circuit breaker: {m.recovery_circuit_breaker_reason}
        </div>
      )}
      <div className="economicsHeader">
        <div>
          <div className="eyebrow">VERIFIED RECOVERY ECONOMICS</div>
          <h2 className="sectionTitle">Hard business outcomes</h2>
        </div>
        <span className="badge">DATABASE DERIVED</span>
      </div>
      <div className="grid metrics economicsMetrics">
        <Metric name="Recovered GMV" value={inr(m.recovered_gmv_paise)} sub="verified payment attribution" gold />
        <Metric name="Recovered ARR" value={inr(m.recovered_arr_paise)} sub="annualized verified recurring charges" />
        <Metric name="Cost per Recovery" value={inr(m.cost_per_recovery_paise)} sub={`${inr(m.total_intervention_cost_paise)} total intervention cost`} />
        <Metric name="Net Recovered Revenue" value={inr(m.net_recovered_revenue_paise)} sub="verified GMV minus intervention cost" gold />
        <Metric name="Gateway Success Lift" value={`+${m.gateway_success_rate_improvement_pp} pp`} sub={`${m.gateway_success_rate_before}% → ${m.gateway_success_rate_after}%`} />
      </div>
      <div className="split">
        <div className="card">
          <h2 className="sectionTitle">Verified recovery</h2>
          <div className="chart">
            <ResponsiveContainer>
              <AreaChart data={data.charts.recovery_series}>
                <defs>
                  <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stopColor="#d6a34a" stopOpacity=".4" />
                    <stop offset="1" stopColor="#d6a34a" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="day" stroke="var(--muted)" />
                <YAxis
                  stroke="var(--muted)"
                  tickFormatter={(x) => `₹${Math.round(x / 100000)}k`}
                />
                <Tooltip formatter={(x) => inr(Number(x))} />
                <Area
                  dataKey="recovered_paise"
                  stroke="#d6a34a"
                  fill="url(#gold)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h2 className="sectionTitle">Agent activity</h2>
          <div className="feed">
            {data.events.map((e: any) => (
              <div className="event" key={e.id}>
                <div className="dot" />
                <div>
                  <b style={{ fontSize: 12 }}>{e.title}</b>
                  <div className="metricSub">{e.detail}</div>
                  {e.amount_paise > 0 && (
                    <div className="green" style={{ fontSize: 11 }}>
                      {inr(e.amount_paise)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="card rootCauseCard" style={{ marginTop: 13 }}>
        <div className="chartHeader">
          <div>
            <h2 className="sectionTitle">Revenue at risk by root cause</h2>
            <p>Recoverable opportunity value grouped by detected failure signal.</p>
          </div>
          <span className="chartCount">
            {data.charts.by_cause.length} active drivers
          </span>
        </div>
        <div className="chart rootCauseChart">
          <ResponsiveContainer>
            <BarChart
              data={data.charts.by_cause}
              margin={{ top: 28, right: 20, left: 6, bottom: 2 }}
              barCategoryGap="24%"
            >
              <CartesianGrid stroke="var(--line)" strokeDasharray="4 7" vertical={false} />
              <XAxis
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tickMargin={13}
                tick={{ fill: "var(--muted)", fontSize: 12 }}
                tickFormatter={(x) => label(String(x))}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                width={58}
                tick={{ fill: "var(--muted)", fontSize: 12 }}
                tickFormatter={(x) => compactInr(Number(x))}
              />
              <Tooltip
                cursor={{ fill: "rgba(226,173,72,.045)" }}
                contentStyle={{
                  background: "var(--panel2)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  boxShadow: "0 14px 36px rgba(0,0,0,.32)",
                }}
                labelStyle={{ color: "var(--text)", fontWeight: 700, marginBottom: 6 }}
                itemStyle={{ color: "var(--accent)" }}
                labelFormatter={(x) => label(String(x))}
                formatter={(x) => [inr(Number(x)), "Revenue at risk"]}
              />
              <Bar dataKey="value_paise" radius={[8, 8, 2, 2]} maxBarSize={92}>
                {data.charts.by_cause.map((_: any, index: number) => (
                  <Cell key={index} fill={causeColors[index % causeColors.length]} />
                ))}
                <LabelList
                  dataKey="value_paise"
                  position="top"
                  formatter={(x: any) => compactInr(Number(x))}
                  fill="var(--text)"
                  fontSize={12}
                  fontWeight={700}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Shell>
  );
}

export function Risk() {
  const { data, error } = useLoad<any>("/api/risk/opportunities");
  const [selected, setSelected] = useState<any>(),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  useEffect(() => {
    if (data?.items?.[0] && !selected)
      api(`/api/risk/opportunities/${data.items[0].id}`).then(setSelected);
  }, [data, selected]);
  async function recover() {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    try {
      const r = await api<any>("/api/recovery/payment-link", {
        method: "POST",
        body: JSON.stringify({ opportunity_id: selected.id }),
      });
      setMessage(
        r.provider_url
          ? `Razorpay Test Payment Link: ${r.provider_url}`
          : r.message || "Recovery action created",
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not create recovery");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell>
      <Title
        title="Revenue Risk"
        subtitle="Ranked opportunities with structured root-cause evidence."
      />
      <ErrorBox text={error} />
      <div className="split">
        <div className="card tableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Amount</th>
                <th>Source</th>
                <th>Cause</th>
                <th>Recovery</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((x: any) => (
                <tr
                  className="click"
                  key={x.id}
                  onClick={() =>
                    api(`/api/risk/opportunities/${x.id}`).then(setSelected)
                  }
                >
                  <td>{x.customer.name}</td>
                  <td>{inr(x.order.amount_paise)}</td>
                  <td>
                    <span className="badge">{label(x.order.data_source)}</span>
                  </td>
                  <td>{label(x.root_cause)}</td>
                  <td className="green">
                    {Math.round(x.recovery_probability * 100)}%
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
        {data && !data.items.length && (
          <div className="muted" style={{ padding: 20 }}>
            No risks detected. Import or synchronize payment data from Data
            Sources.
          </div>
        )}
      </div>
        <div className="card detailPanel">
          {selected ? (
            <>
              <div className="eyebrow">DECISION EXPLAINABILITY</div>
              <h2>{label(selected.decision.selected_action)}</h2>
              <div className="row">
                <span className="muted">Problem</span>
                <b>{label(selected.root_cause)}</b>
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <span className="muted">Amount</span>
                <b>{inr(selected.order.amount_paise)}</b>
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <span className="muted">Policy</span>
                <span className="badge">
                  {label(selected.decision.policy_status)}
                </span>
              </div>
              <h3 className="sectionTitle" style={{ marginTop: 20 }}>
                Evidence
              </h3>
              {selected.evidence.map((x: any) => (
                <div
                  className="card"
                  key={x.signal}
                  style={{ padding: 10, marginTop: 7 }}
                >
                  <b style={{ fontSize: 11 }}>{label(x.signal)}</b>
                  <div className="metricSub">{x.detail}</div>
                </div>
              ))}
              <h3 className="sectionTitle" style={{ marginTop: 20 }}>
                Candidate interventions
              </h3>
              {selected.decision.candidates.map((x: any, i: number) => (
                <div
                  className="card"
                  key={x.action}
                  style={{
                    padding: 10,
                    marginTop: 7,
                    borderColor: i === 0 ? "#80652d" : undefined,
                  }}
                >
                  <div className="row">
                    <b>{label(x.action)}</b>
                    <span className="green">
                      {Math.round(x.probability * 100)}%
                    </span>
                  </div>
                  <div className="metricSub">
                    {inr(x.expected_recovery_paise)} expected · cost{" "}
                    {inr(x.cost_paise)} · risk {inr(x.risk_penalty_paise)}
                  </div>
                </div>
              ))}
              <button
                className="btn"
                onClick={recover}
                disabled={busy}
                style={{ width: "100%", marginTop: 14 }}
              >
                {busy ? "POLICY CHECK…" : "CREATE PAYMENT LINK RECOVERY"}
              </button>
              {message && (
                <div
                  className="notice"
                  style={{ marginTop: 9, overflowWrap: "anywhere" }}
                >
                  {message.startsWith("Razorpay") ? (
                    <a
                      href={message.split(": ").slice(1).join(": ")}
                      target="_blank"
                    >
                      {message}
                    </a>
                  ) : (
                    message
                  )}
                </div>
              )}
            </>
          ) : (
            "Select an opportunity"
          )}
        </div>
      </div>
    </Shell>
  );
}
export function Decisions() {
  const { data, error } = useLoad<any>("/api/decisions");
  return (
    <Shell>
      <Title
        title="AI Decisions"
        subtitle="Problem → evidence → candidates → policy → execution → verification."
      />
      <ErrorBox text={error} />
      <div className="grid">
        {data?.items.map((d: any) => (
          <div className="card" key={d.id}>
            <div className="row">
              <div>
                <div className="eyebrow">{label(d.selected_action)}</div>
                <b>
                  {d.risk.customer.name} · {inr(d.risk.order.amount_paise)}
                </b>
              </div>
              <span className="badge">{label(d.policy_status)}</span>
            </div>
            <p className="muted" style={{ fontSize: 12 }}>
              {d.explanation}
            </p>
            <div className="row">
              <span>
                Predicted{" "}
                <b className="green">
                  {Math.round(d.predicted_probability * 100)}%
                </b>
              </span>
              <span>
                Expected{" "}
                <b className="gold">{inr(d.expected_recovery_paise)}</b>
              </span>
              <span>
                {d.execution
                  ? label(d.execution.verification_status)
                  : "Not executed"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
export function Actions() {
  const { data, error, load } = useLoad<any>("/api/actions");
  const [tab, setTab] = useState("all"),
    [busy, setBusy] = useState("");
  const items = useMemo(
    () =>
      data?.items.filter(
        (x: any) =>
          tab === "all" || x.status === tab || x.verification_status === tab,
      ) || [],
    [data, tab],
  );
  async function act(id: string, verb: string) {
    setBusy(id);
    try {
      await api(`/api/actions/${id}/${verb}`, { method: "POST" });
      await load();
    } finally {
      setBusy("");
    }
  }
  return (
    <Shell>
      <Title
        title="Recovery Actions"
        subtitle="Policy-bound execution with provider status and verified attribution."
      />
      <ErrorBox text={error} />
      <div className="tabs">
        {[
          "all",
          "executed",
          "awaiting_approval",
          "blocked",
          "failed",
          "verified",
        ].map((x) => (
          <button
            key={x}
            className={tab === x ? "btn" : "btnSecondary"}
            onClick={() => setTab(x)}
          >
            {label(x)}
          </button>
        ))}
      </div>
      <div className="card tableWrap">
        <table className="table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Status</th>
              <th>Mode</th>
              <th>Verification</th>
              <th>Recovered</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((a: any) => (
              <tr key={a.id}>
                <td>{label(a.action_type)}</td>
                <td>
                  <span className="badge">{label(a.status)}</span>
                </td>
                <td>
                  {label(a.execution_mode)}
                </td>
                <td>{label(a.verification_status)}</td>
                <td className="green">{inr(a.actual_recovered_paise)}</td>
                <td>
                  <div className="row">
                    {a.status === "awaiting_approval" && (
                      <>
                        <button
                          className="btn"
                          disabled={busy === a.id}
                          onClick={() => act(a.id, "approve")}
                        >
                          Approve
                        </button>
                        <button
                          className="danger"
                          onClick={() => act(a.id, "reject")}
                        >
                          Reject
                        </button>
                      </>
                    )}
                    {a.status === "approved" && (
                      <button
                        className="btn"
                        disabled={busy === a.id}
                        onClick={() => act(a.id, "execute")}
                      >
                        Execute
                      </button>
                    )}
                    {a.provider_url && (
                      <a
                        className="btnSecondary"
                        href={a.provider_url}
                        target="_blank"
                      >
                        Open link
                      </a>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!items.length && (
          <div className="muted" style={{ padding: 20, textAlign: "center" }}>
            No actions in this state. Create one from Revenue Risk.
          </div>
        )}
      </div>
    </Shell>
  );
}
export function Experiments() {
  const { data, error } = useLoad<any>("/api/experiments");
  return (
    <Shell>
      <Title
        title="Recovery Experiments"
        subtitle="Observed performance with sample sizes and honest uncertainty."
      />
      <ErrorBox text={error} />
      {data?.items.map((e: any) => (
        <div className="card" key={e.id} style={{ marginBottom: 13 }}>
          <div className="row">
            <div>
              <div className="eyebrow">{e.status}</div>
              <h2>{e.name}</h2>
              <div className="muted">{e.segment}</div>
            </div>
            <div>
              <div className="metricLabel">Observed incremental revenue</div>
              <div className="metricValue gold">
                {inr(e.incremental_revenue_paise)}
              </div>
            </div>
          </div>
          <div className="grid metrics" style={{ marginTop: 18 }}>
            {e.variants.map((v: any) => (
              <div className="card" key={v.id}>
                <div className="metricLabel">{v.variant}</div>
                <div className="metricValue">{v.recovery_rate}%</div>
                <div className="metricSub">
                  n={v.sample_size} · {v.successful_recoveries} recovered ·{" "}
                  {inr(v.recovered_paise)}
                </div>
                <div className="metricSub">
                  {v.confidence_interval
                    ? `95% CI ${v.confidence_interval[0]}–${v.confidence_interval[1]}%`
                    : "Insufficient sample for interval"}
                </div>
              </div>
            ))}
          </div>
          <div className="notice" style={{ marginTop: 13 }}>
            {e.winner
              ? `Highest observed: ${e.winner}. `
              : "No observed winner. "}
            {e.note}
          </div>
        </div>
      ))}
      {data && !data.items.length && (
        <div className="card muted">
          No experiments yet. Experiments begin after real recovery actions
          produce measurable outcomes.
        </div>
      )}
    </Shell>
  );
}
export function Audit() {
  const { data, error } = useLoad<any>("/api/audit");
  return (
    <Shell>
      <Title
        title="Financial Audit Trail"
        subtitle="Persistent, merchant-isolated events separate from ordinary logs."
      />
      <ErrorBox text={error} />
      <div className="card">
        <div className="feed">
          {data?.items.map((x: any) => (
            <div className="event" key={x.id}>
              <div className="dot" />
              <div className="row" style={{ width: "100%" }}>
                <div>
                  <b>{label(x.event_type)}</b>
                  <div className="metricSub">
                    {x.detail.message ||
                      x.detail.reason ||
                      "Financial state transition"}{" "}
                    · {new Date(x.timestamp).toLocaleString()}
                  </div>
                </div>
                {x.amount_paise > 0 && (
                  <div className="green">{inr(x.amount_paise)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
        {!data?.items.length && (
          <div className="muted">
            No financial actions yet. Import payment data and create an eligible
            recovery action to begin the audit trail.
          </div>
        )}
      </div>
    </Shell>
  );
}
export function Assistant() {
  const [q, setQ] = useState("Why did you choose this intervention?"),
    [result, setResult] = useState<any>(),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function ask() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await api("/api/assistant/query", {
          method: "POST",
          body: JSON.stringify({ query: q }),
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assistant unavailable");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Shell>
      <div className="assistant">
        <div className="eyebrow">TOOL-GROUNDED MERCHANT ASSISTANT</div>
        <h1>Ask your recovery data.</h1>
        <p className="muted">
          Numbers come from authenticated backend tools. The language model,
          when configured, can explain but cannot execute or establish financial
          truth.
        </p>
        <div className="row">
          <input
            className="input"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
          />
          <button className="btn" onClick={ask} disabled={busy}>
            {busy ? "ANALYSING…" : "ASK"}
          </button>
        </div>
        <ErrorBox text={error} />
        {result && (
          <div className="card" style={{ marginTop: 14 }}>
            <div className="eyebrow">ANSWER · {label(result.mode)}</div>
            <p className="answer">{result.answer}</p>
            <div className="metricSub">
              Backend tools: {result.tools_called.join(", ")} · Numbers source:{" "}
              {result.numbers_source}
            </div>
          </div>
        )}
        <div className="card" style={{ marginTop: 12 }}>
          <div className="metricSub">
            Try: “What is my largest revenue risk?”, “Which strategy performs
            best?”, “Show blocked actions”, “How much revenue has AI recovered?”
          </div>
        </div>
      </div>
    </Shell>
  );
}
export function Settings() {
  const { data, error, load } = useLoad<any>("/api/settings");
  const [message, setMessage] = useState("");
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body = {
      automatic_threshold_paise: Number(fd.get("automatic_threshold_paise")),
      approval_threshold_paise: Number(fd.get("approval_threshold_paise")),
      blocked_threshold_paise: Number(fd.get("blocked_threshold_paise")),
      max_retries: Number(fd.get("max_retries")),
      minimum_confidence: Number(fd.get("minimum_confidence")),
      cooldown_minutes: Number(fd.get("cooldown_minutes")),
      allowed_actions: [
        "retry",
        "alternate_payment",
        "recovery_link",
        "checkout_recovery",
      ],
    };
    try {
      await api("/api/settings", { method: "PUT", body: JSON.stringify(body) });
      setMessage("Merchant safety policy saved.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Save failed");
    }
  }
  return (
    <Shell>
      <Title
        title="Merchant Safety Settings"
        subtitle="Deterministic guardrails and server-side Razorpay Test Mode status."
      />
      <ErrorBox text={error} />
      {data && (
        <>
          <div className="card" style={{ marginBottom: 13 }}>
            <div className="row">
              <div>
                <div className="eyebrow">RAZORPAY TEST MODE</div>
                <h2>
                  {data.razorpay.connected ? "Connected" : "Not Connected"}
                </h2>
              </div>
              <span className="badge">{data.razorpay.mode}</span>
            </div>
            <div className="grid metrics">
              <Metric
                name="API Key"
                value={data.razorpay.key_id_masked || "Not configured"}
                sub="secret never exposed"
              />
              <Metric
                name="Webhook"
                value={label(data.razorpay.webhook_status)}
                sub="set after valid signed event"
              />
            </div>
          </div>
          <form className="card form" onSubmit={save}>
            <div className="grid metrics">
              <NumberField
                name="automatic_threshold_paise"
                label="Auto threshold (paise)"
                value={data.automatic_threshold_paise}
              />
              <NumberField
                name="approval_threshold_paise"
                label="Approval threshold (paise)"
                value={data.approval_threshold_paise}
              />
              <NumberField
                name="blocked_threshold_paise"
                label="Blocked ceiling (paise)"
                value={data.blocked_threshold_paise}
              />
              <NumberField
                name="max_retries"
                label="Maximum retries"
                value={data.max_retries}
              />
              <NumberField
                name="minimum_confidence"
                label="Minimum confidence"
                value={data.minimum_confidence}
                step=".01"
              />
              <NumberField
                name="cooldown_minutes"
                label="Cooldown minutes"
                value={data.cooldown_minutes}
              />
            </div>
            <div className="notice">
              Connect merchant-specific Razorpay Test Mode credentials from Data
              Sources before executing a financial recovery workflow.
            </div>
            {message && <div className="notice">{message}</div>}
            <button className="btn">SAVE POLICY</button>
          </form>
        </>
      )}
    </Shell>
  );
}
function NumberField({
  name,
  label: lab,
  value,
  step = "1",
}: {
  name: string;
  label: string;
  value: number;
  step?: string;
}) {
  return (
    <div className="field">
      <label>{lab}</label>
      <input
        className="input"
        name={name}
        type="number"
        step={step}
        defaultValue={value}
      />
    </div>
  );
}

export function DataSources() {
  const { data, error, load } = useLoad<any>("/api/data-sources");
  const [busy, setBusy] = useState(""),
    [message, setMessage] = useState(""),
    [selectedImport, setSelectedImport] = useState<any>(null),
    [editingRecord, setEditingRecord] = useState<any>(null),
    [addingRecord, setAddingRecord] = useState(false);
  useEffect(() => {
    if (!selectedImport) return;
    const timer = window.setTimeout(
      () =>
        document
          .getElementById("managed-import")
          ?.scrollIntoView({ behavior: "smooth", block: "start" }),
      80,
    );
    return () => window.clearTimeout(timer);
  }, [selectedImport?.id]);
  async function connect(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy("connect");
    setMessage("");
    const fd = new FormData(form);
    try {
      await api("/api/data-sources/razorpay/connect", {
        method: "POST",
        body: JSON.stringify({
          key_id: fd.get("key_id"),
          key_secret: fd.get("key_secret"),
          webhook_secret: fd.get("webhook_secret"),
        }),
      });
      form.reset();
      setMessage("Razorpay Test Mode connection verified and encrypted.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Connection failed");
    } finally {
      setBusy("");
    }
  }
  async function sync() {
    setBusy("sync");
    setMessage("");
    try {
      const r = await api<any>("/api/data-sources/razorpay/sync", {
        method: "POST",
        body: JSON.stringify({ days: 30, max_records: 1000 }),
      });
      setMessage(
        `Synchronized ${r.run.counts.orders} orders and ${r.run.counts.payments} payments.`,
      );
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Synchronization failed");
    } finally {
      setBusy("");
    }
  }
  async function upload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    if (
      !(fd.get("file") instanceof File) ||
      (fd.get("file") as File).size === 0
    ) {
      setMessage("Choose a supported payment data file first.");
      return;
    }
    setBusy("file");
    setMessage("");
    try {
      const r = await api<any>("/api/data-sources/import/file", {
        method: "POST",
        body: fd,
      });
      setMessage(
        `Imported ${r.run.counts.payments} payments; ${r.run.counts.failed_payments} failures entered recovery analysis.`,
      );
      form.reset();
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "File import failed");
    } finally {
      setBusy("");
    }
  }
  async function disconnect() {
    if (
      !confirm(
        "Remove the stored Razorpay Test Mode connection? Imported records remain.",
      )
    )
      return;
    setBusy("disconnect");
    try {
      await api("/api/data-sources/razorpay", { method: "DELETE" });
      setMessage(
        "Stored Razorpay credentials removed. Imported records were retained.",
      );
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Disconnect failed");
    } finally {
      setBusy("");
    }
  }
  async function openImport(id: string) {
    setBusy(`open:${id}`);
    setMessage("");
    try {
      setSelectedImport(
        await api<any>(`/api/data-sources/imports/${encodeURIComponent(id)}`),
      );
      setEditingRecord(null);
      setAddingRecord(false);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not open import");
    } finally {
      setBusy("");
    }
  }
  async function saveImportRecord(body: any, originalExternalId?: string) {
    if (!selectedImport) return;
    const creating = !originalExternalId;
    setBusy("record");
    setMessage("");
    try {
      const base = `/api/data-sources/imports/${encodeURIComponent(selectedImport.id)}/payments`;
      setSelectedImport(
        await api<any>(
          creating
            ? base
            : `${base}/${encodeURIComponent(originalExternalId)}`,
          { method: creating ? "POST" : "PUT", body: JSON.stringify(body) },
        ),
      );
      setEditingRecord(null);
      setAddingRecord(false);
      setMessage(creating ? "Payment row added." : "Payment row updated.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Payment row could not be saved");
    } finally {
      setBusy("");
    }
  }
  async function deleteImportRecord(externalId: string) {
    if (
      !selectedImport ||
      !confirm(`Remove payment ${externalId} from this imported file?`)
    )
      return;
    setBusy(`delete-row:${externalId}`);
    setMessage("");
    try {
      setSelectedImport(
        await api<any>(
          `/api/data-sources/imports/${encodeURIComponent(selectedImport.id)}/payments/${encodeURIComponent(externalId)}`,
          { method: "DELETE" },
        ),
      );
      setMessage("Payment row removed.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Payment row could not be removed");
    } finally {
      setBusy("");
    }
  }
  async function deleteImportFile(id: string, filename: string) {
    if (
      !confirm(
        `Remove ${filename} and all of its payment rows that are not used by another imported file?`,
      )
    )
      return;
    setBusy(`delete-file:${id}`);
    setMessage("");
    try {
      await api(`/api/data-sources/imports/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      setSelectedImport(null);
      setEditingRecord(null);
      setAddingRecord(false);
      setMessage("Imported file removed. Dashboard metrics were recalculated.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Imported file could not be removed");
    } finally {
      setBusy("");
    }
  }
  if (!data)
    return (
      <Shell>
        <Title
          title="Data Sources"
          subtitle="Connect merchant payment data securely."
        />
        <ErrorBox text={error} />
        <Loading />
      </Shell>
    );
  const r = data.razorpay;
  return (
    <Shell>
      <Title
        title="Data Sources"
        subtitle="Import historical payments, then keep recovery intelligence current with signed webhooks."
      />
      <ErrorBox text={error} />
      {message && (
        <div className="notice" style={{ marginBottom: 13 }}>
          {message}
        </div>
      )}
      <div className="split">
        <div className="card">
          <div className="row">
            <div>
              <div className="eyebrow">RAZORPAY TEST MODE</div>
              <h2>{r.connected ? "Connected" : "Connect your account"}</h2>
            </div>
            <span className="badge">{r.mode}</span>
          </div>
          {r.connected ? (
            <>
              <div className="grid" style={{ marginTop: 14 }}>
                <SettingRow name="API key" value={r.key_id_masked} />
                <SettingRow name="Webhook" value={label(r.webhook_status)} />
                <SettingRow
                  name="Last sync"
                  value={
                    r.last_sync_at
                      ? new Date(r.last_sync_at).toLocaleString()
                      : "Never"
                  }
                />
                <SettingRow
                  name="Orders imported"
                  value={String(r.imported_orders)}
                />
                <SettingRow
                  name="Payments imported"
                  value={String(r.imported_payments)}
                />
              </div>
              <label className="field" style={{ marginTop: 14 }}>
                <span>Webhook URL</span>
                <input className="input" readOnly value={r.webhook_url} />
              </label>
              <div className="metricSub">
                Add this URL in Razorpay Dashboard → Account & Settings →
                Webhooks and select payment.authorized, payment.captured,
                payment.failed, order.paid and payment_link.paid.
              </div>
              {r.sync_error && <div className="error">{r.sync_error}</div>}
              <div
                className="row"
                style={{ justifyContent: "flex-start", marginTop: 14 }}
              >
                <button className="btn" onClick={sync} disabled={!!busy}>
                  {busy === "sync" ? "SYNCING…" : "SYNC LAST 30 DAYS"}
                </button>
                <button
                  className="danger"
                  onClick={disconnect}
                  disabled={!!busy}
                >
                  DISCONNECT
                </button>
              </div>
            </>
          ) : (
            <form className="form" onSubmit={connect}>
              <label className="field">
                <span>Test Mode Key ID</span>
                <input
                  className="input"
                  name="key_id"
                  required
                  placeholder="rzp_test_…"
                  autoComplete="off"
                />
              </label>
              <label className="field">
                <span>Test Mode Key Secret</span>
                <input
                  className="input"
                  name="key_secret"
                  type="password"
                  required
                  autoComplete="new-password"
                />
              </label>
              <label className="field">
                <span>Webhook signing secret</span>
                <input
                  className="input"
                  name="webhook_secret"
                  type="password"
                  required
                  autoComplete="new-password"
                />
              </label>
              <div className="notice">
                Credentials go directly to the API, are encrypted at rest, and
                are never returned to this browser. Only Test Mode keys are
                accepted.
              </div>
              <button className="btn" disabled={!!busy}>
                {busy === "connect" ? "VERIFYING…" : "VERIFY & CONNECT"}
              </button>
            </form>
          )}
        </div>
        <div className="card">
          <div className="eyebrow">MERCHANT FILE IMPORT</div>
          <h2>Upload payment history</h2>
          <p className="muted">
            Import CSV, TSV, Excel, JSON, or a machine-readable PDF table.
            Amounts must be integer paise. Re-uploading the identical file is
            idempotent.
          </p>
          <form className="form" onSubmit={upload}>
            <input
              className="input"
              name="file"
              type="file"
              accept=".csv,.tsv,.xlsx,.xls,.json,.pdf,text/csv,text/tab-separated-values,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/json,application/pdf"
              required
            />
            <button className="btn" disabled={!!busy}>
              {busy === "file" ? "IMPORTING…" : "IMPORT PAYMENT FILE"}
            </button>
          </form>
          <div className="metricSub" style={{ marginTop: 12 }}>
            Required columns
          </div>
          <pre
            className="notice"
            style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
          >
            external_id,order_id,customer_email,customer_name,amount_paise,status,method,failure_code
          </pre>
          <div className="metricSub">
            Status examples: captured, authorized, failed. Imported data is
            labelled MERCHANT IMPORT.
          </div>
          <div className="notice" style={{ marginTop: 12 }}>
            PDF files must contain selectable, machine-readable table text.
            Scanned images are rejected because RazorRecover never guesses
            financial fields.
          </div>
        </div>
      </div>
      <div className="card" style={{ marginTop: 13 }}>
        <h2 className="sectionTitle">Ingestion history</h2>
        <div className="tableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>File</th>
                <th>Source</th>
                <th>Status</th>
                <th>Records</th>
                <th>Started</th>
                <th>Error</th>
                <th>Manage</th>
              </tr>
            </thead>
            <tbody>
              {data.imports.map((x: any) => (
                <tr key={x.id}>
                  <td>
                    <b>{x.filename || "Razorpay synchronization"}</b>
                  </td>
                  <td>{label(x.source)}</td>
                  <td>
                    <span className="badge">{label(x.status)}</span>
                  </td>
                  <td>{x.editable ? x.record_count : x.counts?.payments ?? 0} payments</td>
                  <td>{new Date(x.started_at).toLocaleString()}</td>
                  <td className="muted">{x.error || "—"}</td>
                  <td>
                    {x.editable ? (
                      <button
                        className="btnSecondary"
                        disabled={!!busy}
                        onClick={() => openImport(x.id)}
                      >
                        {busy === `open:${x.id}` ? "OPENING…" : "VIEW / EDIT"}
                      </button>
                    ) : (
                      <span className="muted">Read only</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.imports.length && (
            <div className="muted" style={{ padding: 16 }}>
              No imports yet.
            </div>
          )}
        </div>
      </div>
      {selectedImport && (
        <div
          className="card"
          id="managed-import"
          style={{ marginTop: 13, scrollMarginTop: 18 }}
        >
          <div className="row" style={{ alignItems: "flex-start" }}>
            <div>
              <div className="eyebrow">MANAGED IMPORT</div>
              <h2 className="sectionTitle" style={{ marginTop: 6 }}>
                {selectedImport.filename}
              </h2>
              <div className="muted">
                {selectedImport.records.length} active payment rows. Changes
                immediately update risk detection and dashboard totals.
              </div>
            </div>
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button
                className="btn"
                disabled={!!busy}
                onClick={() => {
                  setAddingRecord(true);
                  setEditingRecord(null);
                }}
              >
                ADD PAYMENT
              </button>
              <button
                className="danger"
                disabled={!!busy}
                onClick={() =>
                  deleteImportFile(selectedImport.id, selectedImport.filename)
                }
              >
                {busy === `delete-file:${selectedImport.id}`
                  ? "REMOVING…"
                  : "REMOVE FILE"}
              </button>
            </div>
          </div>
          {message && (
            <div className="notice" style={{ marginTop: 13 }}>
              {message}
            </div>
          )}
          {(addingRecord || editingRecord) && (
            <ImportRecordForm
              key={editingRecord?.external_id || "new-payment"}
              record={editingRecord}
              busy={busy === "record"}
              onCancel={() => {
                setAddingRecord(false);
                setEditingRecord(null);
              }}
              onSave={saveImportRecord}
            />
          )}
          <div className="tableWrap" style={{ marginTop: 15 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Payment / Order</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Method</th>
                  <th>Failure</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {selectedImport.records.map((record: any) => (
                  <tr key={record.external_id}>
                    <td>
                      <b>{record.external_id}</b>
                      <div className="metricSub">{record.order_id}</div>
                    </td>
                    <td>
                      {record.customer_name}
                      <div className="metricSub">{record.customer_email}</div>
                    </td>
                    <td>{inr(record.amount_paise)}</td>
                    <td>
                      <span className="badge">{label(record.status)}</span>
                    </td>
                    <td>{label(record.payment_type || "one_time")}</td>
                    <td>{label(record.method)}</td>
                    <td className="muted">{record.failure_code || "—"}</td>
                    <td>
                      <div className="row" style={{ justifyContent: "flex-start" }}>
                        <button
                          className="btnSecondary"
                          disabled={!!busy}
                          onClick={() => {
                            setEditingRecord(record);
                            setAddingRecord(false);
                          }}
                        >
                          EDIT
                        </button>
                        <button
                          className="danger"
                          disabled={!!busy}
                          onClick={() => deleteImportRecord(record.external_id)}
                        >
                          {busy === `delete-row:${record.external_id}`
                            ? "REMOVING…"
                            : "REMOVE"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!selectedImport.records.length && (
              <div className="muted" style={{ padding: 16 }}>
                This file has no payment rows. Add a payment or remove the
                empty file.
              </div>
            )}
          </div>
        </div>
      )}
    </Shell>
  );
}

function ImportRecordForm({
  record,
  busy,
  onCancel,
  onSave,
}: {
  record?: any;
  busy: boolean;
  onCancel: () => void;
  onSave: (body: any, originalExternalId?: string) => Promise<void>;
}) {
  const originalExternalId = record?.external_id;
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const values = Object.fromEntries(new FormData(e.currentTarget));
    await onSave(
      { ...values, amount_paise: Number(values.amount_paise) },
      originalExternalId,
    );
  }
  return (
    <form className="recordForm" onSubmit={submit}>
      <div className="row recordFormHeader">
        <div>
          <div className="eyebrow">
            {record ? "EDIT PAYMENT ROW" : "ADD PAYMENT ROW"}
          </div>
          <div className="metricSub">
            Financial amounts must be entered as integer paise.
          </div>
        </div>
        <button type="button" className="btnSecondary" onClick={onCancel}>
          CANCEL
        </button>
      </div>
      <label className="field">
        <span>External payment ID</span>
        <input className="input" name="external_id" required defaultValue={record?.external_id || ""} />
      </label>
      <label className="field">
        <span>Order ID</span>
        <input className="input" name="order_id" required defaultValue={record?.order_id || ""} />
      </label>
      <label className="field">
        <span>Customer name</span>
        <input className="input" name="customer_name" required defaultValue={record?.customer_name || ""} />
      </label>
      <label className="field">
        <span>Customer email</span>
        <input className="input" name="customer_email" type="email" required defaultValue={record?.customer_email || ""} />
      </label>
      <label className="field">
        <span>Amount (paise)</span>
        <input className="input" name="amount_paise" type="number" min="1" step="1" required defaultValue={record?.amount_paise || ""} />
      </label>
      <label className="field">
        <span>Status</span>
        <select className="input" name="status" required defaultValue={record?.status || "failed"}>
          <option value="failed">Failed</option>
          <option value="authorized">Authorized</option>
          <option value="captured">Captured</option>
        </select>
      </label>
      <label className="field">
        <span>Payment method</span>
        <input className="input" name="method" required placeholder="upi, card, netbanking" defaultValue={record?.method || "upi"} />
      </label>
      <label className="field">
        <span>Payment type</span>
        <select className="input" name="payment_type" required defaultValue={record?.payment_type || "one_time"}>
          <option value="one_time">One-time</option>
          <option value="recurring">Recurring / Subscription</option>
        </select>
      </label>
      <label className="field">
        <span>Failure code</span>
        <input className="input" name="failure_code" placeholder="UPI_TIMEOUT" defaultValue={record?.failure_code || ""} />
      </label>
      <label className="field">
        <span>Currency</span>
        <input className="input" name="currency" required minLength={3} maxLength={3} defaultValue={record?.currency || "INR"} />
      </label>
      <label className="field">
        <span>Customer phone (optional)</span>
        <input className="input" name="customer_phone" defaultValue={record?.customer_phone || ""} />
      </label>
      <button className="btn recordSave" disabled={busy}>
        {busy ? "SAVING…" : record ? "SAVE CHANGES" : "ADD PAYMENT"}
      </button>
    </form>
  );
}

function SettingRow({ name, value }: { name: string; value: string }) {
  return (
    <div
      className="row"
      style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}
    >
      <span className="muted">{name}</span>
      <b>{value}</b>
    </div>
  );
}
