import React from 'react';
import { Shield, Sparkles, CheckCircle, Clock, AlertTriangle, ArrowRight, CornerDownRight, Database, Bot } from 'lucide-react';

export default function GraphView({ traceEvents, activeCaseData }) {
  // Check which nodes have executed in trace
  const executedNodes = new Set(traceEvents.map(e => e.node));
  const isBlocked = traceEvents.some(e => e.event_type === 'injection_detected' || e.data?.autonomy_level === 'blocked');
  const autonomy = activeCaseData?.autonomy_level || '';

  const getNodeState = (name) => {
    if (name === 'blocked' && isBlocked) return 'active-red';
    if (isBlocked && name !== 'intake' && name !== 'blocked') return 'skipped';
    if (executedNodes.has(name)) return 'active-green';
    return 'idle';
  };

  const getStyle = (state) => {
    switch (state) {
      case 'active-green':
        return 'bg-emerald-950/80 border-emerald-500 text-emerald-300 shadow-lg shadow-emerald-500/20';
      case 'active-red':
        return 'bg-red-950/80 border-red-500 text-red-300 shadow-lg shadow-red-500/20';
      case 'active-amber':
        return 'bg-amber-950/80 border-amber-500 text-amber-300 shadow-lg shadow-amber-500/20';
      case 'skipped':
        return 'bg-zinc-950/40 border-zinc-800 text-zinc-600 opacity-50';
      default:
        return 'bg-zinc-900/60 border-zinc-800 text-zinc-400';
    }
  };

  return (
    <div className="bg-zinc-950/90 border-t border-zinc-800/80 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-emerald-400" />
          <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-wider">
            LangGraph Execution Topology
          </h3>
        </div>
        <span className="text-[10px] text-zinc-500 font-mono">
          Stateful Conditional Directed Graph
        </span>
      </div>

      {/* Graph Diagram Container */}
      <div className="overflow-x-auto pb-2">
        <div className="flex items-center gap-2 min-w-max text-xs">
          {/* 1. Intake */}
          <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[100px] transition-all ${getStyle(getNodeState('intake'))}`}>
            <span className="text-[10px] font-mono text-zinc-500">Node 1</span>
            <span className="font-bold text-xs mt-0.5">Intake</span>
            <span className="text-[9px] text-zinc-400 mt-1">PII / Injection</span>
          </div>

          <ArrowRight className="h-4 w-4 text-zinc-600 shrink-0" />

          {/* Conditional Branch for Injection */}
          {isBlocked ? (
            <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[110px] transition-all ${getStyle('active-red')}`}>
              <span className="text-[10px] font-mono text-red-500">Security Edge</span>
              <span className="font-bold text-xs mt-0.5 text-red-400">Blocked Gate</span>
              <span className="text-[9px] text-red-500 mt-1">Direct Refusal</span>
            </div>
          ) : (
            <>
              {/* 2. Triage */}
              <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[100px] transition-all ${getStyle(getNodeState('triage'))}`}>
                <span className="text-[10px] font-mono text-zinc-500">Node 2</span>
                <span className="font-bold text-xs mt-0.5">Triage</span>
                <span className="text-[9px] text-zinc-400 mt-1">Intent / Urgency</span>
              </div>

              <ArrowRight className="h-4 w-4 text-zinc-600 shrink-0" />

              {/* 3. Planner */}
              <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[100px] transition-all ${getStyle(getNodeState('planner'))}`}>
                <span className="text-[10px] font-mono text-zinc-500">Node 3</span>
                <span className="font-bold text-xs mt-0.5">Planner</span>
                <span className="text-[9px] text-zinc-400 mt-1">Tool Routing</span>
              </div>

              <ArrowRight className="h-4 w-4 text-zinc-600 shrink-0" />

              {/* 4. Tools (Parallel) */}
              <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[110px] transition-all ${getStyle(getNodeState('tools'))}`}>
                <span className="text-[10px] font-mono text-zinc-500">Node 4</span>
                <span className="font-bold text-xs mt-0.5">Tools Exec</span>
                <span className="text-[9px] text-zinc-400 mt-1">Orders / RAG</span>
              </div>

              <ArrowRight className="h-4 w-4 text-zinc-600 shrink-0" />

              {/* 5. Reasoner */}
              <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[100px] transition-all ${getStyle(getNodeState('reasoner'))}`}>
                <span className="text-[10px] font-mono text-zinc-500">Node 5</span>
                <span className="font-bold text-xs mt-0.5">Reasoner</span>
                <span className="text-[9px] text-zinc-400 mt-1">Evidence Synth</span>
              </div>

              <ArrowRight className="h-4 w-4 text-zinc-600 shrink-0" />

              {/* 6. Critic */}
              <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[100px] transition-all ${getStyle(getNodeState('critic'))}`}>
                <span className="text-[10px] font-mono text-zinc-500">Node 6</span>
                <span className="font-bold text-xs mt-0.5">Critic Loop</span>
                <span className="text-[9px] text-zinc-400 mt-1">Fact-check</span>
              </div>

              <ArrowRight className="h-4 w-4 text-zinc-600 shrink-0" />

              {/* 7. Guardrails Gate (Deterministic Authority) */}
              <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[110px] transition-all ${getStyle(getNodeState('guardrails'))}`}>
                <span className="text-[10px] font-mono text-zinc-500">Node 7 (Code)</span>
                <span className="font-bold text-xs mt-0.5">Guardrails</span>
                <span className="text-[9px] text-zinc-400 mt-1">₹ & Risk Gates</span>
              </div>

              <ArrowRight className="h-4 w-4 text-zinc-600 shrink-0" />

              {/* 8. Responder */}
              <div className={`p-2.5 rounded-xl border flex flex-col items-center min-w-[100px] transition-all ${getStyle(getNodeState('responder'))}`}>
                <span className="text-[10px] font-mono text-zinc-500">Node 8</span>
                <span className="font-bold text-xs mt-0.5">Responder</span>
                <span className="text-[9px] text-zinc-400 mt-1">Multilingual</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
