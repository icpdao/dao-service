import time
import hashlib

from graphene import Mutation, String, Field, Int, ObjectType, Boolean
from graphql import ResolveInfo

import settings
from app.common.models.icpdao.dao import DAOJobConfig as DAOJobConfigModel
from app.common.models.icpdao.cycle import Cycle
from app.common.schema import BaseObjectType
from app.common.schema.icpdao import DAOJobConfigSchema
from app.common.utils import get_next_time
from app.common.utils.access import check_is_dao_owner
from app.common.utils.route_helper import get_current_user_by_graphql
from app.controllers.task import create_cycle_by_params


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

    ok = Boolean()

    @staticmethod
    def mutate(root, info: ResolveInfo, dao_id, **kwargs):
        record = DAOJobConfigModel.objects(dao_id=dao_id).first()
        if not record:
            raise ValueError('NOT FOUND DAO')
        check_is_dao_owner(get_current_user_by_graphql(info), dao_id=dao_id)
        for field, value in kwargs.items():
            setattr(record, field, value)
        if len(kwargs) > 0:
            record.update_at = int(time.time())
        if float(f'{record.deadline_day}.{record.deadline_time}') <= float(
                f'{record.pair_begin_day}.{record.pair_begin_hour}') <= float(
            f'{record.pair_end_day}.{record.pair_end_hour}') <= float(
            f'{record.voting_begin_day}.{record.voting_begin_hour}') <= float(
              f'{record.voting_end_day}.{record.voting_end_hour}'):
            record.save()
            return UpdateDAOJobConfig(ok=True)
        raise ValueError('error.update_dao_job_config.illegal')


class DAOJobThisCycle(ObjectType):
    time_zone = Int()
    begin_at = Int()
    end_at = Int()
    pair_begin_at = Int()
    pair_end_at = Int()
    vote_begin_at = Int()
    vote_end_at = Int()


class DAOTokenConfig(BaseObjectType):
    eth_dao_id = String()

    def resolve_eth_dao_id(self, info):
        current_user = get_current_user_by_graphql(info)
        assert current_user, 'NOT LOGIN'
        check_is_dao_owner(current_user, dao_id=self._args.dao_id)
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            bytes(self._args.dao_id, encoding='utf-8'),
            bytes(settings.ICPDAO_ETH_DAO_ID_SALT, encoding='utf-8'),
            100000,
            12
        )
        return dk.hex()


class DAOJobConfig(BaseObjectType):
    datum = Field(DAOJobConfigSchema)
    this_cycle = Field(DAOJobThisCycle)

    def resolve_datum(self, info):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        record = DAOJobConfigModel.objects(dao_id=self._args.dao_id).first()
        return record

    def resolve_this_cycle(self, info):
        current_user = get_current_user_by_graphql(info)
        assert current_user, 'NOT LOGIN'
        now_time = int(time.time())
        processing_cycle = Cycle.objects(
            dao_id=self._args.dao_id,
            begin_at__lte=now_time,
            end_at__gt=now_time,
        ).first()
        if processing_cycle:
            return DAOJobThisCycle(
                time_zone=processing_cycle.time_zone,
                begin_at=processing_cycle.begin_at,
                end_at=processing_cycle.end_at,
                pair_begin_at=processing_cycle.pair_begin_at,
                pair_end_at=processing_cycle.pair_end_at,
                vote_begin_at=processing_cycle.vote_begin_at,
                vote_end_at=processing_cycle.vote_end_at,
            )
        newest_cycle = Cycle.objects(
            dao_id=self._args.dao_id).order_by("-begin_at").first()
        if not newest_cycle:
            begin_at = now_time
            return get_predict_cycle(self._args.dao_id, begin_at)
        if newest_cycle and now_time >= newest_cycle.end_at:
            begin_at = newest_cycle.end_at
            return get_predict_cycle(self._args.dao_id, begin_at)
        raise ValueError('NOT MATCH CYCLE')


def get_predict_cycle(dao_id, begin_at):
    config = DAOJobConfigModel.objects(dao_id=dao_id).first()
    end_at = get_next_time(
        config.time_zone, int(time.time()),
        config.deadline_day, config.deadline_time, False)
    pair_begin_at = get_next_time(
        config.time_zone, end_at,
        config.pair_begin_day, config.pair_begin_hour, True)
    pair_end_at = get_next_time(
        config.time_zone, pair_begin_at,
        config.pair_end_day, config.pair_end_hour, False)
    vote_begin_at = get_next_time(
        config.time_zone, pair_end_at,
        config.voting_begin_day, config.voting_begin_hour, True)
    vote_end_at = get_next_time(
        config.time_zone, vote_begin_at,
        config.voting_end_day, config.voting_end_hour, False)

    return DAOJobThisCycle(
        time_zone=config.time_zone,
        begin_at=begin_at, end_at=end_at,
        pair_begin_at=pair_begin_at, pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at, vote_end_at=vote_end_at)
