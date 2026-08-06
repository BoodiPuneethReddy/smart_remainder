"""
scripts/retrieval_benchmark.py — 20-Query Retrieval Quality Benchmark

Evaluates RetrievalAgent Top-1 and Top-3 retrieval accuracy, similarity scores,
and ranking across 20 representative queries across DBMS, OS, DSA, Computer Networks,
Math, Software Engineering, and Machine Learning.
"""

import sys
import json
import logging
from typing import List, Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

BENCHMARK_QUERIES = [
    # (Query, Subject Domain, Expected Concept Title Key)
    ("Explain normalization", "DBMS", "Normalization"),
    ("What is 3NF and BCNF?", "DBMS", "Boyce-Codd Normal Form"),
    ("Explain ACID properties in transactions", "DBMS", "Transactions & ACID"),
    ("How do SQL JOINs work?", "DBMS", "SQL Joins"),
    ("Explain deadlock prevention and avoidance", "OS", "Deadlocks"),
    ("What is process scheduling and round robin?", "OS", "CPU Scheduling"),
    ("Explain virtual memory and paging", "OS", "Virtual Memory & Paging"),
    ("What are semaphores and mutex?", "OS", "Process Synchronization"),
    ("Explain binary search trees", "DSA", "Binary Search Trees"),
    ("What is recursion and base cases?", "DSA", "Recursion & Backtracking"),
    ("Explain Dijkstra algorithm", "DSA", "Graph Algorithms"),
    ("What is Big O notation and time complexity?", "DSA", "Algorithm Analysis"),
    ("Explain TCP vs UDP protocols", "CN", "Transport Layer Protocols"),
    ("What is OSI 7-layer model?", "CN", "OSI Architecture"),
    ("Explain IP addressing and subnetting", "CN", "Network Layer Subnetting"),
    ("Explain matrix multiplication and eigenvalues", "MATH", "Linear Algebra"),
    ("What are differential equations?", "MATH", "Differential Equations"),
    ("Explain Bayes theorem and probability", "MATH", "Probability & Bayes"),
    ("What are software design patterns?", "SE", "Design Patterns"),
    ("Explain neural networks and backpropagation", "ML", "Neural Networks"),
]

