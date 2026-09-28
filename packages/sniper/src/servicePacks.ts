export type ServicePackId =
  | "OPENINGS_COMMERCE"
  | "REAL_ESTATE_IMMERSIVE"
  | "LOCAL_COMMERCE_DIGITAL"
  | "SERVICE_BUSINESS_CRM";

export type ServiceDeliverable =
  | "HIGH_CONVERSION_WEBSITE"
  | "ECOMMERCE_CATALOG"
  | "VISUAL_CONFIGURATOR"
  | "QUOTE_TO_WHATSAPP"
  | "CRM_PIPELINE"
  | "WHATSAPP_AUTOMATION"
  | "ANALYTICS"
  | "PAYMENT_LINK_FLOW"
  | "EMBEDDABLE_3D_TOUR"
  | "PROPERTY_MEDIA_PIPELINE"
  | "LEAD_CAPTURE"
  | "SEO_LOCAL";

export interface VerticalServicePack {
  id: ServicePackId;
  label: string;
  verticalSignals: string[];
  deliverables: ServiceDeliverable[];
  demoProof: string[];
  constraints: string[];
  referenceTechniques: string[];
}

export interface VerticalContext {
  category: string;
  hasWebsite: boolean;
  websiteQuality: number | null;
  hasEcommerce: boolean;
  has3d: boolean;
}

export const SERVICE_PACKS: VerticalServicePack[] = [
  {
    id: "OPENINGS_COMMERCE",
    label: "Aberturas / materiales / interior commerce",
    verticalSignals: ["aberturas", "ventanas", "puertas", "cerramientos", "revestimientos", "materiales de construcción"],
    deliverables: ["HIGH_CONVERSION_WEBSITE", "ECOMMERCE_CATALOG", "VISUAL_CONFIGURATOR", "QUOTE_TO_WHATSAPP", "CRM_PIPELINE", "ANALYTICS"],
    demoProof: [
      "interactive room/material preview",
      "product comparison by size/material/finish",
      "quote flow that preserves selected configuration",
      "mobile-first catalog with clear price-or-quote CTA"
    ],
    constraints: [
      "NO_FAKE_PRODUCT_SPECS",
      "NO_INVENTED_STOCK",
      "NO_INVENTED_PRICE",
      "DEMO_MUST_BE_PRIVATE_UNTIL_AUTHORIZED"
    ],
    referenceTechniques: [
      "browser-native 3D/GLTF configurator",
      "material swapping and daylight preview",
      "structured catalog to quote funnel"
    ]
  },
  {
    id: "REAL_ESTATE_IMMERSIVE",
    label: "Real estate immersive property media",
    verticalSignals: ["inmobiliaria", "real estate", "propiedades", "desarrolladora", "arquitectura"],
    deliverables: ["EMBEDDABLE_3D_TOUR", "PROPERTY_MEDIA_PIPELINE", "LEAD_CAPTURE", "CRM_PIPELINE", "ANALYTICS"],
    demoProof: [
      "photo-to-reviewable 3D scene prototype",
      "walkable or orbitable property preview",
      "iframe-ready hosted viewer shell",
      "lead CTA attached to the viewed property"
    ],
    constraints: [
      "NO_MEASURED_DIGITAL_TWIN_CLAIM_FROM_PHOTOS_ALONE",
      "NO_PROPERTY_DIMENSION_INVENTION",
      "NO_PUBLICATION_WITHOUT_RIGHTS",
      "HEAVY_3D_COMPUTE_OUTSIDE_CLOUDFLARE_WORKER"
    ],
    referenceTechniques: [
      "VIGA-style generate-render-verify loop",
      "Unreal Home Wizard-style evidence and photo-match QA",
      "web viewer export for lightweight embedding"
    ]
  },
  {
    id: "LOCAL_COMMERCE_DIGITAL",
    label: "Local commerce digital conversion",
    verticalSignals: ["comercio", "retail", "tienda", "gastronomía", "farmacia", "ferretería"],
    deliverables: ["HIGH_CONVERSION_WEBSITE", "ECOMMERCE_CATALOG", "QUOTE_TO_WHATSAPP", "WHATSAPP_AUTOMATION", "PAYMENT_LINK_FLOW", "ANALYTICS", "SEO_LOCAL"],
    demoProof: [
      "before/after mobile conversion flow",
      "one-tap contact or checkout path",
      "catalog readability improvement",
      "measurable event instrumentation"
    ],
    constraints: ["NO_FAKE_UPLIFT", "NO_UNVERIFIED_INVENTORY", "NO_UNAUTHORIZED_PUBLISH"],
    referenceTechniques: ["responsive web", "structured catalog", "conversion instrumentation"]
  },
  {
    id: "SERVICE_BUSINESS_CRM",
    label: "Service business CRM and automation",
    verticalSignals: ["servicios", "estudio", "consultora", "clínica", "taller", "profesional"],
    deliverables: ["LEAD_CAPTURE", "CRM_PIPELINE", "WHATSAPP_AUTOMATION", "ANALYTICS"],
    demoProof: [
      "lead intake to CRM pipeline",
      "automated follow-up preview",
      "missed-opportunity dashboard"
    ],
    constraints: ["NO_UNAUTHORIZED_MESSAGE_SEND", "NO_SENSITIVE_DATA_IN_DEMO"],
    referenceTechniques: ["CRM workflow", "message templates", "pipeline analytics"]
  }
];

function normalize(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

export function recommendVerticalPack(context: VerticalContext): VerticalServicePack {
  const category = normalize(context.category);
  const direct = SERVICE_PACKS.find(pack => pack.verticalSignals.some(signal => category.includes(normalize(signal)) || normalize(signal).includes(category)));
  if (direct) return structuredClone(direct);

  if (context.hasWebsite && context.websiteQuality !== null && context.websiteQuality < 45) {
    return structuredClone(SERVICE_PACKS.find(x => x.id === "LOCAL_COMMERCE_DIGITAL")!);
  }
  if (!context.hasWebsite || !context.hasEcommerce) {
    return structuredClone(SERVICE_PACKS.find(x => x.id === "LOCAL_COMMERCE_DIGITAL")!);
  }
  return structuredClone(SERVICE_PACKS.find(x => x.id === "SERVICE_BUSINESS_CRM")!);
}
