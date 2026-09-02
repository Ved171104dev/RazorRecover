import Link from "next/link";
import { Brand } from "@/components/brand";
export default function Home() {
  return (
    <main className="landing">
      <nav className="nav">
        <Link href="/" className="brand landingBrand"><Brand /></Link>
        <div className="landingNavLinks"><a href="#workflow">How it works</a><a href="#guardrails">Guardrails</a><a href="#razorpay">Razorpay</a></div>
        <div className="row">
          <Link className="btnSecondary" href="/login">
            LOGIN
          </Link>
          <Link className="btn" href="/signup">
            CREATE ACCOUNT
          </Link>
        </div>
      </nav>
      <section className="landingHero">
        <div>
          <div className="eyebrow">
            AUTONOMOUS REVENUE RECOVERY INTELLIGENCE
          </div>
          <h1>
            Recover revenue.
            <br />
            <span className="gold">Prove every rupee.</span>
          </h1>
          <p className="muted" style={{ maxWidth: 650, lineHeight: 1.7 }}>
            RazorRecover detects payment risk, explains the cause, selects a
            bounded intervention, applies merchant policy, executes a legitimate
            Razorpay Test Mode workflow, and only counts revenue after
            verification.
          </p>
          <div className="landingHeroActions">

            <Link className="btn" href="/signup">
              CREATE MERCHANT WORKSPACE
            </Link>
            <span className="mode">REAL DATA · TEST PAYMENTS</span>
          </div>
          <div className="landingTrust"><span>✓ Deterministic money logic</span><span>✓ Merchant-isolated data</span><span>✓ Verified attribution</span></div>
        </div>
        <div className="card landingLoopCard">
          <div className="eyebrow">THE CORE LOOP</div>
          <div className="flow" style={{ marginTop: 14 }}>
            {[
              "DETECT",
              "DIAGNOSE",
              "DECIDE",
              "GOVERN",
              "EXECUTE",
              "VERIFY",
              "MEASURE",
              "LEARN",
            ].map((x) => (
              <div key={x}>{x}</div>
            ))}
          </div>
          <div className="notice" style={{ marginTop: 16 }}>
            Financial truth is deterministic. AI explains evidence; it cannot
            fabricate recovery or bypass policy.
          </div>
        </div>
      </section>
      <section className="landingProof">
        <div><strong>POSTGRESQL</strong><span>Persistent merchant data</span></div><div><strong>LOCAL ML</strong><span>Fast decision support</span></div><div><strong>WEBHOOKS</strong><span>Signed provider events</span></div><div><strong>EXPERIMENTS</strong><span>Measured outcomes</span></div>
      </section>
      <section className="landingSection">
        <div className="eyebrow">FROM FAILURE TO FINANCIAL TRUTH</div>
        <div className="landingSectionHead"><h2>More than a failed-payment dashboard.</h2><p>Detection is only the beginning. RazorRecover closes the loop from opportunity discovery to verified attribution and transparent learning.</p></div>
        <div className="landingValueGrid">
          <article><span>01</span><h3>Know what is recoverable</h3><p>Rank opportunities by risk, recovery probability, confidence, and deterministic expected value.</p></article>
          <article><span>02</span><h3>Understand every decision</h3><p>See root cause, evidence, candidate interventions, policy state, and the selected strategy.</p></article>
          <article><span>03</span><h3>Measure actual outcomes</h3><p>Track verified GMV, net recovered revenue, cost per recovery, and strategy performance.</p></article>
        </div>
      </section>
      <section className="landingSection" id="workflow">
        <div className="eyebrow">THE ACCOUNTABLE RECOVERY LOOP</div>
        <div className="landingSectionHead"><h2>One engine. Eight accountable stages.</h2><p>Every stage persists evidence for the merchant, the financial audit trail, and the next decision.</p></div>
        <div className="landingLoop">
          {[
            ["Detect", "Find failed payments and abandoned checkouts worth saving."],["Diagnose", "Explain root cause with provider and customer evidence."],["Decide", "Compare eligible interventions by expected recovery."],["Govern", "Apply retry ceilings, cooldowns, and merchant policy."],["Execute", "Create a legitimate provider workflow or seek approval."],["Verify", "Confirm payment state through webhook or provider API."],["Measure", "Attribute recovered paise once, without duplicates."],["Learn", "Compare predicted and actual strategy outcomes."],
          ].map(([title, copy], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><h3>{title}</h3><p>{copy}</p></article>)}
        </div>
      </section>
      <section className="landingSection landingGuardrails" id="guardrails">
        <div><div className="eyebrow">FINANCIAL AI WITH BOUNDARIES</div><h2>AI explains.<br /><span className="gold">Policy decides.</span></h2><p>The language model creates clear merchant narratives, but cannot alter financial facts, bypass policy, execute an ineligible action, or claim unverified recovery.</p><div className="landingPolicy"><span>MAX RETRIES</span><strong>3 within 7 days</strong><span>HARD STOPS</span><strong>Expired card · blocked account</strong><span>ESCALATION</span><strong>Merchant approval when required</strong></div></div>
        <div className="landingPrinciples">
          <article><b>POLICY</b><div><h3>Policy before action</h3><p>Every intervention is allowed, sent for approval, or blocked by deterministic rules.</p></div></article>
          <article><b>ONCE</b><div><h3>Idempotent by design</h3><p>The same action, webhook, or payment cannot create duplicate execution or attribution.</p></div></article>
          <article><b>PROOF</b><div><h3>Verified financial truth</h3><p>A request is not recovery. Revenue changes only after verified payment evidence.</p></div></article>
        </div>
      </section>
      <section className="landingSection landingProvider" id="razorpay">
        <div><div className="eyebrow">RAZORPAY TEST MODE</div><h2>Execution connected to payment reality.</h2><p>Server-side credentials create legitimate Test Mode payment links. Signed webhooks synchronize provider state and update attribution exactly once.</p></div>
        <div className="landingProviderFlow"><div><strong>Recovery decision</strong><span>Eligible + governed</span></div><i>→</i><div className="active"><strong>Payment Link</strong><span>Razorpay Test Mode</span></div><i>→</i><div><strong>Verification</strong><span>Webhook / API state</span></div></div>
      </section>
      <section className="landingFinalCta"><div><div className="eyebrow">RECOVER WITH EVIDENCE</div><h2>Turn revenue risk into accountable action.</h2><p>Connect Razorpay Test Mode or import merchant payment history to begin.</p></div><div className="row"><Link className="btn" href="/signup">CREATE WORKSPACE →</Link><Link className="btnSecondary" href="/login">LOGIN</Link></div></section>
      <footer className="landingFooter"><div className="brand"><Brand /></div><p>Autonomous revenue recovery with deterministic financial truth.</p><span>TEST MODE · NO REAL MONEY</span></footer>
    </main>
  );
}
