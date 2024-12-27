import { AlgorandClient, Config, microAlgos } from '@algorandfoundation/algokit-utils'

import { MarketplaceClient, MarketplaceFactory, MarketplaceParamsFactory } from "./contracts/Marketplace.ts"


// To DO : 
// (1) Create algorand client function


// framework agnostic wrapper
// creates the digital marketplace dApp
export function create(
    //algorand: AlgorandClient,
    //dmClient: MarketplaceParamsFactory,
    assetBeingSold: bigint,
    listingPrice: bigint,
    quantity: bigint,
    sender: string,
    setAppId: (id: number) => void,
) {

    //function returns an async function
    return async () => {
        console.log("Creating Asa");
        // turn on debug
        Config.configure({ debug: true });

        const algorand = AlgorandClient.testNet(); // Algonode free tier
        //const algorand = AlgorandClient.fromEnvironment();
        //const deployer = algorand.account.fromEnvironment("DEPLOYER", (1).algo());

        // fund creator address
        console.log("Is Testnet: ", algorand.client.isTestNet());
        console.log("Is Localnet: ", algorand.client.isLocalNet());

        let assetId = assetBeingSold;

        if (assetId === BigInt(0)) {
            // create an asset if asset id is 0

            console.log("Creating Asa");
            const assetCreate = await algorand.send.assetCreate({ sender, total: quantity });
            assetId = BigInt(assetCreate.confirmation.assetIndex!);
            console.log("Asset id created:", assetId);
        }

        // create the typed app factory
        const factory = algorand.client.getTypedAppFactory(MarketplaceFactory, { defaultSender: sender })



        const params = await MarketplaceParamsFactory.create.createApplication({ args: [assetId, listingPrice] });

        const { appClient } = await factory.deploy(params);

        console.log(" App ID: ", appClient.appId);

        // make an abi call to the client
        const response = await appClient.params.hello({ args: { name: "world" } });

        console.log("App Client Debug: ", response);


        // create an app call from the client to create a application
        //const createResult = await dmClient.appClient.create.createApplication({ assetId, listingPrice });
        //const createResult = await MarketplaceParamsFactory.create.createApplication({ args: [assetId, listingPrice] });
        // const {createResult } = await MarketplaceFactory.se  

        //console.log("Debug 1: ", createResult);

        //console.log("Debug 1: ", createResult.appId);


        //const mbrTxn = await algorand.createTransaction.payment({ sender, receiver: createResult.appAddress, amount: algokit.algos(0.1 + 0.1), extraFee: algokit.algos(0.0001) });  //mbr + asset fee + inner transaction fee

        //await MarketplaceClient.appClient.optInToAsset({ mbrTxn });

        //await dmClient.createTransaction.optInToAsset(mbrTxn);

        //await algorand.send.assetTransfer({ sender, assetId, receiver: createResult.appAddress, amount: quantity });

        // update the frontend ui
        //setAppId(Number(createResult.appId));
    }

}

export function buy(
    algorand: AlgorandClient,
    dmClient: MarketplaceClient,
    sender: string,
    appAddress: string,
    quantity: bigint,
    listingPrice: bigint,
    setUnitsLeft: (units: bigint) => void
) {
    return async () => {

        // construct the buy transation
        const buyerTxn = await algorand.createTransaction.payment({ sender, receiver: appAddress, amount: microAlgos(quantity * listingPrice) });

        console.log("Debug 2: ", buyerTxn);
        //await dmClient.appClient.buy(buyerTxn, quantity);

        //get the dApp global state
        //const state = await dmClient.appClient.getGlobalState();
        //const info = await algorand.account.getAssetInformation(appAddress, state.assetId!.asBigInt());


        //update the frontend ui
        //setUnitsLeft(info.balance);
    }
}

export function deleteApp(
    algorand: AlgorandClient,
    dmClient: MarketplaceClient,
    setAppId: (id: number) => void,
) {
    return async () => {

        //await dmClient.appClient.delete.deleteApplication({});
        setAppId(0);
    }
}