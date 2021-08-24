from typing import Optional, Any
from enum import Enum as PyEnum
from graphene import Enum

from app.common.models.icpdao.cycle import CycleVotePairTaskStatus, CycleVoteResultStatTaskStatus, \
    VoteResultTypeAllResultType, CycleVoteResultPublishTaskStatus
from app.common.models.icpdao.job import JobPairTypeEnum
from app.common.schema import BaseObjectArgs


class DAOsFilterEnum(Enum):
    all = 0
    owner = 1
    following = 2
    following_and_owner = 3
    member = 4


class CycleFilterEnum(Enum):
    processing = 0
    pairing = 1
    voting = 2
    un_vote_end = 3


class CyclesQueryArgs(BaseObjectArgs):
    dao_id: str
    filter: Optional[list]


class CyclesTokenUnreleasedQueryArgs(BaseObjectArgs):
    last_timestamp: int


class DAOJobConfigQueryArgs(BaseObjectArgs):
    dao_id: str


class CommonPaginationArgs(BaseObjectArgs):
    query: Any
    first: int
    offset: int


class DAOsSortedEnum(Enum):
    number = 0
    following = 2
    job = 3
    size = 3
    token = 3


class JobSortedEnum(Enum):
    size = 0
    income = 1


class DAOsSortedTypeEnum(Enum):
    asc = 0
    desc = 1


class SortedTypeEnum(Enum):
    asc = 0
    desc = 1


class DAOFollowTypeEnum(Enum):
    ADD = 0
    DELETE = 1


class CycleIcpperStatSortedEnum(Enum):
    jobCount = 0
    size = 1
    income = 2


class CycleIcpperStatSortedTypeEnum(Enum):
    asc = 0
    desc = 1


class ICPPERsQuerySortedEnum(Enum):
    joinTime = 'join_time'
    jobCount = 'job_count'
    size = 'size_sum'
    income = 'income_sum'


class ICPPERsQuerySortedTypeEnum(Enum):
    asc = 0
    desc = 1


class JobsQuerySortedEnum(Enum):
    size = 'size'
    income = 'income'
    updateAt = 'update_at'


class JobsQuerySortedTypeEnum(Enum):
    asc = 0
    desc = 1


class JobsQueryPairTypeEnum(Enum):
    pair = JobPairTypeEnum.PAIR.value
    all = JobPairTypeEnum.ALL.value


class CycleVotePairTaskStatusEnum(Enum):
    INIT = CycleVotePairTaskStatus.INIT.value
    PAIRING = CycleVotePairTaskStatus.PAIRING.value
    SUCCESS = CycleVotePairTaskStatus.SUCCESS.value
    FAIL = CycleVotePairTaskStatus.FAIL.value


class UpdateJobVoteTypeByOwnerArgumentPairTypeEnum(Enum):
    pair = JobPairTypeEnum.PAIR.value
    all = JobPairTypeEnum.ALL.value


class CreateCycleVotePairTaskByOwnerStatusEnum(Enum):
    INIT = CycleVotePairTaskStatus.INIT.value
    PAIRING = CycleVotePairTaskStatus.PAIRING.value
    SUCCESS = CycleVotePairTaskStatus.SUCCESS.value
    FAIL = CycleVotePairTaskStatus.FAIL.value


class CreateCycleVoteResultStatTaskByOwnerStatusEnum(Enum):
    INIT = CycleVoteResultStatTaskStatus.INIT.value
    STATING = CycleVoteResultStatTaskStatus.STATING.value
    SUCCESS = CycleVoteResultStatTaskStatus.SUCCESS.value
    FAIL = CycleVoteResultStatTaskStatus.FAIL.value


class CycleVoteResultStatTaskStatusEnum(Enum):
    INIT = CycleVoteResultStatTaskStatus.INIT.value
    STATING = CycleVoteResultStatTaskStatus.STATING.value
    SUCCESS = CycleVoteResultStatTaskStatus.SUCCESS.value
    FAIL = CycleVoteResultStatTaskStatus.FAIL.value


class CycleVoteResultTypeAllResultTypeEnum(Enum):
    YES = VoteResultTypeAllResultType.YES.value
    NO = VoteResultTypeAllResultType.NO.value


class CreateCycleVoteResultPublishTaskByOwnerStatusEnum(Enum):
    INIT = CycleVoteResultPublishTaskStatus.INIT.value
    RUNNING = CycleVoteResultPublishTaskStatus.RUNNING.value
    SUCCESS = CycleVoteResultPublishTaskStatus.SUCCESS.value
    FAIL = CycleVoteResultPublishTaskStatus.FAIL.value


class CycleVoteResultPublishTaskStatusEnum(Enum):
    INIT = CycleVoteResultPublishTaskStatus.INIT.value
    RUNNING = CycleVoteResultPublishTaskStatus.RUNNING.value
    SUCCESS = CycleVoteResultPublishTaskStatus.SUCCESS.value
    FAIL = CycleVoteResultPublishTaskStatus.FAIL.value
