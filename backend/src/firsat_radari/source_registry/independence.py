import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from firsat_radari.db.models import DataSource, SourceRelationship


@dataclass(frozen=True)
class EvidenceOrigin:
    source_id: uuid.UUID
    entity_id: uuid.UUID
    content_id: uuid.UUID


@dataclass(frozen=True)
class IndependenceAssessment:
    evidence_level: str
    source_count: int
    independence_group_count: int
    verified_independent: bool
    blockers: tuple[str, ...]


def assess_source_independence(
    session: Session,
    origins: list[EvidenceOrigin],
) -> IndependenceAssessment:
    source_ids = {origin.source_id for origin in origins}
    if not source_ids:
        return IndependenceAssessment(
            evidence_level="unknown",
            source_count=0,
            independence_group_count=0,
            verified_independent=False,
            blockers=("no_source_origin",),
        )
    sources = {
        source.id: source
        for source in session.scalars(
            select(DataSource).where(DataSource.id.in_(source_ids))
        )
    }
    if len(sources) != len(source_ids):
        return IndependenceAssessment(
            evidence_level="unknown",
            source_count=len(source_ids),
            independence_group_count=0,
            verified_independent=False,
            blockers=("source_registry_incomplete",),
        )
    independence_groups = {
        source.independence_group_key for source in sources.values()
    }
    if len(source_ids) == 1:
        return IndependenceAssessment(
            evidence_level="E1",
            source_count=1,
            independence_group_count=len(independence_groups),
            verified_independent=False,
            blockers=("single_source",),
        )

    blockers: set[str] = set()
    if len(independence_groups) < 2:
        blockers.add("shared_independence_group")
    for source in sources.values():
        if source.independence_status != "independent":
            blockers.add(
                f"source_status:{source.key}:{source.independence_status}"
            )
    relationships = list(
        session.scalars(
            select(SourceRelationship).where(
                SourceRelationship.status.in_(("candidate", "approved")),
                or_(
                    SourceRelationship.source_id.in_(source_ids),
                    SourceRelationship.related_source_id.in_(source_ids),
                ),
            )
        )
    )
    origins_by_entity: dict[uuid.UUID, set[uuid.UUID]] = {}
    origins_by_content: dict[uuid.UUID, set[uuid.UUID]] = {}
    for origin in origins:
        origins_by_entity.setdefault(origin.entity_id, set()).add(
            origin.source_id
        )
        origins_by_content.setdefault(origin.content_id, set()).add(
            origin.source_id
        )
    for relationship in relationships:
        pair = {relationship.source_id, relationship.related_source_id}
        if not pair <= source_ids or relationship.independence_effect == "none":
            continue
        applies = relationship.scope == "global"
        if relationship.scope == "same_entity":
            applies = any(
                pair <= entity_sources
                for entity_sources in origins_by_entity.values()
            )
        elif relationship.scope == "same_content":
            applies = any(
                pair <= content_sources
                for content_sources in origins_by_content.values()
            )
        if applies:
            blockers.add(
                "relationship:"
                f"{relationship.relationship_type}:"
                f"{relationship.independence_effect}"
            )
    verified_independent = not blockers
    return IndependenceAssessment(
        evidence_level="E2" if verified_independent else "unverified_cross_source",
        source_count=len(source_ids),
        independence_group_count=len(independence_groups),
        verified_independent=verified_independent,
        blockers=tuple(sorted(blockers)),
    )
