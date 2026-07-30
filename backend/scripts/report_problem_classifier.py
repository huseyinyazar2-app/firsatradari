import json
from collections import Counter

from sqlalchemy import exists, select

from firsat_radari.db.models import (
    Entity,
    NormalizedDocument,
    ProblemEvidence,
    ProblemExtractionRecord,
)
from firsat_radari.db.session import SessionLocal
from firsat_radari.problem_mining.github import (
    EXTRACTOR_KEY,
    EXTRACTOR_VERSION,
)


def main() -> None:
    with SessionLocal() as session:
        problem_exists = exists().where(
            ProblemEvidence.extraction_record_id
            == ProblemExtractionRecord.id,
            ProblemEvidence.evidence_type == "problem_report",
        )
        rows = list(
            session.execute(
                select(
                    NormalizedDocument.title,
                    NormalizedDocument.canonical_url,
                    Entity.canonical_name,
                    problem_exists.label("is_problem"),
                )
                .join(
                    ProblemExtractionRecord,
                    ProblemExtractionRecord.document_id
                    == NormalizedDocument.id,
                )
                .join(Entity, Entity.id == NormalizedDocument.entity_id)
                .where(
                    ProblemExtractionRecord.extractor_key == EXTRACTOR_KEY,
                    ProblemExtractionRecord.extractor_version
                    == EXTRACTOR_VERSION,
                    ProblemExtractionRecord.status == "succeeded",
                )
                .order_by(
                    Entity.canonical_name,
                    NormalizedDocument.canonical_url,
                )
            )
        )
        positives = [row for row in rows if row.is_problem]
        negatives = [row for row in rows if not row.is_problem]
        by_entity = Counter(row.canonical_name for row in positives)
        report = {
            "extractor": {
                "key": EXTRACTOR_KEY,
                "version": EXTRACTOR_VERSION,
            },
            "processed_count": len(rows),
            "problem_report_count": len(positives),
            "non_problem_count": len(negatives),
            "detected_rate": (
                round(len(positives) / len(rows), 6) if rows else None
            ),
            "problem_reports_by_entity": dict(by_entity.most_common()),
            "review_sample": {
                "positive": [_sample(row) for row in positives[:10]],
                "negative": [_sample(row) for row in negatives[:10]],
            },
            "ground_truth_status": "not_labeled",
            "precision_recall_status": "unavailable_until_review",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))


def _sample(row) -> dict:
    return {
        "entity": row.canonical_name,
        "title": row.title,
        "url": row.canonical_url,
    }


if __name__ == "__main__":
    main()
