"""
Cliente fino para a API REST do GitHub.
Responsável apenas por falar com a API — sem lógica de ranking ou análise.
"""
import os
import time
import base64
import requests
from typing import Optional


GITHUB_API = "https://api.github.com"


class GitHubAuthError(Exception):
    """Levantado quando nenhum token do GitHub foi fornecido."""
    pass


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        # Token é OBRIGATÓRIO. Sem ele, o rate limit (60 req/hora) é atingido
        # rapidamente e a análise de feedback falha silenciosamente (README/Issues
        # somem sem aviso, dando a falsa impressão de "projeto sem documentação").
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise GitHubAuthError(
                "Nenhum GitHub token encontrado.\n\n"
                "O meca-repo-finder exige autenticação para funcionar de forma confiável "
                "(sem token, o rate limit de 60 req/hora estoura rápido e a análise "
                "de README/Issues falha sem avisar).\n\n"
                "Como resolver:\n"
                "  1. Crie um token em https://github.com/settings/tokens\n"
                "     (basta um 'fine-grained token' com acesso de leitura pública, "
                "sem nenhuma permissão especial)\n"
                "  2. Exporte-o: export GITHUB_TOKEN=ghp_xxxxxxxxxxxx\n"
                "     ou passe diretamente: --token ghp_xxxxxxxxxxxx\n"
            )
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "meca-repo-finder",
            "Authorization": f"Bearer {self.token}",
        }
        self.session.headers.update(headers)

    def _get(self, url: str, params: Optional[dict] = None, retries: int = 2,
              max_wait: float = 15) -> dict:
        for attempt in range(retries):
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 5))
                wait = max(reset - time.time(), 2)
                if wait > max_wait or attempt == retries - 1:
                    print(f"[rate limit] limite atingido; pulando (use GITHUB_TOKEN para evitar isso)")
                    return {}
                print(f"[rate limit] aguardando {wait:.0f}s...")
                time.sleep(wait)
                continue
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
        return {}

    def search_repositories(self, query: str, sort: str = "stars",
                             order: str = "desc", per_page: int = 30,
                             language: Optional[str] = None,
                             min_stars: Optional[int] = None,
                             pushed_after: Optional[str] = None) -> list[dict]:
        """
        Busca repositórios. `sort` pode ser: stars, forks, updated, best-match (deixe None/omita).
        Filtros extras (language, min_stars, pushed_after) são incorporados na query
        usando a sintaxe de busca do GitHub.
        """
        q_parts = [query]
        if language:
            q_parts.append(f"language:{language}")
        if min_stars:
            q_parts.append(f"stars:>={min_stars}")
        if pushed_after:
            q_parts.append(f"pushed:>={pushed_after}")

        params = {
            "q": " ".join(q_parts),
            "per_page": per_page,
        }
        if sort != "best-match":
            params["sort"] = sort
            params["order"] = order

        data = self._get(f"{GITHUB_API}/search/repositories", params=params)
        return data.get("items", [])

    def get_issues(self, full_name: str, state: str = "open",
                    per_page: int = 20, labels: Optional[str] = None) -> list[dict]:
        """Retorna issues (não-PR) de um repositório."""
        params = {
            "state": state,
            "per_page": per_page,
            "sort": "comments",
            "direction": "desc",
        }
        if labels:
            params["labels"] = labels
        data = self._get(f"{GITHUB_API}/repos/{full_name}/issues", params=params)
        if not isinstance(data, list):
            return []
        # A API de issues também retorna PRs; filtramos fora
        return [i for i in data if "pull_request" not in i]

    def get_readme(self, full_name: str) -> str:
        """Retorna o texto do README decodificado, ou string vazia se não existir."""
        data = self._get(f"{GITHUB_API}/repos/{full_name}/readme")
        if not data or "content" not in data:
            return ""
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        except Exception:
            return ""
