import os
import time

from app.common.models.icpdao.cycle import Cycle
from tests.base import Base
from unittest import TestCase
from freezegun import freeze_time

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class TestJobConfig(Base):
    create_dao = """
mutation {
  createDao( name: "%s", desc: "test_dao_1", logo:"test_dao_1", timeZone: 480, timeZoneRegion: "Asia/Shanghai") {
    dao {
      id
      name
      logo
      number
      ownerId
      desc
    }
  }
}
"""

    query_job_config = """
query {
  daoJobConfig(daoId: "%s") {
    datum {
      id
      daoId
      deadlineDay
      deadlineTime
      pairBeginDay
      pairBeginHour
      pairEndDay
      pairEndHour
      votingBeginDay
      votingBeginHour
      votingEndDay
      votingEndHour
      timeZone
      createAt
      updateAt
    }
    thisCycle {
      timeZone
      beginAt
      endAt
      pairBeginAt
      pairEndAt
      voteBeginAt
      voteEndAt
    }
    existedLastCycle {
      timeZone
      beginAt
      endAt
      pairBeginAt
      pairEndAt
      voteBeginAt
      voteEndAt
    }
    
    previewNextCycle(%s) {
      timeZone
      beginAt
      endAt
      pairBeginAt
      pairEndAt
      voteBeginAt
      voteEndAt
    }
    
    getNextCycle {
      timeZone
      beginAt
      endAt
      pairBeginAt
      pairEndAt
      voteBeginAt
      voteEndAt    
    }
  }
}  
"""

    update_job_config = """
mutation {
  updateDaoJobConfig(daoId: "%s", %s) {
    ok
  }
}
"""

    @classmethod
    def setup_class(cls):
        # mock user
        cls.icpper = cls.create_icpper_user()
        cls.user_1 = cls.create_normal_user('test_user_1')
        cls.user_2 = cls.create_normal_user('test_user_2')
        cls.user_3 = cls.create_normal_user('test_user_3')

    def _get_preview_next_cycle(self):
        return "timeZone: 480, deadlineDay: 10, deadlineTime: 0, pairBeginDay: 10, pairBeginHour: 0, pairEndDay: 12, pairEndHour: 0, votingBeginDay: 12, votingBeginHour: 0, votingEndDay: 14, votingEndHour: 0"

    def test_query_job_config(self):
        with freeze_time("2012-01-12 12:00:01", tz_offset=8):
            ret = self.graph_query(self.icpper.id, self.create_dao % 'test_dao_1')
            dao_id = ret.json()['data']['createDao']['dao']['id']

            ret = self.graph_query(self.user_2.id, self.query_job_config % (dao_id, self._get_preview_next_cycle()))
            # if normal user can't read dao job config,
            # this status_code should be 400
            assert ret.status_code == 200

            ret2 = self.graph_query(self.icpper.id, self.query_job_config % (dao_id, self._get_preview_next_cycle()))
            assert ret2.status_code == 200
            TestCase().assertDictEqual(ret.json()['data']['daoJobConfig']['datum'], ret2.json()['data']['daoJobConfig']['datum'])
            assert ret.json()['data']['daoJobConfig']['datum']['timeZone'] == 480
            assert ret.json()['data']['daoJobConfig']['datum']['daoId'] == dao_id
            assert ret.json()['data']['daoJobConfig']['datum']['deadlineDay'] == 1
            assert ret.json()['data']['daoJobConfig']['datum']['deadlineTime'] == 12

            assert ret.json()['data']['daoJobConfig']['existedLastCycle'] is None

            assert ret.json()['data']['daoJobConfig']['previewNextCycle']['timeZone'] == 480
            assert ret.json()['data']['daoJobConfig']['getNextCycle']['timeZone'] == 480

            assert ret.json()['data']['daoJobConfig']['previewNextCycle']['beginAt'] == 1326369601
            assert ret.json()['data']['daoJobConfig']['previewNextCycle']['endAt'] == 1328803200

            assert ret.json()['data']['daoJobConfig']['getNextCycle']['beginAt'] == 1326369601
            assert ret.json()['data']['daoJobConfig']['getNextCycle']['endAt'] == 1328068800

            Cycle(
                dao_id=dao_id,
                time_zone=ret.json()['data']['daoJobConfig']['getNextCycle']['timeZone'],
                begin_at=ret.json()['data']['daoJobConfig']['getNextCycle']['beginAt'],
                end_at=ret.json()['data']['daoJobConfig']['getNextCycle']['endAt'],
                pair_begin_at=ret.json()['data']['daoJobConfig']['getNextCycle']['pairBeginAt'],
                pair_end_at=ret.json()['data']['daoJobConfig']['getNextCycle']['pairEndAt'],
                vote_begin_at=ret.json()['data']['daoJobConfig']['getNextCycle']['voteBeginAt'],
                vote_end_at=ret.json()['data']['daoJobConfig']['getNextCycle']['voteEndAt']
            ).save()

            ret = self.graph_query(self.icpper.id, self.query_job_config % (dao_id, self._get_preview_next_cycle()))
            assert ret.status_code == 200
            assert ret.json()['data']['daoJobConfig']['datum']['timeZone'] == 480
            assert ret.json()['data']['daoJobConfig']['datum']['daoId'] == dao_id
            assert ret.json()['data']['daoJobConfig']['datum']['deadlineDay'] == 1
            assert ret.json()['data']['daoJobConfig']['datum']['deadlineTime'] == 12

            assert ret.json()['data']['daoJobConfig']['existedLastCycle']['timeZone'] == 480
            assert ret.json()['data']['daoJobConfig']['existedLastCycle']['endAt'] == 1328068800

            assert ret.json()['data']['daoJobConfig']['previewNextCycle']['timeZone'] == 480
            assert ret.json()['data']['daoJobConfig']['getNextCycle']['timeZone'] == 480

            assert ret.json()['data']['daoJobConfig']['previewNextCycle']['beginAt'] == 1328068800
            assert ret.json()['data']['daoJobConfig']['previewNextCycle']['endAt'] == 1328803200

            assert ret.json()['data']['daoJobConfig']['getNextCycle']['beginAt'] == 1328068800
            assert ret.json()['data']['daoJobConfig']['getNextCycle']['endAt'] == 1330574400

    def test_update_job_config(self):
        ret = self.graph_query(self.icpper.id, self.create_dao % 'test_dao_2')
        dao_id = ret.json()['data']['createDao']['dao']['id']
        ret = self.graph_query(
            self.user_2.id,
            self.update_job_config % (
                dao_id, "pairEndDay: 17"
            )
        )
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]['message'] == 'NOT RIGHT OWNER ACCESS'

        ret = self.graph_query(
            self.icpper.id,
            self.update_job_config % (
                dao_id, "pairEndDay: 17"
            )
        )
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]['message'] == 'error.update_dao_job_config.illegal'

        ret = self.graph_query(
            self.icpper.id,
            self.update_job_config % (
                dao_id, "deadlineDay: 15, pairBeginDay: 16, "
                        "pairEndDay: 17, votingBeginDay: 18, votingEndDay: 20"
            )
        )
        assert ret.status_code == 200

        ret = self.graph_query(
            self.icpper.id,
            self.update_job_config % (
                dao_id, 'timeZone: 480, timeZoneRegion: "Asia/Beijing"'
            )
        )
        assert ret.status_code == 200
