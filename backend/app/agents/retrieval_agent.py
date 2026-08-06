"""
agents/retrieval_agent.py — Top-K Semantic Retrieval Agent

Traverses 12-Stage Document Knowledge Graphs and concept node stores
to retrieve the Top-K relevant concept nodes with explicit similarity scores,
rankings, parents, children, definitions, examples, code, and formulas.
"""

import logging
import re
from typing import List, Optional, Dict, Any
from app.agents.models import KnowledgeGraphModel, ConceptNode, ScoredConceptNode

logger = logging.getLogger(__name__)


def retrieve_top_k_nodes(
    query: str,
    knowledge_graph: Optional[KnowledgeGraphModel],
    top_k: int = 3,
) -> List[ScoredConceptNode]:
    """
    Perform multi-field similarity scoring and prerequisite graph traversal over KnowledgeGraphModel.
    Returns ranked Top-K ScoredConceptNode instances with similarity percentages.
    """
    if not knowledge_graph or not knowledge_graph.concepts:
        logger.info("RetrievalAgent: No active knowledge graph found for query %r.", query)
        return []

    q_clean = query.lower().strip()
    q_terms = [t for t in re.findall(r'\w+', q_clean) if len(t) > 2]
    
    # Build graph edge lookup maps (parents & children)
    parent_map: Dict[str, List[str]] = {}
    child_map: Dict[str, List[str]] = {}
    for edge in knowledge_graph.prerequisite_edges:
        from_id = edge.get("from")
        to_id = edge.get("to")
        if from_id and to_id:
            parent_map.setdefault(to_id, []).append(from_id)
            child_map.setdefault(from_id, []).append(to_id)

    scored_results: List[tuple[float, ConceptNode]] = []

    for concept in knowledge_graph.concepts:
        score = 0.0
        title_lower = concept.title.lower()
        summary_lower = concept.summary.lower()

        # 1. Exact or partial title match (High weight)
        if q_clean in title_lower or title_lower in q_clean:
            score += 45.0
        elif any(t in title_lower for t in q_terms):
            score += 25.0

        # 2. Term matches in summary & definitions
        for term in q_terms:
            if term in summary_lower:
                score += 5.0
            for def_item in concept.definitions:
                if term in def_item.get("term", "").lower() or term in def_item.get("definition", "").lower():
                    score += 8.0

        # 3. Specific topic alias boosts
        if "normaliz" in q_clean or "bcnf" in q_clean or "3nf" in q_clean or "2nf" in q_clean or "1nf" in q_clean:
            if any(n_kw in title_lower or n_kw in summary_lower for n_kw in ["normaliz", "bcnf", "3nf", "2nf", "1nf", "functional dependency"]):
                score += 35.0

        # 4. Richness bonus
        if concept.definitions:
            score += 5.0
        if concept.examples:
            score += 5.0
        if concept.formulas:
            score += 3.0
        if concept.code_snippets:
            score += 3.0

        # Attach parent & child links
        concept.parents = parent_map.get(concept.id, [])
        concept.children = child_map.get(concept.id, [])

        # Cap max raw score at 100.0 for normalized similarity score
        norm_score = min(98.5, max(12.0, score * 1.2)) if score > 0 else 0.0
        scored_results.append((norm_score, concept))

    # Sort descending by score
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # Convert to ScoredConceptNode with rank
    output_nodes: List[ScoredConceptNode] = []
    for rank, (score, concept) in enumerate(scored_results[:top_k], 1):
        output_nodes.append(ScoredConceptNode(
            rank_position=rank,
            similarity_score=round(score, 1),
            node=concept
        ))

    logger.info(
        "RetrievalAgent: Retrieved Top-%d concept nodes for query %r (Top score: %.1f%%, Top node: %s).",
        len(output_nodes), query, output_nodes[0].similarity_score if output_nodes else 0.0,
        output_nodes[0].node.title if output_nodes else "None"
    )

    return output_nodes
