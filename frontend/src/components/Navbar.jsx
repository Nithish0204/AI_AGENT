import React from 'react';
import { ShieldCheck, Cpu, Activity, BarChart3, MessageSquare, Award } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, onOpenAblation }) {
  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-[1700px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo & Branding */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 p-0.5 shadow-lg shadow-emerald-500/20">
            <div className="h-full w-full bg-zinc-950 rounded-[10px] flex items-center justify-center">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-white">AgentTrace AI</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                Production Guardrails
              </span>
            </div>
            <p className="text-[11px] text-zinc-400">Autonomous & Safe Customer Resolution System</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-zinc-900/90 border border-zinc-800 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('demo')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'demo'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
            }`}
          >
            <MessageSquare className="h-3.5 w-3.5 text-emerald-400" />
            Live Agent Demo & Trace
          </button>
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'dashboard'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5 text-cyan-400" />
            Supervisor Dashboard
          </button>
        </div>

        {/* System Status & Benchmark Link */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenAblation}
            className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 text-emerald-300 border border-emerald-500/30 hover:border-emerald-500/60 transition-all hover:shadow-sm"
          >
            <Award className="h-3.5 w-3.5 text-emerald-400" />
            Benchmark & Ablation
          </button>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-[11px]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-zinc-300 font-medium font-mono">Gemini 3.8 Flash</span>
          </div>
        </div>
      </div>
    </header>
  );
}
