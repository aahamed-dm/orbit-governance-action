# orbit-governance-action

Reusable **composite** GitHub Action (Python) for **Orbit AI Governance** evidence collection.

Remote: https://github.com/aahamed-dm/orbit-governance-action

## What it does

1. Calls hosted **dm-orbit-mcp** `health` (optional connectivity check).
2. Collects **changed files** for the PR/push (capped; never uploads the full repo).
3. Calls MCP `validate_changed_files` with that structured payload.
4. **Orbit API** (via MCP) loads customer controls and runs LLM validation — not this Action.
5. Fails the job when any **Required** control has `passed=false` (default).

No Docker image. No binary Action distribution. Public composite + Python source only.

## Install in an agent repo

Repo secrets:

| Secret | Purpose |
|--------|---------|
| `ORBIT_GOVERNANCE_KEY` | Bearer key forwarded to Orbit via MCP |

```yaml
name: Orbit governance evidence

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  evidence:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Orbit governance scan
        uses: aahamed-dm/orbit-governance-action@master
        with:
          orbit_governance_key: ${{ secrets.ORBIT_GOVERNANCE_KEY }}
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `orbit_governance_key` | yes | — | Orbit governance Bearer key |
| `fail_on_required` | no | `true` | Fail job if any Required control fails |
| `source` | no | `ci` | `ci` or `local` |

**Not customer inputs:** Orbit API base URL, MCP URL, AI gateway URL/key/model.

## Layout

```text
action.yml
src/orbit_governance_action/
  config.py          # hardcoded ORBIT_MCP_URL
  inputs.py
  models.py
  mcp_client.py
  changed_files.py
  runner.py
  github_io.py
```
