import os
import json
import ast
import subprocess
import socket
import sys
import time
import re
import uuid
import secrets
import urllib.request
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURATION & PORT MANAGEMENT
# ============================================================

BASE_AGENT_PORT = int(os.getenv("BASE_AGENT_PORT", os.getenv("AGENT_PORT_START", "9000")))
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {}

print("Imports loaded successfully.")

# ============================================================
# TOOL REGISTRY
# ============================================================

TOOL_REGISTRY = {
    "calculator": {
        "category": "basic",
        "package": "Python",
        "imports": [],
        "implementation": "Python arithmetic",
        "description": "Perform mathematical calculations."
    },
    "text_processor": {
        "category": "basic",
        "package": "Python",
        "imports": [],
        "implementation": "Python string operations",
        "description": "Process and transform text."
    },
    "pdf_loader": {
        "category": "document",
        "package": "PyMuPDF",
        "imports": ["import pymupdf"],
        "implementation": "pymupdf.open",
        "description": "Load PDF documents."
    },
    "pdf_text_extractor": {
        "category": "document",
        "package": "PyMuPDF",
        "imports": ["import pymupdf"],
        "implementation": "page.get_text",
        "description": "Extract text from PDF pages."
    },
    "ocr": {
        "category": "document",
        "package": "pytesseract",
        "imports": ["import pytesseract"],
        "implementation": "pytesseract.image_to_string",
        "description": "Read scanned documents."
    },
    "document_chunker": {
        "category": "document",
        "package": "langchain-text-splitters",
        "imports": [
            "from langchain_text_splitters import RecursiveCharacterTextSplitter"
        ],
        "implementation": "RecursiveCharacterTextSplitter",
        "description": "Split long documents into chunks."
    },
    "embeddings": {
        "category": "retrieval",
        "package": "sentence-transformers",
        "imports": [
            "from sentence_transformers import SentenceTransformer"
        ],
        "implementation": "SentenceTransformer",
        "description": "Generate semantic embeddings."
    },
    "vector_store": {
        "category": "retrieval",
        "package": "faiss-cpu",
        "imports": ["import faiss"],
        "implementation": "faiss.IndexFlatL2",
        "description": "Store and search embeddings."
    },
    "file_reader": {
        "category": "coding",
        "package": "Python",
        "imports": ["from pathlib import Path"],
        "implementation": "Path.read_text",
        "description": "Read project files."
    },
    "file_writer": {
        "category": "coding",
        "package": "Python",
        "imports": ["from pathlib import Path"],
        "implementation": "Path.write_text",
        "description": "Write or modify files."
    },
    "python_executor": {
        "category": "coding",
        "package": "Python",
        "imports": ["import subprocess"],
        "implementation": "subprocess.run",
        "description": "Execute Python code."
    },
    "web_search": {
        "category": "web",
        "package": "requests",
        "imports": ["import requests"],
        "implementation": "HTTP requests",
        "description": "Search or access web information."
    },
    "llm": {
        "category": "core",
        "package": "langchain-groq",
        "imports": [
            "from langchain_groq import ChatGroq"
        ],
        "implementation": "ChatGroq",
        "description": "Generate natural-language responses."
    }
}

print(f"{len(TOOL_REGISTRY)} tools available.")

APPROVED_IMPORTS = {
    # Standard Python Libraries
    "os", "json", "subprocess", "sys", "pathlib", "typing", "tempfile",
    "time", "re", "math", "shutil", "io", "uuid", "datetime", "dataclasses",
    "collections", "itertools", "functools", "traceback", "inspect",

    # Document & Vision
    "pymupdf", "fitz", "pytesseract", "PIL", "pillow",

    # Retrieval & ML & Networking
    "faiss", "numpy", "requests", "httpx", "urllib", "sentence_transformers",

    # LangChain / LangGraph ecosystem
    "langchain", "langchain_core", "langchain_groq", "langchain_google_genai",
    "langchain_community", "langchain_text_splitters", "langgraph",

    # Schemas & API
    "pydantic", "fastapi", "uvicorn", "openai", "google"
}


# ============================================================
# CENTRALIZED CONTENT & JSON HELPERS
# ============================================================

def _extract_model_content(response: Any) -> str:
    """Safely extract pure string content from any model response format."""
    if response is None:
        return ""

    if isinstance(response, str):
        content = response
    elif hasattr(response, "content"):
        content = response.content
    elif hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            content = choice.message.content
        elif isinstance(choice, dict):
            content = choice.get("message", {}).get("content", "")
        else:
            content = str(choice)
    elif isinstance(response, dict):
        if "content" in response:
            content = response["content"]
        elif "choices" in response and response["choices"]:
            first = response["choices"][0]
            if isinstance(first, dict):
                content = first.get("message", {}).get("content", "")
            else:
                content = str(first)
        elif "text" in response:
            content = response["text"]
        else:
            content = str(response)
    else:
        content = response

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
                else:
                    parts.append(str(item))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
            else:
                parts.append(str(item))
        content = "\n".join(parts)
    elif isinstance(content, dict):
        if "text" in content:
            content = str(content["text"])
        elif "content" in content:
            content = str(content["content"])
        else:
            content = str(content)
    elif not isinstance(content, str):
        content = str(content) if content is not None else ""

    if "</think>" in content:
        content = content.split("</think>")[-1].strip()
    else:
        content = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()

    return content.strip()


def _clean_json_text(text: str) -> str:
    """Clean markdown fences, tags, and whitespace from JSON strings."""
    if not text:
        return ""
    cleaned = text.strip()

    if "</think>" in cleaned:
        cleaned = cleaned.split("</think>")[-1].strip()
    else:
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE).strip()

    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()
    else:
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    return cleaned


