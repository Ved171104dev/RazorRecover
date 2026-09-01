export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brandLockup" aria-label="RazorRecover">
      <svg className="brandMark" viewBox="0 0 40 40" role="img" aria-hidden="true">
        <rect x="2.5" y="2.5" width="35" height="35" rx="11" fill="none" stroke="currentColor" strokeWidth="1.5" opacity=".35" />
        <path d="M29.5 16.2A10.7 10.7 0 1 0 28 27.1" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" />
        <path d="m27.1 22.6 1.2 5.2-5.2-1.2" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M14.7 14.8h6.1a3.9 3.9 0 0 1 0 7.8h-6.1m3.6 0 5 5.2M14.7 11.9v16.2" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {!compact && <span className="brandWord">RAZOR<b>RECOVER</b></span>}
    </span>
  );
}
