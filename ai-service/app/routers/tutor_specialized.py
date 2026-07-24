"""
ai-service/app/routers/tutor_specialized.py — Specialized AI Tutor Router

Handles:
  - tutor_init_prompt with behavioral matrix
  - tutor_evaluate_response with personality-driven feedback
  - tutor_generate_hint with mode-specific hints
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["tutor"])


class TutorRequest(BaseModel):
    task: str
    context: Dict[str, Any]


class TutorResponse(BaseModel):
    result: str
    text: str = ""


def generate_personality_prompt(personality: str, topic: str) -> str:
    """Generate personality-specific opening prompt."""
    openers = {
        "Friendly Teacher": f"😊 Let's explore **{topic}** together in a friendly way!",
        "Professor": f"🎓 Let us examine the theoretical foundations of **{topic}**.",
        "Interviewer": f"👔 Technical evaluation of your **{topic}** knowledge begins now.",
        "Exam Coach": f"🎯 Master **{topic}** for exam success with strategic focus.",
        "Socratic Tutor": f"🤔 Let's discover **{topic}** through guided questioning.",
    }
    return openers.get(personality, openers["Socratic Tutor"])


def generate_mode_specific_flow(mode: str, personality: str, topic: str, format_type: str) -> str:
    """Generate mode-specific instructional flow."""
    if mode == "Teach Me":
        return (
            f"I will explain **{topic}** with definitions, examples, and analogies. "
            f"Then I'll ask you a checkpoint question to verify understanding."
        )
    elif mode == "Test Me":
        return f"I will ask you a question about **{topic}** immediately. Answer without hints."
    elif mode == "Challenge Me":
        return f"I will present a challenging application scenario involving **{topic}**. Solve it with reasoning."
    elif mode == "Interview Me":
        return f"Mock interview format for **{topic}**. Answer fully; no hints provided."
    elif mode == "Revise":
        return f"Quick revision mode for **{topic}**. Fast-paced questions on weak areas."
    return "I will guide you through **{topic}** step by step."


def generate_assessment_instruction(fmt: str) -> str:
    """Generate format-specific instructions."""
    instructions = {
        "MCQ": "Questions will be formatted as multiple choice with 4 options. Select A, B, C, or D.",
        "Short Answer": "Answer in 1-2 sentences. I will evaluate conceptual accuracy.",
        "True/False": "Respond True or False. Explain your reasoning.",
        "Mixed": "Questions will alternate between MCQ, True/False, and Short Answer.",
    }
    return instructions.get(fmt, instructions["Mixed"])


def evaluate_with_personality(
    personality: str,
    topic: str,
    user_answer: str,
    avg_score: float,
    misconceptions: list
) -> str:
    """Generate personality-specific evaluation feedback."""
    
    if personality == "Friendly Teacher":
        if avg_score >= 80:
            return f"Excellent! You really understand **{topic}**! 🌟 Keep that momentum going!"
        elif avg_score >= 60:
            return f"Good effort on **{topic}**! You're on the right track. Let's strengthen a few concepts."
        else:
            return f"No worries! **{topic}** takes practice. Let's break it down together, step by step."
    
    elif personality == "Professor":
        if avg_score >= 80:
            return f"Your explanation demonstrates solid theoretical comprehension of **{topic}**."
        else:
            misconception_list = ", ".join(misconceptions[:2]) if misconceptions else "conceptual gaps"
            return f"Your response reveals {misconception_list} in the study of **{topic}**. Further rigor required."
    
    elif personality == "Interviewer":
        if avg_score >= 80:
            return f"Strong technical understanding of **{topic}**. You would advance in real interviews."
        else:
            return f"Your answer on **{topic}** lacks the clarity and depth required for senior-level positions."
    
    elif personality == "Exam Coach":
        if avg_score >= 80:
            marks = min(5, int(avg_score / 20))
            return f"**{marks}/5 marks awarded.** Excellent exam-ready response on **{topic}**."
        else:
            return f"This response would lose marks in exam evaluation. Focus on: definitions, mechanisms, examples for **{topic}**."
    
    else:  # Socratic Tutor
        if avg_score >= 80:
            return f"Excellent reasoning! You've discovered the essence of **{topic}**."
        else:
            return f"Interesting perspective. What do you think would happen if you applied **{topic}** differently?"


@router.post("/init", response_model=TutorResponse)
def tutor_init(request: TutorRequest):
    """Initialize tutor session with behavioral specialization."""
    try:
        ctx = request.context
        personality = ctx.get("teacher_personality", "Socratic Tutor")
        learning_mode = ctx.get("learning_mode", "Teach Me")
        assessment_type = ctx.get("assessment_type", "Mixed")
        target_goal = ctx.get("target_goal", "General Learning")
        topic = ctx.get("topic", "Concepts")
        topic_content = ctx.get("topic_content", "")
        difficulty = ctx.get("difficulty_level", 1)

        # Build personalized opening
        personality_opener = generate_personality_prompt(personality, topic)
        mode_flow = generate_mode_specific_flow(learning_mode, personality, topic, assessment_type)
        assessment_instr = generate_assessment_instruction(assessment_type)
        
        goal_text = {
            "College": "University Exam Level",
            "Placement": "Industry Placement & Interview",
            "GATE": "GATE Competitive Exam",
            "General Learning": "Foundational Concepts",
        }.get(target_goal, "General Learning")

        response_text = f"""{personality_opener}

