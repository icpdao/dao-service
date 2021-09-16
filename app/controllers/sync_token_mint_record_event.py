import time

import decimal
import traceback
from collections import defaultdict

from web3 import Web3
from web3.exceptions import TransactionNotFound

from app.common.models.icpdao.cycle import CycleIcpperStat, Cycle
from app.common.models.icpdao.job import Job, JobStatusEnum
from app.common.models.icpdao.token import TokenMintRecord, MintRecordStatusEnum, TokenTransferEventLog, \
    MentorTokenIncomeStat

from settings import ICPDAO_ETH_TOKEN_FACTORY_DEPLOY_BLACK_NUMBER

TOKEN_ABI = """
  [
    {
      "inputs": [
        {
          "internalType": "address[]",
          "name": "_genesisTokenAddressList",
          "type": "address[]"
        },
        {
          "internalType": "uint256[]",
          "name": "_genesisTokenAmountList",
          "type": "uint256[]"
        },
        {
          "internalType": "uint256",
          "name": "_lpRatio",
          "type": "uint256"
        },
        {
          "internalType": "address",
          "name": "_stakingAddress",
          "type": "address"
        },
        {
          "internalType": "address payable",
          "name": "_ownerAddress",
          "type": "address"
        },
        {
          "components": [
            {
              "internalType": "uint128",
              "name": "p",
              "type": "uint128"
            },
            {
              "internalType": "uint16",
              "name": "aNumerator",
              "type": "uint16"
            },
            {
              "internalType": "uint16",
              "name": "aDenominator",
              "type": "uint16"
            },
            {
              "internalType": "uint16",
              "name": "bNumerator",
              "type": "uint16"
            },
            {
              "internalType": "uint16",
              "name": "bDenominator",
              "type": "uint16"
            },
            {
              "internalType": "uint16",
              "name": "c",
              "type": "uint16"
            },
            {
              "internalType": "uint16",
              "name": "d",
              "type": "uint16"
            }
          ],
          "internalType": "struct MintMath.MintArgs",
          "name": "_mintArgs",
          "type": "tuple"
        },
        {
          "internalType": "string",
          "name": "_erc20Name",
          "type": "string"
        },
        {
          "internalType": "string",
          "name": "_erc20Symbol",
          "type": "string"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "constructor"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "address",
          "name": "_manager",
          "type": "address"
        }
      ],
      "name": "AddManager",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "owner",
          "type": "address"
        },
        {
          "indexed": true,
          "internalType": "address",
          "name": "spender",
          "type": "address"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "value",
          "type": "uint256"
        }
      ],
      "name": "Approval",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "operator",
          "type": "address"
        },
        {
          "indexed": false,
          "internalType": "uint256[]",
          "name": "tokenIdList",
          "type": "uint256[]"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "token0TotalAmount",
          "type": "uint256"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "token1TotalAmount",
          "type": "uint256"
        }
      ],
      "name": "BonusWithdrawByTokenIdList",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "_baseTokenAmount",
          "type": "uint256"
        },
        {
          "indexed": false,
          "internalType": "address",
          "name": "_quoteTokenAddress",
          "type": "address"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "_quoteTokenAmount",
          "type": "uint256"
        },
        {
          "indexed": false,
          "internalType": "uint24",
          "name": "_fee",
          "type": "uint24"
        },
        {
          "indexed": false,
          "internalType": "uint160",
          "name": "_sqrtPriceX96",
          "type": "uint160"
        },
        {
          "indexed": false,
          "internalType": "int24",
          "name": "_tickLower",
          "type": "int24"
        },
        {
          "indexed": false,
          "internalType": "int24",
          "name": "_tickUpper",
          "type": "int24"
        },
        {
          "indexed": false,
          "internalType": "address",
          "name": "_lpPool",
          "type": "address"
        }
      ],
      "name": "CreateLPPoolOrLinkLPPool",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "address[]",
          "name": "_mintTokenAddressList",
          "type": "address[]"
        },
        {
          "indexed": false,
          "internalType": "uint24[]",
          "name": "_mintTokenAmountRatioList",
          "type": "uint24[]"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "_startTimestamp",
          "type": "uint256"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "_endTimestamp",
          "type": "uint256"
        },
        {
          "indexed": false,
          "internalType": "int24",
          "name": "_tickLower",
          "type": "int24"
        },
        {
          "indexed": false,
          "internalType": "int24",
          "name": "_tickUpper",
          "type": "int24"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "_mintValue",
          "type": "uint256"
        }
      ],
      "name": "Mint",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "address",
          "name": "_manager",
          "type": "address"
        }
      ],
      "name": "RemoveManager",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "from",
          "type": "address"
        },
        {
          "indexed": true,
          "internalType": "address",
          "name": "to",
          "type": "address"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "value",
          "type": "uint256"
        }
      ],
      "name": "Transfer",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "address",
          "name": "_newOwner",
          "type": "address"
        }
      ],
      "name": "TransferOwnership",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "_baseTokenAmount",
          "type": "uint256"
        }
      ],
      "name": "UpdateLPPool",
      "type": "event"
    },
    {
      "inputs": [],
      "name": "UNISWAP_V3_POSITIONS",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "WETH9",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "manager",
          "type": "address"
        }
      ],
      "name": "addManager",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "owner",
          "type": "address"
        },
        {
          "internalType": "address",
          "name": "spender",
          "type": "address"
        }
      ],
      "name": "allowance",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "spender",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "amount",
          "type": "uint256"
        }
      ],
      "name": "approve",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "account",
          "type": "address"
        }
      ],
      "name": "balanceOf",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "bonusWithdraw",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256[]",
          "name": "tokenIdList",
          "type": "uint256[]"
        }
      ],
      "name": "bonusWithdrawByTokenIdList",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "_baseTokenAmount",
          "type": "uint256"
        },
        {
          "internalType": "address",
          "name": "_quoteTokenAddress",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "_quoteTokenAmount",
          "type": "uint256"
        },
        {
          "internalType": "uint24",
          "name": "_fee",
          "type": "uint24"
        },
        {
          "internalType": "int24",
          "name": "_tickLower",
          "type": "int24"
        },
        {
          "internalType": "int24",
          "name": "_tickUpper",
          "type": "int24"
        },
        {
          "internalType": "uint160",
          "name": "_sqrtPriceX96",
          "type": "uint160"
        }
      ],
      "name": "createLPPoolOrLinkLPPool",
      "outputs": [],
      "stateMutability": "payable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "decimals",
      "outputs": [
        {
          "internalType": "uint8",
          "name": "",
          "type": "uint8"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "spender",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "subtractedValue",
          "type": "uint256"
        }
      ],
      "name": "decreaseAllowance",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "destruct",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "spender",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "addedValue",
          "type": "uint256"
        }
      ],
      "name": "increaseAllowance",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "_address",
          "type": "address"
        }
      ],
      "name": "isManager",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "lpPool",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "lpRatio",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "lpToken0",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "lpToken1",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "managers",
      "outputs": [
        {
          "internalType": "address[]",
          "name": "",
          "type": "address[]"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address[]",
          "name": "_mintTokenAddressList",
          "type": "address[]"
        },
        {
          "internalType": "uint24[]",
          "name": "_mintTokenAmountRatioList",
          "type": "uint24[]"
        },
        {
          "internalType": "uint256",
          "name": "_startTimestamp",
          "type": "uint256"
        },
        {
          "internalType": "uint256",
          "name": "_endTimestamp",
          "type": "uint256"
        },
        {
          "internalType": "int24",
          "name": "_tickLower",
          "type": "int24"
        },
        {
          "internalType": "int24",
          "name": "_tickUpper",
          "type": "int24"
        }
      ],
      "name": "mint",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "mintAnchor",
      "outputs": [
        {
          "internalType": "uint128",
          "name": "p",
          "type": "uint128"
        },
        {
          "internalType": "uint16",
          "name": "aNumerator",
          "type": "uint16"
        },
        {
          "internalType": "uint16",
          "name": "aDenominator",
          "type": "uint16"
        },
        {
          "internalType": "uint16",
          "name": "bNumerator",
          "type": "uint16"
        },
        {
          "internalType": "uint16",
          "name": "bDenominator",
          "type": "uint16"
        },
        {
          "internalType": "uint16",
          "name": "c",
          "type": "uint16"
        },
        {
          "internalType": "uint16",
          "name": "d",
          "type": "uint16"
        },
        {
          "internalType": "uint256",
          "name": "lastTimestamp",
          "type": "uint256"
        },
        {
          "internalType": "uint256",
          "name": "n",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "name",
      "outputs": [
        {
          "internalType": "string",
          "name": "",
          "type": "string"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "owner",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "manager",
          "type": "address"
        }
      ],
      "name": "removeManager",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "staking",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "symbol",
      "outputs": [
        {
          "internalType": "string",
          "name": "",
          "type": "string"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "temporaryAmount",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "totalSupply",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "recipient",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "amount",
          "type": "uint256"
        }
      ],
      "name": "transfer",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "sender",
          "type": "address"
        },
        {
          "internalType": "address",
          "name": "recipient",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "amount",
          "type": "uint256"
        }
      ],
      "name": "transferFrom",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address payable",
          "name": "_newOwner",
          "type": "address"
        }
      ],
      "name": "transferOwnership",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "_baseTokenAmount",
          "type": "uint256"
        },
        {
          "internalType": "int24",
          "name": "_tickLower",
          "type": "int24"
        },
        {
          "internalType": "int24",
          "name": "_tickUpper",
          "type": "int24"
        }
      ],
      "name": "updateLPPool",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "stateMutability": "payable",
      "type": "receive"
    }
  ]
"""


