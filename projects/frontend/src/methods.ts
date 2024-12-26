import * as algokit from "@algorandfoundation/algokit-utils"

import { MarketplaceClient, MarketplaceParamsFactory } from "./contracts/Marketplace"


// framework agnostic wrapper

export function create(algorand: algokit.AlgorandClient,
    dmClient: MarketplaceClient,
    assetBeingSold: bigint,
    listingPrice: bigint,
    quantity: bigint,
    sender: string) {

    //return an async function
    return async () => {
        let assetId = assetBeingSold;

        if (assetId === 0n) {
            const assetCreate = await algorand.send.assetCreate({ sender, total: quantity });
            assetId = BigInt(assetCreate.confirmation.assetIndex!)
        }

        const params = (MarketplaceParamsFactory.create.createApplication({ args: [assetId, listingPrice] }));
        const createResult = await dmClient.appClient.createTransaction.call(params);

        console.log("Debug 1: ", createResult);
        let appId = "";

        const mbrTxn = await algorand.createTransaction.payment({ sender, receiver: appId, amount: algokit.algos(0.1 + 0.1), extraFee: algokit.algos(0.0001) });  //createResult.appAddress

        console.log("Debug 2: ", mbrTxn);
        //await dmClient.createTransaction.optInToAsset({ mbrTxn });

    }

} // deploy app function