from __future__ import annotations

import uuid
from datetime import datetime

import sys
from types import ModuleType, SimpleNamespace


def _install_model_stubs() -> None:
    if 'models' in sys.modules:
        return
    stub = ModuleType('models')

    class _Entity:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    # Provide lightweight stand-ins for the models the meta package expects.
    stub.StoryEntity = _Entity
    stub.Story = SimpleNamespace
    stub.StoryTheme = SimpleNamespace
    stub.StoryEntityOverride = _Entity
    stub.StoryCorpus = SimpleNamespace
    stub.Chapter = SimpleNamespace
    stub.StoryUniverseLink = _Entity
    stub.UniverseCluster = _Entity
    stub.UniverseClusterMembership = _Entity

    sys.modules['models'] = stub


_install_model_stubs()

from meta import EntityOverrideRules, apply_overrides_to_entities


def _entity(name: str, occurrence: int, story_id: uuid.UUID | None = None) -> SimpleNamespace:
    story = story_id or uuid.uuid4()
    return SimpleNamespace(
        story_id=story,
        name=name,
        entity_type="character",
        aliases=None,
        confidence=0.6,
        first_seen_chapter=1,
        last_seen_chapter=3,
        occurrence_count=occurrence,
        metadata={"supporting_chapters": [1, 2, 3]},
        updated_at=datetime.utcnow(),
    )


def test_apply_overrides_merges_and_suppresses() -> None:
    story_id = uuid.uuid4()
    captain = _entity("Captain Voss", 3, story_id)
    alias = _entity("Voss", 2, story_id)
    unwanted = _entity("Background Specter", 1, story_id)

    rules = EntityOverrideRules(
        suppress={"Background Specter"}, merges={"Voss": "Captain Voss"}
    )

    result = apply_overrides_to_entities([captain, alias, unwanted], rules)

    assert len(result) == 1
    merged = result[0]
    assert merged.name == "Captain Voss"
    assert merged.occurrence_count == 5
    assert merged.aliases and "Voss" in merged.aliases and "Captain Voss" in merged.aliases
    assert "Background Specter" not in {entity.name for entity in result}
    assert set(merged.metadata.get("supporting_chapters", [])) == {1, 2, 3}


def test_apply_overrides_without_rules_returns_original() -> None:
    story_id = uuid.uuid4()
    entities = [_entity("Aurora", 2, story_id), _entity("Beacon", 1, story_id)]

    rules = EntityOverrideRules(suppress=set(), merges={})
    result = apply_overrides_to_entities(entities, rules)

    assert len(result) == 2
    names = {entity.name for entity in result}
    assert names == {"Aurora", "Beacon"}
