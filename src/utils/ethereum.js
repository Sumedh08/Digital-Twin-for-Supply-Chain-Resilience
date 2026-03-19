/**
 * CarbonShip Ethereum Integration
 * 
 * Provides MetaMask wallet connection and CBAMRegistry smart contract interaction.
 * Network: Ethereum Sepolia Testnet (Chain ID: 11155111)
 * 
 * All functions are safe to call without MetaMask installed — they return
 * helpful error objects that the UI can display.
 */

import { ethers } from 'ethers';

// Sepolia Testnet configuration
const SEPOLIA_CHAIN_ID = '0xaa36a7'; // 11155111 in hex
const SEPOLIA_NETWORK = {
    chainId: SEPOLIA_CHAIN_ID,
    chainName: 'Sepolia Testnet',
    rpcUrls: ['https://rpc.sepolia.org'],
    blockExplorerUrls: ['https://sepolia.etherscan.io'],
    nativeCurrency: { name: 'SepoliaETH', symbol: 'ETH', decimals: 18 },
};

// Contract ABI (minimal — only the functions we call)
const CBAM_REGISTRY_ABI = [
    "function recordEmission(string _shipmentId, string _exporter, string _product, uint256 _weightTonnes, uint256 _totalCO2Kg, uint256 _cbamTaxEurCents, uint256 _etsPriceEurCents, string _originPort, string _destinationPort) external",
    "function getEmission(string _shipmentId) external view returns (string exporter, string product, uint256 weightTonnes, uint256 totalCO2Kg, uint256 cbamTaxEurCents, uint256 etsPriceEurCents, string originPort, string destinationPort, address recordedBy, uint256 timestamp)",
    "function verifyRecord(string _shipmentId) external view returns (bool exists, uint256 timestamp, address recordedBy)",
    "function getRecordCount() external view returns (uint256)",
    "function getRecentShipmentIds(uint256 count) external view returns (string[])",
    "event EmissionRecorded(string indexed shipmentId, string exporter, uint256 totalCO2Kg, uint256 cbamTaxEurCents, address recordedBy, uint256 timestamp)"
];

// Contract address — set after deployment
let CONTRACT_ADDRESS = null;

/**
 * Load deployment info. Call this once at app startup.
 */
export async function loadDeployment() {
    try {
        const response = await fetch('/contracts/deployment.json');
        if (response.ok) {
            const deployment = await response.json();
            CONTRACT_ADDRESS = deployment.contractAddress;
            console.log('✅ Loaded contract address:', CONTRACT_ADDRESS);
        }
    } catch {
        console.log('ℹ️ No deployment.json found. Deploy the contract first or set address manually.');
    }
}

/**
 * Check if MetaMask is installed
 */
export function isMetaMaskInstalled() {
    return typeof window !== 'undefined' && typeof window.ethereum !== 'undefined';
}

/**
 * Connect to MetaMask wallet and switch to Sepolia network
 * @returns {{ address: string, balance: string, network: string } | { error: string }}
 */
export async function connectWallet() {
    if (!isMetaMaskInstalled()) {
        return { error: 'MetaMask not installed. Please install it from metamask.io' };
    }

    try {
        // Request account access
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });

        // Check if we're on Sepolia
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        if (chainId !== SEPOLIA_CHAIN_ID) {
            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: SEPOLIA_CHAIN_ID }],
                });
            } catch (switchError) {
                // Chain not added to MetaMask — add it
                if (switchError.code === 4902) {
                    await window.ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [SEPOLIA_NETWORK],
                    });
                } else {
                    return { error: 'Please switch to Sepolia Testnet in MetaMask' };
                }
            }
        }

        // Get balance
        const provider = new ethers.BrowserProvider(window.ethereum);
        const balance = await provider.getBalance(accounts[0]);
        const balanceEth = ethers.formatEther(balance);

        return {
            address: accounts[0],
            balance: parseFloat(balanceEth).toFixed(4),
            network: 'Sepolia',
        };
    } catch (err) {
        return { error: err.message || 'Failed to connect wallet' };
    }
}

/**
 * Get the contract instance (connected to signer for write ops)
 */
async function getContract(needsSigner = false) {
    if (!CONTRACT_ADDRESS) {
        throw new Error('Contract not deployed. Run: cd contracts && npm run deploy:sepolia');
    }
    
    const provider = new ethers.BrowserProvider(window.ethereum);
    
    if (needsSigner) {
        const signer = await provider.getSigner();
        return new ethers.Contract(CONTRACT_ADDRESS, CBAM_REGISTRY_ABI, signer);
    }
    
    return new ethers.Contract(CONTRACT_ADDRESS, CBAM_REGISTRY_ABI, provider);
}

/**
 * Record an emission on-chain (requires MetaMask signature)
 * @param {Object} data - Emission data
 * @returns {{ txHash: string, explorerUrl: string } | { error: string }}
 */
export async function recordEmissionOnChain(data) {
    try {
        const contract = await getContract(true);

        // Scale EUR values to cents for integer storage
        const cbamTaxCents = Math.round((data.cbamTaxEur || 0) * 100);
        const etsPriceCents = Math.round((data.etsPriceEur || 68.35) * 100);
        const totalCO2Scaled = Math.round((data.totalCO2Kg || 0) * 100);

        const tx = await contract.recordEmission(
            data.shipmentId,
            data.exporter,
            data.product,
            data.weightTonnes,
            totalCO2Scaled,
            cbamTaxCents,
            etsPriceCents,
            data.originPort,
            data.destinationPort
        );

        // Wait for confirmation (1 block)
        const receipt = await tx.wait(1);

        return {
            success: true,
            txHash: receipt.hash,
            blockNumber: receipt.blockNumber,
            explorerUrl: `https://sepolia.etherscan.io/tx/${receipt.hash}`,
        };
    } catch (err) {
        if (err.code === 'ACTION_REJECTED') {
            return { error: 'Transaction rejected by user' };
        }
        return { error: err.reason || err.message || 'Transaction failed' };
    }
}

/**
 * Verify a record on-chain (read-only, no gas needed)
 */
export async function verifyRecordOnChain(shipmentId) {
    try {
        const contract = await getContract(false);
        const result = await contract.verifyRecord(shipmentId);
        
        return {
            exists: result.exists,
            timestamp: result.exists ? new Date(Number(result.timestamp) * 1000).toISOString() : null,
            recordedBy: result.recordedBy,
        };
    } catch (err) {
        return { error: err.message };
    }
}

/**
 * Get the total on-chain record count
 */
export async function getOnChainRecordCount() {
    try {
        const contract = await getContract(false);
        const count = await contract.getRecordCount();
        return Number(count);
    } catch {
        return 0;
    }
}

/**
 * Get recent shipment IDs from the chain
 */
export async function getRecentRecords(count = 10) {
    try {
        const contract = await getContract(false);
        return await contract.getRecentShipmentIds(count);
    } catch {
        return [];
    }
}

/**
 * Get Etherscan link for a transaction hash
 */
export function getExplorerLink(txHash) {
    return `https://sepolia.etherscan.io/tx/${txHash}`;
}

/**
 * Get Etherscan link for the contract
 */
export function getContractExplorerLink() {
    return CONTRACT_ADDRESS 
        ? `https://sepolia.etherscan.io/address/${CONTRACT_ADDRESS}`
        : null;
}

/**
 * Set contract address manually (for when deployment.json isn't available)
 */
export function setContractAddress(address) {
    CONTRACT_ADDRESS = address;
}
