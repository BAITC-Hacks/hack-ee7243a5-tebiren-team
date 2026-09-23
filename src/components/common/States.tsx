import { Sparkle } from './Icons'

export function LoadingState({ label = 'Loading your career data…' }: { label?: string }) {
  return <div className="state-card"><span className="loader" /><span>{label}</span></div>
}

export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  return <div className="state-card error-state"><span>We couldn’t load this data. Try again.</span>{onRetry && <button className="text-button" onClick={onRetry}>Retry</button>}</div>
}

export function EmptyState({ title, detail, action }: { title: string; detail?: string; action?: React.ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Sparkle size={19} /></div><h3>{title}</h3>{detail && <p>{detail}</p>}{action}</div>
}
