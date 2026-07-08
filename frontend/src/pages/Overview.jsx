import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, AreaChart, Area 
} from 'recharts';
import { 
  Monitor, AlertTriangle, Activity, PenTool, 
  ShieldAlert, Clock, CheckCircle2 
} from 'lucide-react';

export default function Overview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getDashboardOverview()
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center h-full space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
        <p className="text-gray-400 text-sm">Loading Fleet Analytics Overview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-6 flex flex-col justify-center items-center h-full text-center">
        <AlertTriangle className="text-red-500 w-16 h-16 mb-4 animate-bounce" />
        <h3 className="text-xl font-bold text-white mb-2">Failed to Load Dashboard Data</h3>
        <p className="text-gray-400 max-w-md">{error}</p>
      </div>
    );
  }

  const { stats, risk_distribution, problem_distribution, department_distribution } = data;

  // Chart Data preparation
  const riskChartData = [
    { name: 'Low', value: risk_distribution.low, color: '#10B981' },     // Green
    { name: 'Medium', value: risk_distribution.medium, color: '#3B82F6' }, // Blue
    { name: 'High', value: risk_distribution.high, color: '#F59E0B' },     // Amber
    { name: 'Critical', value: risk_distribution.critical, color: '#EF4444' } // Red
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">DRDO Fleet Executive Overview</h1>
        <p className="text-gray-400 text-sm">Real-time status of organization PC assets and intelligence database.</p>
      </div>

      {/* Aggregate Metric Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg flex items-center space-x-4">
          <div className="p-3 bg-blue-500/10 rounded-lg text-blue-500">
            <Monitor className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Total PC Assets</p>
            <h3 className="text-2xl font-bold text-white mt-1">{stats.total_pcs}</h3>
          </div>
        </div>

        <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg flex items-center space-x-4">
          <div className="p-3 bg-emerald-500/10 rounded-lg text-emerald-500">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Average Health</p>
            <h3 className="text-2xl font-bold text-white mt-1">{stats.average_health_score}%</h3>
          </div>
        </div>

        <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg flex items-center space-x-4">
          <div className="p-3 bg-amber-500/10 rounded-lg text-amber-500">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">High Risk / Anomalies</p>
            <h3 className="text-2xl font-bold text-white mt-1">
              {stats.high_risk_pcs} <span className="text-xs font-normal text-gray-500">/ {stats.abnormal_pcs} abnormal</span>
            </h3>
          </div>
        </div>

        <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg flex items-center space-x-4">
          <div className="p-3 bg-purple-500/10 rounded-lg text-purple-500">
            <PenTool className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Repairs Saved (Total / Month)</p>
            <h3 className="text-2xl font-bold text-white mt-1">
              {stats.historical_repairs} <span className="text-xs font-normal text-gray-500">/ +{stats.repairs_added_this_month}</span>
            </h3>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Risk Distribution Chart */}
        <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg lg:col-span-1">
          <h3 className="text-sm font-semibold text-white mb-4">PC Risk Profile Distribution</h3>
          <div className="h-64 flex flex-col justify-center items-center relative">
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie
                  data={riskChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {riskChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', color: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
            
            {/* Legend */}
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 mt-2 text-xs">
              {riskChartData.map((r, i) => (
                <div key={i} className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: r.color }}></span>
                  <span className="text-gray-400">{r.name}: <b>{r.value}</b></span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Problem Category bar chart */}
        <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg lg:col-span-2">
          <h3 className="text-sm font-semibold text-white mb-4">Historical Repairs by Problem Category</h3>
          <div className="h-64">
            {problem_distribution.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">No historical repairs recorded.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={problem_distribution}>
                  <XAxis dataKey="category" stroke="#9CA3AF" fontSize={11} tickLine={false} />
                  <YAxis stroke="#9CA3AF" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', color: '#fff' }}
                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  />
                  <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]}>
                    {problem_distribution.map((entry, index) => {
                      const colors = {
                        'Overheating': '#F59E0B',
                        'Memory Leak': '#A78BFA',
                        'Disk Failure': '#EF4444',
                        'Power Issue': '#3B82F6',
                        'No Problem': '#10B981'
                      };
                      return <Cell key={`cell-${index}`} fill={colors[entry.category] || '#6B7280'} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>

      {/* Repairs by department */}
      <div className="bg-[#0B0F19] border border-[#1F2937] p-5 rounded-lg">
        <h3 className="text-sm font-semibold text-white mb-4">Repair Incidents by Department</h3>
        <div className="h-64">
          {department_distribution.length === 0 ? (
            <div className="h-full flex items-center justify-center text-gray-500 text-sm">No data available.</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={department_distribution} layout="vertical">
                <XAxis type="number" stroke="#9CA3AF" fontSize={11} tickLine={false} />
                <YAxis dataKey="department" type="category" stroke="#9CA3AF" fontSize={11} tickLine={false} width={150} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', color: '#fff' }}
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                />
                <Bar dataKey="count" fill="#8B5CF6" radius={[0, 4, 4, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