def _repair_truncated_json(text: str, expected_type: str = "object") -> Any:
    """Attempt to repair slightly truncated or unclosed JSON output."""
    t = text.strip()
    if expected_type == "object" and not t.startswith("{"):
        idx = t.find("{")
        if idx != -1:
            t = t[idx:]
    elif expected_type == "list" and not t.startswith("["):
        idx = t.find("[")
        if idx != -1:
            t = t[idx:]

    t = re.sub(r",\s*([\]}])", r"\1", t)

    for suffix in ["", "}", "]}", '"}', '"]', '"]}', '", "capabilities": [], "required_tools": ["llm"], "complexity": "SIMPLE", "agent_type": "simple"}']:
        try:
            val = json.loads(t + suffix)
            if expected_type == "object" and isinstance(val, dict):
                return val
            if expected_type == "list" and isinstance(val, list):
                return val
        except Exception:
            pass

    return None


def _parse_json_response(response: Any, expected_type: str = "object") -> Any:
    """Robustly parse JSON object or array from LLM responses."""
    raw_text = _extract_model_content(response)
    text = _clean_json_text(raw_text)

    try:
        val = json.loads(text)
        if expected_type == "object" and isinstance(val, dict):
            return val
        if expected_type == "list" and isinstance(val, list):
            return val
        if expected_type == "any":
            return val
    except Exception:
        pass

    matches = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text, flags=re.IGNORECASE)
    for match in reversed(matches):
        try:
            val = json.loads(match.strip())
            if expected_type == "object" and isinstance(val, dict):
                return val
            if expected_type == "list" and isinstance(val, list):
                return val
            if expected_type == "any":
                return val
        except Exception:
            pass

    open_char = "{" if expected_type == "object" else "["
    close_char = "}" if expected_type == "object" else "]"

    indices = [i for i, c in enumerate(text) if c == open_char]
    for start in reversed(indices):
        end = text.rfind(close_char, start)
        if end != -1:
            candidate = text[start : end + 1]
            try:
                val = json.loads(candidate)
                if expected_type == "object" and isinstance(val, dict):
                    return val
                if expected_type == "list" and isinstance(val, list):
                    return val
                if expected_type == "any":
                    return val
            except Exception:
                pass

    repaired = _repair_truncated_json(text, expected_type=expected_type)
    if repaired is not None:
        return repaired

    raise ValueError(f"Failed to parse valid JSON ({expected_type}) from response:\n{raw_text[:500]}")


