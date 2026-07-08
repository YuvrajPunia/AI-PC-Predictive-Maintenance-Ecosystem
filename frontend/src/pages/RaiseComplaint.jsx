import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { 
  Search, Cpu, HardDrive, Thermometer, Zap, Fan, 
  Activity, AlertCircle, RefreshCw, Send, CheckCircle, ChevronDown, ChevronUp, Info 
} from 'lucide-react';

export default function RaiseComplaint({ onSendToRepair }) {
  const [pcs, setPcs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPcId, setSelectedPcId] = useState('');
  const [selectedPc, setSelectedPc] = useState(null);
  
  const [complaint, setComplaint] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [error, setError] = useState(null);
  
  const [expandedRepairId, setExpandedRepairId] = useState(null);

  const loadingStages = [
    "Understanding complaint text...",
    "Analyzing telemetry data & extracting features...",
    "Running multi-model predictive classifiers...",
    "Querying semantic knowledge base for similar repairs...",
    "Calculating operational risk index & RUL...",
    "Synthesizing evidence-based maintenance recommendation..."
  ];

  // Fetch PC list on mount
  useEffect(() => {
    api.getPcs()
      .then(res => setPcs(res))
      .catch(err => console.error("Failed to load PCs: ", err));
  }, []);

  // Fetch selected PC details
  const handlePcSelect = (pcId) => {
    setSelectedPcId(pcId);
    if (!pcId) {
      setSelectedPc(null);
      return;
    }
    api.getPcById(pcId)
      .then(res => {
        setSelectedPc(res);
        setAnalysisResult(null); // Clear previous analysis
        setError(null);
      })
      .catch(err => {
        setError("Failed to load PC metrics: " + err.message);
      });
  };

  const handleAnalyze = async () => {
    if (!selectedPcId) {
      setError("Please select a PC asset first.");
      return;
    }
    if (!complaint.trim()) {
      setError("Please input the user complaint describing the problem.");
      return;
    }

    setLoading(true);
    setAnalysisResult(null);
    setError(null);

    // Simulate loading stages progression for visual polish
    let stage = 0;
    setLoadingStage(0);
    const interval = setInterval(() => {
      stage += 1;
      if (stage < loadingStages.length) {
        setLoadingStage(stage);
      }
    }, 900);

    try {
      const result = await api.analyzeComplaint(selectedPcId, complaint);
      clearInterval(interval);
      setAnalysisResult(result);
      setLoading(false);
    } catch (err) {
      clearInterval(interval);
      setError(err.message);
      setLoading(false);
    }
  };

  const filteredPcs = pcs.filter(pc => 
    pc.pc_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    pc.department.toLowerCase().includes(searchQuery.toLowerCase()) ||
    pc.model_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectSymptomTag = (tag) => {
    if (!complaint.includes(tag)) {
      setComplaint(prev => prev ? `${prev} Experiencing ${tag.toLowerCase()}.` : `Experiencing ${tag.toLowerCase()}.`);
    }
  };

  // Helper colors for health
  const getHealthColor = (band) => {
    if (band === 'Healthy') return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
    if (band === 'Moderate') return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
    if (band === 'Poor') return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
    return 'text-red-500 bg-red-500/10 border-red-500/20';
  };

  const getRiskColor = (level) => {
    if (level === 'Low') return 'text-emerald-400 border-emerald-500/30';
    if (level === 'Medium') return 'text-blue-400 border-blue-500/30';
    if (level === 'High') return 'text-amber-400 border-amber-500/30';
    return 'text-red-400 border-red-500/30 animate-pulse';
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Raise PC Complaint & AI Diagnostics</h1>
        <p className="text-gray-400 text-sm">Analyze sensor telemetry and query historical completed repairs dynamically.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Panel: Select & Input */}
        <div className="xl:col-span-1 space-y-6">
          
          {/* PC Selector Card */}
          <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white">1. Select Organization PC</h2>
            
            <div className="relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search ID, department, or model..."
                className="w-full bg-[#030712] border border-[#1F2937] pl-9 pr-4 py-2 rounded text-sm text-white focus:outline-none focus:border-cyan-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            <div className="max-h-40 overflow-y-auto border border-[#1F2937] rounded divide-y divide-[#1F2937]">
              {filteredPcs.map(pc => (
                <button
                  key={pc.pc_id}
                  onClick={() => handlePcSelect(pc.pc_id)}
                  className={`w-full text-left px-3 py-2 text-xs flex justify-between items-center transition-colors ${
                    selectedPcId === pc.pc_id ? 'bg-cyan-500/10 text-cyan-400' : 'hover:bg-[#111827] text-gray-300'
                  }`}
                >
                  <span className="font-semibold">{pc.pc_id}</span>
                  <span className="text-gray-500">{pc.model_name.split(' ').slice(0,2).join(' ')}</span>
                </button>
              ))}
              {filteredPcs.length === 0 && (
                <p className="p-3 text-center text-gray-500 text-xs">No matching PCs found.</p>
              )}
            </div>

            {selectedPc && (
              <div className="p-3.5 bg-[#111827] border border-[#1F2937] rounded space-y-1 text-xs">
                <p className="text-gray-400">Model: <b className="text-white">{selectedPc.model_name}</b></p>
                <p className="text-gray-400">Department: <b className="text-white">{selectedPc.department}</b></p>
                <p className="text-gray-400">Location: <b className="text-white">{selectedPc.location}</b></p>
                <p className="text-gray-500 text-[10px] mt-2">Last Updated: {new Date(selectedPc.last_updated).toLocaleString()}</p>
              </div>
            )}
          </div>

          {/* User Complaint Input */}
          <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white">2. User Complaint details</h2>
            
            <textarea
              rows={4}
              placeholder="Describe the issue... (e.g. My laptop becomes extremely hot and shuts down automatically after 20 minutes.)"
              className="w-full bg-[#030712] border border-[#1F2937] p-3 rounded text-sm text-white focus:outline-none focus:border-cyan-500 placeholder-gray-600"
              value={complaint}
              onChange={(e) => setComplaint(e.target.value)}
            />

            <div>
              <p className="text-xs text-gray-400 mb-2">Common Symptom Tags:</p>
              <div className="flex flex-wrap gap-1.5">
                {["Overheating", "Memory Leak", "Disk Failure", "Power Issue", "Unstable Charging"].map(tag => (
                  <button
                    key={tag}
                    onClick={() => selectSymptomTag(tag)}
                    className="px-2 py-1 bg-[#111827] border border-[#1F2937] hover:border-gray-500 text-[10px] text-gray-300 rounded"
                  >
                    +{tag}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={loading || !selectedPcId}
              className={`w-full py-2.5 rounded font-medium text-sm flex items-center justify-center space-x-2 transition-colors ${
                loading || !selectedPcId
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white font-semibold'
              }`}
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Analyzing with AI...</span>
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4" />
                  <span>Analyze with AI</span>
                </>
              )}
            </button>
          </div>

        </div>

        {/* Middle/Right Panel: Telemetry & AI Diagnostic Results */}
        <div className="xl:col-span-2 space-y-6">
          
          {/* Telemetry Sensor Readings Panel */}
          {selectedPc && (
            <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-4">
              <h2 className="text-sm font-semibold text-white">Current Asset Sensor Snapshot</h2>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                
                {/* Temp */}
                <div className={`p-3 rounded border bg-[#030712] ${selectedPc.temperature > 75.0 ? 'border-amber-500/30 text-amber-500' : 'border-[#1F2937] text-gray-300'}`}>
                  <div className="flex items-center space-x-1.5 text-xs text-gray-400">
                    <Thermometer className="w-4 h-4" />
                    <span>Temp</span>
                  </div>
                  <p className="text-lg font-bold mt-1 text-white">{selectedPc.temperature.toFixed(1)}°C</p>
                  <div className="w-full bg-[#111827] h-1 rounded mt-2 overflow-hidden">
                    <div 
                      className={`h-full ${selectedPc.temperature > 75.0 ? 'bg-amber-500' : 'bg-cyan-500'}`} 
                      style={{ width: `${Math.min(100, (selectedPc.temperature / 110) * 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* Fan Speed */}
                <div className={`p-3 rounded border bg-[#030712] ${selectedPc.temperature > 75.0 && selectedPc.fan_speed < 2000.0 ? 'border-red-500/30 text-red-500' : 'border-[#1F2937] text-gray-300'}`}>
                  <div className="flex items-center space-x-1.5 text-xs text-gray-400">
                    <Fan className="w-4 h-4" />
                    <span>Fan Speed</span>
                  </div>
                  <p className="text-lg font-bold mt-1 text-white">{selectedPc.fan_speed.toFixed(0)} RPM</p>
                  <div className="w-full bg-[#111827] h-1 rounded mt-2 overflow-hidden">
                    <div 
                      className={`h-full ${selectedPc.fan_speed < 2000.0 && selectedPc.temperature > 75.0 ? 'bg-red-500' : 'bg-cyan-500'}`} 
                      style={{ width: `${Math.min(100, (selectedPc.fan_speed / 6000) * 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* CPU */}
                <div className={`p-3 rounded border bg-[#030712] ${selectedPc.cpu_usage > 85.0 ? 'border-amber-500/30 text-amber-500' : 'border-[#1F2937] text-gray-300'}`}>
                  <div className="flex items-center space-x-1.5 text-xs text-gray-400">
                    <Cpu className="w-4 h-4" />
                    <span>CPU Load</span>
                  </div>
                  <p className="text-lg font-bold mt-1 text-white">{selectedPc.cpu_usage.toFixed(1)}%</p>
                  <div className="w-full bg-[#111827] h-1 rounded mt-2 overflow-hidden">
                    <div 
                      className="bg-cyan-500 h-full" 
                      style={{ width: `${selectedPc.cpu_usage}%` }}
                    ></div>
                  </div>
                </div>

                {/* RAM */}
                <div className={`p-3 rounded border bg-[#030712] ${selectedPc.ram_usage > 85.0 ? 'border-amber-500/30 text-amber-500' : 'border-[#1F2937] text-gray-300'}`}>
                  <div className="flex items-center space-x-1.5 text-xs text-gray-400">
                    <Activity className="w-4 h-4" />
                    <span>RAM Load</span>
                  </div>
                  <p className="text-lg font-bold mt-1 text-white">{selectedPc.ram_usage.toFixed(1)}%</p>
                  <div className="w-full bg-[#111827] h-1 rounded mt-2 overflow-hidden">
                    <div 
                      className="bg-cyan-500 h-full" 
                      style={{ width: `${selectedPc.ram_usage}%` }}
                    ></div>
                  </div>
                </div>

                {/* Voltage */}
                <div className={`p-3 rounded border bg-[#030712] ${Math.abs(selectedPc.voltage - 15.0) > 3.0 ? 'border-red-500/30 text-red-500' : 'border-[#1F2937] text-gray-300'}`}>
                  <div className="flex items-center space-x-1.5 text-xs text-gray-400">
                    <Zap className="w-4 h-4" />
                    <span>Voltage</span>
                  </div>
                  <p className="text-lg font-bold mt-1 text-white">{selectedPc.voltage.toFixed(2)}V</p>
                  <div className="w-full bg-[#111827] h-1 rounded mt-2 overflow-hidden">
                    <div 
                      className={`h-full ${Math.abs(selectedPc.voltage - 15.0) > 3.0 ? 'bg-red-500' : 'bg-cyan-500'}`} 
                      style={{ width: `${Math.min(100, (selectedPc.voltage / 24) * 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* Disk */}
                <div className={`p-3 rounded border bg-[#030712] ${selectedPc.disk_usage > 90.0 ? 'border-amber-500/30 text-amber-500' : 'border-[#1F2937] text-gray-300'}`}>
                  <div className="flex items-center space-x-1.5 text-xs text-gray-400">
                    <HardDrive className="w-4 h-4" />
                    <span>Disk Space</span>
                  </div>
                  <p className="text-lg font-bold mt-1 text-white">{selectedPc.disk_usage.toFixed(1)}%</p>
                  <div className="w-full bg-[#111827] h-1 rounded mt-2 overflow-hidden">
                    <div 
                      className="bg-cyan-500 h-full" 
                      style={{ width: `${selectedPc.disk_usage}%` }}
                    ></div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* Loading Skeletons */}
          {loading && (
            <div className="bg-[#0B0F19] border border-[#1F2937] p-8 rounded-lg space-y-6 flex flex-col justify-center items-center">
              <div className="relative flex items-center justify-center">
                <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-cyan-500"></div>
                <Activity className="w-6 h-6 text-cyan-500 absolute animate-pulse" />
              </div>
              <div className="text-center space-y-1 max-w-sm">
                <h3 className="font-bold text-white text-sm">Processing Diagnostics</h3>
                <p className="text-cyan-400 text-xs font-semibold animate-pulse">{loadingStages[loadingStage]}</p>
                <div className="w-48 bg-[#111827] h-1.5 rounded-full mt-3 overflow-hidden mx-auto">
                  <div 
                    className="bg-cyan-500 h-full transition-all duration-300"
                    style={{ width: `${((loadingStage + 1) / loadingStages.length) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          {/* AI Diagnostic Output */}
          {analysisResult && (
            <div className="space-y-6">
              
              {/* Health Grid */}
              <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-4">
                <h3 className="text-sm font-semibold text-white">AI Health Assessment</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  
                  {/* Fused Classifier Target */}
                  <div className="p-3 bg-[#030712] border border-[#1F2937] rounded">
                    <p className="text-[10px] text-gray-500 uppercase font-medium">Likely Problem (Fused)</p>
                    <h4 className="text-base font-bold text-white mt-1">
                      {analysisResult.problem_analysis.final_assessment}
                    </h4>
                    <p className="text-[10px] text-gray-400 mt-0.5">
                      Agreement: <b className="text-cyan-400">{analysisResult.problem_analysis.agreement_status}</b>
                    </p>
                  </div>

                  {/* Health Score */}
                  <div className="p-3 bg-[#030712] border border-[#1F2937] rounded">
                    <p className="text-[10px] text-gray-500 uppercase font-medium">Health Score (Surrogate)</p>
                    <div className="flex items-baseline space-x-2 mt-1">
                      <span className="text-xl font-bold text-white">{analysisResult.predictive_health.health_score}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${getHealthColor(analysisResult.predictive_health.health_band)}`}>
                        {analysisResult.predictive_health.health_band}
                      </span>
                    </div>
                  </div>

                  {/* Anomaly Isolation Forest */}
                  <div className="p-3 bg-[#030712] border border-[#1F2937] rounded">
                    <p className="text-[10px] text-gray-500 uppercase font-medium">Anomaly (Isolation Forest)</p>
                    <h4 className={`text-base font-bold mt-1 ${
                      analysisResult.anomaly.label === 'Abnormal' ? 'text-red-400' : 'text-emerald-400'
                    }`}>
                      {analysisResult.anomaly.label}
                    </h4>
                    <p className="text-[10px] text-gray-500">Score: {analysisResult.anomaly.score.toFixed(3)}</p>
                  </div>

                  {/* Operational Risk Index */}
                  <div className={`p-3 bg-[#030712] border rounded border-l-4 ${getRiskColor(analysisResult.predictive_health.risk_level)}`}>
                    <p className="text-[10px] text-gray-500 uppercase font-medium">Operational Risk Index</p>
                    <h4 className="text-xl font-bold text-white mt-1">
                      {analysisResult.predictive_health.risk_index}
                    </h4>
                    <p className="text-[10px] text-gray-400">Risk: <b>{analysisResult.predictive_health.risk_level}</b></p>
                  </div>

                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  
                  {/* Failure Probability */}
                  <div className="p-3 bg-[#030712] border border-[#1F2937] rounded flex justify-between items-center">
                    <div>
                      <p className="text-[10px] text-gray-500 uppercase font-medium">Near-Term Failure Risk</p>
                      <h4 className="text-lg font-bold text-white mt-1">
                        {analysisResult.predictive_health.near_term_failure_risk}%
                      </h4>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-1 rounded text-[10px] font-bold ${
                        analysisResult.predictive_health.will_fail_soon ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-500'
                      }`}>
                        {analysisResult.predictive_health.will_fail_soon ? 'WILL FAIL SOON' : 'STABLE'}
                      </span>
                    </div>
                  </div>

                  {/* RUL prediction */}
                  <div className="p-3 bg-[#030712] border border-[#1F2937] rounded">
                    <p className="text-[10px] text-gray-500 uppercase font-medium">Remaining Useful Life (RUL)</p>
                    <h4 className="text-lg font-bold text-cyan-400 mt-1">
                      {analysisResult.predictive_health.remaining_useful_life_days} Days
                    </h4>
                    <p className="text-[9px] text-gray-500 mt-0.5">Surrogate model approximation based on degradation curves.</p>
                  </div>

                </div>
              </div>

              {/* Local Explainability (SHAP Fallback) */}
              <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-4">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-semibold text-white">Why the AI reached this assessment</h3>
                  <span className="text-[9px] bg-[#111827] text-gray-400 px-1.5 py-0.5 rounded border border-[#1F2937]">Local Feature Attributions</span>
                </div>
                
                <div className="space-y-2.5">
                  {analysisResult.explainability.top_contributing_features.map((feat, idx) => (
                    <div key={idx} className="flex justify-between items-center text-xs">
                      <span className="text-gray-400 font-medium">{feat.feature}</span>
                      <div className="flex items-center space-x-4">
                        <span className="text-white font-semibold">{feat.value.toFixed(1)}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          feat.direction === 'Positive' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                        }`}>
                          {feat.direction === 'Positive' ? 'Favorable (+)' : 'Unfavorable (-)'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top 3 Similar Historical Cases */}
              <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg space-y-4">
                <h3 className="text-sm font-semibold text-white">Top 3 Similar Historical Cases (Semantic retrieval index)</h3>
                
                <div className="space-y-3">
                  {analysisResult.similar_cases.map((caseItem, idx) => (
                    <div key={caseItem.repair_id} className="bg-[#030712] border border-[#1F2937] rounded overflow-hidden">
                      <button
                        onClick={() => setExpandedRepairId(expandedRepairId === caseItem.repair_id ? null : caseItem.repair_id)}
                        className="w-full px-4 py-3 flex justify-between items-center text-left hover:bg-[#111827]"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-bold text-cyan-400">{caseItem.rank}. {caseItem.repair_id}</span>
                          <span className="text-[10px] text-gray-500">PC: {caseItem.pc_id}</span>
                          <span className="text-[10px] text-gray-400 font-semibold">{caseItem.problem}</span>
                        </div>
                        <div className="flex items-center space-x-3">
                          <span className="text-xs bg-cyan-950 text-cyan-400 px-2 py-0.5 rounded-full font-bold">
                            {caseItem.similarity_score}% Match
                          </span>
                          {expandedRepairId === caseItem.repair_id ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                        </div>
                      </button>

                      {expandedRepairId === caseItem.repair_id && (
                        <div className="px-4 pb-4 border-t border-[#1F2937] pt-3 text-xs space-y-3">
                          <div>
                            <p className="text-gray-500 font-semibold">Previous Complaint:</p>
                            <p className="text-gray-300 italic">"{caseItem.historical_complaint}"</p>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                              <p className="text-gray-500 font-semibold">Diagnosis:</p>
                              <p className="text-white">{caseItem.confirmed_diagnosis}</p>
                            </div>
                            <div>
                              <p className="text-gray-500 font-semibold">Root Cause:</p>
                              <p className="text-white">{caseItem.root_cause}</p>
                            </div>
                          </div>
                          <div>
                            <p className="text-gray-500 font-semibold">Treatment Taken:</p>
                            <p className="text-white">{caseItem.treatment_taken}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 font-semibold">Technician Notes:</p>
                            <p className="text-white">{caseItem.technician_notes || 'None'}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 font-semibold">Why Matched:</p>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {caseItem.why_matched.map((reason, rIdx) => (
                                <span key={rIdx} className="px-2 py-0.5 bg-gray-800 text-gray-400 text-[10px] rounded">
                                  {reason}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                  {analysisResult.similar_cases.length === 0 && (
                    <p className="p-4 text-center text-gray-500 text-xs">No historical matching cases found in index.</p>
                  )}
                </div>
              </div>

              {/* AI Maintenance Recommendation Panel */}
              <div className="bg-[#0B0F19] border border-cyan-500/20 p-5 rounded-lg space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-semibold text-white">AI Maintenance Recommendation</h3>
                  <span className="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded font-bold uppercase tracking-wider">Decision Support</span>
                </div>
                
                <div className="space-y-4 text-xs">
                  <div>
                    <p className="text-gray-400 font-semibold">Primary Recommendation:</p>
                    <p className="text-white font-medium mt-0.5">{analysisResult.recommendation.primary_recommendation}</p>
                  </div>

                  <div>
                    <p className="text-gray-400 font-semibold mb-1.5">Recommended Diagnostic Sequence:</p>
                    <ol className="list-decimal list-inside space-y-1 text-gray-300">
                      {analysisResult.recommendation.diagnostic_sequence.map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ol>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-gray-400 font-semibold">Immediate Actions:</p>
                      <ul className="list-disc list-inside space-y-1 text-gray-300 mt-1">
                        {analysisResult.recommendation.immediate_actions.map((act, idx) => (
                          <li key={idx}>{act}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-gray-400 font-semibold">Preventive Actions:</p>
                      <ul className="list-disc list-inside space-y-1 text-gray-300 mt-1">
                        {analysisResult.recommendation.preventive_actions.map((act, idx) => (
                          <li key={idx}>{act}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="p-3 bg-[#030712] border border-[#1F2937] rounded-lg">
                    <p className="text-[10px] text-gray-500 font-semibold uppercase">Disclaimer</p>
                    <p className="text-[10px] text-gray-400 mt-0.5 leading-normal">
                      AI-generated decision support based on current telemetry and historical repair evidence. Final diagnosis should be confirmed by qualified technical personnel.
                    </p>
                  </div>
                </div>

                <div className="border-t border-[#1F2937] pt-4 flex justify-end">
                  <button
                    onClick={() => onSendToRepair({
                      pc_id: selectedPcId,
                      original_complaint: complaint,
                      symptoms: analysisResult.similar_cases[0]?.symptoms || complaint,
                      problem_detected: analysisResult.problem_analysis.final_assessment,
                      analysis: analysisResult
                    })}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded flex items-center space-x-2 transition-colors"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Send to Repair Resolution</span>
                  </button>
                </div>
              </div>

            </div>
          )}

          {!selectedPc && (
            <div className="h-64 border border-dashed border-[#1F2937] rounded-lg flex flex-col justify-center items-center text-center p-6 text-gray-500">
              <Monitor className="w-12 h-12 mb-3 text-gray-600" />
              <p className="text-sm">Please select a PC from the left panel to begin diagnostic analysis.</p>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
