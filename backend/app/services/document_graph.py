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
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# ─── Subject keyword maps for automatic doc_type detection ────────────────────

_SUBJECT_SIGNALS: List[tuple[str, str, List[str]]] = [
    # (doc_type, display_name, keyword_list)
    ("DBMS",   "Database Management Systems",   ["sql", "normalization", "relational", "entity", "er diagram", "primary key", "foreign key", "join", "transaction", "acid", "database", "schema", "tuple", "attribute", "query", "triggers", "views", "indexing", "bcnf", "3nf", "2nf", "cursor"]),
    ("DSA",    "Data Structures & Algorithms",  ["recursion", "algorithm", "linked list", "binary tree", "graph", "heap", "sorting", "searching", "array", "stack", "queue", "dynamic programming", "time complexity", "space complexity", "big o", "traversal", "bfs", "dfs", "dijkstra"]),
    ("OS",     "Operating Systems",             ["process", "thread", "deadlock", "memory", "paging", "segmentation", "scheduling", "semaphore", "mutex", "critical section", "context switch", "virtual memory", "kernel", "system call", "interrupt", "disk scheduling", "cpu scheduling"]),
    ("MATH",   "Mathematics",                   ["matrix", "integral", "derivative", "theorem", "proof", "vector", "eigenvalue", "differential equation", "polynomial", "limit", "fourier", "laplace", "probability", "statistics", "calculus"]),
    ("NETWORK","Computer Networks",             ["protocol", "tcp", "udp", "ip", "routing", "subnet", "dns", "http", "osi model", "bandwidth", "latency", "arp", "mac address", "socket", "packet", "frame"]),
    ("SE",     "Software Engineering",          ["agile", "scrum", "design pattern", "uml", "requirement", "use case", "sdlc", "testing", "deployment", "microservice", "api", "rest", "solid principle"]),
    ("ML",     "Machine Learning / AI",         ["neural network", "gradient descent", "overfitting", "classification", "regression", "clustering", "epoch", "loss function", "training", "feature", "backpropagation", "model", "dataset"]),
]

_FEATURE_SIGNALS: Dict[str, List[str]] = {
    "sql":      ["select", "insert", "update", "delete", "join", "where", "group by", "having", "create table"],
    "code":     ["def ", "class ", "function", "int ", "return ", "for i", "while ", "import ", "algorithm"],
    "formulas": ["formula", "equation", "sum of", "integral", "derivative", "sigma", "∑", "∫", "dx", "=", "theorem"],
    "diagrams": ["figure", "diagram", "chart", "table", "graph shows", "illustrated"],
}


