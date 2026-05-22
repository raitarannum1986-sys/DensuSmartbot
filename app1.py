# ═══════════════════════════════════════════════
# MULTI-AGENT ARCHITECTURE
# ═══════════════════════════════════════════════

def doc_agent(query, text_entries, user, cid):
    return run_doc_qa(query, text_entries, user, cid)


def data_agent(query, df_entries):
    return run_dataframe_analysis(query, df_entries)


def web_agent(query, user, cid):
    return run_web_agent(query, user, cid)


def orchestrator(query, image_entries, text_entries, df_entries, user, cid):
    q = query.lower()

    # Detect intent
    is_data = any(k in q for k in [
        "chart", "plot", "graph", "average", "mean", "sum",
        "trend", "compare", "distribution", "count"
    ])

    is_doc = is_query_about_docs(query)

    # Routing
    if is_data and df_entries:
        result = data_agent(query, df_entries)
        return result, "📊 Data Agent"

    elif is_doc and text_entries:
        result = doc_agent(query, text_entries, user, cid)
        return result, "📄 Document Agent"

    else:
        result = web_agent(query, user, cid)
        return result, "🌐 Web Agent"


# ═══════════════════════════════════════════════
# CHAT (UPDATED)
# ═══════════════════════════════════════════════

def render_chat():

    if not st.session_state.get("azure_endpoint") or not st.session_state.get("azure_api_key"):
        st.warning("Please configure API credentials in sidebar.")
        return

    messages = st.session_state.get("messages", [])

    for msg in messages:
        role = msg["role"]
        with st.chat_message(role):
            st.markdown(msg["content"])

            if msg.get("chart_key") and msg["chart_key"] in st.session_state.get("charts", {}):
                st.pyplot(st.session_state["charts"][msg["chart_key"]])

    prompt = st.chat_input("Ask anything...")

    if not prompt:
        return

    user = st.session_state["user"]

    # Create conversation if needed
    if not st.session_state.get("current_conv"):
        cid = create_conversation(user["user_id"], generate_title(prompt))
        st.session_state["current_conv"] = cid
    else:
        cid = st.session_state["current_conv"]

    # Save user message
    save_message(cid, "user", prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # ── CLASSIFY DOCUMENT TYPES ──
    image_entries, text_entries, df_entries = classify_doc_types()

    # ── RUN ORCHESTRATOR ──
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            result, agent_used = orchestrator(
                prompt,
                image_entries,
                text_entries,
                df_entries,
                user,
                cid
            )

            # Handle output safely
            if isinstance(result, tuple):
                answer = result[0]
                chart_fig = result[1] if len(result) > 1 else None
            else:
                answer = result
                chart_fig = None

            st.caption(f"🧠 Agent Used: {agent_used}")
            st.markdown(answer)

            chart_key = None
            if chart_fig is not None:
                chart_key = f"chart_{uuid.uuid4().hex[:8]}"
                st.session_state.setdefault("charts", {})[chart_key] = chart_fig
                st.pyplot(chart_fig)

    # Save assistant response
    save_message(cid, "assistant", answer)

    st.session_state["messages"].append({
        "role": "assistant",
        "content": answer,
        "chart_key": chart_key,
        "tool_calls": agent_used
    })