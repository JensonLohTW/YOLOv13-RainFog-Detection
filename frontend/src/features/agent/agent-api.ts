import { apiPost } from "@/services/api";

import type { AgentAskRequest, AnalyticsAgentResponse } from "./agent-types";

export function askAnalyticsQuestion(
  question: string,
): Promise<AnalyticsAgentResponse> {
  return apiPost<AnalyticsAgentResponse, AgentAskRequest>("/agent/ask", {
    agent_type: "analytics_qa",
    question,
  });
}
