import time

from graphene import Mutation, String, Field, Int
from graphql import ResolveInfo

from app.common.models.icpdao.dao import DAOJobConfig
from app.common.schema.icpdao import DAOJobConfigSchema
from app.common.utils.access import check_is_dao_owner
from app.common.utils.route_helper import get_current_user_by_graphql


class UpdateDAOJobConfig(Mutation):
    class Arguments:
        dao_id = String(required=True)
        time_zone = Int()
        time_zone_region = String()
        deadline_day = Int()
        deadline_time = Int()
        pair_begin_day = Int()
        pair_begin_hour = Int()
        pair_end_day = Int()
        pair_end_hour = Int()
        voting_begin_day = Int()
        voting_begin_hour = Int()
        voting_end_day = Int()
        voting_end_hour = Int()

    job_config = Field(DAOJobConfigSchema)

    @staticmethod
    def mutate(root, info: ResolveInfo, dao_id, **kwargs):
        record = DAOJobConfig.objects(dao_id=dao_id).first()
        if not record:
            raise ValueError('NOT FOUND DAO')
        check_is_dao_owner(get_current_user_by_graphql(info), dao_id=dao_id)
        for field, value in kwargs.items():
            setattr(record, field, value)
        if len(kwargs) > 0:
            record.update_at = int(time.time())
        record.save()
        return UpdateDAOJobConfig(job_config=record)
