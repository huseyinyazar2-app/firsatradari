"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Source = {
  key: string;
  owner: string;
  evidence_family_key: string;
  independence_status: string;
  policy_status: string;
  policy_version: string | null;
  storage_permission: string;
  retention_days: number | null;
  enabled: boolean;
};
type SourcePolicyDraft = {
  version: string;
  termsUrl: string;
  retentionDays: string;
  independenceRationale: string;
  independenceEvidence: string;
};
type Health = {
  source_key: string;
  last_success_at: string | null;
  open_quality_event_count: number;
  incomplete_collection_count: number;
};
type Cluster = {
  id: string;
  label: string;
  status: string;
  signature: string[];
  document_count: number;
  entity_count: number;
  source_count: number;
  cohesion_mean: string;
};
type Opportunity = {
  id: string;
  origin_cluster_id: string;
  status: string;
};
type Version = {
  id: string;
  opportunity_id: string;
  version_number: number;
  title: string;
  ontology: Record<string, string>;
  evidence_level: string;
};
type ScoreRun = {
  id: string;
  as_of: string;
  status: string;
  rankable_count: number;
};
type Score = {
  opportunity_version_id: string;
  potential_score: string;
  actionability_score: string;
  confidence_score: string;
  uncertainty: string;
  total_score: string | null;
  status: string;
  components: { blockers?: string[] };
};
type OperationsSummary = {
  open_alert_count: number;
  critical_alert_count: number;
  warning_alert_count: number;
  daily_cost_usd: string;
  monthly_cost_usd: string;
  daily_budget_usd: string;
  monthly_budget_usd: string;
  budget_status: string;
  generated_at: string;
};
type OperationalAlert = {
  id: string;
  category: string;
  severity: string;
  message: string;
  last_detected_at: string;
};
type ScheduledJob = {
  id: string;
  key: string;
  job_type: string;
  status: string;
  interval_minutes: number;
  payload: Record<string, unknown>;
  next_run_at: string;
  last_run_at: string | null;
  consecutive_failure_count: number;
};
type ScheduledJobRun = {
  id: string;
  scheduled_job_id: string;
  status: string;
  error_message: string | null;
  started_at: string;
};
type TestSearchResult = {
  query: string;
  ingestion: {
    status: string;
    raw_item_count: number;
    error_count: number;
  };
  normalization: {
    input_count: number;
    success_count: number;
    error_count: number;
  };
  repository_hydration: {
    discovered_count: number;
    requested_count: number;
    normalized_count: number;
    unresolved_count: number;
    error_count: number;
  };
  extraction: {
    input_count: number;
    evidence_count: number;
    error_count: number;
  };
  clustering: {
    cluster_count: number;
    eligible_count: number;
  };
  cluster_metrics: {
    metric_count: number;
    error_count: number;
  };
};
type Backtest = {
  id: string;
  cutoff_at: string;
  outcome_window_days: number;
  status: string;
  prediction_count: number;
  evaluated_count: number;
  positive_count: number;
  brier_score: string | null;
  baseline_brier_score: string | null;
};
type Review = {
  id: string;
  decision: string;
  reviewer: string;
  notes: string;
  created_at: string;
};
type ResearchRun = {
  id: string;
  status: string;
  research_tier: string;
  findings: {
    knowns?: Array<{
      component_key: string;
      statement: string;
      evidence_level: string;
    }>;
    unknowns?: string[];
    risk_flags?: string[];
    question_assessments?: Array<{
      question: string;
      status: string;
      supporting_components: string[];
      caveat: string;
    }>;
    recommended_next_test?: string;
  };
  evidence_snapshot: {
    components?: Array<{
      component_key: string;
      statement: string;
      evidence_level: string;
      evidence: Array<{
        evidence_id: string;
        direction: string;
        excerpt: string;
        confidence: string;
        source_name: string | null;
        source_url: string | null;
        source_license: string | null;
        attribution_required: boolean;
      }>;
      commercial_evidence: Array<{
        outcome_id: string;
        direction: string;
        outcome_type: string;
        amount: string | null;
        currency: string | null;
      }>;
    }>;
  };
  blockers: string[];
  started_at: string;
};
type ScoreHistory = {
  run_id: string;
  as_of: string;
  potential_score: string;
  actionability_score: string;
  confidence_score: string;
  uncertainty: string;
  total_score: string | null;
  status: string;
};
type OpportunityExport = {
  id: string;
  status: string;
  destination: string;
  payload: Record<string, unknown>;
  created_at: string;
};
type ResearchReport = {
  period: string;
  period_start: string;
  period_end: string;
  new_opportunity_count: number;
  new_problem_cluster_count: number;
  latest_score_run_id: string | null;
  rankable_count: number;
  verified_commercial_outcome_count: number;
  open_alert_count: number;
  critical_alert_count: number;
  cost_by_currency: Record<string, string>;
  top_opportunities: Array<{
    opportunity_version_id: string;
    title: string;
    total_score: string | null;
    potential_score: string;
    actionability_score: string;
    confidence_score: string;
    uncertainty: string;
    status: string;
  }>;
};
type ValidationOutcome = {
  id: string;
  outcome_type: string;
  direction: string;
  amount: string | null;
  currency: string | null;
  verification_status: string;
  occurred_at: string;
};
type ValidationExperiment = {
  id: string;
  cluster_id: string;
  opportunity_version_id: string | null;
  experiment_type: string;
  protocol_key: string;
  cohort: string;
  target_segment: string;
  hypothesis: string;
  status: string;
  started_at: string;
  outcomes: ValidationOutcome[];
};
type Vertical = {
  id: string;
  key: string;
  version: string;
  name: string;
  status: string;
};
type ResearchProfile = {
  id: string;
  vertical_definition_id: string;
  key: string;
  version: string;
  name: string;
  constraints: Record<string, string | number>;
  exclusions: Record<string, string[]>;
  preferences: Record<string, string[]>;
};
type ProfileEvaluation = {
  id: string;
  research_profile_id: string;
  eligible: boolean;
  blocker_codes: string[];
  unknown_fields: string[];
  fit_score: string | null;
  data_coverage: string;
};
type DetailData = {
  reviews: Review[];
  researchRuns: ResearchRun[];
  scoreHistory: ScoreHistory[];
  exports: OpportunityExport[];
  profileEvaluations: ProfileEvaluation[];
};
type DashboardData = {
  sources: Source[];
  health: Record<string, Health>;
  clusters: Cluster[];
  opportunities: Opportunity[];
  versions: Version[];
  scoreRun: ScoreRun | null;
  scores: Score[];
  operations: OperationsSummary | null;
  alerts: OperationalAlert[];
  scheduledJobs: ScheduledJob[];
  scheduledJobRuns: ScheduledJobRun[];
  backtests: Backtest[];
  weeklyReport: ResearchReport | null;
  monthlyReport: ResearchReport | null;
  verticals: Vertical[];
  profiles: ResearchProfile[];
};

const EMPTY: DashboardData = {
  sources: [],
  health: {},
  clusters: [],
  opportunities: [],
  versions: [],
  scoreRun: null,
  scores: [],
  operations: null,
  alerts: [],
  scheduledJobs: [],
  scheduledJobRuns: [],
  backtests: [],
  weeklyReport: null,
  monthlyReport: null,
  verticals: [],
  profiles: [],
};
const DEFAULT_API_URL =
  import.meta.env.VITE_FIRSAT_API_URL ?? "http://127.0.0.1:8000";
const EMPTY_DETAIL: DetailData = {
  reviews: [],
  researchRuns: [],
  scoreHistory: [],
  exports: [],
  profileEvaluations: [],
};

function initialApiUrl() {
  if (typeof window === "undefined") return DEFAULT_API_URL;
  return window.localStorage.getItem("firsat-radari-api") ?? DEFAULT_API_URL;
}

function initialApiKey() {
  if (typeof window === "undefined") return "";
  return window.sessionStorage.getItem("firsat-radari-api-key") ?? "";
}

const LABELS: Record<string, string> = {
  customer: "Müşteri",
  job: "Yapılacak iş",
  problem: "Problem",
  context: "Bağlam",
  current_alternative: "Mevcut alternatif",
  solution_gap: "Çözüm açığı",
  payment_reason: "Ödeme nedeni",
  entry_product: "İlk ürün girişi",
  distribution_path: "Dağıtım yolu",
  expansion_path: "Genişleme yolu",
};

