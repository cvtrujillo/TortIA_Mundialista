// src/pages/Tournament.jsx
import BracketView from "../components/BracketView";
import { useGroups } from "../hooks/useTournament";

export default function Tournament() {
  const { data: groups, isLoading } = useGroups();

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <div>
        <p className="text-xs text-gold-400 uppercase tracking-[0.3em] font-mono mb-2">
          WC 2026 · 48 equipos · 12 grupos
        </p>
        <h1 className="font-display text-5xl text-white tracking-wider">
          SIMULADOR DE BRACKET
        </h1>
      </div>

      {/* Groups */}
      {!isLoading && groups && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {Object.entries(groups).map(([name, teams]) => (
            <div
              key={name}
              className="bg-pitch-900 border border-pitch-700 rounded-xl p-3"
            >
              <p className="font-display text-gold-400 tracking-widest mb-2 text-sm">
                GRUPO {name}
              </p>
              {teams.map((team) => (
                <p key={team} className="text-sm text-gray-300 py-0.5 border-b border-pitch-800 last:border-0">
                  {team}
                </p>
              ))}
            </div>
          ))}
        </div>
      )}

      <BracketView />
    </div>
  );
}