def _clean_code_response(response: Any) -> str:
    """Clean markdown fences and extract raw Python source code."""
    text = _extract_model_content(response)

    fenced = re.findall(r"```(?:python|py)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fenced:
        extracted = fenced[-1].strip()
    else:
        extracted = text.strip()
        if extracted.startswith("```"):
            extracted = re.sub(r"^```(?:python|py)?\s*", "", extracted, flags=re.IGNORECASE)
            extracted = re.sub(r"\s*```$", "", extracted).strip()

    if extracted.startswith("{") and extracted.endswith("}"):
        try:
            data = json.loads(extracted)
            if isinstance(data, dict) and "code" in data and isinstance(data["code"], str):
                extracted = data["code"].strip()
        except Exception:
            pass

    return extracted


# ============================================================
# MULTI-PROVIDER LLM CALLER WITH MULTI-MODEL FALLBACK
# ============================================================

def _call_gemini(prompt: str, api_key: str, model_name: str) -> str:
    """Call Google Gemini model."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0, max_output_tokens=4096)
        res = llm.invoke(prompt)
        return _extract_model_content(res)
    except Exception:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        res = model.generate_content(prompt)
        return _extract_model_content(getattr(res, "text", res))


def _call_openrouter(prompt: str, api_key: str, model_name: str) -> str:
    """Call OpenRouter API."""
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=4096
    )
    return _extract_model_content(response)


def _call_groq(prompt: str, api_key: str, model_name: str) -> str:
    """Call Groq model."""
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(model=model_name, api_key=api_key, temperature=0, max_tokens=4096)
        res = llm.invoke(prompt)
        return _extract_model_content(res)
    except Exception:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=4096
        )
        return _extract_model_content(response)


def get_configured_providers(is_strong: bool = False) -> List[Tuple[str, Any, str, str]]:
    """
    Return list of Groq model configurations with fallback order.
    Uses openai/gpt-oss-120b as primary and openai/gpt-oss-20b as fallback.
    """
    providers = []
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        primary_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        models = [primary_model, "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        seen = set()
        for m in models:
            if m and m not in seen:
                seen.add(m)
                providers.append(("Groq", _call_groq, groq_key, m))

    return providers


def invoke_llm(prompt: str, is_strong: bool = False) -> str:
    """
    Invoke LLM exclusively via Groq using openai/gpt-oss-120b and openai/gpt-oss-20b
    with automatic fallback upon encountering rate limits (429), timeouts, or empty responses.
    """
    providers = get_configured_providers(is_strong=is_strong)

    if not providers:
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is not set in your environment or .env file.")
        providers = [
            ("Groq", _call_groq, groq_key, "openai/gpt-oss-120b"),
            ("Groq", _call_groq, groq_key, "openai/gpt-oss-20b")
        ]

    errors = []
    for name, func, key, model in providers:
        try:
            content = func(prompt, key, model)
            if content and content.strip():
                return content.strip()
            errors.append(f"{name} ({model}): Empty response returned")
        except Exception as e:
            err_str = str(e).strip()
            errors.append(f"{name} ({model}): {err_str}")
            time.sleep(0.3)

    raise RuntimeError(
        "Groq LLM invocation failed.\nErrors:\n" + "\n".join(f"- {err}" for err in errors)
    )


def _model_call(prompt: str, system_prompt: str = "", max_tokens: int = 4096, is_strong: bool = False) -> str:
    """Helper alias for model invocations."""
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    return invoke_llm(full_prompt, is_strong=is_strong)


def _json_model_call(
    prompt: str,
    is_strong: bool = False,
    max_retries: int = 3,
    expected_type: str = "object"
) -> Any:
    """Execute LLM call expecting JSON, with automatic retry and error correction prompt."""
    current_prompt = prompt
    last_err = None

    for attempt in range(max_retries):
        try:
            raw_response = invoke_llm(current_prompt, is_strong=is_strong)
            return _parse_json_response(raw_response, expected_type=expected_type)
        except Exception as e:
            last_err = e
            current_prompt = (
                f"{prompt}\n\n"
                f"IMPORTANT FIX: Your previous response was not valid JSON ({e}).\n"
                f"Please output ONLY valid, complete JSON {expected_type} with no markdown fences, explanations, or unescaped characters."
            )
            time.sleep(0.5)

    raise RuntimeError(f"Failed to obtain valid JSON from LLM after {max_retries} attempts: {last_err}")


# ============================================================
# PIPELINE STEPS
# ============================================================

def analyze_requirements(user_prompt: str) -> Dict[str, Any]:
    """Analyze user prompt to determine goal, capabilities, tools, complexity, and agent_type."""
    prompt = f"""You are an expert AI Architect analyzing user requirements for an autonomous AI agent.

USER REQUEST:
{user_prompt}

Analyze the request and determine:
1. Goal: High-level purpose of the agent.
2. Input: Description of expected user inputs (e.g. text prompt, PDF path, code snippet).
3. Output: Expected return type / format.
4. Capabilities: List of key functional capabilities required.
5. Required tools: Tools required from the registry (e.g. pdf_loader, pdf_text_extractor, file_reader, python_executor, web_search, llm).
6. Complexity:
   - "SIMPLE": A single LLM call or basic text Q&A logic without external tools.
   - "TOOL": Agent requires one or more external tools (e.g. PDF extraction, code executor, web search).
   - "COMPLEX": Multi-step orchestration, state management, retrieval pipelines, or LangGraph.
7. Agent Type:
   - "simple": General Q&A / conversational assistant.
   - "coding": Code analysis, debugging, refactoring, or execution.
   - "pdf": PDF reading, document question answering, and page citations.
   - "research": In-depth investigation, web/retrieval search, source comparison, and structured report synthesis.
   - "custom": Any specialized agent not fitting the above.

Respond ONLY with valid JSON:
{{
    "goal": "Description of the goal",
    "input": "Expected inputs",
    "output": "Expected outputs",
    "capabilities": ["capability 1", "capability 2"],
    "required_tools": ["tool1", "tool2"],
    "complexity": "SIMPLE | TOOL | COMPLEX",
    "agent_type": "simple | coding | pdf | research | custom"
}}
"""
    try:
        return _json_model_call(prompt, is_strong=False, expected_type="object")
    except Exception as exc:
        print(f"analyze_requirements LLM failed: {exc}, using deterministic analysis...")
        p_lower = user_prompt.lower()
        if "pdf" in p_lower or "document" in p_lower:
            return {
                "goal": "Process PDF documents, answer questions, and provide page citations.",
                "input": "User question and PDF document path.",
                "output": "Text response with page-level citations.",
                "capabilities": ["PDF reading", "text extraction", "question answering", "citation generation"],
                "required_tools": ["pdf_loader", "pdf_text_extractor", "llm"],
                "complexity": "COMPLEX",
                "agent_type": "pdf"
            }
        elif "code" in p_lower or "python" in p_lower or "debug" in p_lower:
            return {
                "goal": "Analyze code, detect bugs, and execute Python tests.",
                "input": "Code snippet or file path.",
                "output": "Bug explanations and corrected code.",
                "capabilities": ["Code parsing", "execution", "debugging"],
                "required_tools": ["file_reader", "python_executor", "llm"],
                "complexity": "COMPLEX",
                "agent_type": "coding"
            }
        elif "research" in p_lower or "search" in p_lower:
            return {
                "goal": "Perform external research and synthesize structured reports.",
                "input": "Research topic or query.",
                "output": "Structured report with sources.",
                "capabilities": ["Web search", "information synthesis"],
                "required_tools": ["web_search", "llm"],
                "complexity": "COMPLEX",
                "agent_type": "research"
            }
        else:
            return {
                "goal": "Answer general user queries directly.",
                "input": "Text prompt.",
                "output": "Conversational answer.",
                "capabilities": ["General reasoning"],
                "required_tools": ["llm"],
                "complexity": "SIMPLE",
                "agent_type": "simple"
            }


def select_tools(requirements: Dict[str, Any]) -> List[str]:
    """Select the minimal set of tools strictly required from TOOL_REGISTRY."""
    available_tools = [
        {
            "name": name,
            "description": info["description"],
            "category": info["category"]
        }
        for name, info in TOOL_REGISTRY.items()
    ]

    prompt = f"""You are a Tool Selection Agent.

USER REQUIREMENTS:
{json.dumps(requirements, indent=2)}

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

Rules:
1. Select ONLY tool names from AVAILABLE TOOLS.
2. Select only tools genuinely required for the task.
3. For simple Q&A: ["llm"]
4. For PDF document QA: ["pdf_loader", "pdf_text_extractor", "document_chunker", "embeddings", "vector_store", "llm"]
5. For coding/debugging: ["file_reader", "python_executor", "llm"]
6. For research: ["web_search", "file_reader", "llm"]

Return ONLY a JSON array of strings containing selected tool names.
Example:
["pdf_loader", "pdf_text_extractor", "llm"]
"""
    try:
        tools = _json_model_call(prompt, is_strong=False, expected_type="list")
    except Exception as exc:
        print(f"Tool selection LLM failed: {exc}, using fallback...")
        agent_type = str(requirements.get("agent_type", "custom")).lower()
        if agent_type == "pdf":
            tools = ["pdf_loader", "pdf_text_extractor", "document_chunker", "embeddings", "vector_store", "llm"]
        elif agent_type == "coding":
            tools = ["file_reader", "python_executor", "llm"]
        elif agent_type == "research":
            tools = ["web_search", "file_reader", "llm"]
        else:
            tools = ["llm"]

    selected = [t for t in tools if t in TOOL_REGISTRY]
    if "llm" not in selected:
        selected.append("llm")
    return selected


def generate_architecture(requirements: Dict[str, Any], tools: List[str]) -> str:
    """Generate architecture specification string."""
    complexity = requirements.get("complexity", "SIMPLE")

    if complexity == "SIMPLE":
        return """Architecture:
User Input
    ↓
LLM
    ↓
Response
"""

    if complexity == "TOOL":
        return f"""Architecture:
User Input
    ↓
LLM Decision / Input Preparation
    ↓
Tool Execution ({', '.join(tools)})
    ↓
LLM Synthesis
    ↓
Response
"""

    return f"""Architecture:
User Input
    ↓
Planning / Task Breakdown
    ↓
Tool Execution & Retrieval ({', '.join(tools)})
    ↓
Evidence Collection & Synthesis
    ↓
Validation
    ↓
Final Structured Output
"""


def create_agent_spec(
    user_prompt: str,
    requirements: Dict[str, Any],
    complexity: str,
    tools: List[str],
    architecture: str,
    agent_type: str = "custom"
) -> Dict[str, Any]:
    """Construct agent specification with explicit agent_type."""
    if not agent_type:
        agent_type = requirements.get("agent_type", "custom")

    return {
        "agent_name": f"{agent_type.capitalize()}Agent",
        "description": requirements.get("goal", user_prompt),
        "goal": requirements.get("goal", user_prompt),
        "input": requirements.get("input", "prompt"),
        "output": requirements.get("output", "response"),
        "complexity": complexity,
        "agent_type": agent_type,
        "tools": tools,
        "architecture": architecture,
        "model": {
            "provider": "groq",
            "model": (
                "openai/gpt-oss-20b"
                if complexity == "SIMPLE"
                else "openai/gpt-oss-120b"
            ),
            "temperature": 0
        }
    }


def generate_code(agent_spec: Dict[str, Any]) -> str:
    """Generate Python source code for the requested agent specification."""
    complexity = agent_spec.get("complexity", "SIMPLE")
    agent_type = agent_spec.get("agent_type", "custom")
    tools = agent_spec.get("tools", [])

    tool_details = [
        {
            "name": tool,
            "package": TOOL_REGISTRY[tool]["package"],
            "imports": TOOL_REGISTRY[tool]["imports"],
            "implementation": TOOL_REGISTRY[tool]["implementation"],
            "description": TOOL_REGISTRY[tool]["description"]
        }
        for tool in tools
        if tool in TOOL_REGISTRY
    ]

    prompt = f"""You are an expert Python AI Agent Developer.

Generate a self-contained, production-grade Python agent from this specification:

SPECIFICATION:
{json.dumps(agent_spec, indent=2)}

TOOLS:
{json.dumps(tool_details, indent=2)}

==================================================
ARCHITECTURAL GUIDELINES
==================================================

1. DO NOT OVERENGINEER. Use the simplest architecture that satisfies the specification.
2. ENTRY POINT: The module MUST define either `def agent(prompt: str, **kwargs):` or `def run_agent(prompt: str, **kwargs):`.
3. AGENT TYPE SPECIALIZATION:
   - If agent_type is "pdf":
     - Define `def agent(prompt: str, pdf_path: str = None):`.
     - If `pdf_path` is provided, open and extract content using PyMuPDF: `doc = pymupdf.open(pdf_path)`.
     - Extract page text with `page.get_text()`, format with page numbers, and query the LLM.
     - Never use `import fitz`. Use `import pymupdf`.
   - If agent_type is "coding":
     - Define `def agent(prompt: str, code: str = None):`.
     - Analyze code for syntax, logic, runtime errors, and provide explanations & fixes.
     - If `python_executor` is selected, execute safely via `subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)`.
   - If agent_type is "research":
     - By default define ONLY `def agent(prompt: str):`.
     - DO NOT add `pdf_path`, `file_path`, `context_file`, `context_path`, `document_path`, `document_file`, or any other file/document parameter.
     - Add an additional input ONLY when the SPECIFICATION explicitly requires that input.
     - If the specification says that a file/document/PDF is optional, it may be supported, but it must be an explicitly requested input and not invented by the model.
     - Perform task planning, evidence collection, synthesis, and structured report formatting.
   - For ALL agent types:
     - The API input must match the actual generated agent function.
     - NEVER add pdf_path, code, url, file_path, or another parameter merely because of the agent type.
     - Only create additional parameters that are actually needed.
     - The first parameter should be `prompt: str`.
     - Additional parameters should normally have defaults such as `None`.
   - If agent_type is "simple":
     - Build a direct Q&A agent using ChatGroq.

4. IMPORTS & MODELS:
   - For LLM calls: `from langchain_groq import ChatGroq`
   - Use `model = ChatGroq(model="openai/gpt-oss-120b", temperature=0)`
   - Never use `from langchain.schema import ...` (deprecated). Use `from langchain_core.messages import HumanMessage, SystemMessage` or pass prompt strings directly: `model.invoke(prompt)`.
   - Never use `import fitz`. Use `import pymupdf`.
   - Do not import unselected or obsolete libraries.

5. OUTPUT:
   - Return ONLY raw Python source code.
   - Include a standard `if __name__ == "__main__":` block with a simple test.
   IMPORTANT FILE READING RULES:

When the generated agent scans a project:

1. Never assume every file is UTF-8.
2. Never read binary files as text.
3. Only inspect text/source files.
4. Use a safe text reader with encoding fallback.
5. If a file cannot be decoded, skip it and record the error.
6. One unreadable file must never crash the entire agent.

Use this implementation:

from pathlib import Path

TEXT_EXTENSIONS = {
    ".py", ".txt", ".md", ".json",
    ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".html",
    ".css", ".js", ".ts",
    ".tsx", ".jsx", ".sql"
}

def read_text_safe(file_path: str) -> str:
    path = Path(file_path)

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        pass

    for encoding in ("cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    return path.read_bytes().decode(
        "utf-8",
        errors="replace"
    )

def read_project_file(file_path: str) -> str:
    path = Path(file_path)

    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return ""

    return read_text_safe(str(path))
"""
    is_strong = (complexity != "SIMPLE")
    raw_response = invoke_llm(prompt, is_strong=is_strong)
    return _clean_code_response(raw_response)


# ============================================================
# VALIDATION & REPAIR
# ============================================================

def validate_syntax(code: str) -> Tuple[bool, str]:
    """Validate Python syntax via AST parsing."""
    try:
        ast.parse(code)
        return True, "Syntax valid."
    except SyntaxError as e:
        return False, f"Syntax error: {e.msg} at line {e.lineno}"


def validate_imports(code: str) -> Tuple[bool, str]:
    """Ensure all imported packages belong to the approved whitelist and no deprecated packages exist."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, str(e)

    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_pkg = alias.name.split(".")[0]
                if base_pkg == "fitz":
                    errors.append("Forbidden import: 'import fitz'. Use 'import pymupdf' instead.")
                elif alias.name.startswith("langchain.schema"):
                    errors.append("Deprecated import: 'langchain.schema' does not exist. Use 'langchain_core.messages' or invoke directly with strings.")
                elif base_pkg not in APPROVED_IMPORTS:
                    errors.append(f"Unapproved import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_pkg = node.module.split(".")[0]
                if base_pkg == "fitz":
                    errors.append("Forbidden import: 'from fitz ...'. Use 'import pymupdf' instead.")
                elif node.module.startswith("langchain.schema"):
                    errors.append("Deprecated import: 'from langchain.schema ...' does not exist. Use 'from langchain_core.messages import ...' or invoke directly with strings.")
                elif base_pkg not in APPROVED_IMPORTS:
                    errors.append(f"Unapproved module import: {node.module}")

    if errors:
        return False, "\n".join(errors)
    return True, "Imports valid."


def validate_complexity(code: str, agent_spec: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that SIMPLE agents do not include heavy or unnecessary frameworks."""
    complexity = agent_spec.get("complexity", "SIMPLE")
    errors = []

    if complexity == "SIMPLE":
        forbidden = [
            "StateGraph", "FAISS", "faiss", "SentenceTransformer",
            "RecursiveCharacterTextSplitter", "pytesseract", "pymupdf"
        ]
        for item in forbidden:
            if item in code:
                errors.append(f"SIMPLE agent contains unnecessary complex component: {item}")

    if errors:
        return False, "\n".join(errors)
    return True, "Complexity is appropriate."


def validate_tools(code: str, tools: List[str]) -> Tuple[bool, str]:
    """Validate that all selected tools have actual functional implementations in code."""
    errors = []
    tool_markers = {
        "pdf_loader": ["pymupdf.open", "pymupdf"],
        "pdf_text_extractor": ["get_text"],
        "ocr": ["image_to_string", "pytesseract"],
        "document_chunker": ["RecursiveCharacterTextSplitter", "split_text"],
        "embeddings": ["SentenceTransformer", "embeddings"],
        "vector_store": ["IndexFlatL2", "faiss"],
        "file_reader": ["read_text", "open("],
        "file_writer": ["write_text", "open("],
        "python_executor": ["subprocess.run", "subprocess.Popen", "exec("],
        "web_search": ["requests", "httpx", "urllib", "duckduckgo", "search"],
        "llm": ["ChatGroq", "invoke", "model"]
    }

    for tool in tools:
        if tool in tool_markers:
            markers = tool_markers[tool]
            if not any(marker in code for marker in markers):
                errors.append(
                    f"Tool '{tool}' selected but corresponding implementation ({'/'.join(markers)}) was not found in code."
                )

    if errors:
        return False, "\n".join(errors)
    return True, "Tools implemented."


def validate_code(code: str, agent_spec: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Perform complete multi-stage validation on generated agent code."""
    errors = []

    syntax_ok, syntax_msg = validate_syntax(code)
    if not syntax_ok:
        errors.append(syntax_msg)
        return False, errors

    try:
        tree = ast.parse(code)
        func_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if "agent" not in func_names and "run_agent" not in func_names:
            errors.append("Missing required entry point: module must define 'def agent(...)' or 'def run_agent(...)'.")
    except Exception as e:
        errors.append(f"AST entry-point inspection failed: {e}")

    imp_ok, imp_msg = validate_imports(code)
    if not imp_ok:
        errors.append(imp_msg)

    comp_ok, comp_msg = validate_complexity(code, agent_spec)
    if not comp_ok:
        errors.append(comp_msg)

    tools = agent_spec.get("tools", [])
    tools_ok, tools_msg = validate_tools(code, tools)
    if not tools_ok:
        errors.append(tools_msg)

    return (len(errors) == 0), errors


def repair_code(code: str, errors: List[str], agent_spec: Dict[str, Any]) -> str:
    """Repair invalid generated agent code using LLM."""
    prompt = f"""You are an expert Python AI Agent Repair Specialist.

The following Python agent code failed validation:

AGENT SPECIFICATION:
{json.dumps(agent_spec, indent=2)}

ORIGINAL GENERATED CODE:
```python
{code}
```

DETECTED VALIDATION ERRORS:
{chr(10).join(f"- {err}" for err in errors)}

TASK:
Fix ALL listed validation errors and return the COMPLETE, corrected Python code.
1. The code must be syntactically valid Python.
2. Must define an entry point function named `agent(...)` or `run_agent(...)`.
3. If tools are selected, include real implementations for them.
4. For PDF processing, use `import pymupdf` and `doc = pymupdf.open(pdf_path)` / `page.get_text()`. Never `import fitz`.
5. Never use `from langchain.schema import ...`. Use `from langchain_core.messages import HumanMessage, SystemMessage` or pass prompt strings directly: `model.invoke(prompt)`.
6. Return ONLY the complete corrected Python code. No explanations, no markdown around the code.
"""
    response = invoke_llm(prompt, is_strong=True)
    return _clean_code_response(response)




def build_agent(user_prompt: str, callback: Optional[Any] = None) -> Dict[str, Any]:
    """
    End-to-end agent builder pipeline with live model status reporting:
    Requirements -> Tools -> Architecture -> Spec -> Code -> Validate & Repair Loop
    """
    print("\n" + "=" * 70)
    print("USER PROMPT")
    print("=" * 70)
    print(user_prompt)

    # 1. Requirement Analysis
    if callback:
        callback("🧠 [Groq • openai/gpt-oss-120b] Analyzing requirements...", 0)
    requirements = analyze_requirements(user_prompt)
    print("\nRequirement Analysis       ✅")

    complexity = requirements.get("complexity", "SIMPLE")
    agent_type = requirements.get("agent_type", "custom")
    print(f"Complexity                 → {complexity}")
    print(f"Agent Type                 → {agent_type}")

    # 2. Tool Selection
    if callback:
        callback("🔧 [Groq • openai/gpt-oss-120b] Selecting required tools...", 1)
    tools = select_tools(requirements)
    print(f"Selected Tools             → {tools}")

    # 3. Architecture Generation
    if callback:
        callback("🏗️ [Groq • openai/gpt-oss-120b] Generating architecture...", 2)
    architecture = generate_architecture(requirements, tools)
    print("Architecture               ✅")

    # 4. Agent Specification
    if callback:
        callback("📋 [Groq • openai/gpt-oss-120b] Assembling agent specification...", 3)
    agent_spec = create_agent_spec(
        user_prompt=user_prompt,
        requirements=requirements,
        complexity=complexity,
        tools=tools,
        architecture=architecture,
        agent_type=agent_type
    )
    print("Agent Specification        ✅")

    # 5. Code Generation
    if callback:
        callback("💻 [Groq • openai/gpt-oss-120b] Synthesizing agent code...", 4)
    code = generate_code(agent_spec)
    print("Code Generation            ✅")

    # 6. Validation & Repair Loop
    if callback:
        callback("🔍 Validating generated agent code...", 5)
    for attempt in range(3):
        print(f"\nValidation Attempt {attempt + 1}/3")
        is_valid, validation_errors = validate_code(code, agent_spec)

        if is_valid:
            print("🎉 AGENT GENERATED SUCCESSFULLY")
            if callback:
                callback("✅ Agent validation passed successfully!", 6)
            return {
                "agent_spec": agent_spec,
                "agent_type": agent_type,
                "code": code,
                "valid": True,
                "attempts": attempt + 1,
                "errors": []
            }

        print(f"❌ Validation failed on attempt {attempt + 1}:")
        for err in validation_errors:
            print(f"   - {err}")

        if attempt < 2:
            print("🔧 Repairing generated code...")
            if callback:
                callback(f"🔧 [Groq • openai/gpt-oss-120b] Repairing code (Attempt {attempt + 1}/3)...", 5)
            code = repair_code(code, validation_errors, agent_spec)

    return {
        "agent_spec": agent_spec,
        "agent_type": agent_type,
        "code": code,
        "valid": False,
        "attempts": 3,
        "errors": validation_errors
    }


# ============================================================
# FASTAPI WRAPPER & RUNTIME MANAGEMENT
# ============================================================

def generate_agent_id(agent_type: str) -> str:
    """Generate unique agent identifier."""
    short_id = uuid.uuid4().hex[:8]
    clean_type = re.sub(r"[^a-zA-Z0-9_]", "", str(agent_type).lower())
    return f"{clean_type}_{short_id}"



def _get_agent_input_fields(agent_file: str) -> List[str]:
    """Read the generated agent and find its real input parameters."""
    try:
        source = Path(agent_file).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name not in ("agent", "run_agent"):
                    continue

                fields = []
                for arg in node.args.args:
                    if arg.arg not in {
                        "self", "prompt", "user_input", "query", "text"
                    }:
                        fields.append(arg.arg)

                return fields
    except Exception as exc:
        print(f"Input inspection failed: {exc}")

    return []


def _allowed_api_fields(agent_type: str, detected_fields: List[str]) -> List[str]:
    """
    Decide which generated function parameters should be exposed in Swagger.

    This prevents accidental fields such as context_file/file_path from
    appearing on generic research agents.
    """
    agent_type = (agent_type or "custom").lower()

    if agent_type == "research":
        # Generic research API: prompt only unless an explicitly named
        # research input is present.
        blocked = {
            "pdf_path",
            "file_path",
            "context_file",
            "context_path",
            "document_path",
            "document_file",
            "document",
            "pdf",
            "file",
        }
        return [
            field for field in detected_fields
            if field not in blocked
        ]

    if agent_type == "pdf":
        return [
            field for field in detected_fields
            if field not in {"file_path", "context_file", "document_path"}
        ]

    if agent_type == "coding":
        return [
            field for field in detected_fields
            if field not in {"pdf_path", "file_path", "context_file"}
        ]

    return detected_fields


def find_free_port(start_port: int = None) -> int:
    """Find the first available TCP port."""
    if start_port is None:
        start_port = BASE_AGENT_PORT

    reserved = {
        int(info["port"])
        for info in AGENT_REGISTRY.values()
        if info.get("port") is not None
    }

    port = max(start_port, BASE_AGENT_PORT)

    while port <= 65535:
        if port in reserved:
            port += 1
            continue

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1

    raise RuntimeError("No free TCP port is available.")


def is_server_running(port: int) -> bool:
    """Check if a server is actively listening on localhost port."""
    if port is None:
        return False
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/health", timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", int(port))) == 0


def start_agent_server(agent_id: str, port: int = None) -> int:
    """Start an agent API server process if not already running."""
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent: {agent_id}")

    info = AGENT_REGISTRY[agent_id]
    if port is None:
        port = info.get("port", BASE_AGENT_PORT)
    port = int(port)

    if is_server_running(port):
        info["server_running"] = True
        return port

    api_file = Path(info.get("api_file", f"{agent_id}_api.py")).resolve()
    if not api_file.exists():
        raise RuntimeError(f"API wrapper does not exist: {api_file}")

    log_file_path = Path(f"{agent_id}_server.log").resolve()
    log_file = open(log_file_path, "a", encoding="utf-8")

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(api_file.parent)

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "uvicorn",
            f"{api_file.stem}:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(api_file.parent),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=creationflags
    )

    info["pid"] = process.pid
    info["port"] = port
    info["log_file"] = str(log_file_path)

    for _ in range(60):
        time.sleep(0.5)
        if is_server_running(port):
            info["server_running"] = True
            log_file.close()
            return port
        if process.poll() is not None:
            break

    log_file.close()
    log_content = log_file_path.read_text(encoding="utf-8", errors="replace") if log_file_path.exists() else "No log available."
    raise RuntimeError(
        f"Agent API failed to start on port {port}.\n"
        f"Agent File: {info.get('agent_file')}\n"
        f"API File: {api_file}\n"
        f"Log File: {log_file_path}\n"
        f"Server Output:\n{log_content}"
    )


