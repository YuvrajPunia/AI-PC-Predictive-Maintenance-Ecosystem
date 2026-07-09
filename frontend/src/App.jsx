import React, { useState } from 'react';
import Overview from './pages/Overview';
import RaiseComplaint from './pages/RaiseComplaint';
import RepairResolution from './pages/RepairResolution';
import PCFleet from './pages/PCFleet';
import RepairHistory from './pages/RepairHistory';
import ErrorBoundary from './components/ErrorBoundary';
import { 
  Shield, LayoutDashboard, AlertCircle, PenTool, 
  Layers, History, Settings 
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [activeCase, setActiveCase] = useState(null);
  
  // Trigger to update lists on repair submission
  const [updateTrigger, setUpdateTrigger] = useState(0);

  const handleSendToRepair = (caseData) => {
    setActiveCase(caseData);
    setActiveTab('RepairResolution');
  };

  const handleRepairCompleted = () => {
    // Clear active case
    setActiveCase(null);
    // Refresh history
    setUpdateTrigger(prev => prev + 1);
  };

  const tabs = [
    { id: 'Overview', label: 'Overview', icon: LayoutDashboard, component: <Overview /> },
    { 
      id: 'RaiseComplaint', 
      label: 'Raise Complaint', 
      icon: AlertCircle, 
      component: <RaiseComplaint onSendToRepair={handleSendToRepair} /> 
    },
    { 
      id: 'RepairResolution', 
      label: 'Repair Resolution', 
      icon: PenTool, 
      component: <RepairResolution activeCase={activeCase} onRepairCompleted={handleRepairCompleted} /> 
    },
    { id: 'PCFleet', label: 'PC Fleet', icon: Layers, component: <PCFleet /> },
    { 
      id: 'RepairHistory', 
      label: 'Repair History', 
      icon: History, 
      component: <RepairHistory updateTrigger={updateTrigger} /> 
    },
  ];

  return (
    <div className="h-full flex overflow-hidden bg-dark-bg text-[#F9FAFB]">
      
      {/* Sidebar Navigation */}
      <div className="w-64 bg-dark-surface border-r border-dark-border flex flex-col justify-between flex-shrink-0">
        <div>
          
          {/* Theme Insignia */}
          <div className="p-5 border-b border-dark-border flex items-center space-x-3">
            <div className="p-1.5 bg-cyan-500/10 text-cyan-400 rounded-lg">
              <Shield className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">DRDO Maintenance</h2>
              <p className="text-[10px] text-gray-500 font-semibold tracking-wide">Predictive AI Ecosystem</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded text-xs font-semibold tracking-wide transition-colors ${
                    activeTab === tab.id
                      ? 'bg-cyan-600 text-white font-bold'
                      : 'hover:bg-dark-card/50 text-gray-400 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer info (Academic synthetic label) */}
        <div className="p-4 border-t border-dark-border space-y-1">
          <div className="flex items-center space-x-2 text-[9px] bg-amber-500/5 text-amber-500 border border-amber-500/20 p-2.5 rounded-lg leading-normal">
            <span className="font-semibold text-center w-full">ACADEMIC SIMULATED TELEMETRY DATA ONLY</span>
          </div>
          <p className="text-[9px] text-gray-600 text-center mt-1">Version 1.0.0 (Release)</p>
        </div>

      </div>

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-dark-bg">
        <ErrorBoundary>
          {tabs.find(tab => tab.id === activeTab)?.component}
        </ErrorBoundary>
      </div>

    </div>
  );
}
