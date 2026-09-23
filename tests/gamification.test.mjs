import test from 'node:test'
import assert from 'node:assert/strict'
import { achievementDefinitions, completionFeedback, confirmedCount, unlockedAchievements, validDevelopmentSummary } from '../src/gamification/achievements.ts'

for (const [count, earned] of [[0,0], [1,1], [2,1], [3,2], [20,2]]) {
  test('badge thresholds at ' + count, () => {
    assert.equal(achievementDefinitions.filter(badge=>count>=badge.threshold).length, earned)
  })
}

test('new thresholds only; no popups on repeated or unknown counts', () => {
  assert.deepEqual(unlockedAchievements(0,1), ['First step'])
  assert.deepEqual(unlockedAchievements(2,3), ['Building momentum'])
  assert.deepEqual(unlockedAchievements(3,3), [])
  assert.deepEqual(unlockedAchievements(3,1), [])
  assert.deepEqual(unlockedAchievements(undefined,3), [])
  assert.deepEqual(unlockedAchievements(0,undefined), [])
})

test('only positive real skill gains and readiness changes are celebrated', () => {
  const feedback = completionFeedback({
    progress_before: 40, progress_after: 45,
    updated_skills: [
      {skill_id:'A',skill_name:'System Design',before:2,after:3},
      {skill_id:'B',before:4,after:4},
    ],
  })
  assert.equal(feedback.improved.length, 1)
  assert.equal(feedback.closer, true)
  assert.match(feedback.detail, /System Design: 2 → 3/)
  assert.match(feedback.progress, /40% → 45%/)
})

test('no false growth for zero gain or a missing goal', () => {
  for (const [before, after] of [[null,null], [100,100], [60,60], [60,50], [null,50], [50,null]]) {
    const feedback=completionFeedback({progress_before:before,progress_after:after,updated_skills:[]})
    assert.equal(feedback.closer, false)
    assert.doesNotMatch(feedback.detail, /Skill improved/)
  }
  assert.equal(completionFeedback().progress, '')
})

test('missing/invalid summary is not treated as a zero count', () => {
  for (const value of [null, undefined, {}, {completed_unique_activities:-1}, {completed_unique_activities:NaN}, {completed_unique_activities:1.5}, {completed_unique_activities:'3'}]) {
    assert.equal(validDevelopmentSummary(value), false)
  }
  assert.equal(validDevelopmentSummary({completed_unique_activities:0}), true)
})

test('old idempotency receipts cannot roll back currently displayed achievements', () => {
  const receipt=count=>({progress_before:30,progress_after:40,updated_skills:[],development_summary:count===null?null:{completed_unique_activities:count}})
  assert.equal(confirmedCount(3,receipt(1)), 3)
  assert.equal(confirmedCount(3,receipt(null)), 3)
  assert.equal(confirmedCount(3), 3)
  assert.equal(confirmedCount(0,receipt(1)), 1)
})

test('explicit mock preview follows the summary contract and replays safely', async () => {
  const { mockApi } = await import('../src/mock/mockApi.ts')
  const before = await mockApi.getEmployee('E0001')
  assert.equal(before.development_summary.completed_unique_activities, 0)
  const receipt = await mockApi.completeActivity('E0001', 'EV_021', 'preview-test-key')
  assert.equal(receipt.development_summary.completed_unique_activities, 1)
  assert.deepEqual(await mockApi.completeActivity('E0001', 'EV_021', 'preview-test-key'), receipt)
  const after = await mockApi.getEmployee('E0001')
  assert.equal(after.development_summary.completed_unique_activities, 1)
  assert.equal(after.history.filter(row => row.status === 'completed').length, 1)
  assert.equal(after.history[0].date, after.dataset_as_of)
})
