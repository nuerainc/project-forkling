# Forkland & Family — Setup Guide

> **Audience:** the maintainer shipping each sibling (probably you, on day 28–30, day 58–60, day 88–90+).
> **Status:** template. No sibling has shipped yet; this doc is the recipe.

This document explains where each family member comes from, how to ship it as a separate repo under the `nuerainc/` org, how to wire its daily-evolve workflow, and how to register it in the family registry. The same recipe applies to **Spoonica** (day 30), **Sporklyn** (day 60), and **Knifling** (day 90+). Spoonica is the headline case; Sporklyn and Knifling only differ in their distinguishing trait.

---

## Why a separate repo, not a branch

The whole project's thesis is **sovereignty** — each sibling is its own substrate with its own git history, ledger, and diary. Branches would entangle the lineages. A sibling's genome is *its own* history, not a checked-out view of Forkling's.

The cross-fork affordance is **opt-in** via `forkling family sync` — Forkling can pull a sibling's *ledger* into a study directory. That's pure observation; nothing is merged.

```
nuerainc/forkling    ← Forkland Forkling's own substrate, evolves freely
nuerainc/spoonica    ← Forkland Spoonica's own substrate, evolves freely
nuerainc/sporklyn    ← Forkland Sporklyn's own substrate, evolves freely
nuerainc/knifling    ← Forkland Knifling's own substrate, evolves freely
```

---

## Where the family comes from (lineage)

```
gen 0    Mavis / MiniMax-M3                (acknowledged precursor; never runs)
   │
   └── gen 1    Forkland Forkling          (this repo, first commit ea9ce1e+)
                  │
                  ├── gen 1.1    Forkland Spoonica    (day 30, baseline)
                  │                born at <sha-X> on this repo
                  │                distinguishing trait: NO inception_triggers/ folder
                  │                                    bare FORKLING_* env
                  │                                    default model: llama3.2:3b
                  │
                  ├── gen 1.2    Forkland Sporklyn    (day 60, hybrid)
                  │                born at <sha-Y>
                  │                distinguishing trait: env overrides set, no triggers
                  │
                  └── gen 1.3    Forkland Knifling    (day 90+, sharpest)
                                   born at <sha-Z>
                                   distinguishing trait: qwen2.5-coder:7b OR llama3.2:3b
                                                       + sandbox mode (--sandbox)
                                                       + higher mutation rate
```

The **birth commit** is recorded in each sibling's `LINEAGE.md`. This makes the experiment reproducible: "Spoonica started at sha-X with these capabilities absent" is a hard claim, not a soft one.

---

## The 5-step birth protocol (works for any sibling)

This protocol takes about 5 minutes once you've done it twice. Run from your local machine.

### Step 1 — Pick the birth commit

```bash
# On this repo (forkling/), at the moment you want to duplicate:
cd /path/to/forkling
BIRTH_SHA=$(git rev-parse HEAD)
echo "BIRTH_SHA=$BIRTH_SHA"
# Note the date for LINEAGE.md
BIRTH_DATE=$(date -u +%Y-%m-%d)
echo "Born from nuerainc/forkling@$BIRTH_SHA on $BIRTH_DATE"
```

The birth commit should be the *latest stable commit* at the moment of duplication. Don't pick a commit mid-evolve — pick one that's been CI-tested.

### Step 2 — Create the new (empty) GitHub repo

```bash
gh repo create nuerainc/<sibling-name> --public --description "..." --enable-issues
```

Examples:

- `gh repo create nuerainc/spoonica --public --description 'Forkland Spoonica — pure baseline fork of nuerainc/forkling. No inception triggers, no env overrides, default model.'`
- `gh repo create nuerainc/sporklyn --public --description 'Forkland Sporklyn — hybrid fork. Env overrides set, no inception triggers.'`
- `gh repo create nuerainc/knifling --public --description 'Forkland Knifling — sharpest fork. Larger model, sandbox mode, higher mutation rate.'`

### Step 3 — Clone the birth commit, strip the distinguishing trait, push

