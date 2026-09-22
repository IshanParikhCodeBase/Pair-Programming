"""The context pipeline: clustering -> selection -> reranking -> compression.

Each step is independently toggleable via --steps, so we can measure exactly
what each one contributes to cost/accuracy. Reranking and compression aren't
built yet (later sub-tasks) -- right now this pipeline only runs clustering +
selection; asking for "rerank" or "compress" raises clearly instead of
silently doing nothing.
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
from make_charts import load_runs, plot_cost_chart

from contextlab import config
from contextlab.embeddings import embed_texts, load_chunks
from contextlab.model_client import get_model
from contextlab.retrieval import top_k

TOP_K = 15
SYSTEM_PROMPT = (
    "Answer the question using only the context provided below. Be concise: "
    "answer in as few words as possible, using the exact wording/values from "
    "the context where relevant. If the context does not contain the answer, "
    "say \"I don't know.\""
)


def run_pipeline(chunks, chunk_vecs, steps=("cluster", "select")):
    """Apply the enabled steps in order. Returns (surviving_chunks, surviving_vecs).

    `steps` is a subset/order of ("cluster", "select", "rerank", "compress").
    "select" requires "cluster" to have already produced groups.
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

    if "rerank" in steps:
        raise NotImplementedError("reranking isn't built yet")

    if "compress" in steps:
        raise NotImplementedError("compression isn't built yet")

    return working_chunks, working_vecs


def build_prompt(question, retrieved_chunks):
    context_block = "\n\n".join(
        f"[{chunk['source']}]\n{chunk['text']}" for chunk, _ in retrieved_chunks
    )
    return f"Context:\n{context_block}\n\nQuestion: {question}"


def answer_question(question, chunks, chunk_vecs, model, k=TOP_K):
    retrieved = top_k(question, chunks, chunk_vecs, k=min(k, len(chunks)))
    prompt = build_prompt(question, retrieved)
    response = model.generate(system=SYSTEM_PROMPT, user_message=prompt)
    return response, retrieved


def load_gold_questions():
    with open(config.GOLD_PATH) as f:
        return json.load(f)["questions"]


def run(model_name, steps, out_path):
    chunks = load_chunks()
    chunk_vecs = embed_texts([c["text"] for c in chunks])

    pipeline_chunks, pipeline_vecs = run_pipeline(chunks, chunk_vecs, steps=steps)
    print(f"Pipeline steps: {steps}")
    print(f"Chunks before pipeline: {len(chunks)}")
    print(f"Chunks after pipeline:  {len(pipeline_chunks)}\n")

    model = get_model(model_name)
    gold = load_gold_questions()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for item in gold:
            response, retrieved = answer_question(
                item["question"], pipeline_chunks, pipeline_vecs, model
            )
            record = {
                "id": item["id"],
                "question": item["question"],
                "reference_answer": item["answer"],
                "tags": item["tags"],
                "model_answer": response.text,
                "retrieved_chunk_ids": [c["id"] for c, _ in retrieved],
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
    ap.add_argument("--steps", default="cluster,select")
    args = ap.parse_args()

    steps = tuple(args.steps.split(","))
    out_path = config.RESULTS_DIR / f"pipeline_runs_{args.model}.jsonl"

    run(args.model, steps, out_path)

    if args.model == "haiku":
        runs = load_runs(out_path)
        plot_cost_chart(
            runs,
            config.RESULTS_DIR / "cost_chart_phase1.png",
            "Phase 1 pipeline (clustering + selection) — cost per request (Claude Haiku 4.5)",
        )
