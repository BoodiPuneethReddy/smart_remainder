"""
services/document_graph.py — Semantic Knowledge Graph & Document Hierarchy Engine

Transforms raw extracted document text into a structured Semantic Knowledge Graph:
Document
  └── Units / Chapters
        └── TopicNode
              ├── topic_id
              ├── title
              ├── summary
              ├── learning_objectives
              ├── keywords
              ├── difficulty
              ├── est_minutes
              ├── supporting_paragraphs (list of text blocks)
              ├── definitions (list of {term, definition})
              ├── examples (list of example strings)
              ├── question_bank (list of {question, options, correct_answer, explanation})
              ├── prerequisites
              ├── next_topic_id
              └── prev_topic_id
"""

import re
import math
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class DefinitionBlock:
    term: str
    definition: str


@dataclass
class QuestionItem:
    question_id: str
    question_text: str
    options: List[str]
    correct_answer: str
    explanation: str


@dataclass
class TopicNode:
    topic_id: str
    title: str
    summary: str
    learning_objectives: List[str]
    keywords: List[str]
    difficulty: int
    est_minutes: int
    supporting_paragraphs: List[str]
    definitions: List[Dict[str, str]]
    examples: List[str]
    question_bank: List[Dict[str, Any]]
    prerequisites: List[str] = field(default_factory=list)
    prev_topic_id: Optional[str] = None
    next_topic_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SemanticTitleCleaner:
    """
    Normalizes headings and extracts clean semantic titles.
    Eliminates sentence fragments, pronouns, bullets, and trailing text.
    """

    @staticmethod
    def clean(line: str) -> str:
        if not line:
            return ""
        # 1. Remove leading bullets, numbers, and unit tags
        cleaned = re.sub(r'^[\uf0b7\u2022\-\*\#\s]+', '', line)
        cleaned = re.sub(r'^(?:unit[-\s]*[ivxlcdm0-9]+|chapter\s+\d+|section\s+\d+|part\s+\d+|[a-z0-9][\.\)]+)\s*', '', cleaned, flags=re.IGNORECASE).strip()
        
        # 2. Extract leading title phrase if line contains trailing sentence body
        if '.' in cleaned and not cleaned.endswith('.'):
            parts = cleaned.split('.')
            first_part = parts[0].strip()
            if len(first_part) < 60 and not any(kw in first_part.lower() for kw in ['according to', 'defined as', 'includes', 'consists of', 'model of', 'for example']):
                cleaned = first_part

        cleaned = cleaned.rstrip(':').rstrip('.').strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # 3. Suppress noise lines, single-word pronouns, and sentence fragments
        lower = cleaned.lower()
        fragment_starters = [
            'unit.', 'according to', 'the following', 'each level has', 'and software applications',
            'decision making', 'organization', 'models', 'domestic', 'offshore', 'for example',
            'themselves', 'however', 'in addition', 'furthermore', 'therefore', 'capability is provided'
        ]
        if any(lower.startswith(fs) or lower == fs for fs in fragment_starters):
            return ""

        if lower in ['themselves', 'itself', 'ourselves', 'myself', 'others', 'another']:
            return ""

        return cleaned.title() if len(cleaned) <= 50 and not cleaned.isupper() else cleaned


