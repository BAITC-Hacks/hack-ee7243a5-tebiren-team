import type { ActivityHistoryItem } from '../../api/types'
import { Clock } from '../common/Icons'
import { StatusBadge } from '../common/Badge'

export function ActivityHistory({ history }: { history: ActivityHistoryItem[] }) {
  return <section className="card history-section"><div className="section-heading"><div><div className="section-kicker">ACTIVITY HISTORY</div><h2>Learning trail</h2></div><span className="history-count"><Clock size={14} /> {history.length} activities</span></div>{history.length ? <div className="history-list">{history.map((item) => <div className="history-row" key={item.record_id}><div className="history-mark"><span /></div><div className="history-main"><strong>{item.title || item.event_id}</strong><span>{formatDate(item.date)} <i>·</i> {item.event_id}</span></div><div className="history-progress">{item.completion_pct !== undefined && <><div className="mini-track"><div style={{ width: `${item.completion_pct}%` }} /></div><small>{item.completion_pct}%</small></>}</div><div className="history-score">{item.score ? <><b>{item.score}</b><small>score</small></> : item.feedback_rating ? <><b>{'★'.repeat(item.feedback_rating)}</b><small>feedback</small></> : null}</div><StatusBadge status={item.status} /></div>)}</div> : <div className="history-empty">No activities yet. Your completed learning will appear here.</div>}</section>
}

function formatDate(value: string) { return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) }
