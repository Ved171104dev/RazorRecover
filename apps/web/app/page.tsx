import Link from "next/link";
export default function Home() {
  return (
    <main className="landing">
      <nav className="nav">
        <div className="brand">
          RAZOR<span>RECOVER</span>
        </div>
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
          <div
            className="row"
            style={{ justifyContent: "flex-start", marginTop: 22 }}
          >
            <Link className="btn" href="/signup">
              CREATE MERCHANT WORKSPACE
            </Link>
            <span className="mode">REAL DATA · TEST PAYMENTS</span>
          </div>
        </div>
        <div className="card">
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
    </main>
  );
}
