import time

from graphene import Mutation, String, Boolean

from app.common.models.icpdao.cycle import CycleVote, CycleVoteType, Cycle, \
    VoteResultTypeAllResultType
from app.common.models.icpdao.job import Job
from app.common.utils.route_helper import get_current_user_by_graphql


class UpdatePairVote(Mutation):
    class Arguments:
        id = String(required=True)
        vote_job_id = String(required=True)

    ok = Boolean()

    def mutate(self, info, id, vote_job_id):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        cycle_vote = CycleVote.objects(id=id).first()
        if not cycle_vote:
            raise ValueError('NOT FOUND VOTE')
        if cycle_vote.vote_type != CycleVoteType.PAIR.value:
            raise ValueError('NOT PAIR VOTE')
        if cycle_vote.voter_id != str(current_user.id):
            raise ValueError('NOT PERMISSION VOTE')
        cycle = Cycle.objects(id=cycle_vote.cycle_id).first()
        if not cycle:
            raise ValueError('NOT CYCLE')
        if not cycle.paired_at:
            raise ValueError('NOT PAIRED THIS CYCLE')
        now_at = int(time.time())
        if now_at < cycle.vote_begin_at or now_at > cycle.vote_end_at:
            raise ValueError('NOT VOTE TIME')
        if vote_job_id != cycle_vote.left_job_id and vote_job_id != cycle_vote.right_job_id:
            raise ValueError('NOT RIGHT VOTE')
        cycle_vote.vote_job_id = vote_job_id
        cycle_vote.updated_at = now_at
        cycle_vote.save()
        return UpdatePairVote(ok=True)


class UpdateALLVote(Mutation):
    class Arguments:
        id = String(required=True)
        vote = Boolean(required=True)

    ok = Boolean()

    def mutate(self, info, id, vote):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        cycle_vote = CycleVote.objects(id=id).first()
        if not cycle_vote:
            raise ValueError('NOT FOUND VOTE')
        if cycle_vote.vote_type != CycleVoteType.ALL.value:
            raise ValueError('NOT PAIR VOTE')

        cycle = Cycle.objects(id=cycle_vote.cycle_id).first()
        if not cycle:
            raise ValueError('NOT CYCLE')
        if not cycle.paired_at:
            raise ValueError('NOT PAIRED THIS CYCLE')

        now_at = int(time.time())
        if now_at < cycle.vote_begin_at or now_at > cycle.vote_end_at:
            raise ValueError('NOT VOTE TIME')

        voters = Job.objects(cycle_id=cycle_vote.cycle_id).distinct('user_id')
        if str(current_user.id) not in voters:
            raise ValueError('NOT PERMISSION VOTE')

        vote_result = VoteResultTypeAllResultType.YES.value if vote else VoteResultTypeAllResultType.NO.value
        exist_vote = cycle_vote.vote_result_type_all.filter(
            voter_id=str(current_user.id)).first()
        if exist_vote:
            exist_vote.result = vote_result
            exist_vote.updated_at = now_at
        else:
            cycle_vote.vote_result_type_all.create(
                voter_id=str(current_user.id), result=vote_result)
        yes_vote = cycle_vote.vote_result_type_all.filter(
            result=VoteResultTypeAllResultType.YES.value).count()

        cycle_vote.vote_result_stat_type_all = int(
            (yes_vote * 100) / len(voters))
        cycle_vote.updated_at = now_at
        cycle_vote.save()
        return UpdateALLVote(ok=True)
