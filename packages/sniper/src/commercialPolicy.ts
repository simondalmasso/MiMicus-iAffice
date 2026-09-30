import type { ExternalOperation } from "./operatingModel.js";

export const DEFAULT_COMMERCIAL_CONTACT_LIMITS = {
  maxAutonomousContacts: 3,
  minHoursBetweenContacts: 48,
  rollingWindowHours: 30 * 24
} as const;

export type CommercialPolicyDecision = "ALLOW" | "DENY" | "HUMAN_GATE";

export type ContactProvenance =
  | "PUBLIC_BUSINESS_LISTING"
  | "BUSINESS_WEBSITE"
  | "BUSINESS_SOCIAL"
  | "OWNER_PROVIDED"
  | "OTHER_PUBLIC"
  | "UNKNOWN";

export interface CommercialPolicyInput {
  action: ExternalOperation;
  explicitRefusal: boolean;
  optOut: boolean;
  autonomousContactsInWindow: number;
  hoursSinceLastContact: number;
  contactProvenance: ContactProvenance;
  claimsSupported: boolean;
  falseUrgency: boolean;
  humanImpersonation: boolean;
  bulkBlast: boolean;
  acceptedOffer: boolean;
  customerApproval: boolean;
  paymentVerified: boolean;
}

export interface CommercialPolicyResult {
  decision: CommercialPolicyDecision;
  reasons: string[];
}

function isPersuasiveOutreach(action: ExternalOperation): boolean {
  return ["SEND_OUTREACH","SCHEDULE_EXTERNAL_MEETING","SEND_PROPOSAL"].includes(action);
}

function isOutboundMessage(action: ExternalOperation): boolean {
  return isPersuasiveOutreach(action) || ["SEND_DELIVERY_NOTICE","SEND_RECEIPT"].includes(action);
}

function allowedContactProvenance(provenance: ContactProvenance): boolean {
  return ["PUBLIC_BUSINESS_LISTING","BUSINESS_WEBSITE","BUSINESS_SOCIAL","OWNER_PROVIDED","OTHER_PUBLIC"].includes(provenance);
}

export function evaluateCommercialPolicy(input: CommercialPolicyInput): CommercialPolicyResult {
  const reasons: string[] = [];

  if (isOutboundMessage(input.action) && !allowedContactProvenance(input.contactProvenance)) {
    reasons.push("CONTACT_PROVENANCE_UNVERIFIED");
  }

  if (isPersuasiveOutreach(input.action)) {
    if (input.explicitRefusal || input.optOut) reasons.push("DO_NOT_CONTACT");
    if (input.bulkBlast) reasons.push("BULK_BLAST_DENIED");
    if (!input.claimsSupported) reasons.push("UNSUPPORTED_CLAIM");
    if (input.falseUrgency) reasons.push("FALSE_URGENCY_DENIED");
    if (input.humanImpersonation) reasons.push("HUMAN_IMPERSONATION_DENIED");
    if (input.autonomousContactsInWindow >= DEFAULT_COMMERCIAL_CONTACT_LIMITS.maxAutonomousContacts) reasons.push("CONTACT_FATIGUE_LIMIT");
    if (
      input.autonomousContactsInWindow > 0 &&
      input.hoursSinceLastContact < DEFAULT_COMMERCIAL_CONTACT_LIMITS.minHoursBetweenContacts
    ) reasons.push("CONTACT_COOLDOWN");
  }

  if (input.action === "CREATE_PAYMENT_REQUEST" && !input.acceptedOffer) {
    reasons.push("COMMERCIAL_ACCEPTANCE_REQUIRED");
  }

  if (input.action === "DEPLOY_CUSTOMER_WORK" && !input.customerApproval) {
    reasons.push("CUSTOMER_APPROVAL_REQUIRED");
  }

  if ((input.action === "ISSUE_INVOICE" || input.action === "SEND_RECEIPT") && !input.paymentVerified) {
    reasons.push("PAYMENT_VERIFICATION_REQUIRED");
  }

  if (input.action === "TRANSFER_CREDENTIALS" && !input.customerApproval) {
    reasons.push("CREDENTIAL_HANDOFF_APPROVAL_REQUIRED");
  }

  return {
    decision: reasons.length > 0 ? "DENY" : "ALLOW",
    reasons
  };
}