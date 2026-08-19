import { WorkflowEntrypoint } from "cloudflare:workers";
import type { WorkflowEvent, WorkflowStep } from "cloudflare:workers";
import type { Env } from "./runtime-types.js";
import { runBusinessWorkflow } from "./workflow-logic.js";
export interface BusinessWorkflowParams { taskId:string;kind:string;approvalId?:string; }
export class BusinessWorkflow extends WorkflowEntrypoint<Env,BusinessWorkflowParams> {
  override async run(event:WorkflowEvent<BusinessWorkflowParams>,step:WorkflowStep):Promise<{taskId:string;status:"DONE"|"BLOCKED_POLICY"|"REJECTED"}>{
    if(!event.payload.approvalId)return runBusinessWorkflow(event.payload,step);
    await step.do("protected-action-preflight",async()=>({taskId:event.payload.taskId,approvalId:event.payload.approvalId,kind:event.payload.kind,externalExecution:"DISABLED_IN_V1"}));
    try{const eventResult=await step.waitForEvent<{decision?:string;approvalId?:string}>("wait-human-approval",{type:"approval",timeout:"15 minutes"});if(eventResult.payload.approvalId!==event.payload.approvalId||eventResult.payload.decision!=="APPROVED")return {taskId:event.payload.taskId,status:"REJECTED"};return step.do("record-approved-boundary",async()=>({taskId:event.payload.taskId,status:"DONE" as const}));}catch{return {taskId:event.payload.taskId,status:"REJECTED"};}
  }
}
