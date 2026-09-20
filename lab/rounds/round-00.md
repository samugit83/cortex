# Round 0 — install Cortex in the lab, as a new user would

Everything here happens in a **terminal**. It takes about five minutes.

## 0.1 A fixed Claude Code CLI for the sweeps

Cortex's sweeps run `claude -p` headless, so `claude` must be on your PATH. Yours lives
inside the VS Code extension, which auto-updates, and Cortex refuses a sweep whose CLI
version changed half-way (loading rules can differ). So pin one copy for the whole lab:

```bash
mkdir -p ~/.local/opt/claude-lab
cp ~/.vscode/extensions/anthropic.claude-code-2.1.278-linux-x64/resources/native-binary/claude \
   ~/.local/opt/claude-lab/claude
ln -sf ~/.local/opt/claude-lab/claude ~/.local/bin/claude
claude --version            # 2.1.278 (Claude Code)
```

(If the extension folder has a newer version by now, use that one. Just use the same copy
for the whole lab.)

## 0.2 The lab helper

```bash
ln -sf "/home/samuele/Progetti didattici/Cortex/lab/bin/lab" ~/.local/bin/lab
lab status                  # ten rounds, nothing done yet
```

## 0.3 Install Cortex into the repository

This is exactly what Cortex's README tells a new user to do:

```bash
cd "/home/samuele/Progetti didattici/cortex-lab"
cortex doctor               # every tool found, version >= 2.1.276
cortex init
```

`cortex init` adds `.evolve/`, the three commands in `.claude/commands/`, an empty
`.claude/rules/`, a minimal `CLAUDE.md`, and two `.gitignore` lines.

## 0.4 Configure four settings

Open `.evolve/config.yaml` and change these, or paste the block below:

| Setting | From | To | Why |
|---|---|---|---|
| `baseline.model` | `""` | `claude-haiku-4-5-20251001` | rollouts use the same model as your sessions |
| `measurement.max_runs_per_cycle` | 60 | 200 | the confirm sweep grows to 26 tasks × 3 × 2 = 156 rollouts |
| `collection.stop_after_barren_cycles` | 2 | 3 | the lab introduces themes on a schedule; two quiet rounds in a row are expected |
| `environment.rollout_env` | — | add `DISABLE_AUTOUPDATER: "1"` | the pinned CLI must never update itself |

```bash
cd "/home/samuele/Progetti didattici/cortex-lab"
sed -i 's/model: ""  /model: claude-haiku-4-5-20251001  /' .evolve/config.yaml
sed -i 's/max_runs_per_cycle: 60 /max_runs_per_cycle: 200 /' .evolve/config.yaml
sed -i 's/stop_after_barren_cycles: 2 /stop_after_barren_cycles: 3 /' .evolve/config.yaml
sed -i 's/^    PYTHONDONTWRITEBYTECODE: "1"$/&\n    DISABLE_AUTOUPDATER: "1"/' .evolve/config.yaml
cortex config --check       # config.yaml is valid
grep -n 'claude-haiku\|max_runs_per_cycle\|stop_after_barren\|DISABLE_AUTOUPDATER' .evolve/config.yaml
```

The `grep` must print four lines.

## 0.5 Commit the installation

```bash
git add -A && git commit -m "Install Cortex"
cortex status
```

## 0.6 Pin Haiku 4.5 for the lab's chats

So no chat can run on your default model (Opus) by mistake, the lab's project settings pin
the model. Every Claude Code chat opened in `cortex-lab` then uses Haiku 4.5; project
settings override your user default only in this repository:

```bash
cd "/home/samuele/Progetti didattici/cortex-lab"
python3 - <<'EOF'
import json
p = ".claude/settings.json"; d = json.load(open(p))
open(p, "w").write(json.dumps({"model": "claude-haiku-4-5-20251001", **d}, indent=2) + "\n")
EOF
git add -A && git commit -m "Configure Cortex and Claude Code for the lab (Haiku 4.5)"
```

(Done on 2026-09-19 as commit `ab099a8`, together with the config from 0.4.)

## 0.7 Claude Code in the lab

Open `cortex-lab` in VS Code (**File → Open Folder**). If it was already open, reload the
window (**Ctrl+Shift+P → Developer: Reload Window**) so the new settings are read.

Open the Claude Code panel and start a new chat. These go in the **chat box**, never the
terminal:
- `/model` shows the current model: it must be **Haiku 4.5**;
- typing `/` lists commands: `/harvest`, `/evolve` and `/prune` must be there.

---

**Then tell me "round 0 done".** I check the installation (doctor, config, the commands,
CLAUDE.md) before round 1.
