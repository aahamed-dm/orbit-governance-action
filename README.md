# orbit-governance-action

Reusable **composite** GitHub Action (Python) for **Orbit AI Governance** evidence collection.

Remote: https://github.com/aahamed-dm/orbit-governance-action

## What it does

1. Calls hosted **dm-orbit-mcp** `get_capability_context` (MCP URL hardcoded; customers never set Orbit API base URL).
2. Collects **changed files** for the PR/push (capped; never uploads the full repo).
3. Sends changed files + control requirements to the **customer AI gateway** (OpenAI-compatible / LiteLLM).
4. Calls MCP `submit_control_evidence` once per evaluable control (`required` + `recommended`).
5. Fails the job when any **Required** control has `passed=false` (default).

## Install in an agent repo

Repo secrets:

| Secret | Purpose |
|--------|---------|
| `ORBIT_GOVERNANCE_KEY` | Bearer key forwarded to Orbit via MCP |
| `AI_GATEWAY_URL` | LiteLLM / OpenAI-compatible base URL |
| `AI_GATEWAY_API_KEY` | Gateway API key |
| `AI_GATEWAY_MODEL` | Model id accepted by the gateway |

```yaml
name: Orbit governance evidence

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  evidence:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Orbit governance scan
        uses: aahamed-dm/orbit-governance-action@v1
        with:
          orbit_governance_key: ${{ secrets.ORBIT_GOVERNANCE_KEY }}
          ai_gateway_url: ${{ secrets.AI_GATEWAY_URL }}
          ai_gateway_api_key: ${{ secrets.AI_GATEWAY_API_KEY }}
          ai_gateway_model: ${{ secrets.AI_GATEWAY_MODEL }}
```

Pin `@v1` (floating major) or an exact tag like `@v0.3.0`.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `orbit_governance_key` | yes | — | Orbit governance Bearer key |
| `ai_gateway_url` | yes | — | Customer AI gateway base URL |
| `ai_gateway_api_key` | yes | — | Customer gateway key |
| `ai_gateway_model` | yes | — | Model id |
| `fail_on_required` | no | `true` | Fail job if any Required control fails |
| `source` | no | `ci` | `ci` or `local` |

**Not customer inputs:** Orbit API base URL, MCP URL (hardcoded to Cloud Run `/mcp`).

## How the Action runs

Composite Action on the customer runner:

1. `actions/setup-python@v5` (3.12)
2. `pip install` this repo from `${{ github.action_path }}`
3. `python -m orbit_governance_action`

Works on Linux / macOS / Windows runners (no Docker).

## Develop

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Layout

```text
action.yml                         # composite Action entry
pyproject.toml
src/orbit_governance_action/
  config.py                        # hardcoded ORBIT_MCP_URL
  inputs.py                        # INPUT_* env → RunOptions
  models.py                        # pydantic models
  mcp_client.py                    # streamable HTTP MCP
  ai_gateway.py                    # OpenAI-compatible chat.completions
  changed_files.py                 # PR/push change set
  evaluate_controls.py             # gateway prompts + JSON parse
  evidence.py                      # context → submit mapping
  runner.py                        # orchestration
  github_io.py                     # GITHUB_OUTPUT helpers
  __main__.py
tests/
```

## Version tags

```bash
git tag -a v0.3.0 -m "python composite action"
git push origin v0.3.0
git tag -f -a v1 -m "v1 line"
git push origin v1 --force
```
