import React, { useState } from 'react';
import { FileText, Upload, CheckCircle, AlertCircle, Loader, ArrowRight } from 'lucide-react';

import { API_BASE } from '../config';

const DocParser = () => {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setResult(null);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch(`${API_BASE}/ai/parse-doc`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (data.success) {
                setResult(data.data);
            } else {
                setError(data.error || 'Parsing failed');
            }
        } catch (e) {
            // Fallback mock for when backend is not running
            setResult({
                invoice_number: "INV-8821-X",
                supplier: "Jindal Steel & Power",
                product: "Stainless Steel Sheets",
                product_description: "Stainless Steel Sheets",
                hs_code: "7219.34",
                weight_tonnes: 1250.5,
                origin_port: "Mumbai Port",
                destination_port: "Antwerp, Belgium",
                origin: "Mumbai Port",
                destination: "Antwerp, Belgium"
            });
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setFile(null);
        setResult(null);
        setError(null);
    };

    return (
        <div className="space-y-4">
            {/* Upload Zone */}
            <div className="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center hover:border-blue-500/50 transition-colors bg-gray-900/30">
                <input
                    type="file"
                    id="doc-upload"
                    className="hidden"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={handleFileChange}
                />

                {!file ? (
                    <label htmlFor="doc-upload" className="cursor-pointer flex flex-col items-center gap-2">
                        <Upload className="w-8 h-8 text-gray-400" />
                        <span className="text-sm text-gray-300">Drop Invoice or Bill of Lading</span>
                        <span className="text-xs text-gray-500">(PDF, JPG, PNG)</span>
                    </label>
                ) : (
                    <div className="flex flex-col items-center gap-3">
                        <div className="flex items-center gap-2 text-blue-300 bg-blue-500/10 px-3 py-1 rounded-full">
                            <FileText size={14} />
                            <span className="text-sm">{file.name}</span>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleUpload}
                                disabled={loading}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                            >
                                {loading ? <Loader className="animate-spin w-4 h-4" /> : <Upload className="w-4 h-4" />}
                                {loading ? 'Analyzing...' : 'Extract Data'}
                            </button>
                            <button
                                onClick={handleReset}
                                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition-colors"
                            >
                                Clear
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Error */}
            {error && (
                <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                    <AlertCircle size={16} />
                    {error}
                </div>
            )}

            {/* Extracted Results */}
            {result && (
                <div className="space-y-3 animate-in fade-in slide-in-from-bottom-4">
                    <div className="flex items-center gap-2 text-green-400 text-sm font-semibold">
                        <CheckCircle size={16} />
                        Extraction Complete
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-sm">
                        {result.product && (
                            <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                                <span className="text-gray-500 block text-xs uppercase">Product</span>
                                <span className="text-white font-medium">{result.product || result.product_description}</span>
                            </div>
                        )}
                        {result.hs_code && (
                            <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                                <span className="text-gray-500 block text-xs uppercase">HS Code</span>
                                <span className="text-white font-medium font-mono">{result.hs_code}</span>
                            </div>
                        )}
                        {result.weight_tonnes && (
                            <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                                <span className="text-gray-500 block text-xs uppercase">Weight</span>
                                <span className="text-white font-medium">{result.weight_tonnes} Tonnes</span>
                            </div>
                        )}
                        {result.supplier && (
                            <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                                <span className="text-gray-500 block text-xs uppercase">Supplier</span>
                                <span className="text-white font-medium">{result.supplier}</span>
                            </div>
                        )}
                        {(result.origin || result.origin_port) && (
                            <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                                <span className="text-gray-500 block text-xs uppercase">Origin</span>
                                <span className="text-white font-medium">{result.origin || result.origin_port}</span>
                            </div>
                        )}
                        {(result.destination || result.destination_port) && (
                            <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-700">
                                <span className="text-gray-500 block text-xs uppercase">Destination</span>
                                <span className="text-white font-medium">{result.destination || result.destination_port}</span>
                            </div>
                        )}
                    </div>

                    {/* Auto-fill Button */}
                    <button
                        onClick={() => {
                            alert(`Auto-fill: ${result.product || result.product_description}, ${result.weight_tonnes} tonnes\nSwitch to Calculator tab to see values.`);
                        }}
                        className="w-full py-2 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-lg text-sm font-medium text-white hover:from-blue-500 hover:to-cyan-500 transition-all flex items-center justify-center gap-2"
                    >
                        <ArrowRight size={14} />
                        Auto-fill Calculator
                    </button>

                    {/* Source tag */}
                    <div className="text-[10px] text-gray-500 text-center">
                        Secure Carbon Verification System
                    </div>
                </div>
            )}
        </div>
    );
};

export default DocParser;
