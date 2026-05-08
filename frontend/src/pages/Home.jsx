// src/pages/Home.jsx
import { useState } from "react";
import MatchPredictor from "../components/MatchPredictor";
import TeamCard from "../components/TeamCard";

const FEATURED_TEAMS = ["Argentina","France","Brazil","Spain","England","Germany"];

export default function Home() {
  const [selectedTeam, setSelectedTeam] = useState(null);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">
      {/* Hero */}
      <div className="text-center space-y-3">
        <p className="text-xs text-gold-400 uppercase tracking-[0.3em] font-mono">
          Motor de predicción IA · WC 2026
        </p>
        <h1 className="font-display text-6xl md:text-8xl text-white tracking-wider leading-none">
          TORTÍA<br />
          <span className="text-gold-400">MUNDIALISTA</span>
        </h1>
        <p className="text-gray-400 max-w-xl mx-auto text-sm leading-relaxed">
          Predicciones en tiempo real para la Copa del Mundo 2026 usando Dixon-Coles Poisson,
          XGBoost y simulaciones Monte Carlo de 10,000 torneos.
        </p>
      </div>

      {/* Stats banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Equipos", value: "48" },
          { label: "Partidos modelo", value: "1,200+" },
          { label: "Simulaciones", value: "10,000" },
          { label: "Features ML", value: "19" },
        ].map(({ label, value }) => (
          <div key={label} className="bg-pitch-900 border border-pitch-700 rounded-xl p-4 text-center">
            <p className="font-display text-3xl text-gold-400">{value}</p>
            <p className="text-xs text-gray-400 uppercase tracking-widest mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        <MatchPredictor />

        <div className="space-y-4">
          {/* Team selector */}
          <div className="bg-pitch-900 border border-pitch-700 rounded-2xl p-5">
            <h3 className="font-display text-xl text-gold-400 tracking-wide mb-3">
              PERFIL DE EQUIPO
            </h3>
            <div className="flex flex-wrap gap-2 mb-4">
              {FEATURED_TEAMS.map((t) => (
                <button
                  key={t}
                  onClick={() => setSelectedTeam(t)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    selectedTeam === t
                      ? "bg-gold-400 text-pitch-950 font-medium"
                      : "bg-pitch-800 text-gray-300 hover:bg-pitch-700"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
            {selectedTeam && <TeamCard teamName={selectedTeam} />}
            {!selectedTeam && (
              <p className="text-gray-500 text-sm text-center py-8">
                Selecciona un equipo para ver sus estadísticas
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
