import time

from app.common.models.icpdao.token import TokenMintRecord, MintRecordStatusEnum


def run_sync_token_mint_record_event_task(token_mint_record_id):
    record = TokenMintRecord.objects(id=token_mint_record_id).first()
    if not record:
        return

    last_sync_event_at = record.last_sync_event_at if record.last_sync_event_at else 0
    if int(time.time()) - last_sync_event_at <= 5 * 60:
        return

    if record.status == MintRecordStatusEnum.SUCCESS.value:
        if not record.stated:
            record.last_sync_event_at = int(time.time())
            record.save()
            _stat(record)
            return

    if record.status == MintRecordStatusEnum.PENDING.value:
        record.last_sync_event_at = int(time.time())
        record.save()
        _sync_event(record)
        record = TokenMintRecord.objects(id=token_mint_record_id).first()
        if record.status == MintRecordStatusEnum.SUCCESS.value:
            _stat(record)


def _sync_event(token_mint_record):
    mint_tx_hash = token_mint_record.mint_tx_hash
    chain_id = token_mint_record.chain_id
    token_contract_address = token_mint_record.token_contract_address
    # TODO
    """
    整理支持的 chain_id 列表，先简单几个
    发一个挖矿 event 作为测试用
    编写监控 event 代码
    
    mainnet  1
    ropsten  3
    kovan   42
    rinkeby 4 
    """
    pass


def _stat(token_mint_record):
    # TODO
    pass
