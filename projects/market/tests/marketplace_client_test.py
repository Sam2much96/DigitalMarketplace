import algokit_utils
import os
import pytest
from algokit_utils import get_localnet_default_account, TransactionParameters
from algokit_utils.config import config
#from algosdk.v2client.algod import AlgodClient
#from algosdk.v2client.indexer import IndexerClient

from smart_contracts.artifacts.marketplace.marketplace_client import MarketplaceClient

from algokit_utils.beta.algorand_client import AlgorandClient,  PayParams, AssetCreateParams,AssetTransferParams, AssetOptInParams, SuggestedParams
from algokit_utils.beta.account_manager import AddressAndSigner

import algosdk
from algosdk.atomic_transaction_composer import TransactionWithSigner, TransactionSigner,AccountTransactionSigner

from algosdk.mnemonic import to_private_key
from algosdk.account import address_from_private_key
#from algokit_utils.beta.account_manager import TransactionSignerAccount


class AlgorandAccount:
    def __init__(self, mnemonic: str):
        self._private_key = to_private_key(mnemonic)
        self.address = address_from_private_key(self._private_key)
        self.signer = AccountTransactionSigner(self._private_key)
    #def get_signer(self):
    #    return AccountTransactionSigner(self._private_key)


@pytest.fixture(scope="session")
def algorand() -> AlgorandClient:
    """
    Get An Algorand Client to use throughout the test
    """
    # AlgorandClient.default_localnet()
    return AlgorandClient.test_net()


@pytest.fixture(scope="session")
def dispenser(algorand : AlgorandClient) -> AddressAndSigner:
    """
    Get A Dispenser to fund the test address
    """
    # uses environment dispenser mnemonic to fund the account for testnet
    return algorand.account.dispenser()


@pytest.fixture(scope="session")
def creator(algorand: AlgorandClient, dispenser: AddressAndSigner) -> AddressAndSigner:
    #"""Create New Random Algorand Account for testing"""
    # use my algorand test accout fpr testing


    acct =  AlgorandAccount(os.environ["ACCOUNT_MNEMONIC"]) #algorand.account.random()
    #signer = acct.get_signer()

    algorand.set_default_signer( acct.signer)  # Register the creator's signer as default signer for all test txns.

    algorand.send.payment(PayParams(
        sender=dispenser.address,
        receiver=acct.address,
        amount= 100_000
    ))
    creator = AddressAndSigner(address=acct.address, signer=acct.signer)
    return creator
    #return acct


@pytest.fixture(scope="session")
def marketplace_client(
    algorand : AlgorandClient, creator : AddressAndSigner, test_asset_id : int
) -> MarketplaceClient:
    #Instantiate an application client we can use for our test
    
    config.configure(
        debug=True,
        # trace_all=True,
    )

    client = MarketplaceClient(
        algod_client= algorand.client.algod,
        sender = creator.address,
        signer = creator.signer
    )

    # compile smart contractwith asset id
    client.create_create_application(listingPrice=0,assetId=test_asset_id)

    return client



@pytest.fixture(scope="session")
def test_asset_id(creator : AddressAndSigner, algorand: AlgorandClient) -> int:
    params = algorand.get_suggested_params()#SuggestedParams
    sent_txn = algorand.send.asset_create(AssetCreateParams(sender = creator.address, total=10, first_valid_round=params.first, last_valid_round=params.last)) # account for network delays
    return sent_txn["confirmation"]["asset-index"]

# Pytests start from here
def test_opt_in_to_asset(marketplace_client : MarketplaceClient, creator : AddressAndSigner, test_asset_id : int, algorand : AlgorandClient):
    # throws error if app not yet oped int 
    pytest.raises(algosdk.error.AlgodHTTPError, 
                  lambda: algorand.account.get_asset_information(marketplace_client.app_address, test_asset_id)
                  )
    params = algorand.get_suggested_params()#SuggestedParams

    # Web need to send 100_000 for account mbr and 100_000 for asa mbr, to fund the Dapp Address
    # create an opt in transaction for the test asset
    mbr_pay_txn =  algorand.transactions.payment(PayParams(
        sender = creator.address,
        receiver = marketplace_client.app_address,
        amount = 200_000,
        first_valid_round=params.first,
        last_valid_round=params.last,
        extra_fee = 1_000,

    ))

    # opt app into asset
    result = marketplace_client.opt_in_to_asset(
        mbrPay = TransactionWithSigner(txn = mbr_pay_txn, signer=creator.signer),
        transaction_parameters= algokit_utils.TransactionParameters(
            # we are using this asset in the contract so we need to tell the avm it's asset id
            # in future updates to algokit, this would be done automatically
            foreign_assets=[test_asset_id]
        )        
        )
    
    #check that the trasaction was successfull
    assert result.confirmed_round
    assert (algorand.account.get_asset_information(marketplace_client.app_address, test_asset_id)["asset-holding"]["amount"] == 0)


