from algopy import Asset, UInt64, Global, Txn, UInt64,gtxn,itxn
from algopy.arc4 import abimethod, ARC4Contract, String


# Digital Market Place Template

class Marketplace(ARC4Contract):
    
    # GLobal State Variables
    assetId : UInt64
    listingPrice: UInt64

    # create the app
    @abimethod(allow_actions=["NoOp"], create="require")
    def createApplication(self, assetId: Asset, listingPrice: UInt64) -> None:

        self.assetId =assetId.id
        self.lsitingPrice = listingPrice
    
    # update the price listing
    @abimethod
    def setPrice(self, listingPrice : UInt64) -> None:
        assert Txn.sender == Global.creator_address # This set price function can only be classed by the creator address
        self.listingPrice = listingPrice


    #opt in to the asset to be sold
    @abimethod
    def optInToAsset(self, mbrPay: gtxn.PaymentTransaction) -> None:
        assert Txn.sender == Global.creator_address # Transation must be from creator address
        assert not Global.current_application_address.is_opted_in(Asset(self.assetId)) # make sure the dapp is not currently opted into this asset
        assert mbrPay.receiver == Global.current_application_address # assert that the reciever of the asset is this smart contract
        assert mbrPay.amount == Global.min_balance + Global.asset_opt_in_min_balance# assert that the transaction has enough algos to cover the transaction of opt in these assets


        itxn.AssetTransfer(
            xfer_asset=self.assetId,
            asset_receiver = Global.current_application_address,
            asset_amount = 0,
        ).submit()


    # buy the asset
    @abimethod
    def buy(self, buyerTxn : gtxn.PaymentTransaction , quantity: UInt64) -> None:
        assert self.listingPrice != UInt64(0) # make sure the asset quantity isn't zero
        assert Txn.sender == buyerTxn.sender # assert that the account that called the buy method is also the one that sent the payment transaction
        assert buyerTxn.receiver == Global.current_application_address #assert that the transaction receiver is the smart contract address
        assert buyerTxn.amount == self.listingPrice * quantity # THe Transaction ammount should be equal to the asset price times the quantity to be bought

        # Inner Transaction To Transfer the asset to the Buyer
        itxn.AssetTransfer(
            xfer_asset = self.assetId,
            asset_receiver = buyerTxn.sender,
            asset_amount = quantity,
        ).submit()

    # delete the application
    @abimethod(allow_actions=["DeleteApplication"])
    def deleteApplication(self) -> None:
        assert Txn.sender == Global.creator_address

        # withdraw all assets
        itxn.AssetTransfer(
            xfer_asset = self.assetId,
            asset_receiver = Global.creator_address,
            asset_amount = 0,
            asset_close_to= Global.creator_address,
            fee=1000,
        ).submit()

        # Withdraw all funds
        itxn.Payment(
            receiver = Global.creator_address,
            amount = 0,
            close_remainder_to = Global.creator_address,
            fee=1000,
        ).submit()

    # test integration
    @abimethod
    def hello(self, name :String) -> String:
        return "Hello," + name