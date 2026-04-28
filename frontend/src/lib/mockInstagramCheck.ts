import type {
  InstagramCheckSavePayload,
  InstagramClaim,
  InstagramEvaluatedTip,
  InstagramPostCheck,
  TaxPrepItem,
} from "@/types/instagramCheck";

const checks = new Map<string, InstagramPostCheck>();
const prepItems = new Map<string, TaxPrepItem[]>();

function now() {
  return new Date();
}

function cloneCheck(check: InstagramPostCheck): InstagramPostCheck {
  return {
    ...check,
    images: check.images.map((image) => ({ ...image })),
    claims: check.claims.map((claim) => ({
      ...claim,
      followUpQuestions: claim.followUpQuestions.map((question) => ({ ...question })),
    })),
    evaluatedTips: check.evaluatedTips
      ? check.evaluatedTips.map((tip) => ({
          ...tip,
          requiredEvidence: [...tip.requiredEvidence],
          sources: tip.sources.map((source) => ({ ...source })),
        }))
      : check.evaluatedTips,
    updatedAt: new Date(check.updatedAt),
  };
}

function clonePrepItems(items: TaxPrepItem[]): TaxPrepItem[] {
  return items.map((item) => ({
    ...item,
    requiredEvidence: [...item.requiredEvidence],
    createdAt: new Date(item.createdAt),
    updatedAt: new Date(item.updatedAt),
  }));
}

function mockClaim(text: string, category: InstagramClaim["category"], bucket: InstagramClaim["returnBucket"]): InstagramClaim {
  return {
    id: crypto.randomUUID(),
    rawText: text,
    editedText: text,
    category,
    returnBucket: bucket,
    status: "active",
    selectedForImport: false,
    followUpQuestions: [
      {
        id: crypto.randomUUID(),
        prompt: "Wie genau passt dieser Tipp auf deinen Fall?",
        answer: null,
      },
      {
        id: crypto.randomUUID(),
        prompt: "Welche Nachweise oder Beträge liegen dazu vor?",
        answer: null,
      },
    ],
  };
}

function buildClaims(images: File[]): InstagramClaim[] {
  if (images.length > 1) {
    return [
      mockClaim("Homeoffice-Pauschale aus dem Post pruefen", "homeoffice", "anlage_n"),
      mockClaim("Laptop und Monitor als Arbeitsmittel pruefen", "arbeitsmittel", "anlage_n"),
    ];
  }

  return [
    mockClaim("Handwerkerleistungen aus dem Post pruefen", "haushaltsnahe_dienstleistungen", "haushaltsnahe_dienstleistungen"),
  ];
}

export async function analyzeMockInstagramCheck(
  sessionId: string,
  images: File[],
): Promise<InstagramPostCheck> {
  const nextCheck: InstagramPostCheck = {
    sessionId,
    status: "draft",
    images: images.map((image) => ({
      id: crypto.randomUUID(),
      originalFilename: image.name,
      storedPath: `uploads/instagram-check/${sessionId}/${image.name}`,
      contentType: image.type || "image/png",
      sizeBytes: image.size,
    })),
    claims: buildClaims(images),
    evaluatedTips: null,
    updatedAt: now(),
  };
  checks.set(sessionId, nextCheck);
  return cloneCheck(nextCheck);
}

export async function fetchMockInstagramCheck(
  sessionId: string,
): Promise<InstagramPostCheck | null> {
  const value = checks.get(sessionId);
  return value ? cloneCheck(value) : null;
}

export async function saveMockInstagramCheck(
  sessionId: string,
  payload: InstagramCheckSavePayload,
): Promise<InstagramPostCheck> {
  const existing = checks.get(sessionId);
  const nextCheck: InstagramPostCheck = {
    sessionId,
    status: "draft",
    images: existing?.images ?? [],
    claims: payload.claims.map((claim) => ({
      ...claim,
      followUpQuestions: claim.followUpQuestions.map((question) => ({ ...question })),
    })),
    evaluatedTips: null,
    updatedAt: now(),
  };
  checks.set(sessionId, nextCheck);
  return cloneCheck(nextCheck);
}

export async function evaluateMockInstagramCheck(
  sessionId: string,
): Promise<InstagramPostCheck> {
  const existing = checks.get(sessionId);
  if (!existing) {
    throw new Error("Mock-Instagram-Check nicht gefunden");
  }

  const evaluatedTips: InstagramEvaluatedTip[] = existing.claims
    .filter((claim) => claim.status === "active")
    .map((claim) => ({
      claimId: claim.id,
      title: claim.editedText,
      normalizedTip: claim.editedText,
      category: claim.category,
      returnBucket: claim.returnBucket,
      trafficLight:
        claim.followUpQuestions.every((question) => question.answer?.trim())
          ? "green"
          : "yellow",
      explanation:
        claim.followUpQuestions.every((question) => question.answer?.trim())
          ? "Der Mock-Tipp wirkt nach den Antworten grundsaetzlich nutzbar."
          : "Im Mock fehlen noch Antworten oder Nachweise fuer eine gruene Freigabe.",
      estimatedSavingEur:
        claim.category === "homeoffice"
          ? 240
          : claim.category === "arbeitsmittel"
            ? 180
            : claim.category === "haushaltsnahe_dienstleistungen"
              ? 320
              : null,
      requiredEvidence: ["Belege oder Nachweise zum Tipp"],
      sources: [
        {
          law: "EStG",
          paragraph: "§ 9",
          section: "",
          text: "Mock-Quelle fuer die strukturierte Bewertung.",
        },
      ],
    }));

  const adopted = evaluatedTips.filter(
    (tip) =>
      tip.trafficLight === "green" &&
      existing.claims.find((claim) => claim.id === tip.claimId)?.selectedForImport,
  );
  if (adopted.length > 0) {
    const current = prepItems.get(sessionId) ?? [];
    const merged = [...current];
    for (const tip of adopted) {
      if (merged.some((item) => item.sourceClaimId === tip.claimId)) {
        continue;
      }
      merged.unshift({
        id: crypto.randomUUID(),
        sessionId,
        source: "instagram_post",
        sourceClaimId: tip.claimId,
        title: tip.title,
        category: tip.category,
        returnBucket: tip.returnBucket,
        estimatedSavingEur: tip.estimatedSavingEur,
        riskLevel: "low",
        requiredEvidence: [...tip.requiredEvidence],
        summary: tip.explanation,
        status: "confirmed",
        createdAt: now(),
        updatedAt: now(),
      });
    }
    prepItems.set(sessionId, merged);
  }

  const nextCheck: InstagramPostCheck = {
    ...existing,
    status: "evaluated",
    evaluatedTips,
    updatedAt: now(),
  };
  checks.set(sessionId, nextCheck);
  return cloneCheck(nextCheck);
}

export async function fetchMockTaxPrepItems(sessionId: string): Promise<TaxPrepItem[]> {
  return clonePrepItems(prepItems.get(sessionId) ?? []);
}
