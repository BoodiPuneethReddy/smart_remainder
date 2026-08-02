"""
agents/document_agent.py — Document Agent.

Multi-stage document extraction:
  1. Classification (Subject, Doc Type)
  2. Concept extraction & difficulty analysis
  3. Prerequisite dependency graph generation
  4. Code & formula detection
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session
from app.agents.models import KnowledgeGraphModel, ConceptNode
from app.models.imported_document import ImportedDocument
from app.services.document_graph import build_document_knowledge_graph

logger = logging.getLogger(__name__)


def process_document(
    document_id: int,
    db: Session,
) -> KnowledgeGraphModel:
    """
    Executes multi-stage document graph parsing and builds KnowledgeGraphModel.
    """
    doc = db.query(ImportedDocument).filter(ImportedDocument.id == document_id).first()
    if not doc or not doc.extracted_text:
        return KnowledgeGraphModel(
            document_id=document_id,
            subject="General Studies",
            doc_type="Academic Notes",
            total_chapters=1,
            concepts=[
                ConceptNode(
                    id="c1",
                    title="General Overview",
                    chapter="Chapter 1",
                    summary="Basic concepts and introductory topics.",
                    difficulty=1,
                )
            ],
            detected_features=["notes"],
        )

    # Use document_graph service to extract graph dict
    graph_dict = build_document_knowledge_graph(doc.extracted_text, doc.original_filename or "Document")
    
    concepts = []
    edges = []
    
    raw_nodes = graph_dict.get("nodes", [])
    for idx, node in enumerate(raw_nodes):
        cid = f"c{idx+1}"
        concepts.append(
            ConceptNode(
                id=cid,
                title=node.get("title", f"Topic {idx+1}"),
                chapter=node.get("chapter", "Chapter 1"),
                summary=node.get("summary", ""),
                difficulty=node.get("difficulty", 1),
                prerequisites=node.get("prerequisites", []),
                has_code=node.get("has_code", False),
                has_formulas=node.get("has_formulas", False),
                formulas=node.get("formulas", []),
                code_snippets=node.get("code_snippets", []),
            )
        )

    # Prerequisite edges
    raw_edges = graph_dict.get("edges", [])
    for edge in raw_edges:
        edges.append({"from": str(edge.get("from")), "to": str(edge.get("to"))})

    subject = graph_dict.get("subject", "General Studies")
    doc_type = graph_dict.get("doc_type", "Academic Notes")
    features = graph_dict.get("features", ["notes"])

    graph_model = KnowledgeGraphModel(
        document_id=document_id,
        subject=subject,
        doc_type=doc_type,
        total_chapters=len(set(c.chapter for c in concepts)) or 1,
        concepts=concepts,
        prerequisite_edges=edges,
        detected_features=features,
    )

    logger.info("DocumentAgent: Built KnowledgeGraph document_id=%d subject=%r concepts=%d", document_id, subject, len(concepts))
    return graph_model
