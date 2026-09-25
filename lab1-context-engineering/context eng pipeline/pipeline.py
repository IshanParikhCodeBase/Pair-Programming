"""The context pipeline: clustering -> selection -> reranking -> compression.

Each step is independently toggleable via --steps, so we can measure exactly
what each one contributes to cost/accuracy.

Clustering and selection are corpus-level: they run once, before any question
is asked, producing a smaller, deduplicated chunk pool. Reranking is
question-level -- MMR needs a specific query to score against -- so it runs
per question, at retrieval time, in place of plain top-K similarity.
Compression then runs on whatever reranking (or plain top-K) retrieved for
that question, as the final polish right before the prompt is built.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from clustering import DEFAULT_DISTANCE_THRESHOLD, cluster_chunks, group_by_cluster
from selection import select_representatives
from reranking import rerank
from compression import compress_chunks
from make_charts import load_runs, plot_cost_chart

from contextlab import config
from contextlab.embeddings import embed_texts, load_chunks
from contextlab.model_client import get_model
from contextlab.retrieval import top_k

TOP_K = 15
MMR_LAMBDA = 0.7  # the brief's default
SYSTEM_PROMPT = (
    "Answer the question using only the context provided below. Be concise: "
    "answer in as few words as possible, using the exact wording/values from "
    "the context where relevant. If the context does not contain the answer, "
    "say \"I don't know.\""
)


def run_pipeline(chunks, chunk_vecs, steps=("cluster", "select")):
    """Apply the corpus-level steps (cluster, select) once, before any
    question is asked. Returns (surviving_chunks, surviving_vecs). "rerank"
    and "compress" are handled later, per question, in answer_question --
    they're accepted in `steps` here but ignored, since this function only
    prepares the shared candidate pool.
    """
    working_chunks, working_vecs = chunks, chunk_vecs
    groups = None

    if "cluster" in steps:
        labels, _ = cluster_chunks(working_vecs, distance_threshold=DEFAULT_DISTANCE_THRESHOLD)
        groups = group_by_cluster(working_chunks, labels)

    if "select" in steps:
        if groups is None:
            raise ValueError("'select' requires 'cluster' to run first")
        survivors = select_representatives(groups, strategy="most_authoritative")
        working_chunks = list(survivors.values())
        working_vecs = embed_texts([c["text"] for c in working_chunks])

    return working_chunks, working_vecs


def build_prompt(question, chunks):
    context_block = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)
    return f"Context:\n{context_block}\n\nQuestion: {question}"


def retrieve(question, chunks, chunk_vecs, k, use_rerank):
    if use_rerank:
        results = rerank(question, chunks, chunk_vecs, k=min(k, len(chunks)), lambda_param=MMR_LAMBDA)
    else:
        results = top_k(question, chunks, chunk_vecs, k=min(k, len(chunks)))
    return [c for c, _ in results]


def answer_question(question, chunks, chunk_vecs, model, steps, k=TOP_K):
    retrieved_chunks = retrieve(question, chunks, chunk_vecs, k, use_rerank=("rerank" in steps))
    if "compress" in steps:
        retrieved_chunks = compress_chunks(retrieved_chunks)
    prompt = build_prompt(question, retrieved_chunks)
    response = model.generate(system=SYSTEM_PROMPT, user_message=prompt)
    return response, retrieved_chunks


def load_gold_questions():
    with open(config.GOLD_PATH) as f:
        return json.load(f)["questions"]


def run(model_name, steps, out_path):
    chunks = load_chunks()
    chunk_vecs = embed_texts([c["text"] for c in chunks])

    pipeline_chunks, pipeline_vecs = run_pipeline(chunks, chunk_vecs, steps=steps)
    print(f"Pipeline steps: {steps}")
    print(f"Chunks before pipeline: {len(chunks)}")
    print(f"Chunks after cluster+select: {len(pipeline_chunks)}\n")

    model = get_model(model_name)
    gold = load_gold_questions()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for item in gold:
            response, retrieved_chunks = answer_question(
                item["question"], pipeline_chunks, pipeline_vecs, model, steps
            )
            record = {
                "id": item["id"],
                "question": item["question"],
                "reference_answer": item["answer"],
                "tags": item["tags"],
                "model_answer": response.text,
                "retrieved_chunk_ids": [c["id"] for c in retrieved_chunks],
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "input_cost": response.cost.input_cost,
                "output_cost": response.cost.output_cost,
                "total_cost": response.cost.total,
                "model": model.name,
                "pipeline_steps": list(steps),
            }
            f.write(json.dumps(record) + "\n")
            print(f"{item['id']:>4}  ${response.cost.total:.6f}  {response.text[:70]}")

    total_cost = sum(json.loads(line)["total_cost"] for line in open(out_path))
    print(f"\nWrote {len(gold)} runs to {out_path}")
    print(f"Total cost: ${total_cost:.6f}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mock", choices=["mock", "haiku"])
    ap.add_argument("--steps", default="cluster,select,rerank,compress")
    ap.add_argument("--chart-name", default="cost_chart_phase1.png")
    ap.add_argument("--chart-title", default="Phase 1 pipeline (full: cluster+select+rerank+compress) — cost per request (Claude Haiku 4.5)")
    args = ap.parse_args()

    steps = tuple(args.steps.split(","))
    out_path = config.RESULTS_DIR / f"pipeline_runs_{args.model}_{'-'.join(steps)}.jsonl"

    run(args.model, steps, out_path)

    if args.model == "haiku":
        runs = load_runs(out_path)
        plot_cost_chart(runs, config.RESULTS_DIR / args.chart_name, args.chart_title)
