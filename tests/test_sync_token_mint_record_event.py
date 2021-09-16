from app.controllers.sync_token_mint_record_event import test_run
from tests.base import Base


class TestSyncTokenMintRecordEvent(Base):
    def test_run_task(self):
        test_run()