def register_agent(
    agent_type: str,
    generated_code: str,
    input_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Register agent, write code files, find free port, start Uvicorn process,
    capture log file, and verify readiness.
    """
    agent_type = str(agent_type or "custom").lower().strip()
    allowed_types = {"simple", "coding", "pdf", "research", "custom"}
    if agent_type not in allowed_types:
        agent_type = "custom"

    if not generated_code or not generated_code.strip():
        raise ValueError("Generated agent code is empty.")

    try:
        ast.parse(generated_code)
    except SyntaxError as exc:
        raise RuntimeError(f"Generated agent has a syntax error: {exc}") from exc

    agent_id = generate_agent_id(agent_type)
    port = find_free_port(BASE_AGENT_PORT)

    agent_file = Path(f"{agent_id}.py")
    agent_file.write_text(generated_code, encoding="utf-8")

    # Generate a unique API key for this agent.
    api_key = generate_api_key()

    api_file = create_api_wrapper(
        agent_id,
        str(agent_file.resolve()),
        agent_type=agent_type,
        api_key=api_key
    )

    detected_input_fields = _allowed_api_fields(
        agent_type,
        _get_agent_input_fields(str(agent_file.resolve()))
    )

    if input_fields:
        detected_input_fields = list(dict.fromkeys(
            [str(x) for x in input_fields if str(x).strip()]
            + detected_input_fields
        ))

    log_file_path = Path(f"{agent_id}_server.log")

    endpoint = f"/agents/{agent_id}/run"
    registration = {
        "agent_id": agent_id,
        "type": agent_type,
        "agent_file": str(agent_file.resolve()),
        "api_file": str(Path(api_file).resolve()),
        "log_file": str(log_file_path.resolve()),
        "port": port,
        "pid": None,
        "server_running": False,
        "endpoint": endpoint,
        "url": f"http://127.0.0.1:{port}{endpoint}",
        "health_url": f"http://127.0.0.1:{port}/health",
        "docs_url": f"http://127.0.0.1:{port}/docs",
        "api_key": api_key,
        "public_base_url": get_public_api_base_url(),
        "public_url": f"{get_public_api_base_url()}{endpoint}",
        "public_docs_url": f"{get_public_api_base_url()}/docs",
        "input_fields": detected_input_fields
    }

    AGENT_REGISTRY[agent_id] = registration

    # Start Uvicorn process and register
    start_agent_server(agent_id, port)

    print("\n" + "=" * 60)
    print("AGENT REGISTERED & RUNNING")
    print("=" * 60)
    print("Agent ID :", agent_id)
    print("Port     :", port)
    print("PID      :", registration.get("pid"))
    print("Endpoint :", registration["url"])
    print("Docs     :", registration["docs_url"])
    print("Public API:", registration["public_url"])
    print("API Key  : generated and stored in registration")

    return registration


def stop_agent(agent_id: str) -> bool:
    """Stop a running agent API process and release registry."""
    info = AGENT_REGISTRY.get(agent_id)
    if not info:
        return False

    pid = info.get("pid")
    if pid:
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=5)
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    AGENT_REGISTRY.pop(agent_id, None)
    return True


def stop_all_agents() -> List[str]:
    """Stop all active agents in registry."""
    stopped = []
    for agent_id in list(AGENT_REGISTRY.keys()):
        if stop_agent(agent_id):
            stopped.append(agent_id)
    return stopped


def list_registered_agents() -> List[Dict[str, Any]]:
    """Return list of all registered agents."""
    return list(AGENT_REGISTRY.values())


def list_agents() -> List[Dict[str, Any]]:
    """Alias for list_registered_agents."""
    return list(AGENT_REGISTRY.values())


def save_agent(result: Dict[str, Any]) -> Path:
    """Save generated code to generated_agent.py."""
    path = Path("generated_agent.py")
    path.write_text(result["code"], encoding="utf-8")
    print(f"\nAgent saved to: {path.absolute()}")
    return path

def generate_api_key() -> str:
    """Generate a strong per-agent API key."""
    return "uts_" + secrets.token_urlsafe(32)


def get_public_api_base_url() -> str:
    """
    Public base URL used by external websites.

    Set this in .env after deploying, for example:
        API_PUBLIC_BASE_URL=https://api.yourdomain.com
    """
    return os.getenv(
        "API_PUBLIC_BASE_URL",
        "http://127.0.0.1"
    ).rstrip("/")


def create_api_wrapper(
    agent_id: str,
    agent_file: str,
    agent_type: str = "custom",
    api_key: str = ""
) -> str:
    """
    Create a FastAPI wrapper protected by a per-agent API key.

    External clients must send:
        X-API-Key: uts_xxxxxxxxx
    """
    clean_agent_file = str(agent_file).replace("\\", "/")

    # IMPORTANT:
    # Keep your existing dynamic request-schema generation here.
    # The following version is compatible with the current wrapper design.
    input_fields = _get_agent_input_fields(agent_file)

    # Never expose accidental document inputs for generic research agents.
    if (agent_type or "").lower() == "research":
        blocked = {
            "pdf_path",
            "file_path",
            "context_file",
            "context_path",
            "document_path",
            "document_file",
            "document",
            "pdf",
            "file",
        }
        input_fields = [
            field for field in input_fields
            if field not in blocked
        ]

    request_fields = [
        '    prompt: str = Field(..., description="Main instruction for the agent")'
    ]

    for field in input_fields:
        safe_field = re.sub(r"[^a-zA-Z0-9_]", "_", field)

        if safe_field and not safe_field[0].isdigit():
            request_fields.append(
                f'    {safe_field}: Optional[Any] = Field(None, description="Agent input: {safe_field}")'
            )

    request_schema = "\n".join(request_fields)

    wrapper_code = f"""from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any
import importlib.util
import inspect
import secrets
import hmac

app = FastAPI(
    title="Generated {str(agent_type).capitalize()} Agent API",
    description="Authenticated API for generated agent: {agent_id}"
)

# Allow browser-based clients to call the API.
# In production, set API_CORS_ORIGINS to your real frontend domains.
cors_origins = [
    x.strip()
    for x in "{os.getenv("API_CORS_ORIGINS", "*")}".split(",")
    if x.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPECTED_API_KEY = "{api_key}"

spec = importlib.util.spec_from_file_location(
    "generated_agent_{agent_id}",
    r"{clean_agent_file}"
)

if spec is None or spec.loader is None:
    raise RuntimeError("Could not load generated agent module.")

agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_module)


class AgentRequest(BaseModel):
{request_schema}


@app.get("/")
def root():
    return {{
        "status": "running",
        "agent_id": "{agent_id}",
        "agent_type": "{agent_type}",
        "authentication": "X-API-Key",
        "docs_url": "/docs"
    }}


@app.get("/health")
def health():
    return {{
        "status": "healthy",
        "agent_id": "{agent_id}",
        "agent_type": "{agent_type}"
    }}


@app.post("/agents/{agent_id}/run")
def run_agent(
    request: AgentRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header."
        )

    if not hmac.compare_digest(x_api_key, EXPECTED_API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key."
        )

    try:
        func = (
            getattr(agent_module, "agent", None)
            or getattr(agent_module, "run_agent", None)
        )

        if func is None:
            raise RuntimeError(
                "Generated agent must define agent() or run_agent()."
            )

        data = (
            request.model_dump()
            if hasattr(request, "model_dump")
            else request.dict()
        )

        prompt = data.pop("prompt", None)

        signature = inspect.signature(func)
        parameters = signature.parameters
        kwargs = {{}}

        for name in ("prompt", "user_input", "query", "text"):
            if name in parameters:
                kwargs[name] = prompt
                break

        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in parameters.values()
        )

        for name, value in data.items():
            if value is None:
                continue

            if name in parameters:
                kwargs[name] = value
            elif accepts_kwargs:
                kwargs[name] = value

        result = func(**kwargs)

        return {{
            "agent_id": "{agent_id}",
            "agent_type": "{agent_type}",
            "response": result
        }}

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
"""

    ast.parse(wrapper_code)

    wrapper_path = f"{agent_id}_api.py"
    Path(wrapper_path).write_text(wrapper_code, encoding="utf-8")

    return wrapper_path