from web3 import Web3

from app.common.models.icpdao.token import TokenMintRecord, MintRecordStatusEnum
from app.controllers.sync_token_mint_record_event import get_eth_node_url, TOKEN_ABI
from settings import ICPDAO_ETH_TOKEN_FACTORY_DEPLOY_BLACK_NUMBER


def run_find_lost_tx_for_drop_token_mint_record_task(dao_id, token_contract_address, chain_id):
    token_mint_record_query = TokenMintRecord.objects(
        dao_id=dao_id,
        token_contract_address=token_contract_address,
        chain_id=chain_id,
        status__ne=MintRecordStatusEnum.FAIL.value
    ).order_by("-start_timestamp").limit(100)

    no_fail_record_list = [record for record in token_mint_record_query]

    need_find_lost_record_list = []
    last_success_record = None
    for record in no_fail_record_list:
        if record.status == MintRecordStatusEnum.SUCCESS.value:
            last_success_record = record
            break
        if record.status == MintRecordStatusEnum.DROPED.value:
            need_find_lost_record_list.append(record)

    from_black_number = ICPDAO_ETH_TOKEN_FACTORY_DEPLOY_BLACK_NUMBER
    if last_success_record:
        from_black_number = last_success_record.block_number

    web3 = Web3(Web3.WebsocketProvider(get_eth_node_url(last_success_record.chain_id)))
    token = web3.eth.contract(address=Web3.toChecksumAddress(last_success_record.token_contract_address),
                              abi=TOKEN_ABI)
    tef = token.events["Mint"].createFilter(fromBlock=from_black_number, toBlock="latest")

    for log in tef.get_all_entries():
        mint_tx_hash = Web3.toHex(log["transactionHash"])
        _mintTokenAddressList = log["args"]["_mintTokenAddressList"]
        _mintTokenAmountRatioList = log["args"]["_mintTokenAmountRatioList"]
        _startTimestamp = log["args"]["_startTimestamp"]
        _endTimestamp = log["args"]["_endTimestamp"]
        _tickLower = log["args"]["_tickLower"]
        _tickUpper = log["args"]["_tickUpper"]

        for record in need_find_lost_record_list:
            eq1 = _mintTokenAddressList == record.mint_token_address_list
            eq2 = _mintTokenAmountRatioList == record.mint_token_amount_ratio_list
            eq3 = _startTimestamp == record.start_timestamp
            eq4 = _endTimestamp == record.end_timestamp
            eq5 = _tickLower == record.tick_lower
            eq6 = _tickUpper == record.tick_upper

            if eq1 and eq2 and eq3 and eq4 and eq5 and eq6:
                tr = TokenMintRecord.objects(
                    dao_id=dao_id,
                    token_contract_address=token_contract_address,
                    chain_id=chain_id,
                    mint_tx_hash=mint_tx_hash,
                ).first()
                if not tr:
                    record.mint_tx_hash = mint_tx_hash
                    record.status = MintRecordStatusEnum.PENDING.value
                    record.save()
                    break