CHAIN_ID_INFO = {
    "1": "mainnet",
    "3": "ropsten",
    "4": "rinkeby",
    "42": "kovan",
}


def get_eth_node_url(chain_id):
    if chain_id not in list(CHAIN_ID_INFO.keys()):
        return None
    name = CHAIN_ID_INFO[chain_id]
    return "wss://{}.infura.io/ws/v3/99a79f80961b4db7aab7c9f54375eda7".format(name)


def run_sync_token_mint_record_event_task(token_mint_record_id):
    record = TokenMintRecord.objects(id=token_mint_record_id).first()
    if not record:
        return

    last_sync_event_at = record.last_sync_event_at if record.last_sync_event_at else 0
    if int(time.time()) - last_sync_event_at <= 5 * 60:
        return

    try:
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
    except Exception as ex:
        msg = traceback.format_exc()
        print('exception log_exception' + str(ex))
        print(msg)


def _sync_event(token_mint_record):
    mint_tx_hash = token_mint_record.mint_tx_hash
    chain_id = token_mint_record.chain_id
    token_contract_address = token_mint_record.token_contract_address

    web3 = Web3(Web3.WebsocketProvider(get_eth_node_url(chain_id)))
    token = web3.eth.contract(address=Web3.toChecksumAddress(token_contract_address), abi=TOKEN_ABI)
    try:
        tx_receipt = web3.eth.get_transaction_receipt(mint_tx_hash)
        block_number = tx_receipt["blockNumber"]
        status = tx_receipt["status"]
        token_mint_record.block_number = block_number
        if status == 0:
            # 交易失败
            token_mint_record.status = MintRecordStatusEnum.FAIL.value
            token_mint_record.save()
            return
        if status == 1:
            # 交易成功
            rich_logs = token.events.Mint().processReceipt(tx_receipt)
            log = rich_logs[0]
            _mintTokenAddressList = log["args"]["_mintTokenAddressList"]
            _mintTokenAmountRatioList = log["args"]["_mintTokenAmountRatioList"]
            _startTimestamp = log["args"]["_startTimestamp"]
            _endTimestamp = log["args"]["_endTimestamp"]
            _tickLower = log["args"]["_tickLower"]
            _tickUpper = log["args"]["_tickUpper"]

            eq1 = _mintTokenAddressList == token_mint_record.mint_token_address_list
            eq2 = _mintTokenAmountRatioList == token_mint_record.mint_token_amount_ratio_list
            eq3 = _startTimestamp == token_mint_record.start_timestamp
            eq4 = _endTimestamp == token_mint_record.end_timestamp
            eq5 = _tickLower == token_mint_record.tick_lower
            eq6 = _tickUpper == token_mint_record.tick_upper

            token_mint_record.mint_params_has_diff = not (eq1 and eq2 and eq3 and eq4 and eq5 and eq6)

            token_mint_record.mint_value = Web3.fromWei(log["args"]["_mintValue"], "ether")
            token_mint_record.unit_real_size_value = token_mint_record.mint_value / token_mint_record.total_real_size

            token_transfer_event_log_list = []
            rich_logs = token.events.Transfer().processReceipt(tx_receipt)
            for log in rich_logs:
                token_transfer_event_log_list.append(TokenTransferEventLog(
                    to_address=log["args"]["to"],
                    value=log["args"]["value"]
                ))
            token_mint_record.token_transfer_event_logs = token_transfer_event_log_list
            token_mint_record.status = MintRecordStatusEnum.SUCCESS.value
            token_mint_record.save()
    except TransactionNotFound:
        # 没有找到交易结果
        pass


