from graphene import Enum


class DAOsFilterEnum(Enum):
    all = 0
    owner = 1
    following = 2
    following_and_owner = 3


class DAOsSortedEnum(Enum):
    number = 0
    following = 2
    job = 3
    size = 3
    token = 3


class DAOsSortedTypeEnum(Enum):
    asc = 0
    desc = 1


class DAOFollowTypeEnum(Enum):
    ADD = 0
    DELETE = 1
