"""
services/knowledge_graph_service.py — Knowledge Graph Persistence & Targeted Node Retrieval Service

Handles:
  1. Extracting and persisting a full KnowledgeGraph + ConceptNodes in SQLite DB on PDF upload.
  2. Retrieving ONLY selected concept nodes for a LearningSession (never the entire PDF or graph).
"""

import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from app.models.imported_document import ImportedDocument
from app.models.knowledge_graph import KnowledgeGraph, ConceptNode
from app.services.document_graph import build_document_knowledge_graph

logger = logging.getLogger(__name__)


class KnowledgeGraphService:

    @staticmethod
    def get_or_create_graph(db: Session, document_id: int) -> KnowledgeGraph:
        """
        Retrieves existing KnowledgeGraph from DB or extracts and persists a new one.
        Never recreates an existing graph on every request.
        """
        existing_graph = db.query(KnowledgeGraph).filter(
            KnowledgeGraph.document_id == document_id
        ).first()

        if existing_graph and existing_graph.nodes:
            logger.info("KnowledgeGraphService: Using existing graph ID=%d for document_id=%d", existing_graph.id, document_id)
            return existing_graph

        doc = db.query(ImportedDocument).filter(ImportedDocument.id == document_id).first()
        if not doc or not doc.extracted_text:
            raise ValueError(f"Document {document_id} not found or missing extracted text.")

        # Extract KnowledgeGraph structure using DocumentAgent engine
        raw_kg = build_document_knowledge_graph(doc.extracted_text, doc.original_filename)
        subject_name = raw_kg.get("subject", doc.document_type or "General Academic Study")
        raw_nodes = raw_kg.get("nodes", [])

        if not existing_graph:
            graph = KnowledgeGraph(
                document_id=document_id,
                subject=subject_name,
                doc_type=raw_kg.get("doc_type", "ACADEMIC"),
                total_nodes=len(raw_nodes),
                features=raw_kg.get("features", ["concepts", "definitions", "examples", "sql"])
            )
            db.add(graph)
            db.commit()
            db.refresh(graph)
        else:
            graph = existing_graph

        # Persist individual ConceptNodes
        for idx, n in enumerate(raw_nodes, 1):
            node_key = f"node_{idx}"
            c_node = ConceptNode(
                graph_id=graph.id,
                node_key=node_key,
                title=n.get("title", f"Concept {idx}"),
                chapter=n.get("chapter", f"Chapter {idx}"),
                summary=n.get("summary", ""),
                definitions=n.get("definitions", []),
                examples=n.get("examples", []),
                code_snippets=n.get("code_snippets", []),
                formulas=n.get("formulas", []),
                difficulty=n.get("difficulty", 3),
                importance=0.9 if idx <= 2 else (0.75 if idx <= 5 else 0.5),
                est_minutes=n.get("est_minutes", 15),
                prerequisites=n.get("prerequisites", []),
                children=[]
            )
            db.add(c_node)

        db.commit()
        db.refresh(graph)
        logger.info("KnowledgeGraphService: Persisted graph ID=%d with %d nodes", graph.id, len(graph.nodes))
        return graph

    @staticmethod
    def get_nodes_as_dicts(graph: KnowledgeGraph) -> List[Dict[str, Any]]:
        """Converts graph nodes to a list of standard dictionaries."""
        result = []
        for n in graph.nodes:
            result.append({
                "id": n.id,
                "node_key": n.node_key,
                "title": n.title,
                "chapter": n.chapter,
                "summary": n.summary,
                "definitions": n.definitions or [],
                "examples": n.examples or [],
                "code_snippets": n.code_snippets or [],
                "formulas": n.formulas or [],
                "difficulty": n.difficulty,
                "importance": n.importance,
                "est_minutes": n.est_minutes,
                "prerequisites": n.prerequisites or [],
                "children": n.children or []
            })
        return result

    @staticmethod
    def retrieve_selected_nodes(
        db: Session,
        graph_id: int,
        selected_concept_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieves ONLY the specific ConceptNodes selected by CurriculumBuilder.
        Never retrieves the whole document or unselected nodes.
        """
        nodes = db.query(ConceptNode).filter(
            and_(
                ConceptNode.graph_id == graph_id,
                ConceptNode.node_key.in_(selected_concept_ids)
            )
        ).all()

        # Preserve selected order
        node_map = {n.node_key: n for n in nodes}
        result = []
        for key in selected_concept_ids:
            n = node_map.get(key)
            if n:
                result.append({
                    "id": n.id,
                    "node_key": n.node_key,
                    "title": n.title,
                    "chapter": n.chapter,
                    "summary": n.summary,
                    "definitions": n.definitions or [],
                    "examples": n.examples or [],
                    "code_snippets": n.code_snippets or [],
                    "formulas": n.formulas or [],
                    "difficulty": n.difficulty,
                    "importance": n.importance,
                    "est_minutes": n.est_minutes,
                    "prerequisites": n.prerequisites or [],
                    "children": n.children or []
                })
        return result