def _stat(token_mint_record):
    _update_income(token_mint_record)
    _update_mentor_income(token_mint_record)
    token_mint_record.stated = True
    token_mint_record.save()


def _update_mentor_income(token_mint_record):
    dao_id = token_mint_record.dao_id
    chain_id = token_mint_record.chain_id
    token_contract_address = token_mint_record.token_contract_address

    web3 = Web3(Web3.WebsocketProvider(get_eth_node_url(chain_id)))
    token = web3.eth.contract(address=Web3.toChecksumAddress(token_contract_address), abi=TOKEN_ABI)
    token_symbol = token.functions.symbol().call()
    token_name = token.functions.name().call()

    all_ratio = 0
    for ratio in token_mint_record.mint_token_amount_ratio_list:
        all_ratio += ratio
    unit_ratio_token_decimal = token_mint_record.mint_value / decimal.Decimal(str(all_ratio))
    for record in token_mint_record.mint_icpper_records:
        job_user_id = record.user_id
        for index, memtor_record in enumerate(record.mentor_list):
            mentor_id = memtor_record.mentor_id
            icpper_id = job_user_id if index == 0 else record.mentor_list[index-1]
            token_count = unit_ratio_token_decimal * decimal.Decimal(str(memtor_record.mentor_radio))
            MentorTokenIncomeStat.objects(
                mentor_id=mentor_id,
                icpper_id=icpper_id,
                dao_id=dao_id,
                token_contract_address=token_contract_address,
                token_name=token_name,
                token_symbol=token_symbol
            ).update_one(
                upsert=True,
                inc__total_value=token_count
            )


