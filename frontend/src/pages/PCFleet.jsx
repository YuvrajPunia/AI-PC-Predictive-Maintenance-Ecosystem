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

  // Register PC state
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [newPc, setNewPc] = useState({
    model_name: '',
    department: '',
    location: '',
    cpu_usage: '',
    ram_usage: '',
    temperature: '',
    voltage: '',
    disk_usage: '',
    fan_speed: ''
  });
  const [registerErrors, setRegisterErrors] = useState({});
  const [registerSuccess, setRegisterSuccess] = useState(null);
  const [registerError, setRegisterError] = useState(null);

  const refreshFleet = () => {
    api.getPcs()
      .then(res => setPcs(res))
      .catch(err => console.error("Failed to refresh: ", err));
  };

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

  const validateRegisterForm = () => {
    const errors = {};
    if (!newPc.model_name.trim()) errors.model_name = "Model name is required";
    if (!newPc.department.trim()) errors.department = "Department assignment is required";
    if (!newPc.location.trim()) errors.location = "Location is required";
    
    if (newPc.cpu_usage !== '') {
      const v = parseFloat(newPc.cpu_usage);
      if (isNaN(v) || v < 0 || v > 100) errors.cpu_usage = "CPU Usage must be 0 to 100%";
    }
    if (newPc.ram_usage !== '') {
      const v = parseFloat(newPc.ram_usage);
      if (isNaN(v) || v < 0 || v > 100) errors.ram_usage = "RAM Usage must be 0 to 100%";
    }
    if (newPc.disk_usage !== '') {
      const v = parseFloat(newPc.disk_usage);
      if (isNaN(v) || v < 0 || v > 100) errors.disk_usage = "Disk Usage must be 0 to 100%";
    }
    if (newPc.temperature !== '') {
      const v = parseFloat(newPc.temperature);
      if (isNaN(v) || v < -20 || v > 150) errors.temperature = "Temperature must be between -20°C and 150°C";
    }
    if (newPc.fan_speed !== '') {
      const v = parseFloat(newPc.fan_speed);
      if (isNaN(v) || v < 0) errors.fan_speed = "Fan Speed must be non-negative";
    }
    if (newPc.voltage !== '') {
      const v = parseFloat(newPc.voltage);
      if (isNaN(v) || v <= 0 || v > 30) errors.voltage = "Voltage must be positive and <= 30V";
    }
    
    setRegisterErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    if (!validateRegisterForm()) return;
    
    setRegisterSuccess(null);
    setRegisterError(null);
    
    const payload = {
      model_name: newPc.model_name.trim(),
      department: newPc.department.trim(),
      location: newPc.location.trim(),
      cpu_usage: newPc.cpu_usage !== '' ? parseFloat(newPc.cpu_usage) : null,
      ram_usage: newPc.ram_usage !== '' ? parseFloat(newPc.ram_usage) : null,
      temperature: newPc.temperature !== '' ? parseFloat(newPc.temperature) : null,
      voltage: newPc.voltage !== '' ? parseFloat(newPc.voltage) : null,
      disk_usage: newPc.disk_usage !== '' ? parseFloat(newPc.disk_usage) : null,
      fan_speed: newPc.fan_speed !== '' ? parseFloat(newPc.fan_speed) : null,
    };
    
    try {
      const registered = await api.registerPc(payload);
      setRegisterSuccess(`PC ${registered.pc_id} registered successfully!`);
      refreshFleet();
      
      setTimeout(() => {
        setNewPc({
          model_name: '',
          department: '',
          location: '',
          cpu_usage: '',
          ram_usage: '',
          temperature: '',
          voltage: '',
          disk_usage: '',
          fan_speed: ''
        });
        setRegisterSuccess(null);
        setShowRegisterModal(false);
      }, 1500);
    } catch (err) {
      setRegisterError(err.message || "Failed to register PC");
    }
  };

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

  const formatSensorValue = (value, decimals = 1, unit = '') => {
    return typeof value === "number" && Number.isFinite(value)
      ? `${value.toFixed(decimals)}${unit}`
      : "N/A";
  };

  // Helper: Simple frontend health calculation to display list scores
  const estimateHealth = (pc) => {
    if (
      pc.cpu_usage === null || pc.cpu_usage === undefined ||
      pc.ram_usage === null || pc.ram_usage === undefined ||
      pc.temperature === null || pc.temperature === undefined ||
      pc.voltage === null || pc.voltage === undefined
    ) {
      return null;
    }
    let score = 100;
    if (pc.temperature > 75) score -= (pc.temperature - 75) * 1.5;
    if (pc.voltage < 12) score -= (12 - pc.voltage) * 8;
    if (pc.voltage > 18) score -= (pc.voltage - 18) * 8;
    if (pc.cpu_usage > 85 && pc.ram_usage > 85) score -= 15;
    return Math.max(0, Math.min(100, Math.round(score)));
  };

  const getHealthBand = (score) => {
    if (score === null || score === undefined) {
      return { label: 'N/A', color: 'text-gray-400 bg-gray-500/10' };
    }
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
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">DRDO Fleet PC Registry</h1>
            <p className="text-gray-400 text-sm">Review asset configuration, department allocation, and real-time sensor metrics.</p>
          </div>
          <button
            onClick={() => setShowRegisterModal(true)}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors"
          >
            <Monitor className="w-4 h-4" />
            <span>+ Add New PC</span>
          </button>
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
                    <td className={`p-4 text-center font-semibold ${pc.cpu_usage > 85 ? 'text-amber-400' : ''}`}>{formatSensorValue(pc.cpu_usage, 0, '%')}</td>
                    <td className={`p-4 text-center font-semibold ${pc.ram_usage > 85 ? 'text-amber-400' : ''}`}>{formatSensorValue(pc.ram_usage, 0, '%')}</td>
                    <td className={`p-4 text-center font-semibold ${pc.temperature > 75 ? 'text-red-400' : ''}`}>{formatSensorValue(pc.temperature, 0, '°C')}</td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${band.color}`}>
                        {health !== null ? `${health}%` : 'N/A'} ({band.label})
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

      {/* Register PC Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#0B0F19] border border-[#1F2937] w-full max-w-lg rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-[#1F2937] flex justify-between items-center bg-[#0d1321]">
              <h2 className="text-sm font-bold text-white">Register New Organization PC</h2>
              <button 
                onClick={() => setShowRegisterModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRegisterSubmit} className="p-5 overflow-y-auto space-y-4 text-xs">
              
              {registerSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold rounded">
                  {registerSuccess}
                </div>
              )}
              {registerError && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 font-bold rounded">
                  {registerError}
                </div>
              )}

              {/* Required Details */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-cyan-400 border-b border-[#1F2937] pb-1 uppercase tracking-wider">Required Asset Information</h3>
                
                <div className="space-y-1">
                  <label className="text-gray-400 font-semibold block">Hardware Model Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Dell Latitude 7440"
                    className="w-full bg-[#030712] border border-[#1F2937] p-2 rounded text-white focus:outline-none focus:border-cyan-500"
                    value={newPc.model_name}
                    onChange={(e) => setNewPc({...newPc, model_name: e.target.value})}
                  />
                  {registerErrors.model_name && <p className="text-[10px] text-red-400">{registerErrors.model_name}</p>}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-gray-400 font-semibold block">Department *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Avionics Division"
                      className="w-full bg-[#030712] border border-[#1F2937] p-2 rounded text-white focus:outline-none focus:border-cyan-500"
                      value={newPc.department}
                      onChange={(e) => setNewPc({...newPc, department: e.target.value})}
                    />
                    {registerErrors.department && <p className="text-[10px] text-red-400">{registerErrors.department}</p>}
                  </div>
                  <div className="space-y-1">
                    <label className="text-gray-400 font-semibold block">Physical Location *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Lab 4B, Sector 3"
                      className="w-full bg-[#030712] border border-[#1F2937] p-2 rounded text-white focus:outline-none focus:border-cyan-500"
                      value={newPc.location}
                      onChange={(e) => setNewPc({...newPc, location: e.target.value})}
                    />
                    {registerErrors.location && <p className="text-[10px] text-red-400">{registerErrors.location}</p>}
                  </div>
                </div>
              </div>

              {/* Optional Initial Sensors */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold text-cyan-400 border-b border-[#1F2937] pb-1 uppercase tracking-wider">Initial Telemetry (Optional)</h3>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-gray-400 block">Temperature (°C)</label>
                    <input
                      type="number"
                      step="any"
                      placeholder="-20 to 150"
                      className={`w-full bg-[#030712] border p-2 rounded text-white focus:outline-none focus:border-cyan-500 ${registerErrors.temperature ? 'border-red-500/50' : 'border-[#1F2937]'}`}
                      value={newPc.temperature}
                      onChange={(e) => setNewPc({...newPc, temperature: e.target.value})}
                    />
                    {registerErrors.temperature && <p className="text-[10px] text-red-400">{registerErrors.temperature}</p>}
                  </div>
                  <div className="space-y-1">
                    <label className="text-gray-400 block">Fan Speed (RPM)</label>
                    <input
                      type="number"
                      step="any"
                      placeholder="e.g. 3000"
                      className={`w-full bg-[#030712] border p-2 rounded text-white focus:outline-none focus:border-cyan-500 ${registerErrors.fan_speed ? 'border-red-500/50' : 'border-[#1F2937]'}`}
                      value={newPc.fan_speed}
                      onChange={(e) => setNewPc({...newPc, fan_speed: e.target.value})}
                    />
                    {registerErrors.fan_speed && <p className="text-[10px] text-red-400">{registerErrors.fan_speed}</p>}
                  </div>

                  <div className="space-y-1">
                    <label className="text-gray-400 block">CPU Usage (%)</label>
                    <input
                      type="number"
                      step="any"
                      placeholder="0 - 100"
                      className={`w-full bg-[#030712] border p-2 rounded text-white focus:outline-none focus:border-cyan-500 ${registerErrors.cpu_usage ? 'border-red-500/50' : 'border-[#1F2937]'}`}
                      value={newPc.cpu_usage}
                      onChange={(e) => setNewPc({...newPc, cpu_usage: e.target.value})}
                    />
                    {registerErrors.cpu_usage && <p className="text-[10px] text-red-400">{registerErrors.cpu_usage}</p>}
                  </div>
                  <div className="space-y-1">
                    <label className="text-gray-400 block">RAM Usage (%)</label>
                    <input
                      type="number"
                      step="any"
                      placeholder="0 - 100"
                      className={`w-full bg-[#030712] border p-2 rounded text-white focus:outline-none focus:border-cyan-500 ${registerErrors.ram_usage ? 'border-red-500/50' : 'border-[#1F2937]'}`}
                      value={newPc.ram_usage}
                      onChange={(e) => setNewPc({...newPc, ram_usage: e.target.value})}
                    />
                    {registerErrors.ram_usage && <p className="text-[10px] text-red-400">{registerErrors.ram_usage}</p>}
                  </div>

                  <div className="space-y-1">
                    <label className="text-gray-400 block">Voltage (V)</label>
                    <input
                      type="number"
                      step="any"
                      placeholder="0 to 30V"
                      className={`w-full bg-[#030712] border p-2 rounded text-white focus:outline-none focus:border-cyan-500 ${registerErrors.voltage ? 'border-red-500/50' : 'border-[#1F2937]'}`}
                      value={newPc.voltage}
                      onChange={(e) => setNewPc({...newPc, voltage: e.target.value})}
                    />
                    {registerErrors.voltage && <p className="text-[10px] text-red-400">{registerErrors.voltage}</p>}
                  </div>
                  <div className="space-y-1">
                    <label className="text-gray-400 block">Disk Usage (%)</label>
                    <input
                      type="number"
                      step="any"
                      placeholder="0 - 100"
                      className={`w-full bg-[#030712] border p-2 rounded text-white focus:outline-none focus:border-cyan-500 ${registerErrors.disk_usage ? 'border-red-500/50' : 'border-[#1F2937]'}`}
                      value={newPc.disk_usage}
                      onChange={(e) => setNewPc({...newPc, disk_usage: e.target.value})}
                    />
                    {registerErrors.disk_usage && <p className="text-[10px] text-red-400">{registerErrors.disk_usage}</p>}
                  </div>
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="pt-4 flex space-x-3">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="flex-1 py-2 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 font-semibold text-center transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-center transition-colors"
                >
                  Register PC
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}
