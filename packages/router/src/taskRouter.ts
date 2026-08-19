import type { AgentRole, RouteDecision, Task } from "../../core/src/types.js";

export class TaskRouter {
  route(task: Task): RouteDecision {
    const type = task.type.toLowerCase();
    let coalition: AgentRole[];
    let reason: string;
    let modelTier: RouteDecision["modelTier"] = "T0";

    if (type.includes("metric") || type.includes("funnel") || type.includes("anomaly")) {
      coalition = ["DATA"];
      reason = "deterministic metric/anomaly task";
    } else if (type.includes("lead") || type.includes("sales") || type.includes("followup")) {
      coalition = ["SALES"];
      reason = "lead qualification/follow-up task";
    } else if (type.includes("research")) {
      coalition = ["RESEARCH", "AUD"];
      reason = "material sourced claim requires independent audit";
      modelTier = task.risk === "HIGH" ? "T3" : "T1";
    } else if (type.includes("content") || type.includes("campaign")) {
      coalition = ["CMO"];
      reason = "content drafting from verified inputs";
      modelTier = "T1";
    } else if (type.includes("incident") || type.includes("code")) {
      coalition = ["DEV", "AUD"];
      reason = "code/incident task with independent challenge";
      modelTier = task.risk === "HIGH" ? "T3" : "T2";
    } else if (type.includes("priority") || type.includes("ceo")) {
      coalition = ["CEO", "AUD"];
      reason = "material prioritization decision";
      modelTier = task.risk === "LOW" ? "T2" : "T3";
    } else {
      coalition = ["CEO"];
      reason = "unclassified internal task routed to governor";
      modelTier = task.risk === "LOW" ? "T1" : "T2";
    }

    return { taskId: task.id, coalition, modelTier, deterministicFirst: modelTier === "T0", reason };
  }
}
