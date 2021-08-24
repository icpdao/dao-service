import os
import time
from decimal import Decimal

from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.icppership import Icppership, IcppershipProgress, IcppershipStatus
from app.common.models.icpdao.job import Job, JobStatusEnum
from app.common.models.icpdao.user import User, UserStatus
from tests.base import Base

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class TestDAOs(Base):
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

    query_dao = """
query {
  dao(id: "%s") {
    datum {
      id
      name
      desc
      logo
      ownerId
    }
  }
}
"""

    query_dao_icpper = """
query {
  dao(id: "%s") {
    datum {
      id
      name
      desc
      logo
      ownerId
    }
    icppers(sorted: %s, sortedType: %s, first: %s, offset: %s) {
      nodes {
        user {
          id
        }
        jobCount
        size
        income
        joinTime
      }
      stat {
        icpperCount
        jobCount
        size
        income
      }
      total
    }
  }
}
"""

    query_dao_job = """
    query {
      dao(id: "%s") {
        datum {
          id
          name
          desc
          logo
          ownerId
        }
        jobs(sorted: %s, sortedType: %s, first: %s, offset: %s) {
          nodes {
            user {
              id
            }
            datum {
              id
              title
            }
          }
          stat {
            icpperCount
            jobCount
            size
            income
          }
          total
        }
      }
    }
    """

    update_dao_info = """
mutation {
  updateDaoBaseInfo(id: "%s", %s) {
    dao {
       id
       name
       desc
       logo
       updateAt
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
        cls.pre_icpper = cls.create_pre_icpper_user()
        Icppership(
            progress=IcppershipProgress.ACCEPT.value,
            status=IcppershipStatus.PRE_ICPPER.value,
            icpper_github_login=str(cls.pre_icpper.github_login),
            mentor_user_id=str(cls.icpper.id),
            icpper_user_id=str(cls.pre_icpper.id)
        ).save()

    def test_create_dao(self):
        dao_name='test_dao_1'
        ret = self.graph_query(self.user_1.id, self.create_dao % dao_name)
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]['message'] == 'NO ROLE'

        ret = self.graph_query(self.icpper.id, self.create_dao % dao_name)
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['createDao']['dao']['name'] == dao_name
        assert data['data']['createDao']['dao']['logo'] == dao_name
        assert data['data']['createDao']['dao']['ownerId'] == str(self.icpper.id)
        return data['data']['createDao']['dao']['id']

    def test_pre_icpper_create_dao(self):
        dao_name ='test_pre_icpper_create_dao'
        ret = self.graph_query(self.pre_icpper.id, self.create_dao % dao_name)
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['createDao']['dao']['name'] == dao_name
        assert data['data']['createDao']['dao']['ownerId'] == str(self.pre_icpper.id)

        pre_icpper = User.objects(id=str(self.pre_icpper.id)).first()
        icppership = Icppership.objects(icpper_github_login=str(self.pre_icpper.github_login)).first()
        assert pre_icpper.status == UserStatus.ICPPER.value
        assert icppership.progress == IcppershipProgress.ICPPER.value
        assert icppership.status == IcppershipStatus.ICPPER.value

        return data['data']['createDao']['dao']['id']

    def test_query_dao(self):
        dao_id = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_2'
        ).json()['data']['createDao']['dao']['id']
        ret = self.graph_query(self.user_1.id, self.query_dao % (dao_id))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['datum']['name'] == 'test_dao_2'
        assert data['data']['dao']['datum']['ownerId'] == str(self.icpper.id)
        assert data['data']['dao']['datum']['id']

        ret = self.graph_query(self.icpper.id, self.query_dao % (dao_id))
        assert ret.status_code == 200

    def test_query_dao_without_login(self):
        dao_id = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_21'
        ).json()['data']['createDao']['dao']['id']
        ret = self.graph_query_no_login(self.query_dao % (dao_id))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['datum']['name'] == 'test_dao_21'
        assert data['data']['dao']['datum']['ownerId'] == str(self.icpper.id)
        assert data['data']['dao']['datum']['id']


    def test_update_dao_base_info(self):
        dao_id = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_3'
        ).json()['data']['createDao']['dao']['id']
        ret = self.graph_query(
            self.user_1.id, self.update_dao_info % (
                dao_id, 'desc: "xxx"')
        )
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]["message"] == 'NOT RIGHT OWNER ACCESS'
        ret = self.graph_query(
            self.icpper.id, self.update_dao_info % (
                dao_id, 'desc: "xxx"')
        )
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['updateDaoBaseInfo']['dao']['desc'] == "xxx"

    def test_query_dao_icppers(self):
        self.__class__.clear_db()
        u1 = self.__class__.create_icpper_user("test_1", "test_github_login_1")
        u2 = self.__class__.create_icpper_user("test_2", "test_github_login_2")
        u3 = self.__class__.create_icpper_user("test_3", "test_github_login_3")
        dao = DAO(name="d1", owner_id=str(u1.id), github_owner_id=1, github_owner_name="d1").save()
        mock_data = [
            {'uid': str(u1.id), 'size': '1', 'income': '1.111'},
            {'uid': str(u1.id), 'size': '2.3', 'income': '222.222'},
            {'uid': str(u2.id), 'size': '4.5', 'income': '33.333'},
            {'uid': str(u2.id), 'size': '5.6', 'income': '4.44'},
            {'uid': str(u3.id), 'size': '7.8', 'income': '5.5'},
            {'uid': str(u3.id), 'size': '9.1', 'income': '6'},
        ]
        for d, i in enumerate(mock_data):
            Job(
                dao_id=str(dao.id), user_id=i['uid'], title=f'{d}-title',
                size=Decimal(i['size']), income=Decimal(i['income']), create_at=1 if d % 2 == 0 else int(time.time()),
                github_repo_owner="xxx", github_repo_name="xxx", github_repo_owner_id=1, github_repo_id=1,
                github_issue_number=1, bot_comment_database_id=1,
                status=JobStatusEnum.WAITING_FOR_TOKEN.value if d % 2 == 0 else JobStatusEnum.TOKEN_RELEASED.value
            ).save()
        res = self.graph_query(str(u1.id), self.query_dao_icpper % (str(dao.id), "joinTime", "desc", 20, 0))
        nodes = res.json()['data']['dao']['icppers']['nodes']
        stat = res.json()['data']['dao']['icppers']['stat']
        total = res.json()['data']['dao']['icppers']['total']
        assert total == 3
        assert len(nodes) == 3
        assert stat['icpperCount'] == 3
        assert stat['jobCount'] == 6
        assert int(float(stat['size'])) == int(float(sum([Decimal(d['size']) for d in mock_data])))
        assert int(float(stat['income'])) == int(float(sum([Decimal(d['income']) for d in mock_data])))
        return dao, u1

    def test_query_dao_jobs(self):
        dao, u1 = self.test_query_dao_icppers()
        res = self.graph_query(str(u1.id), self.query_dao_job % (str(dao.id), "updateAt", "desc", 20, 0))
        nodes = res.json()['data']['dao']['jobs']['nodes']
        stat = res.json()['data']['dao']['jobs']['stat']
        total = res.json()['data']['dao']['jobs']['total']
        assert len(nodes) == 6
        assert total == 6
        assert stat['icpperCount'] == 3
        assert stat['jobCount'] == 6
