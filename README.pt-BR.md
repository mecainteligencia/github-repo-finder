# github-repo-finder

🇧🇷 Português | [🇬🇧 English](README.md)

Script Python independente (sem depender de nenhuma IA específica) que busca
repositórios no GitHub, ranqueia por diferentes critérios e, opcionalmente,
analisa README + Issues dos melhores resultados para dar um retrato de
qualidade/manutenção.

Funciona em qualquer lugar que rode Python: linha de comando, Claude Code,
Codex, ou como subprocess dentro de um sistema seu.

## Instalação

```bash
pip install requests
```

**Obrigatório:** crie um GitHub Personal Access Token (não precisa de nenhuma
permissão especial, só leitura pública) e exporte:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx   # ou, se você usa o gh: export GITHUB_TOKEN=$(gh auth token)
```

Ou passe direto na chamada: `--token ghp_xxxxxxxxxxxx`.

O token é exigido porque, sem ele, o rate limit (60 requisições/hora) estoura
rápido — e a análise de README/Issues, que consome 2 requisições extras por
repositório, falhava silenciosamente, reportando "sem README" mesmo quando o
repositório tinha um. Com token: 5.000 requisições/hora.

## Uso — linha de comando

```bash
# Busca simples, ranking balanceado (padrão)
python github_repo_finder.py --query "task manager cli"

# Escolher a estratégia de ranking na hora
python github_repo_finder.py --query "rag pipeline" --rank stars      # mais populares
python github_repo_finder.py --query "rag pipeline" --rank recent     # mais ativos recentemente
python github_repo_finder.py --query "rag pipeline" --rank balanced   # combinação de relevância + estrelas + atividade

# Filtros
python github_repo_finder.py --query "web scraper" --language python --min-stars 100

# Analisar README + Issues dos N melhores (mais lento, usa mais requisições)
python github_repo_finder.py --query "vector database" --analyze-top 5

# Saída em JSON puro, para outro programa consumir
python github_repo_finder.py --query "web scraper" --json
```

## Uso — como ferramenta dentro de um agente de IA (Claude Code, Codex, etc.)

Qualquer agente com acesso a shell pode chamar o script e interpretar a saída
JSON. Fluxo típico:

1. O agente recebe do usuário uma palavra-chave ou descrição livre
   ("preciso de algo pra gerenciar tarefas via terminal")
2. O agente decide os parâmetros (query, rank, filtros) — pode até perguntar
   ao usuário qual critério de ranking usar, já que isso é escolhido na hora
3. O agente roda: `python github_repo_finder.py --query "..." --rank balanced --analyze-top 5 --json`
4. O agente lê o JSON estruturado (incluindo `feedback_analysis` de cada repo)
   e escreve a recomendação final em linguagem natural, citando issues e
   trechos do README como evidência

### Limites de consumo de tokens

Tudo que o script imprime é lido pelo agente e vira tokens. Para evitar gasto
descontrolado:

- **No código:** `--limit` é limitado a 20 e `--analyze-top` a 5. A saída
  máxima fica em torno de 3.500 tokens por busca, e o JSON sai compacto.
- **No agente:** o [AGENTS.md](AGENTS.md) (lido por Codex, Cursor e outros; o
  `CLAUDE.md` aponta para ele) instrui o agente a perguntar antes de buscar:
  tamanho da busca, quantas buscas no máximo e critério de ranking. Ele também
  proíbe o agente de abrir páginas dos repositórios por conta própria.

| Tamanho  | Parâmetros                     | Tokens aprox. |
|----------|--------------------------------|---------------|
| Rápida   | `--limit 5`                    | ~600          |
| Normal   | `--limit 10 --analyze-top 3`   | ~1.800        |
| Completa | `--limit 20 --analyze-top 5`   | ~3.500        |

Os tetos são flexíveis: `--max-limit 50 --max-analyze 10 --limit 50 --analyze-top 10`
libera mais resultados (até 100 listados) ao custo de mais tokens e mais
requisições ao GitHub. Sem essas opções, os tetos padrão continuam valendo.

As regras do agente só valem quando ele é aberto na pasta do repositório.

## Uso — como módulo Python dentro de um sistema

```python
from github_client import GitHubClient
from ranking import apply_ranking
from feedback_analysis import analyze_repo_feedback

client = GitHubClient(token="ghp_...")
repos = client.search_repositories("task manager cli", language="python")
ranked = apply_ranking(repos, strategy="balanced")

top = ranked[:5]
for repo in top:
    feedback = analyze_repo_feedback(client, repo["full_name"])
    print(repo["full_name"], feedback["summary"])
```

## Estrutura dos arquivos

- `github_client.py` — chamadas à API do GitHub (busca, README, issues), com
  retry e tratamento de rate limit
- `ranking.py` — as 3 estratégias de ranking (`stars`, `recent`, `balanced`)
- `feedback_analysis.py` — coleta sinais de README (tem instalação? tem
  exemplos? tem badges?) e de Issues abertas (título com sinais de bug/erro,
  quantidade de comentários = engajamento no problema)
- `github_repo_finder.py` — CLI que amarra tudo, com saída em texto legível ou JSON

## Sobre a "análise de feedback"

O GitHub não tem um sistema de reviews/estrelas de satisfação como uma loja
de apps. Por isso a análise aqui é baseada em dois proxies reais:

- **README**: existe? tem seção de instalação? tem exemplos de código?
  (sinal de projeto bem documentado vs. abandonado)
- **Issues abertas**: quantidade, quais têm mais comentários (= mais gente
  afetada), e se os títulos contêm palavras como "bug", "broken", "não
  funciona", "abandoned" etc.

O script só **coleta e estrutura** esses sinais — a interpretação final
("esse projeto parece bem mantido" ou "tem muita reclamação recorrente")
fica a cargo do agente de IA que consome o JSON, já que isso exige
julgamento contextual que vai além de regex.

## Licença

MIT — veja [LICENSE](LICENSE).
