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

---

## Update (2026-09-27): rigor additions since this draft

**Audit-first design, demonstrated.** The capability ledger is
SHA-256-chained and verifiable. The contribution this proposal
claims is bigger than that: after exp003, a self-audit
([`paper/hypothesis_v4r1.md` §0](../paper/hypothesis_v4r1.md))
surfaced **five real measurement-failure modes** (class M1–M5:
endpoint blind to selection; in-loop prompt decoupled from
running source; boolean re-rank resolution; non-reproducible
seeds; wrong statistical test) in the harness that the chain
alone could not catch. We did not paper over them. We
re-registered as [`paper/hypothesis_v4r1.md`](../paper/hypothesis_v4r1.md)
("r1"), shipped a protocol-2 rewrite
([`forkling/experiment2.py`](../forkling/experiment2.py)),
and added a harness self-test
([`tests/test_experiment_power.py`](../tests/test_experiment_power.py),
14/14) that must pass at the commit that produces any new
experiment data. This is **audit-first methodology in
action** — the kind of empirical-AI hygiene MOSS funds.

**exp004 + exp005 — two honest deferrals.** Per v4r1 §6 and
v5 §2.4, both attempts were **deferred, not nulled**, when
calibration produced fewer than the 6-survivor floor
(3 of 12 in exp004; 5 of 24 in exp005). The writeups
([`paper/exp004_results.md`](../paper/exp004_results.md),
[`paper/exp007_results.md`](../paper/exp007_results.md) §background)
call them calibration failures and explicitly refuse to
interpret them as results on the mechanism question. That is
**responsible AI** in the sense MOSS funds: don't manufacture a
result the data doesn't support. Two of the next three
attempts *still* deferred under the same protocol — and that
deferral is itself publishable data, not a failure to ship a
result.

**exp006 + exp007 — closed case, n = 12 across two seeds.**
exp006 cleared the freeze (6 of 33 candidates in band) and
produced a first mechanism result on FORKLAND-BENCH-002
(`qwen2.5-coder:3b`, K = 10, S = 5). exp007 is the
**registered seed-replication** (seed 20261030 vs exp006's
20261025; same benchmark, same protocol). The combined-sample
analysis at n = 12 (registered up front in
[`paper/hypothesis_v7.md`](../paper/hypothesis_v7.md) §4.2) is
the load-bearing empirical test:

- **P − N (filter effect, robust):** +0.545, 95% CI [+0.400,
  +0.691], **p = 0.0005**. Highly significant; 11 of 12
  (task, seed) pairs positive.
- **I − P (amplifier effect, fails to replicate):** −0.425,
  95% CI [−0.550, −0.300], p = 0.0547. CI excludes 0; 8 of
  8 non-zero pairs negative or zero.
- **I − R (loop selector beats random):** +0.340, p = 0.0029.
- **I − N (loop beats one-shot):** +0.433, p = 0.0156.

**Pre-registered interpretation: "filter only."** Selection
on LLM-generated patches is a *filter*, not an *amplifier*,
at this scale on this benchmark with this model. **The
mechanism case that was open for the prior five attempts is
now closed.** Full writeup in
[`paper/methods_paper.md`](../paper/methods_paper.md) §5.

**What this means for the proposal.** The audit-first design
proposed in the body (SHA-256 ledger + harness self-test +
deferred reporting) has *produced a closed mechanism case*
under exactly the rules MOSS encourages: pre-registered
hypotheses, registered calibration procedures, registered
deferred-reporting language, and a registered seed-replication
combined-sample analysis. MOSS support would let us expand
the calibration-frozen benchmark to a wider variety of
bug-fix classes, run the same pre-registered protocol across
multiple coder models (where hardware permits), and ship
*Forkling-30* and *Forkling-90* reference organisms with
the same audit-first methodology.

**Submission checklist (before sending).**

- [ ] Replace `<your-org>` placeholder in the public-repo URL
      with `nuerainc`.
- [ ] Update evidence-of-impact numbers (tests, capability
      counts) to current values from `paper/paper.md`.
- [ ] Add the `paper/hypothesis_v7.md` link to a
      "Methodology" subsection so reviewers can read the
      pre-registration + audit directly. The audit is the
      strongest piece of evidence this proposal has, and
      hiding it would weaken the responsible-AI claim.
- [ ] Run `python -m forkling verify` once and paste the last
      `chain ok: true` line into the audit-first section.
- [ ] Confirm the Mozilla MOSS submission deadline for the
      current cycle (not committed here).
