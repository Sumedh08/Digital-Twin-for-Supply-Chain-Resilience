import os
import hashlib
from datetime import datetime, timedelta
from groq import Groq

# Ensure paths relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(BASE_DIR, "data", "knowledge_base")

class LegalAdvisor:
    CACHE_TTL_MINUTES = 10

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = None
        self._cache = {}
        self.knowledge_base_text = self._load_all_knowledge()
        
        if self.api_key:
            self.model = Groq(api_key=self.api_key)
            print("✅ Groq (Trade Legal Advisor - Full Context) initialized")
        else:
            print("⚠️ No GROQ_API_KEY found. Legal Advisor running in MOCK mode.")

    def _load_all_knowledge(self) -> str:
        """Read all documents in knowledge_base into a single string for Context Injection."""
        print("📚 Loading Regulatory Knowledge Base into RAM...")
        text_data = []
        if os.path.exists(KB_PATH):
            for filename in os.listdir(KB_PATH):
                if filename.endswith(".txt") or filename.endswith(".md"):
                    filepath = os.path.join(KB_PATH, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        text_data.append(f"--- Document: {filename} ---\n{f.read()}\n")
            print(f"✅ Loaded {len(text_data)} regulatory documents into Context Memory.")
        else:
            print(f"⚠️ Knowledge base path not found: {KB_PATH}")
            text_data.append("No local regulations found. Rely on general AI knowledge.")
        return "\n".join(text_data)

    def _get_query_hash(self, query: str) -> str:
        return hashlib.md5(query.lower().strip().encode()).hexdigest()

    def _is_cache_valid(self, query_hash: str) -> bool:
        if query_hash not in self._cache:
            return False
        _, timestamp = self._cache[query_hash]
        return datetime.now() - timestamp < timedelta(minutes=self.CACHE_TTL_MINUTES)

    async def ask_question(self, user_query):
        query_hash = self._get_query_hash(user_query)
        if self._is_cache_valid(query_hash):
            result, _ = self._cache[query_hash]
            return {**result, "cached": True}

        if not self.model:
            return self._get_mock_answer(user_query)

        try:
            print(f"🤖 Calling Groq Legal API: {user_query[:50]}...")
            
            system_prompt = f"""You are a Trade Legal Advisor specializing in EU CBAM and WTO Rules.
CRITICAL INSTRUCTIONS:
1. Answer ONLY based on the provided regulatory CONTEXT below.
2. Always cite the specific Article/Document from the CONTEXT that supports your answer.
3. If the question goes beyond the CONTEXT, state you cannot confirm.
4. Format responses clearly with bullet points.

=== GLOBAL REGULATORY CONTEXT ===
{self.knowledge_base_text}
"""

            completion = self.model.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                max_completion_tokens=1024
            )

            answer_text = completion.choices[0].message.content
            
            # Extract citations dynamically based on whether the model used "Article" or a doc name
            citations = []
            if "Article" in answer_text or "ARTICLE" in answer_text:
                citations.append("Official Regulatory Articles")
            if "WTO" in answer_text:
                citations.append("WTO Rules Reference")
            if not citations:
                citations.append("CarbonShip Knowledge Base")

            result = {
                "answer": answer_text,
                "citations": citations,
                "confidence": "High (Grounded in Full RAM Context)",
                "source": "Llama 3.3 70B (Full Context Agent)"
            }

            self._cache[query_hash] = (result, datetime.now())
            return result

        except Exception as e:
            import traceback
            print(f"❌ Groq Error (Legal): {str(e)}")
            print(traceback.format_exc())
            result = self._get_mock_answer(user_query)
            result["confidence"] = "Medium (Fallback - API Error)"
            self._cache[query_hash] = (result, datetime.now())
            return result

    def _get_mock_answer(self, query: str) -> dict:
        return {
            "answer": "**CBAM Guidelines:**\nFallback mock answer. Ensure API key is correct and network is stable.",
            "citations": ["System Fallback"],
            "confidence": "Low",
            "source": "Simulation / Fallback"
        }

legal_advisor = LegalAdvisor()
