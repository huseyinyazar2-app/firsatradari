import asyncio

from firsat_radari.connectors.github import GitHubConnector
from firsat_radari.connectors.npm import NpmConnector


async def main() -> None:
    github = GitHubConnector()
    npm = NpmConnector()
    try:
        github_result = await github.discover(
            {
                "q": "topic:testing stars:100..5000 archived:false",
                "per_page": 1,
            }
        )
        npm_result = await npm.discover({"text": "observability", "size": 1})
        print(
            "github",
            github_result.status,
            len(github_result.items),
            github_result.is_complete,
            github_result.rate_limit_remaining,
        )
        print(
            "npm",
            npm_result.status,
            len(npm_result.items),
            npm_result.is_complete,
        )
    finally:
        await github.aclose()
        await npm.aclose()


if __name__ == "__main__":
    asyncio.run(main())

