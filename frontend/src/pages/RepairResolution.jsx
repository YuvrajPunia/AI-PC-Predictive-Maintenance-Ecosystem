import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { CheckCircle2, AlertTriangle, PenTool, Database, BookOpen, Clock } from 'lucide-react';

export default function RepairResolution({ activeCase, onRepairCompleted }) {
  // If activeCase is passed from Screen 1, we populate it
  const [pcId, setPcId] = useState(activeCase?.pc_id || '');
  const [complaint, setComplaint] = useState(activeCase?.original_complaint || '');
  const [symptoms, setSymptoms] = useState(activeCase?.symptoms || '');
  const [problemDetected, setProblemDetected] = useState(activeCase?.problem_detected || '');
  
  // Technician inputs
  const [confirmedDiagnosis, setConfirmedDiagnosis] = useState('');
  const [rootCause, setRootCause] = useState('');
  const [treatmentTaken, setTreatmentTaken] = useState('');
  const [downtimeMinutes, setDowntimeMinutes] = useState(60);
  const [technicianNotes, setTechnicianNotes] = useState('');

  const [loading, setLoading] = useState(false);
  const [successResult, setSuccessResult] = useState(null);
  const [error, setError] = useState(null);

  // Sync state if activeCase changes
  useEffect(() => {
    if (activeCase) {
      setPcId(activeCase.pc_id);
      setComplaint(activeCase.original_complaint);
      setSymptoms(activeCase.symptoms);
      setProblemDetected(activeCase.problem_detected);
      setSuccessResult(null);
      setError(null);
      
      // Auto-prefill suggestions for confirmation (but NOT copying directly as final text)
      // Leave technician input clean or guide them with suggestions
      setConfirmedDiagnosis('');
      setRootCause('');
      setTreatmentTaken('');
      setTechnicianNotes('');
    }
  }, [activeCase]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pcId) {
      setError("No active PC ID loaded.");
      return;
    }
    if (!confirmedDiagnosis.trim()) {
      setError("Please specify the Confirmed Diagnosis.");
      return;
    }
    if (!rootCause.trim()) {
      setError("Please specify the root cause of this incident.");
      return;
    }
    if (!treatmentTaken.trim()) {
      setError("Please describe the actual treatments taken.");
      return;
    }
    if (downtimeMinutes <= 0) {
      setError("Downtime minutes must be a positive integer.");
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      pc_id: pcId,
      original_complaint: complaint,
      symptoms: symptoms,
      problem_detected: problemDetected,
      confirmed_diagnosis: confirmedDiagnosis,
      root_cause: rootCause,
      treatment_taken: treatmentTaken,
      downtime_minutes: parseInt(downtimeMinutes),
      technician_notes: technicianNotes
    };

    try {
      const res = await api.completeRepair(payload);
      setSuccessResult(res);
      setLoading(false);
      
      // Clear inputs
      setConfirmedDiagnosis('');
      setRootCause('');
      setTreatmentTaken('');
      setTechnicianNotes('');
      
      // Trigger callback to refresh lists
      if (onRepairCompleted) {
        onRepairCompleted();
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Technician Repair Resolution</h1>
        <p className="text-gray-400 text-sm">Commit the actual repair actions back to the database and update the semantic query index.</p>
      </div>

      {!pcId && !successResult && (
        <div className="border border-dashed border-[#1F2937] rounded-lg p-12 text-center text-gray-500 max-w-lg mx-auto mt-12 space-y-4">
          <AlertTriangle className="w-12 h-12 mx-auto text-amber-500/80" />
          <h3 className="text-white font-semibold">No Active Case Loaded</h3>
          <p className="text-sm">
            Please go to the **Raise Complaint & AI Analysis** screen, select a PC, type in the user complaint, and run the analysis. Once analyzed, click the **"Send to Repair Resolution"** button to load the case.
          </p>
        </div>
      )}

      {successResult && (
        <div className="bg-emerald-500/5 border border-emerald-500/20 p-6 rounded-lg max-w-lg mx-auto space-y-4 text-center">
          <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto animate-pulse" />
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">Repair Log Saved successfully!</h3>
            <p className="text-emerald-400 text-sm font-semibold">Indexed for future AI Retrieval</p>
            <p className="text-gray-400 text-xs mt-1">
              Case record has been appended to `repair_history.csv` and mapped to the SQLite database.
            </p>
          </div>
          <div className="bg-[#030712] p-4 rounded border border-[#1F2937] text-left text-xs space-y-2 max-w-xs mx-auto">
            <p className="text-gray-400">New Repair ID: <b className="text-white">{successResult.repair_id}</b></p>
            <p className="text-gray-400">PC ID: <b className="text-white">{successResult.pc_id}</b></p>
            <p className="text-gray-400">Diagnosis: <b className="text-white">{successResult.confirmed_diagnosis}</b></p>
            <p className="text-gray-400">Timestamp: <b className="text-white">{new Date(successResult.timestamp).toLocaleString()}</b></p>
          </div>
          <button
            onClick={() => setSuccessResult(null)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded transition-colors"
          >
            Clear and Load Next Case
          </button>
        </div>
      )}

      {pcId && !successResult && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          
          {/* Left panel: Read-only Case & AI recommendation */}
          <div className="xl:col-span-1 space-y-6">
            
            {/* Case context card */}
            <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-3">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Active Ticket Context</h3>
              <div className="text-xs space-y-1.5">
                <p className="text-gray-400">PC ID: <b className="text-white">{pcId}</b></p>
                <p className="text-gray-400">Predicted Problem: <b className="text-cyan-400 font-semibold">{problemDetected}</b></p>
                <p className="text-gray-400">User Complaint:</p>
                <p className="text-gray-300 italic bg-[#030712] p-2.5 border border-[#1F2937] rounded mt-1">
                  "{complaint}"
                </p>
              </div>
            </div>

            {/* AI Decision support summary */}
            {activeCase?.analysis && (
              <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-4">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">AI Diagnostics Summary</h3>
                
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-[#030712] p-2 border border-[#1F2937] rounded">
                    <p className="text-gray-500 text-[9px] uppercase">Health Score</p>
                    <p className="text-sm font-bold text-white">{activeCase.analysis.predictive_health.health_score}%</p>
                  </div>
                  <div className="bg-[#030712] p-2 border border-[#1F2937] rounded">
                    <p className="text-gray-500 text-[9px] uppercase">Urgency Estimate</p>
                    <p className="text-sm font-bold text-white">
                      {activeCase.analysis.predictive_health.remaining_useful_life_days !== null 
                        ? `${activeCase.analysis.predictive_health.remaining_useful_life_days} Days` 
                        : 'N/A'}
                    </p>
                  </div>
                  <div className="bg-[#030712] p-2 border border-[#1F2937] rounded">
                    <p className="text-gray-500 text-[9px] uppercase">Anomaly label</p>
                    <p className="text-sm font-bold text-white">{activeCase.analysis.anomaly.label}</p>
                  </div>
                  <div className="bg-[#030712] p-2 border border-[#1F2937] rounded">
                    <p className="text-gray-500 text-[9px] uppercase">Risk Level</p>
                    <p className="text-sm font-bold text-white">{activeCase.analysis.predictive_health.risk_level}</p>
                  </div>
                </div>

                <div className="border-t border-[#1F2937] pt-3 text-xs space-y-2">
                  <p className="text-gray-400 font-semibold flex items-center space-x-1">
                    <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                    <span>AI Suggested Action:</span>
                  </p>
                  <p className="text-gray-300 leading-normal bg-[#030712] p-2.5 rounded border border-[#1F2937]">
                    {activeCase.analysis.recommendation.primary_recommendation}
                  </p>
                </div>
              </div>
            )}

          </div>

          {/* Right Panel: Resolution Form */}
          <div className="xl:col-span-2">
            <form onSubmit={handleSubmit} className="bg-[#0B0F19] border border-[#1F2937] p-6 rounded-lg space-y-5">
              <h3 className="text-sm font-semibold text-white border-b border-[#1F2937] pb-3 flex items-center space-x-2">
                <PenTool className="w-4 h-4 text-cyan-500" />
                <span>Actual Technician Resolution Form</span>
              </h3>

              <div className="space-y-4 text-xs">
                
                {/* Confirmed Diagnosis */}
                <div className="space-y-1">
                  <label className="block text-gray-400 font-medium">Confirmed Diagnosis <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    required
                    placeholder="Enter the concrete diagnosis (e.g. Dust-clogged cooling assembly)"
                    className="w-full bg-[#030712] border border-[#1F2937] p-2.5 rounded text-white focus:outline-none focus:border-cyan-500"
                    value={confirmedDiagnosis}
                    onChange={(e) => setConfirmedDiagnosis(e.target.value)}
                  />
                  {activeCase?.analysis?.recommendation?.primary_recommendation && (
                    <div className="mt-1 flex flex-wrap gap-2 items-center text-[10px]">
                      <span className="text-gray-500 font-medium">AI Suggestions:</span>
                      {activeCase.analysis.recommendation.likely_root_causes.map((rc, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setConfirmedDiagnosis(rc)}
                          className="px-1.5 py-0.5 bg-[#111827] text-gray-400 hover:text-white rounded border border-[#1F2937]"
                        >
                          {rc}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Root Cause */}
                <div className="space-y-1">
                  <label className="block text-gray-400 font-medium">Root Cause Description <span className="text-red-500">*</span></label>
                  <textarea
                    rows={2}
                    required
                    placeholder="Describe the underlying cause of failure (e.g. Accumulation of physical dust restricting radiator airflow)"
                    className="w-full bg-[#030712] border border-[#1F2937] p-2.5 rounded text-white focus:outline-none focus:border-cyan-500"
                    value={rootCause}
                    onChange={(e) => setRootCause(e.target.value)}
                  />
                </div>

                {/* Treatment Taken */}
                <div className="space-y-1">
                  <label className="block text-gray-400 font-medium">Treatment / Actions Taken <span className="text-red-500">*</span></label>
                  <textarea
                    rows={3}
                    required
                    placeholder="Detail the actions performed to resolve the issue (e.g. Disassembled cooling system, blew out dust, cleaned fan blades, reapplied high quality thermal grease)"
                    className="w-full bg-[#030712] border border-[#1F2937] p-2.5 rounded text-white focus:outline-none focus:border-cyan-500"
                    value={treatmentTaken}
                    onChange={(e) => setTreatmentTaken(e.target.value)}
                  />
                </div>

                {/* Downtime & Notes */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  
                  <div className="space-y-1 md:col-span-1">
                    <label className="block text-gray-400 font-medium flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>Downtime (Minutes)</span>
                    </label>
                    <input
                      type="number"
                      required
                      min={0}
                      className="w-full bg-[#030712] border border-[#1F2937] p-2.5 rounded text-white focus:outline-none focus:border-cyan-500"
                      value={downtimeMinutes}
                      onChange={(e) => setDowntimeMinutes(e.target.value)}
                    />
                  </div>

                  <div className="space-y-1 md:col-span-2">
                    <label className="block text-gray-400 font-medium">Technician Notes (Optional)</label>
                    <input
                      type="text"
                      placeholder="Additional notes, verification checks, or recommendations for follow-up"
                      className="w-full bg-[#030712] border border-[#1F2937] p-2.5 rounded text-white focus:outline-none focus:border-cyan-500"
                      value={technicianNotes}
                      onChange={(e) => setTechnicianNotes(e.target.value)}
                    />
                  </div>

                </div>

              </div>

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-xs rounded flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4" />
                  <span>{error}</span>
                </div>
              )}

              <div className="border-t border-[#1F2937] pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={loading}
                  className={`px-4 py-2.5 rounded font-semibold text-xs flex items-center space-x-2 transition-colors ${
                    loading 
                      ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                      : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                  }`}
                >
                  <Database className="w-4 h-4" />
                  <span>{loading ? 'Saving to Database...' : 'Complete Repair & Add to Knowledge Base'}</span>
                </button>
              </div>

            </form>
          </div>

        </div>
      )}

    </div>
  );
}
