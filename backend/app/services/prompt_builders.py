"""
services/prompt_builders.py — Personal Academic Mentor Prompt Architecture

Dedicated prompt builders for Gemini API & Multi-Agent Swarm.
Engineered to deliver natural, human, ChatGPT-like academic mentorship
without exposing backend machinery or static template headers.
"""

from typing import Dict, Any, List


def _format_conversation_history(history: List[Dict[str, str]]) -> str:
    """Format recent Q&A turns into a clean conversational context block."""
    if not history:
        return ""
    lines = ["CONVERSATION HISTORY (Previous turns with this student):"]
    for turn in history[-6:]:  # Last 6 turns for concise context
        sender = "Student" if turn.get("role") == "user" else "Mentor"
        content = turn.get("content", "").strip()
        lines.append(f"{sender}: {content}")
    lines.append("")
    return "\n".join(lines)


def build_tutor_prompt(context: Dict[str, Any]) -> str:
    """
    Builds a grounded prompt for Socratic tutoring and natural explanation.
    Acts as an empathetic professor who adapts tone based on student mastery & history.
    """
    personality = context.get("personality", "Socratic Mentor")
    topic = context.get("topic", "Subject Concepts")
    subject = context.get("subject", "Academic Focus")
    mastery = context.get("mastery", 50.0)
    retention = context.get("retention", 100.0)
    user_answer = context.get("user_answer", "")
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
        prompt_lines.append("Provide a clear, engaging, grounded explanation or feedback directly answering their question.")
    else:
        prompt_lines.append(f"Provide a natural, engaging explanation of {topic} tailored to a student at {mastery:.0f}% mastery.")

    return "\n".join(prompt_lines)


def build_planner_explanation_prompt(context: Dict[str, Any]) -> str:
    """
    Builds a natural mentor rationale for prioritized study schedules.
    """
    tasks = context.get("tasks", [])
    available_minutes = context.get("available_minutes", 240)
    user_time_str = f"{available_minutes // 60}h {available_minutes % 60}m" if available_minutes >= 60 else f"{available_minutes}m"
    history = context.get("history", [])

    prompt_lines = [
        "You are a personal academic study coach helping a student structure their study session.",
        f"Available Study Time Today: {user_time_str}.",
        "",
        "MENTOR GUIDELINES:",
        "1. Write conversationally, as if speaking directly to the student.",
        "2. Explain WHY you recommend this breakdown (e.g. upcoming deadlines, low mastery, exam weight).",
        "3. NEVER mention internal agent names like 'PlannerAgent' or 'ReflectionAgent'.",
        "",
    ]

    history_str = _format_conversation_history(history)
    if history_str:
        prompt_lines.append(history_str)

    prompt_lines.append("RECOMMENDED STUDY SCHEDULE:")
    for idx, t in enumerate(tasks, 1):
        prompt_lines.append(
            f"{idx}. {t.get('title')} ({t.get('subject')}) — {t.get('recommended_minutes')}m "
            f"(Priority: {t.get('priority_score', 50):.0f}/100, Due in {t.get('days_remaining', 7)} days)"
        )

    prompt_lines.append("")
    prompt_lines.append("Present this schedule in a warm, encouraging, and actionable mentor tone.")

    return "\n".join(prompt_lines)


def build_reflection_prompt(context: Dict[str, Any]) -> str:
    """
    Builds prompt for ReflectionAgent workload auditing (JSON format).
    """
    available_minutes = context.get("available_minutes", 240)
    allocated_minutes = context.get("allocated_minutes", 0)
    items = context.get("items", [])

    prompt_lines = [
        "You are the Reflection & Workload Auditor Agent.",
        f"Time Budget: {available_minutes}m | Total Allocated: {allocated_minutes}m | Total Sessions: {len(items)}",
        "",
        "Audit the schedule for overload risk and return JSON format:",
        '{"is_valid": true/false, "replan_required": true/false, "confidence_score": 0.95, "warnings": [...], "recommendations": [...]}',
    ]

    return "\n".join(prompt_lines)


def build_chat_recommendation_prompt(context: Dict[str, Any]) -> str:
    """
    Builds prompt for general chat queries, greetings, analytics summaries, and follow-ups.
    """
    query = context.get("user_query", "")
    intent = context.get("intent", "general")
    subject = context.get("subject", "General")
    learning_ctx = context.get("learning_ctx", {})
    knowledge_graph = context.get("knowledge_graph")
    analytics = context.get("analytics")
    history = context.get("history", [])

    prompt_lines = [
        "You are a personal academic AI study mentor with full memory of this student's progress.",
        f"User Query: \"{query}\"",
        f"Context: Intent = {intent} | Subject Focus = {subject}",
        "",
        "MENTOR GUIDELINES:",
        "1. Be empathetic, intelligent, and direct. Talk like ChatGPT or an expert mentor.",
        "2. NEVER use template headers or list backend agent names (no 'DocumentAgent', 'StrategyAgent', etc.).",
        "3. If the user asks a follow-up ('Why?', 'Simplify that', 'Give another example', 'Continue'), reference the previous conversation naturally.",
        "4. If the prompt is ambiguous, ask a friendly clarifying question instead of guessing.",
        "",
    ]

    history_str = _format_conversation_history(history)
    if history_str:
        prompt_lines.append(history_str)

    if knowledge_graph and knowledge_graph.get("concepts"):
        prompt_lines.append(f"STUDENT'S UPLOADED MATERIAL ({knowledge_graph.get('subject')}):")
        for node in knowledge_graph.get("concepts", [])[:4]:
            prompt_lines.append(f"  - [{node.get('title')}]: {node.get('summary')}")
        prompt_lines.append("")

    if analytics:
        prompt_lines.append(f"STUDENT PROGRESS: {analytics.get('completion_rate', 0):.0f}% tasks completed, Burnout Risk: {analytics.get('burnout_risk_level', 'low')}.")

    if learning_ctx.get("has_learning_data"):
        weak = learning_ctx.get("weak_topics", [])
        if weak:
            prompt_lines.append(f"WEAK TOPICS: {', '.join(w['topic'] for w in weak[:3])}.")

    prompt_lines.append("")
    prompt_lines.append("Provide a helpful, precise, natural Markdown response.")

    return "\n".join(prompt_lines)


def build_document_analysis_prompt(text: str, filename: str) -> str:
    """
    Builds prompt for DocumentAgent knowledge graph extraction from PDF text.
    """
    return (
        f"You are an expert Academic Knowledge Graph Parser.\n"
        f"Document Title: {filename}\n"
        f"Extract key topics, definitions, prerequisite dependencies, code snippets, and formulas into JSON.\n\n"
        f"EXTRACTED TEXT (First 3000 chars):\n{text[:3000]}"
    )
