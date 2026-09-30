import { sha256, stableId } from "../../core/src/hash.js";
import type { D1Like } from "../../memory/src/store.js";
import type { ContactPoint } from "./engine.js";
import { DEFAULT_COMMERCIAL_CONTACT_LIMITS, evaluateCommercialPolicy, type CommercialPolicyResult, type ContactProvenance } from "./commercialPolicy.js";
import type { ExternalOperation } from "./operatingModel.js";

const PERSUASIVE = new Set<ExternalOperation>(["SEND_OUTREACH","SCHEDULE_EXTERNAL_MEETING","SEND_PROPOSAL"]);
const OUTBOUND = new Set<ExternalOperation>(["SEND_OUTREACH","SCHEDULE_EXTERNAL_MEETING","SEND_PROPOSAL","SEND_DELIVERY_NOTICE","SEND_RECEIPT"]);

export interface CommercialActionDraft {
  caseId: string;
  operation: ExternalOperation;
  target: string;
  payload: Record<string,unknown>;
  auditId?: string | null;
}

export interface CommercialGuardSnapshot {
  caseId: string;
  operation: ExternalOperation;
  target: string;
  contactProvenance: ContactProvenance;
  explicitRefusal: boolean;
  optOut: boolean;
  autonomousContactsInWindow: number;
  hoursSinceLastContact: number;
  acceptedOffer: boolean;
  customerApproval: boolean;
  paymentVerified: boolean;
  humanGate: boolean;
  humanGateReasons: string[];
  commercialAuditPass: boolean;
  commercialAuditId: string | null;
  commercialPayloadDigest: string;
}

export interface CommercialGuardEvaluation {
  decision: CommercialPolicyResult["decision"];
  reasons: string[];
  snapshot: CommercialGuardSnapshot;
}

function parse<T>(value:unknown,fallback:T):T{
  if(typeof value!=="string")return fallback;
  try{return JSON.parse(value) as T}catch{return fallback}
}

function normalizeTarget(value:string,kind?:string):string{
  const raw=value.trim().toLowerCase().replace(/^mailto:/,"").replace(/^tel:/,"");
  if(kind==="PHONE"||kind==="WHATSAPP"||/^\+?[\d\s().-]+$/.test(raw))return raw.replace(/\D/g,"");
  return raw;
}

export function contactProvenanceForTarget(contacts:ContactPoint[],target:string):ContactProvenance{
  for(const contact of contacts){
    if(normalizeTarget(contact.value,contact.kind)===normalizeTarget(target,contact.kind))return contact.provenance;
  }
  return "UNKNOWN";
}

export function acceptedCommercialState(status:string,negotiationState:string|null):boolean{
  if(["WON","DELIVERING","DELIVERED"].includes(status.toUpperCase()))return true;
  return ["ACCEPTED","WON","CLOSED_WON","AGREED"].includes(String(negotiationState??"").toUpperCase());
}

export function approvedDeliveryState(state:string|null,acceptance:unknown):boolean{
  const a=acceptance&&typeof acceptance==="object"?acceptance as Record<string,unknown>:{};
  if(a.approved===true||a.accepted===true||a.customerApproved===true)return true;
  return ["APPROVED","ACCEPTED"].includes(String(state??"").toUpperCase());
}

export function verifiedPaymentState(state:string|null):boolean{
  return ["COLLECTED","PAID","VERIFIED","SETTLED"].includes(String(state??"").toUpperCase());
}

export async function commercialActionDigest(draft:CommercialActionDraft):Promise<string>{
  return sha256({caseId:draft.caseId,operation:draft.operation,target:draft.target,payload:draft.payload});
}

export class CommercialGuard {
  constructor(private readonly db:D1Like){}

  async caseExists(caseId:string):Promise<boolean>{
    const row=await this.db.prepare("SELECT id FROM sniper_opportunities WHERE id=?1").bind(caseId).first<{id:string}>();
    return Boolean(row?.id);
  }

