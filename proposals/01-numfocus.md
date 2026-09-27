# Proposal 1 — NumFOCUS Small Grants

**Applicant:** Jeremy Beebe (forkling maintainers)
**Project:** forkling — Version-Control-Native Evolution for Self-Improving Code Agents
**Amount requested:** $5,000
**Submission target:** NumFOCUS Small Grants Program
**Application URL:** https://numfocus.org/programs/small-grants

---

## One-line pitch

forkling turns git into an evolutionary substrate for AI agents — every commit is a generation, the test suite is the fitness function, and the entire evolutionary history is auditable.

## Why NumFOCUS?

forkling is a stdlib-only Python project (zero third-party deps), MIT-licensed, and ships with a 50-test pytest suite. It is the kind of project NumFOCUS exists to support: open-source scientific infrastructure that anyone with Python ≥ 3.9 can run, including on low-memory hardware.

## What we will do with $5,000

| Item | $ | Notes |
|---|---|---|
| Raspberry Pi Zero + 32 GB SD + USB power | $30 | for sovereign-mode testing |
| Domain + hosting (1 yr) | $50 | for the public evolutionary history dataset |
| Coffee (engineer fuel, ~3 mo) | $500 | |
| Travel to one Python conference | $1,500 | PyCon US 2027 or EuroPython 2027 |
| CI compute credits (GitHub Actions) | $200 | for the forkling CI loop |
| Open-source maintainer stipend | $2,500 | partial; matches half-time focus |
| Buffer | $220 | |
| **Total** | **$5,000** | |

## Why we are fundable

1. **Public ledger.** Every capability forkling demonstrates is recorded in a SHA-256-chained append-only log (`forkling verify`). This is verifiable evidence of impact, not self-reported metrics.
2. **Public evolutionary history.** The entire evolution of the agent is in `git log`. Anyone can clone, replay, or fork.
3. **Reproducibility.** `python -m forkling doctor && python -m forkling verify` is the entire setup. No proprietary models, no paid APIs.
4. **Python ecosystem fit.** Pure stdlib + pytest. Anyone teaching Python can use forkling as a teaching example of Plan-Act-Reflect agents.
5. **Already shipped.** v0.2 is committed, tested, and self-improving.

## Deliverables

- v1.0 release with phylogenetic-replay module on real hardware.
- Public dataset of N ≥ 30 generations of forkling's evolution as a single git repository.
- A PyCon talk / workshop titled "Build your own self-improving AI agent in 200 lines of Python."
- A NumFOCUS blog post on how to reproduce forkling's setup.

## Evidence of impact

- **50 tests passing** on Python 3.9-3.13.
- **Capability ledger** with verified SHA-256 chain (`forkling verify` returns `ok: true`).
- **A/B lineage primitive** for controlled selection-pressure experiments.
- **No paid API dependencies** — the agent is sovereign-mode by default.

## Open source license

MIT. All code, data, and artifacts produced under this grant will be MIT-licensed.

## Timeline

| Month | Milestone |
|---|---|
| 1 | Sovereign-mode tested on Pi Zero; commit history preserved |
| 2 | A/B lineages with statistical comparison; fitness-trajectory paper draft |
| 3 | Public evolutionary dataset released; PyCon talk proposal submitted |
| 4 | v1.0 tagged; NumFOCUS blog post published |

## Closing

forkling is the smallest possible self-improving agent that closes the loop end-to-end. We're not building a framework — we're showing the substrate. NumFOCUS is the right partner because reproducibility is the project's foundational value, and that's exactly what NumFOCUS rewards.

— Jeremy Beebe & forkling

---

## Update (2026-09-27): rigor additions since this draft

**Pre-registration discipline in practice.** Four pre-registered
experiments (exp001–003 + the deferred exp004) have now run on
the FORKLAND-BENCH-001 / FORKLAND-BENCH-002 frozen benchmarks, with
hypotheses, models, and stopping rules committed before any
pilot data was viewed. After exp003, a self-audit
([`paper/hypothesis_v4r1.md` §0](../paper/hypothesis_v4r1.md))
surfaced five real measurement-failure modes in the original
harness, leading to a re-registration (`paper/hypothesis_v4r1.md`,
"r1") and a protocol-2 rewrite (`forkling/experiment2.py`). We
did not move goalposts; we re-registered. This is the discipline
NumFOCUS rewards.

**exp004 calibration outcome, deferred honestly.** Per v4r1 §6,
`scripts/freeze_bench_002.py` exited 1 because only 3 of 12
candidates passed the pre-registered freeze rule. This is
reported as **"primary question deferred"**, not as a null
([`paper/exp004_results.md`](../paper/exp004_results.md)). A
clean calibration-failure outcome — with parse_ok = 0.82,
infra = 0, harness self-test 14/14 — is exactly the kind of
honest null reporting the proposal's "public ledger" promise
should be measured against.

**Submission checklist (before sending).**

- [ ] Update the "50 tests" line to the current number.
- [ ] Replace `<your-org>` placeholder in the URL with
      `nuerainc` and link to `https://github.com/nuerainc/project-forkling`.
- [ ] Add the `paper/hypothesis_v4r1.md` link to a
      "Methods" subsection (one paragraph framing the
      pre-registration discipline).
- [ ] Run `python -m forkling verify` once to confirm the
      capability ledger's SHA-256 chain is intact, then
      paste the last `chain ok: true` line into the
      evidence-of-impact section.
- [ ] Confirm NumFOCUS submission deadline (not committed
      here; depends on current cycle).
