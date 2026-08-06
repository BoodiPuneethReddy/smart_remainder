"""
agents/retrieval_agent.py — Top-5 Semantic Retrieval & Reranking Agent

Traverses 12-Stage Document Knowledge Graphs and concept node stores to retrieve,
rerank, and compress the Top-5 relevant concept nodes with explicit similarity scores,
rankings, parents, children, definitions, examples, code, and formulas.
"""

import logging
import re
from typing import List, Optional, Dict, Any
from app.agents.models import KnowledgeGraphModel, ConceptNode, ScoredConceptNode

logger = logging.getLogger(__name__)


def _create_dbms_normalization_graph() -> KnowledgeGraphModel:
    """Standard DBMS 12-Stage Knowledge Graph fallback when no PDF document is uploaded."""
    return KnowledgeGraphModel(
        subject="Database Management Systems",
        concepts=[
            ConceptNode(
                id="norm_01",
                title="Normalization",
                summary="Process of organizing database attributes and relations to minimize redundancy and prevent insertion, update, and deletion anomalies.",
                chapter="Chapter 4: Database Design",
                difficulty=4,
                definitions=[{"term": "Normalization", "definition": "Systematic approach of decomposing tables to eliminate data redundancy."}],
                examples=["Decomposing a non-loss Student-Course table into Student and Enrollment tables."],
                formulas=["R = R1 U R2 with (R1 ∩ R2) -> R1 or (R1 ∩ R2) -> R2"],
                code_snippets=["ALTER TABLE Enrollment ADD CONSTRAINT fk_student FOREIGN KEY (student_id) REFERENCES Student(id);"],
                parents=["fd_01", "ck_01"],
                children=["1nf_01", "2nf_01", "3nf_01", "bcnf_01"]
            ),
            ConceptNode(
                id="fd_01",
                title="Functional Dependency",
                summary="Constraint X -> Y between two sets of attributes in a relation, stating X uniquely determines Y.",
                chapter="Chapter 4: Database Design",
                difficulty=3,
                definitions=[{"term": "Functional Dependency", "definition": "Relationship where attribute set X uniquely determines attribute set Y."}],
                examples=["Student_ID -> {Name, Department, Email}"],
                formulas=["If t1[X] = t2[X], then t1[Y] = t2[Y]"],
                code_snippets=[],
                parents=[],
                children=["norm_01"]
            ),
            ConceptNode(
                id="ck_01",
                title="Candidate Keys",
                summary="Minimal superkey with no redundant attributes capable of uniquely identifying tuples.",
                chapter="Chapter 4: Database Design",
                difficulty=3,
                definitions=[{"term": "Candidate Key", "definition": "Superkey K such that no proper subset of K is a superkey."}],
                examples=["{SSN} or {Student_ID, Course_Code}"],
                formulas=[],
                code_snippets=[],
                parents=[],
                children=["norm_01"]
            ),
            ConceptNode(
                id="1nf_01",
                title="1NF (First Normal Form)",
                summary="Requires all attribute values to be atomic (indivisible) with no repeating groups.",
                chapter="Chapter 4: Database Design",
                difficulty=2,
                definitions=[{"term": "1NF", "definition": "Domain of each attribute contains atomic values."}],
                examples=["Splitting multi-valued phone numbers into separate rows."],
                formulas=[],
                code_snippets=[],
                parents=["norm_01"],
                children=["2nf_01"]
            ),
            ConceptNode(
                id="2nf_01",
                title="2NF (Second Normal Form)",
                summary="In 1NF and no non-prime attribute is partially dependent on any candidate key.",
                chapter="Chapter 4: Database Design",
                difficulty=3,
                definitions=[{"term": "2NF", "definition": "Eliminates partial functional dependencies on composite keys."}],
                examples=["Moving Course_Name out of (Student_ID, Course_ID) table to Course table."],
                formulas=[],
                code_snippets=[],
                parents=["1nf_01"],
                children=["3nf_01"]
            ),
            ConceptNode(
                id="3nf_01",
                title="3NF (Third Normal Form)",
                summary="In 2NF and no non-prime attribute is transitively dependent on a candidate key.",
                chapter="Chapter 4: Database Design",
                difficulty=4,
                definitions=[{"term": "3NF", "definition": "X -> A implies X is superkey or A is prime attribute."}],
                examples=["Moving Zip_Code -> City mapping to separate Location table."],
                formulas=[],
                code_snippets=[],
                parents=["2nf_01"],
                children=["bcnf_01"]
            ),
            ConceptNode(
                id="bcnf_01",
                title="BCNF (Boyce-Codd Normal Form)",
                summary="Strict version of 3NF where for every non-trivial functional dependency X -> Y, X must be a superkey.",
                chapter="Chapter 4: Database Design",
                difficulty=5,
                definitions=[{"term": "BCNF", "definition": "Every determinant X in non-trivial FD X -> Y is a superkey."}],
                examples=["Handling overlapping candidate keys in Advisor-Student schemas."],
                formulas=["For all X -> Y, X is a superkey"],
                code_snippets=[],
                parents=["3nf_01"],
                children=[]
            )
        ],
        prerequisite_edges=[
            {"from": "fd_01", "to": "norm_01"},
            {"from": "ck_01", "to": "norm_01"},
            {"from": "norm_01", "to": "1nf_01"},
            {"from": "1nf_01", "to": "2nf_01"},
            {"from": "2nf_01", "to": "3nf_01"},
            {"from": "3nf_01", "to": "bcnf_01"}
        ]
    )


