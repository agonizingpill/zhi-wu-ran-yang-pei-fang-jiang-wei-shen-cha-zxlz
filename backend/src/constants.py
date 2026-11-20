from enum import StrEnum
class Role(StrEnum):
    ADMIN='admin'
    COLORIST='colorist'
    VIEWER='viewer'
class TrialState(StrEnum):
    DRAFT='draft'
    VERIFIED='verified'
    APPROVED='approved'
    REJECTED='rejected'
