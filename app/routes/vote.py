import time

from graphene import Mutation, String, Boolean

from app.common.models.icpdao.cycle import CycleVote, CycleVoteType, Cycle, \
    VoteResultTypeAllResultType, CycleVoteConfirm, CycleVoteConfirmStatus
from app.common.models.icpdao.job import Job
from app.common.utils.errors import COMMON_NOT_AUTH_ERROR, CYCLE_NOT_FOUND_ERROR, CYCLE_VOTE_TIME_ERROR
from app.common.utils.route_helper import get_current_user_by_graphql


class UpdatePairVote(Mutation):
    class Arguments:
        id = String(required=True)
        vote_job_id = String(required=True)

    ok = Boolean()

    def mutate(self, info, id, vote_job_id):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError(COMMON_NOT_AUTH_ERROR)
        cycle_vote = CycleVote.objects(id=id).first()
        if not cycle_vote:
            raise ValueError('NOT FOUND VOTE')
        if cycle_vote.vote_type != CycleVoteType.PAIR.value:
            raise ValueError('NOT PAIR VOTE')
        if cycle_vote.voter_id != str(current_user.id):
            raise ValueError('NOT PERMISSION VOTE')
        cycle = Cycle.objects(id=cycle_vote.cycle_id).first()
        if not cycle:
            raise ValueError(CYCLE_NOT_FOUND_ERROR)
        if not cycle.paired_at:
            raise ValueError('NOT PAIRED THIS CYCLE')
        now_at = int(time.time())
        if now_at < cycle.vote_begin_at or now_at > cycle.vote_end_at:
            raise ValueError(CYCLE_VOTE_TIME_ERROR)
        cvc = CycleVoteConfirm.objects(cycle_id=str(cycle.id), voter_id=str(current_user.id)).first()
        assert cvc, "errors.vote.no_confirm_record"
        assert cvc.status == CycleVoteConfirmStatus.WAITING.value, "errors.vote.already_confirm"
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
            raise PermissionError(COMMON_NOT_AUTH_ERROR)
        cycle_vote = CycleVote.objects(id=id).first()
        if not cycle_vote:
            raise ValueError('NOT FOUND VOTE')
        if cycle_vote.vote_type != CycleVoteType.ALL.value:
            raise ValueError('NOT ALL VOTE')

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

        cvc = CycleVoteConfirm.objects(cycle_id=str(cycle.id), voter_id=str(current_user.id)).first()
        assert cvc, "errors.vote.no_confirm_record"
        assert cvc.status == CycleVoteConfirmStatus.WAITING.value, "errors.vote.already_confirm"

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


class UpdateVoteConfirm(Mutation):
    class Arguments:
        cycle_id = String(required=True)
        signature_msg = String(required=True)
        signature_address = String(required=True)
        signature = String(required=True)

    ok = Boolean()

    def mutate(self, info, cycle_id, signature_msg, signature_address, signature):
        current_user = get_current_user_by_graphql(info)
        assert current_user, "errors.common.not_login"

        cvc = CycleVoteConfirm.objects(cycle_id=cycle_id, voter_id=str(current_user.id)).first()
        assert cvc, "errors.vote_confirm.notfound"

        cycle_pair_unvote = CycleVote.objects(
            cycle_id=cycle_id, voter_id=str(current_user.id), vote_job_id__existed=False
        ).all()

        assert len(cycle_pair_unvote) > 0, 'errors.vote_confirm.had_un_vote'
        cvc.signature_address = signature_address
        cvc.signature = signature
        cvc.signature_msg = signature_msg
        cvc.update_at = int(time.time())
        cvc.status = CycleVoteConfirmStatus.CONFIRM.value
        cvc.save()
        return UpdateVoteConfirm(ok=True)
