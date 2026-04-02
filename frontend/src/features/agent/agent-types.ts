export type AgentTraceItem = {
  tool_name: string;
  latency_ms: number;
  status: string;
  version: string;
  error_code: string;
  payload: Record<string, unknown>;
};

export type AnalyticsGrounding = {
  intent: string;
  window: {
    date_from: string;
    date_to: string;
  };
  status_summary: {
    task_total: number;
    success_total: number;
    failed_total: number;
    processing_total: number;
  };
  top_classes: Array<{
    class_name: string;
    count: number;
    avg_confidence: number;
  }>;
  daily_trend: Array<{
    day: string;
    task_total: number;
    success_total: number;
    failed_total: number;
  }>;
};

export type AgentAskRequest = {
  agent_type: "detection_explanation" | "analytics_qa";
  question: string;
  task_no?: string;
  image_id?: number;
};

export type AnalyticsAgentResponse = {
  agent_type: "analytics_qa";
  question: string;
  answer: string;
  grounding: AnalyticsGrounding;
  llm: {
    provider: string;
    model: string;
    config_source: string;
    api_key_source: string;
  };
  trace: AgentTraceItem[];
};
