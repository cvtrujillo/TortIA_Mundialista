// src/api/client.js
import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
  headers: { "Content-Type": "application/json" },
});

// ── Match Predictions ──────────────────────────────────────────────────────────

export const predictMatch = (payload) =>
  api.post("/predict/match", payload).then((r) => r.data);

export const predictKnockout = (payload) =>
  api.post("/predict/knockout", payload).then((r) => r.data);

export const postLiveResult = (payload) =>
  api.post("/predict/live-update", payload).then((r) => r.data);

// ── Tournament ─────────────────────────────────────────────────────────────────

export const simulateTournament = (n_simulations = 10000, n_workers = 4) =>
  api.post("/tournament/simulate", { n_simulations, n_workers }).then((r) => r.data);

export const getGroups = () =>
  api.get("/tournament/groups").then((r) => r.data);

// ── Teams ──────────────────────────────────────────────────────────────────────

export const getTeamStats = (teamName) =>
  api.get(`/teams/${encodeURIComponent(teamName)}/stats`).then((r) => r.data);

export const getEloRankings = () =>
  api.get("/teams/rankings/elo").then((r) => r.data);

export const listTeams = () =>
  api.get("/teams/").then((r) => r.data);

// ── Health ─────────────────────────────────────────────────────────────────────

export const checkHealth = () =>
  api.get("/health").then((r) => r.data);
