// src/App.jsx
import { Routes, Route, Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { checkHealth } from "./api/client";
import Home from "./pages/Home";
import Tournament from "./pages/Tournament";
import clsx from "clsx";

function Navbar() {
  const { pathname } = useLocation();
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: checkHealth,
    retry: false,
    refetchInterval: 30_000,
  });

  const links = [
    { to: "/TortIA_Mundialista/", label: "⚽ Predicciones" },
    { to: "/TortIA_Mundialista/tournament", label: "🏆 Bracket" },
  ];

  return (
    <nav className="border-b border-pitch-700 bg-pitch-950/90 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/TortIA_Mundialista/" className="font-display text-2xl text-gold-400 tracking-widest">
          TORTÍA
        </Link>

        <div className="flex items-center gap-1">
          {links.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={clsx(
                "px-4 py-1.5 rounded-lg text-sm transition-colors",
                pathname === to || (to !== "/TortIA_Mundialista/" && pathname.startsWith(to))
                  ? "bg-pitch-700 text-white"
                  : "text-gray-400 hover:text-white hover:bg-pitch-800"
              )}
            >
              {label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div
            className={clsx(
              "w-2 h-2 rounded-full",
              health?.status === "ok" ? "bg-emerald-400" : "bg-red-400"
            )}
            title={health?.status === "ok" ? "API online" : "API offline"}
          />
          <span className="text-xs text-gray-500 hidden sm:inline">
            {health?.models_loaded ? "Modelos cargados" : "Sin modelos"}
          </span>
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-pitch-950">
      <Navbar />
      <main>
        <Routes>
          <Route path="/TortIA_Mundialista/" element={<Home />} />
          <Route path="/TortIA_Mundialista/tournament" element={<Tournament />} />
        </Routes>
      </main>
      <footer className="border-t border-pitch-700 mt-20 py-6 text-center text-xs text-gray-600">
        TortIA Mundialista · WC2026 Prediction Engine ·{" "}
        <a
          href="https://github.com/cvtrujillo/TortIA_Mundialista"
          className="text-gold-400 hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          GitHub
        </a>
      </footer>
    </div>
  );
}
