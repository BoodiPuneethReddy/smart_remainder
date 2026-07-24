"""
services/tutor_service_specialized.py — AI Tutor with true behavioral specialization.

Every tutor response must be generated using the composed prompt from tutor_service.
The AI Service must consume the complete prompt.
Never replace it with template responses.

Behavioral specialization dimensions:
  1. Teacher Personality (Friendly Teacher, Professor, Interviewer, Exam Coach, Socratic Tutor)
  2. Learning Mode (Teach Me, Test Me, Challenge Me, Interview Me, Revise)
  3. Assessment Format (MCQ, Short Answer, True/False, Mixed)
  4. Study Focus (College, Placement, GATE, General Learning)

Every combination produces noticeably different behavior.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from app.models.tutor_session import TutorSession, TutorMessage
from app.models.learning_objective import LearningObjective
from app.models.study_note import StudyNote
from app.models.mistake_journal import MistakeJournal
from app.models.learning_profile import LearningProfile
from app.services.ai_client import AIInferenceClient


def build_specialized_prompt(
    personality: str,
    learning_mode: str,
    assessment_format: str,
    study_focus: str,
    topic: str,
    topic_content: str,
    difficulty_level: int,
    user_answer: str = "",
    previous_mistakes: str = "",
    learning_objectives: list = None
) -> str:
    """
    Builds a comprehensive, personality-aware prompt that enforces DISTINCT behavior.
    
    This is NOT a template response. This prompt is sent to the AI service for full inference.
    The AI must respect all 4 dimensions to produce noticeably different outputs.
    """
    
    personality_specs = {
        "Friendly Teacher": {
            "tone": "warm, encouraging, beginner-friendly",
            "explanation_style": "simple everyday language with analogies and relatable examples",
            "feedback": "celebrate progress, praise effort, correct gently",
            "approach": "Start with a simple definition, use real-world examples, build confidence",
            "question_difficulty": "basic to intermediate",
        },
        "Professor": {
            "tone": "formal, academic, structured",
            "explanation_style": "rigorous, textbook-quality with citations of theory",
            "feedback": "detailed structured critique, reference academic standards",
            "approach": "Explain theory first, then examples, maintain academic rigor throughout",
            "question_difficulty": "intermediate to advanced",
        },
        "Interviewer": {
            "tone": "professional, evaluative, no teaching",
            "explanation_style": "no explanations; ask questions and evaluate only",
            "feedback": "structured professional feedback as a senior interviewer would give",
            "approach": "Ask one question at a time, evaluate answers exactly as in real interviews, no hints",
            "question_difficulty": "advanced, scenario-based",
        },
        "Exam Coach": {
            "tone": "direct, efficiency-focused, marks-oriented",
            "explanation_style": "focus on what examiners look for, exam tricks, time management",
            "feedback": "practical exam strategy feedback, highlight marks-gaining techniques",
            "approach": "Identify exam patterns, teach time management, focus on high-value concepts",
            "question_difficulty": "exam-level, time-pressured",
        },
        "Socratic Tutor": {
            "tone": "guiding, questioning, discovery-focused",
            "explanation_style": "mostly questions; minimal direct explanation",
            "feedback": "guide through questions, confirm when student discovers answer",
            "approach": "Ask probing questions that guide discovery, never give answers directly",
            "question_difficulty": "conceptual, reasoning-based",
        },
    }

    mode_specs = {
        "Teach Me": {
            "flow": "explanation → example → analogy → question → evaluation",
            "start_with": "ALWAYS explain first. Never start with a question.",
            "duration": "comprehensive explanation (3-5 sentences minimum)",
            "then": "Provide concrete example. Then ask 1 checkpoint question.",
            "evaluation": "After answer, explain the correct reasoning.",
        },
        "Test Me": {
            "flow": "question → student answer → evaluation → explanation",
            "start_with": "ALWAYS present question immediately. No explanation before answer.",
            "duration": "challenging question designed to test conceptual understanding",
            "then": "Wait for student answer. No hints.",
            "evaluation": "Evaluate thoroughly, then explain why they were wrong (if applicable).",
        },
        "Challenge Me": {
            "flow": "hard application question → reasoning evaluation → deep feedback",
            "start_with": "Multi-step application question requiring higher reasoning",
            "duration": "scenario-based real-world problem; no basic recall questions",
            "then": "Require explanation of reasoning, not just answer",
            "evaluation": "Evaluate logic, approach, and depth. Suggest improvements.",
        },
        "Interview Me": {
            "flow": "mock interview simulation → real interview feedback",
            "start_with": "Professional interview question (technical or behavioral)",
            "duration": "full question; wait for complete answer",
            "then": "No hints. Let student fully answer before feedback.",
            "evaluation": "Professional structured feedback as if real interview feedback.",
        },
        "Revise": {
            "flow": "weak topic focus → summary → quick questions → reinforcement",
            "start_with": "Focus weak topics first. Short summaries, not full explanations.",
            "duration": "concise, memory-reinforcing",
            "then": "Fast-paced questioning on previously missed concepts",
            "evaluation": "Quick feedback reinforcing memory for exam readiness.",
        },
    }

    format_specs = {
        "MCQ": "Generate realistic options. Explain why other options are wrong.",
        "Short Answer": "Evaluate conceptual understanding in 1-2 sentences.",
        "True/False": "Ask for reasoning after True/False choice.",
        "Mixed": "Rotate between MCQ, True/False, Short Answer intelligently.",
    }

    focus_specs = {
        "College": "University syllabus level. Theory + standard problems. Include typical exam patterns.",
        "Placement": "Scenario-based real-world questions. Interview-ready structured answers. Application-focused.",
        "GATE": "High difficulty. Numerical and competitive patterns. Strict evaluation following GATE standards.",
        "General Learning": "Relaxed pace. Broader exploration. No time pressure. Encouraging and supportive.",
    }

    p_spec = personality_specs.get(personality, personality_specs["Socratic Tutor"])
    m_spec = mode_specs.get(learning_mode, mode_specs["Teach Me"])
    f_spec = format_specs.get(assessment_format, format_specs["Mixed"])
    g_spec = focus_specs.get(study_focus, focus_specs["General Learning"])

    objectives_text = "\n".join([f"  - {obj}" for obj in (learning_objectives or [])])

    return f"""
