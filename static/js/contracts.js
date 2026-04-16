// AgentHire — on-chain config. All contracts live on Avalanche Fuji testnet.
// Addresses from: https://github.com/nichar3232/ai-agent-marketplace/blob/main/deployments.json

window.AGENTHIRE_CHAIN = {
  chainId: 43113,
  chainIdHex: '0xa869',
  name: 'Avalanche Fuji',
  rpcUrl: 'https://api.avax-test.network/ext/C/rpc',
  explorer: 'https://testnet.snowtrace.io',
  nativeCurrency: { name: 'AVAX', symbol: 'AVAX', decimals: 18 },
};

window.AGENTHIRE_ADDRESSES = {
  MockUSDC:           '0x9C49D730Dfb82B7663aBE6069B5bFe867fa34c9f',
  AgentRegistry:      '0x6B71b84Fa3C313ccC43D63A400Ab47e6A0d4BCbB',
  ReputationContract: '0x40ef89Ce1E248Df00AF6Dc37f96BBf92A9Bf603A',
  StakingSlashing:    '0xfc942b4d1Eb363F25886b3F5935394BD4932B896',
  EscrowPayment:      '0xD19990C7CB8C386fa865135Ce9706A5A37A3f2f2',
  AuctionMarket:      '0xa7AEEca5a76bd5Cd38B15dfcC2c288d3645E53E3',
};

// Minimal ABIs — only what the UI actually calls. Full ABIs are in the backend repo.
window.AGENTHIRE_ABIS = {
  MockUSDC: [
    'function balanceOf(address) view returns (uint256)',
    'function approve(address,uint256) returns (bool)',
    'function mint(address,uint256)',
    'function transferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce,uint8 v,bytes32 r,bytes32 s)',
    'function DOMAIN_SEPARATOR() view returns (bytes32)',
  ],
  AgentRegistry: [
    'function nextAgentId() view returns (uint256)',
    'function getAgent(uint256) view returns (tuple(uint256 agentId,address wallet,string name,string endpointURL,uint256 registeredAt,bool active,bool banned))',
    'function getListing(uint256) view returns (tuple(uint256 minPricePerToken,uint256 maxTokensPerSession,bool acceptingWork,uint256 nonce))',
    'function getAgentByWallet(address) view returns (uint256,tuple(uint256 agentId,address wallet,string name,string endpointURL,uint256 registeredAt,bool active,bool banned))',
    'function registerAgent(address,string,string) returns (uint256)',
  ],
  ReputationContract: [
    'function getCreditProfile(uint256) view returns (uint256 score,uint8 tier,uint256 tasksCompleted,uint256 incidentCount,uint64 lastDecayTs,uint256 projectedScore)',
    'function getCategoryTier(uint256,uint256) view returns (uint8)',
  ],
  StakingSlashing: [
    'function getStake(uint256) view returns (uint256,uint256,bool)',
    'function stake(uint256,uint256)',
    'function requestUnstake(uint256,uint256)',
    'function completeUnstake(uint256,address)',
    'function getUnstakeRequest(uint256) view returns (uint256 amount,uint256 availableAt)',
  ],
  EscrowPayment: [
    'function depositFunds(uint256 agentId,uint256 depositAmount,uint256 tokenBudget,uint256 categoryId,uint64 expiresAt) returns (uint256)',
    'function getSession(uint256) view returns (tuple(uint256 agentId,address user,uint256 totalDeposit,uint256 tokenBudget,uint256 pricePerToken,uint256 categoryId,uint64 expiresAt,bool settled,bool cancelled))',
    'function cancelSession(uint256)',
    'function nextSessionId() view returns (uint256)',
  ],
  AuctionMarket: [
    'function postBid(uint256 depositAmount,uint256 tokenBudget,uint256 maxPricePerToken,uint256 categoryId,uint8 minTier,uint64 expiresAt) returns (uint256)',
    'function getBid(uint256) view returns (tuple(address user,uint256 depositAmount,uint256 tokenBudget,uint256 maxPricePerToken,uint256 categoryId,uint8 minTier,uint64 expiresAt,uint256 claimedByAgentId,bool settled,bool cancelled))',
    'function cancelBid(uint256)',
  ],
};
