export type OrchestrationAdoption =
  | "RUNTIME_AUTHORITY"
  | "PATTERN_SOURCE"
  | "REFERENCE_ONLY"
  | "DISCOVERY_ONLY";

export type OrchestrationPattern =
  | "HIERARCHICAL_AGENT_OWNERSHIP"
  | "EVENT_DRIVEN_FLOWS"
  | "DURABLE_STATE_GRAPH"
  | "HUMAN_IN_LOOP_INTERRUPTS"
  | "ROLE_BASED_CREWS"
  | "SEQUENTIAL_PARALLEL_SWARMS"
  | "MARKETING_SPECIALIST_CATALOG"
  | "APPROVAL_WORKFLOWS"
  | "DISTRIBUTED_AGENT_RUNTIME"
  | "TOOL_ENABLED_AGENT"
  | "MEMORY_ENABLED_AGENT"
  | "MULTI_AGENT_HANDOFF";

export interface OrchestrationReference {
  id:
    | "ARIA_GLOBAL_CORE"
    | "SWARMS"
    | "MARKETING_SWARM_TEMPLATE"
    | "MULTI_AGENT_MARKETING_COURSE"
    | "CREWAI"
    | "AUTOGEN"
    | "LANGGRAPH"
    | "SUPERAGI"
    | "AI_AGENTS_101"
    | "AI_MARKETING_TOPIC"
    | "CLAUDE_MARKETING_SKILLS_ECOSYSTEM";
  label: string;
  source: string;
  license: string | null;
  adoption: OrchestrationAdoption;
  patterns: OrchestrationPattern[];
  notes: string[];
}

