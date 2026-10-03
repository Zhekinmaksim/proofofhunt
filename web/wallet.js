async function verifyWalletIdentity(provider, rpc, { account, chainId, endpoint, params }) {
  const accounts = await provider.request({ method: "eth_accounts" });
  if (accounts[0]?.toLowerCase() !== account.toLowerCase()) throw Error("Wallet account changed. Connect again.");
  if (Number(BigInt(await provider.request({ method: "eth_chainId" }))) !== chainId) throw Error(`Select chain ${chainId} with RPC ${endpoint} in your wallet.`);
  const request = { method: "gen_call", params };
  const [a, b] = await Promise.all([provider.request(request), rpc.request(request)]);
  if (JSON.stringify(a) !== JSON.stringify(b)) throw Error(`Wallet RPC does not match this race. Set its RPC URL to ${endpoint}.`);
}
function singleSendProvider(provider, beforeSend = () => {
}) {
  let sent = false;
  return { request: async (request) => {
    if (request.method === "eth_sendTransaction") {
      if (sent) throw Error("Automatic write retry blocked. Check transaction history.");
      sent = true;
      await beforeSend();
    }
    return provider.request(request);
  } };
}
export {
  singleSendProvider,
  verifyWalletIdentity
};
