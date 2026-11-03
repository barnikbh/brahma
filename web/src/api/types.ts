// C8 (core API, incl. R-02 additions) and C9 (knowledge API) shapes, as the U4 and U5
// servers send them (camelCase JSON). The server is the source of truth.

export const DISCLAIMER = "Decision support, not diagnosis";

export interface ApiErrorBody {
  error: { code: string; message: string; retryable?: boolean };
}

// --- Identity and session ------------------------------------------------------------

export type Role = "doctor" | "reviewer" | "system";

export interface Profile {
  profileId: string;
  displayName: string;
  role: Role;
  specialty?: string | null;
  demoRegistration?: string | null;
  listed?: boolean;
}

export interface CurrentModel {
  provider: string;
  model: string;
}

export interface SessionView {
  profile: Profile;
  packVersions: string;
  needsDisclaimer: boolean;
  disclaimer: { version: string; text: string };
  provider: CurrentModel;
}

export interface Feature {
  name: string;
  version?: string;
  screens?: string[];
}

export interface Health {
  status: "ok" | "degraded";
  packs: { pack: string; number: string }[];
  provider: CurrentModel;
  database: string;
  disclaimer: string;
}

// --- Patients and cases --------------------------------------------------------------

export type Sex = "female" | "male" | "unknown";
export type CaseStatus = "new" | "needs_data" | "answered" | "out_of_knowledge" | "follow_up_due";

export interface NewPatient {
  syntheticName: string;
  age: number;
  sex: Sex;
  weightKg?: number | null;
  pregnancyStatus?: string | null;
  comorbidities?: string[];
  allergies?: string[];
  currentMedication?: string[];
}

export interface Patient extends NewPatient {
  patientId: string;
}

export type PatientChange = Partial<Omit<NewPatient, "syntheticName">>;

export interface PackVersionRef {
  pack: string;
  number: string;
}

export interface Case {
  caseId: string;
  patientId: string;
  ownerProfileId: string;
  pinnedPackVersion: PackVersionRef | null;
  origin: "clinic" | "benchmark";
  status: CaseStatus;
  synthetic: true;
  createdAt: string;
  updatedAt: string;
}

export interface CaseSummary {
  caseId: string;
  patientId: string;
  syntheticName: string;
  status: CaseStatus;
  updatedAt: string;
}

export type MessageKind = "text" | "form" | "form_answer" | "pathway" | "map_action";

export interface Message {
  messageId: string;
  caseId: string;
  author: "doctor" | "brahma" | "system";
  kind: MessageKind;
  body: Record<string, unknown>;
  formKind: string | null;
  formState: "open" | "submitted" | null;
  createdAt: string;
}

export type ValidationState = "ok" | "invalid" | "conflict" | "confirm_range";

export interface Finding {
  findingId: string;
  caseId: string;
  kind: string;
  name: string;
  value: number | string | null;
  unit: string | null;
  enteredValue: string | null;
  duration: string | null;
  validationState: ValidationState;
  nodeId: string | null;
}

export type WalkStatus = "paused" | "answered" | "needs_data" | "out_of_knowledge" | "error";

export interface WalkState {
  walkId: string;
  status: WalkStatus;
  waitingFor: string | null;
  lastSectionDone: number | null;
  counts: WalkCounts;
  packVersion: string | null;
  /** Chat text now starts a follow-up turn (the walk has ended). */
  canFollowUp?: boolean;
}

export interface CaseView {
  case: Case;
  patient: Patient;
  messages: Message[];
  formDrafts: Record<string, Record<string, unknown>>;
  findings: Finding[];
  pinnedVersion: string | null;
  newerVersion: string | null;
  lock: LockState;
  walk: WalkState | null;
  disclaimer: string;
}

export type LockState = "held" | "read_only";

// --- Walk (SSE) ------------------------------------------------------------------------

export type WalkMode = "start" | "continue" | "rewalk" | "explore" | "stop_explore" | "follow_up";

export interface WalkRequest {
  mode: WalkMode;
  text?: string | null;
  formMessageId?: string | null;
  formValues?: Record<string, unknown> | null;
  branchNodeId?: string | null;
  walkId?: string | null;
}

export type FormKind = "confirm-findings" | "needs-data" | "edit-treatment" | "patient-details";

export interface FormField {
  name: string;
  label: string;
  kind: "finding" | "test_result";
  findingKind?: string | null;
  value?: number | string | null;
  unit?: string | null;
  duration?: string | null;
  nodeId?: string | null;
  options?: string[] | null;
  validationState?: string | null;
}

