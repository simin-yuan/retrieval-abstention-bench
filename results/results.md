# Results

Questions in the frozen exam: **1017** (every cell below is scored on exactly these, `ids_ok` column).

Criterion A = decline when the best score is below the calibrated threshold. Criterion B = decline when the cited chunk does not contain the anchor. Reported cells exclude the calibration half of the gold questions.


## Retrieval quality on the answerable questions (gold)

| retriever | chunk | k | drop | hit@k | mean retrieved chars | gold abstain A | gold abstain B | ids ok |
|---|---|---|---|---|---|---|---|---|
| bm25 | 1600 | 10 | 0.4 | 99.0% | 15671 | 5.7% | 3.7% | yes |
| bm25 | 1600 | 10 | 0.6 | 98.0% | 15656 | 4.0% | 3.3% | yes |
| bm25 | 1600 | 10 | 0.8 | 89.0% | 15626 | 4.7% | 1.3% | yes |
| bm25 | 1600 | 1 | 0.4 | 93.7% | 1532 | 5.7% | 3.7% | yes |
| bm25 | 1600 | 1 | 0.6 | 90.7% | 1527 | 4.0% | 3.3% | yes |
| bm25 | 1600 | 1 | 0.8 | 76.7% | 1519 | 4.7% | 1.3% | yes |
| bm25 | 1600 | 5 | 0.4 | 99.0% | 7804 | 5.7% | 3.7% | yes |
| bm25 | 1600 | 5 | 0.6 | 96.7% | 7811 | 4.0% | 3.3% | yes |
| bm25 | 1600 | 5 | 0.8 | 86.7% | 7799 | 4.7% | 1.3% | yes |
| bm25 | 3200 | 10 | 0.4 | 99.3% | 30955 | 6.0% | 2.3% | yes |
| bm25 | 3200 | 10 | 0.6 | 98.7% | 30896 | 4.7% | 1.3% | yes |
| bm25 | 3200 | 10 | 0.8 | 90.3% | 30523 | 4.3% | 1.3% | yes |
| bm25 | 3200 | 1 | 0.4 | 93.7% | 3013 | 6.0% | 2.3% | yes |
| bm25 | 3200 | 1 | 0.6 | 90.7% | 2987 | 4.7% | 1.3% | yes |
| bm25 | 3200 | 1 | 0.8 | 72.7% | 2966 | 4.3% | 1.3% | yes |
| bm25 | 3200 | 5 | 0.4 | 99.0% | 15457 | 6.0% | 2.3% | yes |
| bm25 | 3200 | 5 | 0.6 | 96.7% | 15366 | 4.7% | 1.3% | yes |
| bm25 | 3200 | 5 | 0.8 | 87.0% | 15199 | 4.3% | 1.3% | yes |
| bm25 | 800 | 10 | 0.4 | 98.0% | 7932 | 5.7% | 5.3% | yes |
| bm25 | 800 | 10 | 0.6 | 97.3% | 7910 | 5.0% | 6.0% | yes |
| bm25 | 800 | 10 | 0.8 | 91.3% | 7889 | 5.3% | 4.3% | yes |
| bm25 | 800 | 1 | 0.4 | 88.7% | 782 | 5.7% | 5.3% | yes |
| bm25 | 800 | 1 | 0.6 | 86.0% | 781 | 5.0% | 6.0% | yes |
| bm25 | 800 | 1 | 0.8 | 75.0% | 783 | 5.3% | 4.3% | yes |
| bm25 | 800 | 5 | 0.4 | 97.7% | 3954 | 5.7% | 5.3% | yes |
| bm25 | 800 | 5 | 0.6 | 96.3% | 3949 | 5.0% | 6.0% | yes |
| bm25 | 800 | 5 | 0.8 | 87.3% | 3953 | 5.3% | 4.3% | yes |
| ngram-tfidf | 1600 | 10 | 0.4 | 99.7% | 15089 | 4.3% | 4.0% | yes |
| ngram-tfidf | 1600 | 10 | 0.6 | 98.3% | 14984 | 3.7% | 4.7% | yes |
| ngram-tfidf | 1600 | 10 | 0.8 | 90.0% | 15038 | 5.3% | 8.3% | yes |
| ngram-tfidf | 1600 | 1 | 0.4 | 94.3% | 1517 | 4.3% | 4.0% | yes |
| ngram-tfidf | 1600 | 1 | 0.6 | 90.0% | 1509 | 3.7% | 4.7% | yes |
| ngram-tfidf | 1600 | 1 | 0.8 | 71.0% | 1461 | 5.3% | 8.3% | yes |
| ngram-tfidf | 1600 | 5 | 0.4 | 99.0% | 7445 | 4.3% | 4.0% | yes |
| ngram-tfidf | 1600 | 5 | 0.6 | 98.0% | 7410 | 3.7% | 4.7% | yes |
| ngram-tfidf | 1600 | 5 | 0.8 | 86.3% | 7409 | 5.3% | 8.3% | yes |
| ngram-tfidf | 3200 | 10 | 0.4 | 99.3% | 28696 | 4.3% | 2.3% | yes |
| ngram-tfidf | 3200 | 10 | 0.6 | 99.0% | 28444 | 4.3% | 2.3% | yes |
| ngram-tfidf | 3200 | 10 | 0.8 | 90.0% | 28195 | 5.3% | 7.7% | yes |
| ngram-tfidf | 3200 | 1 | 0.4 | 95.0% | 2962 | 4.3% | 2.3% | yes |
| ngram-tfidf | 3200 | 1 | 0.6 | 91.0% | 2915 | 4.3% | 2.3% | yes |
| ngram-tfidf | 3200 | 1 | 0.8 | 67.7% | 2741 | 5.3% | 7.7% | yes |
| ngram-tfidf | 3200 | 5 | 0.4 | 99.0% | 14164 | 4.3% | 2.3% | yes |
| ngram-tfidf | 3200 | 5 | 0.6 | 98.0% | 13976 | 4.3% | 2.3% | yes |
| ngram-tfidf | 3200 | 5 | 0.8 | 85.0% | 13794 | 5.3% | 7.7% | yes |
| ngram-tfidf | 800 | 10 | 0.4 | 98.7% | 7673 | 5.7% | 8.0% | yes |
| ngram-tfidf | 800 | 10 | 0.6 | 97.7% | 7658 | 3.3% | 7.7% | yes |
| ngram-tfidf | 800 | 10 | 0.8 | 89.7% | 7693 | 5.0% | 11.3% | yes |
| ngram-tfidf | 800 | 1 | 0.4 | 88.3% | 774 | 5.7% | 8.0% | yes |
| ngram-tfidf | 800 | 1 | 0.6 | 86.0% | 775 | 3.3% | 7.7% | yes |
| ngram-tfidf | 800 | 1 | 0.8 | 68.7% | 758 | 5.0% | 11.3% | yes |
| ngram-tfidf | 800 | 5 | 0.4 | 98.3% | 3803 | 5.7% | 8.0% | yes |
| ngram-tfidf | 800 | 5 | 0.6 | 96.0% | 3765 | 3.3% | 7.7% | yes |
| ngram-tfidf | 800 | 5 | 0.8 | 83.7% | 3808 | 5.0% | 11.3% | yes |

