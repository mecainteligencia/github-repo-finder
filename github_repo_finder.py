#!/usr/bin/env python3
"""
github-repo-finder: agente de busca de repositórios GitHub.

Uso básico:
    python github_repo_finder.py --query "task manager cli" --rank balanced

Com filtros:
    python github_repo_finder.py --query "rag pipeline" --rank recent --language python --min-stars 50

Com análise de feedback (README + Issues) nos top resultados:
    python github_repo_finder.py --query "vector database" --rank balanced --analyze-top 5

Saída em JSON puro (para outro sistema consumir):
    python github_repo_finder.py --query "web scraper" --rank stars --json

Autenticação (recomendado, evita rate limit):
    export GITHUB_TOKEN=ghp_xxx
"""
import argparse
import json
import sys

from github_client import GitHubClient, GitHubAuthError
from ranking import apply_ranking, STRATEGIES
from feedback_analysis import analyze_repo_feedback


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="github-repo-finder", description="github-repo-finder: agente de busca de repositórios GitHub")
    parser.add_argument("--query", "-q", required=True, help="Palavra-chave ou descrição do que procurar")
    parser.add_argument("--rank", "-r", choices=list(STRATEGIES.keys()), default="balanced",
                         help="Estratégia de ranking: stars, recent ou balanced (padrão: balanced)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Quantos repositórios retornar (padrão: 10)")
    parser.add_argument("--language", help="Filtrar por linguagem (ex: python, javascript)")
    parser.add_argument("--min-stars", type=int, help="Filtrar por número mínimo de estrelas")
    parser.add_argument("--pushed-after", help="Filtrar por atividade após esta data (YYYY-MM-DD)")
    parser.add_argument("--analyze-top", type=int, default=0,
                         help="Rodar análise de feedback (README + Issues) nos N primeiros resultados")
    parser.add_argument("--max-limit", type=int, default=20,
                         help="Teto para --limit (padrão: 20, máximo absoluto: 100). Suba só se quiser mais tokens de saída")
    parser.add_argument("--max-analyze", type=int, default=5,
                         help="Teto para --analyze-top (padrão: 5). Cada repo analisado custa ~2 requisições e mais tokens")
    parser.add_argument("--json", action="store_true", help="Saída em JSON puro (sem formatação de texto)")
    parser.add_argument("--token", help="GitHub token (ou use a variável de ambiente GITHUB_TOKEN)")
    return parser


def run(args) -> dict:
    # tetos padrão para não estourar tokens; o usuário pode subir com --max-limit / --max-analyze
    args.limit = min(args.limit, args.max_limit, 100)  # 100 = máximo por página da API do GitHub
    args.analyze_top = min(args.analyze_top, args.max_analyze)
    client = GitHubClient(token=args.token)

    raw_results = client.search_repositories(
        query=args.query,
        sort="best-match",  # deixamos o ranking real por conta das nossas estratégias
        language=args.language,
        min_stars=args.min_stars,
        pushed_after=args.pushed_after,
        per_page=max(30, args.limit),
    )

    if not raw_results:
        return {"query": args.query, "rank_strategy": args.rank, "results": [], "message": "Nenhum repositório encontrado."}

    ranked = apply_ranking(raw_results, args.rank)[: args.limit]

    results = []
    for r in ranked:
        entry = {
            "full_name": r.get("full_name"),
            "description": r.get("description"),
            "url": r.get("html_url"),
            "stars": r.get("stargazers_count"),
            "forks": r.get("forks_count"),
            "language": r.get("language"),
            "last_push": r.get("pushed_at"),
            "open_issues_count": r.get("open_issues_count"),
            "license": (r.get("license") or {}).get("spdx_id"),
            "score": r.get("_score"),
            "score_reason": r.get("_score_reason"),
        }
        results.append(entry)

    # Análise de feedback só nos top N pedidos (é custoso em chamadas de API)
    if args.analyze_top > 0:
        for entry in results[: args.analyze_top]:
            feedback = analyze_repo_feedback(client, entry["full_name"])
            entry["feedback_analysis"] = feedback

    return {
        "query": args.query,
        "rank_strategy": args.rank,
        "filters": {
            "language": args.language,
            "min_stars": args.min_stars,
            "pushed_after": args.pushed_after,
        },
        "results": results,
    }


def print_human(output: dict) -> None:
    print(f"\nBusca: \"{output['query']}\"  |  Ranking: {output['rank_strategy']}\n")
    if not output["results"]:
        print(output.get("message", "Sem resultados."))
        return

    for i, r in enumerate(output["results"], 1):
        print(f"{i}. {r['full_name']}  ⭐ {r['stars']}  ({r['language'] or '?'})")
        print(f"   {r['description'] or '(sem descrição)'}")
        print(f"   {r['url']}")
        print(f"   score: {r['score']} — {r['score_reason']}")
        if "feedback_analysis" in r:
            fb = r["feedback_analysis"]
            print(f"   feedback: {fb['summary']}")
            for issue in fb["issues"]["top_issues"][:3]:
                print(f"      - issue: \"{issue['title']}\" ({issue['comments']} comentários) {issue['url']}")
        print()


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        output = run(args)
    except GitHubAuthError as e:
        if args.json:
            print(json.dumps({"error": "auth_required", "message": str(e)}, ensure_ascii=False))
        else:
            print(f"\n❌ {e}")
        return 1

    if args.json:
        print(json.dumps(output, ensure_ascii=False))
    else:
        print_human(output)


if __name__ == "__main__":
    sys.exit(main())