def retrieve_top_k_nodes(
    query: str,
    knowledge_graph: Optional[KnowledgeGraphModel],
    top_k: int = 5,
) -> List[ScoredConceptNode]:
    """
    Top-5 Retrieval, Reranking, and Context Compression algorithm.
    Uses exact word-boundary matching and prerequisite graph edge traversal.
    """
    if not knowledge_graph or not knowledge_graph.concepts:
        knowledge_graph = _create_dbms_normalization_graph()

    q_clean = query.lower().strip()
    q_terms = [t for t in re.findall(r'\b\w+\b', q_clean) if len(t) > 2]

    if not q_terms:
        logger.info("RetrievalAgent: Query contains no academic search terms; returning empty concept set.")
        return []

    parent_map: Dict[str, List[str]] = {}
    child_map: Dict[str, List[str]] = {}
    for edge in knowledge_graph.prerequisite_edges:
        f_id, t_id = edge.get("from"), edge.get("to")
        if f_id and t_id:
            parent_map.setdefault(t_id, []).append(f_id)
            child_map.setdefault(f_id, []).append(t_id)

    candidates: List[tuple[float, ConceptNode]] = []

    for concept in knowledge_graph.concepts:
        score = 0.0
        t_lower = concept.title.lower()
        s_lower = concept.summary.lower()

        # 1. Exact title word match
        if q_clean == t_lower:
            score += 95.0
        elif re.search(r'\b' + re.escape(q_clean) + r'\b', t_lower):
            score += 85.0

        # 2. Term overlap (word boundary enforcing)
        for term in q_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', t_lower):
                score += 35.0
            elif re.search(r'\b' + re.escape(term) + r'\b', s_lower):
                score += 15.0

        # 3. Domain topic keyword matching
        if any(k in q_clean for k in ["normaliz", "bcnf", "3nf", "2nf", "1nf", "functional dependency", "candidate key"]):
            if any(k in t_lower for k in ["normaliz", "bcnf", "3nf", "2nf", "1nf", "functional dependency", "candidate key"]):
                score += 40.0

        # 4. Detail richness bonus
        if concept.definitions:
            score += 5.0
        if concept.examples:
            score += 5.0
        if concept.formulas:
            score += 5.0

        concept.parents = parent_map.get(concept.id, [])
        concept.children = child_map.get(concept.id, [])

        norm_score = min(99.0, max(0.0, score))
        if norm_score > 0:
            candidates.append((norm_score, concept))

    # Sort descending by score
    candidates.sort(key=lambda x: x[0], reverse=True)

    reranked: List[ScoredConceptNode] = []
    for rank, (score, concept) in enumerate(candidates[:top_k], 1):
        reranked.append(ScoredConceptNode(
            rank_position=rank,
            similarity_score=round(score, 1),
            node=concept
        ))

    logger.info("RetrievalAgent: Retrieved & Reranked Top-%d nodes (Top-1: '%s' @ %.1f%%)", len(reranked), reranked[0].node.title if reranked else 'None', reranked[0].similarity_score if reranked else 0.0)
    return reranked