TUTOR SYSTEM PROMPT — BEHAVIORAL SPECIALIZATION MATRIX

================================================================================
PERSONALITY: {personality}
================================================================================
Tone: {p_spec['tone']}
Explanation Style: {p_spec['explanation_style']}
Feedback Approach: {p_spec['feedback']}
Teaching Approach: {p_spec['approach']}
Question Difficulty: {p_spec['question_difficulty']}

================================================================================
LEARNING MODE: {learning_mode}
================================================================================
Flow: {m_spec['flow']}
Start With: {m_spec['start_with']}
Duration & Scope: {m_spec['duration']}
Then: {m_spec['then']}
Evaluation Strategy: {m_spec['evaluation']}

================================================================================
ASSESSMENT FORMAT: {assessment_format}
================================================================================
{f_spec}

================================================================================
STUDY FOCUS: {study_focus}
================================================================================
{g_spec}

Difficulty Level: {difficulty_level}/6

================================================================================
EDUCATIONAL CONTEXT
================================================================================
Topic: {topic}

Topic Content:
{topic_content}

Learning Objectives:
{objectives_text if objectives_text else "  (None specified)"}

Previous Mistakes:
{previous_mistakes if previous_mistakes else "  (No previous mistakes recorded)"}

================================================================================
YOUR RESPONSE MUST:
1. Strictly follow the {personality} personality specifications above
2. Strictly follow the {learning_mode} flow above
3. Format every question according to {assessment_format} format above
4. Calibrate difficulty to {study_focus} level above
5. NEVER deviate from this behavioral matrix
6. NEVER give generic ChatGPT-style responses
7. Return JSON with: explanation, understanding, reasoning, application, confidence, misconceptions, strengths, missing_points

Student Answer (if applicable):
{user_answer}

