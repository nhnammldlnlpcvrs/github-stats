import aiohttp
from collections import defaultdict

class Stats:
    def __init__(
        self,
        user,
        token,
        session: aiohttp.ClientSession,
        exclude_repos=None,
        exclude_langs=None,
        ignore_forked_repos=False,
    ):
        self.user = user
        self.token = token
        self.session = session
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }
        self.exclude_repos = exclude_repos or set()
        self.exclude_langs = exclude_langs or set()
        self.ignore_forked_repos = ignore_forked_repos

    async def _get(self, url):
        async with self.session.get(url, headers=self.headers) as r:
            r.raise_for_status()
            return await r.json()

    @property
    async def name(self):
        data = await self._get(f"https://api.github.com/users/{self.user}")
        return data.get("name") or self.user

    @property
    async def repos(self):
        repos = []
        page = 1
        while True:
            data = await self._get(
                f"https://api.github.com/users/{self.user}/repos?per_page=100&page={page}"
            )
            if not data:
                break
            for repo in data:
                if repo["name"] in self.exclude_repos:
                    continue
                if self.ignore_forked_repos and repo["fork"]:
                    continue
                repos.append(repo)
            page += 1
        return repos

    @property
    async def stargazers(self):
        return sum(r["stargazers_count"] for r in await self.repos)

    @property
    async def forks(self):
        return sum(r["forks_count"] for r in await self.repos)

    @property
    async def total_contributions(self):
        data = await self._get(
            f"https://api.github.com/users/{self.user}/events/public"
        )
        return len(data)

    @property
    async def views(self):
        return 0

    @property
    async def lines_changed(self):
        additions = deletions = 0
        for r in await self.repos:
            stats = await self._get(r["url"])
            additions += stats.get("additions", 0)
            deletions += stats.get("deletions", 0)
        return additions, deletions

    @property
    async def languages(self):
        lang_data = defaultdict(int)
        for r in await self.repos:
            langs = await self._get(r["languages_url"])
            for lang, size in langs.items():
                if lang in self.exclude_langs:
                    continue
                lang_data[lang] += size

        total = sum(lang_data.values()) or 1
        result = {}
        for lang, size in lang_data.items():
            result[lang] = {
                "size": size,
                "prop": size * 100 / total,
                "color": None,
            }
        return result