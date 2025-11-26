/**
 * API interface to Tauri backend
 */

import { invoke } from "@tauri-apps/api/core";

export interface StatusResponse {
  total_accounts: number;
  total_transactions: number;
  total_snapshots: number;
  total_integrations: number;
  integration_names: string[];
  earliest_date: string | null;
  latest_date: string | null;
  accounts: unknown[];
  integrations: unknown[];
}

/**
 * Get financial data status from CLI
 */
export async function getStatus(): Promise<StatusResponse> {
  const jsonString = await invoke<string>("status");
  console.log(jsonString);

  // Parse JSON string from Rust backend
  const response = JSON.parse(jsonString);

  // Convert from raw response to StatusResponse
  return {
    total_accounts: Number(response.total_accounts) || 0,
    total_transactions: Number(response.total_transactions) || 0,
    total_snapshots: Number(response.total_snapshots) || 0,
    total_integrations: Number(response.total_integrations) || 0,
    integration_names: response.integration_names || [],
    earliest_date: response.earliest_date || null,
    latest_date: response.latest_date || null,
    accounts: response.accounts || [],
    integrations: response.integrations || []
  };
}
