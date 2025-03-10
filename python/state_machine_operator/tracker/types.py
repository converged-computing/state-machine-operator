from dataclasses import dataclass
from enum import Enum

true_options = ["true", True, "1", 1]


# We need to handle conflict
class SubmissionCode(Enum):
    OK = 0
    ERROR = 1
    CONFLICT = 2


class CancelCode(Enum):
    OK = 0
    ERROR = 1


@dataclass
class JobSubmission:
    status: SubmissionCode
    return_code: int = 0


@dataclass
class JobSetup:
    name: str
    nodes: int
    cores_per_task: int
    script: str = None
    walltime: str = None
    gpus: int = 0
    workdir: str = None
