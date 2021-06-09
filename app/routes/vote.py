import time

from graphene import ObjectType, List, Field, Int


from app.common.models.icpdao.cycle import CycleVote, CycleVoteType, Cycle
from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.job import Job
from app.common.schema.icpdao import CycleVoteSchema
from app.common.utils.route_helper import get_current_user_by_graphql


class Votes(ObjectType):
    vote = List(CycleVoteSchema)
    total = Int()

    def query_vote_list(self, info, dao_id, first=20, offset=0):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise ValueError('NOT CURRENT USER')
        dao = DAO.objects(id=dao_id).first()
        if not dao:
            raise ValueError('NOT DAO')
        last_cycle = Cycle.objects(dao_id=dao_id).order_by('-end_at').first()
        if not last_cycle:
            raise ValueError('NOT LAST CYCLE')
        now = int(time.time())
        if now < last_cycle.vote_begin_at or now >= last_cycle.vote_end_at:
            raise ValueError('NOT VOTE TIME')

        all_type_vote = CycleVote.objects(
            dao_id=dao_id, cycle_id=str(last_cycle.id),
            vote_type=CycleVoteType.ALL.value
        ).all()

        pair_type_vote = CycleVote.objects(
            dao_id=dao_id, cycle_id=str(last_cycle.id),
            vote_type=CycleVoteType.PAIR.value,
            voter_id=str(current_user.id)
        ).all()
