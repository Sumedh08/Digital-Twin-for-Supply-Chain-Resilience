'use strict';

const { Contract } = require('fabric-contract-api');

class EmissionsContract extends Contract {

    async initLedger(ctx) {
        // No initial assets needed
    }

    async RecordEmission(ctx, correlationId, plantId, supplierId, stage, thingId, co2, timestamp, worldStateDigest, payload) {
        // Use a composite key or the correlationId + stage as the ID
        const id = `${correlationId}_${stage}_${thingId}`;
        const exists = await this.EmissionExists(ctx, id);
        if (exists) {
            throw new Error(`The emission record ${id} already exists`);
        }

        const record = {
            id: id,
            correlationId: correlationId,
            plantId: plantId,
            supplierId: supplierId,
            stage: stage,
            thingId: thingId,
            co2Tonnes: parseFloat(co2),
            timestamp: timestamp,
            worldStateDigest: worldStateDigest,
            payload: JSON.parse(payload),
            verifier: 'DigitalTwinEngine_Fabric_v1',
        };

        await ctx.stub.putState(id, Buffer.from(JSON.stringify(record)));
    }

    async QueryEmission(ctx, id) {
        const recordJSON = await ctx.stub.getState(id);
        if (!recordJSON || recordJSON.length === 0) {
            throw new Error(`The emission record ${id} does not exist`);
        }
        return recordJSON.toString();
    }

    async EmissionExists(ctx, id) {
        const recordJSON = await ctx.stub.getState(id);
        return recordJSON && recordJSON.length > 0;
    }

    async GetAllEmissions(ctx) {
        const allResults = [];
        const iterator = await ctx.stub.getStateByRange('', '');
        let result = await iterator.next();
        while (!result.done) {
            const strValue = Buffer.from(result.value.value.toString()).toString('utf8');
            let record;
            try {
                record = JSON.parse(strValue);
            } catch (err) {
                console.log(err);
                record = strValue;
            }
            allResults.push(record);
            result = await iterator.next();
        }
        return JSON.stringify(allResults);
    }

    async GetEmissionsByCorrelation(ctx, correlationId) {
        const allResults = [];
        const iterator = await ctx.stub.getStateByRange('', '');
        let result = await iterator.next();
        while (!result.done) {
            const strValue = Buffer.from(result.value.value.toString()).toString('utf8');
            let record;
            try {
                record = JSON.parse(strValue);
                if (record.correlationId === correlationId) {
                    allResults.push(record);
                }
            } catch (err) {
                // Skip if not JSON or doesn't match
            }
            result = await iterator.next();
        }
        return JSON.stringify(allResults);
    }
}

module.exports = EmissionsContract;
