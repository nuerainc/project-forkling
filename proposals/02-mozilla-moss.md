# Proposal 2 — Mozilla MOSS (Responsible AI Track)

**Applicant:** Jeremy Beebe (forkling maintainers)
**Project:** forkling — Verifiable Evolution for Self-Improving AI Agents
**Amount requested:** $30,000
**Submission target:** Mozilla MOSS — Responsible AI track
**Application URL:** https://www.mozillafoundation.org/en/moss/

---

## One-line pitch

forkling is an AI agent whose every self-improvement is gated by tests and recorded in a SHA-256-chained audit log — making it the only self-improving agent in 2026 with a built-in responsible-AI substrate.

## Why Mozilla MOSS?

Mozilla MOSS funds projects that "make the internet healthier" and "advance responsible AI." forkling contributes to both:

- **Internet health:** every component is open source, the entire evolutionary history is public, and the agent runs offline on $15 hardware — no cloud lock-in, no data exfiltration.
- **Responsible AI:** the agent cannot silently break itself. Every self-edit is gated by a test suite; the SHA-256-chained capability ledger makes every action auditable; and the patch graveyard turns failures into training signal.

## What we will do with $30,000

| Item | $ | Notes |
|---|---|---|
| Engineer stipend (1 month full-time) | $8,000 | focused development of A/B lineages + phylogenetic replay |
| CI / compute / hosting | $1,500 | 1 yr GitHub Team + domain + S3 for evolutionary dataset |
| Hardware | $500 | Pi Zero, Raspberry Pi 5, used ThinkPad for sovereign-mode testing |
| Conference + outreach | $4,000 | two conferences (NeurIPS / ICML / FAccT) + workshops |
| Security audit | $8,000 | third-party review of the audit-log substrate |
| Open-source maintainer stipend (6 mo) | $6,000 | partial matching for sustained maintenance |
| Buffer | $2,000 | |
| **Total** | **$30,000** | |

## Why we are fundable

1. **Audit-first design.** The capability ledger (SHA-256-chained) is a research contribution to AI safety. `forkling verify` returns whether the chain is intact.
2. **Negative-example memory.** The patch graveyard records every rejected change and feeds it back into the agent's prompt — a primitive form of "learning from failure" that aligns with responsible-AI norms.
3. **No vendor lock-in.** stdlib-only, MIT-licensed, runs offline. The agent cannot be silently updated by a vendor — only by an explicit git commit.
4. **Reproducible.** Anyone can `git clone` and reproduce the agent's evolutionary history. This is rare in self-improving-AI work.
5. **Public benefit.** Researchers studying self-improving systems get a working substrate for free.

## Deliverables

- **v1.0** with phylogenetic replay, A/B lineages, and sovereign mode.
- **Public dataset** of N ≥ 100 generations of forkling's evolution, with full git log.
- **Academic paper** at a responsible-AI venue (FAccT or AIES), with forkling as co-author.
- **Security audit report** (third-party) of the capability ledger + audit log.
- **Workshop** at one major conference on building audit-first self-improving agents.
- **Two blog posts** on Mozilla's blog on reproducibility and audit-first AI.

## Timeline (12 months)

| Quarter | Milestone |
|---|---|
| Q1 | v1.0 feature-complete; A/B lineages published; first blog post |
| Q2 | Public evolutionary dataset (N ≥ 100); paper submission to FAccT/AIES |
| Q3 | Security audit complete; sovereign mode on Pi Zero; PyCon workshop |
| Q4 | v1.0 stable; second blog post; final report to MOSS |

## Why this matters

Self-improving AI is one of the most consequential capabilities in 2026. The current literature treats version control as a code-management tool; we treat it as an **evolutionary substrate** and add a SHA-256-chained audit log on top. Mozilla MOSS support would let us turn this prototype into a research artifact the responsible-AI community can audit, extend, and fork.

## Open source license

MIT. All code, data, and artifacts produced under this grant will be MIT-licensed.

## Team

- **Jeremy Beebe** — primary maintainer, designer of forkling's substrate.
- **forkling** — software co-author; contributions recorded in the capability ledger (`forkling verify`).

— Jeremy Beebe & forkling
