const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying CBAMRegistry to", hre.network.name, "...");

  const CBAMRegistry = await hre.ethers.getContractFactory("CBAMRegistry");
  const registry = await CBAMRegistry.deploy();
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  console.log("✅ CBAMRegistry deployed to:", address);

  // Save deployment info for backend and frontend
  const deploymentInfo = {
    network: hre.network.name,
    contractAddress: address,
    deployedAt: new Date().toISOString(),
    abi: JSON.parse(registry.interface.formatJson()),
  };

  // Write to contracts/deployment.json (used by backend and frontend)
  const outputPath = path.join(__dirname, "..", "deployment.json");
  fs.writeFileSync(outputPath, JSON.stringify(deploymentInfo, null, 2));
  console.log("📄 Deployment info saved to:", outputPath);

  // Also copy ABI to frontend src/utils/ for ethers.js
  const frontendAbiPath = path.join(__dirname, "..", "..", "src", "utils", "CBAMRegistryABI.json");
  fs.mkdirSync(path.dirname(frontendAbiPath), { recursive: true });
  fs.writeFileSync(frontendAbiPath, JSON.stringify(deploymentInfo.abi, null, 2));
  console.log("📄 ABI saved to frontend:", frontendAbiPath);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
