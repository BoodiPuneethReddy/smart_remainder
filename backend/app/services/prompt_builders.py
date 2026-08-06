"""
services/prompt_builders.py — Personal Academic Mentor Grounded Prompt Architecture

Dedicated prompt builders for Gemini AI Client & Multi-Agent Swarm.
Enforces strict grounding: Gemini acts as the reasoning engine and MUST only
use facts from retrieved knowledge graph nodes, planner outputs, reflection audits,
learning profiles, analytics, and pruned conversation memory.
"""

import json
from typing import Dict, Any, List


def _format_conversation_history(history: List[Dict[str, str]]) -> str:
    """Format recent Q&A turns into a clean conversational context block."""
    if not history:
        return ""
    lines = ["CONVERSATION HISTORY (Previous turns with this student):"]
    for turn in history[-6:]:
        sender = "Student" if turn.get("role") == "user" or turn.get("user_query") else "Mentor"
        content = turn.get("content", turn.get("user_query", "")).strip()
        lines.append(f"{sender}: {content}")
    lines.append("")
    return "\n".join(lines)


def build_tutor_prompt(context: Dict[str, Any]) -> str:
    """Builds Socratic tutoring prompt for concepts."""
    topic = context.get("topic", context.get("user_query", "Subject Concepts"))
    subject = context.get("subject", "DBMS")
    mastery = context.get("mastery", 50.0)
    retention = context.get("retention", 100.0)
    user_answer = context.get("user_answer", context.get("user_query", ""))
    knowledge_graph = context.get("knowledge_graph", {})
    mistake_history = context.get("mistakes", [])
    history = context.get("history", [])

    prompt_lines = [
        "You are an expert, supportive university professor and personal academic mentor.",
        f"You are helping a student in {subject} (Topic: {topic}).",
        f"Student Profile: Current Mastery = {mastery:.0f}% | Retention = {retention:.0f}%.",
        "",
        "MENTOR GUIDELINES:",
        "1. Write naturally and conversationally, like an expert mentor in office hours.",
        "2. NEVER use robotic headers like 'DocumentAgent', 'StrategyAgent', 'Educational Guide', or 'Checkpoint Question'.",
        "3. Address misconceptions directly if the student has past mistakes.",
        "4. If the query is a follow-up (e.g., 'Why?', 'Simplify that', 'Give another example'), seamlessly build upon the previous explanation without restarting.",
        "",
    ]

    history_str = _format_conversation_history(history)
    if history_str:
        prompt_lines.append(history_str)

    if knowledge_graph and knowledge_graph.get("nodes"):
        prompt_lines.append("RELEVANT COURSE MATERIAL CONCEPTS:")
        for idx, node in enumerate(knowledge_graph.get("nodes", [])[:5], 1):
            prompt_lines.append(f"  - [{node.get('title')}]: {node.get('summary')}")
        prompt_lines.append("")

    if mistake_history:
        prompt_lines.append("PAST STUDENT MISCONCEPTIONS TO ADDRESS:")
        for m in mistake_history[:3]:
            prompt_lines.append(f"  - Weak point on '{m.get('topic')}': {m.get('mistake_summary')}")
        prompt_lines.append("")

    if user_answer:
        prompt_lines.append(f"STUDENT QUESTION / RESPONSE: \"{user_answer}\"")
        prompt_lines.append(f"Provide a clear, engaging, grounded explanation of {topic} for {subject}.")
    else:
        prompt_lines.append(f"Provide a natural, engaging explanation of {topic} tailored to a student at {mastery:.0f}% mastery.")

    return "\n".join(prompt_lines)


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
    Constructs a minimized, strictly grounded prompt for Gemini reasoning engine.
    """
    user_query = context.get("user_query", "")
    intent = context.get("intent", "general")
    subject = context.get("subject", "General Academic Study")
    history = context.get("history", [])
    learning_ctx = context.get("learning_ctx", {})
    retrieved_nodes = context.get("retrieved_nodes", [])
    plan = context.get("plan", {})
    reflection = context.get("reflection", {})
    analytics = context.get("analytics", {})

    mastery_pct = learning_ctx.get("mastery_score", 65.0)
    mastery_tier = "Beginner (<40%)" if mastery_pct < 40 else ("Intermediate (40-75%)" if mastery_pct <= 75 else "Advanced (>75%)")

    prompt_sections = [
        "================================================================================",
        "SYSTEM ROLE:",
        "You are a personal academic AI study mentor with perfect memory of this student's progress.",
        "Talk like ChatGPT or an expert professor in office hours: direct, empathetic, intelligent, and natural.",
        "",
        "GROUNDING DIRECTIVES (CRITICAL):",
        "1. Everything you state MUST originate strictly from the RETRIEVED KNOWLEDGE NODES, PLANNER OUTPUT, or LEARNING PROFILE below.",
        "2. Do NOT fabricate facts, invent unprovided exam dates, or guess missing concepts.",
        "3. Do NOT use template headers or mention internal agent names ('PlannerAgent', 'ReflectionAgent', 'DocumentAgent').",
        "4. Adapt your explanation depth based on the student's mastery level (" + mastery_tier + ").",
        "================================================================================",
        "",
        "CURRENT GOAL & CONTEXT:",
        f"  • User Query: \"{user_query}\"",
        f"  • Intent: {intent} | Subject Focus: {subject}",
        f"  • Student Mastery Tier: {mastery_tier} ({mastery_pct:.1f}%) | Retention: {learning_ctx.get('retention_score', 100.0):.1f}%",
        "",
        "RECENT CONVERSATION HISTORY (Pruned):",
        _format_conversation_history(history),
        "",
    ]

    if retrieved_nodes:
        prompt_sections.append("RETRIEVED KNOWLEDGE GRAPH NODES (Top-K Grounded Source):")
        for n in retrieved_nodes[:3]:
            prompt_sections.append(json.dumps({
                "citation_node_id": n.get("id"),
                "title": n.get("title"),
                "similarity_score": n.get("similarity_score"),
                "summary": n.get("summary"),
                "difficulty": n.get("difficulty"),
                "definitions": n.get("definitions"),
                "examples": n.get("examples"),
                "formulas": n.get("formulas"),
                "code_snippets": n.get("code_snippets"),
                "parents_prerequisites": n.get("parents"),
                "children": n.get("children")
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

    if analytics:
        prompt_sections.append("ANALYTICS SUMMARY:")
        prompt_sections.append(json.dumps(analytics, indent=2))
        prompt_sections.append("")

    prompt_sections.append("TASK:")
    prompt_sections.append("Generate a helpful, grounded Markdown response directly addressing the user query.")

    return "\n".join(prompt_sections)
