// src/components/ProbabilityBar.jsx
export default function ProbabilityBar({ label, value, color = "bg-gold-400" }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-300">{label}</span>
        <span className="font-mono text-sm text-white font-medium">
          {value.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-pitch-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}
