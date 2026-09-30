export type SemanticPatternStatus = "CANDIDATE" | "VERIFIED" | "DISPUTED";

export interface SemanticPatternState {
  patternId: string;
  scopeKey: string;
  statement: string;
  supportCount: number;
  contradictionCount: number;
  confidence: number;
  status: SemanticPatternStatus;
}

export interface SemanticObservation {
  supports: boolean;
  audited: boolean;
}

export function smoothedOutcomeRate(wins:number,losses:number):number{
  const w=Math.max(0,Math.trunc(wins));
  const l=Math.max(0,Math.trunc(losses));
  return (w+1)/(w+l+2);
}

export function applySemanticObservation(
  pattern:SemanticPatternState,
  observation:SemanticObservation
):SemanticPatternState{
  if(!observation.audited)return {...pattern};
  const next={...pattern};
  if(observation.supports)next.supportCount+=1;
  else next.contradictionCount+=1;
  next.confidence=smoothedOutcomeRate(next.supportCount,next.contradictionCount);
  if(next.supportCount>=3&&next.confidence>=0.7)next.status="VERIFIED";
  else if(next.contradictionCount>=next.supportCount&&next.contradictionCount>=2)next.status="DISPUTED";
  else next.status="CANDIDATE";
  return next;
}
