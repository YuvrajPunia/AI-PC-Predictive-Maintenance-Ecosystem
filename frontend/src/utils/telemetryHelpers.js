export const formatSensorValue = (value, decimals = 1, unit = '') => {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toFixed(decimals)}${unit}`
    : "N/A";
};

export const estimateHealth = (pc) => {
  if (
    !pc ||
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

export const getHealthBand = (score) => {
  if (score === null || score === undefined) {
    return { label: 'N/A', color: 'text-gray-400 bg-gray-500/10' };
  }
  if (score >= 80) return { label: 'Healthy', color: 'text-emerald-400 bg-emerald-500/10' };
  if (score >= 60) return { label: 'Moderate', color: 'text-blue-400 bg-blue-500/10' };
  if (score >= 40) return { label: 'Poor', color: 'text-amber-400 bg-amber-500/10' };
  return { label: 'Critical', color: 'text-red-400 bg-red-500/10 border border-red-500/20' };
};
