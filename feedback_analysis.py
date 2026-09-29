"""
Análise de "feedback" de um repositório: README (clareza/propósito) + Issues
(reclamações recorrentes, saúde da manutenção).

Esta camada só coleta e resume sinais brutos — a interpretação qualitativa
final (ex: "esse projeto parece mal mantido") é feita pelo agente de IA
que consome esse módulo (Claude Code, Codex, etc.), a partir do resumo
estruturado retornado aqui. Isso evita depender de um modelo de IA
específico dentro do próprio script.
"""
import re
from collections import Counter
from github_client import GitHubClient


# Palavras-chave simples para sinalizar issues problemáticas sem precisar de IA aqui
NEGATIVE_SIGNALS = [
    "broken", "bug", "crash", "fail", "error", "not working", "doesn't work",
    "deprecated", "abandoned", "vulnerability", "security issue", "memory leak",
    "quebrado", "erro", "não funciona", "falha", "abandonado", "vulnerabilidade",
]


def _readme_signals(readme_text: str) -> dict:
    if not readme_text:
        return {
            "has_readme": False,
            "length_chars": 0,
            "has_installation_section": False,
            "has_usage_examples": False,
            "has_badges": False,
        }

    lower = readme_text.lower()
    return {
        "has_readme": True,
        "length_chars": len(readme_text),
        "has_installation_section": bool(re.search(r"#+\s*(install|instalação|setup|getting started)", lower)),
        "has_usage_examples": "```" in readme_text,
        "has_badges": bool(re.search(r"!\[.*?\]\(https?://(img\.shields\.io|badge)", readme_text)),
    }


def _issue_signals(issues: list[dict]) -> dict:
    if not issues:
        return {
            "open_issues_sampled": 0,
            "top_issues": [],
            "negative_keyword_hits": 0,
            "avg_comments": 0,
        }

    negative_hits = 0
    top_issues = []
    total_comments = 0

    for issue in issues:
        title = issue.get("title", "")
        comments = issue.get("comments", 0)
        total_comments += comments

        title_lower = title.lower()
        if any(sig in title_lower for sig in NEGATIVE_SIGNALS):
            negative_hits += 1

        top_issues.append({
            "title": title,
            "comments": comments,
            "url": issue.get("html_url", ""),
            "created_at": issue.get("created_at", ""),
        })

    # já vem ordenado por comments desc do github_client
    top_issues = top_issues[:5]

    return {
        "open_issues_sampled": len(issues),
        "top_issues": top_issues,
        "negative_keyword_hits": negative_hits,
        "avg_comments": round(total_comments / len(issues), 1) if issues else 0,
    }


def analyze_repo_feedback(client: GitHubClient, full_name: str) -> dict:
    """
    Coleta sinais de README e Issues para um único repositório.
    Retorna um dicionário estruturado — não um julgamento final —
    para que o agente de IA que chamou este script possa interpretar.
    """
    readme_text = client.get_readme(full_name)
    issues = client.get_issues(full_name, state="open", per_page=20)

    readme_info = _readme_signals(readme_text)
    issues_info = _issue_signals(issues)

    # Um pequeno resumo textual pronto, útil tanto para humano quanto para IA
    summary_bits = []
    if readme_info["has_readme"]:
        summary_bits.append("possui README")
        if readme_info["has_installation_section"]:
            summary_bits.append("com seção de instalação")
        if readme_info["has_usage_examples"]:
            summary_bits.append("e exemplos de uso")
    else:
        summary_bits.append("SEM README (sinal de alerta)")

    if issues_info["open_issues_sampled"] > 0:
        summary_bits.append(
            f"{issues_info['open_issues_sampled']} issues abertas analisadas, "
            f"{issues_info['negative_keyword_hits']} com sinais negativos no título"
        )
    else:
        summary_bits.append("nenhuma issue aberta encontrada")

    return {
        "full_name": full_name,
        "readme": readme_info,
        "issues": issues_info,
        "summary": "; ".join(summary_bits),
    }
