// src/components/BracketView.jsx
import { useState } from "react";
import { useSimulateTournament } from "../hooks/useTournament";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from "recharts";

const COLORS = [
  "#f5c842","#e6b800","#10b981","#34d399","#60a5fa","#818cf8",
  "#f87171","#fb923c","#a78bfa","#4ade80","#38bdf8","#f472b6",
];

export default function BracketView() {
  const { mutate: simulate, data, isPending, error } = useSimulateTournament();
  const [n, setN] = useState(5000);

  const top12 = data?.slice(0, 12) ?? [];

  return (
    <div className="space-y-6">
      <div className="bg-pitch-900 border border-pitch-700 rounded-2xl p-6">
        <h2 className="font-display text-3xl text-gold-400 tracking-wide mb-2">
          SIMULACIÓN MONTE CARLO
        </h2>
        <p className="text-sm text-gray-400 mb-5">
          Corre el torneo completo N veces y calcula probabilidades de bracket.
        </p>

        <div className="flex items-center gap-4 mb-5">
          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-widest">
              Simulaciones: <span className="text-gold-400 font-mono">{n.toLocaleString()}</span>
            </label>
            <input
              type="range"
              min={1000}
              max={50000}
              step={1000}
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
              className="w-full accent-gold-400"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1k (rápido)</span>
              <span>50k (preciso)</span>
            </div>
          </div>
        </div>

        <button
          onClick={() => simulate({ n_simulations: n, n_workers: 4 })}
          disabled={isPending}
          className="w-full bg-gold-400 hover:bg-gold-500 text-pitch-950 font-display
                     text-xl tracking-widest py-3 rounded-xl transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending
            ? `SIMULANDO ${n.toLocaleString()} TORNEOS...`
            : "🎲 SIMULAR TORNEO"}
        </button>

        {error && (
          <p className="text-red-400 text-sm text-center mt-3">
            {error.response?.data?.detail || error.message}
          </p>
        )}
      </div>

      {data && (
        <>
          {/* Win probability chart */}
          <div className="bg-pitch-900 border border-pitch-700 rounded-2xl p-6">
            <h3 className="font-display text-xl text-white mb-4 tracking-wide">
              PROBABILIDAD DE CAMPEONAR — TOP 12
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={top12} layout="vertical" barSize={18}>
                  <XAxis
                    type="number"
                    domain={[0, "auto"]}
                    tick={{ fill: "#9ca3af", fontSize: 11 }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <YAxis
                    type="category"
                    dataKey="team"
                    width={100}
                    tick={{ fill: "#e5e7eb", fontSize: 12 }}
                  />
                  <Tooltip
                    formatter={(v) => [`${v}%`, "Prob. campeonar"]}
                    contentStyle={{
                      background: "#102b1b",
                      border: "1px solid #1a3d27",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="win_pct" radius={[0, 4, 4, 0]}>
                    {top12.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Full table */}
          <div className="bg-pitch-900 border border-pitch-700 rounded-2xl p-6">
            <h3 className="font-display text-xl text-white mb-4 tracking-wide">
              RESULTADOS COMPLETOS
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-400 uppercase tracking-widest border-b border-pitch-700">
                    <th className="text-left py-2 pr-4">#</th>
                    <th className="text-left py-2 pr-4">Equipo</th>
                    <th className="text-right py-2 pr-4">🏆 Campeón</th>
                    <th className="text-right py-2 pr-4">Final</th>
                    <th className="text-right py-2 pr-4">Semis</th>
                    <th className="text-right py-2 pr-4">Cuartos</th>
                    <th className="text-right py-2">R16</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row, i) => (
                    <tr
                      key={row.team}
                      className="border-b border-pitch-800 hover:bg-pitch-800 transition-colors"
                    >
                      <td className="py-2 pr-4 text-gray-500 font-mono">{i + 1}</td>
                      <td className="py-2 pr-4 font-medium text-white">{row.team}</td>
                      <td className="py-2 pr-4 text-right font-mono text-gold-400">
                        {row.win_pct}%
                      </td>
                      <td className="py-2 pr-4 text-right font-mono text-gray-300">
                        {row.final_pct}%
                      </td>
                      <td className="py-2 pr-4 text-right font-mono text-gray-400">
                        {row.sf_pct}%
                      </td>
                      <td className="py-2 pr-4 text-right font-mono text-gray-500">
                        {row.qf_pct}%
                      </td>
                      <td className="py-2 text-right font-mono text-gray-600">
                        {row.r16_pct}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
