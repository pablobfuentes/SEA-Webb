from enum import Enum


class NodeType(str, Enum):
    PROBLEM = "problem"
    DECISION = "decision"
    CRITERION = "criterion"
    ALTERNATIVE = "alternative"
    ASSUMPTION = "assumption"
    CALCULATION = "calculation"
    CHECK = "check"
    DOCUMENT = "document"
    DIDACTIC = "didactic"
    OUTPUT = "output"


class BranchState(str, Enum):
    ACTIVE = "active"
    EXPLORED = "explored"
    DISCARDED = "discarded"
    PENDING = "pending"
    FAILED = "failed"
    APPROVED = "approved"
    ARCHIVED = "archived"


class NodeState(str, Enum):
    OPEN = "open"
    BLOCKED = "blocked"
    PENDING = "pending"
    COMPLETE = "complete"


class SourceType(str, Enum):
    USER_CONFIRMED = "user_confirmed"
    IMPORTED = "imported"
    ASSUMED = "assumed"
    CALCULATED = "calculated"


class AuthorityLevel(str, Enum):
    PRIMARY = "primary"
    COMPLEMENTARY = "complementary"
    CONTEXTUAL = "contextual"


class DocumentApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NormativeClassification(str, Enum):
    UNKNOWN = "unknown"
    PRIMARY_STANDARD = "primary_standard"
    SUPPORTING_DOCUMENT = "supporting_document"
    REFERENCE_DOCUMENT = "reference_document"


class DocumentCorpusPolicy(str, Enum):
    """How ingest/approve relate to the normative (active) corpus."""
    STRICT = "strict"
    APPROVE_ALSO_ACTIVATES = "approve_also_activates"
