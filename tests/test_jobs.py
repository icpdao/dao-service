import datetime
import time

import responses

from app import webhooks_route
from app.common.models.icpdao.dao import DAO
from tests.base import Base


class TestJobs(Base):
    create_job = """
mutation { 
  createJob(daoId: "%s", issueLink: "%s", size: %s) {
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
    update_job_size = """
mutation {
  updateJob(id: "%s", size: %s) {
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
  updateJob(id: "%s", addPr: "%s") {
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
  updateJob(id: "%s", deletePr: "%s") {
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
        cls.normal_user = cls.create_normal_user('mockuser1')

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
        dao_id = self.get_or_create_dao()
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo",
            json={"id": 222}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/1",
            json={"user": {"login": "mockicpper"}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/1/comments",
            json={"id": 333}
        )
        mark_issue = "https://github.com/mockdao/mockrepo/issues/1"
        mark_size = 2.3
        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (dao_id, mark_issue, str(mark_size))
        )
        assert res.status_code == 200
        data = res.json()
        assert data['data']['createJob']['job']['node']['daoId'] == dao_id
        assert data['data']['createJob']['job']['node']['githubRepoOwner'] == "mockdao"
        assert data['data']['createJob']['job']['node']['githubIssueNumber'] == 1
        assert data['data']['createJob']['job']['node']['size'] == 2.3

        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (dao_id, mark_issue, str(mark_size))
        )
        assert res.json()['errors'][0]['message'] == 'THIS ISSUE HAD EXIST'

        res = self.graph_query(
            str(self.normal_user.id),
            self.create_job % (dao_id, mark_issue, str(mark_size))
        )
        assert res.json()['errors'][0]['message'] == 'ONLY ICPPER CAN MARK JOB'

        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % ("60bd826e9778eaccaf0cd9ca", mark_issue, str(mark_size))
        )
        assert res.json()['errors'][0]['message'] == 'NOT DAO'

        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/2",
            json={"user": {"login": "xxx"}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        mark_issue = "https://github.com/mockdao/mockrepo/issues/2"
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/2/comments",
            json={"id": 444}
        )
        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (dao_id, mark_issue, str(mark_size))
        )
        assert res.json()['errors'][0]['message'] == 'ONLY ISSUE USER CAN MARK THIS ISSUE'

    @responses.activate
    def test_query_jobs(self):
        dao_id = self.get_or_create_dao()
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo",
            json={"id": 222}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/3",
            json={"user": {"login": "mockicpper"}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/3/comments",
            json={"id": 333}
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/4",
            json={"user": {"login": "mockicpper"}, "state": "open", "title": "xxx", "body": "xxx"}
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/mockdao/mockrepo/issues/4/comments",
            json={"id": 555}
        )
        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (dao_id, "https://github.com/mockdao/mockrepo/issues/3", "4.3")
        )

        res = self.graph_query(
            str(self.icpper.id),
            self.create_job % (dao_id, "https://github.com/mockdao/mockrepo/issues/4", "5.3")
        )

        res = self.graph_query(
            str(self.icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        assert len(res.json()['data']['jobs']['job']) == 3
        assert res.json()['data']['jobs']['stat']['size'] == 2.3 + 4.3 + 5.3

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
        assert res.json()['data']['jobs']['stat']['size'] == 3.4 + 7.2 + 13.1

    @responses.activate
    def test_update_job_pr(self):
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/pulls/10",
            json={
                'user': {'login': "mockicpper"},
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
            json={'id': 222}
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
        job_id = res.json()['data']['jobs']['job'][0]['node']['id']
        res = self.graph_query(
            str(self.icpper.id),
            self.update_job_pr % (
                job_id,
                "https://github.com/mockdao/mockrepo/pull/10"
            )
        )
        assert res.json()['data']['updateJob']['job']['prs'][0]['githubPrNumber'] == 10
        assert res.json()['data']['updateJob']['job']['prs'][0]['id']
        res = self.graph_query(
            str(self.icpper.id),
            self.delete_job_pr % (
                job_id,
                res.json()['data']['updateJob']['job']['prs'][0]['id']
            )
        )
        assert len(res.json()['data']['updateJob']['job']['prs']) == 0

    @responses.activate
    def test_webhooks(self):
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
                },
            },
            "repository": {
                "id": 222,
                "name": "mockrepo",
                "owner": {
                    "login": "mockdao"
                }
            }
        }
        res = self.graph_query(
            str(self.icpper.id),
            self.query_jobs % ("mockdao", "0", str(int(time.time())))
        )
        print(res.json())
        res = self.client.post(
            webhooks_route,
            json=request_data
        )
        assert res.json()['success'] is True
