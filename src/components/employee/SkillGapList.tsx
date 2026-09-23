import type { SkillGap } from '../../api/types'
import { TinyTag } from '../common/Badge'

export function SkillGapList({ skills }: { skills: SkillGap[] }) {
  const visible = skills.filter((skill) => skill.required > 0).sort((a, b) => b.gap - a.gap)
  return <section className="card skill-card-section"><div className="section-heading"><div><div className="section-kicker">SKILL GAPS</div><h2>What will move you forward</h2></div><span className="count-badge">{visible.filter((skill) => skill.gap > 0).length} gaps</span></div><div className="skill-list">{visible.map((skill) => <SkillCard key={skill.skill_id} skill={skill} />)}</div></section>
}

function SkillCard({ skill }: { skill: SkillGap }) {
  const currentWidth = `${(skill.current / 5) * 100}%`
  const requiredWidth = `${(skill.required / 5) * 100}%`
  return <div className={`skill-row ${skill.critical ? 'critical' : ''}`}><div className="skill-title"><strong>{skill.name}</strong>{skill.critical && <TinyTag tone="orange">Critical skill</TinyTag>}</div><div className="skill-bars"><div className="bar-line"><span className="bar-label">Current</span><div className="bar-track"><div className="bar-current" style={{ width: currentWidth }} /></div><b>{skill.current}<small>/5</small></b></div><div className="bar-line"><span className="bar-label">Required</span><div className="bar-track"><div className="bar-required" style={{ width: requiredWidth }} /></div><b>{skill.required}<small>/5</small></b></div></div><div className={`gap-chip ${skill.gap === 0 ? 'gap-zero' : ''}`}>{skill.gap === 0 ? 'On target' : `Gap ${skill.gap}`}</div></div>
}
