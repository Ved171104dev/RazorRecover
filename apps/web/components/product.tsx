"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Database, LogOut, Settings as SettingsIcon, Store, UserRound } from "lucide-react";

import { api, inr, label } from "@/lib/api";
import { Brand } from "@/components/brand";

const RecoveryChart = dynamic(() => import("./dashboard-charts").then((module) => module.RecoveryChart), { ssr: false });
const RootCauseChart = dynamic(() => import("./dashboard-charts").then((module) => module.RootCauseChart), { ssr: false });

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
  const load = useCallback(() =>
    api<T>(path)
      .then(setData)
      .catch((e) => setError(e.message)), [path]);
  useEffect(() => {
    void load();
  }, [load]);
  return { data, error, load };
}
function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter(),
    pathname = usePathname();
  const { data: user } = useLoad<any>("/api/auth/me");
  const [accountOpen, setAccountOpen] = useState(false);
  const accountRef = useRef<HTMLDivElement>(null);
  const initials = (user?.user.name || user?.merchant.name || "Merchant")
    .split(/\s+/)
    .slice(0, 2)
    .map((part: string) => part[0])
    .join("")
    .toUpperCase();
  useEffect(() => {
    function closeOnOutside(event: PointerEvent) {
      if (!accountRef.current?.contains(event.target as Node)) setAccountOpen(false);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setAccountOpen(false);
    }
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  async function logout() {
    setAccountOpen(false);
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      router.replace("/");
      router.refresh();
    }
  }
  return (
    <main className="shell">
      <nav className="nav">
        <Link
          href="/dashboard"
          className="brand"
          style={{ textDecoration: "none" }}
        >
          <Brand />
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
        <select
          className="mobileNav"
          aria-label="Navigate merchant workspace"
          value={nav.find((item) => pathname.startsWith(`/${item}`)) || "dashboard"}
          onChange={(event) => router.push(`/${event.target.value}`)}
        >
          {nav.map((item) => <option key={item} value={item}>{label(item)}</option>)}
        </select>
        <div className="accountMenuWrap" ref={accountRef}>
          <button
            className="accountTrigger"
            type="button"
            aria-haspopup="menu"
            aria-expanded={accountOpen}
            onClick={() => setAccountOpen((open) => !open)}
          >
            <span className="avatar">{initials || "M"}</span>
            <span className="accountTriggerText">
              <strong>{user?.merchant.name || "Merchant workspace"}</strong>
              <small>{user?.user.name || "Authenticated user"}</small>
            </span>
            <ChevronDown size={15} className={accountOpen ? "accountChevron open" : "accountChevron"} />
          </button>
          {accountOpen && (
            <div className="accountPopover" role="menu">
              <div className="accountIdentity">
                <span className="accountAvatarLarge">{initials || "M"}</span>
                <div>
                  <strong>{user?.user.name || "Merchant user"}</strong>
                  <span>{user?.user.email || "Authenticated"}</span>
                </div>
              </div>
              <div className="merchantIdentity">
                <Store size={17} />
                <div>
                  <small>MERCHANT WORKSPACE</small>
                  <strong>{user?.merchant.name || "Merchant"}</strong>
                  <span>{label(user?.merchant.role || "member")} · ID {String(user?.merchant.id || "").slice(0, 8)}</span>
                </div>
              </div>
              <div className="accountMenuLinks">
                <Link href="/settings" role="menuitem" onClick={() => setAccountOpen(false)}><SettingsIcon size={17} /><span><strong>Merchant settings</strong><small>Policies and Razorpay status</small></span></Link>
                <Link href="/data-sources" role="menuitem" onClick={() => setAccountOpen(false)}><Database size={17} /><span><strong>Payment data</strong><small>Connections and imports</small></span></Link>
                <Link href="/dashboard" role="menuitem" onClick={() => setAccountOpen(false)}><UserRound size={17} /><span><strong>Merchant dashboard</strong><small>Recovery command center</small></span></Link>
              </div>
              <button className="accountLogout" type="button" role="menuitem" onClick={logout}>
                <LogOut size={17} /><span><strong>Log out</strong><small>Return to the public home page</small></span>
              </button>
            </div>
          )}
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
    <div className="card metricCard">

      <div className="metricLabel">{name}</div>
      <div className={"metricValue " + (gold ? "gold" : "")}>{value}</div>
      {sub && <div className="metricSub">{sub}</div>}
    </div>
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
      <section className="card recoveryPath" aria-label="Live recovery workflow">
        <div className="row recoveryPathHeader">
          <div><div className="eyebrow">LIVE RECOVERY PATH</div><h2>From detected risk to verified learning</h2></div>
          <span className="badge">DATABASE DERIVED</span>
        </div>
        <div className="recoveryPathGrid">
          {[
            ["01", "Detect", compactInr(m.revenue_at_risk_paise), "/risk"],
            ["02", "Diagnose", label(data.charts.by_cause[0]?.name || "No signal"), "/risk"],
            ["03", "Decide", `${m.ai_actions} actions`, "/decisions"],
            ["04", "Govern", `${m.pending_approvals} pending`, "/actions"],
            ["05", "Execute", `${m.ai_actions} prepared`, "/actions"],
            ["06", "Verify", `${m.successful_actions} verified`, "/actions"],
            ["07", "Measure", compactInr(m.recovered_revenue_paise), "/audit"],
            ["08", "Learn", `${m.active_experiments} active`, "/experiments"],
          ].map(([step, stage, value, href]) => <Link href={href} key={stage}><span>{step}</span><strong>{stage}</strong><small>{value}</small></Link>)}
        </div>
      </section>
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
          sub="randomized holdout estimate"
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
          <RecoveryChart data={data.charts.recovery_series} />
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
        <RootCauseChart data={data.charts.by_cause} />
      </div>
    </Shell>
  );
}

