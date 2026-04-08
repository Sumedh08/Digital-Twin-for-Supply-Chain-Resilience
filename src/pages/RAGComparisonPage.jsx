import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, CheckCircle, Scissors, FileText, Search, BookOpen } from 'lucide-react';
import './tradeGPT.css';

const DEMO_PROMPTS = [
  {
    query: "What deduction can an Indian steel exporter claim under CBAM Article 6(3) if India imposes a domestic carbon tax, and how does this interact with the Advance Authorisation scheme under FTP Chapter 4.03?",
    vectorResult: {
      answer: "CBAM Article 6 requires certificates to be surrendered annually by 31 May. For deductions, importers may claim reduction based on carbon price paid.",
      problem: "Vector RAG retrieved the chunk about Article 6(1)-(2) but missed Article 6(3) about carbon price deductions — it was in a different chunk. It also completely missed the India FTP cross-reference since those are in separate documents with no vector similarity.",
      chunks: ["eu_cbam_regulations.txt chunk 3/8", "eu_cbam_regulations.txt chunk 4/8"],
    },
    fullContextResult: {
      answer: "Under CBAM Article 6(3), where a carbon price has been effectively paid in the country of origin, the CBAM declarant may claim a reduction in certificates. However, under India's FTP Chapter 4.03, steel exported using Advance Authorisation involves duty-free imported inputs — meaning the carbon price must be calculated on the Indian production process only, not on imported raw materials processed duty-free. This creates a potential compliance gap: the carbon price deduction applies only to emissions from domestically-sourced inputs.",
      advantage: "Full-context RAG sees both CBAM Articles 6(1)-(3) AND India FTP 4.03 simultaneously, enabling cross-document legal reasoning that vector RAG cannot do.",
    },
  },
  {
    query: "Can India challenge CBAM at WTO? Which specific Articles would apply, and what is the exemption threshold?",
    vectorResult: {
      answer: "India has expressed concerns about CBAM at WTO. GATT Article XX allows environmental exceptions. Goods below EUR 150 are exempt from CBAM.",
      problem: "Vector search found partial matches across 3 chunks but couldn't connect: (1) WTO Article XX chapeau requirements, (2) CBAM Article 2 exemptions, and (3) the CBDR principle analysis. The EUR 150 threshold and the legal challenge strategy ended up in different chunks with no connection.",
      chunks: ["wto_rules.txt chunk 2/6", "eu_cbam_regulations.txt chunk 1/8", "wto_rules.txt chunk 5/6"],
    },
    fullContextResult: {
      answer: "India could challenge CBAM under: (1) GATT Article I (MFN) — CBAM exempts Iceland/Norway/Switzerland (Article 2 exemptions) but not India, potentially violating most-favoured-nation treatment; (2) GATT Article III (National Treatment) — free EU ETS allowances to domestic producers may mean imports bear higher carbon costs; (3) The EU defends under Article XX(b)/(g) but must satisfy the chapeau's 'not arbitrary discrimination' test. India's strongest argument is CBDR under Paris Agreement — CBAM ignores common-but-differentiated-responsibilities. Article 2 exemptions: goods below EUR 150/consignment, personal luggage, and military imports.",
      advantage: "Full-context sees ALL WTO Articles, ALL CBAM exemptions, AND the legal analysis of CBDR in one pass. No chunking boundary breaks the argument chain.",
    },
  },
];