class DocumentGraphParser:
    """
    Parses extracted text into a structured Semantic Knowledge Graph.
    Divides text strictly by semantic section headings rather than token count.
    """

    @staticmethod
    def build_graph(text: str, filename: str) -> Dict[str, Any]:
        if not text or len(text.strip()) < 30:
            return {
                "document_title": filename,
                "subject": "General Study",
                "topics": []
            }

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        # Identify section boundaries
        sections: List[Dict[str, Any]] = []
        current_title = "Introduction & Foundations"
        current_paragraphs: List[str] = []

        for line in lines:
            line_clean = SemanticTitleCleaner.clean(line)
            line_lower = line.lower()

            is_heading = (
                (line.isupper() and len(line_clean) > 3 and len(line_clean) < 65)
                or line.endswith(":")
                or any(line_lower.startswith(p) for p in ["a)", "b)", "c)", "d)", "e)", "f)", "a).", "b).", "c).", "d).", "1.", "2.", "3.", "4.", "5."])
                or any(kw in line_lower for kw in ["introduction", "overview", "definitions", "principles", "theory", "types of", "classification", "mechanism", "structure", "functions", "evolution of", "drivers of", "components", "trends", "challenges", "role of", "applications"])
            )

            if is_heading and line_clean and len(line_clean) >= 4 and len(line_clean) <= 65:
                if current_paragraphs or sections:
                    sections.append({
                        "raw_title": line_clean,
                        "title": line_clean,
                        "paragraphs": current_paragraphs[:]
                    })
                    current_paragraphs = []
                current_title = line_clean
            else:
                current_paragraphs.append(line)

        if current_paragraphs:
            sections.append({
                "raw_title": current_title,
                "title": current_title,
                "paragraphs": current_paragraphs[:]
            })

        # Filter out empty sections
        valid_sections = [s for s in sections if s["paragraphs"] or len(sections) == 1]
        if not valid_sections:
            valid_sections = [{
                "raw_title": "Core Subject Concepts",
                "title": "Core Subject Concepts",
                "paragraphs": lines
            }]

        # Build Topic Nodes
        topic_nodes: List[TopicNode] = []
        total_sections = len(valid_sections)

        for idx, sec in enumerate(valid_sections):
            t_id = f"topic_{idx + 1}"
            title = sec["title"]
            paras = sec["paragraphs"]
            full_text = "\n".join(paras).strip()

            # Extract Definitions & Examples
            definitions = []
            examples = []
            for p in paras:
                if any(k in p.lower() for k in ["defined as", "is defined", "refers to", "means"]):
                    parts = re.split(r'\bis defined as\b|\brefers to\b|\bis defined\b', p, flags=re.IGNORECASE)
                    if len(parts) >= 2:
                        term = parts[0].strip()[:40]
                        defn = parts[1].strip()[:200]
                        definitions.append({"term": term, "definition": defn})
                if any(k in p.lower() for k in ["for example", "for instance", "e.g.", "such as"]):
                    examples.append(p[:250])

            # Extract Keywords
            words = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', full_text) if w.lower() not in ['this', 'that', 'with', 'from', 'have', 'were', 'their', 'which', 'other', 'also', 'such', 'into']]
            keywords = list(dict.fromkeys(words))[:6] or [title]

            # Generate Summary
            summary = (full_text[:220] + "...") if len(full_text) > 220 else (full_text or f"Key concepts and principles for {title}.")

            # Learning Objectives
            objectives = [
                f"Master fundamental concepts of {title}.",
                f"Explain structural mechanics and operational principles of {title}.",
                f"Apply {title} principles to practical domain scenarios."
            ]

            # Generate Topic-Specific Question Bank
            question_bank = []
            if paras:
                q_text = paras[0][:140].replace('\n', ' ')
                question_bank.append({
                    "question_id": f"{t_id}_q1",
                    "question_text": f"Based on the material for **{title}**, what is the primary operational purpose of: \"{q_text}...\"?",
                    "options": [
                        summary[:100],
                        "Arbitrary unverified operational assumption",
                        "Disabling structural domain constraints",
                        "None of the above"
                    ],
                    "correct_answer": summary[:100],
                    "explanation": f"Grounded directly in topic text: '{summary}'"
                })

            prev_id = f"topic_{idx}" if idx > 0 else None
            next_id = f"topic_{idx + 2}" if idx + 1 < total_sections else None

            node = TopicNode(
                topic_id=t_id,
                title=title,
                summary=summary,
                learning_objectives=objectives,
                keywords=keywords,
                difficulty=3,
                est_minutes=max(10, len(full_text.split()) // 20) if full_text else 15,
                supporting_paragraphs=paras,
                definitions=definitions,
                examples=examples,
                question_bank=question_bank,
                prerequisites=[f"topic_{idx}"] if idx > 0 else [],
                prev_topic_id=prev_id,
                next_topic_id=next_id
            )
            topic_nodes.append(node)

        # Detect Subject
        clean_fn = re.sub(r'[\-_]', ' ', filename).replace('.pdf', '').replace('.txt', '').strip()
        clean_fn_sub = re.sub(r'^(?:unit|chapter|section|part|doc|module|lab|lecture)[\s0-9\-_]*', '', clean_fn, flags=re.IGNORECASE).strip()
        subject = clean_fn_sub.title() if len(clean_fn_sub) > 3 and not clean_fn_sub.isdigit() else "General Academic Study"

        return {
            "document_title": filename,
            "subject": subject,
            "topics_count": len(topic_nodes),
            "topics": [node.to_dict() for node in topic_nodes]
        }


def build_document_knowledge_graph(extracted_text: str, filename: str = "Document") -> dict:
    """Convenience helper building knowledge graph dictionary for DocumentAgent."""
    result = DocumentGraphParser.build_graph(extracted_text, filename)
    
    nodes = []
    edges = []
    raw_topics = result.get("topics", [])
    for idx, t in enumerate(raw_topics):
        nodes.append({
            "title": t.get("title", f"Topic {idx+1}"),
            "chapter": f"Chapter {idx+1}",
            "summary": t.get("summary", ""),
            "difficulty": t.get("difficulty", 1),
            "prerequisites": t.get("prerequisites", []),
            "has_code": any(k in (t.get("summary", "")).lower() for k in ["code", "function", "class", "def", "int", "return"]),
            "has_formulas": any(k in (t.get("summary", "")).lower() for k in ["formula", "equation", "sum", "math"]),
        })
        if idx > 0:
            edges.append({"from": f"c{idx}", "to": f"c{idx+1}"})

    return {
        "subject": result.get("subject", "General Academic Study"),
        "doc_type": "Academic Notes",
        "nodes": nodes,
        "edges": edges,
        "features": ["concepts", "notes", "prerequisites"]
    }
