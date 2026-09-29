# Regras para usar o meca-repo-finder (economia de tokens)

## Antes de qualquer busca, pergunte ao usuário (uma única vez, com a ferramenta de perguntas do agente se houver)

1. **Tamanho da busca**
   - Rápida: `--limit 5`, sem análise (~600 tokens)
   - Normal: `--limit 10 --analyze-top 3` (~1.800 tokens)
   - Completa: `--limit 20 --analyze-top 5` (~3.500 tokens, é o máximo que o script permite)
2. **Quantas buscas no máximo** posso fazer nesta pesquisa: 1, 2 ou 3
3. **Critério de ranking**: balanced (padrão), stars ou recent
4. **Linguagem / estrelas mínimas** (opcional)

Se o usuário já respondeu algo no pedido, não pergunte de novo.

## Durante a pesquisa

- Nunca passe do número de buscas combinado. Se precisar de mais, pare e peça.
- Não abra README, issues ou páginas dos repositórios por conta própria (WebFetch, gh, curl): use só o que o script retorna.
- Use sempre `--json` e rode com `python3 -W ignore meca_repo_finder.py`.
- Ao final, informe quantas buscas foram usadas e uma estimativa de tokens (tamanho da saída ÷ 4).

## Limites flexíveis

O script limita `--limit` a 20 e `--analyze-top` a 5. Só suba esses tetos
(`--max-limit`, `--max-analyze`) se o **usuário pedir explicitamente** um valor
maior. Antes, avise o custo estimado (~150 tokens por repo listado, ~500 por
repo analisado) e confirme.