export type ProgressStep =
  | "reading_findings"
  | "matching_diagnosis"
  | "refining"
  | "planning_treatment"
  | "checking_sources"
  | "writing_explanation";

export interface WalkCounts {
  steps: number;
  cited: number;
  ungrounded: number;
}

export type MapStatus =
  | "used"
  | "entry"
  | "test_needed"
  | "not_in_pack"
  | "bypassed"
  | "not_taken"
  | "exploring"
  | "tried"
  | "option"
  | "planned"
  | "chosen";

/** How a prior therapy went, from the doctor's treatment history. */
export type TherapyResponse = "failed" | "lost_response" | "intolerant" | "responded";

export type MapColumn = "findings" | "diagnosis" | "tests" | "subtype" | "treatment" | "monitor";

export interface MapNode {
  nodeId: string;
  type: string;
  label: string;
  column: MapColumn | string;
  status: MapStatus;
  /** A test result (`value`) or, for a prior therapy, how it went (`response`). */
  result: { value?: string; response?: TherapyResponse } | null;
}

export interface MapEdge {
  edgeId: string;
  from: string;
  to: string;
  style: "walked" | "bypassed" | "not_taken" | "exploring";
}

export interface MapData {
  version: string;
  nodes: MapNode[];
  edges: MapEdge[];
  selectedPath: string[];
  exploreLanes?: { laneId: string; nodeIds: string[] }[];
}

export interface DonePayload {
  walkId: string;
  sessionId: string | null;
  outcome: "answered" | "needs_data" | "out_of_knowledge";
  counts: WalkCounts;
  packVersion: string;
  provider: string;
  model: string;
  disclaimer: string;
  previousPackVersion?: string;
  message?: string;
  offers: string[];
  /** Chat text after this walk starts a follow-up turn (treatment history). */
  followUp?: boolean;
}

export interface TherapyHistoryItem {
  drug: string;
  response: TherapyResponse;
  nodeIds: string[];
}

export type WalkEvent =
  | { type: "progress"; payload: { step: ProgressStep } }
  | {
      type: "form";
      payload: { kind: FormKind; messageId: string; walkId: string; fields: FormField[] };
    }
  | { type: "paused"; payload: { walkId: string; waitingFor: string } }
  | {
      type: "map_update";
      payload: { walkId: string; laneId?: string; nodes: MapNode[]; edges: MapEdge[] };
    }
  | {
      type: "line";
      payload: { sectionId: string; text: string; nodeIds: string[]; laneId?: string };
    }
  | {
      type: "section_done";
      payload: { walkId: string; sectionId: string; title: string; laneId?: string };
    }
  | { type: "done"; payload: DonePayload }
  | {
      type: "error";
      payload: { code: string; message: string; retryable: boolean; walkId?: string | null };
    }
  | { type: "lane_closed"; payload: { walkId: string; laneId: string; branchNodeId: string } }
  | {
      type: "history";
      payload: { walkId: string; text: string; therapies: TherapyHistoryItem[] };
    };

export type WalkEventType = WalkEvent["type"];

// --- Nodes ---------------------------------------------------------------------------

export interface Source {
  sourceId: string;
  title: string;
  year: number;
  section: string;
  url?: string | null;
}

export interface GraphNode {
  nodeId: string;
  packVersion?: PackVersionRef | null;
  type: string;
  label: string;
  content: string;
  fields: Record<string, unknown>;
  sourceIds: string[];
  column: string;
  alternative?: boolean;
}

export interface NodeComment {
  commentId: string;
  nodeId: string;
  authorProfileId: string;
  text: string;
  createdAt: string;
}

export interface SafetyResult {
  check: "allergy" | "pregnancy" | "interaction" | "duplicate_class";
  status: "ok" | "conflict" | "not_checked";
  nodeIds: string[];
  message: string;
  drugNodeId: string;
}

export type DoseNote = { value: number; unit: string; formula: string } | { missing: string };

export interface TreatmentEdit {
  editId: string;
  caseId: string;
  nodeId: string;
  original: Record<string, unknown>;
  newValues: Record<string, unknown>;
  editorProfileId: string;
  createdAt: string;
}

export interface NodeDetail {
  node: GraphNode;
  sources: Source[];
  comments: NodeComment[];
  safety: SafetyResult[];
  dose: DoseNote | null;
  edited: TreatmentEdit | null;
  updated?: NodeUpdated | null;
  initialVersion?: string;
  packVersion: string | null;
  disclaimer: string;
}

export interface EditOutcome {
  edit: TreatmentEdit;
  dose: { value: number; unit: string; formula: string } | { nodeId: string; message: string };
  safety: SafetyResult[];
}

