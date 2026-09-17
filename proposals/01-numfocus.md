# Proposal 1 — NumFOCUS Small Grants

**Applicant:** Jeremy Beebe (forkland maintainers)
**Project:** forkland — Version-Control-Native Evolution for Self-Improving Code Agents
**Amount requested:** $5,000
**Submission target:** NumFOCUS Small Grants Program
**Application URL:** https://numfocus.org/programs/small-grants

---

## One-line pitch

forkland turns git into an evolutionary substrate for AI agents — every commit is a generation, the test suite is the fitness function, and the entire evolutionary history is auditable.

## Why NumFOCUS?

forkland is a stdlib-only Python project (zero third-party deps), MIT-licensed, and ships with a 50-test pytest suite. It is the kind of project NumFOCUS exists to support: open-source scientific infrastructure that anyone with Python ≥ 3.9 can run, including on low-memory hardware.

## What we will do with $5,000

| Item | $ | Notes |
|---|---|---|
| Raspberry Pi Zero + 32 GB SD + USB power | $30 | for sovereign-mode testing |
| Domain + hosting (1 yr) | $50 | for the public evolutionary history dataset |
| Coffee (engineer fuel, ~3 mo) | $500 | |
| Travel to one Python conference | $1,500 | PyCon US 2027 or EuroPython 2027 |
| CI compute credits (GitHub Actions) | $200 | for the dogfood CI loop |
| Open-source maintainer stipend | $2,500 | partial; matches half-time focus |
| Buffer | $220 | |
| **Total** | **$5,000** | |

## Why we are fundable

1. **Public ledger.** Every capability forkland demonstrates is recorded in a SHA-256-chained append-only log (`forkling verify`). This is verifiable evidence of impact, not self-reported metrics.
2. **Public evolutionary history.** The entire evolution of the agent is in `git log`. Anyone can clone, replay, or fork.
3. **Reproducibility.** `python -m forkling doctor && python -m forkling verify` is the entire setup. No proprietary models, no paid APIs.
4. **Python ecosystem fit.** Pure stdlib + pytest. Anyone teaching Python can use forkland as a teaching example of Plan-Act-Reflect agents.
5. **Already shipped.** v0.2 is committed, tested, and self-improving.

## Deliverables

- v1.0 release with phylogenetic-replay module on real hardware.
- Public dataset of N ≥ 30 generations of forkland's evolution as a single git repository.
- A PyCon talk / workshop titled "Build your own self-improving AI agent in 200 lines of Python."
- A NumFOCUS blog post on how to reproduce forkland's setup.

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

forkland is the smallest possible self-improving agent that closes the loop end-to-end. We're not building a framework — we're showing the substrate. NumFOCUS is the right partner because reproducibility is the project's foundational value, and that's exactly what NumFOCUS rewards.

— Jeremy Beebe & forkland
