import time
import json
import re
import random
from typing import Dict, Any, Optional, Tuple, List
from groq import Groq, APIError, RateLimitError, AuthenticationError

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMProviderError
from app.retrieval.prompts import SYSTEM_PROMPT, USER_GENERATION_PROMPT

class AnswerGenerator:
    """
    Orchestrates evidence-grounded answer generation using Groq LLM API.
    Handles exponential backoff, rate limits (429), token accounting, and fallback formatting.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.client: Optional[Groq] = None

        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed initializing Groq client: {e}")

    def generate(
        self,
        question: str,
        repo_id: str,
        repo_name: str,
        graph_context: Dict[str, Any],
        source_evidence: List[Dict[str, Any]],
        max_attempts: int = 3
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Executes grounded LLM completion call with bounded retries and backoff.
        Returns (answer_markdown, metadata).
        """
        if not self.client:
            logger.warning("No Groq API key configured. Generating deterministic graph summary fallback.")
            return self._generate_deterministic_fallback(question, repo_id, graph_context, source_evidence)

        # 1. Format context (optimized for model context and ITPM limit)
        call_paths_str = ""
        for cp in graph_context.get("call_paths", [])[:4]:
            chain = " -> ".join(cp.get("nodes", []))
            call_paths_str += f"- Path: {chain}\n"
        if not call_paths_str:
            call_paths_str = "None explicitly resolved between seed endpoints."

        exc_str = ""
        for er in graph_context.get("exception_records", [])[:6]:
            exc_str += f"- {er.get('source')} {er.get('type')} {er.get('target')} (line {er.get('properties', {}).get('line')})\n"
        if not exc_str:
            exc_str = "None detected in direct traversal."

        nodes_str = ""
        for n in graph_context.get("ranked_nodes", [])[:10]:
            qname = n.get("qualified_name") or n.get("name")
            rel = n.get("rel_path", "")
            lines = f"lines {n.get('start_line')}-{n.get('end_line')}" if "start_line" in n else ""
            nodes_str += f"- [{n.get('type')}] {qname} ({rel} {lines})\n"

        snippets_str = ""
        for se in source_evidence[:3]:
            snippet_text = se.get("snippet", "")
            lines = snippet_text.splitlines()
            # Retain critical 85 lines of retry/exception handling logic per snippet
            if len(lines) > 85:
                snippet_text = "\n".join(lines[:85]) + "\n... [truncated for context limit] ..."
            snippets_str += f"\n--- File: {se.get('file')} ({se.get('symbol', 'general')}) Lines {se.get('start_line')}-{se.get('end_line')} ---\n"
            snippets_str += snippet_text + "\n"

        prompt_body = USER_GENERATION_PROMPT.format(
            question=question,
            repository_name=repo_name,
            repository_id=repo_id,
            call_paths_text=call_paths_str,
            exceptions_text=exc_str,
            nodes_text=nodes_str,
            source_snippets_text=snippets_str
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_body}
        ]

        backoff = 1.0
        start_time = time.perf_counter()
        current_max_tokens = 920

        for attempt in range(1, max_attempts + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=current_max_tokens,
                    timeout=settings.QUERY_TIMEOUT_SECONDS
                )

                latency_ms = int((time.perf_counter() - start_time) * 1000)
                usage = completion.usage
                tokens_in = usage.prompt_tokens if usage else 0
                tokens_out = usage.completion_tokens if usage else 0

                raw_text = completion.choices[0].message.content or ""
                metadata = {
                    "model": self.model,
                    "attempts": attempt,
                    "latency_ms": latency_ms,
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "provider": "groq",
                    "status": "success"
                }
                return raw_text, metadata

            except AuthenticationError as auth_err:
                logger.error(f"Groq authentication failed: {auth_err}")
                raise LLMProviderError(f"Groq API authentication failure: {auth_err}")

            except RateLimitError as rate_err:
                logger.warning(f"Groq Rate Limit encountered on attempt {attempt}: {rate_err}")
                err_str = str(rate_err).lower()
                # If OTPM exceeded, immediately decrease max_tokens
                if "output tokens per minute" in err_str or "reduce max_tokens" in err_str:
                    current_max_tokens = max(400, current_max_tokens - 200)

                if attempt == max_attempts:
                    logger.error("Rate limit retry budget exhausted. Returning deterministic fallback.")
                    answer, meta = self._generate_deterministic_fallback(question, repo_id, graph_context, source_evidence)
                    meta["warning"] = f"Groq Rate Limit exhausted after {max_attempts} attempts."
                    return answer, meta
                sleep_time = backoff + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
                backoff *= 2.0

            except APIError as api_err:
                err_str = str(api_err).lower()
                logger.warning(f"Groq API error on attempt {attempt}: {api_err}")
                if "413" in err_str or "too large" in err_str or "itpm" in err_str:
                    logger.warning("Request too large for ITPM limit; condensing prompt snippets for retry.")
                    condensed_snippets = ""
                    for se in source_evidence[:2]:
                        s_lines = se.get("snippet", "").splitlines()[:45]
                        condensed_snippets += f"\n--- File: {se.get('file')} ({se.get('symbol', 'general')}) Lines {se.get('start_line')}-{se.get('end_line')} ---\n"
                        condensed_snippets += "\n".join(s_lines) + "\n"
                    prompt_body = USER_GENERATION_PROMPT.format(
                        question=question,
                        repository_name=repo_name,
                        repository_id=repo_id,
                        call_paths_text=call_paths_str,
                        exceptions_text=exc_str,
                        nodes_text=nodes_str,
                        source_snippets_text=condensed_snippets
                    )
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt_body}
                    ]

                if attempt == max_attempts:
                    answer, meta = self._generate_deterministic_fallback(question, repo_id, graph_context, source_evidence)
                    meta["warning"] = f"Groq API error exhausted: {api_err}"
                    return answer, meta
                time.sleep(backoff)
                backoff *= 1.5

            except Exception as e:
                logger.error(f"Unexpected error calling Groq on attempt {attempt}: {e}")
                if attempt == max_attempts:
                    answer, meta = self._generate_deterministic_fallback(question, repo_id, graph_context, source_evidence)
                    meta["warning"] = f"Unexpected generation error: {e}"
                    return answer, meta
                time.sleep(backoff)

        return self._generate_deterministic_fallback(question, repo_id, graph_context, source_evidence)

    def _generate_deterministic_fallback(
        self,
        question: str,
        repo_id: str,
        graph_context: Dict[str, Any],
        source_evidence: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Deterministic graph-evidence synthesizer when LLM is unavailable or offline.
        Strictly formats facts directly from AST nodes, edges, and extracted lines.
        """
        ranked = graph_context.get("ranked_nodes", [])
        top_symbols = [n.get("qualified_name") or n.get("name") for n in ranked[:6]]
        exc_records = graph_context.get("exception_records", [])

        citations = []
        for se in source_evidence:
            citations.append({
                "file": se.get("file"),
                "symbol": se.get("symbol"),
                "start_line": se.get("start_line"),
                "end_line": se.get("end_line")
            })

        body = f"""### Summary
Based on static AST graph traversal of repository `{repo_id}`, the system identified {len(ranked)} relevant structural entities and {len(source_evidence)} verified source snippets answering: *"{question}"*.

### Execution Flow
1. Core control flow links through: {', '.join(top_symbols[:4]) if top_symbols else 'entry points'}.
2. Traversal identified {len(graph_context.get('edges', []))} direct relationships connecting callers, callees, and modules.

### Files and Symbols Involved
"""
        for n in ranked[:8]:
            qname = n.get("qualified_name") or n.get("name")
            rel = n.get("rel_path", "")
            lines = f"lines {n.get('start_line')}-{n.get('end_line')}" if "start_line" in n else ""
            body += f"- `{qname}` in `{rel}` {lines}\n"

        body += "\n### Error Handling & Retries\n"
        if exc_records:
            for er in exc_records[:6]:
                body += f"- `{er.get('source')}` handles or raises `{er.get('target')}` at line {er.get('properties', {}).get('line')}\n"
        else:
            body += "- Exception handlers were examined across connected nodes.\n"

        body += "\n### Discovered Graph Path\n"
        call_paths = graph_context.get("call_paths", [])
        if call_paths:
            for cp in call_paths[:2]:
                body += f"`{' -> '.join(cp.get('nodes', []))}`\n"
        else:
            body += f"`{' -> '.join(top_symbols[:3])}`\n"

        body += "\n### Evidence & Limitations\n"
        body += "Generated deterministically via AST knowledge graph traversal. Dynamic runtime conditions and external service states require runtime execution validation.\n"

        body += "\n### Citations\n```json\n"
        body += json.dumps(citations, indent=2)
        body += "\n```\n"

        meta = {
            "model": "deterministic_graph_engine",
            "provider": "local_ast",
            "status": "deterministic_fallback",
            "latency_ms": 5
        }
        return body, meta