def test_deposit(marketplace_client : MarketplaceClient, creator : AddressAndSigner, test_asset_id : int, algorand : AlgorandClient):
    params = algorand.get_suggested_params()#SuggestedParams
    
    result = algorand.send.asset_transfer(AssetTransferParams(
        sender=creator.address,
        asset_id=test_asset_id,
        receiver=marketplace_client.app_address,
        amount = 3,
        first_valid_round=params.first,
        last_valid_round=params.last
        ))
    
    assert result["confirmation"]
    assert (algorand.account.get_asset_information(marketplace_client.app_address, test_asset_id)["asset-holding"]["amount"] == 3)



def test_set_price(marketplace_client : MarketplaceClient):
    result = marketplace_client.set_price(listingPrice=300_000) # set price to 3  algos

    assert result.confirmed_round



def test_buy(marketplace_client : MarketplaceClient, creator : AddressAndSigner, test_asset_id : int, algorand : AlgorandClient, dispenser : AddressAndSigner):
    params = algorand.get_suggested_params()#SuggestedParams
    # create new account to be the buyer
    buyer = algorand.account.random()

    # use dispenser to fund buyer for buy transaction
    algorand.send.payment(PayParams(sender= dispenser.address, receiver= buyer.address, amount = 603_000, first_valid_round=params.first, last_valid_round=params.last ))

    # opt buyer into the asset
    algorand.send.asset_opt_in(AssetOptInParams( sender= buyer.address, asset_id=test_asset_id, first_valid_round=params.first, last_valid_round=params.last))

    assert  (algorand.get_account_balance(buyer.address) >= 600_000) # make sure buyer has enough algos to cover this

    # form a transaciton to buy 2 assets from the buyer address
    buyer_payment_txn = algorand.transactions.payment(
        PayParams(
            sender = buyer.address,
            receiver= marketplace_client.app_address,
            amount= 2 * 300_000,
            extra_fee= 1_000, # double extra fee for every inner transaction in the smart contract
            first_valid_round=params.first, 
            last_valid_round=params.last
        )
    )

    result = marketplace_client.buy(
        buyerTxn= TransactionWithSigner(txn=buyer_payment_txn, signer=buyer.signer),
        quantity = 2,
        transaction_parameters = TransactionParameters(sender=buyer.address, signer=buyer.signer,foreign_assets=[test_asset_id])
    )

    assert result.confirmed_round
    assert (algorand.account.get_asset_information(buyer.address, test_asset_id)["asset-holding"]["amount"] == 2)


def test_say_hello(marketplace_client: MarketplaceClient) -> None:
    result = marketplace_client.hello(name="World")

    assert result.return_value == "Hello,World"


"""
def test_simulate_says_hello_with_correct_budget_consumed(
    marketplace_client: MarketplaceClient, algod_client: AlgorandClient,
) -> None:
    result = (
        marketplace_client.compose().hello(name="World").hello(name="Jane").simulate()
    )

    assert result.abi_results[0].return_value == "Hello,World"
    assert result.abi_results[1].return_value == "Hello,Jane"
    assert result.simulate_response["txn-groups"][0]["app-budget-consumed"] < 100


"""
@pytest.fixture(scope="session")
def test_delete_application(marketplace_client : MarketplaceClient, creator : AddressAndSigner, test_asset_id : int, algorand : AlgorandClient, dispenser : AddressAndSigner):
    # would fail if dApp does not have 1000 micro algos to cover the inner transaction fees via overspend logical error
    before_call_amount = algorand.account.get_information(creator.address)["amount"]

    result = marketplace_client.delete_delete_application(
        transaction_parameters=TransactionParameters(sender=creator.address, signer=creator.signer,foreign_assets=[test_asset_id]),
 
    )

    assert result.confirmed_round

    after_call_amount = algorand.account.get_information(creator.address)["amount"]
    assert after_call_amount - before_call_amount == (2 * 3_300_000) + 200_000 - 3000 # 
    assert(algorand.account.get_asset_information(creator.address, test_asset_id)["asset-holding"]["amount"] == 8)