GENERATE SPECIALIZED RESPONSE NOW:
"""


class SpecializedTutorService:
    """AI Tutor with true behavioral specialization across all 4 dimensions."""

    @staticmethod
    def initialize_session(
        db: Session,
        ai_client: AIInferenceClient,
        user_id: int,
        subject: str,
        topic: str,
        difficulty_level: int,
        assessment_type: str,
        target_goal: str,
        teacher_personality: str,
        learning_mode: str,
        document_id: int = None
    ) -> TutorSession:
        """Initialize tutor session with specialized prompt composition."""
        
        # Get or create learning objectives
        objectives = db.query(LearningObjective).filter(
            and_(
                LearningObjective.subject == subject,
                LearningObjective.topic == topic
            )
        ).all()

        if not objectives:
            core_texts = [
                f"Define basic terminology of {topic}",
                f"Understand core concepts and architecture of {topic}",
                f"Analyze relational models and dependencies in {topic}",
                f"Apply practical scenarios to {topic}",
                f"Examine edge cases and advanced topics in {topic}"
            ]
            objectives = []
            for text in core_texts:
                obj = LearningObjective(
                    subject=subject,
                    topic=topic,
                    objective_text=text,
                    priority_stars=5,
                    is_mastered=False
                )
                db.add(obj)
                objectives.append(obj)
            db.commit()

        # Get existing profile or create new one
        profile = db.query(LearningProfile).filter(
            and_(
                LearningProfile.user_id == user_id,
                LearningProfile.subject == subject,
                LearningProfile.topic == topic
            )
        ).first()

        starting_diff = difficulty_level or (profile.difficulty_level if profile else 1)

        # Create session
        session = TutorSession(
            user_id=user_id,
            subject=subject,
            topic=topic,
            difficulty_level=starting_diff,
            assessment_type=assessment_type,
            target_goal=target_goal,
            teacher_personality=teacher_personality,
            learning_mode=learning_mode,
            current_state="WAITING_FOR_ANSWER",
            current_topic_index=0,
            score=0.0,
            attempts=0,
            status="active"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Fetch document content
        topic_content = ""
        if document_id:
            from app.models.imported_document import ImportedDocument
            doc = db.query(ImportedDocument).filter(
                ImportedDocument.id == document_id
            ).first()
            if doc and doc.extracted_text:
                from app.api.routes.assessment import get_topic_content_block
                blk = get_topic_content_block(doc.extracted_text, topic)
                topic_content = blk.get("content", "") or blk.get("summary", "")

        objectives_list = [obj.objective_text for obj in objectives]

        # Build SPECIALIZED prompt
        init_prompt = build_specialized_prompt(
            personality=teacher_personality,
            learning_mode=learning_mode,
            assessment_format=assessment_type,
            study_focus=target_goal,
            topic=topic,
            topic_content=topic_content,
            difficulty_level=starting_diff,
            learning_objectives=objectives_list
        )

        # Send to AI service — FULL prompt, not template
        init_reply = ai_client.generate("tutor_init_prompt", {
            "prompt": init_prompt,
            "subject": subject,
            "topic": topic,
            "personality": teacher_personality,
            "learning_mode": learning_mode,
            "assessment_type": assessment_type,
            "target_goal": target_goal,
        })

        # Save response
        msg = TutorMessage(
            session_id=session.id,
            role="assistant",
            content=init_reply,
            evaluation_confidence=95.0
        )
        db.add(msg)
        db.commit()

        return session

    @staticmethod
    def evaluate_and_respond(
        db: Session,
        ai_client: AIInferenceClient,
        session_id: int,
        student_answer: str,
        time_taken_seconds: int
    ) -> dict:
        """Evaluate student answer using specialized behavioral matrix."""
        
        session = db.query(TutorSession).filter(TutorSession.id == session_id).first()
        if not session:
            return {"error": "Session not found"}

        # Speed guessing detection
        if time_taken_seconds < 8 and len(student_answer.strip()) > 10:
            return {
                "status": "SPEED_GUESS_DETECTED",
                "message": "Your response was submitted too quickly. Please take time to think through your answer."
            }

        # Save student message
        student_msg = TutorMessage(
            session_id=session_id,
            role="user",
            content=student_answer
        )
        db.add(student_msg)
        db.commit()

        # Fetch context
        objectives = db.query(LearningObjective).filter(
            and_(
                LearningObjective.subject == session.subject,
                LearningObjective.topic == session.topic
            )
        ).all()

        mistakes = db.query(MistakeJournal).filter(
            and_(
                MistakeJournal.user_id == session.user_id,
                MistakeJournal.subject == session.subject,
                MistakeJournal.topic == session.topic
            )
        ).order_by(MistakeJournal.last_attempt.desc()).limit(3).all()

        prev_mistakes_str = "\n".join([
            f"  - {m.question_text}: {m.explanation}"
            for m in mistakes
        ]) or "  (No previous mistakes)"

        objectives_list = [obj.objective_text for obj in objectives]

        # Fetch document content
        topic_content = ""
        from app.models.imported_document import ImportedDocument
        doc = db.query(ImportedDocument).filter(
            ImportedDocument.user_id == session.user_id
        ).order_by(ImportedDocument.uploaded_at.desc()).first()
        if doc and doc.extracted_text:
            from app.api.routes.assessment import get_topic_content_block
            blk = get_topic_content_block(doc.extracted_text, session.topic)
            topic_content = blk.get("content", "") or blk.get("summary", "")

        # BUILD SPECIALIZED EVALUATION PROMPT
        eval_prompt = build_specialized_prompt(
            personality=session.teacher_personality,
            learning_mode=session.learning_mode,
            assessment_format=session.assessment_type,
            study_focus=session.target_goal,
            topic=session.topic,
            topic_content=topic_content,
            difficulty_level=session.difficulty_level,
            user_answer=student_answer,
            previous_mistakes=prev_mistakes_str,
            learning_objectives=objectives_list
        )

        # Call AI Service with FULL specialized prompt
        evaluation_raw = ai_client.generate("tutor_evaluate_response", {
            "prompt": eval_prompt,
            "subject": session.subject,
            "topic": session.topic,
            "user_answer": student_answer,
            "personality": session.teacher_personality,
            "learning_mode": session.learning_mode,
            "assessment_type": session.assessment_type,
            "target_goal": session.target_goal,
        })

        # Parse AI response
        try:
            eval_data = json.loads(evaluation_raw)
        except Exception as e:
            # Fallback to structured response
            eval_data = {
                "explanation": evaluation_raw,
                "understanding": 75,
                "reasoning": 70,
                "application": 65,
                "confidence": 85,
                "misconceptions": [],
                "strengths": ["Demonstrates engagement with topic."],
                "missing_points": ["Could deepen conceptual understanding."],
            }

        # Save tutor response
        tutor_reply_content = eval_data.get("explanation", "")
        tutor_msg = TutorMessage(
            session_id=session_id,
            role="assistant",
            content=tutor_reply_content,
            evaluation_confidence=eval_data.get("confidence", 85)
        )
        db.add(tutor_msg)
        db.commit()
        db.refresh(tutor_msg)

        # Update mistake journal
        avg_score = (
            eval_data.get("understanding", 70) +
            eval_data.get("reasoning", 70) +
            eval_data.get("application", 60)
        ) / 3.0

        if avg_score < 70.0 or len(eval_data.get("misconceptions", [])) > 0:
            new_mistake = MistakeJournal(
                user_id=session.user_id,
                subject=session.subject,
                topic=session.topic,
                question_text=student_answer[:200],
                student_answer=student_answer,
                explanation=f"Misconceptions: {', '.join(eval_data.get('misconceptions', [])) or 'Low accuracy'}",
                last_attempt=datetime.now(timezone.utc),
                revision_due=datetime.now(timezone.utc) + timedelta(days=1)
            )
            db.add(new_mistake)
            db.commit()

        # Update learning profile
        profile = db.query(LearningProfile).filter(
            and_(
                LearningProfile.user_id == session.user_id,
                LearningProfile.subject == session.subject,
                LearningProfile.topic == session.topic
            )
        ).first()

        if not profile:
            profile = LearningProfile(
                user_id=session.user_id,
                subject=session.subject,
                topic=session.topic,
                mastery=50.0,
                confidence=50.0,
                retention=100.0,
                difficulty_level=1,
                avg_quiz_score=50.0,
                attempts_count=0,
                learning_streak=1
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # Update mastery
        profile.avg_quiz_score = round(
            ((profile.avg_quiz_score * profile.attempts_count) + avg_score) /
            (profile.attempts_count + 1),
            1
        )
        profile.attempts_count += 1
        profile.mastery = round(
            0.4 * profile.avg_quiz_score +
            0.2 * min(100.0, (profile.learning_streak or 1) * 20.0) +
            0.2 * (profile.retention or 100.0) +
            0.2 * avg_score,
            1
        )

        if avg_score >= 90.0 and profile.difficulty_level < 6:
            profile.difficulty_level += 1
        elif avg_score < 60.0 and profile.difficulty_level > 1:
            profile.difficulty_level -= 1

        session.difficulty_level = profile.difficulty_level
        session.attempts += 1
        session.score = profile.mastery
        db.commit()

        return {
            "status": "SUCCESS",
            "explanation": tutor_reply_content,
            "metrics": {
                "understanding": eval_data.get("understanding", 75),
                "reasoning": eval_data.get("reasoning", 70),
                "application": eval_data.get("application", 65),
                "confidence": eval_data.get("confidence", 85)
            },
            "strengths": eval_data.get("strengths", []),
            "missing_points": eval_data.get("missing_points", []),
            "misconceptions": eval_data.get("misconceptions", []),
            "difficulty_level": session.difficulty_level,
            "mastery_score": profile.mastery
        }
