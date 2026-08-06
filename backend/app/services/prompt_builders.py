"""
services/prompt_builders.py — Grounded & Adaptive Mentor Prompt Architecture

Dedicated prompt builders for Gemini AI Client & Multi-Agent Swarm.
Enforces strict grounding and adaptive tutoring strategy:
  - Beginner: Simple analogies, real-world examples, small check-in quizzes, avoid dense jargon.
  - Intermediate: Clear definitions, standard SQL examples, balanced theory & practice.
  - Advanced: Technical depth, edge cases, interview-style questions, query optimization.
"""

import json
from typing import Dict, Any, List


def _format_conversation_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return ""
    lines = ["CONVERSATION HISTORY (Recent turns with student):"]
    for turn in history[-4:]:
        sender = "Student" if turn.get("role") == "user" or turn.get("user_query") else "Mentor"
        content = turn.get("content", turn.get("user_query", "")).strip()
        lines.append(f"{sender}: {content}")
    lines.append("")
    return "\n".join(lines)


def build_tutor_prompt(context: Dict[str, Any]) -> str:
    """Builds Socratic tutoring prompt for concepts."""
    return build_grounded_mentor_prompt(context)


def build_planner_explanation_prompt(context: Dict[str, Any]) -> str:
    """Builds a natural mentor rationale for prioritized study schedules."""
    available_minutes = context.get("available_minutes", 240)
    user_time_str = f"{available_minutes // 60}h {available_minutes % 60}m" if available_minutes >= 60 else f"{available_minutes}m"
    tasks = context.get("tasks", [])

    prompt_lines = [
        "You are a personal academic study coach helping a student structure their study session.",
        f"Available Study Time Today: {user_time_str} ({available_minutes}m).",
        "",
        "RECOMMENDED SESSIONS:",
    ]
    for t in tasks:
        p_score = t.get('priority_score', 50)
        prompt_lines.append(f"  - {t.get('subject')} '{t.get('title')}': {t.get('recommended_minutes')}m (Priority: {int(p_score)}/100)")

    return "\n".join(prompt_lines)


def build_reflection_prompt(context: Dict[str, Any]) -> str:
    """Builds a plan feasibility audit prompt."""
    avail = context.get("available_minutes", 60)
    alloc = context.get("allocated_minutes", 90)
    return f"Audit plan feasibility: {alloc}m allocated vs {avail}m available budget."


def build_chat_recommendation_prompt(context: Dict[str, Any]) -> str:
    """Builds general chat recommendation prompt."""
    return build_grounded_mentor_prompt(context)


def build_document_analysis_prompt(text: str, filename: str) -> str:
    """Builds document extraction prompt."""
    return f"Analyze document text from '{filename}': {text[:300]}"


