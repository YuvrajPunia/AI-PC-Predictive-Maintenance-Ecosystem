import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Search, PenTool, Calendar, ShieldCheck, Clock, BookOpen, X } from 'lucide-react';

export default function RepairHistory({ updateTrigger }) {
  const [repairs, setRepairs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Search
  const [search, setSearch] = useState('');
  
  // Active Modal state
  const [activeRepair, setActiveRepair] = useState(null);

  useEffect(() => {
    setLoading(true);
    api.getRepairs()
      .then(res => {
        setRepairs(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [updateTrigger]);

  const filteredRepairs = repairs.filter(rep => {
    const term = search.toLowerCase();
    return (
      rep.repair_id.toLowerCase().includes(term) ||
      rep.pc_id.toLowerCase().includes(term) ||
      rep.user_complaint.toLowerCase().includes(term) ||
      rep.confirmed_diagnosis.toLowerCase().includes(term) ||
      rep.root_cause.toLowerCase().includes(term) ||
      rep.treatment_taken.toLowerCase().includes(term) ||
      rep.problem_detected.toLowerCase().includes(term)
    );
  });

  if (loading) {
    return (
      <div className="flex-1 flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-white">Repair Incident Logs & Knowledge Base</h1>
        <p className="text-gray-400 text-sm">Query and audit completed repairs globally across organization departments.</p>
      </div>

      {/* Search */}
      <div className="bg-[#0B0F19] border border-[#1F2937] p-4 rounded-lg flex items-center space-x-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search ID, PC, complaint, diagnosis, treatment, root cause..."
            className="w-full bg-[#030712] border border-[#1F2937] pl-9 pr-4 py-2 rounded text-xs text-white focus:outline-none focus:border-cyan-500"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span className="text-xs text-gray-500">{filteredRepairs.length} records found</span>
      </div>

      {/* List Table */}
      <div className="bg-[#0B0F19] border border-[#1F2937] rounded-lg overflow-hidden">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#030712] border-b border-[#1F2937] text-gray-400 font-semibold uppercase tracking-wider">
              <th className="p-4">Repair ID</th>
              <th className="p-4">PC ID</th>
              <th className="p-4">Timestamp</th>
              <th className="p-4">Problem</th>
              <th className="p-4">Confirmed Diagnosis</th>
              <th className="p-4">Root Cause</th>
              <th className="p-4 text-center">Downtime</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1F2937] text-gray-300">
            {filteredRepairs.map(rep => (
              <tr 
                key={rep.repair_id}
                onClick={() => setActiveRepair(rep)}
                className="hover:bg-[#111827] cursor-pointer transition-colors"
              >
                <td className="p-4 font-bold text-cyan-400">{rep.repair_id}</td>
                <td className="p-4 font-semibold text-white">{rep.pc_id}</td>
                <td className="p-4 text-gray-400">{new Date(rep.timestamp).toLocaleDateString()}</td>
                <td className="p-4">
                  <span className="px-2 py-0.5 bg-[#111827] text-gray-400 rounded-full font-medium">
                    {rep.problem_detected}
                  </span>
                </td>
                <td className="p-4 text-white font-medium">{rep.confirmed_diagnosis}</td>
                <td className="p-4 text-gray-400 max-w-xs truncate">{rep.root_cause}</td>
                <td className="p-4 text-center text-gray-400 font-medium">{rep.downtime_minutes} m</td>
              </tr>
            ))}
            {filteredRepairs.length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-gray-500">No repair logs match query filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Modal Overlay */}
      {activeRepair && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-[#0B0F19] border border-[#1F2937] w-full max-w-lg rounded-lg overflow-hidden flex flex-col relative animate-in zoom-in-95 duration-200">
            <button 
              onClick={() => setActiveRepair(null)}
              className="absolute top-4 right-4 p-1.5 hover:bg-[#111827] rounded text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="p-5 border-b border-[#1F2937] bg-[#030712] flex items-center space-x-2.5">
              <PenTool className="w-5 h-5 text-cyan-500" />
              <div>
                <h3 className="font-bold text-white text-base">Repair Log: {activeRepair.repair_id}</h3>
                <p className="text-[10px] text-gray-500">Target Asset PC: {activeRepair.pc_id}</p>
              </div>
            </div>

            <div className="p-5 text-xs space-y-4 max-h-[70vh] overflow-y-auto">
              
              <div className="flex items-center space-x-5 text-gray-400 border-b border-[#1F2937] pb-3">
                <div className="flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5 text-cyan-500" />
                  <span>Date: {new Date(activeRepair.timestamp).toLocaleString()}</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <Clock className="w-3.5 h-3.5 text-cyan-500" />
                  <span>Downtime: {activeRepair.downtime_minutes} Minutes</span>
                </div>
              </div>

              <div>
                <p className="text-gray-500 font-bold uppercase tracking-wider text-[9px] mb-1">User Complaint Details</p>
                <p className="text-gray-300 italic bg-[#030712] p-2.5 border border-[#1F2937] rounded">
                  "{activeRepair.user_complaint}"
                </p>
              </div>

              <div>
                <p className="text-gray-500 font-bold uppercase tracking-wider text-[9px] mb-1">Symptoms profile</p>
                <p className="text-white bg-[#030712] p-2.5 border border-[#1F2937] rounded">
                  {activeRepair.symptoms}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-500 font-bold uppercase tracking-wider text-[9px] mb-1">Confirmed Diagnosis</p>
                  <p className="text-white font-medium">{activeRepair.confirmed_diagnosis}</p>
                </div>
                <div>
                  <p className="text-gray-500 font-bold uppercase tracking-wider text-[9px] mb-1">Problem Category</p>
                  <span className="px-2 py-0.5 bg-gray-800 text-gray-400 font-bold rounded">
                    {activeRepair.problem_detected}
                  </span>
                </div>
              </div>

              <div>
                <p className="text-gray-500 font-bold uppercase tracking-wider text-[9px] mb-1">Root Cause Analysis</p>
                <p className="text-gray-300 leading-relaxed bg-[#030712] p-2.5 border border-[#1F2937] rounded">
                  {activeRepair.root_cause}
                </p>
              </div>

              <div>
                <p className="text-gray-500 font-bold uppercase tracking-wider text-[9px] mb-1">Treatment Performed</p>
                <p className="text-gray-300 leading-relaxed bg-[#030712] p-2.5 border border-[#1F2937] rounded">
                  {activeRepair.treatment_taken}
                </p>
              </div>

              <div>
                <p className="text-gray-500 font-bold uppercase tracking-wider text-[9px] mb-1">Technician Notes</p>
                <p className="text-gray-300 leading-relaxed bg-[#030712] p-2.5 border border-[#1F2937] rounded">
                  {activeRepair.technician_notes || 'No additional notes provided.'}
                </p>
              </div>

            </div>

            <div className="p-4 border-t border-[#1F2937] bg-[#030712] flex justify-end">
              <button 
                onClick={() => setActiveRepair(null)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
