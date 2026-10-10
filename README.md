# Retrieval Abstention Bench

[![verify](https://github.com/simin-yuan/retrieval-abstention-bench/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/simin-yuan/retrieval-abstention-bench/actions/workflows/verify.yml)

**Does your retrieval or memory layer know when the answer is not in the corpus?**

Most retrieval benchmarks score answerable questions: did the right passage come back? This one is about the other half. Three of its four question sets are *unanswerable by construction*, and the measurement is whether the system declines — or cites a passage it cannot support.

No LLM is involved anywhere: no API key, no network, no judge model. It is Python standard library only, the exam is frozen with a sha256, and the same command always produces the same numbers.

## 60-second quick start

```bash
git clone https://github.com/simin-yuan/retrieval-abstention-bench
cd retrieval-abstention-bench
python bench/cli.py verify                                                # 33 s: the harness checks itself
python bench/cli.py score --retriever bm25 --chunk 1600 --k 5 --drop 0.6  # 17 s: one cell, printed
python bench/cli.py run --preset default                                  # ~7 min: 54 cells -> results/
```

Requirements: Python 3.9 or newer. Nothing to install, no network access needed.

Real output of `python bench/cli.py score --retriever bm25 --chunk 1600 --k 5 --drop 0.6`, a verbatim excerpt from the middle of the printed JSON object (the ellipsis is where the per-bucket block and the `cell` block follow):

```json
  "abstain_B_gap_cross_minus_gold": {
   "ci95": [
    0.7766666666666666,
    0.8733333333333334
   ],
   "diff": 0.8266666666666667
  },
  "auc_A_cross_vs_gold": 0.6342888888888889,
  "auc_A_intra_vs_gold": 0.5201139601139602,
  ...
  "gold_hit": 0.9666666666666667,
  "threshold": 9.579170392031694
```

The same cell, as the headline table in `results/results.md` (Baseline `bm25`, 1600-character chunks, top-5, 60% of the context words dropped):

| bucket | n | abstain A | abstain B | answered (B) | anchor beyond top-1 |
|---|---|---|---|---|---|
| gold | 300 | 4.0% | 3.3% | 96.7% | 3.3% |
| entity-fake | 300 | 7.0% | 100.0% | 0.0% | 0.0% |
| relation-fake-intra | 117 | 3.4% | 86.3% | 13.7% | 70.9% |
| relation-fake-cross | 300 | 12.0% | 86.0% | 14.0% | 69.0% |

Read the last four rows against the first one. The `gold` row is the answerable half: not declining, and getting the passage, is the success condition. For the three fake rows, declining is the success condition, so `answered (B)` is the failure count — the times the system cited a passage that does not contain the phrase the question was built around. Criterion B gap, cross-book fakes minus gold: **+82.7 points** (95% bootstrap CI +77.7 to +87.3).

## How it differs from the frameworks you already have

Star counts read from the GitHub API on 2026-10-11.

| project | stars | what it is | why it is not this |
|---|---|---|---|
| [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas) | 15,983 | RAG evaluation with LLM-as-judge metrics | every metric calls a judge model, and its synthetic test generation is LLM-based as well |
| [confident-ai/deepeval](https://github.com/confident-ai/deepeval) | 18,731 | LLM evaluation framework, model-graded assertions | the grader is an LLM, and its synthesizer writes test cases with one; the unanswerable case is something you supply |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | 25,870 | prompt, agent and RAG testing with red-teaming | needs model providers, and the assertions are hand-written, so it measures the cases you thought of |
| **this bench** | — | abstention on a frozen exam with constructed negatives | no LLM, no network, deterministic; the unanswerable questions are *constructed and checked* rather than written by hand |

Three things here are not in those tools, and they are the point:

1. **The negatives are built, not written.** A relation-level fake takes a real question and swaps one entity anchor for another real entity that sits far away in the text. Whether it is genuinely unanswerable is then *checked numerically* (a distance rule) instead of being asserted. Hand-written unanswerable sets only measure the cases their author imagined.
2. **The parameters are frozen before anything is scored.** Every threshold, chunk size, drop ratio and band lives in `bench/config.py`, and the exam manifest records their values next to the exam's sha256. `verify` fails if a recorded parameter no longer matches the code, so a number cannot be improved by moving a threshold after the fact.
3. **It reports how much of the question is still source text.** Questions are built from real sentences with a controlled fraction of context words removed, and every result is broken down by IDF-weighted overlap between the question and its source passage — so a reader can see whether the measured abstention is explained by the question practically quoting the answer.

## How it works

**Four question sets, one corpus.** The corpus is four novels by Jane Austen, all published during her lifetime, 214 chapters and 3.1 million characters (`corpus/SOURCE.md` records the editions, the public-domain basis and the per-book hashes).

| set | how it is built | the correct behaviour |
|---|---|---|
| `gold` | question drawn from a sentence containing a real entity anchor; the answer span is masked out of the question | answer it, and retrieve the span |
| `entity-fake` | same construction, anchor replaced with an invented name | decline — the anchor occurs nowhere in the corpus |
| `relation-fake-intra` | same construction, anchor replaced with a real entity of the same book that never comes within one chunk of the answer entity | decline |
| `relation-fake-cross` | anchor replaced with a real entity of a different book | decline |

`entity-fake` is a sanity check rather than a headline: an anchor that does not exist anywhere makes the answer unanswerable for a trivial reason. The `relation-fake` tiers are the interesting ones, because the anchor is real, appears in the corpus, and is simply nowhere near anything that supports the relation the question asks about.

**Two criteria, one interface.** An answerer is any object with `answer(question, ranked, chunks) -> {"abstain": bool, "cited_chunk_id": str or None}`.

- Criterion A: decline when the best score is below a threshold calibrated on *half* of the gold questions. The reported numbers come from the other half.
- Criterion B: decline when the cited chunk does not contain the anchor. It inspects the top-1 chunk only, and when a real system is plugged in it inspects that system's `cited_chunk_id`. Free-form text is never checked — with no LLM there is no way to verify a sentence, which is exactly the point of an offline harness.

Two zero-dependency retrievers ship with it, Okapi BM25 and word 1-2 gram TF-IDF with cosine, so the bench measures a real retrieval layer rather than a stub. Swapping in your own is a few lines (`run.RETRIEVERS`).

**Reachability before scoring.** A question whose answer span no chunk covers is unanswerable for a reason that has nothing to do with the system, so those questions are dropped before the frequency pairing and before sealing, under every chunk size in the grid. The manifest records how many were dropped and why. Every cell is then scored on exactly the same questions, which the `ids ok` column of the report checks.

**Frequency pairing.** Rarity drives retrieval scores, so a fake built from a rare anchor would be easier to spot than a gold question built from a common one. Gold and fake questions are paired inside five anchor-frequency bands so both sides carry the same frequency profile.

**Sealing.** `python bench/cli.py seal` writes `exam/exam.jsonl` and a manifest with the frozen parameters, the reachability accounting, the distance-check result and sha256 values for the corpus, the entity table and the exam. Re-running it with the same seed reproduces the same exam.

**Statistics.** The gold-vs-fake abstention gap comes with a 95% bootstrap CI on the difference (independently resampled per group); ablations are paired McNemar tests on the same questions; criterion A is reported as a rank-based AUC, where 0.5 means the score cannot tell the two sets apart.

## It checks itself

```bash
python bench/cli.py verify
```

14 self-checks and 7 falsification cases, 33 seconds, exit status 0 or 1. Real output:

```
PASS manifest sha256                        exam.jsonl sha256 matches the manifest
PASS exam shape                             1017 rows, 1017 unique ids, 0 malformed, buckets {'gold': 300, ...}
PASS entity table                           69 entities {'person': 46, 'place': 23}, 0 bad types, 0 numeric, 0 with no occurrence
PASS distance rule                          417 relation-level rows checked, 0 failures
PASS frozen parameters unchanged            13 frozen parameters
PASS negative: fakes declined by construction  criterion B abstain on entity-level fakes under the oracle: 1.000
PASS positive: oracle ceiling               oracle retriever: gold hit@5 1.000, cross abstain B 1.000
PASS positive: empty retriever floor        empty retriever: hit 0.000, gold abstain A 1.000, gold abstain B 1.000
PASS positive: answerer extremes            always-answer abstains=False, never-answer abstains=True, free text rejected=True

14 checks, 0 failed
```

The positive controls matter as much as the assertions: an oracle retriever that is handed the correct chunk drives `gold hit@5` to 1.000 and cross-book abstention to 1.000, which is what shows the metric can reach its ceiling instead of being stuck. A retriever that returns nothing drives both to their floor.

Then the falsification pass breaks things on purpose and requires the checks to notice:

```
CAUGHT manifest byte flip           exam.jsonl sha256 MISMATCH: 95ca6edb5c90c040...4f8290f vs 6996471dd35faf...ea861440
CAUGHT entity-level anchor leaks    300 entity-level fakes, 1 of their anchors occur in the corpus (717)
CAUGHT entities too close           pair elinor/marianne: 417 relation-level rows checked, 1 failures
CAUGHT shorter arm                  204 vs 199 questions, identical=False
CAUGHT parameter moved after sealing  13 frozen parameters; drifted: hit_overlap 0.5 -> 0.0
CAUGHT oracle misses the answer     oracle retriever: gold hit@5 0.997, cross abstain B 1.000
CAUGHT fake answered                criterion B abstain on entity-level fakes under the oracle: 0.997

7 cases, 0 breakages unnoticed
```

A check that cannot fail is decoration, so a missed breakage is a test failure here.

CI runs `verify` and one scoring cell on Python 3.9 and 3.12 (run `38071558272`, green on both).

## Limitations

- **Pronouns are invisible to this.** A relation-fake question can in principle be answerable through a pronoun elsewhere in the corpus, and the string-matching checks cannot see that. Those questions make the bench lenient, not strict.
- **The corpus is famous.** These four novels are in the training data of every large model. If you plug an LLM answerer in, it may answer from memory, which would inflate the measured abstention. The retrieval-only headline is unaffected; the design keeps the LLM out for exactly that reason.
- **Free text is not checked.** Only citations taken from a retrieved chunk can be verified offline. A system that writes prose needs an adapter that reports which chunk it used.
- **English only, one author, four books.** The entity table, the distance rule and the frequency bands are corpus-specific constructions; the harness generalises, the corpus does not.
- **The cross-book tier is easier for criterion A than for criterion B.** Its swapped anchor occurs nowhere in the target book, and a score can legitimately notice that: AUC 0.634 against gold, versus 0.520 on the same-book tier, where the anchor is real, present and merely far away. Criterion B has no such shortcut, which is why the headline rests on it.
- **Sample size.** 1017 questions, of which 117 are same-book fakes — that tier's interval is wide, and it is reported separately for that reason.
- **Criterion A is calibrated on half the gold questions, once, for the whole corpus**, not per cell. It is a fixed threshold, not a tuned one.

## Corpus

Four novels by Jane Austen, all published during her lifetime: *Sense and Sensibility* (1811), *Pride and Prejudice* (1813), *Mansfield Park* (1814), *Emma* (1815). She died in 1817, so the works are in the US public domain and clear life-plus-100-year terms elsewhere. Texts come from the Standard Ebooks editions, which dedicate each file to the public domain under CC0 1.0. `corpus/SOURCE.md` has the details; `corpus/AMBIGUOUS.md` records the names deliberately left out of the entity table and why. The build strips everything outside the chapter bodies and asserts that the transcription project named in the source edition's imprint appears nowhere — the string is assembled from fragments at runtime so that the assertion itself does not ship it.

Rebuilding the corpus needs network access; the built corpus is committed, so nothing else does.

```bash
python corpus/build_corpus.py --out corpus
```

## License

MIT for the code — see `LICENSE`. The corpus is public domain, CC0 1.0 as distributed by Standard Ebooks. If you use this in academic work, `CITATION.cff` has the citation.
