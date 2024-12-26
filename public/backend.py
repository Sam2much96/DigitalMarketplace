from flask import Flask, jsonify, request
from algokit_utils import get_localnet_default_account, TransactionParameters
from algokit_utils.beta.algorand_client import AlgorandClient, PayParams, AssetTransferParams
from algokit_utils.beta.account_manager import AddressAndSigner
from smart_contracts.artifacts.marketplace.marketplace_client import MarketplaceClient
from algosdk.atomic_transaction_composer import TransactionWithSigner
import algosdk

app = Flask(__name__)

# Initialize Algorand client
algorand = AlgorandClient.default_local_net()

# Wallet and marketplace variables
creator = None
marketplace_client = None
test_asset_id = None

# Helper function to fund account
def fund_account(account):
    dispenser = algorand.account.dispenser()
    algorand.send.payment(PayParams(
        sender=dispenser.address,
        receiver=account.address,
        amount=10_000_000
    ))
    return account

@app.route('/connect-wallet', methods=['POST'])
def connect_wallet():
    global creator
    if not creator:
        creator = fund_account(algorand.account.random())
    return jsonify({"message": "Wallet connected.", "address": creator.address})

@app.route('/update-listing', methods=['POST'])
def update_listing():
    global marketplace_client, test_asset_id

    if not creator:
        return jsonify({"error": "Wallet not connected."}), 400

    if not marketplace_client:
        # Initialize the marketplace client
        marketplace_client = MarketplaceClient(
            algod_client=algorand.client.algod,
            sender=creator.address,
            signer=creator.signer
        )
        test_asset_id = algorand.send.asset_create(
            sender=creator.address,
            total=10
        )["confirmation"]["asset-index"]

        marketplace_client.create_create_application(
            listingPrice=0, assetId=test_asset_id
        )
        return jsonify({"message": "Marketplace listing updated."})
    else:
        return jsonify({"message": "Marketplace already initialized."})

@app.route('/price', methods=['GET'])
def get_price():
    if not marketplace_client:
        return jsonify({"error": "Marketplace not initialized."}), 400
    return jsonify({"price": 3_300_000})

@app.route('/buy', methods=['POST'])
def buy_asset():
    global marketplace_client, test_asset_id

    data = request.json
    quantity = data.get("quantity", 1)

    if not marketplace_client:
        return jsonify({"error": "Marketplace not initialized."}), 400

    buyer = fund_account(algorand.account.random())
    algorand.send.asset_opt_in(AssetTransferParams(sender=buyer.address, asset_id=test_asset_id))

    buyer_payment_txn = algorand.transactions.payment(
        PayParams(
            sender=buyer.address,
            receiver=marketplace_client.app_address,
            amount=quantity * 3_300_000,
            extra_fee=1_000
        )
    )

    result = marketplace_client.buy(
        buyerTxn=TransactionWithSigner(txn=buyer_payment_txn, signer=buyer.signer),
        quantity=quantity,
        transaction_parameters=TransactionParameters(sender=buyer.address, signer=buyer.signer, foreign_assets=[test_asset_id])
    )
    return jsonify({"message": "Purchase successful.", "round": result.confirmed_round})

@app.route('/hello', methods=['GET'])
def hello():
    if not marketplace_client:
        return jsonify({"error": "Marketplace not initialized."}), 400
    name = request.args.get('name', 'World')
    result = marketplace_client.hello(name=name)
    return jsonify({"message": result.return_value})

if __name__ == '__main__':
    app.run(debug=True)
