// src/components/MatchPredictor.jsx
import { useState } from "react";
import { usePredictMatch } from "../hooks/usePrediction";
import ProbabilityBar from "./ProbabilityBar";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from "recharts";
import clsx from "clsx";

const TEAMS = [
  "Argentina","Australia","Belgium","Bolivia","Brazil","Cameroon","Canada",
  "Chile","Colombia","Costa Rica","Croatia","Denmark","Ecuador","England",
  "France","Germany","Ghana","Indonesia","Iran","Japan","Mexico","Morocco",
  "Netherlands","New Zealand","Panama","Paraguay","Peru","Poland",
  "Portugal","Qatar","Saudi Arabia","Senegal","Serbia","South Korea",
  "Spain","Switzerland","Tunisia","Uruguay","USA","Uzbekistan","Venezuela","Wales",
];

const VENUES = [
  "Mexico City","Guadalajara","Monterrey","Dallas","Los Angeles","New York",
  "Seattle","San Francisco","Boston","Miami","Atlanta","Kansas City",
  "Toronto","Vancouver",
];

const CONF_COLOR = {
  high: "text-emerald-400",
  medium: "text-gold-400",
  low: "text-red-400",
};

export default function MatchPredictor() {
  const { mutate: predict, data, isPending, error } = usePredictMatch();

  const [form, setForm] = useState({
    home_team: "Argentina",
    away_team: "France",
    venue: "Mexico City",
    stage: "group",
    home_rest_days: 4,
    away_rest_days: 4,
    away_travel_km: 9000,
    neutral_venue: false,
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    predict(form);
  };

  const chartData = data
    ? [
        { name: `🏠 ${data.home_team}`, value: data.outcome_probs.home_win, fill: "#10b981" },
        { name: "Empate", value: data.outcome_probs.draw, fill: "#f5c842" },
        { name: `✈️ ${data.away_team}`, value: data.outcome_probs.away_win, fill: "#ef4444" },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Form */}
      <form
        onSubmit={handleSubmit}
        className="bg-pitch-900 border border-pitch-700 rounded-2xl p-6 space-y-5"
      >
        <h2 className="font-display text-3xl text-gold-400 tracking-wide">
          PREDICCIÓN DE PARTIDO
        </h2>

        {/* Teams */}
        <div className="grid grid-cols-2 gap-4">
          {[["home_team", "Local 🏠"], ["away_team", "Visitante ✈️"]].map(([key, label]) => (
            <div key={key}>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-widest">
                {label}
              </label>
              <select
                value={form[key]}
                onChange={(e) => set(key, e.target.value)}
                className="w-full bg-pitch-800 border border-pitch-700 rounded-lg px-3 py-2
                           text-white text-sm focus:border-gold-400 focus:outline-none"
              >
                {TEAMS.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          ))}
        </div>

        {/* Venue + Stage */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-widest">
              Sede
            </label>
            <select
              value={form.venue}
              onChange={(e) => set("venue", e.target.value)}
              className="w-full bg-pitch-800 border border-pitch-700 rounded-lg px-3 py-2
                         text-white text-sm focus:border-gold-400 focus:outline-none"
            >
              {VENUES.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-widest">
              Fase
            </label>
            <select
              value={form.stage}
              onChange={(e) => set("stage", e.target.value)}
              className="w-full bg-pitch-800 border border-pitch-700 rounded-lg px-3 py-2
                         text-white text-sm focus:border-gold-400 focus:outline-none"
            >
              <option value="group">Fase de grupos</option>
              <option value="r16">Octavos</option>
              <option value="qf">Cuartos</option>
              <option value="sf">Semifinal</option>
              <option value="final">Final</option>
            </select>
          </div>
        </div>

        {/* Rest + Travel */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { key: "home_rest_days", label: "Días descanso local", max: 20 },
            { key: "away_rest_days", label: "Días descanso visita", max: 20 },
            { key: "away_travel_km", label: "Distancia viaje (km)", max: 20000 },
          ].map(({ key, label, max }) => (
            <div key={key}>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-widest">
                {label}: <span className="text-gold-400 font-mono">{form[key]}</span>
              </label>
              <input
                type="range"
                min={0}
                max={max}
                step={key === "away_travel_km" ? 100 : 1}
                value={form[key]}
                onChange={(e) => set(key, Number(e.target.value))}
                className="w-full accent-gold-400"
              />
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <input
            id="neutral"
            type="checkbox"
            checked={form.neutral_venue}
            onChange={(e) => set("neutral_venue", e.target.checked)}
            className="accent-gold-400 w-4 h-4"
          />
          <label htmlFor="neutral" className="text-sm text-gray-300">
            Sede neutral (sin ventaja de local)
          </label>
        </div>

        <button
          type="submit"
          disabled={isPending}
          className="w-full bg-gold-400 hover:bg-gold-500 text-pitch-950 font-display
                     text-xl tracking-widest py-3 rounded-xl transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "CALCULANDO..." : "⚽ PREDECIR"}
        </button>

        {error && (
          <p className="text-red-400 text-sm text-center">
            Error: {error.response?.data?.detail || error.message}
          </p>
        )}
      </form>

      {/* Results */}
      {data && (
        <div className="bg-pitch-900 border border-pitch-700 rounded-2xl p-6 space-y-6 animate-fadeIn">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-display text-2xl text-white tracking-wide">
              {data.home_team} vs {data.away_team}
            </h3>
            <span className={clsx("text-sm font-mono uppercase", CONF_COLOR[data.confidence])}>
              Confianza: {data.confidence}
            </span>
          </div>

          {/* Probability bars */}
          <div className="space-y-3">
            <ProbabilityBar
              label={`🏠 ${data.home_team} gana`}
              value={data.outcome_probs.home_win}
              color="bg-emerald-500"
            />
            <ProbabilityBar
              label="Empate"
              value={data.outcome_probs.draw}
              color="bg-gold-400"
            />
            <ProbabilityBar
              label={`✈️ ${data.away_team} gana`}
              value={data.outcome_probs.away_win}
              color="bg-red-500"
            />
          </div>

          {/* Chart */}
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barSize={48}>
                <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  formatter={(v) => [`${v.toFixed(1)}%`, "Probabilidad"]}
                  contentStyle={{
                    background: "#102b1b",
                    border: "1px solid #1a3d27",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Score + xG */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-pitch-800 rounded-xl p-4">
              <p className="text-xs text-gray-400 uppercase tracking-widest mb-1">
                Marcador más probable
              </p>
              <p className="font-display text-4xl text-gold-400 tracking-widest">
                {data.most_likely_score}
              </p>
            </div>
            <div className="bg-pitch-800 rounded-xl p-4">
              <p className="text-xs text-gray-400 uppercase tracking-widest mb-1">
                Goles esperados (xG)
              </p>
              <p className="font-display text-2xl text-white">
                <span className="text-emerald-400">{data.expected_goals.home}</span>
                <span className="text-gray-500 mx-2">—</span>
                <span className="text-red-400">{data.expected_goals.away}</span>
              </p>
            </div>
          </div>

          {/* Top 5 scorelines */}
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-widest mb-3">
              Top 5 marcadores probables
            </p>
            <div className="space-y-2">
              {data.top_5_scorelines.map((s, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="font-mono text-sm text-gold-400 w-10">{s.score}</span>
                  <div className="flex-1 bg-pitch-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-gold-400 rounded-full transition-all"
                      style={{ width: `${Math.min(s.probability * 5, 100)}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs text-gray-400 w-12 text-right">
                    {s.probability.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