def build_test_knowledge_graphs() -> Dict[str, Any]:
    from app.agents.models import KnowledgeGraphModel, ConceptNode

    return {
        "DBMS": KnowledgeGraphModel(
            subject="Database Management Systems",
            doc_type="DBMS",
            concepts=[
                ConceptNode(
                    id="db_1", title="Database Normalization (1NF, 2NF, 3NF)", chapter="Ch 3",
                    summary="Database normalization structures relational tables to eliminate insertion, deletion, and update anomalies.",
                    definitions=[{"term": "3NF", "definition": "No transitive dependencies on candidate keys."}],
                    examples=["Decomposing Student_Courses into Student and Course tables."],
                    difficulty=3, prerequisites=["db_0"], parents=["db_0"], children=["db_2"]
                ),
                ConceptNode(
                    id="db_2", title="Boyce-Codd Normal Form (BCNF)", chapter="Ch 3",
                    summary="Stricter form of 3NF where every determinant must be a candidate key.",
                    definitions=[{"term": "BCNF", "definition": "For X -> Y, X must be a super key."}],
                    difficulty=4, prerequisites=["db_1"], parents=["db_1"]
                ),
                ConceptNode(
                    id="db_3", title="Transactions & ACID Properties", chapter="Ch 5",
                    summary="ACID (Atomicity, Consistency, Isolation, Durability) guarantees reliable processing of database operations.",
                    definitions=[{"term": "Atomicity", "definition": "All or nothing transaction execution."}],
                    difficulty=3
                ),
                ConceptNode(
                    id="db_4", title="SQL Joins & Relational Algebra", chapter="Ch 2",
                    summary="INNER, LEFT, RIGHT, and FULL OUTER joins combine records from two relational tables based on key fields.",
                    difficulty=2
                ),
                ConceptNode(
                    id="db_0", title="Functional Dependencies & Keys", chapter="Ch 3",
                    summary="A functional dependency X -> Y specifies that attribute X uniquely determines attribute Y.",
                    difficulty=2, children=["db_1"]
                )
            ],
            prerequisite_edges=[{"from": "db_0", "to": "db_1"}, {"from": "db_1", "to": "db_2"}]
        ),

        "OS": KnowledgeGraphModel(
            subject="Operating Systems",
            doc_type="OS",
            concepts=[
                ConceptNode(
                    id="os_1", title="Deadlocks & Banker's Algorithm", chapter="Ch 4",
                    summary="Deadlock handling via Prevention, Avoidance (Banker's algorithm), Detection, and Recovery.",
                    definitions=[{"term": "Deadlock", "definition": "Circular wait among processes for resource locks."}],
                    difficulty=4
                ),
                ConceptNode(
                    id="os_2", title="CPU Scheduling Algorithms", chapter="Ch 3",
                    summary="Preemptive and non-preemptive scheduling algorithms: FCFS, SJF, Priority, and Round Robin.",
                    difficulty=3
                ),
                ConceptNode(
                    id="os_3", title="Virtual Memory & Paging Architecture", chapter="Ch 6",
                    summary="Paging divides memory into page frames, resolving external fragmentation via page tables.",
                    difficulty=4
                ),
                ConceptNode(
                    id="os_4", title="Process Synchronization & Semaphores", chapter="Ch 4",
                    summary="Mutex locks and counting semaphores protect critical sections to prevent race conditions.",
                    difficulty=3
                )
            ]
        ),

        "DSA": KnowledgeGraphModel(
            subject="Data Structures & Algorithms",
            doc_type="DSA",
            concepts=[
                ConceptNode(
                    id="dsa_1", title="Binary Search Trees (BST)", chapter="Ch 2",
                    summary="Binary tree node structure where left child is less than root and right child is greater.",
                    difficulty=2
                ),
                ConceptNode(
                    id="dsa_2", title="Recursion & Backtracking", chapter="Ch 1",
                    summary="Functions calling themselves with base case termination criteria for divide-and-conquer.",
                    difficulty=3
                ),
                ConceptNode(
                    id="dsa_3", title="Graph Algorithms (Dijkstra & Shortest Path)", chapter="Ch 5",
                    summary="Dijkstra algorithm computes single-source shortest paths on non-negative weighted graphs.",
                    difficulty=4
                ),
                ConceptNode(
                    id="dsa_4", title="Algorithm Analysis & Big O Notation", chapter="Ch 1",
                    summary="Asymptotic notation measuring upper-bound time and space complexity growth rates.",
                    difficulty=2
                )
            ]
        ),

        "CN": KnowledgeGraphModel(
            subject="Computer Networks",
            doc_type="CN",
            concepts=[
                ConceptNode(
                    id="cn_1", title="Transport Layer Protocols (TCP vs UDP)", chapter="Ch 3",
                    summary="TCP offers reliable, connection-oriented byte streams; UDP offers fast, connectionless datagrams.",
                    difficulty=3
                ),
                ConceptNode(
                    id="cn_2", title="OSI Architecture & 7 Layers", chapter="Ch 1",
                    summary="7-layer conceptual model: Physical, Data Link, Network, Transport, Session, Presentation, Application.",
                    difficulty=2
                ),
                ConceptNode(
                    id="cn_3", title="Network Layer Subnetting & IP Addressing", chapter="Ch 4",
                    summary="IPv4/IPv6 addressing, CIDR notation, subnet masks, and packet routing.",
                    difficulty=3
                )
            ]
        ),

        "MATH": KnowledgeGraphModel(
            subject="Mathematics",
            doc_type="MATH",
            concepts=[
                ConceptNode(
                    id="m_1", title="Linear Algebra & Eigenvalues", chapter="Ch 2",
                    summary="Matrix operations, determinants, eigenvalues (Det(A - λI) = 0), and eigenvectors.",
                    formulas=["Ax = λx", "det(A - λI) = 0"],
                    difficulty=4
                ),
                ConceptNode(
                    id="m_2", title="Differential Equations", chapter="Ch 4",
                    summary="First and second-order ordinary differential equations and analytical solution methods.",
                    difficulty=4
                ),
                ConceptNode(
                    id="m_3", title="Probability & Bayes Theorem", chapter="Ch 1",
                    summary="Conditional probability P(A|B) = P(B|A)P(A)/P(B) and random variable distributions.",
                    formulas=["P(A|B) = (P(B|A) * P(A)) / P(B)"],
                    difficulty=3
                )
            ]
        ),

        "SE": KnowledgeGraphModel(
            subject="Software Engineering",
            doc_type="SE",
            concepts=[
                ConceptNode(
                    id="se_1", title="Software Design Patterns (Gang of Four)", chapter="Ch 3",
                    summary="Creational, Structural, and Behavioral patterns (Singleton, Factory, Observer, Strategy).",
                    difficulty=3
                )
            ]
        ),

        "ML": KnowledgeGraphModel(
            subject="Machine Learning",
            doc_type="ML",
            concepts=[
                ConceptNode(
                    id="ml_1", title="Neural Networks & Backpropagation Algorithm", chapter="Ch 5",
                    summary="Multi-layer perceptron optimization using gradient descent and chain-rule backpropagation.",
                    difficulty=5
                )
            ]
        ),
    }


