import { sha256 } from "../../core/src/hash.js";
import { discoverCandidate } from "./providerEvidence.js";
import type { ProviderEvidenceRecord } from "./computeTypes.js";
export const OMNIROUTE_DISCOVERY_SOURCE={repository:"diegosouzapw/OmniRoute",commit:"3c9cb21cca443b8caef5aa180827a6989e258a95",verifiedAt:"2026-08-19T19:05:00.000Z",authority:"THIRD_PARTY_CATALOG_CANDIDATE_ONLY"} as const;
export interface DiscoveredCandidate{providerId:string;modelId?:string;claimedFree:boolean;sourcePath:string;}
export async function candidateEvidence(candidate:DiscoveredCandidate,retrievedAt:string):Promise<ProviderEvidenceRecord>{const contentHash=await sha256({candidate,source:OMNIROUTE_DISCOVERY_SOURCE});return discoverCandidate(candidate.providerId,`https://github.com/${OMNIROUTE_DISCOVERY_SOURCE.repository}/commit/${OMNIROUTE_DISCOVERY_SOURCE.commit}#${candidate.sourcePath}`,retrievedAt,new Date(new Date(retrievedAt).getTime()+24*3600000).toISOString(),contentHash);}
export function mayActivateFromDiscovery(_evidence:ProviderEvidenceRecord):false{return false;}