def _detect_subject_and_features(text: str, filename: str) -> tuple[str, str, List[str]]:
    """
    Scan document text to detect subject domain and content features.
    Returns (doc_type, display_subject, features_list).
    """
    text_lower = text.lower()
    filename_lower = filename.lower()

    best_doc_type = None
    best_display = None
    best_count = 0

    for doc_type, display, keywords in _SUBJECT_SIGNALS:
        count = sum(1 for kw in keywords if kw in text_lower or kw in filename_lower)
        if count > best_count:
            best_count = count
            best_doc_type = doc_type
            best_display = display

    # Fallback: derive from filename
    if not best_doc_type or best_count < 2:
        clean_fn = re.sub(r'[\-_]', ' ', filename).replace('.pdf', '').replace('.txt', '').strip()
        clean_fn = re.sub(r'^(?:unit|chapter|section|part|doc|module|lab|lecture)[\s0-9\-_]*', '', clean_fn, flags=re.IGNORECASE).strip()
        best_display = clean_fn.title() if len(clean_fn) > 3 and not clean_fn.isdigit() else "General Academic Study"
        best_doc_type = "ACADEMIC"

    # Detect content features
    features = []
    for feature_name, signals in _FEATURE_SIGNALS.items():
        if any(sig in text_lower for sig in signals):
            features.append(feature_name)

    if not features:
        features = ["concepts", "notes"]

    # Always add prerequisites as a universal feature
    if "prerequisites" not in features:
        features.append("prerequisites")

    return best_doc_type, best_display, features


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
    """Normalizes headings and extracts clean semantic titles."""

    @staticmethod
    def clean(line: str) -> str:
        if not line:
            return ""
        cleaned = re.sub(r'^[\uf0b7\u2022\-\*\#\s]+', '', line)
        cleaned = re.sub(r'^(?:unit[-\s]*[ivxlcdm0-9]+|chapter\s+\d+|section\s+\d+|part\s+\d+|[a-z0-9][\.\)]+)\s*', '', cleaned, flags=re.IGNORECASE).strip()

        if '.' in cleaned and not cleaned.endswith('.'):
            parts = cleaned.split('.')
            first_part = parts[0].strip()
            if len(first_part) < 60 and not any(kw in first_part.lower() for kw in ['according to', 'defined as', 'includes', 'consists of', 'model of', 'for example']):
                cleaned = first_part

        cleaned = cleaned.rstrip(':').rstrip('.').strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)

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
    Divides text strictly by semantic section headings.
    """

    @staticmethod
    def build_graph(text: str, filename: str) -> Dict[str, Any]:
        if not text or len(text.strip()) < 30:
            return {
                "document_title": filename,
                "subject": "General Study",
                "doc_type": "ACADEMIC",
                "features": ["concepts", "notes", "prerequisites"],
                "topics": []
            }

        # Detect subject and features from full text BEFORE sectioning
        doc_type, display_subject, features = _detect_subject_and_features(text, filename)

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        sections: List[Dict[str, Any]] = []
        current_title = "Introduction & Foundations"
        current_paragraphs: List[str] = []

        for line in lines:
            line_clean = SemanticTitleCleaner.clean(line)
            line_lower = line.lower()

            is_heading = (
                (line.isupper() and len(line_clean) > 3 and len(line_clean) < 65)
                or line.endswith(":")
                or any(line_lower.startswith(p) for p in ["a)", "b)", "c)", "d)", "e)", "f)", "1.", "2.", "3.", "4.", "5."])
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

        valid_sections = [s for s in sections if s["paragraphs"] or len(sections) == 1]
        if not valid_sections:
            valid_sections = [{
                "raw_title": "Core Subject Concepts",
                "title": "Core Subject Concepts",
                "paragraphs": lines
            }]

        topic_nodes: List[TopicNode] = []
        total_sections = len(valid_sections)

        for idx, sec in enumerate(valid_sections):
            t_id = f"topic_{idx + 1}"
            title = sec["title"]
            paras = sec["paragraphs"]
            full_text = "\n".join(paras).strip()

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

            words = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', full_text) if w.lower() not in ['this', 'that', 'with', 'from', 'have', 'were', 'their', 'which', 'other', 'also', 'such', 'into']]
            keywords = list(dict.fromkeys(words))[:6] or [title]

            summary = (full_text[:220] + "...") if len(full_text) > 220 else (full_text or f"Key concepts and principles for {title}.")

            objectives = [
                f"Master fundamental concepts of {title}.",
                f"Explain structural mechanics and operational principles of {title}.",
                f"Apply {title} principles to practical domain scenarios."
            ]

            # Difficulty scales with section index (later sections = harder)
            difficulty = min(6, 1 + (idx * 6 // max(total_sections, 1)))

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
                difficulty=difficulty,
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

        return {
            "document_title": filename,
            "subject": display_subject,
            "doc_type": doc_type,
            "features": features,
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
        summary_lower = (t.get("summary", "")).lower()
        nodes.append({
            "title": t.get("title", f"Topic {idx+1}"),
            "chapter": f"Chapter {idx+1}",
            "summary": t.get("summary", ""),
            "difficulty": t.get("difficulty", 1),
            "prerequisites": t.get("prerequisites", []),
            "keywords": t.get("keywords", []),
            "definitions": t.get("definitions", []),
            "examples": t.get("examples", []),
            "est_minutes": t.get("est_minutes", 15),
            "has_code": any(k in summary_lower for k in ["code", "function", "class", "def", "int", "return", "algorithm", "recursion"]),
            "has_formulas": any(k in summary_lower for k in ["formula", "equation", "sum", "math", "integral", "derivative"]),
        })
        if idx > 0:
            edges.append({"from": f"c{idx}", "to": f"c{idx+1}"})

    return {
        "subject": result.get("subject", "General Academic Study"),
        "doc_type": result.get("doc_type", "ACADEMIC"),
        "nodes": nodes,
        "edges": edges,
        "features": result.get("features", ["concepts", "notes", "prerequisites"])
    }


def merge_knowledge_graphs(graphs: List[dict]) -> dict:
    """
    Merge multiple knowledge graph dictionaries of the SAME subject domain.
    Deduplicates nodes by title, re-indexes chapters, and merges edges and features.
    """
    if not graphs:
        return {
            "subject": "General Academic Study",
            "doc_type": "ACADEMIC",
            "nodes": [],
            "edges": [],
            "features": ["concepts", "notes", "prerequisites"]
        }
    if len(graphs) == 1:
        return graphs[0]

    merged_subject = graphs[0].get("subject", "General Academic Study")
    merged_doc_type = graphs[0].get("doc_type", "ACADEMIC")

    seen_titles = set()
    combined_nodes = []
    combined_features = set()

    for g in graphs:
        combined_features.update(g.get("features", []))
        for n in g.get("nodes", []):
            t_lower = n.get("title", "").strip().lower()
            if t_lower and t_lower not in seen_titles:
                seen_titles.add(t_lower)
                # Clone node with re-indexed chapter
                node_copy = dict(n)
                node_copy["chapter"] = f"Chapter {len(combined_nodes) + 1}"
                combined_nodes.append(node_copy)

    combined_edges = []
    for idx in range(len(combined_nodes) - 1):
        combined_edges.append({"from": f"c{idx+1}", "to": f"c{idx+2}"})

    return {
        "subject": merged_subject,
        "doc_type": merged_doc_type,
        "nodes": combined_nodes,
        "edges": combined_edges,
        "features": list(combined_features)
    }