def build_grounded_mentor_prompt(context: Dict[str, Any]) -> str:
    """
    Constructs a minimized, strictly grounded, and adaptively tailored prompt for Gemini reasoning engine.
    """
    user_query = context.get("user_query", context.get("user_answer", ""))
    topic = context.get("topic", "")
    intent = context.get("intent", "general")
    subject = context.get("subject", "General Academic Study")
    history = context.get("history", [])
    learning_ctx = context.get("learning_ctx", {})
    retrieved_nodes = context.get("retrieved_nodes", [])
    kg_dict = context.get("knowledge_graph", {})
    if not retrieved_nodes and isinstance(kg_dict, dict) and kg_dict.get("nodes"):
        retrieved_nodes = kg_dict.get("nodes")

    plan = context.get("plan", {})
    reflection = context.get("reflection", {})
    analytics = context.get("analytics", {})
    mistakes = context.get("mistakes", [])

    mastery_pct = context.get("mastery", learning_ctx.get("mastery_score", 65.0))
    mastery_level = context.get("mastery_level", "Intermediate")
    if mastery_pct < 40:
        mastery_level = "Beginner"
    elif mastery_pct > 75:
        mastery_level = "Advanced"

    personality = context.get("teacher_personality", context.get("personality", "Socratic Tutor"))
    goal = context.get("target_goal", context.get("goal", "General Learning"))
    mode = context.get("learning_mode", "Teach Me")
    fmt = context.get("assessment_type", "Mixed")
    length = context.get("session_length", "60 min")

    personality_directives = {
        "Socratic Tutor": "Ask guiding questions. Never immediately reveal answers. Help student discover concepts.",
        "Professor": "Detailed academic lectures. Formal definitions and rigorous theoretical explanations.",
        "Friendly Teacher": "Simple language. Intuitive real-world analogies. Encouraging and supportive tone.",
        "Exam Coach": "Exam-oriented bullet points. Focus on scoring marks, high-yield topics, and exam tips.",
        "Interviewer": "Conduct a professional technical mock interview. Ask crisp follow-up questions and evaluate every answer."
    }

    goal_directives = {
        "Semester": "Align with university semester syllabus and core conceptual foundations.",
        "Mid Exam": "Focus on high-priority mid-term examination units and definitions.",
        "College Exam": "Cover the complete college exam syllabus thoroughly with key definitions and diagrams.",
        "Placement": "Emphasize technical interview concepts, problem solving, and practical coding/SQL implementation.",
        "Interview": "Conduct behavioral and technical interview questions with crisp evaluative feedback.",
        "GATE": "Focus on competitive exam level mathematical rigor, edge cases, and numerical problem solving.",
        "General Learning": "Foster curiosity, deep conceptual understanding, and real-world practical applications."
    }

    mode_directives = {
        "Teach Me": "Explain concepts step-by-step before asking any check-in questions.",
        "Mixed": "Balance explanation, check-in quiz questions, practical examples, and interactive discussion.",
        "Test Me": "Ask questions ONLY! Do NOT provide explanations until the student submits their response.",
        "Revise": "Provide a rapid bullet-point summary, key formula/definition cheat sheet, and rapid recall highlights.",
        "Challenge Me": "Ask hard edge-case questions, optimization tradeoffs, and deep conceptual challenge problems.",
        "Interview Me": "Structure the interaction as a live technical interview. Ask one question at a time and grade student answers."
    }

    # Adaptive Pedagogy Guidance
    adaptive_guidance = (
        f"PEDAGOGICAL DIRECTIVES (USER SELECTIONS):\n"
        f"• TUTOR PERSONALITY [{personality}]: {personality_directives.get(personality, personality_directives['Socratic Tutor'])}\n"
        f"• LEARNING GOAL [{goal}]: {goal_directives.get(goal, goal_directives['General Learning'])}\n"
        f"• LEARNING MODE [{mode}]: {mode_directives.get(mode, mode_directives['Teach Me'])}\n"
        f"• ASSESSMENT FORMAT [{fmt}]: Format check-in questions matching '{fmt}'.\n"
        f"• SESSION DURATION [{length}]: Structure depth appropriate for {length} duration.\n"
        f"• MASTERY TIER [{mastery_level}]: Calibrate explanation density to {mastery_level} student tier."
    )

    prompt_sections = [
        "================================================================================",
        "SYSTEM ROLE:",
        f"You are an expert academic AI study mentor ({personality}) with perfect memory of this student's progress.",
        "Teach ONLY from the supplied extracted content below. Never invent concepts.",
        "",
        "GROUNDING DIRECTIVES (CRITICAL):",
        "1. Everything you state MUST originate strictly from the RETRIEVED KNOWLEDGE NODES, PLANNER OUTPUT, or LEARNING PROFILE below.",
        "2. Do NOT fabricate facts, invent unprovided exam dates, or guess missing concepts.",
        "3. Do NOT use template headers or mention internal agent names ('PlannerAgent', 'ReflectionAgent', 'DocumentAgent').",
        "",
        adaptive_guidance,
        "================================================================================",
        "",
        "CURRENT GOAL & CONTEXT:",
        f"  • User Query: \"{user_query}\"",
        f"  • Subject Focus: {subject}" + (f" | Topic: {topic}" if topic else ""),
        f"  • Intent: {intent}",
        f"  • Student Mastery Tier: {mastery_level} ({mastery_pct:.0f}%) | Retention: {context.get('retention', 100.0):.0f}%",
        "",
        "RECENT CONVERSATION HISTORY (Pruned):",
        _format_conversation_history(history),
        "",
    ]

    if mistakes:
        prompt_sections.append("PAST MISCONCEPTIONS TO ADDRESS:")
        for m in mistakes:
            prompt_sections.append(f"  - [{m.get('topic')}]: {m.get('mistake_summary')}")
        prompt_sections.append("")

    if retrieved_nodes:
        prompt_sections.append("RETRIEVED KNOWLEDGE GRAPH NODES (Top-5 Grounded Source):")
        for n in retrieved_nodes[:5]:
            prompt_sections.append(json.dumps({
                "citation_node_id": n.get("id", n.get("title")),
                "title": n.get("title"),
                "similarity_score": n.get("similarity_score", "100.0%"),
                "summary": n.get("summary"),
                "difficulty": n.get("difficulty", 3),
                "definitions": n.get("definitions", []),
                "examples": n.get("examples", []),
                "formulas": n.get("formulas", []),
                "code_snippets": n.get("code_snippets", []),
                "parents_prerequisites": n.get("parents", []),
                "children": n.get("children", [])
            }, indent=2))
        prompt_sections.append("")

    if plan:
        prompt_sections.append("PLANNER OUTPUT (Deterministic Schedule & Score Calculations):")
        prompt_sections.append(json.dumps(plan, indent=2))
        prompt_sections.append("")

    if reflection:
        prompt_sections.append("REFLECTION AUDIT (Feasibility & Quality Verification):")
        prompt_sections.append(json.dumps(reflection, indent=2))
        prompt_sections.append("")

    if analytics and intent != "greeting":
        comp_rate = analytics.get("completion_rate", 75.0)
        prompt_sections.append(f"ANALYTICS SUMMARY (Completion Rate: {comp_rate:.0f}%):")
        prompt_sections.append(json.dumps(analytics, indent=2))
        prompt_sections.append("")

    prompt_sections.append("TASK:")
    prompt_sections.append("Generate a helpful, grounded Markdown response directly addressing the user query.")

    return "\n".join(prompt_sections)
