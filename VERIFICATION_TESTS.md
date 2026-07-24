# Verification Tests for AI Specialization

## Test 1: Switch Personalities

Create 3 sessions with same topic (DBMS → Normalization):

**Session A: Friendly Teacher**
- Expected: Warm tone, encouraging feedback
- Example: "Excellent! You really understand DBMS! 🌟"

**Session B: Professor**
- Expected: Formal tone, academic language
- Example: "Your explanation demonstrates solid theoretical comprehension."

**Session C: Exam Coach**
- Expected: Direct tone, marks-focused
- Example: "3/5 marks awarded. Focus on: definitions, mechanisms."

**Observe:** Tone and feedback style visibly change

## Test 2: Switch Learning Modes

Same topic, same personality. Change mode only:

**Teach Me:**
- Expected: Explains 1NF → 2NF → 3NF, THEN asks question

**Test Me:**
- Expected: Asks question IMMEDIATELY, no explanation first

**Challenge Me:**
- Expected: "Design a schema and explain normalization decisions"

**Interview Me:**
- Expected: "Tell me about normalization. Full answer expected."

**Revise:**
- Expected: Short summary, fast-paced questions

**Observe:** Question timing and structure visibly changes

## Test 3: Switch Assessment Formats

Same topic, personality, mode. Change format only:

**MCQ:**
- Expected: "Which is 2NF? A) B) C) D)"

**Short Answer:**
- Expected: "Explain difference between 2NF and 3NF"

**True/False:**
- Expected: "Normalization reduces redundancy. True/False? Explain."

**Mixed:**
- Expected: Rotates between formats

**Observe:** Question format changes visibly

## Test 4: Switch Study Focus

Same all others. Change focus only:

**College:**
- Expected: "Define normalization. What are 1NF, 2NF, 3NF?"

**Placement:**
- Expected: "Design production DB. Apply normalization. Why?"

**GATE:**
- Expected: Complex numerical example, strict marking

**General Learning:**
- Expected: Relaxed pace, encouraging tone

**Observe:** Difficulty and scenario complexity increase

## Test 5: Document Grounding

1. Upload study material PDF
2. Start tutor session with that document
3. Ask tutor questions

**Expected:**
- Tutor says: "Based on your document for [Topic]..."
- All examples quote actual document sections
- NO hallucinated content
- Questions come ONLY from uploaded material

## Test 6: Task Completion

1. Dashboard shows 5 active tasks
2. User marks "DBMS" complete
3. Dashboard updates immediately

**Expected:**
- Task disappears
- Completion rate increases
- "Next recommendation" shows highest-priority task
- Schedule recalculates automatically
- No page refresh needed

## Test 7: Time Constraint

1. Dashboard shows 7-day schedule
2. User says: "I only have 2 hours today"
3. Check today's schedule

**Expected:**
- Today shows exactly 120 minutes
- Lower-priority tasks shift to later days
- Message: "Updated max daily hours to 2.0"
- Backend logs recalculation

## Test 8: Preference Persistence

1. User says: "I don't study Sundays"
2. Generate 30-day schedule
3. Log out and back in
4. Generate schedule again

**Expected:**
- ALL schedules skip Sundays forever
- Preference persists across sessions
- No Sundays appear in future schedules

## Test 9: Conflict Detection

Create tasks:
- Task A (DBMS Exam): due June 30
- Task B (DSA Exam): due June 30
- Task C (Quiz): due July 2, 10h work, 1 day away

**Expected API Response:**
```json
{
  "deadline_conflicts": [
    {"date": "2026-06-30", "count": 2, "tasks": ["DBMS", "DSA"]}
  ],
  "insufficient_prep": [
    {"task": "Quiz", "days": 1, "hours": 10}
  ]
}
```

## Test 10: Loading States

Every AI operation must show:
1. Loading spinner
2. "Thinking..." state
3. Success with explanation
4. Metrics displayed

**Expected:**
- Each state visible for 200+ ms
- No silent failures
- Progress visible to user

---

**All tests should demonstrate visibly different behavior based on selection.**
