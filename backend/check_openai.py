"""Opt-in live check. Uses environment/.env credentials, never prints secrets."""
import json
import time
from pathlib import Path

from app.config import openai_enabled
from app.data_loader import load_dataset
from app.recommendation.engine import recommendations
from app.services.runtime_state import RuntimeState


def main():
    if not openai_enabled():
        raise SystemExit('Set OPENAI_API_KEY and OPENAI_MODEL on the backend first.')
    state = RuntimeState(load_dataset(Path(__file__).parent / 'data'))
    baseline = recommendations(state, 'E0002', enrich_explanations=False)
    start = time.monotonic()
    result = recommendations(state, 'E0002')
    elapsed = time.monotonic() - start
    for expected, actual in zip(baseline['recommendations'], result['recommendations'], strict=True):
        for field in ('event_id', 'rank', 'score', 'skill_impacts', 'evidence', 'reasons'):
            assert actual[field] == expected[field], field
    sources = [r['explanation_source'] for r in result['recommendations']]
    print(json.dumps({'seconds': round(elapsed, 3), 'sources': sources, 'ranking_and_facts_unchanged': True}))
    if not sources or any(source != 'openai' for source in sources):
        raise SystemExit('Live OpenAI response was not verified; deterministic fallback remained available.')
    if elapsed >= 9:
        raise SystemExit('Live response exceeded the 9 second backend budget.')


if __name__ == '__main__':
    main()
