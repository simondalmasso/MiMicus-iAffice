export type SemanticOutcome = "REPLIED" | "MEETING" | "WON" | "LOST" | "UNKNOWN";

export interface SemanticEpisode {
  episodeId: string;
  tacticId: string;
  outcome: SemanticOutcome;
  audited: boolean;
  evidenceRefs: string[];
  category: string;
  locality: string;
  createdAt: string;
}

export interface SemanticPatternCandidate {
  scopeKey: string;
  statement: string;
  confidence: number;
  evidenceRefs: string[];
  supportCount: number;
  contradictionCount: number;
  status: "ACTIVE" | "CONTESTED" | "STALE";
  latestEvidenceAt: string;
}

const SUPPORT = new Set<SemanticOutcome>(["REPLIED","MEETING","WON"]);

function ageDays(then:string,now:string):number {
  const delta=Date.parse(now)-Date.parse(then);
  return Number.isFinite(delta)?Math.max(0,delta/86400000):365;
}

export function buildSemanticPatterns(episodes:SemanticEpisode[],now=new Date().toISOString()):SemanticPatternCandidate[] {
  const eligible=episodes.filter(x=>x.audited&&x.evidenceRefs.length>0&&x.outcome!=="UNKNOWN");
  const groups=new Map<string,SemanticEpisode[]>();
  for(const episode of eligible){
    const key=`category=${episode.category}|locality=${episode.locality}|tactic=${episode.tacticId}`;
    const rows=groups.get(key)??[];
    rows.push(episode);
    groups.set(key,rows);
  }
  const patterns:SemanticPatternCandidate[]=[];
  for(const [scopeKey,rows] of groups){
    const support=rows.filter(x=>SUPPORT.has(x.outcome));
    const contradictions=rows.filter(x=>x.outcome==="LOST");
    if(support.length<1) continue;
    const latest=rows.map(x=>x.createdAt).sort().at(-1)!;
    const freshness=Math.exp(-ageDays(latest,now)/120);
    const evidenceStrength=(support.length+1)/(support.length+contradictions.length+2);
    const confidence=Math.max(0,Math.min(1,evidenceStrength*freshness));
    const stale=ageDays(latest,now)>180;
    const contested=contradictions.length>=support.length;
    patterns.push({
      scopeKey,
      statement:`${rows[0]!.tacticId} has audited positive evidence for ${rows[0]!.category} in ${rows[0]!.locality}`,
      confidence,
      evidenceRefs:[...new Set(rows.flatMap(x=>x.evidenceRefs))].sort(),
      supportCount:support.length,
      contradictionCount:contradictions.length,
      status:stale?"STALE":contested?"CONTESTED":"ACTIVE",
      latestEvidenceAt:latest
    });
  }
  return patterns.sort((a,b)=>b.confidence-a.confidence||a.scopeKey.localeCompare(b.scopeKey));
}
