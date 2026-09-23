import { achievementDefinitions } from '../../gamification/achievements'
import './gamification.css'

function AchievementArt({ icon }: { icon: 'sprout' | 'medal' }) {
  return <svg width="52" height="52" viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
    {icon === 'sprout' ? <>
      <circle cx="32" cy="32" r="28" fill="currentColor" opacity=".09" />
      <path d="M32 48V31" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <path d="M32 35C16 36 14 25 16 20c12-1 18 5 16 15Z" fill="currentColor" opacity=".35" />
      <path d="M32 29C32 15 43 12 49 15c0 12-6 18-17 14Z" fill="currentColor" />
      <path d="m32 34-8-7m8 1 8-7M22 49h20" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </> : <>
      <path d="m22 40-4 18 14-7 14 7-4-18" fill="currentColor" opacity=".3" />
      <circle cx="32" cy="28" r="21" fill="currentColor" opacity=".14" />
      <circle cx="32" cy="28" r="16" stroke="currentColor" strokeWidth="2.5" />
      <path d="m32 16 3.5 7.5 8.2 1.1-5.9 5.8 1.4 8.2-7.2-3.9-7.2 3.9 1.4-8.2-5.9-5.8 8.2-1.1Z" fill="currentColor" />
    </>}
  </svg>
}

export function Achievements({ count }: { count: number }) {
  const earnedCount = achievementDefinitions.filter(badge => count >= badge.threshold).length
  return <section className="card achievements" aria-labelledby="achievements-title">
    <div className="achievement-heading">
      <div><div className="section-kicker">SMALL STEPS, REAL GROWTH</div><h2 id="achievements-title">Your achievements</h2></div>
      <span className="achievement-total">{earnedCount} / 2 earned</span>
    </div>
    <div className="achievement-grid">
      {achievementDefinitions.map(badge => {
        const earned = count >= badge.threshold
        return <div key={badge.id} className={'achievement-tile ' + (earned ? 'is-earned' : 'is-locked')} data-testid={badge.id}>
          <div className="achievement-art"><AchievementArt icon={badge.icon} /></div>
          <div className="achievement-copy"><h3>{badge.name}</h3><p>{badge.detail}</p>
            <span className="achievement-state">{earned ? '✓ Earned' : Math.min(count, badge.threshold) + '/' + badge.threshold + ' completed'}</span>
          </div>
        </div>
      })}
    </div>
    <p className="achievement-footnote">Celebrating completed development activities. Required HR training is not counted.</p>
  </section>
}
