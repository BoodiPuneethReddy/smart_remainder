/**
 * components/ui/RuntimeInspector.tsx — Developer Mode Swarm Telemetry & Grounding Inspector
 * 
 * Provides an un-truncated, full runtime trace modal/drawer exposing:
 *   - User Query & Intent
 *   - Live Execution Graph (Active vs Skipped Agents)
 *   - Shared Memory Evolution (Before -> After)
 *   - Per-Agent Latency Breakdown & Confidence
 *   - Planner Score Breakdown & Deferred Task Reasons
 *   - Reflection Audit (Violations & Recommendations)
 *   - Grounding Citation Metadata (Definitions, Examples, SQL, Formulas)
 *   - Exact Gemini System Prompt & Raw Output
 */
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, X, Terminal, Cpu, Database, CheckCircle2, ShieldCheck, ChevronRight, RefreshCw, FileCode, Layers } from 'lucide-react';
import { api } from '../../lib/api';

interface RuntimeInspectorProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function RuntimeInspector({ isOpen, onClose }: RuntimeInspectorProps) {
  const [telemetry, setTelemetry] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'graph' | 'memory' | 'planner' | 'reflection' | 'grounding' | 'prompt'>('graph');

  const fetchTelemetry = async () => {
    setLoading(true);
    try {
      const res = await api.getLatestTelemetry();
      setTelemetry(res.data);
    } catch (err) {
      console.error("Failed to fetch telemetry:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchTelemetry();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const activeAgentsSet = new Set(telemetry?.active_agents || []);
  const allAgents = ["IntentAgent", "ContextAgent", "RetrievalAgent", "DocumentAgent", "StrategyAgent", "PlannerAgent", "ReflectionAgent", "ReminderAgent", "AnalyticsAgent", "TutorAgent"];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden text-slate-100 font-sans"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h3 className="font-bold text-lg text-slate-100 flex items-center gap-2">
                Swarm Agentic Telemetry Inspector
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  DEVELOPER MODE
                </span>
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                Query: "{telemetry?.query || 'Loading...'}" | Intent: {telemetry?.intent || 'N/A'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button 
              onClick={fetchTelemetry}
              className="p-2 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              title="Refresh Telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button 
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Top Metric Strip */}
        <div className="grid grid-cols-4 gap-4 px-6 py-3 bg-slate-950/30 border-b border-slate-800 text-xs font-mono">
          <div className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded-lg border border-slate-700/50">
            <span className="text-slate-400">Total Latency:</span>
            <span className="text-indigo-400 font-bold">{telemetry?.total_latency_ms || 0} ms</span>
          </div>
          <div className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded-lg border border-slate-700/50">
            <span className="text-slate-400">Executed Confidence:</span>
            <span className="text-emerald-400 font-bold">{(telemetry?.dynamic_confidence * 100 || 0).toFixed(0)}%</span>
          </div>
          <div className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded-lg border border-slate-700/50">
            <span className="text-slate-400">Active Agents:</span>
            <span className="text-amber-400 font-bold">{telemetry?.active_agents?.length || 0} / 10</span>
          </div>
          <div className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded-lg border border-slate-700/50">
            <span className="text-slate-400">Knowledge Nodes:</span>
            <span className="text-cyan-400 font-bold">{telemetry?.retrieved_nodes?.length || 0} Retrieved</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6 gap-2 text-xs font-medium">
          {[
            { id: 'graph', label: 'Execution Graph', icon: Cpu },
            { id: 'memory', label: 'Stateful Memory', icon: Database },
            { id: 'planner', label: 'Planner Reasoning', icon: Layers },
            { id: 'reflection', label: 'Reflection Audit', icon: ShieldCheck },
            { id: 'grounding', label: 'Grounding Citations', icon: CheckCircle2 },
            { id: 'prompt', label: 'System Prompt', icon: FileCode },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 px-3 flex items-center gap-2 border-b-2 font-mono transition-colors ${
                  isActive 
                    ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10' 
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 p-6 overflow-y-auto font-mono text-xs text-slate-300">
          {activeTab === 'graph' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-indigo-400" />
                  Dynamic DAG Execution Topology
                </h4>
                <div className="grid grid-cols-5 gap-3 p-4 bg-slate-950 rounded-xl border border-slate-800">
                  {allAgents.map((agentName, idx) => {
                    const isExecuted = activeAgentsSet.has(agentName);
                    return (
                      <div 
                        key={agentName}
                        className={`p-3 rounded-lg border flex flex-col justify-between transition-all ${
                          isExecuted 
                            ? 'bg-indigo-950/40 border-indigo-500/50 text-indigo-200 shadow-lg shadow-indigo-500/10' 
                            : 'bg-slate-900/40 border-slate-800 text-slate-600 opacity-60'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-slate-500 font-bold">NODE {idx + 1}</span>
                          <span className={`w-2 h-2 rounded-full ${isExecuted ? 'bg-emerald-400 animate-ping' : 'bg-slate-700'}`} />
                        </div>
                        <span className="font-bold text-xs mt-2">{agentName}</span>
                        <span className={`text-[10px] mt-1 ${isExecuted ? 'text-emerald-400' : 'text-slate-600'}`}>
                          {isExecuted ? '● EXECUTED' : '○ SKIPPED'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-slate-200 mb-3">Agent Step Telemetry & Per-Step Latency</h4>
                <div className="space-y-2">
                  {telemetry?.step_logs?.map((step: any, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-slate-500 text-[10px]">#{idx + 1}</span>
                        <span className="font-bold text-indigo-300 w-32">{step.agent_name}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          step.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                          step.status === 'warning' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-500'
                        }`}>
                          {step.status.toUpperCase()}
                        </span>
                        <span className="text-slate-400 text-xs truncate max-w-md">{step.summary}</span>
                      </div>
                      <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
                        <span>Latency: <strong className="text-indigo-400">{step.latency_ms?.toFixed(2) || '0.10'} ms</strong></span>
                        <span>Conf: <strong className="text-emerald-400">{(step.confidence_score * 100).toFixed(0)}%</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'memory' && (
            <div className="grid grid-cols-2 gap-6">
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                <h4 className="text-sm font-semibold text-slate-200 mb-3 text-amber-400">Memory BEFORE Execution</h4>
                <pre className="p-3 bg-slate-900 rounded-lg text-slate-300 overflow-x-auto text-[11px]">
                  {JSON.stringify(telemetry?.memory_before, null, 2)}
                </pre>
              </div>
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                <h4 className="text-sm font-semibold text-slate-200 mb-3 text-emerald-400">Memory AFTER Execution</h4>
                <pre className="p-3 bg-slate-900 rounded-lg text-slate-300 overflow-x-auto text-[11px]">
                  {JSON.stringify(telemetry?.memory_after, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'planner' && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-slate-200">Deterministic Schedule & Score Breakdown</h4>
              {telemetry?.planner_output ? (
                <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-emerald-300 overflow-x-auto text-[11px]">
                  {JSON.stringify(telemetry?.planner_output, null, 2)}
                </pre>
              ) : (
                <div className="p-8 text-center bg-slate-950 rounded-xl border border-slate-800 text-slate-500">
                  PlannerAgent was skipped for this query intent (Conversational / Conceptual Tutor query).
                </div>
              )}
            </div>
          )}

          {activeTab === 'reflection' && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-slate-200">Reflection Audit Result</h4>
              {telemetry?.reflection_audit ? (
                <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-amber-300 overflow-x-auto text-[11px]">
                  {JSON.stringify(telemetry?.reflection_audit, null, 2)}
                </pre>
              ) : (
                <div className="p-8 text-center bg-slate-950 rounded-xl border border-slate-800 text-slate-500">
                  ReflectionAgent was skipped for this query intent.
                </div>
              )}
            </div>
          )}

          {activeTab === 'grounding' && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-slate-200">Factual Grounding Report & Citations</h4>
              <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-cyan-300 overflow-x-auto text-[11px]">
                {JSON.stringify(telemetry?.grounding_report, null, 2)}
              </pre>
            </div>
          )}

          {activeTab === 'prompt' && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-slate-200">Exact System Prompt sent to Gemini</h4>
              <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-slate-300 overflow-x-auto text-[11px] whitespace-pre-wrap">
                {telemetry?.exact_prompt || 'Conversational direct response.'}
              </pre>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
