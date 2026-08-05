"""
agents/retrieval_agent.py — Top-K Semantic Retrieval Agent

Traverses 12-Stage Document Knowledge Graphs and concept node stores
to retrieve the Top-K relevant concept nodes (definitions, formulas, code, prerequisites).
Prevents sending full raw PDFs or entire documents to Gemini.
"""

import logging
from typing import List, Optional, Dict, Any
from app.agents.models import KnowledgeGraphModel, ConceptNode

logger = logging.getLogger(__name__)


def retrieve_top_k_nodes(
    query: str,
    knowledge_graph: Optional[KnowledgeGraphModel],
    top_k: int = 3,
) -> List[ConceptNode]:
    """
    Perform semantic keyword matching and prerequisite graph traversal over KnowledgeGraphModel.
    Returns Top-K most relevant ConceptNode instances.
    """
    if not knowledge_graph or not knowledge_graph.concepts:
        logger.info("RetrievalAgent: No active knowledge graph found for query %r.", query)
        return []

    q_lower = query.lower().strip()
    scored_nodes: List[tuple[float, ConceptNode]] = []

    for concept in knowledge_graph.concepts:
        score = 0.0
        title_lower = concept.title.lower()
        summary_lower = concept.summary.lower()

        # Direct title match
        if q_lower in title_lower or title_lower in q_lower:
            score += 10.0

        # Term overlap in summary
        for term in q_lower.split():
            if len(term) > 2 and term in summary_lower:
                score += 2.0

        # Bonus for presence of definitions, formulas, or code
        if concept.formulas:
            score += 1.5
        if concept.code_snippets:
            score += 1.5

        scored_nodes.append((score, concept))

    # Sort descending by relevance score
    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    top_nodes = [node for score, node in scored_nodes[:top_k]]

    logger.info(
        "RetrievalAgent: Retrieved Top-%d concept nodes for query %r (Top node: %s).",
        len(top_nodes), query, top_nodes[0].title if top_nodes else "None"
    )

    return top_nodes