export function Risk() {
  const { data, error } = useLoad<any>("/api/risk/opportunities");
  const { data: radar, error: radarError, load: loadRadar } = useLoad<any>("/api/risk/incidents");
  const [selected, setSelected] = useState<any>(),
    [busy, setBusy] = useState(false),
    [batchBusy, setBatchBusy] = useState(false),
    [incidentBusy, setIncidentBusy] = useState(false),
    [selectedIds, setSelectedIds] = useState<Set<string>>(new Set()),
    [message, setMessage] = useState("");
  useEffect(() => {
    if (data?.items?.[0] && !selected)
      api(`/api/risk/opportunities/${data.items[0].id}`).then(setSelected);
  }, [data, selected]);
  function toggleOpportunity(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else if (next.size < 10) next.add(id);
      return next;
    });
  }
  async function prepareSelectedActions() {
    if (!selectedIds.size) return;
    setBatchBusy(true);
    setMessage("");
    try {
      const result = await api<any>("/api/actions/prepare", {
        method: "POST",
        body: JSON.stringify({ opportunity_ids: Array.from(selectedIds) }),
      });
      const counts = Object.entries(result.counts || {})
        .map(([status, count]) => `${count} ${label(status)}`)
        .join(" · ");
      setMessage(`${result.message}${counts ? ` — ${counts}` : ""}. Open Recovery Actions to approve, reject, or execute.`);
      setSelectedIds(new Set());
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not prepare actions");
    } finally {
      setBatchBusy(false);
    }
  }
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
  async function applyIncidentGuardrails() {
    setIncidentBusy(true);setMessage("");
    try {
      const result=await api<any>("/api/risk/incidents/automate",{method:"POST"});
      setMessage(result.paused ? `Recovery circuit breaker activated until ${new Date(result.until).toLocaleString()}: ${result.reason}` : result.reason);
      await loadRadar();
    } catch (e) { setMessage(e instanceof Error ? e.message : "Incident automation failed"); }
    finally { setIncidentBusy(false); }
  }
  return (
    <Shell>
      <Title
        title="Revenue Risk"
        subtitle="Ranked opportunities with structured root-cause evidence."
      />
      <ErrorBox text={error} />
      <ErrorBox text={radarError} />
      <div className="card incidentRadar">
        <div className="row">
          <div>
            <div className="eyebrow">LIVE PAYMENT INCIDENT RADAR</div>
            <h2>Provider and failure clusters</h2>
            <div className="metricSub">
              Latest 1 hour compared with the preceding 23-hour baseline. Derived from merchant payment records.
            </div>
          </div>
          <span className={radar?.circuit_breaker?.active ? "badge dangerBadge" : "badge"}>
            {radar?.circuit_breaker?.active ? "RECOVERY PAUSED" : "GUARDRAILS ACTIVE"}
          </span>
        </div>
        <button className="btnSecondary" style={{marginTop:14}} disabled={incidentBusy} onClick={applyIncidentGuardrails}>
          {incidentBusy ? "EVALUATING…" : "APPLY INCIDENT GUARDRAILS"}
        </button>
        <div className="incidentGrid">
          {radar?.incidents?.slice(0, 4).map((incident: any) => (
            <article className="incidentCard" key={incident.id}>
              <div className="row">
                <span className={"severity " + incident.severity}>{label(incident.severity)}</span>
                <b>{incident.affected_payments} failures</b>
              </div>
              <h3>{label(incident.failure_code)}</h3>
              <div className="metricSub">{label(incident.method)} · {incident.bank}</div>
              <strong className="gold">{inr(incident.revenue_at_risk_paise)} at risk</strong>
              <div className="metricSub">
                {incident.current_failure_rate}% now
                {incident.baseline_failure_rate != null ? ` · ${incident.baseline_failure_rate}% baseline · ${incident.lift_percentage_points >= 0 ? "+" : ""}${incident.lift_percentage_points} pp` : " · baseline unavailable"}
              </div>
              <p>{incident.recommended_response}</p>
            </article>
          ))}
          {radar && !radar.incidents.length && <div className="muted">No failure cluster is active in the current window.</div>}
        </div>
      </div>
      <div className="split">
        <div className="card tableWrap">
          <div className="row" style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
            <div>
              <b>Merchant action queue</b>
              <div className="metricSub">Select 1–10 opportunities. Preparing an action applies policy but does not execute or claim recovery.</div>
            </div>
            <button className="btn" disabled={!selectedIds.size || batchBusy} onClick={prepareSelectedActions}>
              {batchBusy ? "PREPARING…" : `PREPARE ${selectedIds.size || ""} ACTION${selectedIds.size === 1 ? "" : "S"}`}
            </button>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Select</th>
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
                  <td onClick={(event) => event.stopPropagation()}>
                    <input
                      type="checkbox"
                      aria-label={`Select ${x.customer.name}`}
                      checked={selectedIds.has(x.id)}
                      disabled={!selectedIds.has(x.id) && selectedIds.size >= 10}
                      onChange={() => toggleOpportunity(x.id)}
                    />
                  </td>
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
    [busy, setBusy] = useState(""),
    [proof, setProof] = useState<any>(),
    [proofError, setProofError] = useState(""),
    [message, setMessage] = useState("");
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
    setMessage("");
    try {
      await api(`/api/actions/${id}/${verb}`, { method: "POST" });
      await load();
      setMessage(`${label(verb)} completed from verified backend state.`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy("");
    }
  }
  async function notify(id:string,medium:"email"|"sms") {
    setBusy(`${medium}:${id}`);setMessage("");
    try {
      await api(`/api/actions/${id}/notify`,{method:"POST",body:JSON.stringify({medium})});
      await load();setMessage(`Razorpay accepted the ${medium.toUpperCase()} Payment Link notification.`);
    } catch(e) { setMessage(e instanceof Error ? e.message : "Notification failed"); }
    finally { setBusy(""); }
  }
  async function viewProof(id: string) {
    setBusy(`proof:${id}`);
    setProofError("");
    try {
      setProof(await api<any>(`/api/actions/${id}/proof`));
    } catch (e) {
      setProofError(e instanceof Error ? e.message : "Could not load recovery proof");
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
      {message && <div className="notice" style={{marginBottom:13}}>{message}</div>}
      <div className="tabs">
        {[
          "all",
          "executed",
          "awaiting_approval",
          "blocked",
          "failed",
          "verified",
          "shadow",
          "holdout",
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
              <th>Customer / Order</th>
              <th>Amount</th>
              <th>Action</th>
              <th>Experiment</th>
              <th>Status</th>
              <th>Mode</th>
              <th>Verification</th>
              <th>Delivery</th>
              <th>Recovered</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((a: any) => (
              <tr key={a.id}>
                <td>
                  <b>{a.customer?.name || "Customer"}</b>
                  <div className="metricSub">{a.order?.external_ref || a.payment?.external_ref}</div>
                </td>
                <td className="gold">{inr(a.amount_paise)}</td>
                <td>{label(a.action_type)}</td>
                <td>
                  {a.experiment ? <><span className="badge">{a.experiment.variant}</span><div className="metricSub">Outcome pending until verification</div></> : <span className="muted">Not assigned</span>}
                </td>
                <td>
                  <span className="badge">{label(a.status)}</span>
                </td>
                <td>
                  {label(a.execution_mode)}
                </td>
                <td>{label(a.verification_status)}</td>
                <td>
                  <span className="badge">{label(a.delivery_status)}</span>
                  <div className="metricSub">{a.delivery_channel ? label(a.delivery_channel) : "No channel"}</div>
                </td>
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
                    {a.provider_reference && !["verified","failed"].includes(a.status) && (
                      <>
                        <button className="btnSecondary" disabled={!!busy} onClick={() => act(a.id,"reconcile")}>Reconcile</button>
                        <button className="btnSecondary" disabled={!!busy} onClick={() => notify(a.id,"email")}>Email</button>
                        {a.customer?.phone_available && <button className="btnSecondary" disabled={!!busy} onClick={() => notify(a.id,"sms")}>SMS</button>}
                      </>
                    )}
                    <button className="btnSecondary" disabled={busy === `proof:${a.id}`} onClick={() => viewProof(a.id)}>
                      Proof
                    </button>
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
      <ErrorBox text={proofError} />
      {proof && (
        <section className="card proofReceipt">
          <div className="row proofHeader">
            <div>
              <div className="eyebrow">RECOVERY PROOF RECEIPT</div>
              <h2>{proof.receipt_id}</h2>
              <div className="metricSub">Generated from {label(proof.generated_from)} · predicted and actual values are kept separate.</div>
            </div>
            <button className="btnSecondary" onClick={() => setProof(undefined)}>Close</button>
          </div>
          <div className="proofEconomics">
            <Metric name="Revenue at risk" value={inr(proof.problem.amount_at_risk_paise)} sub={label(proof.problem.root_cause)} />
            <Metric name="Predicted recovery" value={inr(proof.financial_truth.predicted_recovery_paise)} sub="model estimate" />
            <Metric name="Actual verified" value={inr(proof.financial_truth.actual_verified_recovery_paise)} sub={proof.financial_truth.counted_as_recovered ? "attribution recorded" : "not counted"} />
            <Metric name="Verification" value={label(proof.verification.status)} sub={label(proof.verification.source || "not verified")} />
          </div>
          <div className="proofStages">
            {[
              ["Problem", `${label(proof.problem.root_cause)} · confidence ${Math.round(proof.problem.confidence * 100)}%`],
              ["Decision", `${label(proof.decision.selected_action)} · ${Math.round(proof.decision.predicted_probability * 100)}% predicted`],
              ["Governance", `${label(proof.governance.policy_status)}${proof.governance.approval ? ` · approval ${label(proof.governance.approval.status)}` : ""}`],
              ["Delivery", `${label(proof.delivery.status)} · ${label(proof.delivery.channel || "no channel")} · ${proof.action.contacts?.length || 0} contact event(s)`],
              ["Verification", `${label(proof.verification.status)} · ${proof.verification.webhook_evidence.length} signed event(s)`],
              ["Attribution", `${label(proof.attribution.status)} · ${inr(proof.attribution.amount_recovered_paise)}`],
            ].map(([stage, detail]) => <article key={stage}><span>{stage}</span><strong>{detail}</strong></article>)}
          </div>
          <div className="notice">{proof.delivery.note}</div>
          <h3>Immutable financial audit timeline</h3>
          <div className="proofTimeline">
            {proof.audit_timeline.map((event: any, index: number) => (
              <div key={`${event.timestamp}:${index}`}><span>{new Date(event.timestamp).toLocaleString()}</span><b>{label(event.event)}</b><small>{event.detail?.message || "Persisted event"}</small></div>
            ))}
            {!proof.audit_timeline.length && <span className="muted">No audit events are associated with this action yet.</span>}
          </div>
        </section>
      )}
    </Shell>
  );
}
export function Experiments() {
  const { data, error, load } = useLoad<any>("/api/experiments");
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  async function createHoldout() {
    setBusy(true);setMessage("");
    try {
      await api("/api/experiments", {method:"POST",body:JSON.stringify({name:"AI Recovery Incrementality Holdout",segment:"Eligible policy-approved payment recovery opportunities",experiment_type:"controlled_holdout"})});
      setMessage("Controlled 10% holdout is running. Future eligible actions receive a deterministic assignment.");
      await load();
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not create holdout"); }
    finally { setBusy(false); }
  }
  return (
    <Shell>
      <Title
        title="Recovery Experiments"
        subtitle="Randomized holdouts measure incremental recovery beyond natural customer payment."
      />
      <ErrorBox text={error} />
      <div className="card experimentIntro">
        <div>
          <div className="eyebrow">CAUSAL MEASUREMENT</div>
          <h2>Prove lift, not correlation</h2>
          <div className="metricSub">10% control receives no AI contact; 90% treatment receives the policy-approved recommendation. Assignment is deterministic and persisted.</div>
        </div>
        <button className="btn" disabled={busy || data?.items?.some((x:any)=>x.experiment_type==="controlled_holdout" && x.status==="running")} onClick={createHoldout}>
          {busy ? "STARTING…" : "START CONTROLLED HOLDOUT"}
        </button>
      </div>
      {message && <div className="notice" style={{marginBottom:13}}>{message}</div>}
      {data?.items.map((e: any) => (
        <div className="card" key={e.id} style={{ marginBottom: 13 }}>
          <div className="row">
            <div>
              <div className="eyebrow">{e.status} · {label(e.experiment_type)} · n={e.participants} · {e.pending_outcomes} pending</div>
              <h2>{e.name}</h2>
              <div className="muted">{e.segment}</div>
            </div>
            <div>
              <div className="metricLabel">Causal incremental revenue</div>
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
                  n={v.sample_size} · {v.pending_outcomes} pending · {v.excluded_outcomes} excluded · {v.completed_outcomes} verified outcomes
                </div>
                <div className="metricSub">
                  Predicted {inr(v.predicted_recovery_paise)} · verified {v.successful_recoveries} · {inr(v.recovered_paise)}
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
            {e.experiment_type === "controlled_holdout" && e.uplift_percentage_points != null ? `Measured uplift: ${e.uplift_percentage_points >= 0 ? "+" : ""}${e.uplift_percentage_points} percentage points. ` : ""}
            {e.winner ? `Evidence-ready winner: ${e.winner}. ` : "No causal winner declared. "}
            {e.note}
          </div>
        </div>
      ))}
      {data && !data.items.length && (
        <div className="card muted">
          No experiments yet. Start the controlled holdout, then prepare eligible actions from Revenue Risk.
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
                    · {new Date(x.timestamp).toLocaleString()} · {label(x.actor_type)}
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
  const prompts = [
    "What is my net recovered revenue?",
    "Why is revenue at risk?",
    "How did gateway success rate change?",
    "What is recovered ARR?",
    "How much revenue is incremental?",
    "Which strategy performs best?",
  ];
  async function ask(question = q) {
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    setQ(question);
    try {
      setResult(
        await api("/api/assistant/query", {
          method: "POST",
          body: JSON.stringify({ query: question }),
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
        <h1>Ask your revenue intelligence.</h1>
        <p className="muted">
          Ask about revenue risk, recovered GMV or ARR, recovery cost, gateway
          success, policy, and experiments. Numbers come from authenticated
          backend tools; the model explains but cannot execute or establish
          financial truth.
        </p>
        <div className="assistantComposer">
          <input
            className="input"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void ask()}
            aria-label="Ask a merchant finance question"
          />
          <button className="btn" onClick={() => void ask()} disabled={busy || !q.trim()}>
            {busy ? "ANALYSING…" : "ASK"}
          </button>
        </div>
        <div className="assistantPrompts">
          {prompts.map((prompt) => <button type="button" key={prompt} disabled={busy} onClick={() => void ask(prompt)}>{prompt}</button>)}
        </div>
        <ErrorBox text={error} />
        {result && (
          <div className="card assistantAnswer" style={{ marginTop: 14 }}>
            <div className="row">
              <div className="eyebrow">ANSWER · {label(result.mode)}</div>
              <span className="badge">{label(result.scope || "merchant finance")}</span>
            </div>
            <p className="answer">{result.answer}</p>
            <div className="metricSub">
              {result.tools_called.length ? `Backend tools: ${result.tools_called.join(", ")} · ` : ""}
              Numbers source: {result.grounding || result.numbers_source}
            </div>
          </div>
        )}
        <div className="assistantBoundary">
          Merchant finance only. The assistant does not provide personal
          investment, trading, tax, lending, or legal advice and cannot execute
          recovery actions.
        </div>
      </div>
    </Shell>
  );
}
export function Settings() {
  const { data, error, load } = useLoad<any>("/api/settings");
  const { data: modelHealth } = useLoad<any>("/api/model/health");
  const { data: team, load: loadTeam } = useLoad<any>("/api/team");
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
      shadow_mode: fd.get("shadow_mode") === "on",
      maker_checker_enabled: fd.get("maker_checker_enabled") === "on",
      incident_auto_pause_enabled: fd.get("incident_auto_pause_enabled") === "on",
      daily_contact_limit: Number(fd.get("daily_contact_limit")),
      quiet_hours_start_utc: Number(fd.get("quiet_hours_start_utc")),
      quiet_hours_end_utc: Number(fd.get("quiet_hours_end_utc")),
      max_model_brier_score: Number(fd.get("max_model_brier_score")),
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
  async function addMember(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();const form=e.currentTarget;const fd=new FormData(form);setMessage("");
    try {
      await api("/api/team",{method:"POST",body:JSON.stringify({name:fd.get("name"),email:fd.get("email"),password:fd.get("password"),role:fd.get("role")})});
      form.reset();await loadTeam();setMessage("Team member created and associated with this merchant.");
    } catch(e) { setMessage(e instanceof Error ? e.message : "Could not add team member"); }
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
            <label className="shadowControl">
              <span>
                <b>Shadow mode</b>
                <small>Score, decide, govern, and audit every opportunity without creating links, contacting customers, or calling the payment provider.</small>
              </span>
              <input name="shadow_mode" type="checkbox" defaultChecked={data.shadow_mode} />
            </label>
            <label className="shadowControl">
              <span><b>Maker–checker approvals</b><small>When enabled, the user who prepares an approval-required action cannot approve it. Add an Approver below first.</small></span>
              <input name="maker_checker_enabled" type="checkbox" defaultChecked={data.maker_checker_enabled} />
            </label>
            <label className="shadowControl">
              <span><b>Automatic incident circuit breaker</b><small>Allows deterministic critical failure clusters to pause recovery execution for one hour.</small></span>
              <input name="incident_auto_pause_enabled" type="checkbox" defaultChecked={data.incident_auto_pause_enabled} />
            </label>
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
              <NumberField name="daily_contact_limit" label="Customer contacts / 24h" value={data.daily_contact_limit} />
              <NumberField name="quiet_hours_start_utc" label="Quiet hours start (UTC)" value={data.quiet_hours_start_utc} />
              <NumberField name="quiet_hours_end_utc" label="Quiet hours end (UTC)" value={data.quiet_hours_end_utc} />
              <NumberField name="max_model_brier_score" label="Maximum Brier score" value={data.max_model_brier_score} step=".01" />
            </div>
            <div className="notice">
              Connect merchant-specific Razorpay Test Mode credentials from Data
              Sources before executing a financial recovery workflow.
            </div>
            {message && <div className="notice">{message}</div>}
            <button className="btn">SAVE POLICY</button>
          </form>
          <div className="grid settingsOps">
            <section className="card">
              <div className="eyebrow">MODEL QUALITY GATE</div>
              <h2>{label(modelHealth?.status || "loading")}</h2>
              <div className="metricValue">{modelHealth?.brier_score ?? "—"}</div>
              <div className="metricSub">Brier score · threshold {modelHealth?.threshold ?? data.max_model_brier_score} · n={modelHealth?.sample_size || 0}</div>
              <div className="notice" style={{marginTop:12}}>{modelHealth?.interpretation || "Execution remains available until sufficient verified outcomes exist."}</div>
            </section>
            <section className="card">
              <div className="eyebrow">MERCHANT TEAM</div>
              <h2>Maker–checker roles</h2>
              <div className="teamList">{team?.items?.map((member:any)=><div className="row" key={member.id}><span><b>{member.name}</b><small>{member.email}</small></span><span className="badge">{label(member.role)}</span></div>)}</div>
              {team?.current_role==="owner" && <form className="form compactForm" onSubmit={addMember}>
                <input className="input" name="name" required placeholder="Member name" />
                <input className="input" name="email" type="email" required placeholder="member@gmail.com" />
                <input className="input" name="password" type="password" required minLength={10} placeholder="Temporary strong password" />
                <select className="input" name="role" defaultValue="approver"><option value="approver">Approver</option><option value="analyst">Analyst</option></select>
                <button className="btn">ADD TEAM MEMBER</button>
              </form>}
            </section>
          </div>
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
  const { data: reliability, error: reliabilityError, load: loadReliability } = useLoad<any>("/api/webhooks/reliability");
  const { data: operations, load: loadOperations } = useLoad<any>("/api/operations/health");
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
  }, [selectedImport]);
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
      await loadReliability();
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
  async function testConnection() {
    setBusy("test-connection");
    setMessage("");
    try {
      const result = await api<any>("/api/data-sources/razorpay/test", { method: "POST" });
      setMessage(`Razorpay API connection verified at ${new Date(result.last_verified_at).toLocaleString()}.`);
      await Promise.all([load(), loadOperations()]);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Connection test failed");
    } finally {
      setBusy("");
    }
  }
  async function copyWebhookUrl() {
    if (!data?.razorpay?.webhook_url) return;
    try {
      await navigator.clipboard.writeText(data.razorpay.webhook_url);
      setMessage("Merchant-specific webhook URL copied.");
    } catch {
      setMessage("Could not copy automatically. Select the webhook URL and copy it manually.");
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
  async function replayWebhook(id:string) {
    setBusy(`replay:${id}`);setMessage("");
    try {
      await api(`/api/webhooks/${id}/replay`,{method:"POST"});
      setMessage("Webhook replay accepted. Financial idempotency remains enforced.");
      await loadReliability();
    } catch(e) { setMessage(e instanceof Error ? e.message : "Webhook replay failed"); }
    finally { setBusy(""); }
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
      <ErrorBox text={reliabilityError} />
      {message && (
        <div className="notice" style={{ marginBottom: 13 }}>
          {message}
        </div>
      )}
      <div className="card setupChecklist">
        <div className="row">
          <div>
            <div className="eyebrow">GO-LIVE CHECKLIST</div>
            <h2>Connect, verify, recover</h2>
            <div className="metricSub">Each completed step is backed by merchant-scoped database state.</div>
          </div>
          <span className="badge">{[
            r.connected,
            r.webhook_status === "verified",
            r.imported_payments > 0 || data.imports.some((item:any) => (item.counts?.payments || 0) > 0),
          ].filter(Boolean).length}/3 READY</span>
        </div>
        <div className="checklistGrid">
          <div className={r.connected ? "checklistItem complete" : "checklistItem"}><b>1</b><span><strong>Connect Razorpay</strong><small>{r.connected ? "Test API credentials verified" : "Add rzp_test_ credentials below"}</small></span></div>
          <div className={r.webhook_status === "verified" ? "checklistItem complete" : "checklistItem"}><b>2</b><span><strong>Verify webhook</strong><small>{r.webhook_status === "verified" ? "A signed event was accepted" : "Add the generated URL in Razorpay"}</small></span></div>
          <div className={r.imported_payments > 0 || data.imports.some((item:any) => (item.counts?.payments || 0) > 0) ? "checklistItem complete" : "checklistItem"}><b>3</b><span><strong>Load payment data</strong><small>{r.imported_payments > 0 ? `${r.imported_payments} Razorpay payments synchronized` : "Sync Razorpay or import a file"}</small></span></div>
        </div>
        <div className="row checklistActions">
          <span className="metricSub">Next: review a detected opportunity and prepare a policy-bound action.</span>
          <Link className="btnSecondary" href="/risk">OPEN REVENUE RISK</Link>
        </div>
      </div>
      <div className={r.connected ? "card reliabilityCenter" : "card reliabilityCenter reliabilityEmpty"}>
        <div className="row">
          <div>
            <div className="eyebrow">WEBHOOK RELIABILITY CENTER</div>
            <h2>{r.connected ? "Financial event integrity" : "Monitoring activates after connection"}</h2>
            <div className="metricSub">{r.connected ? "Signature validation, idempotency, processing state, and last verified delivery—without exposing webhook payloads." : "Connect Razorpay first. Signed delivery metrics will appear after the first Test Mode webhook reaches this merchant."}</div>
          </div>
          <span className="badge">{label(r.connected ? reliability?.health || "waiting for event" : "not connected")}</span>
        </div>
        {r.connected ? <>
          <div className="reliabilityMetrics">
            <Metric name="Received" value={String(reliability?.metrics?.received || 0)} sub="merchant events" />
            <Metric name="Valid signatures" value={String(reliability?.metrics?.signature_valid || 0)} sub="cryptographically accepted" />
            <Metric name="Duplicates ignored" value={String(reliability?.metrics?.duplicates_ignored || 0)} sub="idempotency enforced" />
            <Metric name="Processing failures" value={String(reliability?.metrics?.processing_failures || 0)} sub={reliability?.metrics?.pending ? `${reliability.metrics.pending} pending` : "queue clear"} />
          </div>
          <div className="metricSub reliabilityFoot">
            Last valid event: {reliability?.metrics?.last_valid_event_at ? new Date(reliability.metrics.last_valid_event_at).toLocaleString() : "None received"} · {reliability?.metrics?.out_of_order_assumption || "Provider state is authoritative."}
          </div>
          <div className="operationsStrip">
            <span>API <b>{label(operations?.api || "unavailable")}</b></span>
            <span>Database <b>{label(operations?.database || "unavailable")}</b></span>
            <span>Redis <b>{label(operations?.redis || "unavailable")}</b></span>
            <span>Worker <b>{label(operations?.worker?.status || "unavailable")}</b></span>
          </div>
          {!!reliability?.events?.length && <div className="webhookEvents">
            {reliability.events.slice(0,6).map((event:any)=><div className="row" key={event.id}>
              <span><b>{label(event.event_type)}</b><small>{event.event_id} · {new Date(event.received_at).toLocaleString()} · replayed {event.replay_count}×</small></span>
              <span className="row"><span className="badge">{label(event.status)}</span>{["failed","received"].includes(event.status) && event.signature_valid && <button className="btnSecondary" disabled={busy===`replay:${event.id}`} onClick={()=>replayWebhook(event.id)}>Replay</button>}</span>
            </div>)}
          </div>}
        </> : <div className="reliabilityEmptySteps"><span>1 · Connect test credentials</span><span>2 · Copy the generated webhook URL</span><span>3 · Send a signed Razorpay Test Mode event</span></div>}
      </div>
      <div className="sourceSectionHead">
        <div><div className="eyebrow">PAYMENT DATA INTAKE</div><h2>Choose a trusted source</h2><p>Connect Razorpay for continuous Test Mode synchronization or import historical merchant records for analysis.</p></div>
        <span className="badge">REAL DATA ONLY</span>
      </div>
      <div className="split sourceGrid">
        <div className="card sourceCard">
          <div className="row">
            <div>
              <div className="eyebrow">01 · RAZORPAY TEST MODE</div>
              <h2>{r.connected ? "Connected" : "Connect your account"}</h2>
              <div className="metricSub">Continuous orders, payments, Payment Links, and signed lifecycle events.</div>
            </div>
            <span className="badge">{r.mode}</span>
          </div>
          {r.connected ? (
            <>
              <div className="grid" style={{ marginTop: 14 }}>
                <SettingRow name="API key" value={r.key_id_masked} />
                <SettingRow name="Webhook" value={label(r.webhook_status)} />
                <SettingRow name="API status" value={label(operations?.razorpay?.status || "checking")} />
                <SettingRow name="Worker" value={label(operations?.worker?.status || "checking")} />
                <SettingRow
                  name="Last API verification"
                  value={r.last_verified_at ? new Date(r.last_verified_at).toLocaleString() : "Never"}
                />
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
                <span className="copyField">
                  <input className="input" readOnly value={r.webhook_url} />
                  <button className="btnSecondary" type="button" onClick={copyWebhookUrl}>COPY</button>
                </span>
              </label>
              <div className="metricSub">
                Add this URL in Razorpay Dashboard → Account & Settings →
                Webhooks and select payment.authorized, payment.captured,
                payment.failed, order.paid, payment_link.paid,
                payment_link.cancelled and payment_link.expired.
              </div>
              {r.sync_error && <div className="error">{r.sync_error}</div>}
              <div
                className="row"
                style={{ justifyContent: "flex-start", marginTop: 14 }}
              >
                <button className="btn" onClick={sync} disabled={!!busy}>
                  {busy === "sync" ? "SYNCING…" : "SYNC LAST 30 DAYS"}
                </button>
                <button className="btnSecondary" type="button" onClick={testConnection} disabled={!!busy}>
                  {busy === "test-connection" ? "TESTING…" : "TEST CONNECTION"}
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
        <div className="card sourceCard">
          <div className="eyebrow">02 · MERCHANT FILE IMPORT</div>
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