export interface TraverseResponse {
  map: MapData;
  notice: string;
}

// --- Sessions (history) ----------------------------------------------------------------

export type Outcome = "answered" | "needs_data" | "out_of_knowledge" | "error";

export interface SessionSummary {
  sessionId: string;
  caseId: string;
  createdAt: string;
  label: string;
  outcome: Outcome;
  packVersion: string;
}

export interface AnswerLine {
  text: string;
  nodeIds: string[];
}

export interface AnswerSection {
  sectionId: string;
  title: string;
  lines: AnswerLine[];
}

export interface SessionRecord {
  sessionId: string;
  createdAt: string;
  caseId: string;
  walkId: string;
  profileId: string;
  packVersion: string;
  provider: string;
  model: string;
  inputs: { text: string; findings: Record<string, unknown>[] };
  pathNodeIds: string[];
  answer: { summary: string; sections: AnswerSection[]; counts: Partial<WalkCounts> };
  sources: string[];
  explanation: AnswerLine[];
  outcome: Outcome;
}

export interface AuditEntry {
  entryId: string;
  createdAt: string;
  kind: string;
  caseId?: string | null;
  sessionId?: string | null;
  profileId: string;
  packVersion?: string | null;
  payload: Record<string, unknown>;
}

export interface SessionDetail {
  record: SessionRecord;
  entries: AuditEntry[];
  map: MapData;
  disclaimer: string;
}

// --- Knowledge (C9) ----------------------------------------------------------------------

export type ProposalStatus = "proposed" | "published" | "rejected";

export interface ProposalChange {
  nodeId: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown>;
  sourcePassage: string | null;
  sourceUrl?: string | null;
  copyFlag: boolean;
}

export interface Proposal {
  proposalId: string;
  pack: string;
  baseVersion: string;
  targetVersion: string;
  proposerProfileId: string;
  proposerName?: string | null;
  reviewerName?: string | null;
  origin: "doctor" | "drafted" | "scheduled";
  comment: string;
  status: ProposalStatus;
  sourceId: string | null;
  reviewerProfileId: string | null;
  reviewComment: string | null;
  publishedVersion: string | null;
  createdAt: string;
  decidedAt: string | null;
  changes: ProposalChange[];
  copyFlaggedNodeIds: string[];
  /** New links into the graph, and the pack sources the changes cite. */
  changeSet?: { addEdges?: { fromNodeId: string; toNodeId: string }[] };
  citedSources?: Source[];
}

export interface ProposalIn {
  pack: string;
  nodeId: string;
  change: Record<string, unknown>;
  comment: string;
  sourceUrl?: string | null;
  section?: string | null;
}

export interface VersionHistoryEntry {
  version: string;
  status: "live" | "superseded" | "proposed" | "rejected";
  date: string;
  author: string;
  authorName?: string | null;
  change: string;
  comment: string | null;
  proposalId: string | null;
}

/** Who last updated a node, who approved it, and when (set when a proposal is published). */
export interface NodeUpdated {
  nodeId: string;
  updatedBy: string;
  updatedByName: string;
  approvedBy: string;
  approvedByName: string;
  updatedAt: string;
  version: string;
  proposalId: string;
}

export interface PackInfo {
  pack: string;
  name: string;
  liveVersion: string;
  versions: string[];
}

export interface BrowseNode {
  nodeId: string;
  type: string;
  label: string;
  column: string;
  updatedAt: string | null;
}

export interface BrowseEdge {
  edgeId: string;
  from: string;
  to: string;
  relation: string;
  label: string;
}

export interface PackGraph {
  pack: string;
  version: string;
  initialVersion: string;
  nodes: BrowseNode[];
  edges: BrowseEdge[];
}

export interface Neighbour {
  edgeId: string;
  nodeId: string;
  type: string;
  label: string;
  relation: string;
  relationLabel: string;
}

export interface BrowseDetail {
  node: GraphNode;
  sources: Source[];
  comments: NodeComment[];
  outgoing: Neighbour[];
  incoming: Neighbour[];
  updated: NodeUpdated | null;
  initialVersion: string;
  packVersion: string;
}

export interface ThreadMessage {
  position: number;
  role: "doctor" | "assistant";
  text: string;
  proposalId: string | null;
  createdAt: string;
}

export interface UpdateThread {
  threadId: string;
  pack: string;
  profileId: string;
  profileName?: string | null;
  status: "open" | "proposed" | "stuck";
  rounds: number;
  createdAt: string;
  updatedAt: string;
  messages: ThreadMessage[];
  proposals: Proposal[];
}
