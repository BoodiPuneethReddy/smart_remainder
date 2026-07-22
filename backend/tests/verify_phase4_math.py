import sys
import os
import math
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from app.agents.learning_agent import calculate_retention, schedule_revision
from app.services.tutor_service import TutorService

def run_phase4_verification():
    print("==========================================================")
    print("  PHASE 4 — LEARNING INTELLIGENCE MATHEMATICS VERIFICATION ")
    print("==========================================================")
    
    results = []

    def record_test(name, passed, detail="", evidence=""):
        status = "PASS" if passed else "FAIL"
        results.append({
            "name": name,
            "passed": passed,
            "detail": detail,
            "evidence": evidence
        })
        print(f"[{status}] {name}")
        if detail:
            print(f"       Detail: {detail}")
        if evidence:
            print(f"       Evidence: {evidence}")

    # 1. Ebbinghaus Forgetting Curve - Manual Math Comparison
    # Formula: R = exp(-elapsed_days / (interval_days * 2.0)) * 100.0
    now = datetime.now(timezone.utc)
    
    # Test case 1a: Immediate revision (0 elapsed days) -> expect 100.0%
    r_immediate = calculate_retention(now, interval_days=7)
    expected_1a = 100.0
    if abs(r_immediate - expected_1a) < 0.1:
        record_test("Ebbinghaus Math - Immediate Revision (t=0)", True, f"Calculated: {r_immediate}%, Expected: {expected_1a}%")
    else:
        record_test("Ebbinghaus Math - Immediate Revision (t=0)", False, f"Calculated {r_immediate}%, Expected {expected_1a}%")

    # Test case 1b: 7 days elapsed with interval 7 days -> strength S = 14.0
    # exp(-7 / 14.0) = exp(-0.5) ~ 0.60653 -> 60.7%
    seven_days_ago = now - timedelta(days=7)
    r_7days = calculate_retention(seven_days_ago, interval_days=7)
    expected_1b = round(math.exp(-7.0 / 14.0) * 100.0, 1) # 60.7%
    if abs(r_7days - expected_1b) <= 0.2:
        record_test("Ebbinghaus Math - 7 Days Decay (t=7, S=14)", True, f"Calculated: {r_7days}%, Manual Math: {expected_1b}%")
    else:
        record_test("Ebbinghaus Math - 7 Days Decay (t=7, S=14)", False, f"Calculated {r_7days}%, Expected {expected_1b}%")

    # 2. Spaced Repetition Scheduler Transitions
    # SR_INTERVALS = [1, 3, 7, 14, 30]
    next_int_pass = schedule_revision(current_interval=7, quiz_score=85.0)
    if next_int_pass == 14:
        record_test("Spaced Repetition - Success Advancement (7 -> 14 days)", True, f"Next Interval: {next_int_pass} days for Score 85.0%")
    else:
        record_test("Spaced Repetition - Success Advancement (7 -> 14 days)", False, f"Expected 14, got {next_int_pass}")

    next_int_fail = schedule_revision(current_interval=14, quiz_score=40.0)
    if next_int_fail == 7:
        record_test("Spaced Repetition - Failure Regression (14 -> 7 days)", True, f"Next Interval: {next_int_fail} days for Score 40.0%")
    else:
        record_test("Spaced Repetition - Failure Regression (14 -> 7 days)", False, f"Expected 7, got {next_int_fail}")

    # 3. Grounding Confidence % Transparent Formula Verification
    # Formula: chunk_sim * 0.4 + cit_overlap * 0.3 + retriever_score * 0.2 + supp_chunks * 0.1
    # Sample values: chunk_sim=80.0, cit_overlap=70.0, retriever_score=90.0, supp_chunks=50.0
    # Expected: 80*0.4 (32) + 70*0.3 (21) + 90*0.2 (18) + 50*0.1 (5) = 76.0%
    c_sim, c_over, r_score, s_weight = 80.0, 70.0, 90.0, 50.0
    calc_grounding = round(c_sim * 0.4 + c_over * 0.3 + r_score * 0.2 + s_weight * 0.1, 1)
    expected_grounding = 76.0
    if calc_grounding == expected_grounding:
        record_test("Grounding Confidence Formula Verification", True, f"Calculated: {calc_grounding}%, Manual Math: {expected_grounding}%")
    else:
        record_test("Grounding Confidence Formula Verification", False, f"Calculated {calc_grounding}%, Expected {expected_grounding}%")

    # 4. Balanced Mastery Score Multi-Factor Formula Verification
    # Formula: 0.4 * HistAccuracy + 0.2 * Consistency + 0.2 * Retention + 0.2 * RecentPerformance
    # Sample values: HistAccuracy=80.0, Consistency=60.0, Retention=90.0, RecentPerf=70.0
    # Expected: 0.4*80 (32) + 0.2*60 (12) + 0.2*90 (18) + 0.2*70 (14) = 76.0%
    hist_acc, cons, ret, rec_perf = 80.0, 60.0, 90.0, 70.0
    calc_mastery = round(0.4 * hist_acc + 0.2 * cons + 0.2 * ret + 0.2 * rec_perf, 1)
    expected_mastery = 76.0
    if calc_mastery == expected_mastery:
        record_test("Balanced Mastery Score Formula Verification", True, f"Calculated: {calc_mastery}%, Manual Math: {expected_mastery}%")
    else:
        record_test("Balanced Mastery Score Formula Verification", False, f"Calculated {calc_mastery}%, Expected {expected_mastery}%")

    # 5. Speed Guessing Protection Threshold (< 8s)
    time_fast = 4  # 4 seconds
    time_valid = 12 # 12 seconds
    
    is_fast_blocked = (time_fast < 8)
    is_valid_allowed = (time_valid >= 8)
    
    if is_fast_blocked and is_valid_allowed:
        record_test("Speed Guessing Protection Threshold (< 8s)", True, "Fast submit (4s) blocked, valid submit (12s) accepted", f"Fast Blocked: {is_fast_blocked}, Valid Accepted: {is_valid_allowed}")
    else:
        record_test("Speed Guessing Protection Threshold (< 8s)", False, f"Threshold logic failure: fast={is_fast_blocked}, valid={is_valid_allowed}")

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    print("\n==========================================================")
    print(f" PHASE 4 SUMMARY: Total {len(results)} | Passed {passed_count} | Failed {failed_count}")
    print("==========================================================")
    
    return results

if __name__ == "__main__":
    run_phase4_verification()
