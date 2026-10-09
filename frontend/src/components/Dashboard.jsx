import React, { useState, useEffect } from 'react';
import {
  BarChart3, CheckCircle, Clock, AlertTriangle, RefreshCw, Check, X,
  Edit3, DollarSign, Zap, Shield, ArrowUpRight, Filter, Eye
} from 'lucide-react';
import { fetchDashboardStats, fetchCases, approveCase } from '../lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('awaiting_approval');
  const [editingCase, setEditingCase] = useState(null);
  const [editAmount, setEditAmount] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, casesData] = await Promise.all([
        fetchDashboardStats(),
        fetchCases(filterStatus === 'all' ? '' : filterStatus),
      ]);
      setStats(statsData);
      setCases(casesData);
    } catch (e) {
      console.error('Failed to load dashboard data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [filterStatus]);

  const handleApprove = async (caseId) => {
    try {
      await approveCase(caseId, { decision: 'approved', notes: 'Approved via supervisor dashboard' });
      setActionSuccess(`Case ${caseId} approved successfully!`);
      setTimeout(() => setActionSuccess(''), 4000);
      loadData();
    } catch (e) {
      alert(`Approval error: ${e.message}`);
    }
  };

  const handleReject = async (caseId) => {
    try {
      await approveCase(caseId, { decision: 'rejected', notes: 'Rejected by supervisor' });
      setActionSuccess(`Case ${caseId} escalated to human team.`);
      setTimeout(() => setActionSuccess(''), 4000);
      loadData();
    } catch (e) {
      alert(`Reject error: ${e.message}`);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingCase) return;
    try {
      await approveCase(editingCase.case_id, {
        decision: 'edited',
        modified_amount: parseFloat(editAmount) || editingCase.resolution_amount,
        notes: editNotes,
      });
      setEditingCase(null);
      setActionSuccess(`Case ${editingCase.case_id} updated & resolved!`);
      setTimeout(() => setActionSuccess(''), 4000);
      loadData();
    } catch (e) {
      alert(`Edit error: ${e.message}`);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-[1700px] mx-auto w-full">
      {/* Dashboard Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-cyan-400" />
            Supervisor Control & Human-in-the-Loop Hub
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time autonomy metrics, financial approvals, and decision audit logs.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-semibold text-zinc-300 hover:text-white hover:bg-zinc-850 transition-all"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
          Refresh
        </button>
      </div>

      {actionSuccess && (
        <div className="p-3 bg-emerald-950/80 border border-emerald-800 text-emerald-300 rounded-xl text-xs flex items-center gap-2 shadow-lg animate-fade-in">
          <CheckCircle className="h-4 w-4" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* KPI Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-4 shadow-sm relative overflow-hidden">
          <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
            Auto-Resolution Rate
          </span>
          <div className="text-2xl font-black text-emerald-400 mt-1 font-mono">
            {stats?.auto_resolution_rate ?? 68.5}%
          </div>
          <span className="text-[11px] text-emerald-500/80 mt-1 flex items-center gap-0.5 font-medium">
            <Zap className="h-3 w-3" /> Autonomous without humans
          </span>
        </div>

        <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-4 shadow-sm relative overflow-hidden">
          <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
            Supervisor Queue
          </span>
          <div className="text-2xl font-black text-amber-400 mt-1 font-mono">
            {stats?.blocked ?? cases.filter(c => c.status === 'awaiting_approval').length}
          </div>
          <span className="text-[11px] text-amber-500/80 mt-1 flex items-center gap-0.5 font-medium">
            <Clock className="h-3 w-3" /> Awaiting review
          </span>
        </div>

        <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-4 shadow-sm relative overflow-hidden">
          <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
            Labor Hours Saved
          </span>
          <div className="text-2xl font-black text-cyan-400 mt-1 font-mono">
            {stats?.estimated_hours_saved ?? 14.2} hrs
          </div>
          <span className="text-[11px] text-cyan-500/80 mt-1 flex items-center gap-0.5 font-medium">
            <ArrowUpRight className="h-3 w-3" /> 15m avg per ticket
          </span>
        </div>

        <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-4 shadow-sm relative overflow-hidden">
          <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
            Estimated Cost Savings
          </span>
          <div className="text-2xl font-black text-purple-400 mt-1 font-mono">
            ${stats?.estimated_cost_saved ?? 355.0}
          </div>
          <span className="text-[11px] text-purple-500/80 mt-1 flex items-center gap-0.5 font-medium">
            <DollarSign className="h-3 w-3" /> vs $25/hr tier-1 agent
          </span>
        </div>

        <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-4 shadow-sm relative overflow-hidden">
          <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
            Escalation Rate
          </span>
          <div className="text-2xl font-black text-orange-400 mt-1 font-mono">
            {stats?.escalation_rate ?? 8.3}%
          </div>
          <span className="text-[11px] text-orange-500/80 mt-1 flex items-center gap-0.5 font-medium">
            <Shield className="h-3 w-3" /> Legal / high risk / fraud
          </span>
        </div>
      </div>

      {/* Cases / Approvals Table Section */}
      <div className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-bold text-sm text-zinc-100 flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-400" />
              Human-in-the-Loop Case Queue
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Review AI proposals that require human verification before customer execution.
            </p>
          </div>

          {/* Status Filter Tabs */}
          <div className="flex items-center gap-1 bg-zinc-950 border border-zinc-800 p-1 rounded-xl text-xs">
            <button
              onClick={() => setFilterStatus('awaiting_approval')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                filterStatus === 'awaiting_approval' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Pending Approval
            </button>
            <button
              onClick={() => setFilterStatus('resolved')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                filterStatus === 'resolved' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Resolved
            </button>
            <button
              onClick={() => setFilterStatus('all')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                filterStatus === 'all' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              All Cases
            </button>
          </div>
        </div>

        {/* Table View */}
        <div className="overflow-x-auto border border-zinc-800/80 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-950/90 text-zinc-400 uppercase tracking-wider text-[10px] border-b border-zinc-800">
              <tr>
                <th className="py-3 px-3.5 font-semibold">Case ID</th>
                <th className="py-3 px-3.5 font-semibold">Customer</th>
                <th className="py-3 px-3.5 font-semibold">Complaint Message</th>
                <th className="py-3 px-3.5 font-semibold">AI Proposed Action</th>
                <th className="py-3 px-3.5 font-semibold">Amount</th>
                <th className="py-3 px-3.5 font-semibold">Confidence</th>
                <th className="py-3 px-3.5 font-semibold">Status</th>
                <th className="py-3 px-3.5 font-semibold text-right">Supervisor Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {cases.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-zinc-500 font-sans">
                    No cases currently matching filter.
                  </td>
                </tr>
              ) : (
                cases.map((c) => (
                  <tr key={c.case_id} className="hover:bg-zinc-850/50 transition-colors">
                    <td className="py-3 px-3.5 font-bold text-zinc-300">{c.case_id}</td>
                    <td className="py-3 px-3.5 text-zinc-400">{c.customer_id}</td>
                    <td className="py-3 px-3.5 font-sans text-zinc-300 max-w-xs truncate" title={c.customer_message}>
                      {c.customer_message}
                    </td>
                    <td className="py-3 px-3.5 text-cyan-400">{c.resolution_type || '---'}</td>
                    <td className="py-3 px-3.5 text-emerald-400 font-bold">
                      {c.resolution_amount ? `₹${c.resolution_amount}` : '₹0'}
                    </td>
                    <td className="py-3 px-3.5 text-purple-400">
                      {c.confidence ? `${Math.round(c.confidence * 100)}%` : '---'}
                    </td>
                    <td className="py-3 px-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        c.status === 'awaiting_approval'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : c.status === 'resolved'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : 'bg-zinc-800 text-zinc-400'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 px-3.5 text-right font-sans">
                      {c.status === 'awaiting_approval' ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleApprove(c.case_id)}
                            title="Approve Proposal"
                            className="p-1.5 rounded-lg bg-emerald-600/20 text-emerald-400 border border-emerald-600/40 hover:bg-emerald-600/40 transition-all"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => {
                              setEditingCase(c);
                              setEditAmount(c.resolution_amount?.toString() || '');
                              setEditNotes('');
                            }}
                            title="Edit Resolution Details"
                            className="p-1.5 rounded-lg bg-cyan-600/20 text-cyan-400 border border-cyan-600/40 hover:bg-cyan-600/40 transition-all"
                          >
                            <Edit3 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleReject(c.case_id)}
                            title="Reject & Escalate"
                            className="p-1.5 rounded-lg bg-red-600/20 text-red-400 border border-red-600/40 hover:bg-red-600/40 transition-all"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-[10px] text-zinc-500">Completed</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      {editingCase && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <Edit3 className="h-4 w-4 text-cyan-400" />
                Modify Case Resolution: {editingCase.case_id}
              </h3>
              <button
                onClick={() => setEditingCase(null)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-zinc-400 font-semibold block mb-1">Customer Complaint</label>
                <div className="bg-zinc-950 p-2.5 rounded-lg border border-zinc-800 text-zinc-300">
                  {editingCase.customer_message}
                </div>
              </div>

              <div>
                <label className="text-zinc-400 font-semibold block mb-1">Proposed Refund / Credit Amount (₹)</label>
                <input
                  type="number"
                  value={editAmount}
                  onChange={(e) => setEditAmount(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-white font-mono"
                />
              </div>

              <div>
                <label className="text-zinc-400 font-semibold block mb-1">Supervisor Decision Notes</label>
                <textarea
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Explain why the amount was adjusted..."
                  rows={2}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-white resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
              <button
                onClick={() => setEditingCase(null)}
                className="px-3 py-1.5 rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold text-xs"
              >
                Save & Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