export const ORCHESTRATION_REFERENCES: OrchestrationReference[] = [
  {
    id: "ARIA_GLOBAL_CORE",
    label: "AriaOS Global Decision Core",
    source: "internal://packages/sniper/src/globalCore.ts",
    license: null,
    adoption: "RUNTIME_AUTHORITY",
    patterns: [
      "HIERARCHICAL_AGENT_OWNERSHIP",
      "EVENT_DRIVEN_FLOWS",
      "DURABLE_STATE_GRAPH",
      "HUMAN_IN_LOOP_INTERRUPTS",
      "MULTI_AGENT_HANDOFF"
    ],
    notes: [
      "Only runtime authority for portfolio orchestration.",
      "Cloudflare/D1 remains canonical control plane and source of truth."
    ]
  },
  {
    id: "SWARMS",
    label: "Swarms",
    source: "https://github.com/kyegomez/swarms",
    license: "Apache-2.0",
    adoption: "PATTERN_SOURCE",
    patterns: [
      "HIERARCHICAL_AGENT_OWNERSHIP",
      "SEQUENTIAL_PARALLEL_SWARMS",
      "MULTI_AGENT_HANDOFF"
    ],
    notes: [
      "Upstream describes sequential, concurrent and hierarchical multi-agent architectures.",
      "Do not install as a second orchestration authority; extract compatible patterns."
    ]
  },
  {
    id: "MARKETING_SWARM_TEMPLATE",
    label: "Marketing Swarm Template",
    source: "https://github.com/The-Swarm-Corporation/Marketing-Swarm-Template",
    license: "MIT",
    adoption: "PATTERN_SOURCE",
    patterns: [
      "MARKETING_SPECIALIST_CATALOG",
      "ROLE_BASED_CREWS"
    ],
    notes: [
      "Upstream exposes 10+ platform-specific marketing agents in agents.yaml.",
      "Use as inspiration for specialist charters and skills, not as a runtime dependency."
    ]
  },
  {
    id: "MULTI_AGENT_MARKETING_COURSE",
    label: "Multi-Agent Marketing Course",
    source: "https://github.com/The-Swarm-Corporation/Multi-Agent-Marketing-Course",
    license: "MIT",
    adoption: "PATTERN_SOURCE",
    patterns: [
      "SEQUENTIAL_PARALLEL_SWARMS",
      "APPROVAL_WORKFLOWS",
      "MARKETING_SPECIALIST_CATALOG"
    ],
    notes: [
      "Educational/operational source for sequential, parallel and approval-oriented marketing flows.",
      "Do not treat course material as production runtime."
    ]
  },
  {
    id: "CREWAI",
    label: "CrewAI",
    source: "https://github.com/crewAIInc/crewAI",
    license: "MIT",
    adoption: "PATTERN_SOURCE",
    patterns: [
      "ROLE_BASED_CREWS",
      "EVENT_DRIVEN_FLOWS",
      "HIERARCHICAL_AGENT_OWNERSHIP"
    ],
    notes: [
      "Upstream distinguishes autonomous Crews from precise event-driven Flows.",
      "Adopt role/flow concepts where they improve ownership and observability."
    ]
  },
  {
    id: "AUTOGEN",
    label: "Microsoft AutoGen",
    source: "https://github.com/microsoft/autogen",
    license: "SEE_UPSTREAM",
    adoption: "REFERENCE_ONLY",
    patterns: [
      "DISTRIBUTED_AGENT_RUNTIME",
      "MULTI_AGENT_HANDOFF",
      "TOOL_ENABLED_AGENT"
    ],
    notes: [
      "Upstream README marks AutoGen maintenance mode.",
      "Microsoft recommends Microsoft Agent Framework for new projects.",
      "Do not add AutoGen as a new runtime dependency."
    ]
  },
  {
    id: "LANGGRAPH",
    label: "LangGraph",
    source: "https://github.com/langchain-ai/langgraph",
    license: "MIT",
    adoption: "PATTERN_SOURCE",
    patterns: [
      "DURABLE_STATE_GRAPH",
      "HUMAN_IN_LOOP_INTERRUPTS",
      "MEMORY_ENABLED_AGENT"
    ],
    notes: [
      "Upstream emphasizes durable execution, human-in-the-loop and memory.",
      "Use these as design references; D1/Workflows remain canonical implementation."
    ]
  },
  {
    id: "SUPERAGI",
    label: "SuperAGI",
    source: "https://github.com/TransformerOptimus/SuperAGI",
    license: "MIT",
    adoption: "REFERENCE_ONLY",
    patterns: [
      "TOOL_ENABLED_AGENT",
      "MULTI_AGENT_HANDOFF"
    ],
    notes: [
      "Useful as historical/productivity-agent reference.",
      "No runtime adoption without a separate current-maintenance and fit review."
    ]
  },
  {
    id: "AI_AGENTS_101",
    label: "AI Agents 101",
    source: "https://github.com/nluninja/ai-agents-101",
    license: "MIT",
    adoption: "REFERENCE_ONLY",
    patterns: [
      "MEMORY_ENABLED_AGENT",
      "MULTI_AGENT_HANDOFF",
      "TOOL_ENABLED_AGENT"
    ],
    notes: [
      "Upstream is an n8n tutorial series rather than a general orchestration framework.",
      "Use only for simple workflow examples and handoff patterns."
    ]
  },
  {
    id: "AI_MARKETING_TOPIC",
    label: "GitHub ai-marketing topic",
    source: "https://github.com/topics/ai-marketing",
    license: null,
    adoption: "DISCOVERY_ONLY",
    patterns: [],
    notes: [
      "This is a discovery index, not a single project.",
      "Every candidate found through it requires independent source/license/runtime verification."
    ]
  },
  {
    id: "CLAUDE_MARKETING_SKILLS_ECOSYSTEM",
    label: "Marketing skills ecosystem",
    source: "discovery://marketing-agent-skills",
    license: null,
    adoption: "DISCOVERY_ONLY",
    patterns: [
      "MARKETING_SPECIALIST_CATALOG"
    ],
    notes: [
      "Skills are evaluated individually and version-pinned before admission.",
      "No topic page or ecosystem label grants execution authority."
    ]
  }
];

export function getAdoptedPatterns(): OrchestrationPattern[] {
  const patterns = new Set<OrchestrationPattern>();
  for (const ref of ORCHESTRATION_REFERENCES) {
    if (ref.adoption === "PATTERN_SOURCE" || ref.adoption === "RUNTIME_AUTHORITY") {
      for (const pattern of ref.patterns) patterns.add(pattern);
    }
  }
  return [...patterns].sort();
}

export function assertSingleRuntimeAuthority(refs: OrchestrationReference[]): void {
  const runtime = refs.filter(x => x.adoption === "RUNTIME_AUTHORITY");
  if (runtime.length !== 1 || runtime[0]?.id !== "ARIA_GLOBAL_CORE") {
    throw new Error("ORCHESTRATION_RUNTIME_AUTHORITY_CONFLICT");
  }
}
