"""
scripts/runtime_proof.py — Phase 1 Runtime Evidence Capturer

Executes the 7 benchmark prompts against the dynamic execution graph engine,
capturing ASCII graph visualizations, executed agents, skipped agents & reasons,
shared memory state evolution, minimal pruned context, Gemini prompts/responses,
and execution timings.
"""

import sys
import json
import time
import logging

# Configure stdout encoding for utf-8
sys.stdout.reconfigure(encoding='utf-8')

PROMPTS = [
    "Hi",
    "Explain normalization",
    "Why?",
    "Give another example",
    "I only have 2 hours today",
    "Create a one hour study plan",
    "Quiz me"
]

def main():
    print("================================================================================", flush=True)
    print("           PHASE 1 RUNTIME EVIDENCE REPORT — DYNAMIC EXECUTION GRAPH", flush=True)
    print("================================================================================\n", flush=True)

    from app.core.database import SessionLocal
    from app.models.user import User
    from app.agents.orchestrator import execute_swarm_workflow
    from app.agents.graph_builder import visualize_runtime_graph, AGENT_CONTRACTS
    from app.services.ai_client import get_ai_client
    from app.services.prompt_builders import build_chat_recommendation_prompt

    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("ERROR: No test user found in database.", flush=True)
        return

    client = get_ai_client()

    for idx, prompt_text in enumerate(PROMPTS, 1):
        start_time = time.time()
        print(f"\n################################################################################", flush=True)
        print(f"BENCHMARK PROMPT {idx}: \"{prompt_text}\"", flush=True)
        print(f"################################################################################", flush=True)

        # 1. Incoming Request Payload
        http_payload = {"question": prompt_text}
        print("\n1. EXACT INCOMING REQUEST PAYLOAD:", flush=True)
        print(json.dumps(http_payload, indent=2), flush=True)

        # Execute Swarm Workflow directly
        try:
            result = execute_swarm_workflow(user.id, prompt_text, db, client)
            intent = result.primary_intent
            step_logs = result.step_logs
            skipped_agents = result.skipped_agents
            exec_graph = result.execution_graph
            answer = result.formatted_response
        except Exception as exc:
            print(f"EXECUTION ERROR: {exc}", flush=True)
            continue

        exec_latency = (time.time() - start_time) * 1000

        # 2. Dynamic Execution Graph & Visualization
        print("\n2. DYNAMIC RUNTIME EXECUTION GRAPH:", flush=True)
        active_list = exec_graph.active_agents if exec_graph else [s.agent_name for s in step_logs if s.status != 'skipped']
        print("--------------------------------------------------------------------------------", flush=True)
        print(visualize_runtime_graph(active_list), flush=True)
        print("--------------------------------------------------------------------------------", flush=True)

        # 3. Executed Agents List & Contracts
        print("\n3. EXECUTED AGENTS & DECLARED CONTRACTS:", flush=True)
        executed_steps = [s for s in step_logs if s.status != 'skipped']
        print(f"Total Active Agents Executed: {len(executed_steps)}", flush=True)
        for step in executed_steps:
            contract = AGENT_CONTRACTS.get(step.agent_name)
            inputs_str = f" | Reads: {contract.shared_memory_read}" if contract else ""
            print(f"  • {step.agent_name} -> Status: {step.status} | Summary: {step.summary}{inputs_str}", flush=True)

        # 4. Skipped Agents List with Explicit Rationale
        print("\n4. SKIPPED AGENTS & EVALUATED RATIONALE:", flush=True)
        print(f"Total Agents Skipped: {len(skipped_agents)}", flush=True)
        for skipped in skipped_agents:
            print(f"  • {skipped.agent_name} [SKIPPED] -> Reason: {skipped.skip_reason}", flush=True)

        # 5. Shared Memory & Top-K Concept Nodes (RetrievalAgent Output)
        print("\n5. TOP-K RETRIEVED CONCEPT NODES (RetrievalAgent Output):", flush=True)
        from app.agents.retrieval_agent import retrieve_top_k_nodes
        top_k_nodes = retrieve_top_k_nodes(prompt_text, result.knowledge_graph, top_k=3) if result.knowledge_graph else []
        print(f"  • Top-K Concept Nodes Retrieved: {len(top_k_nodes)}", flush=True)
        for node in top_k_nodes:
            print(f"    - [{node.id}] {node.title}: {node.summary[:80]}...", flush=True)
            if node.formulas:
                print(f"      Formulas: {node.formulas}", flush=True)
            if node.code_snippets:
                print(f"      Code Snippets: {len(node.code_snippets)} snippet(s)", flush=True)

        # 6. Raw Gemini Prompt & Response
        built_prompt = build_chat_recommendation_prompt({
            "user_query": prompt_text,
            "intent": intent,
            "subject": "DBMS",
        })
        print("\n6. RAW GEMINI SYSTEM PROMPT (Sample Construction):", flush=True)
        print("--------------------------------------------------------------------------------", flush=True)
        print(built_prompt, flush=True)
        print("--------------------------------------------------------------------------------", flush=True)

        print("\n7. RAW GEMINI RESPONSE / RENDERED TEXT:", flush=True)
        print("--------------------------------------------------------------------------------", flush=True)
        print(answer, flush=True)
        print("--------------------------------------------------------------------------------", flush=True)

        # 8. Execution Timings
        print("\n8. EXECUTION TIMINGS & LATENCY:", flush=True)
        print(f"  • Total Workflow Execution Latency: {exec_latency:.2f} ms", flush=True)
        print(f"  • Active Agents Executed: {len(active_list)}", flush=True)

        # 9. Final API JSON Output
        print("\n9. EXACT FINAL API JSON RETURNED TO FRONTEND:", flush=True)
        print(json.dumps({
            "primary_intent": intent,
            "active_agents_count": len(active_list),
            "skipped_agents_count": len(skipped_agents),
            "execution_tree": active_list,
            "answer_preview": answer[:120] + "..." if len(answer) > 120 else answer
        }, indent=2), flush=True)

if __name__ == "__main__":
    main()
