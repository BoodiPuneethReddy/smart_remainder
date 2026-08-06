"""
scripts/phase3_proof.py — Phase 3 Real Planner & Reflection Loop Evidence Script

Demonstrates active feedback loop:
1. User provides constraint query: "Create a one hour study plan" (60 minutes).
2. PlannerAgent builds initial raw plan.
3. ReflectionAgent detects overload / budget mismatch and issues replan_required = True.
4. Orchestrator passes ReflectionSuggestion back to PlannerAgent to recalculate.
5. PlannerAgent scales plan down to fit 60m budget cap.
6. ReflectionAgent re-evaluates and approves revised plan.
"""

import sys
import json
import logging

sys.stdout.reconfigure(encoding='utf-8')

PROMPTS = [
    "I only have 2 hours today",
    "Create a one hour study plan"
]

def main():
    out_file = open('phase3_feedback_proof.txt', 'w', encoding='utf-8')
    def print_log(*args, **kwargs):
        print(*args, **kwargs)
        print(*args, **kwargs, file=out_file)
        out_file.flush()

    print_log("================================================================================")
    print_log("      PHASE 3 DETAILED RUNTIME EVIDENCE — PLANNER & REFLECTION FEEDBACK LOOP")
    print_log("================================================================================\n")

    from app.core.database import SessionLocal
    from app.models.user import User
    from app.agents.orchestrator import execute_swarm_workflow
    from app.agents.session_state import get_session

    from app.services.ai_client import get_ai_client

    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("ERROR: No test user found in database.")
        return

    client = get_ai_client()
    session = get_session(user.id)

    for idx, prompt_text in enumerate(PROMPTS, 1):
        print_log(f"\n################################################################################")
        print_log(f"BENCHMARK PROMPT {idx}: \"{prompt_text}\"")
        print_log(f"################################################################################")

        try:
            result = execute_swarm_workflow(user.id, prompt_text, db, client)
            exec_graph = result.execution_graph
            step_logs = result.step_logs
            plan = result.plan
            answer = result.formatted_response
        except Exception as exc:
            import traceback
            print_log(f"EXECUTION ERROR: {exc}")
            traceback.print_exc()
            continue

        print_log("\n1. DYNAMIC RUNTIME EXECUTION GRAPH:")
        print_log("--------------------------------------------------------------------------------")
        print_log(" -> ".join(exec_graph.active_agents) if exec_graph else "None")
        print_log("--------------------------------------------------------------------------------")

        print_log("\n2. AGENT STEP LOGS & REFLECTION FEEDBACK TRAIL:")
        for s in step_logs:
            if s.agent_name in ["PlannerAgent", "ReflectionAgent"]:
                icon = "⚠️" if s.status == "warning" else "✅"
                print_log(f"  • [{s.agent_name}] ({s.status.upper()}) {icon}: {s.summary}")

        if plan:
            print_log(f"\n3. FINAL REVISED PLAN (BUDGET CAP: {plan.available_minutes}m, ALLOCATED: {plan.allocated_minutes}m):")
            for item in plan.items:
                print_log(f"  - [{item.subject}] {item.title}: {item.recommended_minutes} mins (Priority: {item.priority_score:.1f})")

        print_log("\n4. FINAL NATURAL LANGUAGE PRESENTATION:")
        print_log("--------------------------------------------------------------------------------")
        print_log(answer[:300] + "...")
        print_log("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    main()
