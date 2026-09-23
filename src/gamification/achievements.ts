import type { CompletionResult, DevelopmentSummary } from '../api/types'

export const achievementDefinitions = [
  { id: 'first-step', name: 'First step', threshold: 1, detail: 'Complete your first development activity.', icon: 'sprout' },
  { id: 'momentum', name: 'Building momentum', threshold: 3, detail: 'Complete 3 different development activities.', icon: 'medal' },
] as const

export function validDevelopmentSummary(value: unknown): value is DevelopmentSummary {
  if (!value || typeof value !== 'object' || !('completed_unique_activities' in value)) return false
  const count = value.completed_unique_activities
  return typeof count === 'number' && Number.isSafeInteger(count) && count >= 0
}

export function unlockedAchievements(before: number | undefined, after: number | undefined): string[] {
  if (before === undefined || after === undefined) return []
  return achievementDefinitions.filter(badge => before < badge.threshold && after >= badge.threshold).map(badge => badge.name)
}

export function completionFeedback(result?: CompletionResult) {
  const improved = result?.updated_skills.filter(skill => skill.after > skill.before) ?? []
  const closer = result?.progress_before != null && result.progress_after != null && result.progress_after > result.progress_before
  return {
    improved,
    closer,
    detail: improved.length
      ? 'Skill improved — ' + improved.map(skill => (skill.skill_name || skill.skill_id) + ': ' + skill.before + ' → ' + skill.after).join('; ')
      : 'Your learning history was updated.',
    progress: result?.progress_before != null && result.progress_after != null
      ? 'Readiness: ' + result.progress_before + '% → ' + result.progress_after + '%.'
      : '',
  }
}

// A cached completion is a historical receipt; only a fresh profile may lower
// the count (e.g. after reset). Missing legacy receipts never mean zero.
export function confirmedCount(current: number, result?: CompletionResult): number {
  return validDevelopmentSummary(result?.development_summary)
    ? Math.max(current, result.development_summary.completed_unique_activities)
    : current
}
