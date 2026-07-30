from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from firsat_radari.db.models import DataSource, Entity, EntityExternalId
from firsat_radari.normalization.base import NormalizationValidationError


def get_or_create_entity(
    session: Session,
    source: DataSource,
    *,
    entity_type: str,
    external_type: str,
    external_id: str,
    canonical_name: str,
    canonical_url: str | None,
    observed_at: datetime,
    existing_entity: Entity | None = None,
) -> Entity:
    external_mapping = session.scalar(
        select(EntityExternalId).where(
            EntityExternalId.source_id == source.id,
            EntityExternalId.external_type == external_type,
            EntityExternalId.external_id == external_id,
        )
    )
    if external_mapping is not None:
        entity = session.get(Entity, external_mapping.entity_id)
        if entity is None:
            raise NormalizationValidationError("entity_mapping_target_missing")
        if entity.entity_type != entity_type:
            raise NormalizationValidationError("entity_mapping_type_mismatch")
        external_mapping.last_seen_at = observed_at
        external_mapping.external_url = canonical_url
        return entity

    entity = existing_entity
    if entity is None:
        entity = Entity(
            entity_type=entity_type,
            canonical_name=canonical_name,
            canonical_url=canonical_url,
            status="active",
        )
        session.add(entity)
        session.flush()
    session.add(
        EntityExternalId(
            entity_id=entity.id,
            source_id=source.id,
            external_type=external_type,
            external_id=external_id,
            external_url=canonical_url,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
        )
    )
    return entity
