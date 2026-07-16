# macetenth-plugins

A Claude Code plugin marketplace.

## Plugins

### [token-efficient-scripts](plugins/token-efficient-scripts)
Write throwaway bash/python for one-off file & data tasks so they cost minimal tokens and run fast — with a `/bench` command and a benchmark that logs its own findings.

## Install

```
/plugin marketplace add MaceTenth/token-efficient-scripts
/plugin install token-efficient-scripts@macetenth-plugins
```

## Repo layout

```
.claude-plugin/marketplace.json      # marketplace manifest
plugins/token-efficient-scripts/     # the plugin (skill + command + hook + benchmark)
slide.html                           # one-slide explainer of the skill
```

The plugin's `SKILL.md` is the single source of truth. Weekly re-benchmark findings are appended to
`plugins/token-efficient-scripts/skills/token-efficient-scripts/references/benchmark-findings.md`.
