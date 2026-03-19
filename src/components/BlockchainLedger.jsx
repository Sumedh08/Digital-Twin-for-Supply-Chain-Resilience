import React, { useState, useEffect } from 'react';
import { Box, Link2, Shield, CheckCircle, AlertTriangle, Zap, Clock, Wallet, ExternalLink, Globe, Cpu } from 'lucide-react';

import { API_BASE } from '../config';
import {
    isMetaMaskInstalled,
    connectWallet,
    recordEmissionOnChain,
    verifyRecordOnChain,
    getOnChainRecordCount,
    getContractExplorerLink,
} from '../utils/ethereum';

/**
 * BlockchainLedger Component
 * Dual-mode: Local Python chain + Ethereum Sepolia on-chain recording
 */
const BlockchainLedger = () => {
    // Local chain state
    const [chain, setChain] = useState([]);
    const [chainValid, setChainValid] = useState(true);
    const [loading, setLoading] = useState(true);
    const [executing, setExecuting] = useState(false);
    const [lastReceipt, setLastReceipt] = useState(null);

    // Ethereum state
    const [walletAddress, setWalletAddress] = useState(null);
    const [walletBalance, setWalletBalance] = useState(null);
    const [onChainCount, setOnChainCount] = useState(0);
    const [ethTxHash, setEthTxHash] = useState(null);
    const [ethError, setEthError] = useState(null);
    const [recordingOnChain, setRecordingOnChain] = useState(false);
    const [activeTab, setActiveTab] = useState('local'); // 'local' | 'onchain'

    const fetchChain = async () => {
        try {
            const response = await fetch(`${API_BASE}/blockchain/chain`);
            const data = await response.json();
            if (data.success) {
                setChain(data.blocks);
                setChainValid(data.is_valid);
            }
        } catch (err) {
            console.error('Failed to fetch chain:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchChain();
        // Check if already connected
        if (isMetaMaskInstalled() && window.ethereum.selectedAddress) {
            handleConnectWallet();
        }
    }, []);

    const handleConnectWallet = async () => {
        const result = await connectWallet();
        if (result.error) {
            setEthError(result.error);
        } else {
            setWalletAddress(result.address);
            setWalletBalance(result.balance);
            setEthError(null);
            // Fetch on-chain record count
            const count = await getOnChainRecordCount();
            setOnChainCount(count);
        }
    };

    const executeContract = async () => {
        setExecuting(true);
        try {
            const response = await fetch(`${API_BASE}/blockchain/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shipment_id: `SHIP-${Date.now()}`,
                    exporter: "Tata Steel Ltd",
                    product_type: "steel_hot_rolled",
                    weight_tonnes: 500,
                    origin_port: "Mundra",
                    destination_port: "Rotterdam",
                    distance_km: 11265,
                    transport_mode: "container_ship",
                    origin_country: "India",
                    ship_type: "Container Ship"
                })
            });
            const data = await response.json();
            if (data.success) {
                setLastReceipt(data.receipt);
                await fetchChain();
            }
        } catch (err) {
            console.error('Contract execution failed:', err);
        } finally {
            setExecuting(false);
        }
    };

    const executeOnChain = async () => {
        if (!walletAddress) {
            setEthError('Connect MetaMask first');
            return;
        }
        setRecordingOnChain(true);
        setEthError(null);
        setEthTxHash(null);

        try {
            // First execute locally to get the receipt data
            const response = await fetch(`${API_BASE}/blockchain/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shipment_id: `SHIP-${Date.now()}`,
                    exporter: "Tata Steel Ltd",
                    product_type: "steel_hot_rolled",
                    weight_tonnes: 500,
                    origin_port: "Mundra",
                    destination_port: "Rotterdam",
                    distance_km: 11265,
                    transport_mode: "container_ship",
                    origin_country: "India",
                    ship_type: "Container Ship"
                })
            });
            const localData = await response.json();

            if (localData.success) {
                setLastReceipt(localData.receipt);
                await fetchChain();

                // Now record on Ethereum
                const ethResult = await recordEmissionOnChain({
                    shipmentId: localData.receipt.shipment_id,
                    exporter: "Tata Steel Ltd",
                    product: "steel_hot_rolled",
                    weightTonnes: 500,
                    totalCO2Kg: localData.receipt.total_co2_kg,
                    cbamTaxEur: localData.receipt.cbam_tax_eur,
                    etsPriceEur: localData.receipt.ets_price_used,
                    originPort: "Mundra",
                    destinationPort: "Rotterdam"
                });

                if (ethResult.error) {
                    setEthError(ethResult.error);
                } else {
                    setEthTxHash(ethResult.txHash);
                    const count = await getOnChainRecordCount();
                    setOnChainCount(count);
                }
            }
        } catch (err) {
            setEthError(err.message || 'Failed to execute');
        } finally {
            setRecordingOnChain(false);
        }
    };

    const truncateHash = (hash) => {
        if (!hash) return '';
        return `${hash.substring(0, 8)}...${hash.substring(hash.length - 6)}`;
    };

    const truncateAddress = (addr) => {
        if (!addr) return '';
        return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-500/20 rounded-lg">
                        <Link2 className="text-purple-400" size={20} />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">CarbonChain Ledger</h3>
                        <p className="text-xs text-gray-400">Ethereum Sepolia + Local PoW</p>
                    </div>
                </div>
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs ${chainValid ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {chainValid ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
                    {chainValid ? 'Valid' : 'Corrupted'}
                </div>
            </div>

            {/* MetaMask Connection */}
            <div className="bg-gradient-to-r from-orange-500/10 to-purple-500/10 border border-orange-500/20 rounded-xl p-3">
                {walletAddress ? (
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                            <span className="text-xs text-gray-300">
                                <span className="text-orange-400 font-mono">{truncateAddress(walletAddress)}</span>
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400">{walletBalance} ETH</span>
                            <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-[10px] rounded-full">Sepolia</span>
                        </div>
                    </div>
                ) : (
                    <button
                        onClick={handleConnectWallet}
                        className="w-full flex items-center justify-center gap-2 py-2 text-sm text-orange-300 hover:text-orange-200 transition-colors"
                    >
                        <Wallet size={16} />
                        Connect MetaMask (Sepolia)
                    </button>
                )}
            </div>

            {/* Tab Switcher */}
            <div className="flex gap-1 bg-white/5 rounded-lg p-1">
                <button
                    onClick={() => setActiveTab('local')}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-medium transition-all ${activeTab === 'local' ? 'bg-purple-500/30 text-purple-300' : 'text-gray-400 hover:text-gray-300'}`}
                >
                    <Cpu size={12} />
                    Local Chain
                </button>
                <button
                    onClick={() => setActiveTab('onchain')}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-medium transition-all ${activeTab === 'onchain' ? 'bg-blue-500/30 text-blue-300' : 'text-gray-400 hover:text-gray-300'}`}
                >
                    <Globe size={12} />
                    On-Chain (Sepolia)
                </button>
            </div>

            {/* Execute Buttons */}
            {activeTab === 'local' ? (
                <button
                    onClick={executeContract}
                    disabled={executing}
                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg font-semibold text-white text-sm flex items-center justify-center gap-2 hover:from-purple-500 hover:to-blue-500 transition-all disabled:opacity-50"
                >
                    {executing ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Mining Block...
                        </>
                    ) : (
                        <>
                            <Zap size={16} />
                            Execute Local Smart Contract
                        </>
                    )}
                </button>
            ) : (
                <button
                    onClick={executeOnChain}
                    disabled={recordingOnChain || !walletAddress}
                    className="w-full py-3 bg-gradient-to-r from-orange-600 to-red-600 rounded-lg font-semibold text-white text-sm flex items-center justify-center gap-2 hover:from-orange-500 hover:to-red-500 transition-all disabled:opacity-50"
                >
                    {recordingOnChain ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Recording on Ethereum...
                        </>
                    ) : (
                        <>
                            <Globe size={16} />
                            {walletAddress ? 'Record on Sepolia' : 'Connect Wallet First'}
                        </>
                    )}
                </button>
            )}

            {/* Ethereum Transaction Result */}
            {ethTxHash && (
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-blue-400 text-sm font-semibold mb-2">
                        <CheckCircle size={14} />
                        On-Chain Transaction Confirmed
                    </div>
                    <div className="text-xs space-y-1">
                        <div className="flex justify-between">
                            <span className="text-gray-400">Tx Hash:</span>
                            <span className="font-mono text-blue-300">{truncateHash(ethTxHash)}</span>
                        </div>
                    </div>
                    <a
                        href={`https://sepolia.etherscan.io/tx/${ethTxHash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                        <ExternalLink size={12} />
                        View on Etherscan
                    </a>
                </div>
            )}

            {/* Error Display */}
            {ethError && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-xs text-red-400">
                    ⚠️ {ethError}
                </div>
            )}

            {/* Local Receipt */}
            {lastReceipt && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-green-400 text-xs font-semibold mb-2">
                        <CheckCircle size={14} />
                        Transaction Confirmed
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="text-gray-400">Block Hash:</div>
                        <div className="text-white font-mono">{truncateHash(lastReceipt.block_hash)}</div>
                        <div className="text-gray-400">Total CO₂:</div>
                        <div className="text-white">{(lastReceipt.total_co2_kg / 1000).toFixed(2)} tonnes</div>
                        <div className="text-gray-400">CBAM Tax:</div>
                        <div className="text-emerald-400 font-semibold">€{lastReceipt.cbam_tax_eur.toLocaleString()}</div>
                    </div>
                </div>
            )}

            {/* Chain Visualization */}
            {activeTab === 'local' && (
                <div className="space-y-3 max-h-48 overflow-y-auto pr-2">
                    {chain.slice().reverse().map((block, idx) => (
                        <div key={block.index} className="relative">
                            {idx > 0 && (
                                <div className="absolute -top-3 left-5 w-0.5 h-3 bg-purple-500/50"></div>
                            )}
                            <div className={`bg-white/5 rounded-lg p-3 border ${block.index === 0 ? 'border-yellow-500/50' : 'border-white/10'}`}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <Box size={14} className={block.index === 0 ? 'text-yellow-400' : 'text-purple-400'} />
                                        <span className="text-sm font-semibold text-white">
                                            {block.index === 0 ? 'Genesis Block' : `Block #${block.index}`}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-1 text-xs text-gray-500">
                                        <Clock size={10} />
                                        {new Date(block.timestamp).toLocaleTimeString()}
                                    </div>
                                </div>
                                <div className="text-xs space-y-1">
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Hash:</span>
                                        <span className="font-mono text-purple-300">{truncateHash(block.hash)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Txns:</span>
                                        <span className="text-white">{block.transactions.length}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Nonce:</span>
                                        <span className="text-gray-300">{block.nonce}</span>
                                    </div>
                                </div>
                                {block.transactions.length > 0 && (
                                    <div className="mt-2 pt-2 border-t border-white/10">
                                        {block.transactions.slice(0, 1).map((tx, i) => (
                                            <div key={i} className="text-xs bg-purple-500/10 rounded p-2">
                                                <div className="flex justify-between">
                                                    <span className="text-gray-400">Exporter:</span>
                                                    <span className="text-white">{tx.exporter}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-400">Tax:</span>
                                                    <span className="text-emerald-400">€{tx.cbam_tax_eur?.toFixed(2)}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* On-Chain Tab Content */}
            {activeTab === 'onchain' && (
                <div className="space-y-3">
                    <div className="bg-white/5 rounded-lg p-4 border border-blue-500/20">
                        <div className="text-center">
                            <div className="text-3xl font-bold text-blue-400">{onChainCount}</div>
                            <div className="text-xs text-gray-400 mt-1">Records on Sepolia</div>
                        </div>
                    </div>
                    
                    {getContractExplorerLink() && (
                        <a
                            href={getContractExplorerLink()}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-2 w-full py-2 bg-white/5 rounded-lg text-xs text-blue-400 hover:text-blue-300 transition-colors border border-white/10"
                        >
                            <ExternalLink size={12} />
                            View Contract on Etherscan
                        </a>
                    )}

                    <div className="text-center text-xs text-gray-500 py-4">
                        {!walletAddress ? (
                            <p>Connect MetaMask to interact with the Sepolia contract</p>
                        ) : !getContractExplorerLink() ? (
                            <div className="space-y-2">
                                <p className="text-yellow-400">Contract not yet deployed</p>
                                <p className="text-gray-500">Run: <code className="bg-white/10 px-1 rounded">cd contracts && npm run deploy:sepolia</code></p>
                            </div>
                        ) : (
                            <p>Click "Record on Sepolia" to store data on Ethereum</p>
                        )}
                    </div>
                </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-white/5 rounded-lg p-2">
                    <div className="text-lg font-bold text-purple-400">{chain.length}</div>
                    <div className="text-xs text-gray-400">Local Blocks</div>
                </div>
                <div className="bg-white/5 rounded-lg p-2">
                    <div className="text-lg font-bold text-blue-400">{onChainCount}</div>
                    <div className="text-xs text-gray-400">On-Chain</div>
                </div>
                <div className="bg-white/5 rounded-lg p-2">
                    <div className="text-lg font-bold text-green-400">{chain.reduce((acc, b) => acc + b.transactions.length, 0)}</div>
                    <div className="text-xs text-gray-400">Total Txns</div>
                </div>
            </div>
        </div>
    );
};

export default BlockchainLedger;
