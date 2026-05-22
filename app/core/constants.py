"""Shared enumerations and policy constants for the RAG monolith."""
from enum import Enum


class Role(str, Enum):
    ADMIN = "Admin"
    SECURITY_ANALYST = "Security Analyst"
    HR = "HR"
    FINANCE = "Finance"
    ENGINEERING = "Engineering"
    MANAGER = "Manager"
    EMPLOYEE = "Employee"
    GUEST = "Guest"


class SensitivityTier(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    STRICT_CONFIDENTIAL = "STRICT_CONFIDENTIAL"


class HandlingLabel(str, Enum):
    ALLOW = "ALLOW"
    MASK = "MASK"
    TOKENIZE = "TOKENIZE"
    HASH = "HASH"
    DROP = "DROP"


class EntityType(str, Enum):
    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    EMP_ID = "EMP_ID"
    CUSTOMER_ID = "CUSTOMER_ID"
    CONTRACT_NUMBER = "CONTRACT_NUMBER"
    ACCOUNT_NUMBER = "ACCOUNT_NUMBER"
    PROJECT_NAME = "PROJECT_NAME"
    API_KEY = "API_KEY"
    CONFIDENTIAL_PHRASE = "CONFIDENTIAL_PHRASE"
    FINANCIAL_FIGURE = "FINANCIAL_FIGURE"


ALL_ROLES = [r.value for r in Role]

# Ordered low -> high. Used for clearance comparisons.
TIER_ORDER = {
    SensitivityTier.PUBLIC.value: 0,
    SensitivityTier.INTERNAL.value: 1,
    SensitivityTier.CONFIDENTIAL.value: 2,
    SensitivityTier.STRICT_CONFIDENTIAL.value: 3,
}

# Default clearance ceiling per role.
ROLE_CLEARANCE = {
    Role.ADMIN.value: SensitivityTier.STRICT_CONFIDENTIAL.value,
    Role.SECURITY_ANALYST.value: SensitivityTier.STRICT_CONFIDENTIAL.value,
    Role.HR.value: SensitivityTier.CONFIDENTIAL.value,
    Role.FINANCE.value: SensitivityTier.CONFIDENTIAL.value,
    Role.ENGINEERING.value: SensitivityTier.CONFIDENTIAL.value,
    Role.MANAGER.value: SensitivityTier.INTERNAL.value,
    Role.EMPLOYEE.value: SensitivityTier.INTERNAL.value,
    Role.GUEST.value: SensitivityTier.PUBLIC.value,
}

# How each detected entity type is handled during sanitization.
ENTITY_HANDLING = {
    EntityType.PERSON.value: HandlingLabel.TOKENIZE.value,
    EntityType.EMAIL.value: HandlingLabel.TOKENIZE.value,
    EntityType.PHONE.value: HandlingLabel.TOKENIZE.value,
    EntityType.EMP_ID.value: HandlingLabel.TOKENIZE.value,
    EntityType.CUSTOMER_ID.value: HandlingLabel.TOKENIZE.value,
    EntityType.CONTRACT_NUMBER.value: HandlingLabel.TOKENIZE.value,
    EntityType.ACCOUNT_NUMBER.value: HandlingLabel.TOKENIZE.value,
    EntityType.PROJECT_NAME.value: HandlingLabel.TOKENIZE.value,
    EntityType.FINANCIAL_FIGURE.value: HandlingLabel.HASH.value,
    EntityType.CONFIDENTIAL_PHRASE.value: HandlingLabel.MASK.value,
    EntityType.API_KEY.value: HandlingLabel.DROP.value,
}

# Sensitivity tier a tokenized value belongs to (gates de-tokenization).
ENTITY_TOKEN_TIER = {
    EntityType.PERSON.value: SensitivityTier.CONFIDENTIAL.value,
    EntityType.EMAIL.value: SensitivityTier.CONFIDENTIAL.value,
    EntityType.PHONE.value: SensitivityTier.CONFIDENTIAL.value,
    EntityType.EMP_ID.value: SensitivityTier.CONFIDENTIAL.value,
    EntityType.CUSTOMER_ID.value: SensitivityTier.CONFIDENTIAL.value,
    EntityType.PROJECT_NAME.value: SensitivityTier.CONFIDENTIAL.value,
    EntityType.FINANCIAL_FIGURE.value: SensitivityTier.CONFIDENTIAL.value,
    EntityType.CONTRACT_NUMBER.value: SensitivityTier.STRICT_CONFIDENTIAL.value,
    EntityType.ACCOUNT_NUMBER.value: SensitivityTier.STRICT_CONFIDENTIAL.value,
    EntityType.API_KEY.value: SensitivityTier.STRICT_CONFIDENTIAL.value,
}


def tier_rank(tier: str) -> int:
    return TIER_ORDER.get(tier, 0)
