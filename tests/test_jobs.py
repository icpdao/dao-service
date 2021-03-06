import datetime
import decimal
import time
import random

import responses

from app import webhooks_route
from app.common.models.icpdao.dao import DAO, DAOFollow
from app.common.models.icpdao.icppership import Icppership, IcppershipProgress, IcppershipStatus
from app.common.models.icpdao.job import Job, JobPR, JobPRComment
from app.common.models.icpdao.user import User, UserStatus
from app.common.models.icpdao.user_github_token import UserGithubToken
from app.common.utils.errors import JOB_CREATE_ISSUE_REPEAT_ERROR
from tests.base import Base


def _get_github_user_id(github_login):
    random.seed(github_login)
    github_user_id = int(random.random() * 10000)
    random.seed()
    return github_user_id


class TestJobs(Base):
    create_job = """
mutation { 
  createJob(issueLink: "%s", size: %s, autoCreatePr: false) {
    job {
      node {
        id
        daoId
        cycleId
        createAt
        githubRepoName
        githubRepoOwner
        githubRepoId
        githubIssueNumber
        title
        status
        size
      }
    }
  }
}
"""

    query_jobs = """
query {
  jobs(daoName: "%s", beginTime: %s, endTime: %s, sorted: size, sortedType: desc) {
    job {
      ... on Job {
        node {
          id
          daoId
          userId
          size
          status
        }
        prs {
          id
          githubPrNumber
        }
      }
    }
    stat {
      size
      
    }
    total
  }
}    
"""

    query_other_user_jobs = """
    query {
      jobs(daoName: "%s", beginTime: %s, endTime: %s, sorted: size, sortedType: desc, userName: "%s") {
        job {
          ... on Job {
            node {
              id
              daoId
              userId
              size
              status
            }
            prs {
              id
              githubPrNumber
            }
          }
        }
        stat {
          size

        }
        total
      }
    }    
    """

    update_job_size = """
mutation {
  updateJob(id: "%s", size: %s, autoCreatePr: false) {
    job {
      ... on Job {
        node {
          ... on JobSchema {
            id
          }
        }
        prs {
          id
          githubPrNumber
        }
      }
    }
  }
}
"""
    update_job_pr = """
mutation {
  updateJob(id: "%s", size: %s, autoCreatePr: false, prs: [{id: %s, htmlUrl: "%s"}]) {
    job {
      ... on Job {
        node {
          ... on JobSchema {
            id
          }
        }
        prs {
          id
          githubPrNumber
        }
      }
    }
  }
}
"""
    delete_job_pr = """
mutation {
  updateJob(id: "%s", size: %s, autoCreatePr: false) {
    job {
      ... on Job {
        node {
          ... on JobSchema {
            id
          }
        }
        prs {
          id
          githubPrNumber
        }
      }
    }
  }
}
"""

    delete_job = """
mutation {
  deleteJob(id: "%s") {
    ok
  }
}
"""

    @classmethod
    def setup_class(cls):
        responses.add(
            responses.GET,
            'https://api.github.com/orgs/mockdao/installation',
            json={'id': 1, 'account': {'login': 'mockdao', 'id': 2, 'node_id': 'MDEyOk9yZ2FuaXphdGlvbjc4NzIwNzg5', 'avatar_url': 'https://avatars.githubusercontent.com/u/78720789?v=4', 'gravatar_id': '', 'url': 'https://api.github.com/users/icpdao', 'html_url': 'https://github.com/icpdao', 'followers_url': 'https://api.github.com/users/icpdao/followers', 'following_url': 'https://api.github.com/users/icpdao/following{/other_user}', 'gists_url': 'https://api.github.com/users/icpdao/gists{/gist_id}', 'starred_url': 'https://api.github.com/users/icpdao/starred{/owner}{/repo}', 'subscriptions_url': 'https://api.github.com/users/icpdao/subscriptions', 'organizations_url': 'https://api.github.com/users/icpdao/orgs', 'repos_url': 'https://api.github.com/users/icpdao/repos', 'events_url': 'https://api.github.com/users/icpdao/events{/privacy}', 'received_events_url': 'https://api.github.com/users/icpdao/received_events', 'type': 'Organization', 'site_admin': False}, 'repository_selection': 'all', 'access_tokens_url': 'https://api.github.com/app/installations/1/access_tokens', 'repositories_url': 'https://api.github.com/installation/repositories', 'html_url': 'https://github.com/organizations/icpdao/settings/installations/17334704', 'app_id': 111590, 'app_slug': 'icpdao-test', 'target_id': 78720789, 'target_type': 'Organization', 'permissions': {'issues': 'write', 'contents': 'write', 'metadata': 'read', 'single_file': 'write', 'pull_requests': 'write', 'organization_hooks': 'read'}, 'events': ['pull_request'], 'created_at': '2021-06-02T06:36:00.000Z', 'updated_at': '2021-06-04T18:09:14.000Z', 'single_file_name': 'file_bot', 'has_multiple_single_files': False, 'single_file_paths': ['file_bot'], 'suspended_by': None, 'suspended_at': None}
        )
        responses.add(
            responses.POST,
            'https://api.github.com/app/installations/1/access_tokens',
            json={'expires_at': '3021-06-04T18:09:14.000Z', 'token': 'mocktoken'},
            status=201
        )
        cls.icpper = cls.create_icpper_user("mockicpper", "mockicpper")
        cls.normal_user = cls.create_normal_user('mockuser1', 'mockuser1')
        cls.pre_icpper = cls.create_pre_icpper_user()
        UserGithubToken(
            github_user_id=cls.icpper.github_user_id,
            github_login=cls.icpper.github_login,
            access_token="xxxx",
            expires_in=1,
            refresh_token="xxx",
            refresh_token_expires_in=1,
            token_at=int(time.time())
        ).save()
        UserGithubToken(
            github_user_id=cls.pre_icpper.github_user_id,
            github_login=cls.pre_icpper.github_login,
            access_token="xxxx",
            expires_in=1,
            refresh_token="xxx",
            refresh_token_expires_in=1,
            token_at=int(time.time())
        ).save()
        UserGithubToken(
            github_user_id=cls.normal_user.github_user_id,
            github_login=cls.normal_user.github_login,
            access_token="xxxx",
            expires_in=1,
            refresh_token="xxx",
            refresh_token_expires_in=1,
            token_at=int(time.time())
        ).save()
        Icppership(
            progress=IcppershipProgress.ACCEPT.value,
            status=IcppershipStatus.PRE_ICPPER.value,
            icpper_github_login=(cls.pre_icpper.github_login),
            mentor_user_id=str(cls.icpper.id),
            icpper_user_id=str(cls.pre_icpper.id)
        ).save()

    def get_or_create_dao(self):
        dao = DAO.objects(name="mockdao").first()
        if dao:
            return str(dao.id)
        create_dao = """
mutation {
  createDao( name: "mockdao", desc: "mockdao", logo:"mockdao", timeZone: 8, timeZoneRegion: "Asia/Shanghai") {
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
        res = self.graph_query(str(self.icpper.id), create_dao)
        return res.json()['data']['createDao']['dao']['id']

    @responses.activate
    def test_create_job(self):
        DAOFollow.drop_collection()
        dao_id = self.get_or_create_dao()
        responses.add(
            responses.GET,
            "https://api.github.com/orgs/mockdao",
            json={
                'id': _get_github_user_id('mockdao')
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo",
            json={
                "id": 222,
                "name": "mockrepo",
                "owner": {
                    "id": _get_github_user_id("mockdao"),
                    "login": "mockdao"
                }
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/1",
            json={"user": {"login": "mockicpper", "id": _get_github_user_id("mockicpper")}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/1/comments",
            json={"id": 333}
        )
        mark_issue = "https://github.com/mockdao/mockrepo/issues/1"
        mark_size = 2.3

        assert DAOFollow.objects(user_id=str(self.icpper.id), dao_id=dao_id).first() is None

        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (mark_issue, str(mark_size))
        )

        assert res.status_code == 200
        data = res.json()
        assert data['data']['createJob']['job']['node']['daoId'] == dao_id
        assert data['data']['createJob']['job']['node']['githubRepoOwner'] == "mockdao"
        assert data['data']['createJob']['job']['node']['githubIssueNumber'] == 1
        assert data['data']['createJob']['job']['node']['size'] == 2.3

        assert DAOFollow.objects(user_id=str(self.icpper.id), dao_id=dao_id).first() is not None

        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (mark_issue, str(mark_size))
        )
        assert res.json()['errors'][0]['message'] == JOB_CREATE_ISSUE_REPEAT_ERROR

        # NTOE: ???????????????????????????
        # res = self.graph_query(
        #     str(self.normal_user.id),
        #     self.create_job % (mark_issue, str(mark_size))
        # )
        # assert res.json()['errors'][0]['message'] == 'error.mark_job.user_role'

        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (mark_issue, str(mark_size))
        )
        assert res.json()['errors'][0]['message'] == JOB_CREATE_ISSUE_REPEAT_ERROR

        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/2",
            json={"user": {"login": "xxx", "id": _get_github_user_id("xxx")}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        mark_issue = "https://github.com/mockdao/mockrepo/issues/2"
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/2/comments",
            json={"id": 444}
        )
        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (mark_issue, str(mark_size))
        )
        assert res.json()['errors'][0]['message'] == 'error.mark_job.issue_user'

    @responses.activate
    def test_pre_icpper_create_job(self):
        dao_id = self.get_or_create_dao()
        responses.add(
            responses.GET,
            "https://api.github.com/orgs/mockdao",
            json={
                'id': _get_github_user_id('mockdao')
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo",
            json={
                "id": 222,
                "name": "mockrepo",
                "owner": {
                    "id": _get_github_user_id("mockdao"),
                    "login": "mockdao"
                }
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/11",
            json={"user": {"login": self.pre_icpper.github_login, "id": _get_github_user_id(self.pre_icpper.github_login)}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/10",
            json={"user": {"login": self.pre_icpper.github_login,
                           "id": _get_github_user_id(self.pre_icpper.github_login)}, "state": "open", "title": "xxx",
                  "body": "xxx"}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/111",
            json={"user": {"login": self.pre_icpper.github_login,
                           "id": _get_github_user_id(self.pre_icpper.github_login)}, "state": "open", "title": "xxx",
                  "body": "xxx", 'id': 5551}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/11/comments",
            json={"id": 333}
        )
        mark_issue = "https://github.com/mockdao/mockrepo/issues/11"
        mark_size = 2.3
        res = self.graph_query(
            str(self.pre_icpper.id),
            self.create_job % (mark_issue, str(mark_size))
        )

        assert res.status_code == 200
        data = res.json()
        assert data['data']['createJob']['job']['node']['daoId'] == dao_id
        assert data['data']['createJob']['job']['node']['githubRepoOwner'] == "mockdao"
        assert data['data']['createJob']['job']['node']['githubIssueNumber'] == 11
        assert data['data']['createJob']['job']['node']['size'] == 2.3

        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/pulls/111",
            json={
                'user': {'login': self.pre_icpper.github_login, "id": _get_github_user_id(self.pre_icpper.github_login)},
                'id': 5551,
                'node_id': 'xxx',
                'number': 111,
                'state': 'open',
                'title': 'xxx',
                "merged_at": datetime.datetime.utcnow().isoformat(),
                "merged": True,
                "merged_by": {
                    "login": self.pre_icpper.github_login,
                    "id": _get_github_user_id(self.pre_icpper.github_login)
                },
                'created_at': '', 'updated_at': ''
            }
        )

        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/pulls/111/reviews",
            json={}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/333",
            json={}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/111/comments",
            json={'id': 7777}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/7777",
            json={'id': 8888}
        )
        res = self.graph_query(
            str(self.pre_icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        job_id = res.json()['data']['jobs']['job'][0]['node']['id']
        job_size = res.json()['data']['jobs']['job'][0]['node']['size']
        res = self.graph_query(
            str(self.pre_icpper.id),
            self.update_job_pr % (
                job_id, job_size,
                '5551', "https://github.com/mockdao/mockrepo/pull/111"
            )
        )
        assert res.json()['data']['updateJob']['job']['prs'][0]['githubPrNumber'] == 111
        assert res.json()['data']['updateJob']['job']['prs'][0]['id']

        pre_icpper = User.objects(id=str(self.pre_icpper.id)).first()
        icppership = Icppership.objects(icpper_github_login=str(self.pre_icpper.github_login)).first()
        assert pre_icpper.status == UserStatus.ICPPER.value
        assert icppership.progress == IcppershipProgress.ACCEPT.value
        assert icppership.status == IcppershipStatus.ICPPER.value

    @responses.activate
    def test_normal_create_job(self):
        dao_id = self.get_or_create_dao()
        responses.add(
            responses.GET,
            "https://api.github.com/orgs/mockdao",
            json={
                'id': _get_github_user_id('mockdao')
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo",
            json={
                "id": 222,
                "name": "mockrepo",
                "owner": {
                    "id": _get_github_user_id("mockdao"),
                    "login": "mockdao"
                }
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/13",
            json={"user": {"login": self.normal_user.github_login, "id": _get_github_user_id(self.normal_user.github_login)}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/12",
            json={"user": {"login": self.normal_user.github_login,
                           "id": _get_github_user_id(self.normal_user.github_login)}, "state": "open", "title": "xxx",
                  "body": "xxx"}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/211",
            json={"user": {"login": self.normal_user.github_login,
                           "id": _get_github_user_id(self.normal_user.github_login)}, "state": "open", "title": "xxx",
                  "body": "xxx", 'id': 5551}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/13/comments",
            json={"id": 433}
        )
        mark_issue = "https://github.com/mockdao/mockrepo/issues/13"
        mark_size = 2.3
        res = self.graph_query(
            str(self.normal_user.id),
            self.create_job % (mark_issue, str(mark_size))
        )

        assert res.status_code == 200
        data = res.json()
        assert data['data']['createJob']['job']['node']['daoId'] == dao_id
        assert data['data']['createJob']['job']['node']['githubRepoOwner'] == "mockdao"
        assert data['data']['createJob']['job']['node']['githubIssueNumber'] == 13
        assert data['data']['createJob']['job']['node']['size'] == 2.3

        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/pulls/211",
            json={
                'user': {'login': self.normal_user.github_login, "id": _get_github_user_id(self.normal_user.github_login)},
                'id': 5551,
                'node_id': 'xxx',
                'number': 211,
                'state': 'open',
                'title': 'xxx',
                "merged_at": datetime.datetime.utcnow().isoformat(),
                "merged": True,
                "merged_by": {
                    "login": self.normal_user.github_login,
                    "id": _get_github_user_id(self.normal_user.github_login)
                },
                'created_at': '', 'updated_at': ''
            }
        )

        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/pulls/211/reviews",
            json={}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/433",
            json={}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/211/comments",
            json={'id': 8777}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/8777",
            json={'id': 8888}
        )
        res = self.graph_query(
            str(self.normal_user.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        job_id = res.json()['data']['jobs']['job'][0]['node']['id']
        job_size = res.json()['data']['jobs']['job'][0]['node']['size']
        res = self.graph_query(
            str(self.normal_user.id),
            self.update_job_pr % (
                job_id, job_size,
                '5551', "https://github.com/mockdao/mockrepo/pull/211"
            )
        )
        assert res.json()['data']['updateJob']['job']['prs'][0]['githubPrNumber'] == 211
        assert res.json()['data']['updateJob']['job']['prs'][0]['id']

        normal_user = User.objects(id=str(self.normal_user.id)).first()
        assert normal_user.status == UserStatus.NORMAL.value

    @responses.activate
    def test_query_jobs(self):
        dao_id = self.get_or_create_dao()
        responses.add(
            responses.GET,
            "https://api.github.com/orgs/mockdao",
            json={
                'id': _get_github_user_id('mockdao')
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo",
            json={
                "id": 222,
                "name": "mockrepo",
                "owner": {
                    "id": _get_github_user_id("mockdao"),
                    "login": "mockdao"
                }
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/3",
            json={"user": {"login": "mockicpper", "id": _get_github_user_id("mockicpper")}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/3/comments",
            json={"id": 333}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/4",
            json={"user": {"login": "mockicpper", "id": _get_github_user_id("mockicpper")}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/4/comments",
            json={"id": 555}
        )
        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % ("https://github.com/mockdao/mockrepo/issues/3", "4.3")
        )

        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % ("https://github.com/mockdao/mockrepo/issues/4", "5.3")
        )

        res = self.graph_query(
            str(self.icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        assert len(res.json()['data']['jobs']['job']) == 3
        # 2.3 + 4.3 + 5.3 = 11.9
        assert str(res.json()['data']['jobs']['stat']['size']) == "11.9"

        res = self.graph_query(
            str(self.normal_user.id),
            self.query_other_user_jobs % ("mockdao", "0", str(int(time.time())), self.icpper.github_login)
        )
        assert len(res.json()['data']['jobs']['job']) == 3
        # 2.3 + 4.3 + 5.3 = 11.9
        assert str(res.json()['data']['jobs']['stat']['size']) == "11.9"

    @responses.activate
    def test_update_job_size(self):
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/333",
            json={}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/555",
            json={}
        )
        res = self.graph_query(
            str(self.icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        jobs = res.json()['data']['jobs']['job']
        job = jobs[0]
        res = self.graph_query(
            str(self.icpper.id),
            self.update_job_size % (job['node']['id'], str(3.4))
        )
        job = jobs[1]
        res = self.graph_query(
            str(self.icpper.id),
            self.update_job_size % (job['node']['id'], str(7.2))
        )
        job = jobs[2]
        res = self.graph_query(
            str(self.icpper.id),
            self.update_job_size % (job['node']['id'], str(13.1))
        )
        res = self.graph_query(
            str(self.icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        # 3.4 + 7.2 + 13.1  23.7
        assert res.json()['data']['jobs']['stat']['size'] == "23.7"

    @responses.activate
    def test_update_job_pr(self):
        responses.add(
            responses.GET,
            "https://api.github.com/orgs/mockdao",
            json={
                'id': _get_github_user_id('mockdao')
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/10",
            json={"user": {"login": self.pre_icpper.github_login,
                           "id": _get_github_user_id(self.pre_icpper.github_login)}, "state": "open", "title": "xxx",
                  "body": "xxx", 'id': 555}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/333",
            json={}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/pulls/10",
            json={
                'user': {'login': "mockicpper", "id": _get_github_user_id("mockicpper")},
                'id': 555,
                'node_id': 'xxx',
                'number': 10,
                'state': 'open',
                'title': 'xxx',
                'created_at': '', 'updated_at': ''
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo",
            json={
                'id': 222,
                "name": "mockrepo",
                "owner": {
                    "id": _get_github_user_id("mockdao"),
                    "login": "mockdao"
                }
            }
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/pulls/10/reviews",
            json={}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/555",
            json={}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/10/comments",
            json={'id': 777}
        )
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/777",
            json={'id': 888}
        )
        res = self.graph_query(
            str(self.icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        item_list = [item for item in Job.objects.all()]
        job_id = res.json()['data']['jobs']['job'][0]['node']['id']
        job_size = res.json()['data']['jobs']['job'][0]['node']['size']
        res = self.graph_query(
            str(self.icpper.id),
            self.update_job_pr % (
                job_id, job_size,
                "555", "https://github.com/mockdao/mockrepo/pull/10"
            )
        )
        assert res.json()['data']['updateJob']['job']['prs'][0]['githubPrNumber'] == 10
        assert res.json()['data']['updateJob']['job']['prs'][0]['id']
        res = self.graph_query(
            str(self.icpper.id),
            self.delete_job_pr % (
                job_id,
                job_size
            )
        )
        assert len(res.json()['data']['updateJob']['job']['prs']) == 0

    @responses.activate
    def test_webhooks(self):
        responses.add(
            responses.PATCH,
            "https://api.github.com/repos/mockdao/mockrepo/issues/comments/333",
            json={}
        )
        request_data = {
            "action": "closed",
            "number": 10,
            "pull_request": {
                "url": "xxx",
                "id": 555,
                "node_id": "MDExOlB1bGxSZXF1ZXN0Mjc5MTQ3NDM3",
                "number": 10,
                "state": "closed",
                "title": "Webhook Update",
                "user": {"login": "mockicpper"},
                "body": "Webhook Update Body",
                "merged_at": datetime.datetime.utcnow().isoformat(),
                "merged": True,
                "merged_by": {
                    "login": "mockuser1",
                    "id": _get_github_user_id("mockuser1")
                },
            },
            "repository": {
                "id": 222,
                "name": "mockrepo",
                "owner": {
                    "login": "mockdao",
                    "id": _get_github_user_id("mockdao")
                }
            }
        }
        res = self.graph_query(
            str(self.icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        res = self.client.post(
            webhooks_route,
            json=request_data
        )
        assert res.json()['success'] is True

    def test_delete_job(self):
        self.__class__.clear_db()
        self.icpper = self.__class__.create_icpper_user(nickname='icpper', github_login='iccper')
        self.icpper1 = self.__class__.create_icpper_user(nickname='icpper1', github_login='iccper1')
        self.icpper2 = self.__class__.create_icpper_user(nickname='icpper2', github_login='iccper2')
        dao_id = self.get_or_create_dao()
        job1 = Job(
            dao_id=dao_id,
            user_id=str(self.icpper1.id),
            title="111111",
            body_text="111111",
            github_repo_owner="mocklogin1",
            github_repo_name="mockreponame",
            github_repo_owner_id=_get_github_user_id('mocklogin1'),
            github_repo_id=1,
            github_issue_number=1,
            bot_comment_database_id=1,
            size=decimal.Decimal("1")
        ).save()
        job2 = Job(
            dao_id=dao_id,
            user_id=str(self.icpper2.id),
            title="222222",
            body_text="222222",
            github_repo_owner="mocklogin2",
            github_repo_name="mockreponame",
            github_repo_owner_id=_get_github_user_id('mocklogin2'),
            github_repo_id=1,
            github_issue_number=2,
            bot_comment_database_id=2,
            size=decimal.Decimal("1")
        ).save()
        job_pr1 = JobPR(
            job_id=str(job1.id),
            user_id=str(self.icpper1.id),
            title="1111111_pr",
            github_repo_owner="mocklogin1",
            github_repo_name="mockreponame",
            github_repo_owner_id=_get_github_user_id('mocklogin1'),
            github_repo_id=1,
            github_pr_number=3,
            github_pr_id=3
        ).save()
        job_pr2 = JobPR(
            job_id=str(job2.id),
            user_id=str(self.icpper2.id),
            title="222222_pr",
            github_repo_owner="mocklogin2",
            github_repo_name="mockreponame",
            github_repo_owner_id=_get_github_user_id('mocklogin2'),
            github_repo_id=1,
            github_pr_number=4,
            github_pr_id=4
        ).save()
        job_pr_comment1 = JobPRComment(
            github_repo_id=1,
            github_pr_number=job_pr1.github_pr_number,
            bot_comment_database_id=1
        ).save()
        job_pr_comment2 = JobPRComment(
            github_repo_id=1,
            github_pr_number=job_pr2.github_pr_number,
            bot_comment_database_id=1
        ).save()

        res = self.graph_query(
            str(self.icpper1.id),
            self.delete_job % str(job1.id)
        )

        assert res.json()['data']['deleteJob']['ok'] is True
        assert Job.objects.count() == 1
        assert JobPR.objects.count() == 1
        assert JobPRComment.objects.count() == 1
        assert Job.objects(id=str(job1.id)).first() is None
        assert JobPR.objects(id=str(job_pr1.id)).first() is None
        assert JobPRComment.objects(id=str(job_pr_comment1.id)).first() is None

        res = self.graph_query(
            str(self.icpper1.id),
            self.delete_job % str(job2.id)
        )

        assert res.json()['data']['deleteJob'] is None
        assert Job.objects.count() == 1
        assert JobPR.objects.count() == 1
        assert JobPRComment.objects.count() == 1
        assert Job.objects(id=str(job1.id)).first() is None
        assert JobPR.objects(id=str(job_pr1.id)).first() is None
        assert JobPRComment.objects(id=str(job_pr_comment1.id)).first() is None