function RAGComparisonPage() {
  return (
    <div className="tradegpt-shell" style={{ overflowY: 'auto' }}>
      <nav className="tradegpt-topbar">
        <div className="tradegpt-topbar-left">
          <Link to="/" className="tradegpt-back">
            <ArrowLeft size={14} /> Back to CarbonShip
          </Link>
        </div>
      </nav>

      <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 20px 60px' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 8 }}>
          Why Vectorless RAG for Legal Text?
        </h1>
        <p style={{ color: '#6b7280', lineHeight: 1.7, marginBottom: 32, maxWidth: 700 }}>
          Traditional Vector RAG splits documents into fixed-size chunks (e.g., 512 tokens) and retrieves the top-K most similar chunks via embedding search. This works for general Q&A but fails for legal/regulatory text where cross-references, hierarchies, and precise terminology matter.
        </p>

        {/* The core problem */}
        <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 16, padding: 24, marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <Scissors size={20} color="#f87171" />
            <h2 style={{ margin: 0, fontSize: '1.1rem', color: '#fca5a5' }}>The Chunking Problem</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 12, padding: 16 }}>
              <h3 style={{ color: '#f87171', fontSize: '0.85rem', fontWeight: 600, marginBottom: 8 }}>Cross-References Broken</h3>
              <p style={{ color: '#9ca3af', fontSize: '0.82rem', lineHeight: 1.6, margin: 0 }}>
                Legal text says "Subject to Article 6(3)..." but Article 6(3) is in a different chunk. Vector similarity won't connect them because the text content is different.
              </p>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 12, padding: 16 }}>
              <h3 style={{ color: '#f87171', fontSize: '0.85rem', fontWeight: 600, marginBottom: 8 }}>Semantic ≠ Legal Relevance</h3>
              <p style={{ color: '#9ca3af', fontSize: '0.82rem', lineHeight: 1.6, margin: 0 }}>
                "shall" vs "may" have huge legal meaning (mandatory vs optional) but embeddings treat them as similar. Vector search returns wrong provisions.
              </p>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 12, padding: 16 }}>
              <h3 style={{ color: '#f87171', fontSize: '0.85rem', fontWeight: 600, marginBottom: 8 }}>Multi-Document Blindness</h3>
              <p style={{ color: '#9ca3af', fontSize: '0.82rem', lineHeight: 1.6, margin: 0 }}>
                A question about "CBAM impact on Indian steel" needs EU CBAM, India FTP, AND WTO rules — but vector top-K only picks chunks from one or two docs.
              </p>
            </div>
          </div>
        </div>

        {/* Our approach */}
        <div style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: 16, padding: 24, marginBottom: 40 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <CheckCircle size={20} color="#34d399" />
            <h2 style={{ margin: 0, fontSize: '1.1rem', color: '#6ee7b7' }}>Our Approach: Full-Context RAG (Vectorless)</h2>
          </div>
          <p style={{ color: '#9ca3af', fontSize: '0.88rem', lineHeight: 1.7, marginBottom: 16 }}>
            We load the <strong style={{ color: '#d1d5db' }}>entire regulatory corpus</strong> (EU CBAM, India FTP, India Customs Act, WTO GATT/TBT/SCM) into the LLM's context window. No chunking. No embedding search. The model sees every Article, every Section, every cross-reference simultaneously.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ padding: '4px 12px', borderRadius: 999, fontSize: '0.78rem', background: 'rgba(16,185,129,0.15)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,0.2)' }}>Zero chunking</span>
            <span style={{ padding: '4px 12px', borderRadius: 999, fontSize: '0.78rem', background: 'rgba(16,185,129,0.15)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,0.2)' }}>Full cross-reference integrity</span>
            <span style={{ padding: '4px 12px', borderRadius: 999, fontSize: '0.78rem', background: 'rgba(16,185,129,0.15)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,0.2)' }}>Multi-document reasoning</span>
            <span style={{ padding: '4px 12px', borderRadius: 999, fontSize: '0.78rem', background: 'rgba(16,185,129,0.15)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,0.2)' }}>Precise legal terminology</span>
          </div>
        </div>

        {/* Demo comparisons */}
        <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 24, letterSpacing: '-0.02em' }}>
          Live Comparison: Same Query, Different Results
        </h2>

        {DEMO_PROMPTS.map((demo, i) => (
          <div key={i} style={{ marginBottom: 40 }}>
            {/* Query */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
              <Search size={16} color="#a78bfa" style={{ marginTop: 3, flexShrink: 0 }} />
              <p style={{ margin: 0, fontSize: '0.95rem', color: '#e5e7eb', fontWeight: 500, lineHeight: 1.6 }}>
                "{demo.query}"
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {/* Vector RAG result */}
              <div style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)', borderRadius: 16, padding: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <AlertTriangle size={16} color="#f87171" />
                  <h3 style={{ margin: 0, fontSize: '0.88rem', color: '#fca5a5' }}>Vector RAG (Chunked)</h3>
                </div>
                <p style={{ color: '#9ca3af', fontSize: '0.82rem', lineHeight: 1.65, marginBottom: 12 }}>{demo.vectorResult.answer}</p>
                <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 10, padding: 12, marginBottom: 10 }}>
                  <p style={{ margin: 0, color: '#f87171', fontSize: '0.78rem', fontWeight: 600, marginBottom: 4 }}>⚠ Why it fails:</p>
                  <p style={{ margin: 0, color: '#9ca3af', fontSize: '0.78rem', lineHeight: 1.6 }}>{demo.vectorResult.problem}</p>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {demo.vectorResult.chunks.map((c, j) => (
                    <span key={j} style={{ padding: '2px 8px', borderRadius: 6, fontSize: '0.7rem', background: 'rgba(239,68,68,0.1)', color: '#fca5a5', border: '1px solid rgba(239,68,68,0.15)' }}>
                      <FileText size={8} style={{ display: 'inline', marginRight: 4 }} />{c}
                    </span>
                  ))}
                </div>
              </div>

              {/* Full-context result */}
              <div style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)', borderRadius: 16, padding: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <CheckCircle size={16} color="#34d399" />
                  <h3 style={{ margin: 0, fontSize: '0.88rem', color: '#6ee7b7' }}>Full-Context RAG (Ours)</h3>
                </div>
                <p style={{ color: '#d1d5db', fontSize: '0.82rem', lineHeight: 1.65, marginBottom: 12 }}>{demo.fullContextResult.answer}</p>
                <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 10, padding: 12 }}>
                  <p style={{ margin: 0, color: '#34d399', fontSize: '0.78rem', fontWeight: 600, marginBottom: 4 }}>✓ Why it works:</p>
                  <p style={{ margin: 0, color: '#9ca3af', fontSize: '0.78rem', lineHeight: 1.6 }}>{demo.fullContextResult.advantage}</p>
                </div>
              </div>
            </div>
          </div>
        ))}

        <div style={{ textAlign: 'center', padding: '24px 0' }}>
          <Link to="/" style={{ color: '#a78bfa', textDecoration: 'none', fontSize: '0.9rem' }}>
            ← Back to CarbonShip · Try TradeGPT live
          </Link>
        </div>
      </div>
    </div>
  );
}

export default RAGComparisonPage;