export function ResearchDashboard() {
  const [tab, setTab] = useState<
    "search" | "radar" | "problems" | "sources" | "backtests" | "operations"
    | "reports" | "validation" | "profile"
  >("search");
  const [apiUrl, setApiUrl] = useState(initialApiUrl);
  const [draftUrl, setDraftUrl] = useState(initialApiUrl);
  const [apiKey, setApiKey] = useState(initialApiKey);
  const [draftApiKey, setDraftApiKey] = useState(initialApiKey);
  const [data, setData] = useState(EMPTY);
  const [detail, setDetail] = useState(EMPTY_DETAIL);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [reviewer, setReviewer] = useState("research-owner");
  const [decision, setDecision] = useState("investigate");
  const [reviewNotes, setReviewNotes] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [validation, setValidation] = useState<ValidationExperiment[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationSegment, setValidationSegment] = useState("");
  const [validationHypothesis, setValidationHypothesis] = useState("");
  const [validationParticipant, setValidationParticipant] = useState("");
  const [validationNotes, setValidationNotes] = useState("");
  const [validationExperimentType, setValidationExperimentType] =
    useState("customer_interview");
  const [validationCohort, setValidationCohort] = useState("radar");
  const [validationOutcomeType, setValidationOutcomeType] =
    useState("qualified_interview");
  const [validationAmount, setValidationAmount] = useState("");
  const [validationEvidence, setValidationEvidence] = useState("");
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [operationsError, setOperationsError] = useState<string | null>(null);
  const [testSearchError, setTestSearchError] = useState<string | null>(null);
  const [testSearchQuery, setTestSearchQuery] = useState("workflow automation");
  const [testSearchResult, setTestSearchResult] =
    useState<TestSearchResult | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [capitalBudget, setCapitalBudget] = useState("10000");
  const [maxBuildWeeks, setMaxBuildWeeks] = useState("12");
  const [maxTeamSize, setMaxTeamSize] = useState("2");
  const [observedCategory, setObservedCategory] = useState("saas");
  const [observedCost, setObservedCost] = useState("");
  const [observedBuildWeeks, setObservedBuildWeeks] = useState("");
  const [observedTeamSize, setObservedTeamSize] = useState("");
  const [observedSalesMotion, setObservedSalesMotion] =
    useState("self_service");
  const [selectedProfileId, setSelectedProfileId] = useState("");

  const apiRequest = useCallback(
    async <T,>(path: string, init?: RequestInit): Promise<T> => {
      const headers = new Headers(init?.headers);
      headers.set("Accept", "application/json");
      if (init?.body) headers.set("Content-Type", "application/json");
      if (apiKey) headers.set("X-Firsat-Api-Key", apiKey);
      if (reviewer.trim()) headers.set("X-Firsat-Actor", reviewer.trim());
      const response = await fetch(`${apiUrl}${path}`, { ...init, headers });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(payload?.detail ?? `${path}: ${response.status}`);
      }
      return response.json() as Promise<T>;
    },
    [apiKey, apiUrl, reviewer],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await apiRequest("/health");
      const [
        sources,
        clusters,
        opportunities,
        versions,
        scoreRuns,
        operations,
        alerts,
        scheduledJobs,
        scheduledJobRuns,
        backtests,
        weeklyReport,
        monthlyReport,
        verticals,
        profiles,
      ] = await Promise.all([
        apiRequest<Source[]>("/sources"),
        apiRequest<Cluster[]>(
          "/problem-clusters?status=cross_entity_candidate&limit=100",
        ),
        apiRequest<Opportunity[]>("/opportunities?limit=100"),
        apiRequest<Version[]>("/opportunity-versions?current_only=true&limit=500"),
        apiRequest<ScoreRun[]>("/opportunity-score-runs?limit=20"),
        apiRequest<OperationsSummary>("/operations/summary"),
        apiRequest<OperationalAlert[]>(
          "/operational-alerts?status=open&limit=100",
        ),
        apiRequest<ScheduledJob[]>("/scheduled-jobs?limit=100"),
        apiRequest<ScheduledJobRun[]>("/scheduled-job-runs?limit=100"),
        apiRequest<Backtest[]>("/backtest-runs?limit=20"),
        apiRequest<ResearchReport>("/reports/weekly"),
        apiRequest<ResearchReport>("/reports/monthly"),
        apiRequest<Vertical[]>("/verticals"),
        apiRequest<ResearchProfile[]>("/research-profiles"),
      ]);
      const healthRows = await Promise.all(
        sources.map((source) =>
          apiRequest<Health>(`/sources/${source.key}/health`),
        ),
      );
      const scoreRun =
        scoreRuns.find((item) => item.status === "succeeded") ?? null;
      const scores = scoreRun
        ? await apiRequest<Score[]>(
            `/opportunity-score-runs/${scoreRun.id}/snapshots`,
          )
        : [];
      const next: DashboardData = {
        sources,
        clusters,
        opportunities,
        versions,
        health: Object.fromEntries(
          healthRows.map((item) => [item.source_key, item]),
        ),
        scoreRun,
        scores,
        operations,
        alerts,
        scheduledJobs,
        scheduledJobRuns,
        backtests,
        weeklyReport,
        monthlyReport,
        verticals,
        profiles,
      };
      setData(next);
      setSelectedId((current) => current ?? opportunities[0]?.id ?? null);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Araştırma verileri alınamadı.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const latestVersions = useMemo(() => {
    const result = new Map<string, Version>();
    data.versions.forEach((version) => {
      const previous = result.get(version.opportunity_id);
      if (!previous || version.version_number > previous.version_number) {
        result.set(version.opportunity_id, version);
      }
    });
    return result;
  }, [data.versions]);
  const scoreByVersion = useMemo(
    () =>
      new Map(data.scores.map((item) => [item.opportunity_version_id, item])),
    [data.scores],
  );
  const ranked = useMemo(
    () =>
      data.opportunities
        .map((opportunity) => {
          const version = latestVersions.get(opportunity.id);
          return {
            opportunity,
            version,
            score: version ? scoreByVersion.get(version.id) : undefined,
          };
        })
        .sort(
          (left, right) =>
            Number(right.score?.total_score ?? -1) -
            Number(left.score?.total_score ?? -1),
        ),
    [data.opportunities, latestVersions, scoreByVersion],
  );
  const selected = ranked.find((item) => item.opportunity.id === selectedId);
  const selectedProfile =
    data.profiles.find((item) => item.id === selectedProfileId) ??
    data.profiles[0];
  const openQuality = Object.values(data.health).reduce(
    (total, health) => total + health.open_quality_event_count,
    0,
  );

  const loadDetail = useCallback(
    async (versionId: string) => {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const [
          reviews,
          researchRuns,
          scoreHistory,
          exports,
          profileEvaluations,
        ] =
          await Promise.all([
            apiRequest<Review[]>(
              `/opportunity-versions/${versionId}/reviews`,
            ),
            apiRequest<ResearchRun[]>(
              `/opportunity-versions/${versionId}/research-runs`,
            ),
            apiRequest<ScoreHistory[]>(
              `/opportunity-versions/${versionId}/score-history`,
            ),
            apiRequest<OpportunityExport[]>(
              `/opportunity-exports?opportunity_version_id=${versionId}`,
            ),
            apiRequest<ProfileEvaluation[]>(
              `/opportunity-versions/${versionId}/profile-evaluations`,
            ),
          ]);
        setDetail({
          reviews,
          researchRuns,
          scoreHistory,
          exports,
          profileEvaluations,
        });
      } catch (reason) {
        setDetailError(
          reason instanceof Error
            ? reason.message
            : "Fırsat ayrıntıları alınamadı.",
        );
      } finally {
        setDetailLoading(false);
      }
    },
    [apiRequest],
  );

  const loadValidation = useCallback(async () => {
    setValidationLoading(true);
    setValidationError(null);
    try {
      const experiments = await apiRequest<ValidationExperiment[]>(
        "/commercial-validation-experiments?limit=100",
      );
      const outcomes = await Promise.all(
        experiments.map((experiment) =>
          apiRequest<ValidationOutcome[]>(
            `/commercial-validation-experiments/${experiment.id}/outcomes`,
          ),
        ),
      );
      setValidation(
        experiments.map((experiment, index) => ({
          ...experiment,
          outcomes: outcomes[index],
        })),
      );
    } catch (reason) {
      setValidationError(
        reason instanceof Error
          ? reason.message
          : "Doğrulama verileri alınamadı.",
      );
    } finally {
      setValidationLoading(false);
    }
  }, [apiRequest]);

  useEffect(() => {
    if (!selected?.version) return;
    const timer = window.setTimeout(
      () => void loadDetail(selected.version!.id),
      0,
    );
    return () => window.clearTimeout(timer);
  }, [loadDetail, selected?.version]);

  useEffect(() => {
    if (tab !== "validation") return;
    const timer = window.setTimeout(() => void loadValidation(), 0);
    return () => window.clearTimeout(timer);
  }, [loadValidation, tab]);

  const createResearch = async () => {
    if (!selected?.version) return;
    setActionBusy(true);
    setDetailError(null);
    try {
      await apiRequest(
        `/opportunity-versions/${selected.version.id}/research-runs`,
        {
          method: "POST",
          body: JSON.stringify({
            research_tier: "validation_ready",
            focus_questions: [],
            requested_by: reviewer,
          }),
        },
      );
      await loadDetail(selected.version.id);
    } catch (reason) {
      setDetailError(
        reason instanceof Error ? reason.message : "Araştırma başlatılamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const saveReview = async () => {
    if (!selected?.version || !reviewNotes.trim()) return;
    setActionBusy(true);
    setDetailError(null);
    try {
      await apiRequest(
        `/opportunity-versions/${selected.version.id}/reviews`,
        {
          method: "POST",
          body: JSON.stringify({
            decision,
            reviewer,
            notes: reviewNotes.trim(),
          }),
        },
      );
      setReviewNotes("");
      await loadDetail(selected.version.id);
    } catch (reason) {
      setDetailError(
        reason instanceof Error ? reason.message : "Karar kaydedilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const prepareExport = async () => {
    if (!selected?.version) return;
    const researchRun = detail.researchRuns.find(
      (item) => item.status === "succeeded",
    );
    if (!researchRun) return;
    setActionBusy(true);
    setDetailError(null);
    try {
      const result = await apiRequest<OpportunityExport>(
        "/opportunity-exports",
        {
          method: "POST",
          body: JSON.stringify({
            opportunity_version_id: selected.version.id,
            research_run_id: researchRun.id,
            destination: "sales-partner",
            idempotency_key: `sales-partner:${selected.version.id}:${researchRun.id}`,
            created_by: reviewer,
          }),
        },
      );
      downloadJson(
        result.payload,
        `firsat-${selected.version.id.slice(0, 8)}.json`,
      );
      await loadDetail(selected.version.id);
    } catch (reason) {
      setDetailError(
        reason instanceof Error ? reason.message : "Aktarım hazırlanamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const createValidationExperiment = async () => {
    if (
      !selected?.version ||
      !validationSegment.trim() ||
      !validationHypothesis.trim()
    ) {
      return;
    }
    setActionBusy(true);
    setValidationError(null);
    try {
      await apiRequest("/commercial-validation-experiments", {
        method: "POST",
        body: JSON.stringify({
          cluster_id: selected.opportunity.origin_cluster_id,
          opportunity_version_id: selected.version.id,
          external_key: `ui:${Date.now()}`,
          protocol_key: "internal-validation-v1",
          cohort: validationCohort,
          experiment_type: validationExperimentType,
          target_segment: validationSegment.trim(),
          hypothesis: validationHypothesis.trim(),
          status: "running",
          started_at: new Date().toISOString(),
          created_by: reviewer,
        }),
      });
      setValidationSegment("");
      setValidationHypothesis("");
      await loadValidation();
    } catch (reason) {
      setValidationError(
        reason instanceof Error ? reason.message : "Deney oluşturulamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const createValidationOutcome = async () => {
    const experiment = validation.find((item) => item.status === "running");
    const paymentOutcome = [
      "prepayment",
      "contract",
      "sale",
      "renewal",
    ].includes(validationOutcomeType);
    if (
      !experiment ||
      validationParticipant.trim().length < 3 ||
      !validationNotes.trim() ||
      (paymentOutcome &&
        (!validationAmount || !validationEvidence.trim()))
    ) {
      return;
    }
    setActionBusy(true);
    setValidationError(null);
    try {
      await apiRequest(
        `/commercial-validation-experiments/${experiment.id}/outcomes`,
        {
          method: "POST",
          body: JSON.stringify({
            idempotency_key: `ui:${Date.now()}`,
            participant_key: validationParticipant.trim(),
            outcome_type: validationOutcomeType,
            amount: validationAmount ? Number(validationAmount) : null,
            currency: validationAmount ? "USD" : null,
            evidence_reference: validationEvidence.trim() || null,
            notes: validationNotes.trim(),
            occurred_at: new Date().toISOString(),
            created_by: reviewer,
          }),
        },
      );
      setValidationParticipant("");
      setValidationNotes("");
      setValidationAmount("");
      setValidationEvidence("");
      await loadValidation();
    } catch (reason) {
      setValidationError(
        reason instanceof Error ? reason.message : "Sonuç kaydedilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const reviewValidationOutcome = async (outcomeId: string) => {
    setActionBusy(true);
    setValidationError(null);
    try {
      await apiRequest(`/commercial-outcomes/${outcomeId}/review`, {
        method: "PATCH",
        body: JSON.stringify({
          new_status: "verified",
          reviewer,
          notes: "Kaynak kanıtı araştırma masasında kontrol edildi.",
        }),
      });
      await loadValidation();
    } catch (reason) {
      setValidationError(
        reason instanceof Error ? reason.message : "Sonuç doğrulanamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const closeValidationExperiment = async (experimentId: string) => {
    setActionBusy(true);
    setValidationError(null);
    try {
      await apiRequest(
        `/commercial-validation-experiments/${experimentId}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            status: "completed",
            ended_at: new Date().toISOString(),
          }),
        },
      );
      await loadValidation();
    } catch (reason) {
      setValidationError(
        reason instanceof Error ? reason.message : "Deney kapatılamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const recordValidationOptOut = async () => {
    if (validationParticipant.trim().length < 3) return;
    setActionBusy(true);
    setValidationError(null);
    try {
      await apiRequest("/commercial-contact-preferences", {
        method: "POST",
        body: JSON.stringify({
          participant_key: validationParticipant.trim(),
          channel: "all",
          scope: "commercial-validation",
          status: "opt_out",
          evidence_reference: validationEvidence.trim() || null,
          recorded_by: reviewer,
        }),
      });
      setValidationParticipant("");
      setValidationEvidence("");
    } catch (reason) {
      setValidationError(
        reason instanceof Error ? reason.message : "İletişim tercihi kaydedilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const approveSource = async (
    sourceKey: string,
    draft: SourcePolicyDraft,
  ) => {
    setActionBusy(true);
    setSourceError(null);
    try {
      await apiRequest(`/sources/${sourceKey}/policies`, {
        method: "POST",
        body: JSON.stringify({
          version: draft.version.trim(),
          reviewer,
          commercial_use_status: "allowed",
          storage_permission: "allowed",
          derived_data_permission: "allowed",
          llm_processing_permission: "prohibited",
          retention_days: Number(draft.retentionDays),
          terms_url: draft.termsUrl.trim(),
          notes: "Araştırma panelinden açık kullanıcı onayıyla kaydedildi.",
        }),
      });
      await load();
    } catch (reason) {
      setSourceError(
        reason instanceof Error ? reason.message : "Kaynak politikası kaydedilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const setSourceEnabled = async (sourceKey: string, enabled: boolean) => {
    setActionBusy(true);
    setSourceError(null);
    try {
      await apiRequest(`/sources/${sourceKey}/enabled`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      });
      await load();
    } catch (reason) {
      setSourceError(
        reason instanceof Error ? reason.message : "Kaynak durumu değiştirilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const reviewSourceIndependence = async (
    sourceKey: string,
    draft: SourcePolicyDraft,
  ) => {
    setActionBusy(true);
    setSourceError(null);
    try {
      await apiRequest(`/sources/${sourceKey}/independence-reviews`, {
        method: "POST",
        body: JSON.stringify({
          version: draft.version.trim(),
          new_status: "independent",
          reviewer,
          rationale: draft.independenceRationale.trim(),
          evidence_references: [draft.independenceEvidence.trim()],
        }),
      });
      await load();
    } catch (reason) {
      setSourceError(
        reason instanceof Error ? reason.message : "Bağımsızlık incelemesi kaydedilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const createScheduledJob = async (
    jobType: "operations_evaluation" | "opportunity_scoring",
  ) => {
    const profile = selectedProfile;
    if (jobType === "opportunity_scoring" && !profile) {
      setOperationsError("Puanlama takvimi için önce bir araştırma profili oluşturun.");
      return;
    }
    setActionBusy(true);
    setOperationsError(null);
    try {
      await apiRequest("/scheduled-jobs", {
        method: "POST",
        body: JSON.stringify({
          key:
            jobType === "operations_evaluation"
              ? "operations-health-v1"
              : `profile-score-${profile.id}`,
          job_type: jobType,
          interval_minutes:
            jobType === "operations_evaluation" ? 60 : 1440,
          payload:
            jobType === "opportunity_scoring"
              ? { research_profile_id: profile.id }
              : {},
          next_run_at: new Date().toISOString(),
          created_by: reviewer,
        }),
      });
      await load();
    } catch (reason) {
      setOperationsError(
        reason instanceof Error ? reason.message : "Takvim oluşturulamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const setScheduledJobStatus = async (jobId: string, status: string) => {
    setActionBusy(true);
    setOperationsError(null);
    try {
      await apiRequest(`/scheduled-jobs/${jobId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await load();
    } catch (reason) {
      setOperationsError(
        reason instanceof Error ? reason.message : "Takvim durumu değiştirilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const runDueScheduledJobs = async () => {
    setActionBusy(true);
    setOperationsError(null);
    try {
      await apiRequest("/scheduler/run-due", {
        method: "POST",
        body: JSON.stringify({
          as_of: new Date().toISOString(),
          limit: 20,
        }),
      });
      await load();
    } catch (reason) {
      setOperationsError(
        reason instanceof Error ? reason.message : "Zamanı gelen işler çalıştırılamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const runTestSearch = async () => {
    const query = testSearchQuery.trim();
    if (query.length < 3) {
      setTestSearchError("Test araması en az 3 karakter olmalı.");
      return;
    }
    setActionBusy(true);
    setTestSearchError(null);
    setTestSearchResult(null);
    try {
      const result = await apiRequest<TestSearchResult>("/radar/test-search", {
        method: "POST",
        body: JSON.stringify({ query, limit: 20 }),
      });
      setTestSearchResult(result);
      await load();
    } catch (reason) {
      setTestSearchError(
        reason instanceof Error
          ? reason.message
          : "Test araması tamamlanamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const createResearchProfile = async () => {
    setActionBusy(true);
    setProfileError(null);
    try {
      let vertical = data.verticals[0];
      if (!vertical) {
        vertical = await apiRequest<Vertical>("/verticals", {
          method: "POST",
          body: JSON.stringify({
            key: "software",
            version: "1.0.0",
            name: "Yazılım",
            status: "active",
            config: {
              categories: [
                "mobile",
                "saas",
                "browser_extension",
                "ai_tool",
                "vertical_software",
                "api_data",
              ],
            },
            selection_rationale:
              "İlk sürümün veri ve problem kapsamı yazılım fırsatlarıdır.",
            created_by: reviewer,
          }),
        });
      }
      const version = new Date()
        .toISOString()
        .replace(/[-:TZ.]/g, "")
        .slice(0, 14);
      const createdProfile = await apiRequest<ResearchProfile>("/research-profiles", {
        method: "POST",
        body: JSON.stringify({
          vertical_definition_id: vertical.id,
          key: "founder-fit",
          version,
          name: "Kurucu uyumu",
          status: "active",
          constraints: {
            capital_budget: Number(capitalBudget),
            max_build_weeks: Number(maxBuildWeeks),
            max_team_size: Number(maxTeamSize),
          },
          exclusions: {
            categories: ["game"],
            terms: [],
            sales_motions: [],
          },
          preferences: {
            sales_motions: ["self_service", "product_led"],
          },
          created_by: reviewer,
        }),
      });
      setSelectedProfileId(createdProfile.id);
      await load();
    } catch (reason) {
      setProfileError(
        reason instanceof Error ? reason.message : "Araştırma profili oluşturulamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const evaluateSelectedProfile = async () => {
    const profile = selectedProfile;
    if (!profile || !selected?.version) return;
    const observed: Record<string, string | number> = {
      category: observedCategory.trim(),
      sales_motion: observedSalesMotion,
    };
    if (observedCost) observed.estimated_initial_cost = Number(observedCost);
    if (observedBuildWeeks) {
      observed.estimated_build_weeks = Number(observedBuildWeeks);
    }
    if (observedTeamSize) {
      observed.required_team_size = Number(observedTeamSize);
    }
    setActionBusy(true);
    setProfileError(null);
    try {
      await apiRequest(
        `/opportunity-versions/${selected.version.id}/profile-evaluations`,
        {
          method: "POST",
          body: JSON.stringify({
            research_profile_id: profile.id,
            observed_attributes: observed,
            evaluated_by: reviewer,
          }),
        },
      );
      await loadDetail(selected.version.id);
    } catch (reason) {
      setProfileError(
        reason instanceof Error ? reason.message : "Kurucu uyumu değerlendirilemedi.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const scoreWithProfile = async () => {
    const profile = selectedProfile;
    if (!profile) return;
    setActionBusy(true);
    setProfileError(null);
    try {
      await apiRequest("/opportunity-score-runs", {
        method: "POST",
        body: JSON.stringify({
          as_of: new Date().toISOString(),
          research_profile_id: profile.id,
        }),
      });
      await load();
    } catch (reason) {
      setProfileError(
        reason instanceof Error ? reason.message : "Puanlama çalıştırılamadı.",
      );
    } finally {
      setActionBusy(false);
    }
  };

  const toggleCompare = (id: string) => {
    setCompareIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : current.length < 3
          ? [...current, id]
          : current,
    );
  };

  const saveUrl = () => {
    const value = draftUrl.trim().replace(/\/+$/, "");
    if (!/^https?:\/\//.test(value)) return;
    window.localStorage.setItem("firsat-radari-api", value);
    if (draftApiKey.trim()) {
      window.sessionStorage.setItem(
        "firsat-radari-api-key",
        draftApiKey.trim(),
      );
    } else {
      window.sessionStorage.removeItem("firsat-radari-api-key");
    }
    setApiUrl(value);
    setApiKey(draftApiKey.trim());
    setSettingsOpen(false);
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">FR</span>
          <div>
            <strong>Fırsat Radarı</strong>
            <small>Araştırma Masası</small>
          </div>
        </div>
        <nav aria-label="Ana menü">
          <Nav active={tab === "search"} onClick={() => setTab("search")}>
            Test araması
          </Nav>
          <Nav active={tab === "radar"} onClick={() => setTab("radar")}>
            Radar
          </Nav>
          <Nav
            active={tab === "problems"}
            onClick={() => setTab("problems")}
          >
            Problem keşfi
          </Nav>
          <Nav active={tab === "sources"} onClick={() => setTab("sources")}>
            Kaynaklar
          </Nav>
          <Nav
            active={tab === "backtests"}
            onClick={() => setTab("backtests")}
          >
            Backtest
          </Nav>
          <Nav
            active={tab === "operations"}
            onClick={() => setTab("operations")}
          >
            Operasyon
          </Nav>
          <Nav active={tab === "reports"} onClick={() => setTab("reports")}>
            Raporlar
          </Nav>
          <Nav
            active={tab === "validation"}
            onClick={() => setTab("validation")}
          >
            Doğrulama
          </Nav>
          <Nav active={tab === "profile"} onClick={() => setTab("profile")}>
            Profil
          </Nav>
        </nav>
        <div className="sidebar-foot">
          <span className={`connection-dot ${error ? "down" : ""}`} />
          {error ? "Bağlantı yok" : loading ? "Güncelleniyor" : "API bağlı"}
        </div>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">VERİ TEMELLİ KEŞİF</p>
            <h1>
              {tab === "search"
                ? "Test araması"
                : tab === "radar"
                ? "Fırsat radarı"
                : tab === "problems"
                  ? "Problem keşfi"
                  : tab === "sources"
                    ? "Kaynak ve kalite"
                    : tab === "backtests"
                      ? "Geçmiş performans"
                      : tab === "operations"
                        ? "Operasyon sağlığı"
                        : tab === "reports"
                          ? "Araştırma raporları"
                          : tab === "validation"
                            ? "Doğrulama laboratuvarı"
                            : "Araştırma profili"}
            </h1>
          </div>
          <div className="top-actions">
            <button
              className="ghost-button"
              onClick={() => setSettingsOpen((value) => !value)}
            >
              API ayarı
            </button>
            <button
              className="primary-button"
              onClick={() => void load()}
              disabled={loading}
            >
              {loading ? "Yükleniyor…" : "Yenile"}
            </button>
          </div>
          {settingsOpen && (
            <div className="settings-popover">
              <label htmlFor="api-url">Backend adresi</label>
              <input
                id="api-url"
                value={draftUrl}
                onChange={(event) => setDraftUrl(event.target.value)}
              />
              <label htmlFor="api-key">Yazma API anahtarı</label>
              <input
                id="api-key"
                type="password"
                autoComplete="off"
                value={draftApiKey}
                onChange={(event) => setDraftApiKey(event.target.value)}
                placeholder="Yalnızca bu sekmede saklanır"
              />
              <label htmlFor="reviewer">Araştırmacı kimliği</label>
              <input
                id="reviewer"
                value={reviewer}
                onChange={(event) => setReviewer(event.target.value)}
              />
              <button onClick={saveUrl}>Kaydet ve bağlan</button>
            </div>
          )}
        </header>
        {error ? (
          <State
            title="Veri bağlantısı kurulamadı"
            text={`${error}. Backend adresini kontrol edip tekrar deneyin.`}
            action={() => void load()}
          />
        ) : loading ? (
          <section className="loading-grid" aria-label="Veriler yükleniyor">
            {Array.from({ length: 6 }).map((_, index) => (
              <div className="loading-block" key={index} />
            ))}
          </section>
        ) : (
          <>
            <section className="kpi-row" aria-label="Özet göstergeler">
              <Kpi
                label="Etkin kaynak"
                value={data.sources.filter((item) => item.enabled).length}
                note={`${data.sources.length} kayıtlı`}
              />
              <Kpi
                label="Açık kalite olayı"
                value={openQuality}
                note={openQuality ? "İnceleme gerekli" : "Temiz"}
                warning={openQuality > 0}
              />
              <Kpi
                label="Aday problem"
                value={data.clusters.length}
                note="Çapraz varlık"
              />
              <Kpi
                label="Sıralanabilir fırsat"
                value={data.scoreRun?.rankable_count ?? 0}
                note={
                  data.scoreRun
                    ? formatDate(data.scoreRun.as_of)
                    : "Puanlama bekleniyor"
                }
              />
            </section>
            {tab === "radar" && (
              <Radar
                ranked={ranked}
                selected={selected}
                selectedId={selectedId}
                onSelect={setSelectedId}
                compareIds={compareIds}
                onToggleCompare={toggleCompare}
                detail={detail}
                detailLoading={detailLoading}
                detailError={detailError}
                decision={decision}
                reviewNotes={reviewNotes}
                actionBusy={actionBusy}
                onDecision={setDecision}
                onReviewNotes={setReviewNotes}
                onSaveReview={() => void saveReview()}
                onResearch={() => void createResearch()}
                onExport={() => void prepareExport()}
              />
            )}
            {tab === "search" && (
              <TestSearch
                error={testSearchError}
                busy={actionBusy}
                query={testSearchQuery}
                result={testSearchResult}
                onQuery={setTestSearchQuery}
                onSearch={() => void runTestSearch()}
                onShowProblems={() => setTab("problems")}
              />
            )}
            {tab === "problems" && <Problems clusters={data.clusters} />}
            {tab === "sources" && (
              <Sources
                sources={data.sources}
                health={data.health}
                error={sourceError}
                busy={actionBusy}
                onApprove={(key, draft) => void approveSource(key, draft)}
                onEnabled={(key, enabled) =>
                  void setSourceEnabled(key, enabled)
                }
                onIndependence={(key, draft) =>
                  void reviewSourceIndependence(key, draft)
                }
              />
            )}
            {tab === "backtests" && <Backtests rows={data.backtests} />}
            {tab === "operations" && (
              <Operations
                summary={data.operations}
                alerts={data.alerts}
                jobs={data.scheduledJobs}
                runs={data.scheduledJobRuns}
                error={operationsError}
                busy={actionBusy}
                hasProfile={Boolean(selectedProfile)}
                selectedProfileId={selectedProfile?.id ?? ""}
                onCreateOperations={() =>
                  void createScheduledJob("operations_evaluation")
                }
                onCreateScoring={() =>
                  void createScheduledJob("opportunity_scoring")
                }
                onStatus={(id, status) =>
                  void setScheduledJobStatus(id, status)
                }
                onRunDue={() => void runDueScheduledJobs()}
              />
            )}
            {tab === "reports" && (
              <Reports
                weekly={data.weeklyReport}
                monthly={data.monthlyReport}
              />
            )}
            {tab === "validation" && (
              <ValidationLab
                experiments={validation}
                loading={validationLoading}
                error={validationError}
                hasSelectedOpportunity={Boolean(selected?.version)}
                segment={validationSegment}
                hypothesis={validationHypothesis}
                participant={validationParticipant}
                notes={validationNotes}
                experimentType={validationExperimentType}
                cohort={validationCohort}
                outcomeType={validationOutcomeType}
                amount={validationAmount}
                evidence={validationEvidence}
                actionBusy={actionBusy}
                onSegment={setValidationSegment}
                onHypothesis={setValidationHypothesis}
                onParticipant={setValidationParticipant}
                onNotes={setValidationNotes}
                onExperimentType={setValidationExperimentType}
                onCohort={setValidationCohort}
                onOutcomeType={setValidationOutcomeType}
                onAmount={setValidationAmount}
                onEvidence={setValidationEvidence}
                onCreateExperiment={() => void createValidationExperiment()}
                onCreateOutcome={() => void createValidationOutcome()}
                onReviewOutcome={(id) => void reviewValidationOutcome(id)}
                onCloseExperiment={(id) =>
                  void closeValidationExperiment(id)
                }
                onOptOut={() => void recordValidationOptOut()}
                onRetry={() => void loadValidation()}
              />
            )}
            {tab === "profile" && (
              <ProfileSettings
                profiles={data.profiles}
                selectedProfileId={selectedProfile?.id ?? ""}
                selectedTitle={selected?.version?.title ?? null}
                latestEvaluation={
                  detail.profileEvaluations.find(
                    (item) =>
                      item.research_profile_id === selectedProfile?.id,
                  ) ?? null
                }
                error={profileError}
                busy={actionBusy}
                capitalBudget={capitalBudget}
                maxBuildWeeks={maxBuildWeeks}
                maxTeamSize={maxTeamSize}
                category={observedCategory}
                estimatedCost={observedCost}
                buildWeeks={observedBuildWeeks}
                teamSize={observedTeamSize}
                salesMotion={observedSalesMotion}
                onCapitalBudget={setCapitalBudget}
                onMaxBuildWeeks={setMaxBuildWeeks}
                onMaxTeamSize={setMaxTeamSize}
                onCategory={setObservedCategory}
                onEstimatedCost={setObservedCost}
                onBuildWeeks={setObservedBuildWeeks}
                onTeamSize={setObservedTeamSize}
                onSalesMotion={setObservedSalesMotion}
                onSelectedProfile={setSelectedProfileId}
                onCreateProfile={() => void createResearchProfile()}
                onEvaluate={() => void evaluateSelectedProfile()}
                onScore={() => void scoreWithProfile()}
              />
            )}
          </>
        )}
      </section>
    </main>
  );
}

function ValidationLab({
  experiments,
  loading,
  error,
  hasSelectedOpportunity,
  segment,
  hypothesis,
  participant,
  notes,
  experimentType,
  cohort,
  outcomeType,
  amount,
  evidence,
  actionBusy,
  onSegment,
  onHypothesis,
  onParticipant,
  onNotes,
  onExperimentType,
  onCohort,
  onOutcomeType,
  onAmount,
  onEvidence,
  onCreateExperiment,
  onCreateOutcome,
  onReviewOutcome,
  onCloseExperiment,
  onOptOut,
  onRetry,
}: {
  experiments: ValidationExperiment[];
  loading: boolean;
  error: string | null;
  hasSelectedOpportunity: boolean;
  segment: string;
  hypothesis: string;
  participant: string;
  notes: string;
  experimentType: string;
  cohort: string;
  outcomeType: string;
  amount: string;
  evidence: string;
  actionBusy: boolean;
  onSegment: (value: string) => void;
  onHypothesis: (value: string) => void;
  onParticipant: (value: string) => void;
  onNotes: (value: string) => void;
  onExperimentType: (value: string) => void;
  onCohort: (value: string) => void;
  onOutcomeType: (value: string) => void;
  onAmount: (value: string) => void;
  onEvidence: (value: string) => void;
  onCreateExperiment: () => void;
  onCreateOutcome: () => void;
  onReviewOutcome: (id: string) => void;
  onCloseExperiment: (id: string) => void;
  onOptOut: () => void;
  onRetry: () => void;
}) {
  const active = experiments.find((item) => item.status === "running");
  const requiresPaymentEvidence = [
    "prepayment",
    "contract",
    "sale",
    "renewal",
  ].includes(outcomeType);
  if (loading) {
    return <div className="detail-loading">Doğrulama verileri yükleniyor…</div>;
  }
  return (
    <section className="validation-layout">
      {error && (
        <div className="state-panel compact-state" role="alert">
          <strong>Doğrulama API bağlantısı hazır değil</strong>
          <p>
            {error}. API anahtarı, doğrulama özelliği ve hash secret ayarlarını
            kontrol edin.
          </p>
          <button className="primary-button" onClick={onRetry}>
            Tekrar dene
          </button>
        </div>
      )}
      <div className="validation-forms">
        <article className="panel validation-form">
          <h2>Yeni görüşme deneyi</h2>
          <p>Radar’da seçili fırsat sürümüne bağlanır.</p>
          <select
            value={experimentType}
            onChange={(event) => onExperimentType(event.target.value)}
          >
            <option value="customer_interview">Müşteri görüşmesi</option>
            <option value="price_test">Fiyat testi</option>
            <option value="pilot_offer">Pilot teklifi</option>
            <option value="pre_sale">Ön satış</option>
            <option value="landing_page">Açılış sayfası</option>
          </select>
          <select
            value={cohort}
            onChange={(event) => onCohort(event.target.value)}
          >
            <option value="radar">Radar grubu</option>
            <option value="control">Kontrol grubu</option>
            <option value="baseline">Taban grup</option>
          </select>
          <input
            value={segment}
            onChange={(event) => onSegment(event.target.value)}
            placeholder="Hedef müşteri segmenti"
          />
          <textarea
            value={hypothesis}
            onChange={(event) => onHypothesis(event.target.value)}
            placeholder="Test edilecek hipotez"
            rows={4}
          />
          <button
            className="primary-button"
            disabled={
              actionBusy ||
              !hasSelectedOpportunity ||
              !segment.trim() ||
              !hypothesis.trim()
            }
            onClick={onCreateExperiment}
          >
            Deneyi başlat
          </button>
        </article>
        <article className="panel validation-form">
          <h2>Görüşme sonucu</h2>
          <p>
            Kişisel veri yerine CRM gibi bir sistemde üretilmiş opak anahtar
            kullanın.
          </p>
          <select
            value={outcomeType}
            onChange={(event) => onOutcomeType(event.target.value)}
          >
            <option value="qualified_interview">Nitelikli görüşme</option>
            <option value="price_acceptance">Fiyat kabulü</option>
            <option value="pilot_commitment">Pilot taahhüdü</option>
            <option value="prepayment">Ön ödeme</option>
            <option value="contract">Sözleşme</option>
            <option value="sale">Satış</option>
            <option value="repeat_usage">Tekrar kullanım</option>
            <option value="renewal">Yenileme</option>
            <option value="rejection">Ret</option>
            <option value="no_budget">Bütçe yok</option>
          </select>
          <input
            value={participant}
            onChange={(event) => onParticipant(event.target.value)}
            placeholder="crm:account:anon-001"
          />
          <textarea
            value={notes}
            onChange={(event) => onNotes(event.target.value)}
            placeholder="Görüşme kanıtı ve kısa not"
            rows={4}
          />
          <input
            type="number"
            min="0"
            value={amount}
            onChange={(event) => onAmount(event.target.value)}
            placeholder="Tutar (ödeme sonuçları için USD)"
          />
          <input
            value={evidence}
            onChange={(event) => onEvidence(event.target.value)}
            placeholder="Kanıt referansı"
          />
          <button
            className="primary-button"
            disabled={
              actionBusy ||
              !active ||
              participant.trim().length < 3 ||
              !notes.trim() ||
              (requiresPaymentEvidence &&
                (!amount || Number(amount) <= 0 || !evidence.trim()))
            }
            onClick={onCreateOutcome}
          >
            Sonucu kaydet
          </button>
          <button
            className="ghost-button"
            disabled={actionBusy || participant.trim().length < 3}
            onClick={onOptOut}
          >
            İletişim reddini kaydet
          </button>
        </article>
      </div>
      <div className="panel table-panel">
        <Heading
          title="Doğrulama deneyleri"
          text="Kontrol kohortu, protokol ve bağımsız sonuç incelemesi korunur."
          count={experiments.length}
        />
        {experiments.length === 0 ? (
          <Empty
            title="Deney yok"
            text="Radar’dan bir fırsat seçip ilk görüşme deneyini başlatın."
          />
        ) : (
          <div className="experiment-list">
            {experiments.map((experiment) => (
              <article key={experiment.id}>
                <div className="experiment-title">
                  <div>
                    <strong>{experiment.hypothesis}</strong>
                    <small>{experiment.target_segment}</small>
                  </div>
                  <span className="pill">
                    {humanStatus(experiment.status)}
                  </span>
                </div>
                {experiment.status === "running" && (
                  <button
                    className="ghost-button"
                    disabled={actionBusy}
                    onClick={() => onCloseExperiment(experiment.id)}
                  >
                    Deneyi tamamla
                  </button>
                )}
                <div className="experiment-meta">
                  <Summary
                    label="Protokol"
                    value={experiment.protocol_key}
                  />
                  <Summary
                    label="Kohort"
                    value={humanStatus(experiment.cohort)}
                  />
                  <Summary
                    label="Sonuç"
                    value={String(experiment.outcomes.length)}
                  />
                </div>
                <div className="outcome-list">
                  {experiment.outcomes.map((outcome) => (
                    <div key={outcome.id}>
                      <span
                        className={`direction ${outcome.direction}`}
                      >
                        {humanStatus(outcome.direction)}
                      </span>
                      <strong>{humanStatus(outcome.outcome_type)}</strong>
                      <small>
                        {humanStatus(outcome.verification_status)} ·{" "}
                        {formatDate(outcome.occurred_at)}
                      </small>
                      {outcome.verification_status === "pending" && (
                        <button
                          className="ghost-button"
                          disabled={actionBusy}
                          onClick={() => onReviewOutcome(outcome.id)}
                        >
                          Kanıtı doğrula
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Reports({
  weekly,
  monthly,
}: {
  weekly: ResearchReport | null;
  monthly: ResearchReport | null;
}) {
  if (!weekly || !monthly) {
    return (
      <div className="panel">
        <Empty
          title="Rapor verisi yok"
          text="Puanlama ve operasyon verileri oluştuğunda rapor burada görünür."
        />
      </div>
    );
  }
  return (
    <section className="report-layout">
      <div className="report-cards">
        <ReportCard title="Son 7 gün" report={weekly} />
        <ReportCard title="Son 30 gün" report={monthly} />
      </div>
      <div className="panel table-panel">
        <Heading
          title="Haftanın öne çıkan fırsatları"
          text="Toplam puan yalnızca güven ve veri yeterliliği kapısını geçenlerde gösterilir."
          count={weekly.top_opportunities.length}
        />
        {weekly.top_opportunities.length === 0 ? (
          <Empty
            title="Sıralanabilir fırsat yok"
            text="Eksik kanıtlar tamamlandığında fırsatlar rapora girer."
          />
        ) : (
          <div className="report-ranking">
            {weekly.top_opportunities.map((item, index) => (
              <article key={item.opportunity_version_id}>
                <span>{index + 1}</span>
                <strong>{item.title}</strong>
                <Summary
                  label="Potansiyel"
                  value={percent(item.potential_score)}
                />
                <Summary
                  label="Eylem"
                  value={percent(item.actionability_score)}
                />
                <Summary
                  label="Güven"
                  value={percent(item.confidence_score)}
                />
                <b>
                  {item.total_score
                    ? Math.round(Number(item.total_score) * 100)
                    : "—"}
                </b>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function ProfileSettings({
  profiles,
  selectedProfileId,
  selectedTitle,
  latestEvaluation,
  error,
  busy,
  capitalBudget,
  maxBuildWeeks,
  maxTeamSize,
  category,
  estimatedCost,
  buildWeeks,
  teamSize,
  salesMotion,
  onCapitalBudget,
  onMaxBuildWeeks,
  onMaxTeamSize,
  onCategory,
  onEstimatedCost,
  onBuildWeeks,
  onTeamSize,
  onSalesMotion,
  onSelectedProfile,
  onCreateProfile,
  onEvaluate,
  onScore,
}: {
  profiles: ResearchProfile[];
  selectedProfileId: string;
  selectedTitle: string | null;
  latestEvaluation: ProfileEvaluation | null;
  error: string | null;
  busy: boolean;
  capitalBudget: string;
  maxBuildWeeks: string;
  maxTeamSize: string;
  category: string;
  estimatedCost: string;
  buildWeeks: string;
  teamSize: string;
  salesMotion: string;
  onCapitalBudget: (value: string) => void;
  onMaxBuildWeeks: (value: string) => void;
  onMaxTeamSize: (value: string) => void;
  onCategory: (value: string) => void;
  onEstimatedCost: (value: string) => void;
  onBuildWeeks: (value: string) => void;
  onTeamSize: (value: string) => void;
  onSalesMotion: (value: string) => void;
  onSelectedProfile: (value: string) => void;
  onCreateProfile: () => void;
  onEvaluate: () => void;
  onScore: () => void;
}) {
  const current =
    profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0];
  return (
    <section className="profile-layout">
      {error && (
        <div className="state-panel compact-state" role="alert">
          <strong>Profil işlemi tamamlanamadı</strong>
          <p>{error}</p>
        </div>
      )}
      <div className="validation-forms">
        <article className="panel validation-form">
          <h2>Kurucu sınırları</h2>
          <p>
            Yeni sürüm oluşturulduğunda önceki profil korunur; puanlar seçilen
            profil sürümüne bağlanır.
          </p>
          {profiles.length > 0 && (
            <label>
              Etkin araştırma profili
              <select
                value={current?.id ?? ""}
                onChange={(event) => onSelectedProfile(event.target.value)}
              >
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name} · {profile.version}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Başlangıç sermayesi
            <input
              type="number"
              min="0"
              value={capitalBudget}
              onChange={(event) => onCapitalBudget(event.target.value)}
            />
          </label>
          <label>
            En fazla geliştirme haftası
            <input
              type="number"
              min="0"
              value={maxBuildWeeks}
              onChange={(event) => onMaxBuildWeeks(event.target.value)}
            />
          </label>
          <label>
            En fazla ekip büyüklüğü
            <input
              type="number"
              min="0"
              value={maxTeamSize}
              onChange={(event) => onMaxTeamSize(event.target.value)}
            />
          </label>
          <button
            className="primary-button"
            disabled={
              busy ||
              Number(capitalBudget) < 0 ||
              Number(maxBuildWeeks) < 0 ||
              Number(maxTeamSize) < 0
            }
            onClick={onCreateProfile}
          >
            {current ? "Yeni profil sürümü oluştur" : "İlk profili oluştur"}
          </button>
          {current && (
            <small>
              Etkin profil: {current.name} · {current.version}
            </small>
          )}
        </article>
        <article className="panel validation-form">
          <h2>Fırsat uyumu</h2>
          <p>{selectedTitle ?? "Radar ekranından bir fırsat seçin."}</p>
          <input
            value={category}
            onChange={(event) => onCategory(event.target.value)}
            placeholder="Kategori"
          />
          <input
            type="number"
            min="0"
            value={estimatedCost}
            onChange={(event) => onEstimatedCost(event.target.value)}
            placeholder="Tahmini başlangıç maliyeti"
          />
          <input
            type="number"
            min="0"
            value={buildWeeks}
            onChange={(event) => onBuildWeeks(event.target.value)}
            placeholder="Tahmini geliştirme haftası"
          />
          <input
            type="number"
            min="0"
            value={teamSize}
            onChange={(event) => onTeamSize(event.target.value)}
            placeholder="Gerekli ekip büyüklüğü"
          />
          <select
            value={salesMotion}
            onChange={(event) => onSalesMotion(event.target.value)}
          >
            <option value="self_service">Self servis</option>
            <option value="product_led">Ürün odaklı</option>
            <option value="founder_sales">Kurucu satışı</option>
            <option value="enterprise_sales">Kurumsal satış</option>
          </select>
          <button
            className="primary-button"
            disabled={busy || !current || !selectedTitle || !category.trim()}
            onClick={onEvaluate}
          >
            Uyumu değerlendir
          </button>
          {latestEvaluation && (
            <div className="profile-result">
              <Summary
                label="Uyum"
                value={
                  latestEvaluation.fit_score
                    ? percent(latestEvaluation.fit_score)
                    : "Bilinmiyor"
                }
              />
              <Summary
                label="Veri kapsamı"
                value={percent(latestEvaluation.data_coverage)}
              />
              <span
                className={`pill ${
                  latestEvaluation.eligible ? "positive" : ""
                }`}
              >
                {latestEvaluation.eligible ? "Uygun" : "Engelli"}
              </span>
            </div>
          )}
        </article>
      </div>
      <div className="panel profile-score-action">
        <div>
          <h2>Profil bağlı puanlama</h2>
          <p>
            Yalnızca bu profil için yeterli ve uygun değerlendirmesi bulunan
            fırsatlar sıralanır.
          </p>
        </div>
        <button
          className="primary-button"
          disabled={busy || !current}
          onClick={onScore}
        >
          Puanla ve radarı yenile
        </button>
      </div>
    </section>
  );
}

function ReportCard({
  title,
  report,
}: {
  title: string;
  report: ResearchReport;
}) {
  const cost = Object.entries(report.cost_by_currency)
    .map(([currency, value]) => `${money(value)} ${currency}`)
    .join(" · ");
  return (
    <article className="panel report-card">
      <div>
        <span className="eyebrow">{title}</span>
        <small>
          {formatDate(report.period_start)} – {formatDate(report.period_end)}
        </small>
      </div>
      <div className="report-metrics">
        <Summary
          label="Yeni fırsat"
          value={String(report.new_opportunity_count)}
        />
        <Summary
          label="Yeni problem"
          value={String(report.new_problem_cluster_count)}
        />
        <Summary
          label="Doğrulanmış sonuç"
          value={String(report.verified_commercial_outcome_count)}
        />
        <Summary label="Maliyet" value={cost || "0"} />
      </div>
    </article>
  );
}

function Backtests({ rows }: { rows: Backtest[] }) {
  return (
    <section className="panel table-panel">
      <Heading
        title="Zaman kesmeli backtest"
        text="Tahminler, yalnızca kesim tarihinden önce bilinen verilerle karşılaştırılır."
      />
      {rows.length === 0 ? (
        <Empty
          title="Backtest henüz yok"
          text="Yeterli tarih ve tamamlanmış sonuç penceresi oluştuğunda performans burada görünür."
        />
      ) : (
        <div className="backtest-list">
          {rows.map((row) => (
            <article className="backtest-row" key={row.id}>
              <div>
                <strong>{formatDate(row.cutoff_at)}</strong>
                <small>{row.outcome_window_days} günlük sonuç penceresi</small>
              </div>
              <Stat label="Tahmin" value={row.prediction_count} />
              <Stat label="Değerlendirilen" value={row.evaluated_count} />
              <Stat label="Pozitif" value={row.positive_count} />
              <Stat label="Brier" value={decimal(row.brier_score)} />
              <Stat
                label="Taban çizgisi"
                value={decimal(row.baseline_brier_score)}
              />
              <span className="pill">{humanStatus(row.status)}</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

const TEST_SEARCH_EXAMPLES = [
  "workflow automation errors",
  "self hosted backup failure",
  "developer onboarding friction",
  "API rate limit problems",
];

function TestSearch({
  error,
  busy,
  query,
  result,
  onQuery,
  onSearch,
  onShowProblems,
}: {
  error: string | null;
  busy: boolean;
  query: string;
  result: TestSearchResult | null;
  onQuery: (value: string) => void;
  onSearch: () => void;
  onShowProblems: () => void;
}) {
  const totalErrors = result
    ? result.ingestion.error_count +
      result.normalization.error_count +
      result.repository_hydration.error_count +
      result.extraction.error_count +
      result.cluster_metrics.error_count
    : 0;
  return (
    <section className="search-layout">
      {error && (
        <div className="state-panel compact-state" role="alert">
          <strong>Test araması tamamlanamadı</strong>
          <p>{error}</p>
        </div>
      )}
      <div className="panel search-guide-panel">
        <div>
          <p className="eyebrow">NE YAZMALISIN?</p>
          <h2>Bir ürün fikri değil, araştırılacak problem alanını yaz</h2>
          <p>
            Şimdilik açık GitHub issue başlıkları ve açıklamaları taranıyor. Bu
            yüzden İngilizce, somut ve 2–6 kelimelik problem ifadeleri en iyi
            sonucu verir.
          </p>
        </div>
        <div className="search-examples" aria-label="Örnek test aramaları">
          {TEST_SEARCH_EXAMPLES.map((example) => (
            <button
              type="button"
              className="search-example"
              key={example}
              disabled={busy}
              onClick={() => onQuery(example)}
            >
              {example}
            </button>
          ))}
        </div>
        <p className="search-caveat">
          “Bana iş fikri bul” veya uzun bir proje tarifi yazma. Bu ekran sohbet
          etmez; sahadaki açık problem kayıtlarını arar. Genel tüketici talebi,
          Google Ads ve SEO verisi henüz bu test aramasının kapsamında değildir.
        </p>
      </div>

      <div className="panel test-search-panel">
        <div className="research-heading">
          <div>
            <h2>Tek seferlik canlı arama</h2>
            <p>En fazla 20 güncel, açık ve herkese açık GitHub kaydı işlenir.</p>
          </div>
        </div>
        <form
          className="test-search-form"
          onSubmit={(event) => {
            event.preventDefault();
            onSearch();
          }}
        >
          <label htmlFor="test-search-query">Problem alanı veya konu</label>
          <div>
            <input
              id="test-search-query"
              value={query}
              minLength={3}
              maxLength={120}
              disabled={busy}
              onChange={(event) => onQuery(event.target.value)}
              placeholder="Örn. workflow automation errors"
              autoComplete="off"
            />
            <button
              className="primary-button"
              type="submit"
              disabled={busy || query.trim().length < 3}
            >
              {busy ? "Veriler araştırılıyor…" : "Test aramasını başlat"}
            </button>
          </div>
        </form>
        {busy && (
          <p className="search-progress" role="status">
            GitHub kayıtları alınıyor, doğrulanıyor ve problem kümeleri
            hesaplanıyor. Bu işlem yaklaşık 1–2 dakika sürebilir.
          </p>
        )}
        {result && (
          <div className="test-search-result" role="status" aria-live="polite">
            <div className="search-result-heading">
              <div>
                <strong>“{result.query}” araması tamamlandı</strong>
                <small>
                  Sonuçlar mevcut veri havuzuyla birlikte değerlendirildi.
                </small>
              </div>
              <button className="ghost-button" onClick={onShowProblems}>
                Problem kümelerini gör
              </button>
            </div>
            <div className="search-result-stats">
              <Stat label="Toplanan" value={result.ingestion.raw_item_count} />
              <Stat
                label="Normalize edilen"
                value={result.normalization.success_count}
              />
              <Stat
                label="Problem kanıtı"
                value={result.extraction.evidence_count}
              />
              <Stat
                label="Güncel küme"
                value={result.clustering.cluster_count}
              />
              <Stat label="Hata" value={totalErrors} />
            </div>
            <p>
              Bir kayıt bulunması otomatik olarak fırsat olduğu anlamına gelmez.
              Sistem; tekrar, farklı proje/kaynak desteği ve istatistiksel güven
              kapıları geçilmeden fırsat kartı üretmez.
            </p>
          </div>
        )}
      </div>

      <div className="panel search-process-panel">
        <div className="research-heading">
          <div>
            <h2>Arka planda ne olacak?</h2>
            <p>Arama, ham kayıttan kanıtlı fırsata doğru kontrollü ilerler.</p>
          </div>
        </div>
        <ol className="search-process">
          <li>
            <strong>Kaynak taraması</strong>
            <span>Açık GitHub issue başlık ve açıklamalarında sorgu aranır.</span>
          </li>
          <li>
            <strong>Bağlam doğrulama</strong>
            <span>Deponun kimliği ve metadata bilgileri doğrulanır.</span>
          </li>
          <li>
            <strong>Temizleme</strong>
            <span>Kayıtlar saklanır, tekilleştirilir ve ortak şemaya çevrilir.</span>
          </li>
          <li>
            <strong>Problem çıkarımı</strong>
            <span>Hata, engel, eksik özellik ve sürtünme sinyalleri aranır.</span>
          </li>
          <li>
            <strong>İstatistiksel kapı</strong>
            <span>Benzer sinyaller kümelenir; tekrar ve güven metrikleri hesaplanır.</span>
          </li>
        </ol>
      </div>
    </section>
  );
}

function Operations({
  summary,
  alerts,
  jobs,
  runs,
  error,
  busy,
  hasProfile,
  selectedProfileId,
  onCreateOperations,
  onCreateScoring,
  onStatus,
  onRunDue,
}: {
  summary: OperationsSummary | null;
  alerts: OperationalAlert[];
  jobs: ScheduledJob[];
  runs: ScheduledJobRun[];
  error: string | null;
  busy: boolean;
  hasProfile: boolean;
  selectedProfileId: string;
  onCreateOperations: () => void;
  onCreateScoring: () => void;
  onStatus: (id: string, status: string) => void;
  onRunDue: () => void;
}) {
  const latestRunByJob = new Map<string, ScheduledJobRun>();
  const hasOperationsJob = jobs.some(
    (job) => job.job_type === "operations_evaluation",
  );
  const hasScoringJob = jobs.some(
    (job) =>
      job.job_type === "opportunity_scoring" &&
      job.payload.research_profile_id === selectedProfileId,
  );
  runs.forEach((run) => {
    if (!latestRunByJob.has(run.scheduled_job_id)) {
      latestRunByJob.set(run.scheduled_job_id, run);
    }
  });
  return (
    <section className="ops-layout">
      {error && (
        <div className="state-panel compact-state" role="alert">
          <strong>Operasyon işlemi tamamlanamadı</strong>
          <p>{error}</p>
        </div>
      )}
      {summary ? (
        <div className="ops-summary">
          <article className="kpi">
            <small>Açık alarm</small>
            <strong className={alerts.length ? "danger-text" : ""}>
              {summary.open_alert_count}
            </strong>
            <span>{summary.critical_alert_count} kritik</span>
          </article>
          <article className="kpi">
            <small>Günlük maliyet</small>
            <strong>${money(summary.daily_cost_usd)}</strong>
            <span>{budgetNote(summary.daily_budget_usd)}</span>
          </article>
          <article className="kpi">
            <small>Aylık maliyet</small>
            <strong>${money(summary.monthly_cost_usd)}</strong>
            <span>{budgetNote(summary.monthly_budget_usd)}</span>
          </article>
        </div>
      ) : (
        <div className="panel">
          <Empty
            title="Operasyon özeti yok"
            text="Operasyon değerlendirmesi çalıştırıldığında sağlık bilgisi burada görünür."
          />
        </div>
      )}
      <div className="panel table-panel">
        <div className="research-heading">
          <div>
            <h2>Zamanlanmış işler</h2>
            <p>
              Sağlık değerlendirmesi ve profil bağlı puanlama otomatik çalışır.
              Kaynak tarama sorguları API üzerinden açıkça yapılandırılır.
            </p>
          </div>
          <div className="research-actions">
            <button
              className="ghost-button"
              disabled={busy || hasOperationsJob}
              onClick={onCreateOperations}
            >
              {hasOperationsJob ? "Sağlık takvimi hazır" : "Saatlik sağlık takvimi"}
            </button>
            <button
              className="ghost-button"
              disabled={busy || !hasProfile || hasScoringJob}
              onClick={onCreateScoring}
            >
              {hasScoringJob ? "Puanlama takvimi hazır" : "Günlük puanlama takvimi"}
            </button>
            <button
              className="primary-button"
              disabled={busy || !jobs.some((job) => job.status === "active")}
              onClick={onRunDue}
            >
              Zamanı gelenleri çalıştır
            </button>
          </div>
        </div>
        {jobs.length === 0 ? (
          <Empty
            title="Takvim tanımlı değil"
            text="Yukarıdaki kontrollere basarak temel operasyon takvimlerini oluşturabilirsiniz."
          />
        ) : (
          <div className="alert-list">
            {jobs.map((job) => {
              const latestRun = latestRunByJob.get(job.id);
              return (
                <article className="alert-row" key={job.id}>
                  <span className={`severity ${job.status}`}>
                    {humanStatus(job.status)}
                  </span>
                  <div>
                    <strong>{job.key}</strong>
                    <small>
                      {humanStatus(job.job_type)} · {job.interval_minutes} dk ·
                      sonraki {formatDate(job.next_run_at)}
                    </small>
                    {latestRun?.error_message && (
                      <small className="danger-text">
                        {latestRun.error_message}
                      </small>
                    )}
                  </div>
                  <button
                    className="ghost-button"
                    disabled={busy || job.status === "retired"}
                    onClick={() =>
                      onStatus(
                        job.id,
                        job.status === "active" ? "paused" : "active",
                      )
                    }
                  >
                    {job.status === "active" ? "Duraklat" : "Etkinleştir"}
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </div>
      <div className="panel table-panel">
        <Heading
          title="Etkin operasyon alarmları"
          text={
            summary
              ? `Son değerlendirme: ${formatDate(summary.generated_at)}`
              : "Henüz değerlendirme çalışmadı."
          }
          count={alerts.length}
        />
        {alerts.length === 0 ? (
          <Empty
            title="Etkin alarm yok"
            text="Kaynak güncelliği, kalite ve bütçe eşikleri normal görünüyor."
          />
        ) : (
          <div className="alert-list">
            {alerts.map((alert) => (
              <article className="alert-row" key={alert.id}>
                <span className={`severity ${alert.severity}`}>
                  {humanStatus(alert.severity)}
                </span>
                <div>
                  <strong>{alert.message}</strong>
                  <small>
                    {humanStatus(alert.category)} ·{" "}
                    {formatDate(alert.last_detected_at)}
                  </small>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Radar({
  ranked,
  selected,
  selectedId,
  onSelect,
  compareIds,
  onToggleCompare,
  detail,
  detailLoading,
  detailError,
  decision,
  reviewNotes,
  actionBusy,
  onDecision,
  onReviewNotes,
  onSaveReview,
  onResearch,
  onExport,
}: {
  ranked: Array<{
    opportunity: Opportunity;
    version?: Version;
    score?: Score;
  }>;
  selected?: { opportunity: Opportunity; version?: Version; score?: Score };
  selectedId: string | null;
  onSelect: (id: string) => void;
  compareIds: string[];
  onToggleCompare: (id: string) => void;
  detail: DetailData;
  detailLoading: boolean;
  detailError: string | null;
  decision: string;
  reviewNotes: string;
  actionBusy: boolean;
  onDecision: (value: string) => void;
  onReviewNotes: (value: string) => void;
  onSaveReview: () => void;
  onResearch: () => void;
  onExport: () => void;
}) {
  const latestResearch = detail.researchRuns[0];
  const exportReady =
    detail.researchRuns.some((item) => item.status === "succeeded") &&
    detail.reviews[0]?.decision === "validate";
  const comparison = ranked.filter((item) =>
    compareIds.includes(item.opportunity.id),
  );
  return (
    <div className="radar-stack">
      {comparison.length > 0 && (
        <section className="panel comparison-panel">
          <Heading
            title="Fırsat karşılaştırması"
            text="En fazla üç fırsat; potansiyel, eylem ve güven ayrıştırılarak."
            count={comparison.length}
          />
          <div className="comparison-grid">
            {comparison.map(({ opportunity, version, score }) => (
              <article key={opportunity.id}>
                <button
                  className="remove-compare"
                  onClick={() => onToggleCompare(opportunity.id)}
                  aria-label="Karşılaştırmadan çıkar"
                >
                  ×
                </button>
                <strong>{version?.title ?? "Sürümsüz fırsat"}</strong>
                <Summary
                  label="Potansiyel"
                  value={percent(score?.potential_score)}
                />
                <Summary
                  label="Eylem"
                  value={percent(score?.actionability_score)}
                />
                <Summary
                  label="Güven"
                  value={percent(score?.confidence_score)}
                />
                <Summary
                  label="Toplam"
                  value={percent(score?.total_score ?? undefined)}
                />
              </article>
            ))}
          </div>
        </section>
      )}
      <section className="radar-layout">
      <div className="panel opportunity-list">
        <Heading
          title="Kanıtlı fırsatlar"
          text="Güven eşiğini geçenler önce gösterilir."
          count={ranked.length}
        />
        {ranked.length === 0 ? (
          <Empty
            title="Henüz fırsat yok"
            text="Tüm kanıt kapılarını geçen bir küme oluştuğunda burada görünür."
          />
        ) : (
          ranked.map(({ opportunity, version, score }, index) => (
            <div
              key={opportunity.id}
              className={`opportunity-row ${
                selectedId === opportunity.id ? "selected" : ""
              }`}
            >
              <button
                className="opportunity-main"
                onClick={() => onSelect(opportunity.id)}
              >
                <span className="rank">
                  {score?.total_score ? index + 1 : "—"}
                </span>
                <span className="row-copy">
                  <strong>{version?.title ?? "Sürümsüz fırsat"}</strong>
                  <small>
                    {score?.status === "rankable"
                      ? `${percent(score.confidence_score)} güven`
                      : humanStatus(score?.status ?? "not_scored")}
                  </small>
                </span>
                <span
                  className={`score ${
                    score?.total_score ? "" : "muted-score"
                  }`}
                >
                  {score?.total_score
                    ? Math.round(Number(score.total_score) * 100)
                    : "—"}
                </span>
              </button>
              <button
                className="compare-button"
                aria-pressed={compareIds.includes(opportunity.id)}
                onClick={() => onToggleCompare(opportunity.id)}
                title="Karşılaştır"
              >
                {compareIds.includes(opportunity.id) ? "✓" : "+"}
              </button>
            </div>
          ))
        )}
      </div>
      <div className="panel detail-panel">
        {!selected?.version ? (
          <Empty
            title="Fırsat seçin"
            text="Kanıt ve ontoloji ayrıntıları burada görüntülenir."
          />
        ) : (
          <>
            <div className="detail-title">
              <div>
                <span className="pill positive">
                  {selected.version.evidence_level}
                </span>
                <h2>{selected.version.title}</h2>
              </div>
              <span className="version">
                v{selected.version.version_number}
              </span>
            </div>
            <div className="score-strip">
              <Metric label="Potansiyel" value={selected.score?.potential_score} />
              <Metric
                label="Eylem"
                value={selected.score?.actionability_score}
              />
              <Metric label="Güven" value={selected.score?.confidence_score} />
              <Metric
                label="Belirsizlik"
                value={selected.score?.uncertainty}
                inverse
              />
            </div>
            {selected.score && selected.score.status !== "rankable" && (
              <div className="warning-box">
                Sıralama engeli:{" "}
                {selected.score.components.blockers
                  ?.map(humanStatus)
                  .join(", ")}
              </div>
            )}
            <div className="ontology-grid">
              {Object.entries(selected.version.ontology).map(([key, value]) => (
                <article key={key}>
                  <small>{LABELS[key] ?? key}</small>
                  <p>{value}</p>
                </article>
              ))}
            </div>
            <section className="research-section">
              <div className="research-heading">
                <div>
                  <h3>Kanıtlı derin araştırma</h3>
                  <p>
                    Bilinenler, karşı kanıtlar ve sonraki en ucuz doğrulama.
                  </p>
                </div>
                <div className="research-actions">
                  <button
                    className="ghost-button"
                    disabled={actionBusy}
                    onClick={onResearch}
                  >
                    Araştırmayı yenile
                  </button>
                  <button
                    className="primary-button"
                    disabled={actionBusy || !exportReady}
                    onClick={onExport}
                  >
                    Aktarım paketi
                  </button>
                </div>
              </div>
              {detailError && (
                <div className="warning-box">{detailError}</div>
              )}
              {detailLoading ? (
                <div className="detail-loading">Ayrıntılar yükleniyor…</div>
              ) : !latestResearch ? (
                <p className="muted-copy">
                  Henüz araştırma anlık görüntüsü yok. Yazma API anahtarını
                  ayarlayıp araştırmayı başlatın.
                </p>
              ) : (
                <>
                  <div className="research-summary">
                    <Summary
                      label="Durum"
                      value={humanStatus(latestResearch.status)}
                      danger={latestResearch.status === "blocked"}
                    />
                    <Summary
                      label="Önerilen test"
                      value={humanStatus(
                        latestResearch.findings.recommended_next_test ??
                          "unknown",
                      )}
                    />
                    <Summary
                      label="Tarih"
                      value={formatDate(latestResearch.started_at)}
                    />
                  </div>
                  {latestResearch.blockers.length > 0 && (
                    <div className="warning-box">
                      Araştırma engelleri:{" "}
                      {latestResearch.blockers.map(humanStatus).join(", ")}
                    </div>
                  )}
                  {Boolean(latestResearch.findings.risk_flags?.length) && (
                    <div className="warning-box">
                      Karşı kanıt ve riskler:{" "}
                      {latestResearch.findings.risk_flags
                        ?.map(humanStatus)
                        .join(", ")}
                    </div>
                  )}
                  <div className="evidence-list">
                    {latestResearch.evidence_snapshot.components?.map(
                      (component) => (
                        <article key={component.component_key}>
                          <div>
                            <small>
                              {LABELS[component.component_key] ??
                                component.component_key}
                            </small>
                            <span className="pill">
                              {component.evidence_level}
                            </span>
                          </div>
                          <strong>{component.statement}</strong>
                          {component.evidence.map((evidence) => (
                            <div key={evidence.evidence_id}>
                              <blockquote
                                className={
                                  evidence.direction === "refutes"
                                    ? "refuting"
                                    : ""
                                }
                              >
                                {evidence.excerpt}
                              </blockquote>
                              {evidence.source_url && (
                                <small className="evidence-attribution">
                                  Kaynak:{" "}
                                  <a
                                    href={evidence.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    {evidence.source_name ?? "Kaynak belge"}
                                  </a>
                                  {evidence.source_license
                                    ? ` · ${evidence.source_license}`
                                    : ""}
                                </small>
                              )}
                            </div>
                          ))}
                          {component.commercial_evidence.map((outcome) => (
                            <p
                              className="commercial-proof"
                              key={outcome.outcome_id}
                            >
                              {humanStatus(outcome.outcome_type)}
                              {outcome.amount
                                ? ` · ${outcome.amount} ${outcome.currency}`
                                : ""}
                            </p>
                          ))}
                        </article>
                      ),
                    )}
                  </div>
                </>
              )}
            </section>
            <section className="decision-grid">
              <div>
                <h3>Puan geçmişi</h3>
                {detail.scoreHistory.length === 0 ? (
                  <p className="muted-copy">Puan sürümü yok.</p>
                ) : (
                  <div className="history-list">
                    {detail.scoreHistory.map((item) => (
                      <article key={item.run_id}>
                        <span>{formatDate(item.as_of)}</span>
                        <strong>
                          {item.total_score
                            ? Math.round(Number(item.total_score) * 100)
                            : "—"}
                        </strong>
                        <small>{humanStatus(item.status)}</small>
                      </article>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <h3>Manuel karar</h3>
                <div className="review-form">
                  <select
                    value={decision}
                    onChange={(event) => onDecision(event.target.value)}
                  >
                    <option value="investigate">İncele</option>
                    <option value="validate">Doğrulamaya gönder</option>
                    <option value="watch">İzle</option>
                    <option value="reject">Reddet</option>
                    <option value="archive">Arşivle</option>
                  </select>
                  <textarea
                    value={reviewNotes}
                    onChange={(event) => onReviewNotes(event.target.value)}
                    placeholder="Kararın gerekçesi…"
                    rows={3}
                  />
                  <button
                    className="primary-button"
                    disabled={actionBusy || !reviewNotes.trim()}
                    onClick={onSaveReview}
                  >
                    Kararı kaydet
                  </button>
                </div>
                <div className="review-history">
                  {detail.reviews.slice(0, 5).map((review) => (
                    <article key={review.id}>
                      <div>
                        <span className="pill">
                          {humanStatus(review.decision)}
                        </span>
                        <small>
                          {review.reviewer} · {formatDate(review.created_at)}
                        </small>
                      </div>
                      <p>{review.notes}</p>
                    </article>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}
      </div>
      </section>
    </div>
  );
}

function Problems({ clusters }: { clusters: Cluster[] }) {
  return (
    <section className="panel table-panel">
      <Heading
        title="Tekrarlanan problem kümeleri"
        text="Kaynak, varlık yayılımı ve küme tutarlılığıyla birlikte."
      />
      {clusters.length === 0 ? (
        <Empty
          title="Problem kümesi yok"
          text="Toplama ve çıkarım tamamlandığında kümeler burada görünür."
        />
      ) : (
        <div className="data-table">
          {clusters.map((cluster) => (
            <article className="cluster-row" key={cluster.id}>
              <div>
                <strong>{cluster.label}</strong>
                <div className="tag-row">
                  {cluster.signature.slice(0, 5).map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </div>
              <Stat label="Belge" value={cluster.document_count} />
              <Stat label="Varlık" value={cluster.entity_count} />
              <Stat label="Kaynak" value={cluster.source_count} />
              <Stat label="Tutarlılık" value={percent(cluster.cohesion_mean)} />
              <span className="pill">{humanStatus(cluster.status)}</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function Sources({
  sources,
  health,
  error,
  busy,
  onApprove,
  onEnabled,
  onIndependence,
}: {
  sources: Source[];
  health: Record<string, Health>;
  error: string | null;
  busy: boolean;
  onApprove: (key: string, draft: SourcePolicyDraft) => void;
  onEnabled: (key: string, enabled: boolean) => void;
  onIndependence: (key: string, draft: SourcePolicyDraft) => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, SourcePolicyDraft>>({});
  const draftFor = (key: string) =>
    drafts[key] ?? {
      version: new Date().toISOString().slice(0, 10),
      termsUrl: "",
      retentionDays: "90",
      independenceRationale: "",
      independenceEvidence: "",
    };
  const updateDraft = (
    key: string,
    field: keyof SourcePolicyDraft,
    value: string,
  ) => {
    setDrafts((current) => ({
      ...current,
      [key]: { ...draftFor(key), [field]: value },
    }));
  };
  if (!sources.length) {
    return (
      <div className="panel">
        <Empty
          title="Kayıtlı kaynak yok"
          text="Kaynak kayıt kartları oluşturulduğunda burada görünür."
        />
      </div>
    );
  }
  return (
    <section>
      {error && (
        <div className="state-panel compact-state" role="alert">
          <strong>Kaynak yönetimi tamamlanamadı</strong>
          <p>{error}</p>
        </div>
      )}
      <div className="source-grid">
      {sources.map((source) => {
        const item = health[source.key];
        const draft = draftFor(source.key);
        return (
          <article className="panel source-card" key={source.key}>
            <div className="source-title">
              <div>
                <span
                  className={`source-icon ${
                    source.enabled ? "" : "muted-icon"
                  }`}
                >
                  {source.key.slice(0, 2).toUpperCase()}
                </span>
                <div>
                  <h2>{source.owner}</h2>
                  <p>{source.evidence_family_key}</p>
                </div>
              </div>
              <span className={`pill ${source.enabled ? "positive" : ""}`}>
                {source.enabled ? "Etkin" : "Kapalı"}
              </span>
            </div>
            <dl>
              <Pair label="Politika" value={humanStatus(source.policy_status)} />
              <Pair
                label="Bağımsızlık"
                value={humanStatus(source.independence_status)}
              />
              <Pair label="Son başarı" value={formatDate(item?.last_success_at)} />
              <Pair
                label="Kalite olayı"
                value={String(item?.open_quality_event_count ?? 0)}
                danger={Boolean(item?.open_quality_event_count)}
              />
            </dl>
            {source.policy_status !== "approved" ? (
              <div className="source-governance">
                <p>
                  Etkinleştirmeden önce kullanım ve saklama koşullarını
                  incelediğinizi kaydedin.
                </p>
                <input
                  aria-label={`${source.owner} politika sürümü`}
                  value={draft.version}
                  onChange={(event) =>
                    updateDraft(source.key, "version", event.target.value)
                  }
                  placeholder="Politika sürümü"
                />
                <input
                  aria-label={`${source.owner} kullanım koşulları adresi`}
                  value={draft.termsUrl}
                  onChange={(event) =>
                    updateDraft(source.key, "termsUrl", event.target.value)
                  }
                  placeholder="https://…/terms"
                />
                <input
                  aria-label={`${source.owner} saklama süresi`}
                  type="number"
                  min="1"
                  max="3650"
                  value={draft.retentionDays}
                  onChange={(event) =>
                    updateDraft(
                      source.key,
                      "retentionDays",
                      event.target.value,
                    )
                  }
                />
                <small>
                  Ticari kullanım, saklama ve türetilmiş veri: izinli · LLM:
                  yasak
                </small>
                <button
                  className="primary-button"
                  disabled={
                    busy ||
                    !draft.version.trim() ||
                    !draft.termsUrl.trim() ||
                    Number(draft.retentionDays) < 1
                  }
                  onClick={() => onApprove(source.key, draft)}
                >
                  Politikayı onayla
                </button>
              </div>
            ) : (
              <button
                className={source.enabled ? "ghost-button" : "primary-button"}
                disabled={busy}
                onClick={() => onEnabled(source.key, !source.enabled)}
              >
                {source.enabled ? "Kaynağı duraklat" : "Kaynağı etkinleştir"}
              </button>
            )}
            {source.independence_status !== "independent" && (
              <div className="source-governance">
                <p>
                  Kaynağın sahiplik ve içerik bağımsızlığını kanıtlayan
                  incelemeyi ayrıca kaydedin.
                </p>
                <textarea
                  aria-label={`${source.owner} bağımsızlık gerekçesi`}
                  rows={3}
                  value={draft.independenceRationale}
                  onChange={(event) =>
                    updateDraft(
                      source.key,
                      "independenceRationale",
                      event.target.value,
                    )
                  }
                  placeholder="Bağımsızlık gerekçesi"
                />
                <input
                  aria-label={`${source.owner} bağımsızlık kanıtı`}
                  value={draft.independenceEvidence}
                  onChange={(event) =>
                    updateDraft(
                      source.key,
                      "independenceEvidence",
                      event.target.value,
                    )
                  }
                  placeholder="https://…/evidence"
                />
                <button
                  className="ghost-button"
                  disabled={
                    busy ||
                    !draft.independenceRationale.trim() ||
                    !draft.independenceEvidence.trim()
                  }
                  onClick={() => onIndependence(source.key, draft)}
                >
                  Bağımsızlık incelemesini onayla
                </button>
              </div>
            )}
          </article>
        );
      })}
      </div>
    </section>
  );
}

function Nav({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button className={active ? "active" : ""} onClick={onClick}>
      {children}
    </button>
  );
}
function Heading({
  title,
  text,
  count,
}: {
  title: string;
  text: string;
  count?: number;
}) {
  return (
    <div className="panel-heading">
      <div>
        <h2>{title}</h2>
        <p>{text}</p>
      </div>
      {count !== undefined && <span className="count">{count}</span>}
    </div>
  );
}
function Kpi({
  label,
  value,
  note,
  warning = false,
}: {
  label: string;
  value: number;
  note: string;
  warning?: boolean;
}) {
  return (
    <article className="kpi">
      <small>{label}</small>
      <strong className={warning ? "danger-text" : ""}>{value}</strong>
      <span>{note}</span>
    </article>
  );
}
function Metric({
  label,
  value,
  inverse = false,
}: {
  label: string;
  value?: string;
  inverse?: boolean;
}) {
  const numeric = Number(value ?? 0);
  return (
    <div>
      <span>{label}</span>
      <strong>{value ? `${Math.round(numeric * 100)}%` : "—"}</strong>
      <i>
        <b
          style={{
            width: `${Math.round((inverse ? 1 - numeric : numeric) * 100)}%`,
          }}
        />
      </i>
    </div>
  );
}
function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="table-stat">
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}
function Pair({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={danger ? "danger-text" : ""}>{value}</dd>
    </div>
  );
}
function Summary({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div>
      <small>{label}</small>
      <strong className={danger ? "danger-text" : ""}>{value}</strong>
    </div>
  );
}
function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <span>○</span>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}
function State({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action: () => void;
}) {
  return (
    <section className="state-panel" role="alert">
      <strong>{title}</strong>
      <p>{text}</p>
      <button className="primary-button" onClick={action}>
        Tekrar dene
      </button>
    </section>
  );
}
function percent(value?: string) {
  return value ? `${Math.round(Number(value) * 100)}%` : "—";
}
function formatDate(value?: string | null) {
  if (!value) return "Henüz yok";
  return new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium" }).format(
    new Date(value),
  );
}
function humanStatus(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
function decimal(value: string | null) {
  return value === null ? "—" : Number(value).toFixed(3);
}
function money(value: string) {
  return Number(value).toFixed(2);
}
function budgetNote(value: string) {
  return Number(value) > 0 ? `$${money(value)} sınır` : "Sınır tanımsız";
}
function downloadJson(value: Record<string, unknown>, filename: string) {
  const blob = new Blob([JSON.stringify(value, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
