import os
import json

DATASET_DIR = os.path.abspath(os.path.dirname(__file__) + "/dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

SUBJECTS_DATA = {
    "DBMS": {
        "filename": "DBMS_Complete_Notes.txt",
        "content": """Database Management System (DBMS) Notes 2026
Topic: Normalization & Transaction ACID Properties
Lecture 1: Functional Dependencies & Normal Forms
1NF (First Normal Form): Eliminates repeating groups and ensures atomic values in every column.
2NF (Second Normal Form): Must be in 1NF and eliminate partial dependencies (non-key attributes must depend on the full primary key).
3NF (Third Normal Form): Must be in 2NF and eliminate transitive dependencies (non-key attributes must not depend on other non-key attributes).
BCNF (Boyce-Codd Normal Form): A stricter version of 3NF where for every functional dependency X -> Y, X must be a super key.

Lecture 2: ACID Properties of Transactions
- Atomicity: All operations in a transaction succeed or all fail (All-or-Nothing).
- Consistency: Database moves from one valid state to another valid state, preserving integrity constraints.
- Isolation: Concurrent transactions execute independently without interfering with each other.
- Durability: Once committed, data changes persist permanently even after system crashes.
"""
    },
    "Operating_Systems": {
        "filename": "OS_Process_Memory_Notes.txt",
        "content": """Operating Systems (OS) Core Concepts
Topic: Process Scheduling, Deadlocks, & Virtual Memory
1. Process States: New -> Ready -> Running -> Waiting -> Terminated.
2. CPU Scheduling Algorithms: First-Come-First-Served (FCFS), Shortest Job First (SJF), Round Robin (RR), Priority Scheduling.
3. Deadlock Necessary Conditions:
   - Mutual Exclusion
   - Hold and Wait
   - No Preemption
   - Circular Wait
4. Banker's Algorithm: Used for deadlock avoidance by verifying safe states before allocation.
5. Virtual Memory & Paging: Page tables translate logical addresses to physical frame addresses. Page fault occurs when requested page is not in RAM.
"""
    },
    "Computer_Networks": {
        "filename": "Computer_Networks_OSI_TCP.txt",
        "content": """Computer Networks Handbook 2026
Topic: OSI 7-Layer Model & TCP/IP Protocol Suite
Layer 7: Application (HTTP, HTTPS, FTP, DNS)
Layer 6: Presentation (SSL/TLS Encryption, Data Formatting)
Layer 5: Session (Session Setup, Maintenance, Tear-down)
Layer 4: Transport (TCP Reliable Segment Flow Control, UDP Datagram Connectionless)
Layer 3: Network (IP Address Routing, ICMP, Packet Fragmentation)
Layer 2: Data Link (MAC Addresses, Ethernet Framing, Error Detection CRC)
Layer 1: Physical (Bits, Cables, Optical Signals, Repeaters)

TCP 3-Way Handshake: SYN -> SYN-ACK -> ACK.
"""
    },
    "Python": {
        "filename": "Python_Advanced_Concepts.txt",
        "content": """Python Programming & Data Engineering Notes
Topic: Decorators, Generators, & Asynchronous I/O
1. Decorators: Higher-order functions that wrap another function to extend behavior without modifying source. Syntax: @decorator_name.
2. Generators & Yield: Functions using 'yield' produce lazy-evaluated iterators, minimizing memory usage for large data streams.
3. Asyncio & Coroutines: Event loop manages asynchronous tasks using 'async def' and 'await' keywords for non-blocking I/O.
4. Memory Management: Python uses reference counting and a generational Garbage Collector (GC) to reclaim memory.
"""
    },
    "Java": {
        "filename": "Java_OOP_Concurrency.txt",
        "content": """Java Enterprise Programming Notes
Topic: Object-Oriented Programming (OOP) & Concurrency
1. Four Pillars of OOP: Encapsulation, Abstraction, Inheritance, Polymorphism.
2. JVM Architecture: ClassLoader -> Heap, Method Area, Stack, PC Register -> Execution Engine (JIT Compiler, GC).
3. Concurrency: Synchronized blocks, ReentrantLock, and ThreadPoolExecutor manage thread safety and prevent race conditions.
4. Java Garbage Collection: G1 Garbage Collector divides heap into regions, managing Young and Old generations efficiently.
"""
    },
    "Data_Structures": {
        "filename": "Data_Structures_Algorithms.txt",
        "content": """Data Structures & Algorithms (DSA) Manual
Topic: Binary Search Trees, Graphs, & Time Complexity
1. Binary Search Tree (BST): Left subtree contains nodes < parent; right subtree contains nodes > parent. Search time: O(log N) average, O(N) worst.
2. AVL & Red-Black Trees: Self-balancing BSTs guaranteeing O(log N) operations by performing tree rotations.
3. Graph Algorithms:
   - Breadth-First Search (BFS): Uses Queue, O(V + E) complexity.
   - Depth-First Search (DFS): Uses Stack/Recursion, O(V + E) complexity.
   - Dijkstra's Algorithm: Shortest path in weighted graphs using Priority Queue, O((V + E) log V).
"""
    },
    "Calculus": {
        "filename": "Calculus_Differential_Equations.txt",
        "content": """Calculus II & Differential Equations
Topic: Derivatives, Integrals, & Taylor Series
1. Derivative Definition: f'(x) = lim(h->0) [f(x+h) - f(x)] / h. Represents instantaneous rate of change.
2. Fundamental Theorem of Calculus: Integral of f(x) from a to b = F(b) - F(a), where F'(x) = f(x).
3. Taylor Series Expansion: f(x) = sum_{n=0}^inf [f^(n)(a) / n!] * (x - a)^n.
4. Differential Equations: First-order separable equations dy/dx = g(x)h(y) solved by integrating separate variables.
"""
    },
    "Physics": {
        "filename": "Physics_Mechanics_Electromagnetism.txt",
        "content": """Physics I & II Engineering Reference
Topic: Newton's Laws, Work-Energy, & Maxwell's Equations
1. Newton's Three Laws:
   - First Law: Inertia (body remains at rest/constant velocity unless acted upon).
   - Second Law: F = dp/dt = m * a.
   - Third Law: Action-Reaction (equal and opposite forces).
2. Work-Energy Theorem: Total work done on an object equals change in kinetic energy: W = Delta KE = 1/2 m v^2 - 1/2 m u^2.
3. Maxwell's Equations:
   - Gauss's Law for Electricity: div E = rho / epsilon_0
   - Gauss's Law for Magnetism: div B = 0 (no magnetic monopoles)
   - Faraday's Law: curl E = -dB/dt (induction)
   - Ampere-Maxwell Law: curl B = mu_0 J + mu_0 epsilon_0 dE/dt.
"""
    },
    "Biology": {
        "filename": "Biology_Cellular_Genetics.txt",
        "content": """Cellular Biology & Genetics Reference
Topic: DNA Replication, Protein Synthesis, & Mitosis
1. DNA Double Helix Structure: Adenine pairs with Thymine (2 H-bonds), Guanine pairs with Cytosine (3 H-bonds).
2. Central Dogma of Molecular Biology: DNA -> Transcription -> mRNA -> Translation -> Protein.
3. Mitosis vs Meiosis:
   - Mitosis: Produces 2 identical diploid somatic daughter cells (Prophase, Metaphase, Anaphase, Telophase).
   - Meiosis: Produces 4 genetically diverse haploid gametes.
4. ATP (Adenosine Triphosphate): Energy currency of the cell produced during oxidative phosphorylation in mitochondria.
"""
    },
    "History": {
        "filename": "World_History_Industrial_Revolution.txt",
        "content": """World History & Global Economics
Topic: The Industrial Revolution & World Wars
1. First Industrial Revolution (1760-1840): Transition to steam power, mechanized textile production, and coal mining in Britain.
2. Second Industrial Revolution (1870-1914): Expansion of steel production, electricity, internal combustion engines, and assembly lines.
3. World War I (1914-1918): Caused by Alliance Systems, Imperialism, & Nationalism; ended by Treaty of Versailles.
4. World War II (1939-1945): Allied vs Axis Powers; led to creation of the United Nations and the Cold War era.
"""
    }
}

def generate_files():
    created_count = 0
    for key, data in SUBJECTS_DATA.items():
        filepath = os.path.join(DATASET_DIR, data["filename"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(data["content"].strip())
        created_count += 1
        print(f"Created study source: {data['filename']}")
    
    print(f"\nGenerated total {created_count} complete study sources in {DATASET_DIR}")

if __name__ == "__main__":
    generate_files()
