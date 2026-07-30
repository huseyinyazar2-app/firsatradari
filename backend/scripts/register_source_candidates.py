from sqlalchemy import select

from firsat_radari.db.models import DataSource, SourceRelationship
from firsat_radari.db.session import SessionLocal
from firsat_radari.source_registry.service import (
    SourceCandidate,
    SourceRegistryService,
    SourceRelationshipDeclaration,
)

_CANDIDATES = (
    SourceCandidate(
        key="github",
        source_type="code_host",
        owner="GitHub",
        base_url="https://api.github.com",
        evidence_family_key="developer_repository_activity",
        independence_group_key="github",
        independence_status="conditional",
    ),
    SourceCandidate(
        key="npm",
        source_type="package_registry",
        owner="npm",
        base_url="https://registry.npmjs.org",
        evidence_family_key="package_distribution",
        independence_group_key="npm",
        independence_status="conditional",
    ),
    SourceCandidate(
        key="stack_exchange",
        source_type="technical_q_and_a",
        owner="Stack Exchange, Inc.",
        base_url="https://api.stackexchange.com",
        evidence_family_key="technical_q_and_a",
        independence_group_key="stack_exchange",
        independence_status="conditional",
    ),
)


def main() -> None:
    with SessionLocal() as session:
        registry = SourceRegistryService(session)
        existing_keys = set(session.scalars(select(DataSource.key)))
        for candidate in _CANDIDATES:
            if candidate.key in existing_keys:
                print(f"unchanged: {candidate.key}")
                continue
            registry.register_candidate(candidate)
            print(f"registered candidate: {candidate.key}")
        sources = {
            source.key: source
            for source in session.scalars(
                select(DataSource).where(DataSource.key.in_(("github", "npm")))
            )
        }
        relationship_exists = session.scalar(
            select(SourceRelationship.id).where(
                SourceRelationship.relationship_type
                == "shared_product_identity",
                SourceRelationship.scope == "same_entity",
            )
        )
        if set(sources) == {"github", "npm"} and relationship_exists is None:
            registry.declare_relationship(
                SourceRelationshipDeclaration(
                    source_key="github",
                    related_source_key="npm",
                    relationship_type="shared_product_identity",
                    scope="same_entity",
                    independence_effect="invalidates",
                    reviewer="system-bootstrap",
                    rationale=(
                        "A package and its declared repository can describe "
                        "the same underlying product."
                    ),
                )
            )
            print("registered relationship: github <-> npm")


if __name__ == "__main__":
    main()
