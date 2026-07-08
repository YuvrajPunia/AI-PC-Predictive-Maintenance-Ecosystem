import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Search, Monitor, Thermometer, Cpu, Zap, Activity, Info, X } from 'lucide-react';

export default function PCFleet() {
  const [pcs, setPcs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Search & Filter state
  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [locFilter, setLocFilter] = useState('');
  
  // Detail Drawer state
  const [selectedPc, setSelectedPc] = useState(null);
  const [telemetry, setTelemetry] = useState([]);
  const [telLoading, setTelLoading] = useState(false);

  useEffect(() => {
    api.getPcs()
      .then(res => {
        setPcs(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const handleRowClick = async (pc) => {
    setSelectedPc(pc);
    setTelLoading(true);
    setTelemetry([]);
    try {
      const history = await api.getPcTelemetry(pc.pc_id);
      setTelemetry(history);
      setTelLoading(false);
    } catch (err) {
      console.error(err);
      setTelLoading(false);
    }
  };

  // Helper: Simple frontend health calculation to display list scores
  const estimateHealth = (pc) => {
    let score = 100;
    if (pc.temperature > 75) score -= (pc.temperature - 75) * 1.5;
    if (pc.voltage < 12) score -= (12 - pc.voltage) * 8;
    if (pc.voltage > 18) score -= (pc.voltage - 18) * 8;
    if (pc.cpu_usage > 85 && pc.ram_usage > 85) score -= 15;
    return Math.max(0, Math.min(100, Math.round(score)));
  };

  const getHealthBand = (score) => {
    if (score >= 80) return { label: 'Healthy', color: 'text-emerald-400 bg-emerald-500/10' };
    if (score >= 60) return { label: 'Moderate', color: 'text-blue-400 bg-blue-500/10' };
    if (score >= 40) return { label: 'Poor', color: 'text-amber-400 bg-amber-500/10' };
    return { label: 'Critical', color: 'text-red-400 bg-red-500/10 border border-red-500/20' };
  };

  const filteredPcs = pcs.filter(pc => {
    const matchesSearch = pc.pc_id.toLowerCase().includes(search.toLowerCase()) || 
                          pc.model_name.toLowerCase().includes(search.toLowerCase());
    const matchesDept = !deptFilter || pc.department === deptFilter;
    const matchesLoc = !locFilter || pc.location === locFilter;
    return matchesSearch && matchesDept && matchesLoc;
  });

  const depts = [...new Set(pcs.map(p => p.department))];
  const locs = [...new Set(pcs.map(p => p.location))];

  if (loading) {
    return (
      <div className="flex-1 flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      
      {/* Fleet List Panel */}
      <div className="flex-1 flex flex-col p-6 space-y-4 overflow-y-auto">
        <div>
          <h1 className="text-2xl font-bold text-white">DRDO Fleet PC Registry</h1>
          <p className="text-gray-400 text-sm">Review asset configuration, department allocation, and real-time sensor metrics.</p>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-[#0B0F19] border border-[#1F2937] p-4 rounded-lg">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search PC ID or Model..."
              className="w-full bg-[#030712] border border-[#1F2937] pl-9 pr-4 py-2 rounded text-xs text-white focus:outline-none focus:border-cyan-500"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            className="bg-[#030712] border border-[#1F2937] px-3 py-2 rounded text-xs text-white focus:outline-none focus:border-cyan-500"
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
          >
            <option value="">All Departments</option>
            {depts.map(d => <option key={d} value={d}>{d}</option>)}
          </select>

          <select
            className="bg-[#030712] border border-[#1F2937] px-3 py-2 rounded text-xs text-white focus:outline-none focus:border-cyan-500"
            value={locFilter}
            onChange={(e) => setLocFilter(e.target.value)}
          >
            <option value="">All Locations</option>
            {locs.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>

        {/* Table */}
        <div className="bg-[#0B0F19] border border-[#1F2937] rounded-lg overflow-hidden flex-1 overflow-y-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#030712] border-b border-[#1F2937] text-gray-400 font-semibold uppercase tracking-wider">
                <th className="p-4">PC ID</th>
                <th className="p-4">Model Name</th>
                <th className="p-4">Department</th>
                <th className="p-4">Location</th>
                <th className="p-4 text-center">CPU</th>
                <th className="p-4 text-center">RAM</th>
                <th className="p-4 text-center">Temp</th>
                <th className="p-4 text-center">Health</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937] text-gray-300">
              {filteredPcs.map(pc => {
                const health = estimateHealth(pc);
                const band = getHealthBand(health);
                return (
                  <tr 
                    key={pc.pc_id}
                    onClick={() => handleRowClick(pc)}
                    className="hover:bg-[#111827] cursor-pointer transition-colors"
                  >
                    <td className="p-4 font-bold text-white">{pc.pc_id}</td>
                    <td className="p-4">{pc.model_name}</td>
                    <td className="p-4 text-gray-400">{pc.department}</td>
                    <td className="p-4 text-gray-400">{pc.location}</td>
                    <td className={`p-4 text-center font-semibold ${pc.cpu_usage > 85 ? 'text-amber-400' : ''}`}>{pc.cpu_usage.toFixed(0)}%</td>
                    <td className={`p-4 text-center font-semibold ${pc.ram_usage > 85 ? 'text-amber-400' : ''}`}>{pc.ram_usage.toFixed(0)}%</td>
                    <td className={`p-4 text-center font-semibold ${pc.temperature > 75 ? 'text-red-400' : ''}`}>{pc.temperature.toFixed(0)}°C</td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${band.color}`}>
                        {health}% ({band.label})
                      </span>
                    </td>
                  </tr>
                );
              })}
              {filteredPcs.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-gray-500">No assets matching filters found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details Slide-out Drawer */}
      {selectedPc && (
        <div className="w-96 bg-[#0B0F19] border-l border-[#1F2937] p-6 flex flex-col space-y-6 overflow-y-auto relative animate-in slide-in-from-right duration-250">
          <button 
            onClick={() => setSelectedPc(null)}
            className="absolute top-6 right-6 p-1.5 hover:bg-[#111827] rounded text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>

          <div>
            <span className="text-[10px] bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded font-bold uppercase">Asset Detail</span>
            <h2 className="text-xl font-bold text-white mt-2">{selectedPc.pc_id}</h2>
            <p className="text-gray-400 text-xs mt-0.5">{selectedPc.model_name}</p>
          </div>

          <div className="border-t border-[#1F2937] pt-4 space-y-3 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Department:</span>
              <span className="text-white font-medium">{selectedPc.department}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Location:</span>
              <span className="text-white font-medium">{selectedPc.location}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Last Telemetry Check:</span>
              <span className="text-white font-medium">{new Date(selectedPc.last_updated).toLocaleTimeString()}</span>
            </div>
          </div>

          {/* Telemetry Chart */}
          <div className="border-t border-[#1F2937] pt-4 space-y-4">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Historical Telemetry Trends</h3>
            {telLoading ? (
              <div className="h-40 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
              </div>
            ) : telemetry.length > 0 ? (
              <div className="space-y-4">
                
                {/* Temp Chart */}
                <div className="space-y-1">
                  <p className="text-[10px] text-gray-500 uppercase">Temperature Trend (°C)</p>
                  <div className="h-28 bg-[#030712] border border-[#1F2937] p-2 rounded">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={telemetry}>
                        <XAxis dataKey="timestamp" hide />
                        <YAxis hide domain={['dataMin - 10', 'dataMax + 10']} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', color: '#fff', fontSize: '10px' }}
                          labelFormatter={(label) => new Date(label).toLocaleDateString()}
                        />
                        <Area type="monotone" dataKey="temperature" stroke="#EF4444" fill="rgba(239, 68, 68, 0.1)" strokeWidth={1.5} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Utilization Chart */}
                <div className="space-y-1">
                  <p className="text-[10px] text-gray-500 uppercase">CPU / RAM Load Trend (%)</p>
                  <div className="h-28 bg-[#030712] border border-[#1F2937] p-2 rounded">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={telemetry}>
                        <XAxis dataKey="timestamp" hide />
                        <YAxis hide domain={[0, 100]} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', color: '#fff', fontSize: '10px' }}
                          labelFormatter={(label) => new Date(label).toLocaleDateString()}
                        />
                        <Area type="monotone" dataKey="cpu_usage" stroke="#3B82F6" fill="rgba(59, 130, 246, 0.1)" strokeWidth={1.5} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

              </div>
            ) : (
              <p className="text-gray-500 text-center py-8 text-xs">No historical readings found.</p>
            )}
          </div>

        </div>
      )}

    </div>
  );
}
