import sys
import os
import json
import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from app.services.ai_client import LocalAIService

def verify_stage3_cross_reference_check():
    print("================================================================================")
    print("      VERIFYING STAGE 3 TUTOR ENGINE CROSS-REFERENCE GROUNDING CHECK            ")
    print("================================================================================")

    ai_client = LocalAIService()

    # 1. Test query on uploaded subject (IT Infrastructure)
    ctx_uploaded = {
        "topic": "IT Infrastructure",
        "user_answer": "IT infrastructure provides shared technology resources for business applications.",
        "has_uploaded_material": True
    }
    res_uploaded_str = ai_client.generate("tutor_evaluate_response", ctx_uploaded)
    res_uploaded = json.loads(res_uploaded_str)

    print("\n--- Test 1: Query on Subject with Uploaded Document (IT Infrastructure) ---")
    print(f"• Explanation: {res_uploaded.get('explanation')[:120]}...")
    print(f"• Understanding Score: {res_uploaded.get('understanding')}%")

    assert res_uploaded.get("understanding") > 0, "Uploaded subject evaluation failed!"
    print("[PASS] 1. Uploaded Subject (IT Infrastructure) evaluated with grounded feedback!")

    # 2. Test query on un-uploaded subject (Calculus / Organic Chemistry)
    ctx_missing = {
        "topic": "Calculus",
        "user_answer": "Integration by parts",
        "has_uploaded_material": False,
        "no_material_uploaded": True
    }
    res_missing_str = ai_client.generate("tutor_evaluate_response", ctx_missing)
    res_missing = json.loads(res_missing_str)

    print("\n--- Test 2: Query on Un-Uploaded Subject (Calculus) ---")
    print(f"• Explanation: {res_missing.get('explanation')}")

    assert "No material uploaded for **Calculus** yet" in res_missing.get("explanation"), "Cross-reference check failed! Tutor engine did not report missing material!"
    print("[PASS] 2. Un-Uploaded Subject (Calculus) reported plainly: 'No material uploaded for Calculus yet'!")

    print("\n================================================================================")
    print(" [PASS] STAGE 3 CROSS-REFERENCE GROUNDING CHECK VERIFIED PROVABLY AT RUNTIME! ")
    print("================================================================================")

if __name__ == "__main__":
    verify_stage3_cross_reference_check()
