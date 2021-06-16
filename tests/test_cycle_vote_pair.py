import time

from app.common.models.icpdao.cycle import Cycle, CycleVotePairTask, CycleVotePairTaskStatus
from app.common.models.icpdao.dao import DAO
from tests.base import Base


class TestCycleVotePair(Base):
    create_pair_task = """
mutation{
    createCycleVotePairTaskByOwner(cycleId: "%s"){
        status
    }
}
"""

    @staticmethod
    def get_cycle_time_by_end_at(end_at):
        begin_at = end_at - 30 * 24 * 60 * 60
        end_at = end_at
        pair_begin_at = end_at + 12 * 60 * 60
        pair_end_at = pair_begin_at + 18 * 60 * 60
        vote_begin_at = pair_end_at
        vote_end_at = vote_begin_at + 18 * 60 * 60

        return begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at

    def test_create_pair_task(self):
        # creat dao
        # creat cycle
        self.__class__.clear_db()
        self.icpper = self.__class__.create_icpper_user()
        self.icpper2 = self.__class__.create_icpper_user()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper.id)
        )
        test_dao.save()

        end_at = time.time()
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_2 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_2.save()

        end_at = test_cycle_2.begin_at
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_1 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=time.time() - 60 * 60,
            pair_end_at=time.time() + 60 * 60,
            vote_begin_at=time.time() + 2 * 60 * 60,
            vote_end_at=time.time() + 3 * 60 * 60,
        )
        test_cycle_1.save()

        # time range
        res = self.graph_query(
            self.icpper.id, self.create_pair_task % str(test_cycle_2.id)
        )
        assert not not res.json()['errors']

        # not owner
        res = self.graph_query(
            self.icpper2.id, self.create_pair_task % str(test_cycle_1.id)
        )
        assert not not res.json()['errors']

        # no old
        res = self.graph_query(
            self.icpper.id, self.create_pair_task % str(test_cycle_1.id)
        )

        assert res.json()['data']['createCycleVotePairTaskByOwner']['status'] == 'INIT'
        assert CycleVotePairTask.objects.count() == 1
        assert CycleVotePairTask.objects.first().status == CycleVotePairTaskStatus.INIT.value

        # have old task sttatus is init pairing
        res = self.graph_query(
            self.icpper.id, self.create_pair_task % str(test_cycle_1.id)
        )

        assert res.json()['data']['createCycleVotePairTaskByOwner']['status'] == 'INIT'
        assert CycleVotePairTask.objects.count() == 1
        assert CycleVotePairTask.objects.first().status == CycleVotePairTaskStatus.INIT.value

        # have old task sttatus is fail
        old_task = CycleVotePairTask.objects.first()
        old_task.status = CycleVotePairTaskStatus.FAIL.value
        old_task.save()
        time.sleep(1)
        res = self.graph_query(
            self.icpper.id, self.create_pair_task % str(test_cycle_1.id)
        )

        assert res.json()['data']['createCycleVotePairTaskByOwner']['status'] == 'INIT'
        assert CycleVotePairTask.objects.count() == 2
        assert CycleVotePairTask.objects.order_by('-id').first().status == CycleVotePairTaskStatus.INIT.value

        time.sleep(1)
        # is paired re pair
        old_task = CycleVotePairTask.objects.order_by('-id').first()
        old_task.status = CycleVotePairTaskStatus.SUCCESS.value
        old_task.save()
        test_cycle_1.paired_at = time.time()
        test_cycle_1.save()

        res = self.graph_query(
            self.icpper.id, self.create_pair_task % str(test_cycle_1.id)
        )

        assert res.json()['data']['createCycleVotePairTaskByOwner']['status'] == 'INIT'
        assert CycleVotePairTask.objects.count() == 3
        assert CycleVotePairTask.objects.order_by('-id').first().status == CycleVotePairTaskStatus.INIT.value
