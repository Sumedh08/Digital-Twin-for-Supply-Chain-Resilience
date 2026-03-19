const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("CBAMRegistry", function () {
  let registry;
  let owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const CBAMRegistry = await ethers.getContractFactory("CBAMRegistry");
    registry = await CBAMRegistry.deploy();
    await registry.waitForDeployment();
  });

  describe("Recording Emissions", function () {
    it("Should record an emission and increment count", async function () {
      await registry.recordEmission(
        "SHIP-001",
        "Tata Steel Ltd",
        "steel_hot_rolled",
        500,
        92500000,   // 925,000.00 kg CO2 (scaled by 100)
        560625,     // €5,606.25 in cents
        6835,       // €68.35 in cents
        "Mundra",
        "Rotterdam"
      );

      expect(await registry.getRecordCount()).to.equal(1);
    });

    it("Should emit EmissionRecorded event", async function () {
      await expect(
        registry.recordEmission(
          "SHIP-002", "JSW Steel", "steel_pipes", 100,
          19500000, 133200, 6835, "Mumbai", "Hamburg"
        )
      ).to.emit(registry, "EmissionRecorded")
       .withArgs("SHIP-002", "JSW Steel", 19500000, 133200, owner.address, await getBlockTimestamp());
    });

    it("Should prevent duplicate shipment IDs", async function () {
      await registry.recordEmission(
        "SHIP-003", "Hindalco", "aluminium_primary", 50,
        72500000, 495625, 6835, "Mundra", "Antwerp"
      );

      await expect(
        registry.recordEmission(
          "SHIP-003", "Hindalco", "aluminium_primary", 50,
          72500000, 495625, 6835, "Mundra", "Antwerp"
        )
      ).to.be.revertedWith("Record already exists");
    });

    it("Should reject empty shipment ID", async function () {
      await expect(
        registry.recordEmission(
          "", "Test", "steel_hot_rolled", 100,
          18500000, 126475, 6835, "Mumbai", "Rotterdam"
        )
      ).to.be.revertedWith("Shipment ID required");
    });
  });

  describe("Reading Records", function () {
    beforeEach(async function () {
      await registry.recordEmission(
        "SHIP-READ-001", "Tata Steel", "steel_hot_rolled", 500,
        92500000, 560625, 6835, "Mundra", "Rotterdam"
      );
    });

    it("Should retrieve a stored record", async function () {
      const record = await registry.getEmission("SHIP-READ-001");
      expect(record.exporter).to.equal("Tata Steel");
      expect(record.product).to.equal("steel_hot_rolled");
      expect(record.weightTonnes).to.equal(500);
    });

    it("Should verify record existence", async function () {
      const result = await registry.verifyRecord("SHIP-READ-001");
      expect(result.exists).to.be.true;
      expect(result.recordedBy).to.equal(owner.address);
    });

    it("Should return false for non-existent record", async function () {
      const result = await registry.verifyRecord("NONEXISTENT");
      expect(result.exists).to.be.false;
    });
  });

  describe("Enumeration", function () {
    it("Should return recent shipment IDs", async function () {
      await registry.recordEmission("A", "Ex1", "steel_hot_rolled", 10, 1850000, 12648, 6835, "P1", "P2");
      await registry.recordEmission("B", "Ex2", "cement_clinker", 20, 1700000, 11622, 6835, "P3", "P4");
      await registry.recordEmission("C", "Ex3", "aluminium_primary", 30, 43500000, 297225, 6835, "P5", "P6");

      const recent = await registry.getRecentShipmentIds(2);
      expect(recent.length).to.equal(2);
      expect(recent[0]).to.equal("C"); // Most recent first
      expect(recent[1]).to.equal("B");
    });
  });
});

async function getBlockTimestamp() {
  const block = await ethers.provider.getBlock("latest");
  return block.timestamp;
}