def _update_income(token_mint_record):
    decimal_unit = token_mint_record.unit_real_size_value
    dao_id = token_mint_record.dao_id
    cycle_ids = token_mint_record.cycle_ids

    stats = CycleIcpperStat.objects(cycle_id__in=cycle_ids, dao_id=dao_id).all()
    jobs = Job.objects(dao_id=dao_id, cycle_id__in=cycle_ids).all()
    jobs_dict = defaultdict(lambda: defaultdict(list))

    for job in jobs:
        jobs_dict[job.cycle_id][job.user_id].append(job)

    for ss in stats:
        ss.income = decimal_unit * ss.size
        uint_size = decimal.Decimal(0)
        if ss.job_size > 0:
            uint_size = ss.size / ss.job_size

        for job in jobs_dict[ss.cycle_id][ss.user_id]:
            job.income = job.size * uint_size * decimal_unit
            job.status = JobStatusEnum.TOKEN_RELEASED.value
            job.save()

        ss.save()

    Cycle.objects(id__in=cycle_ids).update(token_released_at=int(time.time()))


def test_run():
    pass
    # token_contract_address = "0x3164d487640e0f208D5Fd2Db3E0eb8E371442143"
    # from_black_number = 10994132
    # web3 = Web3(Web3.WebsocketProvider(get_eth_node_url("3")))
    # token = web3.eth.contract(address=Web3.toChecksumAddress(token_contract_address), abi=TOKEN_ABI)
    # tef = token.events["Mint"].createFilter(fromBlock=from_black_number, toBlock="latest")
    #
    # for log in tef.get_all_entries():
    #     print("11111111111111111")
    #     print(log)
    #     print(Web3.toHex(log["transactionHash"]))
    #     print("222222222222222222")
    #     print(log["blockNumber"])
    #     print(log["args"])
    #     print(log["args"]["_mintTokenAddressList"])
    #     print(log["args"]["_mintTokenAmountRatioList"])
    #     print(log["args"]["_startTimestamp"])
    #     print(log["args"]["_endTimestamp"])
    #     print(log["args"]["_tickLower"])
    #     print(log["args"]["_tickUpper"])
    #     print(log["args"]["_mintValue"])
    #     print("3333333333333333333")
    # print(2)
    # last_success_record = TokenMintRecord.objects(
    #     dao_id=token_mint_record.dao_id,
    #     token_contract_address=token_mint_record.token_contract_address,
    #     chain_id=token_mint_record.chain_id,
    #     status=MintRecordStatusEnum.SUCCESS.value
    # ).order_by("-end_timestamp").first()


    # token_contract_address = "0x3164d487640e0f208D5Fd2Db3E0eb8E371442143"
    # from_black_number = 10994132
    # tx_hash = "0x869335a92a088ae8935f040660528ad8b92b6779da2835fd8a6051323629f1d9"
    # web3 = Web3(Web3.WebsocketProvider(get_eth_node_url("3")))
    # token = web3.eth.contract(address=Web3.toChecksumAddress(token_contract_address), abi=TOKEN_ABI)
    # token_symbol = token.functions.symbol().call()
    # token_name = token.functions.name().call()
    # print(token_symbol)
    # print(token_name)
    # try:
    #     tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
    #     block_number = tx_receipt["blockNumber"]
    #     status = tx_receipt["status"]
    #     if status == 0:
    #         print("交易失败")
    #     if status == 1:
    #         print("交易成功")
    #         rich_logs = token.events.Mint().processReceipt(tx_receipt)
    #         log = rich_logs[0]
    #         print(log["args"]["_startTimestamp"])
    #         print(log["args"]["_endTimestamp"])
    #         print(log["args"])
    #         rich_logs = token.events.Transfer().processReceipt(tx_receipt)
    #         for log in rich_logs:
    #             print(log["args"]["to"])
    #             print(log["args"]["value"])
    # except TransactionNotFound:
    #     print("没有找到交易结果")
