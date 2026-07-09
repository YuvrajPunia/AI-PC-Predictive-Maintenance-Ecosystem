const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'https://ai-pc-predictive-maintenance-ecosystem.onrender.com';
  }
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  const response = await fetch(url, { ...options, headers });
  
  if (!response.ok) {
    let errorDetail = 'API Request Failed';
    try {
      const errBody = await response.json();
      errorDetail = errBody.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }
  
  return response.json();
}

export const api = {
  // PCs
  getPcs: () => request('/api/pcs'),
  getPcById: (id) => request(`/api/pcs/${id}`),
  getPcTelemetry: (id) => request(`/api/pcs/${id}/telemetry`),
  registerPc: (pcData) => request('/api/pcs', {
    method: 'POST',
    body: JSON.stringify(pcData)
  }),
  
  // AI Diagnostics
  analyzeComplaint: (pcId, complaint, currentReadings = null) => request('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ pc_id: pcId, complaint, current_readings: currentReadings })
  }),
  
  // Repairs
  getRepairs: () => request('/api/repairs'),
  getRepairById: (id) => request(`/api/repairs/${id}`),
  completeRepair: (repairData) => request('/api/repairs/complete', {
    method: 'POST',
    body: JSON.stringify(repairData)
  }),
  
  // Dashboard
  getDashboardOverview: () => request('/api/dashboard/overview'),
};
