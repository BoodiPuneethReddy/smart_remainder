/**
 * components/ui/KnowledgeGraphExplorer.tsx — Interactive Academic Knowledge Graph Explorer
 * 
 * Interactive 12-Stage Knowledge Graph component allowing students to inspect concepts:
 *   DBMS -> Normalization -> Functional Dependency -> Candidate Keys -> 1NF -> 2NF -> 3NF -> BCNF
 * Clickable concept nodes displaying definitions, examples, formulas, SQL snippets, prerequisites,
 * dependents, and difficulty levels.
 */
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Network, BookOpen, Code, HelpCircle, ArrowRight, CheckCircle2, ChevronRight } from 'lucide-react';
import { api } from '../../lib/api';

export default function KnowledgeGraphExplorer() {
  const [graph, setGraph] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadGraph() {
      try {
        const res = await api.getKnowledgeGraph();
        const data = res.data;
        setGraph(data);
        if (data?.concepts?.length > 0) {
          setSelectedNode(data.concepts[0]);
        }
      } catch (err) {
        console.error("Failed to load Knowledge Graph:", err);
      } finally {
        setLoading(false);
      }
    }
    loadGraph();
  }, []);

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 animate-pulse">
        Loading 12-Stage Academic Knowledge Graph Explorer...
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-slate-100 font-sans shadow-xl">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-indigo-500/20 text-indigo-400 rounded-xl border border-indigo-500/30">
            <Network className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-lg text-slate-100 flex items-center gap-2">
              Academic Knowledge Graph Explorer
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                {graph?.subject || 'DBMS'}
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Prerequisite DAG hierarchy & concept node definitions
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Node List Sidebar */}
        <div className="col-span-4 space-y-2 max-h-[500px] overflow-y-auto pr-2">
          {graph?.concepts?.map((node: any, idx: number) => {
            const isSelected = selectedNode?.id === node.id;
            return (
              <button
                key={node.id}
                onClick={() => setSelectedNode(node)}
                className={`w-full p-3.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                  isSelected 
                    ? 'bg-indigo-950/60 border-indigo-500/50 text-indigo-200 shadow-md' 
                    : 'bg-slate-950/40 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2 font-mono text-xs text-slate-500">
                    <span>STAGE {idx + 1}</span>
                    <span>•</span>
                    <span className="text-amber-400">DIFF {node.difficulty}/6</span>
                  </div>
                  <div className="font-bold text-sm text-slate-100 mt-0.5">{node.title}</div>
                </div>
                <ChevronRight className={`w-4 h-4 transition-transform ${isSelected ? 'text-indigo-400 translate-x-1' : 'text-slate-600'}`} />
              </button>
            );
          })}
        </div>

        {/* Selected Node Detailed Inspector Panel */}
        <div className="col-span-8 bg-slate-950 border border-slate-800 rounded-xl p-5 overflow-y-auto max-h-[500px] font-mono text-xs">
          {selectedNode ? (
            <div className="space-y-5">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] uppercase tracking-wider text-indigo-400 font-bold">CONCEPT NODE DETAILS</span>
                  <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px]">
                    Difficulty Level {selectedNode.difficulty}/6
                  </span>
                </div>
                <h4 className="text-xl font-bold text-slate-100">{selectedNode.title}</h4>
                <p className="text-slate-400 mt-1 font-sans text-xs">{selectedNode.summary}</p>
              </div>

              {/* Definitions */}
              {selectedNode.definitions?.length > 0 && (
                <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                  <h5 className="font-bold text-indigo-300 text-xs mb-1 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5" /> Formal Definition
                  </h5>
                  <p className="text-slate-300 font-sans text-xs">
                    {selectedNode.definitions[0].definition}
                  </p>
                </div>
              )}

              {/* Examples */}
              {selectedNode.examples?.length > 0 && (
                <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                  <h5 className="font-bold text-emerald-300 text-xs mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Practical Example
                  </h5>
                  <p className="text-slate-300 font-sans text-xs">
                    {selectedNode.examples[0]}
                  </p>
                </div>
              )}

              {/* Code Snippets / SQL */}
              {selectedNode.code_snippets?.length > 0 && (
                <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                  <h5 className="font-bold text-cyan-300 text-xs mb-1 flex items-center gap-1.5">
                    <Code className="w-3.5 h-3.5" /> SQL Constraint Example
                  </h5>
                  <pre className="text-cyan-400 text-[11px] bg-slate-950 p-2 rounded border border-slate-800 overflow-x-auto">
                    {selectedNode.code_snippets[0]}
                  </pre>
                </div>
              )}

              {/* Prerequisites & Dependents */}
              <div className="grid grid-cols-2 gap-4 pt-2">
                <div className="p-2.5 bg-slate-900/40 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 font-bold block mb-1">PREREQUISITE NODES</span>
                  <div className="flex flex-wrap gap-1">
                    {selectedNode.parents?.length > 0 ? (
                      selectedNode.parents.map((p: string) => (
                        <span key={p} className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px]">{p}</span>
                      ))
                    ) : (
                      <span className="text-slate-600 text-[10px]">None (Root Concept)</span>
                    )}
                  </div>
                </div>
                <div className="p-2.5 bg-slate-900/40 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 font-bold block mb-1">DEPENDENT CHILD NODES</span>
                  <div className="flex flex-wrap gap-1">
                    {selectedNode.children?.length > 0 ? (
                      selectedNode.children.map((c: string) => (
                        <span key={c} className="px-2 py-0.5 bg-indigo-950 text-indigo-300 border border-indigo-800/40 rounded text-[10px]">{c}</span>
                      ))
                    ) : (
                      <span className="text-slate-600 text-[10px]">Leaf Concept</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500">
              Select a concept node from the sidebar to inspect details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
