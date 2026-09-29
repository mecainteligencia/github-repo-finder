"""
Estratégias de ranking para repositórios do GitHub.
Cada estratégia recebe a lista de repositórios (formato bruto da API de busca)
e devolve a mesma lista ordenada, com um campo extra "_score" e "_score_reason".
"""
from datetime import datetime, timezone


def _days_since(date_str: str) -> float:
    if not date_str:
        return 9999
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def rank_stars(repos: list[dict]) -> list[dict]:
    """Ordena puramente por popularidade (estrelas)."""
    for r in repos:
        r["_score"] = r.get("stargazers_count", 0)
        r["_score_reason"] = f"{r.get('stargazers_count', 0)} estrelas"
    return sorted(repos, key=lambda r: r["_score"], reverse=True)


def rank_recent(repos: list[dict]) -> list[dict]:
    """Ordena por atividade recente (último push), com estrelas como desempate leve."""
    for r in repos:
        days = _days_since(r.get("pushed_at", ""))
        # score maior = mais recente. Normaliza para uma escala legível.
        r["_score"] = max(0, 1000 - days) + min(r.get("stargazers_count", 0), 500) / 50
        r["_score_reason"] = f"último commit há {int(days)} dias"
    return sorted(repos, key=lambda r: r["_score"], reverse=True)


def rank_balanced(repos: list[dict]) -> list[dict]:
    """
    Combina relevância (posição original da busca = relevância textual),
    popularidade (estrelas, em log para não deixar mega-projetos dominarem)
    e recência (atividade nos últimos ~180 dias pesa mais).
    """
    import math
    n = len(repos)
    for idx, r in enumerate(repos):
        relevance_score = (n - idx) / n  # 1.0 para o 1º resultado da busca, decrescendo
        stars = r.get("stargazers_count", 0)
        popularity_score = math.log10(stars + 1) / 5  # normaliza escala log
        days = _days_since(r.get("pushed_at", ""))
        recency_score = max(0, 1 - days / 365)  # 1.0 se hoje, 0 se > 1 ano

        score = (relevance_score * 0.35) + (popularity_score * 0.35) + (recency_score * 0.30)
        r["_score"] = round(score, 4)
        r["_score_reason"] = (
            f"relevância={relevance_score:.2f}, "
            f"popularidade={popularity_score:.2f} ({stars}★), "
            f"recência={recency_score:.2f} ({int(days)}d atrás)"
        )
    return sorted(repos, key=lambda r: r["_score"], reverse=True)


STRATEGIES = {
    "stars": rank_stars,
    "recent": rank_recent,
    "balanced": rank_balanced,
}


def apply_ranking(repos: list[dict], strategy: str) -> list[dict]:
    if strategy not in STRATEGIES:
        raise ValueError(f"Estratégia inválida: {strategy}. Use uma de: {list(STRATEGIES)}")
    return STRATEGIES[strategy](repos)