## Headline: bm25, chunk 1600, top-5, drop 0.6

| bucket | n | abstain A | abstain B | answered (B) | anchor beyond top-1 |
|---|---|---|---|---|---|
| gold | 300 | 4.0% | 3.3% | 96.7% | 3.3% |
| entity-fake | 300 | 7.0% | 100.0% | 0.0% | 0.0% |
| relation-fake-intra | 117 | 3.4% | 86.3% | 13.7% | 70.9% |
| relation-fake-cross | 300 | 12.0% | 86.0% | 14.0% | 69.0% |

Abstain-rate gap, relation-fake (cross) minus gold, criterion B: **+82.7 points** (95% bootstrap CI +77.7 to +87.3).

Criterion A, score AUC between gold and relation-fake (cross): **0.634** (0.5 = the score cannot tell them apart).

Criterion A, score AUC between gold and relation-fake (intra): **0.520**. The cross-book tier is the easier of the two for criterion A -- its swapped anchor never occurs in the target book at all, and a score is allowed to notice that. The same-book tier keeps the swapped anchor inside the book, a long way from the answer, so it is the cleaner test of whether a score threshold can see the difference.


## Ablations (one variable at a time, baseline bm25|1600|5|0.6)

Each row changes exactly one axis; the paired test is McNemar on the same questions, criterion B, and no arm loses questions (see `ids ok` above).

