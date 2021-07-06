import iso8601
import datetime

from starlette.background import BackgroundTasks
from starlette.types import Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette import status

import settings
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.job import JobPR, JobPRStatusEnum
from app.common.utils.github_app import GithubAppClient
from app.controllers.task import sync_job_issue_status_comment


class GithubWebhooksApp:

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        request = Request(scope, receive=receive)
        response = await self.handler(request)
        await response(scope, receive, send)

    async def handler(self, request: Request) -> Response:
        if request.method != 'POST':
            return PlainTextResponse(
                "No GraphQL query found in the request",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        req_data = await request.json()
        background = BackgroundTasks()
        if req_data.get('pull_request') and req_data.get(
                'pull_request').get('url'):
            await self.handler_pr(req_data, background)
            return JSONResponse(
                {"success": True}, status_code=status.HTTP_200_OK,
                background=background
            )
        return JSONResponse(
            {"success": False}, status_code=status.HTTP_404_NOT_FOUND,
            background=background
        )

    async def handler_pr(self, data, background):
        need_check_jobs = set()
        repo_owner = data['repository']['owner']['login']
        repo_name = data['repository']['name']
        repo_id = data['repository']['id']
        pr_title = data['pull_request']['title']
        if data.get('action') == 'closed' and data['pull_request']['merged'] is True:
            merged_time = iso8601.parse_date(
                data['pull_request']['merged_at'])
            merged_at = int(
                merged_time.replace(tzinfo=datetime.timezone.utc).timestamp())
            JobPR.objects(
                github_repo_owner=repo_owner,
                github_repo_name=repo_name,
                github_repo_id=repo_id,
                github_pr_number=data['pull_request']['number']
            ).update(
                status=JobPRStatusEnum.MERGED.value,
                title=pr_title,
                merged_user_github_user_id=data['pull_request']['merged_by']['id'],
                merged_at=merged_at
            )
            job_ids = JobPR.objects(
                github_repo_owner=repo_owner,
                github_repo_name=repo_name,
                github_repo_id=repo_id,
                github_pr_number=data['pull_request']['number']
            ).distinct('job_id')
            need_check_jobs = need_check_jobs | set(job_ids)

        if len(need_check_jobs) > 0:
            app_token = GithubAppToken.get_token(
                app_id=settings.ICPDAO_GITHUB_APP_ID,
                app_private_key=settings.ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY,
                dao_name=repo_owner
            )
            if app_token is None:
                raise ValueError('NOT APP TOKEN')
            app_client = GithubAppClient(app_token, repo_owner)
            background.add_task(
                sync_job_issue_status_comment, app_client, need_check_jobs)