**Learning Mode:** {learning_mode}
**Assessment Format:** {assessment_type}
**Target Level:** {goal_text}
**Difficulty:** Level {difficulty}/6

---

{mode_flow}

{assessment_instr}

"""
        
        if learning_mode in ["Test Me", "Challenge Me", "Interview Me"]:
            response_text += f"\n**Question 1:**\nBased on **{topic}**, what is the core principle or mechanism you understand?"
        else:
            if topic_content:
                response_text += f"\n### Overview of {topic}\n\n{topic_content[:300]}...\n\n**Now, let me ask you:**\nWhat do you already know about **{topic}**?"
            else:
                response_text += f"\n### Let's Begin\n\nTell me: What do you already know about **{topic}**?"

        return TutorResponse(result=response_text, text=response_text)
    
    except Exception as e:
        logger.error(f"Error in tutor_init: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate", response_model=TutorResponse)
def tutor_evaluate(request: TutorRequest):
    """Evaluate student answer with behavioral specialization."""
    try:
        ctx = request.context
        personality = ctx.get("teacher_personality", "Socratic Tutor")
        learning_mode = ctx.get("learning_mode", "Teach Me")
        assessment_type = ctx.get("assessment_type", "Mixed")
        user_answer = ctx.get("user_answer", "")
        topic = ctx.get("topic", "Concepts")
        topic_content = ctx.get("topic_content", "")

        # Simulate semantic evaluation
        answer_length = len(user_answer.strip())
        has_keywords = any(word in user_answer.lower() for word in topic.lower().split())
        
        # Score based on answer characteristics
        if answer_length < 10:
            understanding = 40
            reasoning = 30
            application = 20
            misconceptions = ["Answer is too brief"]
        elif answer_length < 50:
            understanding = 65
            reasoning = 55
            application = 50
            misconceptions = [] if has_keywords else ["Missing key terminology"]
        else:
            understanding = 85
            reasoning = 80
            application = 75
            misconceptions = []

        avg_score = (understanding + reasoning + application) / 3.0

        # Generate personality-specific evaluation
        evaluation = evaluate_with_personality(
            personality=personality,
            topic=topic,
            user_answer=user_answer,
            avg_score=avg_score,
            misconceptions=misconceptions
        )

        # Generate next question based on mode
        if learning_mode == "Socratic Tutor":
            next_q = f"Interesting. Why do you think **{topic}** works that way?"
        elif learning_mode == "Exam Coach":
            next_q = f"How would you structure an exam answer on **{topic}** to score maximum marks?"
        elif learning_mode == "Interviewer":
            next_q = f"Walk me through how you would apply **{topic}** in a real-world scenario."
        else:
            next_q = f"Can you give me a concrete example of **{topic}** in practice?"

        response_text = f"""{evaluation}

---

**Feedback:**
- Understanding: {understanding}/100
- Reasoning: {reasoning}/100
- Application: {application}/100

**Next Question:**
{next_q}
"""

        # Return as JSON for semantic parsing
        result_json = json.dumps({
            "explanation": evaluation,
            "understanding": understanding,
            "reasoning": reasoning,
            "application": application,
            "confidence": 88,
            "misconceptions": misconceptions,
            "strengths": ["Demonstrates engagement"] if answer_length > 20 else ["Attempt made"],
            "missing_points": ["Could expand explanation"] if answer_length < 100 else [],
            "next_question": next_q,
        })

        return TutorResponse(result=result_json, text=response_text)
    
    except Exception as e:
        logger.error(f"Error in tutor_evaluate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hint", response_model=TutorResponse)
def tutor_hint(request: TutorRequest):
    """Generate mode-specific hint."""
    try:
        ctx = request.context
        personality = ctx.get("teacher_personality", "Socratic Tutor")
        learning_mode = ctx.get("learning_mode", "Teach Me")
        topic = ctx.get("topic", "Concepts")
        attempt = ctx.get("attempt_number", 1)

        # Mode-specific hints
        if learning_mode == "Socratic Tutor":
            hints = {
                1: f"Think about the purpose of **{topic}**. What problem does it solve?",
                2: f"How would **{topic}** fail or behave differently if one aspect changed?",
                3: f"Can you relate **{topic}** to something you already know well?",
                4: f"**{topic}** is fundamental to understanding {topic}. Focus on the core principle."
            }
        elif learning_mode == "Exam Coach":
            hints = {
                1: f"State the exact definition of **{topic}** first.",
                2: f"List 2-3 characteristics or key equations for **{topic}**.",
                3: f"Draw or describe the structure or workflow of **{topic}**.",
                4: f"Examiners expect: definition + mechanism + example for **{topic}**."
            }
        elif learning_mode == "Interviewer":
            hints = {
                1: f"How would you implement **{topic}** in production?",
                2: f"What are the trade-offs or challenges with **{topic}**?",
                3: f"How does **{topic}** scale in large systems?",
                4: f"Describe a real scenario where **{topic}** is critical."
            }
        else:  # Teach Me / Test Me
            hints = {
                1: f"What is **{topic}** used for?",
                2: f"What are the key components of **{topic}**?",
                3: f"How does **{topic}** interact with related concepts?",
                4: f"**{topic}** fundamentally means: [core principle here]"
            }

        hint_text = hints.get(attempt, hints.get(4, "Keep thinking! You're on the right track."))
        
        return TutorResponse(result=hint_text, text=hint_text)
    
    except Exception as e:
        logger.error(f"Error in tutor_hint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