def main():
    print("================================================================================")
    print("        RETRIEVAL AGENT QUALITY BENCHMARK — 20 REPRESENTATIVE QUERIES")
    print("================================================================================\n")

    from app.agents.retrieval_agent import retrieve_top_k_nodes

    graphs = build_test_knowledge_graphs()

    top1_correct = 0
    top3_correct = 0
    total_queries = len(BENCHMARK_QUERIES)

    for idx, (query, domain, expected_key) in enumerate(BENCHMARK_QUERIES, 1):
        kg = graphs.get(domain)
        retrieved_nodes = retrieve_top_k_nodes(query, kg, top_k=3)

        hit_top1 = False
        hit_top3 = False
        top1_title = "None"
        top1_score = 0.0

        if retrieved_nodes:
            top1_title = retrieved_nodes[0].node.title
            top1_score = retrieved_nodes[0].similarity_score
            if expected_key.lower() in top1_title.lower():
                hit_top1 = True

            for node in retrieved_nodes:
                if expected_key.lower() in node.node.title.lower():
                    hit_top3 = True
                    break

        if hit_top1:
            top1_correct += 1
        if hit_top3:
            top3_correct += 1

        status_icon = "✅ TOP-1 PASS" if hit_top1 else ("⚠️ TOP-3 PASS" if hit_top3 else "❌ FAIL")

        print(f"[{idx:02d}/20] Query: \"{query}\" | Domain: {domain}")
        print(f"       Result: {status_icon} | Score: {top1_score:.1f}% | Top-1 Node: '{top1_title}'")

    top1_acc = (top1_correct / total_queries) * 100
    top3_acc = (top3_correct / total_queries) * 100

    print("\n================================================================================")
    print(f"RETRIEVAL ACCURACY REPORT:")
    print(f"  • Total Benchmark Queries Evaluated: {total_queries}")
    print(f"  • Top-1 Retrieval Accuracy: {top1_acc:.1f}% ({top1_correct}/{total_queries})")
    print(f"  • Top-3 Retrieval Accuracy: {top3_acc:.1f}% ({top3_correct}/{total_queries})")
    print("================================================================================")

if __name__ == "__main__":
    main()
