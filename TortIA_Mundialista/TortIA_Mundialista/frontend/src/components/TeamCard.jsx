// src/components/TeamCard.jsx
import { useTeamStats } from "../hooks/usePrediction";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip
} from "recharts";

function StatRow({ label, value, unit = "" }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-pitch-700 last:border-0">
      <span className="text-sm text-gray-400">{label}</span>
      <span className="font-mono text-sm text-white">
        {typeof value === "number" ? value.toFixed(2) : value}
        {unit && <span className="text-gray-500 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export default function TeamCard({ teamName }) {
  const { data, isLoading, error } = useTeamStats(teamName);

  if (!teamName) return null;
  if (isLoading) return (
    <div className="bg-pitch-900 border border-pitch-700 rounded-2xl p-6 animate-pulse">
      <div className="h-6 bg-pitch-700 rounded w-1/2 mb-4" />
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => <div key={i} className="h-4 bg-pitch-700 rounded" />)}
      </div>
    </div>
  );
  if (error) return (
    <div className="bg-pitch-900 border border-red-900 rounded-2xl p-6 text-red-400 text-sm">
      Error cargando {teamName}: {error.message}
    </div>
  );

  const radarData = [
    { subject: "Ataque", A: data.xg_avg_last5 * 50, fullMark: 100 },
    { subject: "Defensa", A: (3 - data.xgc_avg_last5) * 33, fullMark: 100 },
    { subject: "Forma", A: (data.last5_ppg / 3) * 100, fullMark: 100 },
    { subject: "Goles", A: data.goals_avg_last5 * 33, fullMark: 100 },
    { subject: "Elo", A: Math.min((data.elo - 1400) / 8, 100), fullMark: 100 },
  ];

  return (
    <div className="bg-pitch-900 border border-pitch-700 rounded-2xl p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-display text-2xl text-white tracking-wide">{data.team}</h3>
          <p className="text-xs text-gray-400 mt-0.5">Estadísticas actualizadas</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl text-gold-400">{Math.round(data.elo)}</p>
          <p className="text-xs text-gray-400">Elo rating</p>
        </div>
      </div>

      {/* Radar */}
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData}>
            <PolarGrid stroke="#1a3d27" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "#102b1b",
                border: "1px solid #1a3d27",
                borderRadius: 8,
              }}
            />
            <Radar
              name={data.team}
              dataKey="A"
              stroke="#f5c842"
              fill="#f5c842"
              fillOpacity={0.2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Stats */}
      <div className="space-y-0">
        <StatRow label="Puntos por partido (últimos 5)" value={data.last5_ppg} />
        <StatRow label="xG promedio (últimos 5)" value={data.xg_avg_last5} />
        <StatRow label="xGC promedio (concedidos)" value={data.xgc_avg_last5} />
        <StatRow label="Goles anotados (prom.)" value={data.goals_avg_last5} />
        <StatRow label="Goles recibidos (prom.)" value={data.goals_conceded_avg_last5} />
        {data.attack_strength && (
          <StatRow label="Fuerza ofensiva (Poisson)" value={data.attack_strength} />
        )}
        {data.defense_strength && (
          <StatRow label="Fuerza defensiva (Poisson)" value={data.defense_strength} />
        )}
      </div>
    </div>
  );
}