  async evaluate(draft:CommercialActionDraft,now=new Date().toISOString()):Promise<CommercialGuardEvaluation>{
    if(!draft.caseId||!draft.operation||!draft.target||!draft.payload||typeof draft.payload!=="object")throw new Error("COMMERCIAL_ACTION_SCHEMA_INVALID");

    const opportunity=await this.db.prepare(
      "SELECT id,status,contacts_json FROM sniper_opportunities WHERE id=?1"
    ).bind(draft.caseId).first<Record<string,unknown>>();
    if(!opportunity)throw new Error("COMMERCIAL_CASE_NOT_FOUND");

    const contacts=parse<ContactPoint[]>(opportunity.contacts_json,[]);
    const provenance=OUTBOUND.has(draft.operation)?contactProvenanceForTarget(contacts,draft.target):"OWNER_PROVIDED";

    const controls=await this.db.prepare(
      "SELECT do_not_contact,explicit_refusal FROM sniper_contact_controls WHERE case_id=?1"
    ).bind(draft.caseId).first<Record<string,unknown>>();

    const windowStart=new Date(Date.parse(now)-DEFAULT_COMMERCIAL_CONTACT_LIMITS.rollingWindowHours*3600_000).toISOString();
    const count=await this.db.prepare(
      "SELECT COUNT(*) AS n FROM sniper_commercial_effects WHERE case_id=?1 AND operation IN ('SEND_OUTREACH','SCHEDULE_EXTERNAL_MEETING','SEND_PROPOSAL') AND state='EXECUTED' AND created_at>=?2"
    ).bind(draft.caseId,windowStart).first<{n:number}>();
    const latest=await this.db.prepare(
      "SELECT created_at FROM sniper_commercial_effects WHERE case_id=?1 AND operation IN ('SEND_OUTREACH','SCHEDULE_EXTERNAL_MEETING','SEND_PROPOSAL') AND state='EXECUTED' ORDER BY created_at DESC LIMIT 1"
    ).bind(draft.caseId).first<{created_at:string}>();

    const negotiation=await this.db.prepare(
      "SELECT state,human_gate,human_gate_reasons_json FROM sniper_negotiations WHERE opportunity_id=?1 ORDER BY updated_at DESC LIMIT 1"
    ).bind(draft.caseId).first<Record<string,unknown>>();

    const delivery=await this.db.prepare(
      "SELECT state,acceptance_json FROM sniper_deliveries WHERE opportunity_id=?1 ORDER BY updated_at DESC LIMIT 1"
    ).bind(draft.caseId).first<Record<string,unknown>>();

    const payment=await this.db.prepare(
      "SELECT state FROM sniper_payments WHERE opportunity_id=?1 ORDER BY updated_at DESC LIMIT 1"
    ).bind(draft.caseId).first<{state:string}>();

    const digest=await commercialActionDigest(draft);
    let auditPass=!PERSUASIVE.has(draft.operation);
    let resolvedAuditId:string|null=null;
    if(PERSUASIVE.has(draft.operation)&&draft.auditId){
      const audit=await this.db.prepare(
        "SELECT id,verdict,strategy,evidence_refs_json FROM audit_findings WHERE id=?1 AND target_id=?2"
      ).bind(draft.auditId,digest).first<Record<string,unknown>>();
      const refs=audit?parse<string[]>(audit.evidence_refs_json,[]):[];
      auditPass=Boolean(audit&&String(audit.verdict)==="PASS"&&String(audit.strategy)==="COMMERCIAL_COPY_GUARD"&&refs.length>0);
      if(auditPass)resolvedAuditId=String(audit!.id);
    }

    const nowMs=Date.parse(now);
    const lastMs=latest?Date.parse(latest.created_at):NaN;
    const hoursSinceLastContact=Number.isFinite(nowMs)&&Number.isFinite(lastMs)?Math.max(0,(nowMs-lastMs)/3600_000):Number.MAX_SAFE_INTEGER;
    const acceptedOffer=acceptedCommercialState(String(opportunity.status),negotiation?.state==null?null:String(negotiation.state));
    const humanGate=Number(negotiation?.human_gate??0)===1;
    const humanGateReasons=negotiation?parse<string[]>(negotiation.human_gate_reasons_json,[]):[];
    const customerApproval=approvedDeliveryState(delivery?.state==null?null:String(delivery.state),delivery?parse(delivery.acceptance_json,{}):{});
    const paymentVerified=verifiedPaymentState(payment?.state??null);

    const result=evaluateCommercialPolicy({
      action:draft.operation,
      explicitRefusal:Number(controls?.explicit_refusal??0)===1,
      optOut:Number(controls?.do_not_contact??0)===1,
      autonomousContactsInWindow:Number(count?.n??0),
      hoursSinceLastContact,
      contactProvenance:provenance,
      claimsSupported:auditPass,
      falseUrgency:false,
      humanImpersonation:false,
      bulkBlast:false,
      acceptedOffer,
      customerApproval,
      paymentVerified
    });
    const reasons=[...result.reasons];
    if(PERSUASIVE.has(draft.operation)&&!auditPass)reasons.push("COMMERCIAL_AUDIT_PASS_REQUIRED");
    if(humanGate&&["SEND_PROPOSAL","SCHEDULE_EXTERNAL_MEETING","CREATE_PAYMENT_REQUEST"].includes(draft.operation))reasons.push("HUMAN_GATE_REQUIRED");

    const snapshot:CommercialGuardSnapshot={
      caseId:draft.caseId,
      operation:draft.operation,
      target:draft.target,
      contactProvenance:provenance,
      explicitRefusal:Number(controls?.explicit_refusal??0)===1,
      optOut:Number(controls?.do_not_contact??0)===1,
      autonomousContactsInWindow:Number(count?.n??0),
      hoursSinceLastContact,
      acceptedOffer,
      customerApproval,
      paymentVerified,
      humanGate,
      humanGateReasons,
      commercialAuditPass:auditPass,
      commercialAuditId:resolvedAuditId,
      commercialPayloadDigest:digest
    };
    const decision:CommercialPolicyResult["decision"]=reasons.includes("HUMAN_GATE_REQUIRED")?"HUMAN_GATE":reasons.length?"DENY":"ALLOW";
    return {decision,reasons:[...new Set(reasons)],snapshot};
  }

