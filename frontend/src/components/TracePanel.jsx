import React, { useState } from 'react';
import {
  Terminal, ShieldCheck, CheckCircle2, AlertTriangle, XCircle, Clock,
  ChevronDown, ChevronRight, Layers, Database, Sparkles, AlertOctagon, Search, FileText
} from 'lucide-react';

export default function TracePanel({ traceEvents, isProcessing, activeCaseData }) {
  const [expandedNodes, setExpandedNodes] = useState({});
  const [activeTab, setActiveTab] = useState('timeline'); // 'timeline' | 'raw'

  const toggleNode = (nodeKey) => {
    setExpandedNodes(prev => ({
      ...prev,
      [nodeKey]: !prev[nodeKey],
    }));
  };

  // Group events by node name
  const nodeOrder = ['intake', 'triage', 'planner', 'tools', 'reasoner', 'critic', 'guardrails', 'responder', 'logger'];
  
  const groupedEvents = {};
  traceEvents.forEach(evt => {
    const node = evt.node || 'system';
    if (!groupedEvents[node]) groupedEvents[node] = [];
    groupedEvents[node].push(evt);
  });

  const getConfidence = () => {
    if (activeCaseData?.confidence) return Math.round(activeCaseData.confidence * 100);
    // Try to find in trace
    for (let evt of traceEvents) {
      if (evt.data?.confidence) return Math.round(evt.data.confidence * 100);
      if (evt.data?.resolution_confidence) return Math.round(evt.data.resolution_confidence * 100);
    }
    return null;
  };

  const getAutonomyBadge = () => {
    const level = activeCaseData?.autonomy_level || '';
    if (level === 'auto_resolve') {
      return { text: 'AUTO-RESOLVE', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' };
    }
    if (level === 'human_approval') {
      return { text: 'HUMAN APPROVAL', color: 'bg-amber-500/20 text-amber-400 border-amber-500/40' };
    }
    if (level === 'escalate') {
      return { text: 'ESCALATE', color: 'bg-orange-500/20 text-orange-400 border-orange-500/40' };
    }
    if (level === 'blocked') {
      return { text: 'INJECTION BLOCKED', color: 'bg-red-500/20 text-red-400 border-red-500/40' };
    }
    return null;
  };

  const autonomyBadge = getAutonomyBadge();
  const confidence = getConfidence();

  return (
    <div className="flex flex-col h-full bg-zinc-950/80 border-r border-zinc-800/80">
      {/* Trace Header & Telemetry */}
      <div className="p-4 border-b border-zinc-800/80 bg-zinc-900/60">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-emerald-400" />
            <h2 className="font-bold text-sm text-zinc-100">Live Agent Reasoning Trace</h2>
            <span className="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
              SSE Stream
            </span>
          </div>

          <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 p-0.5 rounded-lg text-xs">
            <button
              onClick={() => setActiveTab('timeline')}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                activeTab === 'timeline' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Node Timeline
            </button>
            <button
              onClick={() => setActiveTab('raw')}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                activeTab === 'raw' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Raw Events ({traceEvents.length})
            </button>
          </div>
        </div>

        {/* Telemetry KPIs */}
        <div className="grid grid-cols-3 gap-2 mt-2">
          {/* Confidence Meter */}
          <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2.5">
            <span className="text-[10px] uppercase font-semibold text-zinc-400 tracking-wider block mb-1">
              Confidence
            </span>
            <div className="flex items-center justify-between">
              <span className="text-base font-bold font-mono text-cyan-400">
                {confidence !== null ? `${confidence}%` : '---'}
              </span>
              <div className="w-12 bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-cyan-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${confidence || 0}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Autonomy Decision */}
          <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2.5">
            <span className="text-[10px] uppercase font-semibold text-zinc-400 tracking-wider block mb-1">
              Guardrail Authority
            </span>
            <div>
              {autonomyBadge ? (
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border inline-block ${autonomyBadge.color}`}>
                  {autonomyBadge.text}
                </span>
              ) : (
                <span className="text-xs text-zinc-500 font-mono">Evaluating...</span>
              )}
            </div>
          </div>

          {/* Nodes Step Counter */}
          <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2.5">
            <span className="text-[10px] uppercase font-semibold text-zinc-400 tracking-wider block mb-1">
              Graph Progression
            </span>
            <div className="flex items-center gap-1.5">
              <span className="text-base font-bold font-mono text-emerald-400">
                {Object.keys(groupedEvents).length}
              </span>
              <span className="text-xs text-zinc-500">/ 10 Nodes</span>
              {isProcessing && (
                <span className="animate-spin text-emerald-400 text-xs ml-auto">⚡</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Body: Timeline vs Raw */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {traceEvents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-500">
            <Layers className="h-8 w-8 text-zinc-700 mb-2" />
            <p className="text-xs font-semibold text-zinc-400">Awaiting Graph Activation</p>
            <p className="text-[11px] text-zinc-600 max-w-xs mt-1">
              When a message is sent, you'll see every LangGraph node execute step-by-step with sub-millisecond telemetry.
            </p>
          </div>
        ) : activeTab === 'timeline' ? (
          <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-[2px] before:bg-zinc-800">
            {Object.keys(groupedEvents).map((nodeName, idx) => {
              const events = groupedEvents[nodeName];
              const isExpanded = !!expandedNodes[nodeName];
              const lastEvt = events[events.length - 1];
              const isBlocked = events.some(e => e.event_type === 'injection_detected' || e.data?.autonomy_level === 'blocked');

              return (
                <div key={nodeName} className="relative group">
                  {/* Node Status Icon Node Marker */}
                  <div className={`absolute -left-[23px] top-1.5 h-5 w-5 rounded-full border flex items-center justify-center text-[10px] font-bold shadow-md ${
                    isBlocked
                      ? 'bg-red-950 border-red-500 text-red-400'
                      : 'bg-zinc-900 border-emerald-500 text-emerald-400'
                  }`}>
                    {idx + 1}
                  </div>

                  {/* Node Card */}
                  <div className={`bg-zinc-900/90 border rounded-xl overflow-hidden transition-all ${
                    isBlocked
                      ? 'border-red-900/60 bg-red-950/10'
                      : 'border-zinc-800 hover:border-zinc-700'
                  }`}>
                    {/* Card Top Header */}
                    <button
                      onClick={() => toggleNode(nodeName)}
                      className="w-full px-3.5 py-2.5 flex items-center justify-between text-left hover:bg-zinc-850/60 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-zinc-200 uppercase tracking-wide font-mono">
                          {nodeName}
                        </span>
                        <span className="text-[10px] text-zinc-400 px-1.5 py-0.2 rounded bg-zinc-800/80">
                          {events.length} {events.length === 1 ? 'event' : 'events'}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {isBlocked ? (
                          <span className="text-[10px] font-bold text-red-400 flex items-center gap-1">
                            <AlertOctagon className="h-3 w-3" /> BLOCKED
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" /> Completed
                          </span>
                        )}
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-zinc-400" />
                        )}
                      </div>
                    </button>

                    {/* Summary snippet if collapsed */}
                    {!isExpanded && (
                      <div className="px-3.5 pb-2.5 pt-0 text-[11px] text-zinc-400 line-clamp-1 font-mono">
                        {nodeName === 'intake' && events[0]?.data?.language && (
                          <span>Lang: <strong>{events[0].data.language}</strong> | PII Masked: <strong>{events[0].data.pii_entities_count || 0}</strong></span>
                        )}
                        {nodeName === 'triage' && (
                          <span>Intent: <strong>{events[0]?.data?.primary_intent || 'Analyzed'}</strong></span>
                        )}
                        {nodeName === 'tools' && (
                          <span>Executed: <strong>{events.map(e => e.data?.tool_name || '').filter(Boolean).join(', ') || 'Parallel Lookups'}</strong></span>
                        )}
                        {nodeName === 'reasoner' && (
                          <span>Decision: <strong>{lastEvt?.data?.resolution_type || 'Calculated'}</strong></span>
                        )}
                        {nodeName === 'guardrails' && (
                          <span>Gate: <strong>{lastEvt?.data?.autonomy_level || 'Enforced'}</strong></span>
                        )}
                      </div>
                    )}

                    {/* Expanded Details */}
                    {isExpanded && (
                      <div className="px-3.5 py-2.5 bg-zinc-950/60 border-t border-zinc-800/60 space-y-2 text-xs">
                        {events.map((evt, eIdx) => (
                          <div key={eIdx} className="bg-zinc-900 border border-zinc-800/80 rounded-lg p-2.5">
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                                {evt.event_type || 'event'}
                              </span>
                              {evt.latency_ms && (
                                <span className="text-[9px] font-mono text-zinc-500">
                                  {evt.latency_ms} ms
                                </span>
                              )}
                            </div>
                            
                            {/* Render Structured Event Details */}
                            {evt.data && (
                              <pre className="text-[10px] font-mono text-zinc-300 bg-zinc-950 p-2 rounded border border-zinc-855 overflow-x-auto whitespace-pre-wrap max-h-48">
                                {JSON.stringify(evt.data, null, 2)}
                              </pre>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <pre className="text-[10px] font-mono text-zinc-300 bg-zinc-950 p-3 rounded-xl border border-zinc-800/80 overflow-x-auto">
            {JSON.stringify(traceEvents, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
