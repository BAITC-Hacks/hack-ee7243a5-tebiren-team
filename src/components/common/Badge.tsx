import type { ActivityStatus } from '../../api/types'

const labels: Record<ActivityStatus, string> = { completed: 'Completed', in_progress: 'In progress', dropped: 'Dropped', no_show: 'No-show', declined: 'Declined', overdue: 'Overdue' }
export function StatusBadge({ status }: { status: ActivityStatus }) { return <span className={`status-badge status-${status}`}><span className="status-dot" />{labels[status]}</span> }
export function TinyTag({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'green' | 'lime' | 'orange' }) { return <span className={`tiny-tag tiny-${tone}`}>{children}</span> }
