"""One entry point for the whole bench.

    python bench/cli.py seal     --per-arm 300   # freeze exam/exam.jsonl
    python bench/cli.py verify                   # self-tests + falsification
    python bench/cli.py run      --preset quick  # score the grid, write results/
    python bench/cli.py score    --cell bm25 1600 5 0.6   # one cell, printed

`verify` is the one to read first: it is the harness checking itself, including
the two assertions that make the exam meaningful and the controls that show each
metric can move to both ends.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ablate  # noqa: E402
import config  # noqa: E402
import corpus as C  # noqa: E402
import falsify  # noqa: E402
import run  # noqa: E402
import selftest  # noqa: E402


def cmd_seal(args):
    import seal
    return seal.main(["--per-arm", str(args.per_arm)])


def cmd_verify(args):
    code = selftest.main([args.exam])
    print()
    code |= falsify.main()
    return code


def cmd_run(args):
    corpus = C.Corpus()
    rows = run.load_exam(args.exam)
    payload = ablate.run_grid(corpus, rows, args.preset,
                              progress=lambda m: print(" ", m) if args.verbose else None)
    os.makedirs(args.out, exist_ok=True)
    run.write_results(os.path.join(args.out, "results.json"), payload)
    with open(os.path.join(args.out, "results.md"), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write(ablate.render(payload))
    print("wrote %s/results.json and %s/results.md" % (args.out, args.out))
    return 0


def cmd_score(args):
    corpus = C.Corpus()
    rows = run.load_exam(args.exam)
    records = run.evaluate_cell(corpus, rows, args.retriever, args.chunk, args.k, args.drop)
    summary = run.summarize(records)
    print(json.dumps({"cell": {"retriever": args.retriever, "size": args.chunk, "k": args.k,
                               "drop_ratio": args.drop},
                      "summary": summary}, indent=1, sort_keys=True))
    return 0


def cmd_render(args):
    """Re-render the report from a saved payload, without re-scoring anything."""
    with open(args.results, encoding="utf-8") as fh:
        payload = json.load(fh)
    out_path = os.path.join(args.out, "results.md")
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(ablate.render(payload))
    print("re-rendered %s" % out_path)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("seal", help="freeze the exam")
    p.add_argument("--per-arm", type=int, default=300)
    p.set_defaults(func=cmd_seal)

    p = sub.add_parser("verify", help="self-tests and falsification")
    p.add_argument("--exam", default=os.path.join(HERE, "..", "exam", "exam.jsonl"))
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("run", help="score the grid and write results")
    p.add_argument("--preset", default="quick", choices=sorted(ablate.PRESETS))
    p.add_argument("--out", default=os.path.join(HERE, "..", "results"))
    p.add_argument("--exam", default=os.path.join(HERE, "..", "exam", "exam.jsonl"))
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("score", help="score a single cell and print it")
    p.add_argument("--retriever", default="bm25", choices=sorted(run.RETRIEVERS))
    p.add_argument("--chunk", type=int, default=config.CHUNK_SIZES[1],
                   choices=list(config.CHUNK_SIZES))
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--drop", type=float, default=0.6, choices=list(config.DROP_RATIOS))
    p.add_argument("--exam", default=os.path.join(HERE, "..", "exam", "exam.jsonl"))
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("render", help="re-render results.md from results.json")
    p.add_argument("--results", default=os.path.join(HERE, "..", "results", "results.json"))
    p.add_argument("--out", default=os.path.join(HERE, "..", "results"))
    p.set_defaults(func=cmd_render)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
