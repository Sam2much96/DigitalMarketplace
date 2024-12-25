import * as algokit from "@algorandfoundation/algokit-utils"

import { MarketplaceClient } from "./contracts/Marketplace"


// framework agnostic wrapper

export function create(algorand: algokit.AlgorandClient, dmClient: MarketplaceClient, assetBeingSold: bigint, listingPrice: bigint) {
    //return an async function
    return async () => { await dmClient }

} // deploy app function