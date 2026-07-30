from firsat_radari.normalization.base import SnapshotNormalizer
from firsat_radari.normalization.github import GitHubRepositoryNormalizer
from firsat_radari.normalization.github_work_items import (
    GitHubWorkItemNormalizer,
)
from firsat_radari.normalization.npm import NpmPackageNormalizer
from firsat_radari.normalization.stack_exchange import (
    StackExchangeQuestionNormalizer,
)


class NormalizerRegistryError(ValueError):
    pass


def create_normalizer(normalizer_key: str) -> SnapshotNormalizer:
    if normalizer_key == "github":
        return GitHubRepositoryNormalizer()
    if normalizer_key == "github_work_items":
        return GitHubWorkItemNormalizer()
    if normalizer_key == "npm":
        return NpmPackageNormalizer()
    if normalizer_key == "stack_exchange_questions":
        return StackExchangeQuestionNormalizer()
    raise NormalizerRegistryError(f"Unsupported normalizer: {normalizer_key}")
