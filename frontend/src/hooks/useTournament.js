// src/hooks/useTournament.js
import { useMutation, useQuery } from "@tanstack/react-query";
import { simulateTournament, getGroups } from "../api/client";

export function useSimulateTournament() {
  return useMutation({
    mutationFn: ({ n_simulations, n_workers }) =>
      simulateTournament(n_simulations, n_workers),
  });
}

export function useGroups() {
  return useQuery({
    queryKey: ["groups"],
    queryFn: getGroups,
    staleTime: Infinity,
  });
}
