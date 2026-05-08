// src/hooks/usePrediction.js
import { useMutation, useQuery } from "@tanstack/react-query";
import { predictMatch, predictKnockout, getTeamStats, getEloRankings, listTeams } from "../api/client";

export function usePredictMatch() {
  return useMutation({
    mutationFn: predictMatch,
    onError: (err) => console.error("Prediction error:", err),
  });
}

export function usePredictKnockout() {
  return useMutation({
    mutationFn: predictKnockout,
  });
}

export function useTeamStats(teamName) {
  return useQuery({
    queryKey: ["teamStats", teamName],
    queryFn: () => getTeamStats(teamName),
    enabled: Boolean(teamName),
    staleTime: 5 * 60 * 1000, // 5 min
  });
}

export function useEloRankings() {
  return useQuery({
    queryKey: ["eloRankings"],
    queryFn: getEloRankings,
    staleTime: 10 * 60 * 1000,
  });
}

export function useTeamsList() {
  return useQuery({
    queryKey: ["teamsList"],
    queryFn: () => listTeams().then((d) => d.teams),
    staleTime: Infinity,
  });
}