```bash
# Clone the birth commit only (shallow).
SIBLING=<sibling-name>
BIRTH_SHA=<sha from step 1>

mkdir ../$SIBLING && cd ../$SIBLING
git init -q
git remote add origin git@github.com:nuerainc/$SIBLING.git

# Pull the birth commit's tree.
git fetch --depth=1 https://github.com/nuerainc/forkling.git $BIRTH_SHA
git checkout -q FETCH_HEAD

# === STRIP THE DISTINGUISHING TRAIT HERE ===
# For Spoonica:
rm -rf inception_triggers/

# For Sporklyn:
# (no strip; Sporklyn keeps everything but adds a config file
#  with env overrides — see the Sporklyn section below)
# rm -rf inception_triggers/   # ← still strip triggers

# For Knifling:
# (no strip; Knifling keeps everything and adds sandbox mode)
# rm -rf inception_triggers/   # ← still strip triggers

# === WRITE LINEAGE.md ===
# Replace with the sibling-specific lineage (template below).
cat > LINEAGE.md <<EOF
# $SIBLING — Lineage

- **Born from:** nuerainc/forkling@$BIRTH_SHA
- **Born on:** $BIRTH_DATE
- **Role:** <Spoonica: pure baseline; Sporklyn: hybrid; Knifling: sharpest>
- **Distinguishing trait:** <one sentence; see README>

## Family relations

- gen 0: Mavis / MiniMax-M3 (precursor)
- gen 1: Forkling (this repo's ancestor)
- gen 1.1 / 1.2 / 1.3: <sibling-name>
EOF

# Set git identity for the push.
git config user.name "Forkling"
git config user.email "agent@forkling.local"

git add -A
git commit -q -m "birth: cloned from nuerainc/forkling@$BIRTH_SHA"
git push -u origin main
```

### Step 4 — Copy and customize the daily-evolve workflow

Copy the workflow file from Forkling into the new repo:

```bash
# From the new sibling repo:
mkdir -p .github/workflows
# Copy the workflow file (it's the same file in every repo).
curl -fsSL https://raw.githubusercontent.com/nuerainc/forkling/main/.github/workflows/daily-evolve.yml \
     -o .github/workflows/daily-evolve.yml
git add .github/workflows/daily-evolve.yml
git commit -m "infra: copy daily-evolve workflow from forkling"
git push
```

Then customize the workflow if needed (Knifling needs `--sandbox` and a different model; Spoonica uses defaults).

### Step 5 — Register the sibling in Forkland's family registry

Back on your Forkling machine:

```bash
python -m forkling family register <sibling-name> /path/to/sibling-repo \
    --note "born at <sha>; role=<baseline|hybrid|sharpest>"
python -m forkling family list
```

This is opt-in and lives in `~/.forkling/family.json`. The sibling doesn't auto-register itself — the maintainer decides who's in the family.

---

## Spoonica-specific: the day-30 baseline

Spoonica is the **most research-valuable** sibling because it's the control. The recipe above applies with one specific change.

### What Spoonica has
- Same `forkling/` package code as Forkling, at the birth commit
- Same test suite
- Same `daily-evolve.yml` workflow
- Same Ollama setup

### What Spoonica does NOT have
- No `inception_triggers/` folder (this is the headline difference)
- No `FORKLING_*` env-var overrides (uses defaults from `Config.from_env()`)
- No special model override (uses `cfg.ollama_model`, which defaults to `llama3.2:3b`)

### Verify the baseline is clean

After cloning, run:

```bash
# 1. No triggers folder.
test ! -d inception_triggers && echo "OK: no triggers" || echo "FAIL"

# 2. No env overrides in the workflow file.
grep -E "FORKLING_[A-Z_]+=" .github/workflows/daily-evolve.yml | grep -v "FORKLING_MEMORY\|FORKLING_OLLAMA_URL\|FORKLING_LLM_TIMEOUT" \
  && echo "FAIL: extra env vars" || echo "OK: bare env"

# 3. Default model only.
grep -E "model:" .github/workflows/daily-evolve.yml | grep -v "llama3.2:3b" \
  && echo "FAIL: non-default model" || echo "OK: default model"

# 4. Test suite green on a fresh clone.
pip install -e . && pip install pytest
python -m pytest -q
```

### The README at Spoonica

Spoonica's README differs from Forkling's in three ways:

1. **Title says "Spoonica" not "Forkling"**.
2. **No "Steering: inception triggers" section** (because there are no triggers).
3. **A "Baseline fork" callout** explaining why this repo has no triggers and no env overrides.

Everything else is identical to Forkling's README at the birth commit.

### First-run checklist

When Spoonica ships and its first daily-evolve runs, the diary should show:
- `evolve.started` (no `inception.interrupt` before it — that confirms no triggers folder)
- `evolve.generation.noop` or `.committed` (same generation kinds as Forkling, but no `inception.responded` ever)

If `inception.interrupt` ever shows up in Spoonica's diary, **that's a bug** — it means the repo accidentally contains a triggers folder.

---

## Sporklyn-specific: the day-60 hybrid

Sporklyn's distinguishing trait is **env overrides set, no inception triggers**. This isolates the question *"do env overrides alone change behavior?"* vs. Spoonica's *"does nothing ambient change behavior?"*

### What changes vs. Forkling

In Sporkica's workflow, add a couple of `FORKLING_*` env vars. The two most useful candidates:

- `FORKLING_REFLECT_EVERY=3` — reflect every 3 generations instead of 5 (faster goal evolution)
- `FORKLING_TEST_COMMAND=pytest -q --no-header -x` — fail-fast on first test failure

