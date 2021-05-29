import os

from tests.base import Base
from unittest import TestCase

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class TestJobConfig(Base):
    create_dao = """
mutation {
  createDao( name: "%s", desc: "test_dao_1", logo:"test_dao_1", timeZone: 8, timeZoneRegion: "Asia/Shanghai") {
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
}  
"""

    update_job_config = """
mutation {
  updateDaoJobConfig(daoId: "%s", %s) {
    jobConfig {
      id
      deadlineDay
      %s
    }
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

    def test_query_job_config(self):

        ret = self.graph_query(self.icpper.id, self.create_dao % 'test_dao_1')
        dao_id = ret.json()['data']['createDao']['dao']['id']

        ret = self.graph_query(self.user_2.id, self.query_job_config % dao_id)
        # if normal user can't read dao job config,
        # this status_code should be 400
        assert ret.status_code == 200

        ret2 = self.graph_query(self.icpper.id, self.query_job_config % dao_id)
        assert ret2.status_code == 200
        TestCase().assertDictEqual(ret.json(), ret2.json())
        assert ret.json()['data']['daoJobConfig']['timeZone'] == 8
        assert ret.json()['data']['daoJobConfig']['daoId'] == dao_id
        assert ret.json()['data']['daoJobConfig']['deadlineDay'] == 1
        assert ret.json()['data']['daoJobConfig']['deadlineTime'] == 12

    def test_update_job_config(self):
        ret = self.graph_query(self.icpper.id, self.create_dao % 'test_dao_2')
        dao_id = ret.json()['data']['createDao']['dao']['id']
        ret = self.graph_query(
            self.user_2.id,
            self.update_job_config % (
                dao_id, "pairEndDay: 17", "pairEndDay"
            )
        )
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]['message'] == 'NOT RIGHT OWNER ACCESS'

        ret = self.graph_query(
            self.icpper.id,
            self.update_job_config % (
                dao_id, "pairEndDay: 17", "pairEndDay"
            )
        )
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['updateDaoJobConfig']['jobConfig']['pairEndDay'] == 17
        assert data['data']['updateDaoJobConfig']['jobConfig']['deadlineDay'] == 1

        ret = self.graph_query(
            self.icpper.id,
            self.update_job_config % (
                dao_id, "pairBeginDay: 17, votingBeginDay: 18", "pairBeginDay votingBeginDay"
            )
        )
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['updateDaoJobConfig']['jobConfig']['pairBeginDay'] == 17
        assert data['data']['updateDaoJobConfig']['jobConfig']['deadlineDay'] == 1
        assert data['data']['updateDaoJobConfig']['jobConfig']['votingBeginDay'] == 18

        ret = self.graph_query(
            self.icpper.id,
            self.update_job_config % (
                dao_id, 'timeZone: 480, timeZoneRegion: "Asia/Beijing"', "timeZone timeZoneRegion"
            )
        )
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['updateDaoJobConfig']['jobConfig']['timeZone'] == 480
        assert data['data']['updateDaoJobConfig']['jobConfig']['timeZoneRegion'] == "Asia/Beijing"


