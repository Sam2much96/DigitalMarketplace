import algokit_utils
import pytest
from algokit_utils import get_localnet_default_account, TransactionParameters
from algokit_utils.config import config
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from smart_contracts.artifacts.marketplace.marketplace_client import MarketplaceClient

from algokit_utils.beta.algorand_client import AlgorandClient,  PayParams, AssetCreateParams,AssetTransferParams, AssetOptInParams
from algokit_utils.beta.account_manager import AddressAndSigner

import algosdk
from algosdk.atomic_transaction_composer import TransactionWithSigner

@pytest.fixture(scope="session")
def algorand() -> AlgorandClient:
    """
    Get An Algorand Client to use throughout the test
    """
    return AlgorandClient.default_local_net()


@pytest.fixture(scope="session")
def dispenser(algorand : AlgorandClient) -> AddressAndSigner:
    """
    Get A Dispenser to fund the test address
    """

    return algorand.account.dispenser()


@pytest.fixture(scope="session")
def creator(algorand: AlgorandClient, dispenser: AddressAndSigner) -> AddressAndSigner:
    """Create New Random Algorand Account for testing"""
    acct = algorand.account.random()
    algorand.send.payment(PayParams(
        sender=dispenser.address,
        receiver=acct.address,
        amount= 10_000_000
    ))

    return acct

@pytest.fixture(scope="session")
def test_asset_id(creator : AddressAndSigner, algorand: AlgorandClient) -> int:
    sent_txn = algorand.send.asset_create(AssetCreateParams(sender = creator.address, total=10))
    return sent_txn["confirmation"]["asset-index"]


@pytest.fixture(scope="session")
def marketplace_client(
    algorand : AlgorandClient, creator : AddressAndSigner, test_asset_id : int
) -> MarketplaceClient:
    """Instantiate an application client we can use for our test"""
    
    config.configure(
        debug=True,
        # trace_all=True,
    )

    client = MarketplaceClient(
        algod_client= algorand.client.algod,
        sender = creator.address,
        signer = creator.signer
    )

    # compile smart contract
    client.create_create_application(listingPrice=0,assetId=test_asset_id)

    return client


def test_opt_in_to_asset(marketplace_client : MarketplaceClient, creator : AddressAndSigner, test_asset_id : int, algorand : AlgorandClient):
    # throws error if app not yet oped int 
    pytest.raises(algosdk.error.AlgodHTTPError, 
                  lambda: algorand.account.get_asset_information(marketplace_client.app_address, test_asset_id)
                  )
   
    # Web need to send 100_000 for account mbr and 100_000 for asa mbr
    # create an opt in transaction for the test asset
    mbr_pay_txn =  algorand.transactions.payment(PayParams(
        sender = creator.address,
        receiver = marketplace_client.app_address,
        amount = 200_000,
        extra_fee = 1_000

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
    result = algorand.send.asset_transfer(AssetTransferParams(
        sender=creator.address,
        asset_id=test_asset_id,
        receiver=marketplace_client.app_address,
        amount = 3
        ))
    
    assert result["confirmation"]
    assert (algorand.account.get_asset_information(marketplace_client.app_address, test_asset_id)["asset-holding"]["amount"] == 3)


def test_set_price(marketplace_client : MarketplaceClient):
    result = marketplace_client.set_price(listingPrice=3_300_000)

    assert result.confirmed_round



def test_buy(marketplace_client : MarketplaceClient, creator : AddressAndSigner, test_asset_id : int, algorand : AlgorandClient, dispenser : AddressAndSigner):
    
    # create new account to be the buyer
    buyer = algorand.account.random()

    # use dispenser to fund buyer
    algorand.send.payment(PayParams(sender= dispenser.address, receiver= buyer.address, amount = 10_000_000 ))

    # opt buyer into the asset
    algorand.send.asset_opt_in(AssetOptInParams( sender= buyer.address, asset_id=test_asset_id))

    # form a transaciton to buy 2 assets
    buyer_payment_txn = algorand.transactions.payment(
        PayParams(
            sender = buyer.address,
            receiver= marketplace_client.app_address,
            amount= 2 * 3_300_000,
            extra_fee= 1_000 # double extra fee for every inner transaction in the smart contract
        )
    )

    result = marketplace_client.buy(
        buyerTxn= TransactionWithSigner(txn=buyer_payment_txn, signer=buyer.signer),
        quantity = 2,
        transaction_parameters = TransactionParameters(sender=buyer.address, signer=buyer.signer,foreign_assets=[test_asset_id])
    )

    assert result.confirmed_round
    assert (algorand.account.get_asset_information(buyer.address, test_asset_id)["asset-holding"]["amount"] == 2)



def test_says_hello(marketplace_client: MarketplaceClient) -> None:
    result = marketplace_client.hello(name="World")

    assert result.return_value == "Hello,World"

def test_simulate_says_hello_with_correct_budget_consumed(
    marketplace_client: MarketplaceClient, algod_client: AlgodClient
) -> None:
    result = (
        marketplace_client.compose().hello(name="World").hello(name="Jane").simulate()
    )

    assert result.abi_results[0].return_value == "Hello,World"
    assert result.abi_results[1].return_value == "Hello,Jane"
    assert result.simulate_response["txn-groups"][0]["app-budget-consumed"] < 100



def test_delete_application(marketplace_client : MarketplaceClient, creator : AddressAndSigner, test_asset_id : int, algorand : AlgorandClient, dispenser : AddressAndSigner):
    before_call_amount = algorand.account.get_information(creator.address)["amount"]

    result = marketplace_client.delete_delete_application(
        transaction_parameters=TransactionParameters(sender=creator.address, signer=creator.signer,foreign_assets=[test_asset_id]),
 
    )

    assert result.confirmed_round

    after_call_amount = algorand.account.get_information(creator.address)["amount"]
    assert after_call_amount - before_call_amount == (2 * 3_300_000) + 200_000 - 3000 # 
    assert(algorand.account.get_asset_information(creator.address, test_asset_id)["asset-holding"]["amount"] == 8)

