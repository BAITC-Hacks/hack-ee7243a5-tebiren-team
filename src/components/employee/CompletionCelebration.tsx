import { useEffect, useState } from 'react'
import type { CompletionResult } from '../../api/types'
import { completionFeedback } from '../../gamification/achievements'
import { Check } from '../common/Icons'
import './gamification.css'

export function CompletionCelebration({ result, unlocked }: { result?: CompletionResult; unlocked: string[] }) {
  const [animating, setAnimating] = useState(true)
  useEffect(() => {
    const timer = window.setTimeout(() => setAnimating(false), 1000)
    return () => window.clearTimeout(timer)
  }, [])
  const feedback = completionFeedback(result)
  return <div role="status" aria-atomic="true" className={'completion-celebration ' + (animating ? 'is-celebrating' : '')}>
    <div className="celebration-mark" aria-hidden="true">
      <Check size={23} />
      {animating && <span className="celebration-particles">{Array.from({ length: 8 }, (_, i) => <i key={i} />)}</span>}
    </div>
    <div className="celebration-copy">
      <strong>Activity completed!</strong>
      <p>{feedback.detail}</p>
      {feedback.progress && <p>{feedback.closer && <span className="closer-label">Closer to your goal. </span>}{feedback.progress}</p>}
      {unlocked.length > 0 && <p className="achievement-unlocked">Achievement unlocked: {unlocked.join(' · ')}</p>}
    </div>
  </div>
}
