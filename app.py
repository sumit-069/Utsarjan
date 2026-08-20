import streamlit as st
import json
import time
import datetime

from agent import (
    build_agent,
    register_agent,
    is_server_running,
    start_agent_server,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="utsarjan - AI Agent Builder",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* =========================
       GLOBAL
    ========================= */

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes shimmer {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    @keyframes pulseGlow {
        0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.35); }
        50%      { box-shadow: 0 0 0 8px rgba(99, 102, 241, 0); }
    }

    /* =========================
       HERO
    ========================= */

    .hero {
        padding: 40px 34px;
        border-radius: 24px;
        background: linear-gradient(
            120deg,
            rgba(99, 102, 241, 0.20),
            rgba(168, 85, 247, 0.14),
            rgba(236, 72, 153, 0.12)
        );
        background-size: 200% 200%;
        animation: shimmer 10s ease infinite, fadeInUp 0.6s ease;
        border: 1px solid rgba(128, 128, 128, 0.18);
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
    }

    .hero-title {
        font-size: 46px;
        font-weight: 800;
        margin-bottom: 8px;
        letter-spacing: -1.2px;
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-subtitle {
        font-size: 18px;
        color: #9a9a9a;
        max-width: 750px;
        line-height: 1.65;
    }

    .hero-badge {
        display: inline-block;
        padding: 7px 14px;
        border-radius: 20px;
        background: rgba(99, 102, 241, 0.18);
        border: 1px solid rgba(99, 102, 241, 0.35);
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 16px;
        animation: pulseGlow 2.4s ease-in-out infinite;
    }

    /* =========================
       SECTION HEADINGS
    ========================= */

    .section-title {
        font-size: 24px;
        font-weight: 700;
        margin-top: 15px;
        margin-bottom: 8px;
        animation: fadeInUp 0.5s ease;
    }

    .section-subtitle {
        color: #8b8b8b;
        margin-bottom: 18px;
    }

    /* =========================
       CARDS
    ========================= */

    .info-card {
        padding: 22px;
        border-radius: 18px;
        border: 1px solid rgba(128, 128, 128, 0.18);
        background: rgba(128, 128, 128, 0.04);
        min-height: 120px;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        animation: fadeInUp 0.5s ease;
    }

    .info-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 24px rgba(99, 102, 241, 0.15);
        border-color: rgba(99, 102, 241, 0.4);
    }

    .card-label {
        font-size: 12.5px;
        color: #888;
        letter-spacing: 0.6px;
        margin-bottom: 8px;
    }

    .card-value {
        font-size: 26px;
        font-weight: 800;
    }

    /* =========================
       EXAMPLE PROMPT CARDS
    ========================= */

    .example-card {
        padding: 16px 18px;
        border-radius: 14px;
        border: 1px solid rgba(128, 128, 128, 0.16);
        background: rgba(128, 128, 128, 0.035);
        margin-bottom: 10px;
        transition: all 0.18s ease;
    }

    .example-card:hover {
        border-color: rgba(99, 102, 241, 0.45);
        background: rgba(99, 102, 241, 0.07);
        transform: translateX(3px);
    }

    /* =========================
       TOOL BADGES
    ========================= */

    .tool-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
    }

    .tool-badge {
        padding: 8px 14px;
        border-radius: 20px;
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.28);
        font-size: 13px;
        font-weight: 500;
        transition: transform 0.15s ease;
    }

    .tool-badge:hover {
        transform: scale(1.06);
        background: rgba(99, 102, 241, 0.2);
    }

    /* =========================
       API CARD
    ========================= */

    .api-card {
        padding: 26px;
        border-radius: 20px;
        border: 1px solid rgba(34, 197, 94, 0.3);
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.10), rgba(34, 197, 94, 0.03));
        margin-top: 15px;
        animation: fadeInUp 0.5s ease;
    }

    .api-title {
        font-size: 21px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .api-subtitle {
        color: #888;
        margin-bottom: 20px;
    }

    /* =========================
       STEP INDICATOR / PIPELINE
    ========================= */

    .pipeline {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        margin: 20px 0 30px 0;
    }

    .pipeline-step {
        flex: 1;
        text-align: center;
        padding: 14px 5px;
        border-radius: 14px;
        background: rgba(128,128,128,0.06);
        border: 1px solid rgba(128,128,128,0.15);
        font-size: 12px;
        font-weight: 600;
        transition: all 0.25s ease;
    }

    .pipeline-step.active {
        background: rgba(99, 102, 241, 0.18);
        border-color: rgba(99, 102, 241, 0.55);
        transform: scale(1.05);
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
    }

    .pipeline-step.done {
        background: rgba(34, 197, 94, 0.14);
        border-color: rgba(34, 197, 94, 0.4);
    }

    /* =========================
       BUTTON POLISH
    ========================= */

    div.stButton > button[kind="primary"] {
        border-radius: 14px;
        font-weight: 700;
        padding: 0.7rem 1rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        box-shadow: 0 6px 18px rgba(99, 102, 241, 0.25);
    }

    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(99, 102, 241, 0.35);
    }

    div.stButton > button {
        border-radius: 12px;
        transition: transform 0.12s ease;
    }

    div.stButton > button:hover {
        transform: translateX(2px);
    }

    /* =========================
       FOOTER
    ========================= */

    .footer {
        text-align: center;
        color: #777;
        font-size: 13px;
        padding-top: 40px;
    }

    .footer-badge {
        display: inline-block;
        margin: 0 4px;
        padding: 3px 9px;
        border-radius: 12px;
        background: rgba(128,128,128,0.08);
        font-size: 11px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_registered" not in st.session_state:
    st.session_state.last_registered = None

if "history" not in st.session_state:
    st.session_state.history = []

if "example_prompt" not in st.session_state:
    st.session_state.example_prompt = ""


PIPELINE_LABELS = [
    ("🧠", "Requirements"),
    ("🔧", "Tools"),
    ("🏗️", "Architecture"),
    ("📋", "Specification"),
    ("💻", "Code"),
    ("✅", "Validation"),
    ("🌐", "API"),
]


def render_pipeline(active_index=-1, done_index=-1):
    """Renders the 7-step pipeline strip, optionally highlighting progress."""
    html = '<div class="pipeline">'
    for i, (icon, label) in enumerate(PIPELINE_LABELS):
        cls = "pipeline-step"
        if i <= done_index:
            cls += " done"
        elif i == active_index:
            cls += " active"
        html += f'<div class="{cls}">{icon}<br>{label}</div>'
    html += "</div>"
    return html


pipeline_placeholder_slot = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## ⚡ utsarjan")

    st.caption(
        "Autonomous AI Agent Creation & Instant API Engine."
    )

    st.divider()

    st.markdown("### ⚡ Quick Examples")

    examples = [
        ("💬", "Simple Q&A Agent",
         "Create a simple AI agent that answers user questions."),
        ("📄", "PDF Question Answering",
         "Create an AI agent that reads PDF files, answers questions "
         "from them, and provides page-level citations."),
        ("💻", "Coding Agent",
         "Create an AI coding agent that finds and explains errors "
         "in Python code."),
        ("🔎", "Research Agent",
         "Create an AI research agent that analyzes information and "
         "provides structured answers."),
    ]

    for icon, label, prompt in examples:
        if st.button(f"{icon} {label}", use_container_width=True):
            st.session_state.example_prompt = prompt

    st.divider()

    st.markdown("### 🏗️ Pipeline")

    for icon, label in PIPELINE_LABELS:
        st.caption(f"{icon} {label}")

    if st.session_state.history:
        st.divider()
        st.markdown("### 🕘 History")
        for item in reversed(st.session_state.history[-5:]):
            with st.expander(f"{item['icon']} {item['title']}", expanded=False):
                st.caption(item["time"])
                st.code(item["endpoint"], language="text")


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">⚡ utsarjan • Prompt → Agent → API</div>
        <div class="hero-title">utsarjan</div>
        <div class="hero-subtitle">
            Describe the AI agent you want in plain English.
            utsarjan analyzes your requirements, selects the
            required tools, designs the architecture, generates
            the code, validates it, and exposes the agent as a
            live authenticated API — all in one click.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# PIPELINE (idle state)
# ============================================================

pipeline_slot = st.empty()
pipeline_slot.markdown(render_pipeline(), unsafe_allow_html=True)


# ============================================================
# PROMPT SECTION
# ============================================================

st.markdown(
    '<div class="section-title">✨ Describe Your Agent</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'One prompt is enough. The builder handles the rest.'
    '</div>',
    unsafe_allow_html=True
)

user_prompt = st.text_area(
    "Agent description",
    value=st.session_state.example_prompt,
    placeholder=(
        "Example: Create an AI agent that reads PDF files, "
        "answers questions from them, and provides page-level citations."
    ),
    height=150,
    label_visibility="collapsed"
)

char_count = len(user_prompt.strip())
count_col, _ = st.columns([1, 4])
with count_col:
    st.caption(f"{char_count} characters")

create_button = st.button(
    "🚀 Build My Agent",
    type="primary",
    use_container_width=True
)


# ============================================================
# BUILD AGENT
# ============================================================

if create_button:

    if not user_prompt.strip():
        st.warning("⚠️ Please describe the agent you want to create.")
        st.stop()

    st.session_state.example_prompt = ""

    st.divider()

    st.markdown(
        '<div class="section-title">⚙️ Building Your Agent</div>',
        unsafe_allow_html=True
    )

    try:
        with st.status("Starting build pipeline...", expanded=True) as build_status:

            pipeline_slot.markdown(render_pipeline(active_index=0), unsafe_allow_html=True)
            st.write("🧠 Analyzing requirements from your prompt...")
            time.sleep(0.25)

            pipeline_slot.markdown(render_pipeline(active_index=1, done_index=0), unsafe_allow_html=True)
            st.write("🔧 Selecting the tools this agent will need...")
            time.sleep(0.25)

            pipeline_slot.markdown(render_pipeline(active_index=2, done_index=1), unsafe_allow_html=True)
            st.write("🏗️ Designing the agent architecture...")
            time.sleep(0.25)

            pipeline_slot.markdown(render_pipeline(active_index=4, done_index=3), unsafe_allow_html=True)
            st.write("💻 Generating agent code...")

            result = build_agent(user_prompt)

            pipeline_slot.markdown(render_pipeline(active_index=5, done_index=4), unsafe_allow_html=True)
            st.write("🔍 Validating generated agent...")
            time.sleep(0.25)

            if not result.get("valid", False):
                build_status.update(label="Validation failed", state="error")
                st.error("❌ Generated agent failed validation.")
                st.json(result)
                st.stop()

            pipeline_slot.markdown(render_pipeline(active_index=6, done_index=5), unsafe_allow_html=True)
            build_status.update(label="Agent generation completed!", state="complete")

    except Exception as e:
        st.error(f"❌ Agent Builder Error: {e}")
        st.exception(e)
        st.stop()

    st.session_state.last_result = result

    st.balloons()
    st.success("🎉 Your AI agent was generated successfully!")

    spec = result["agent_spec"]

    # ========================================================
    # OVERVIEW CARDS
    # ========================================================

    st.divider()
    st.markdown('<div class="section-title">📊 Agent Overview</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="card-label">COMPLEXITY</div>
                <div class="card-value">{spec["complexity"]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="card-label">TOOLS</div>
                <div class="card-value">{len(spec.get("tools", []))}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="card-label">VALIDATION</div>
                <div class="card-value">✅ PASSED</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # TABS
    # ========================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔧 Tools", "🏗️ Architecture", "💻 Generated Code", "📋 Specification"]
    )

    with tab1:
        st.subheader("Selected Tools")
        tools = spec.get("tools", [])
        if tools:
            badges = "".join(f'<span class="tool-badge">🔹 {tool}</span>' for tool in tools)
            st.markdown(f'<div class="tool-container">{badges}</div>', unsafe_allow_html=True)
        else:
            st.info("This agent does not require external tools.")

    with tab2:
        st.subheader("Generated Architecture")
        st.code(spec["architecture"], language="text")

    with tab3:
        st.subheader("Generated Python Code")
        st.code(result["code"], language="python")
        st.download_button(
            "⬇️ Download Agent Code",
            data=result["code"],
            file_name="generated_agent.py",
            mime="text/x-python",
            use_container_width=True
        )

    with tab4:
        st.subheader("Agent Specification")
        st.json(spec)

    # ========================================================
    # API REGISTRATION
    # ========================================================
    
    st.divider()
    st.markdown(
        '<div class="section-title">🌐 Deployable Agent API</div>',
        unsafe_allow_html=True
    )
    
    
    def detect_agent_type(prompt: str, spec: dict) -> str:
        """Determine the actual purpose/type of the generated agent."""
        agent_type = spec.get("agent_type")
        if agent_type:
            return str(agent_type).lower().strip()
    
        prompt_lower = prompt.lower()
    
        if any(word in prompt_lower for word in [
            "pdf", "document", "documents", "page-level citation",
            "page citation", "pdf files", "read pdf"
        ]):
            return "pdf"
    
        if any(word in prompt_lower for word in [
            "coding agent", "code agent", "coding assistant",
            "debugging agent", "debug python", "debug code",
            "find errors in python", "find errors in code",
            "fix python errors", "fix code errors",
            "programming agent", "analyze python code"
        ]):
            return "coding"
    
        if any(word in prompt_lower for word in [
            "research agent", "research assistant", "web research",
            "research", "analyze information", "structured research"
        ]):
            return "research"
    
        if any(word in prompt_lower for word in [
            "simple ai agent", "simple agent", "answers user questions",
            "answer user questions", "answer questions", "question answering",
            "q&a", "general assistant"
        ]):
            return "simple"
    
        return "custom"
    
    
    # ========================================================
    # REGISTER AGENT + START DEDICATED FASTAPI SERVER
    # ========================================================

    try:

        with st.spinner(
            "Registering agent and starting FastAPI server..."
        ):

            agent_type = detect_agent_type(
                user_prompt,
                spec
            )

            registered = register_agent(
                agent_type,
                result["code"]
            )

        if not registered:
            raise RuntimeError(
                "register_agent() returned no registration data."
            )

        st.session_state.last_registered = registered

        agent_id = registered.get(
            "agent_id",
            "unknown"
        )

        # register_agent() must allocate a unique port.
        port = registered.get("port")

        if port is None:
            raise RuntimeError(
                "register_agent() did not return a port. "
                "Replace your agent.py with the latest "
                "per-agent-port version."
            )

        port = int(port)

        endpoint = registered.get(
            "endpoint",
            f"/agents/{agent_id}/run"
        )

        local_api_url = f"http://127.0.0.1:{port}{endpoint}"
        local_docs_url = f"http://127.0.0.1:{port}/docs"

        # Public URL is used after deployment; locally it falls back to localhost.
        api_url = registered.get("public_url") or local_api_url
        docs_url = registered.get("public_docs_url") or local_docs_url

        # Keep local URLs available for development.
        registered["local_url"] = local_api_url
        registered["local_docs_url"] = local_docs_url

        health_url = registered.get(
            "health_url",
            f"http://127.0.0.1:{port}/health"
        )

        st.session_state.history.append({
            "icon": "🤖",
            "title": agent_id,
            "endpoint": endpoint,
            "time": datetime.datetime.now().strftime(
                "%b %d, %H:%M"
            )
        })

        st.success(
            f"🚀 {agent_type.title()} agent registered successfully."
        )

        # ----------------------------------------------------
        # AGENT INFORMATION
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:
            st.caption("AGENT TYPE")
            st.code(agent_type)

        with col2:
            st.caption("AGENT ID")
            st.code(agent_id)

        with col3:
            st.caption("PORT")
            st.code(str(port))

        # ----------------------------------------------------
        # API ENDPOINT
        # ----------------------------------------------------

        st.subheader("🔗 API Endpoint")
        st.code(api_url)

        # ----------------------------------------------------
        # API KEY
        # ----------------------------------------------------

        api_key = registered.get("api_key")

        st.subheader("🔐 Agent API Key")
        if api_key:
            st.warning(
                "Keep this key private. Anyone who has it can call this agent."
            )
            st.code(api_key, language="text")

            st.download_button(
                "⬇️ Download API Credentials",
                data=(
                    f"Agent ID: {agent_id}\n"
                    f"API Key: {api_key}\n"
                    f"API URL: {api_url}\n"
                    f"Swagger: {docs_url}\n"
                ),
                file_name=f"{agent_id}_credentials.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info(
                "No API key was returned. Make sure the latest agent.py is installed."
            )

        # ----------------------------------------------------
        # SWAGGER
        # ----------------------------------------------------

        st.subheader("📖 FastAPI Swagger Documentation")

        st.link_button(
            "🚀 Open Swagger UI",
            docs_url,
            use_container_width=True
        )

        st.code(docs_url)

        # ----------------------------------------------------
        # API WRAPPER
        # ----------------------------------------------------

        st.subheader("📦 Generated API Wrapper")

        api_file = registered.get(
            "api_file",
            ""
        )

        st.code(
            api_file or "API wrapper file not returned."
        )

        # ----------------------------------------------------
        # INTEGRATION EXAMPLE
        # ----------------------------------------------------

        if api_key:
            st.subheader("🔌 Website Integration")

            curl_example = (
                f'curl -X POST "{api_url}" '
                f'-H "Content-Type: application/json" '
                f'-H "X-API-Key: {api_key}" '
                f'-d \'{{"prompt":"Hello agent"}}\''
            )

            st.code(curl_example, language="bash")

            st.caption(
                "For a production website, keep the API key on your backend "
                "and do not expose it in browser JavaScript."
            )

        # ----------------------------------------------------
        # SERVER STATUS
        # ----------------------------------------------------

        st.subheader("▶️ Agent API Server")

        server_live = is_server_running(
            port
        )

        if not server_live:

            try:

                server_live = start_agent_server(
                    agent_id,
                    port
                )

            except Exception as server_error:

                server_live = False

                st.error(
                    "❌ FastAPI server failed to start."
                )

                st.exception(
                    server_error
                )

        if server_live:

            st.success(
                f"🟢 FastAPI Server is LIVE on port {port}"
            )

            st.link_button(
                "📖 Open /docs",
                docs_url,
                use_container_width=True
            )

            st.caption(
                f"Health endpoint: {health_url}"
            )

        else:

            st.warning(
                f"🟡 Server is not responding on port {port}."
            )

        # ----------------------------------------------------
        # TEST
        # ----------------------------------------------------

        st.subheader("🧪 Test Your Agent")

        st.markdown(
            f"""
            **API:** `{api_url}`

            **Swagger:** `{docs_url}`

            **Health:** `{health_url}`

            1. Open Swagger UI.
            2. Find `POST /agents/{agent_id}/run`.
            3. Click **Try it out**.
            4. Enter your request body.
            5. Send the API key using the `X-API-Key` header.
            6. Click **Execute**.
            """
        )

        if agent_type == "coding":

            st.success(
                "💻 Coding Agent detected — specialized "
                "for analyzing and fixing code."
            )

        elif agent_type == "pdf":

            st.success(
                "📄 PDF Agent detected — specialized "
                "for document question answering."
            )

        elif agent_type == "research":

            st.success(
                "🔎 Research Agent detected."
            )

        elif agent_type == "simple":

            st.success(
                "💬 Simple Q&A Agent detected."
            )

        else:

            st.info(
                "🤖 Custom Agent detected."
            )

    except Exception as e:

        st.error(
            f"❌ API registration failed: {e}"
        )

        st.exception(e)


# ============================================================
# PREVIOUS AGENT
# ============================================================

elif st.session_state.last_result:

    st.divider()
    st.subheader("📌 Last Generated Agent")

    previous = st.session_state.last_registered

    if previous:
        col1, col2 = st.columns(2)

        with col1:
            st.caption("Agent ID")
            st.code(previous["agent_id"])

        with col2:
            st.caption("API Endpoint")
            st.code(previous["endpoint"])

    if st.button("🔁 Build Another Agent", use_container_width=True):
        st.session_state.last_result = None
        st.session_state.last_registered = None
        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        ⚡ <strong>utsarjan</strong> — Autonomous AI Agent & API Engine
        <br>
        <span class="footer-badge">Prompt</span> →
        <span class="footer-badge">Requirements</span> →
        <span class="footer-badge">Architecture</span> →
        <span class="footer-badge">Code</span> →
        <span class="footer-badge">FastAPI</span>
    </div>
    """,
    unsafe_allow_html=True
)