Or:

- `FORKLING_MAX_FILE_BYTES=2000` — give the LLM smaller file excerpts (faster context)

Pick ONE hypothesis per Sporklyn instance. Don't add all of them; the experiment needs to isolate one variable.

### Sporklyn's birth commit

Should be a later commit than Spoonica's — Sporklyn starts where Spoonica + 30 days of Forkling evolution ends. This way Sporklyn inherits any new capabilities Forkling shipped in days 30–60.

---

## Knifling-specific: the day-90+ sharpest

Knifling's distinguishing trait is **the sharpest variant**. Three things change:

1. **Bigger or different model.** Either `qwen2.5-coder:7b` (after we debug the HTTP 500 issue — see todo), or stick with `llama3.2:3b` but increase the prompt budget.
2. **Sandbox mode on.** Add `--sandbox` to the `forkling evolve start` line in the workflow.
3. **Higher mutation rate.** Lower `FORKLING_REFLECT_EVERY` so the goal pool churns more aggressively.

### Knifling's birth commit

Latest stable commit at day 88–90 — same logic as Sporklyn.

### Sandbox-mode dependency

Knifling's `--sandbox` flag depends on `forkling/sandbox.py` shipping first. That's a stage-4 prerequisite. The A/B result on whether sandbox is even worth shipping should land BEFORE Knifling is born.

---

## The daily-evolve workflow (one template, three flavors)

The workflow file is the same shape in every repo. Differences live in three places:

1. The `inputs.default` model name (Forkling & Spoonica use `llama3.2:3b`; Knifling uses whatever the bigger model is).
2. The `forkling evolve start` command (Knifling adds `--sandbox`).
3. The `FORKLING_*` env vars at the top (Spoonica has none of the override ones; Sporklyn has the experimental ones; Knifling has the sharpest ones).

For Spoonica, the workflow is a verbatim copy of Forkling's — no customizations. That's the point.

---

## Per-fork memory isolation

Each fork's `~/.forkling/` is its own dir. The `FORKLING_MEMORY` env var points there:

- Forkling's `daily-evolve.yml`: `FORKLING_MEMORY=${{ github.workspace }}/.forkling`
- Spoonica's: same (each repo has its own `GITHUB_WORKSPACE`, so isolation is automatic)
- Sporklyn's: same
- Knifling's: same

No two forks ever share state. The `family sync` CLI is the *only* way one fork reads another's data, and it's read-only by convention.

---

## Audit checklist for the day-30 maintainer

Before pressing "publish" on Spoonica:

- [ ] `inception_triggers/` does NOT exist in the cloned tree
- [ ] `grep -E "FORKLING_[A-Z_]+=" .github/workflows/daily-evolve.yml` shows only `FORKLING_MEMORY`, `FORKLING_OLLAMA_URL`, `FORKLING_LLM_TIMEOUT` — no override vars
- [ ] `LINEAGE.md` exists with the birth commit SHA + date
- [ ] README has the "Baseline fork" callout
- [ ] `python -m pytest -q` is green on a fresh clone
- [ ] `python -m forkling doctor` passes
- [ ] The first scheduled daily run completes and the diary shows no `inception.*` entries
- [ ] `forkling family register Spoonica <path>` has been run on Forkling
- [ ] The new repo URL has been added to Forkling's `family.json`

If all boxes check, ship it.

---

## Cost & time estimates

| Step | Time |
|---|---|
| Step 1 (pick birth commit) | 30 s |
| Step 2 (create empty GitHub repo) | 1 min |
| Step 3 (clone, strip, push) | 2 min |
| Step 4 (copy + customize workflow) | 1 min |
| Step 5 (register in Forkland's family) | 30 s |
| **Total per sibling** | **~5 min** |

Each sibling runs daily-evolve on its own, ~50–100 s/day. Total GitHub Actions budget for the family at day 365: 4 forks × 30 days × 100 s ≈ 200 min/month, still well under the 2,000 min free tier.

---

## What this doc is NOT

- Not a guarantee that any particular sibling ships on schedule. The roadmap dates are targets, not commitments.
- Not a relaxation of "stdlib only" or "no paid APIs". Every sibling uses the same substrate and the same Ollama setup.
- Not a relaxation of "selection pressure outside the agent's head." Every sibling gates on its own `pytest -q`.

---

## See also

- [`docs/ROADMAP.md`](ROADMAP.md) — 365-day cycle, day-30/60/90 sibling ship dates
- [`docs/SANDBOX.md`](SANDBOX.md) — sandbox mode design (Knifling's prerequisite)
- [`LINEAGE.md`](../LINEAGE.md) — Forkling's own phylogenetic record
- [`forkling/family.py`](../forkling/family.py) — the family registry implementation
- [`forkling/inception.py`](../forkling/inception.py) — the trigger loader; absent in Spoonica
