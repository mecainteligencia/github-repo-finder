# github-repo-finder

[🇧🇷 Português](README.pt-BR.md) | 🇬🇧 English

Standalone Python script (no dependency on any specific AI) that searches
GitHub repositories, ranks them by different criteria and, optionally,
analyzes the README and Issues of the top results to give a quick picture of
quality and maintenance.

It runs anywhere Python runs: command line, Claude Code, Codex, or as a
subprocess inside your own system.

## Installation

```bash
pip install requests
```

**Required:** create a GitHub Personal Access Token (no special permissions,
public read-only is enough) and export it:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx   # or, if you use the gh CLI: export GITHUB_TOKEN=$(gh auth token)
```

Or pass it directly: `--token ghp_xxxxxxxxxxxx`.

The token is required because without it the rate limit (60 requests/hour) is
hit quickly, and the README/Issues analysis (2 extra requests per repository)
used to fail silently, reporting "no README" even when one existed. With a
token you get 5,000 requests/hour.

## Usage: command line

```bash
# Simple search, balanced ranking (default)
python github_repo_finder.py --query "task manager cli"

# Pick the ranking strategy on the fly
python github_repo_finder.py --query "rag pipeline" --rank stars      # most popular
python github_repo_finder.py --query "rag pipeline" --rank recent     # most recently active
python github_repo_finder.py --query "rag pipeline" --rank balanced   # relevance + stars + activity

# Filters
python github_repo_finder.py --query "web scraper" --language python --min-stars 100

# Analyze README + Issues of the top N (slower, uses more requests)
python github_repo_finder.py --query "vector database" --analyze-top 5

# Plain JSON output, for another program to consume
python github_repo_finder.py --query "web scraper" --json
```

## Usage: as a tool inside an AI agent (Claude Code, Codex, etc.)

Any agent with shell access can call the script and read the JSON output.
Typical flow:

1. The agent receives a keyword or free-form description from the user
   ("I need something to manage tasks from the terminal")
2. The agent picks the parameters (query, rank, filters), and can ask the user
   which ranking criterion to use
3. The agent runs: `python github_repo_finder.py --query "..." --rank balanced --analyze-top 5 --json`
4. The agent reads the structured JSON (including each repo's
   `feedback_analysis`) and writes the final recommendation in natural
   language, citing issues and README excerpts as evidence

### Token consumption limits

Everything the script prints is read by the agent and becomes tokens. To avoid
runaway costs:

- **In the code:** `--limit` is capped at 20 and `--analyze-top` at 5. Maximum
  output is around 3,500 tokens per search, and the JSON is compact.
- **In the agent:** [AGENTS.md](AGENTS.md) (read by Codex, Cursor and others;
  `CLAUDE.md` points to it) tells the agent to ask before searching: search
  size, maximum number of searches and ranking criterion. It also forbids the
  agent from opening repository pages on its own.

| Size     | Parameters                     | Approx. tokens |
|----------|--------------------------------|----------------|
| Quick    | `--limit 5`                    | ~600           |
| Normal   | `--limit 10 --analyze-top 3`   | ~1,800         |
| Full     | `--limit 20 --analyze-top 5`   | ~3,500         |

The caps are adjustable: `--max-limit 50 --max-analyze 10 --limit 50 --analyze-top 10`
allows more results (up to 100 listed) at the cost of more tokens and more
GitHub requests. Without these options the default caps apply.

The agent rules only apply when the agent is opened in the repository folder.

## Usage: as a Python module

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

## How the search works

The script asks GitHub for the 30 best matches for your query (across the
whole of GitHub, with no date limit unless you use `--pushed-after`), re-ranks
those 30 locally with your chosen strategy, and returns the top `--limit`.
Only repositories within GitHub's first 30 matches can appear, so use
`--language` and `--min-stars` (applied by GitHub before picking) or different
keywords to surface other projects.

## Files

- `github_client.py`: GitHub API calls (search, README, issues), with retry and
  rate-limit handling
- `ranking.py`: the 3 ranking strategies (`stars`, `recent`, `balanced`)
- `feedback_analysis.py`: collects README signals (installation section?
  examples? badges?) and open-Issue signals (bug/error words in titles,
  comment count as a proxy for how many people are affected)
- `github_repo_finder.py`: the CLI that ties everything together, with
  human-readable or JSON output

## About the "feedback analysis"

GitHub has no review/satisfaction rating system like an app store, so the
analysis relies on two real proxies:

- **README**: does it exist? Installation section? Code examples? (well
  documented vs. abandoned)
- **Open Issues**: how many, which have the most comments (more people
  affected), and whether titles contain words like "bug", "broken",
  "not working", "abandoned", etc.

The script only **collects and structures** these signals. The final judgment
("this project looks well maintained" or "lots of recurring complaints") is
left to the AI agent consuming the JSON, since it needs contextual reasoning
beyond regex.

## License

MIT, see [LICENSE](LICENSE).