| axis | value | gold hit@k | cross abstain B | Δ vs baseline | McNemar p |
|---|---|---|---|---|---|
| top-k,drop-ratio | bm25/1600/10/0.4 | 99.0% | 94.3% | +4.0 pts | 5.8e-09 |
| top-k | bm25/1600/10/0.6 | 98.0% | 86.0% | +0.0 pts | 1 |
| top-k,drop-ratio | bm25/1600/10/0.8 | 89.0% | 62.0% | -10.3 pts | 2.4e-22 |
| top-k,drop-ratio | bm25/1600/1/0.4 | 93.7% | 94.3% | +4.0 pts | 5.8e-09 |
| top-k | bm25/1600/1/0.6 | 90.7% | 86.0% | +0.0 pts | 1 |
| top-k,drop-ratio | bm25/1600/1/0.8 | 76.7% | 62.0% | -10.3 pts | 2.4e-22 |
| drop-ratio | bm25/1600/5/0.4 | 99.0% | 94.3% | +4.0 pts | 5.8e-09 |
| drop-ratio | bm25/1600/5/0.8 | 86.7% | 62.0% | -10.3 pts | 2.4e-22 |
| chunk,top-k,drop-ratio | bm25/3200/10/0.4 | 99.3% | 88.7% | +1.5 pts | 0.077 |
| chunk,top-k | bm25/3200/10/0.6 | 98.7% | 79.3% | -2.9 pts | 1.3e-07 |
| chunk,top-k,drop-ratio | bm25/3200/10/0.8 | 90.3% | 50.0% | -14.8 pts | 7.1e-37 |
| chunk,top-k,drop-ratio | bm25/3200/1/0.4 | 93.7% | 88.7% | +1.5 pts | 0.077 |
| chunk,top-k | bm25/3200/1/0.6 | 90.7% | 79.3% | -2.9 pts | 1.3e-07 |
| chunk,top-k,drop-ratio | bm25/3200/1/0.8 | 72.7% | 50.0% | -14.8 pts | 7.1e-37 |
| chunk,drop-ratio | bm25/3200/5/0.4 | 99.0% | 88.7% | +1.5 pts | 0.077 |
| chunk | bm25/3200/5/0.6 | 96.7% | 79.3% | -2.9 pts | 1.3e-07 |
| chunk,drop-ratio | bm25/3200/5/0.8 | 87.0% | 50.0% | -14.8 pts | 7.1e-37 |
| chunk,top-k,drop-ratio | bm25/800/10/0.4 | 98.0% | 96.3% | +5.1 pts | 2.4e-11 |
| chunk,top-k | bm25/800/10/0.6 | 97.3% | 88.3% | +2.2 pts | 0.00031 |
| chunk,top-k,drop-ratio | bm25/800/10/0.8 | 91.3% | 70.3% | -6.4 pts | 1.7e-09 |
| chunk,top-k,drop-ratio | bm25/800/1/0.4 | 88.7% | 96.3% | +5.1 pts | 2.4e-11 |
| chunk,top-k | bm25/800/1/0.6 | 86.0% | 88.3% | +2.2 pts | 0.00031 |
| chunk,top-k,drop-ratio | bm25/800/1/0.8 | 75.0% | 70.3% | -6.4 pts | 1.7e-09 |
| chunk,drop-ratio | bm25/800/5/0.4 | 97.7% | 96.3% | +5.1 pts | 2.4e-11 |
| chunk | bm25/800/5/0.6 | 96.3% | 88.3% | +2.2 pts | 0.00031 |
| chunk,drop-ratio | bm25/800/5/0.8 | 87.3% | 70.3% | -6.4 pts | 1.7e-09 |
| top-k,drop-ratio,retriever | ngram-tfidf/1600/10/0.4 | 99.7% | 98.0% | +5.3 pts | 2.6e-13 |
| top-k,retriever | ngram-tfidf/1600/10/0.6 | 98.3% | 91.3% | +3.0 pts | 5.5e-06 |
| top-k,drop-ratio,retriever | ngram-tfidf/1600/10/0.8 | 90.0% | 70.7% | -4.6 pts | 5.6e-05 |
| top-k,drop-ratio,retriever | ngram-tfidf/1600/1/0.4 | 94.3% | 98.0% | +5.3 pts | 2.6e-13 |
| top-k,retriever | ngram-tfidf/1600/1/0.6 | 90.0% | 91.3% | +3.0 pts | 5.5e-06 |
| top-k,drop-ratio,retriever | ngram-tfidf/1600/1/0.8 | 71.0% | 70.7% | -4.6 pts | 5.6e-05 |
| drop-ratio,retriever | ngram-tfidf/1600/5/0.4 | 99.0% | 98.0% | +5.3 pts | 2.6e-13 |
| retriever | ngram-tfidf/1600/5/0.6 | 98.0% | 91.3% | +3.0 pts | 5.5e-06 |
| drop-ratio,retriever | ngram-tfidf/1600/5/0.8 | 86.3% | 70.7% | -4.6 pts | 5.6e-05 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/3200/10/0.4 | 99.3% | 97.7% | +4.7 pts | 1.2e-09 |
| chunk,top-k,retriever | ngram-tfidf/3200/10/0.6 | 99.0% | 88.7% | +1.3 pts | 0.079 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/3200/10/0.8 | 90.0% | 65.7% | -7.6 pts | 2.5e-10 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/3200/1/0.4 | 95.0% | 97.7% | +4.7 pts | 1.2e-09 |
| chunk,top-k,retriever | ngram-tfidf/3200/1/0.6 | 91.0% | 88.7% | +1.3 pts | 0.079 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/3200/1/0.8 | 67.7% | 65.7% | -7.6 pts | 2.5e-10 |
| chunk,drop-ratio,retriever | ngram-tfidf/3200/5/0.4 | 99.0% | 97.7% | +4.7 pts | 1.2e-09 |
| chunk,retriever | ngram-tfidf/3200/5/0.6 | 98.0% | 88.7% | +1.3 pts | 0.079 |
| chunk,drop-ratio,retriever | ngram-tfidf/3200/5/0.8 | 85.0% | 65.7% | -7.6 pts | 2.5e-10 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/800/10/0.4 | 98.7% | 98.3% | +6.6 pts | 2.2e-18 |
| chunk,top-k,retriever | ngram-tfidf/800/10/0.6 | 97.7% | 92.7% | +4.4 pts | 1.4e-09 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/800/10/0.8 | 89.7% | 76.7% | -1.6 pts | 0.18 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/800/1/0.4 | 88.3% | 98.3% | +6.6 pts | 2.2e-18 |
| chunk,top-k,retriever | ngram-tfidf/800/1/0.6 | 86.0% | 92.7% | +4.4 pts | 1.4e-09 |
| chunk,top-k,drop-ratio,retriever | ngram-tfidf/800/1/0.8 | 68.7% | 76.7% | -1.6 pts | 0.18 |
| chunk,drop-ratio,retriever | ngram-tfidf/800/5/0.4 | 98.3% | 98.3% | +6.6 pts | 2.2e-18 |
| chunk,retriever | ngram-tfidf/800/5/0.6 | 96.0% | 92.7% | +4.4 pts | 1.4e-09 |
| chunk,drop-ratio,retriever | ngram-tfidf/800/5/0.8 | 83.7% | 76.7% | -1.6 pts | 0.18 |

## Leak check: abstention by IDF-weighted overlap of the question with its source passage

| overlap | n gold | n cross | gold hit@k | cross abstain B |
|---|---|---|---|---|
| 0.0-0.2 | 0 | 0 | - | - |
| 0.2-0.4 | 0 | 2 | - | 0.0% |
| 0.4-0.6 | 0 | 3 | - | 0.0% |
| 0.6-0.8 | 0 | 41 | - | 39.0% |
| 0.8-1.0 | 300 | 254 | 96.7% | 95.3% |

Read the bands within a bucket, not across them: a relation-level fake replaces the anchor with an entity that does not appear in the source passage, so its overlap is lower by construction, which is why the two `n` columns shift differently. Every gold question sits in the top band (they keep their source text verbatim, which is what makes them answerable), so the fakes are the interesting column: the ones still close to their source passage are declined most reliably, and the bands where the query was cut hardest are the noisy ones where a wrong chunk can happen to contain the swapped anchor.


## Per-question records

`results.json` carries one record per question per kept cell, including top-1 score, cited chunk, coverage of the gold span and both criteria's decision, so every number above can be recomputed without the corpus.

