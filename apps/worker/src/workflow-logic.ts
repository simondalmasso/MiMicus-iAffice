export interface LogicalWorkflowStep { do<T>(name: string, fn: () => Promise<T>): Promise<T>; }
export interface BusinessWorkflowParams { taskId: string; kind: string; }
export async function runBusinessWorkflow(payload: BusinessWorkflowParams,step: LogicalWorkflowStep): Promise<{taskId:string;status:"DONE"|"BLOCKED_POLICY"}> {
  const accepted=await step.do("accept",async()=>({taskId:payload.taskId,kind:payload.kind}));
  const preflight=await step.do("policy-preflight",async()=>({allowed:!["MONEY_MUTATION","CREDENTIAL_MUTATION","DESTRUCTIVE_MUTATION"].includes(accepted.kind)}));
  if(!preflight.allowed)return {taskId:accepted.taskId,status:"BLOCKED_POLICY"};
  return step.do("complete",async()=>({taskId:accepted.taskId,status:"DONE" as const}));
}