  async setContactControl(input:{caseId:string;doNotContact:boolean;explicitRefusal:boolean;reason?:string|null;evidenceRefs:string[]},now=new Date().toISOString()):Promise<void>{
    if(!(await this.caseExists(input.caseId)))throw new Error("COMMERCIAL_CASE_NOT_FOUND");
    if((input.doNotContact||input.explicitRefusal)&&input.evidenceRefs.length===0)throw new Error("CONTACT_CONTROL_EVIDENCE_REQUIRED");
    await this.db.prepare(
      "INSERT INTO sniper_contact_controls (case_id,do_not_contact,explicit_refusal,reason,evidence_refs_json,updated_at) VALUES (?1,?2,?3,?4,?5,?6) ON CONFLICT(case_id) DO UPDATE SET do_not_contact=excluded.do_not_contact,explicit_refusal=excluded.explicit_refusal,reason=excluded.reason,evidence_refs_json=excluded.evidence_refs_json,updated_at=excluded.updated_at"
    ).bind(input.caseId,input.doNotContact?1:0,input.explicitRefusal?1:0,input.reason??null,JSON.stringify(input.evidenceRefs),now).run();
  }

  async recordCommercialAudit(input:{caseId:string;operation:ExternalOperation;target:string;payload:Record<string,unknown>;verdict:"PASS"|"FAIL"|"UNCERTAIN";reason:string;evidenceRefs:string[]},now=new Date().toISOString()):Promise<{auditId:string;targetDigest:string}>{
    if(!(await this.caseExists(input.caseId)))throw new Error("COMMERCIAL_CASE_NOT_FOUND");
    if(input.evidenceRefs.length===0)throw new Error("COMMERCIAL_AUDIT_EVIDENCE_REQUIRED");
    const targetDigest=await commercialActionDigest({caseId:input.caseId,operation:input.operation,target:input.target,payload:input.payload});
    const auditId=await stableId("commercial-copy-audit",{targetDigest,verdict:input.verdict,reason:input.reason,evidenceRefs:[...input.evidenceRefs].sort(),now});
    const hash=await sha256({auditId,targetDigest,verdict:input.verdict,reason:input.reason,evidenceRefs:input.evidenceRefs,strategy:"COMMERCIAL_COPY_GUARD"});
    await this.db.prepare(
      "INSERT OR IGNORE INTO audit_findings (id,target_id,verdict,reason,evidence_refs_json,created_at,strategy,hash) VALUES (?1,?2,?3,?4,?5,?6,'COMMERCIAL_COPY_GUARD',?7)"
    ).bind(auditId,targetDigest,input.verdict,input.reason,JSON.stringify(input.evidenceRefs),now,hash).run();
    return {auditId,targetDigest};
  }

  async recordExecuted(input:{caseId:string;operation:ExternalOperation;target:string;intentId:string;receiptId:string},now=new Date().toISOString()):Promise<void>{
    const effectId=await stableId("commercial-effect",{intentId:input.intentId});
    await this.db.prepare(
      "INSERT OR IGNORE INTO sniper_commercial_effects (effect_id,case_id,operation,target,intent_id,receipt_id,state,created_at) VALUES (?1,?2,?3,?4,?5,?6,'EXECUTED',?7)"
    ).bind(effectId,input.caseId,input.operation,input.target,input.intentId,input.receiptId,now).run();
  }
}

export function isExternalOperation(value:unknown):value is ExternalOperation{
  return typeof value==="string"&&[
    "SEND_OUTREACH","SCHEDULE_EXTERNAL_MEETING","SEND_PROPOSAL","PUBLISH_CONTENT",
    "DEPLOY_CUSTOMER_WORK","SEND_DELIVERY_NOTICE","TRANSFER_CREDENTIALS",
    "CREATE_PAYMENT_REQUEST","ISSUE_INVOICE","SEND_RECEIPT"
  ].includes(value);
}