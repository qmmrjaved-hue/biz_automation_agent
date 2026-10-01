"""
app.py — Business Automation Agent web dashboard (Streamlit).

A chat page talking directly to the unified Agent controller, plus one
dedicated page per skill for structured, form-based interaction. Every
static UI string is translated via i18n.t(); a sidebar toggle switches the
whole dashboard between Italian and English.

Entry point: streamlit run app.py
"""

import os
import tempfile
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st

import memory
from config import settings
from controller import Agent
from i18n import t
from skills import approval_workflow, document_processing, email_automation, etl, reporting, voice_to_db

st.set_page_config(
    page_title="Business Automation Agent",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS — enterprise/corporate look ──────────────────────────────────
st.markdown(
    """
<style>
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  header {visibility: hidden;}
  .block-container {padding-top: 1.5rem; max-width: 1200px;}

  html, body, [class*="css"] {
    font-family: "Segoe UI", Arial, sans-serif;
  }

  .stButton > button {
    background-color: #0F172A;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.5rem 1.4rem;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  .stButton > button:hover { background-color: #1E293B; }

  .baa-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 100%);
    padding: 30px 36px;
    border-radius: 10px;
    margin-bottom: 22px;
  }
  .baa-header h1 {
    color: white; font-size: 34px; font-weight: 800; margin: 0 0 4px 0; letter-spacing: -0.5px;
  }
  .baa-header p { color: #93C5FD; font-size: 14px; margin: 0; }

  .baa-card {
    background: white; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 14px;
  }
  .baa-section {
    font-size: 14px; font-weight: 700; color: #0F172A; text-transform: uppercase;
    letter-spacing: 0.4px; border-bottom: 2px solid #1E3A5F; padding-bottom: 6px; margin-bottom: 12px;
  }

  .baa-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
  }
  .badge-pending  { background: #FEF3C7; color: #92400E; }
  .badge-approved { background: #D1FAE5; color: #065F46; }
  .badge-rejected { background: #FEE2E2; color: #991B1B; }

  .baa-success { background: #F0FFF4; border: 1px solid #48BB78; border-radius: 6px; padding: 12px 16px; color: #1C4532; margin-bottom: 10px; }
  .baa-error   { background: #FFF5F5; border: 1px solid #FC8181; border-radius: 6px; padding: 12px 16px; color: #742A2A; margin-bottom: 10px; }
  .baa-warn    { background: #FFFBEB; border: 1px solid #F6C453; border-radius: 6px; padding: 12px 16px; color: #7A5B0A; margin-bottom: 10px; }

  .chat-bubble-user  { background: #1E3A5F; color: white; padding: 10px 14px; border-radius: 10px 10px 2px 10px; margin: 6px 0; max-width: 80%; margin-left: auto; }
  .chat-bubble-agent { background: #F1F5F9; color: #0F172A; padding: 10px 14px; border-radius: 10px 10px 10px 2px; margin: 6px 0; max-width: 80%; }

  .baa-footer { text-align: center; color: #94A3B8; font-size: 11px; margin-top: 28px; padding-top: 10px; border-top: 1px solid #E2E8F0; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "page" not in st.session_state:
    st.session_state.page = "chat"
if "lang" not in st.session_state:
    st.session_state.lang = "it"

LANG = st.session_state.lang


def _header():
    st.markdown(
        f"""
        <div class="baa-header">
          <h1>Business Automation Agent</h1>
          <p>{t("header_tagline", LANG)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _footer():
    st.markdown(f'<div class="baa-footer">{t("footer", LANG)}</div>', unsafe_allow_html=True)


def _gemini_warning():
    if not settings.gemini_api_key:
        st.markdown(f'<div class="baa-warn">{t("gemini_warning", LANG)}</div>', unsafe_allow_html=True)
        return True
    return False


def _dry_run_note():
    if settings.dry_run:
        st.caption(t("dry_run_note", LANG))


def _error(msg) -> None:
    st.markdown(f'<div class="baa-error">{t("error_prefix", LANG)}: {msg}</div>', unsafe_allow_html=True)


# ── Sidebar navigation ───────────────────────────────────────────────────────
_PAGE_KEYS = ["chat", "documents", "inbox", "approvals", "ask_db", "etl", "reports"]
_NAV_LABEL_KEYS = {
    "chat": "nav_chat", "documents": "nav_documents", "inbox": "nav_inbox",
    "approvals": "nav_approvals", "ask_db": "nav_ask_db", "etl": "nav_etl", "reports": "nav_reports",
}

with st.sidebar:
    st.markdown("**Business Automation Agent**")

    lang_choice = st.radio(
        t("language_label", LANG), ["it", "en"],
        index=["it", "en"].index(st.session_state.lang),
        format_func=lambda code: "Italiano" if code == "it" else "English",
        horizontal=True,
        label_visibility="visible",
    )
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()

    st.caption(t("session_label", LANG, id=st.session_state.session_id))
    st.divider()
    st.session_state.page = st.radio(
        "nav", _PAGE_KEYS,
        index=_PAGE_KEYS.index(st.session_state.page),
        format_func=lambda k: t(_NAV_LABEL_KEYS[k], LANG),
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(t("sink_dry_run", LANG, sink=settings.default_sink, dry_run=settings.dry_run))
    st.caption(t("gemini_key_label", LANG) + " " +
               (t("configured", LANG) if settings.gemini_api_key else t("missing", LANG)))


# ── Chat page ────────────────────────────────────────────────────────────────

def chat_page():
    _header()
    st.markdown(f'<div class="baa-section">{t("section_chat", LANG)}</div>', unsafe_allow_html=True)
    _gemini_warning()

    for turn in st.session_state.chat_history:
        cls = "chat-bubble-user" if turn["role"] == "user" else "chat-bubble-agent"
        st.markdown(f'<div class="{cls}">{turn["content"]}</div>', unsafe_allow_html=True)

    user_input = st.chat_input(t("chat_input_placeholder", LANG))
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        try:
            agent = Agent(session_id=st.session_state.session_id, language=LANG)
            with st.spinner(t("chat_spinner", LANG)):
                reply = agent.handle(user_input)
        except Exception as e:
            reply = f"{t('error_prefix', LANG)}: {e}"
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    _footer()


# ── Documents page ───────────────────────────────────────────────────────────

def documents_page():
    _header()
    st.markdown(f'<div class="baa-section">{t("section_documents", LANG)}</div>', unsafe_allow_html=True)
    _gemini_warning()

    uploaded = st.file_uploader(t("upload_document_label", LANG), type=["pdf", "txt"])
    sink = st.selectbox(t("save_to_label", LANG), ["excel", "sheets", "postgres"], index=0)

    if uploaded is not None and st.button(t("process_document_btn", LANG)):
        ext = os.path.splitext(uploaded.name)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(uploaded.read())
        tmp.close()

        try:
            with st.spinner(t("extracting_spinner", LANG)):
                doc = document_processing.process_document(tmp.name, sink=sink, language=LANG)
            st.markdown(f'<div class="baa-success">{t("document_processed", LANG, type=doc.doc_type)}</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="baa-card"><div class="baa-section">{t("extracted_fields", LANG)}</div>',
                        unsafe_allow_html=True)
            st.table(pd.DataFrame(list(doc.fields.items()), columns=[t("field_col", LANG), t("value_col", LANG)]))
            st.markdown("</div>", unsafe_allow_html=True)
            st.write(t("summary_label", LANG), doc.summary)
            st.caption(f'{t("saved_to_label", LANG)} {doc.saved_to}')
        except Exception as e:
            _error(e)
        finally:
            os.unlink(tmp.name)

    st.divider()
    st.markdown(f'<div class="baa-section">{t("recent_documents", LANG)}</div>', unsafe_allow_html=True)
    docs = memory.list_extracted_documents()[:10]
    if docs:
        st.dataframe(
            pd.DataFrame([{"file": d["source_file"], "type": d["doc_type"],
                            "summary": d["summary"], "when": d["created_at"]} for d in docs]),
            hide_index=True, use_container_width=True,
        )
    else:
        st.caption(t("no_documents_yet", LANG))

    _footer()


# ── Inbox page ────────────────────────────────────────────────────────────────

def inbox_page():
    _header()
    st.markdown(f'<div class="baa-section">{t("section_inbox", LANG)}</div>', unsafe_allow_html=True)
    _gemini_warning()
    _dry_run_note()

    if not (settings.imap_host and settings.imap_user and settings.imap_password):
        st.markdown(f'<div class="baa-warn">{t("imap_not_configured", LANG)}</div>', unsafe_allow_html=True)
    else:
        limit = st.number_input(t("max_emails_label", LANG), min_value=1, max_value=50, value=10)
        if st.button(t("check_inbox_btn", LANG)):
            try:
                with st.spinner(t("reading_spinner", LANG)):
                    results = email_automation.handle_inbox(limit=int(limit), language=LANG)
                if results:
                    st.dataframe(
                        pd.DataFrame([r.__dict__ for r in results]),
                        hide_index=True, use_container_width=True,
                    )
                else:
                    st.info(t("no_unread_emails", LANG))
            except Exception as e:
                _error(e)

    st.divider()
    st.markdown(f'<div class="baa-section">{t("quick_draft_section", LANG)}</div>', unsafe_allow_html=True)
    subject = st.text_input(t("subject_label", LANG))
    body = st.text_area(t("message_text_label", LANG))
    if st.button(t("generate_draft_btn", LANG)) and body:
        try:
            with st.spinner(t("generating_spinner", LANG)):
                reply = email_automation.draft_reply(subject=subject, body=body, language=LANG)
            st.markdown('<div class="baa-card">', unsafe_allow_html=True)
            st.write(reply)
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            _error(e)

    _footer()


# ── Approvals page ────────────────────────────────────────────────────────────

def _status_badge(status: str) -> str:
    cls = {"pending": "badge-pending", "approved": "badge-approved", "rejected": "badge-rejected"}.get(status, "")
    return f'<span class="baa-badge {cls}">{status}</span>'


def approvals_page():
    _header()
    st.markdown(f'<div class="baa-section">{t("section_approvals", LANG)}</div>', unsafe_allow_html=True)
    _dry_run_note()

    with st.form("new_approval"):
        st.write(t("new_request_label", LANG))
        title = st.text_input(t("title_label", LANG))
        requester = st.text_input(t("requester_label", LANG))
        steps = st.text_input(t("steps_label", LANG), value="manager,finance")
        submitted = st.form_submit_button(t("create_request_btn", LANG))
        if submitted and title and requester:
            step_list = [s.strip() for s in steps.split(",") if s.strip()]
            approval = approval_workflow.create_request(title, requester, step_list)
            st.markdown(f'<div class="baa-success">{t("request_created", LANG, id=approval.request_id)}</div>',
                        unsafe_allow_html=True)

    st.divider()
    st.markdown(f'<div class="baa-section">{t("pending_requests", LANG)}</div>', unsafe_allow_html=True)
    pending = approval_workflow.list_pending()
    if not pending:
        st.caption(t("no_pending_requests", LANG))
    for approval in pending:
        current_owner = approval.steps[approval.current_step_index]
        with st.container():
            card_body = t("approval_card", LANG, id=approval.request_id, requester=approval.requester,
                          owner=current_owner, i=approval.current_step_index + 1, n=len(approval.steps))
            st.markdown(
                f'<div class="baa-card"><strong>{approval.title}</strong> {_status_badge(approval.status)}<br>'
                f'{card_body}</div>',
                unsafe_allow_html=True,
            )
            col_actor, col_approve, col_reject = st.columns([2, 1, 1])
            actor = col_actor.text_input("actor", key=f"actor_{approval.request_id}", label_visibility="collapsed",
                                          placeholder=t("actor_placeholder", LANG))
            if col_approve.button(t("approve_btn", LANG), key=f"approve_{approval.request_id}"):
                approval_workflow.decide(approval.request_id, "approve", actor or current_owner)
                st.rerun()
            if col_reject.button(t("reject_btn", LANG), key=f"reject_{approval.request_id}"):
                approval_workflow.decide(approval.request_id, "reject", actor or current_owner)
                st.rerun()

    st.divider()
    st.markdown(f'<div class="baa-section">{t("all_requests", LANG)}</div>', unsafe_allow_html=True)
    all_requests = memory.list_approvals()
    if all_requests:
        st.dataframe(
            pd.DataFrame([{
                t("id_col", LANG): a["request_id"], t("title_col", LANG): a["title"],
                t("status_col", LANG): a["status"], t("updated_col", LANG): a["updated_at"],
            } for a in all_requests]),
            hide_index=True, use_container_width=True,
        )

    _footer()


# ── Ask Database page ─────────────────────────────────────────────────────────

def ask_database_page():
    _header()
    st.markdown(f'<div class="baa-section">{t("section_ask_db", LANG)}</div>', unsafe_allow_html=True)
    _gemini_warning()

    db_target = st.text_input(t("db_target_label", LANG), value=settings.warehouse_db_path)

    tab_text, tab_audio = st.tabs([t("tab_text_question", LANG), t("tab_voice_question", LANG)])

    question = None
    audio_path = None

    with tab_text:
        question = st.text_input(t("text_question_label", LANG))

    with tab_audio:
        audio_file = st.file_uploader(t("upload_audio_label", LANG), type=["wav", "mp3"])
        if audio_file is not None:
            ext = os.path.splitext(audio_file.name)[1]
            tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp_audio.write(audio_file.read())
            tmp_audio.close()
            audio_path = tmp_audio.name
            st.caption(t("audio_ready", LANG))

    if st.button(t("run_query_btn", LANG)):
        try:
            with st.spinner(t("processing_spinner", LANG)):
                result = voice_to_db.ask(db_target=db_target, text=question or None, audio_path=audio_path)
        except Exception as e:
            result = {"error": str(e), "sql": None, "results": None, "stage": "unknown"}
        finally:
            if audio_path:
                os.unlink(audio_path)

        if result.get("transcript"):
            st.caption(t("transcript_label", LANG, text=result["transcript"]))
        if result.get("error"):
            st.markdown(
                f'<div class="baa-error">{t("error_with_stage", LANG, stage=result.get("stage"), error=result["error"])}</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="baa-card"><div class="baa-section">{t("generated_sql", LANG)}</div>',
                        unsafe_allow_html=True)
            st.code(result["sql"], language="sql")
            st.markdown("</div>", unsafe_allow_html=True)

            df = result.get("results")
            if df is not None and not df.empty:
                st.dataframe(df, hide_index=True, use_container_width=True)
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                text_cols = df.select_dtypes(exclude="number").columns.tolist()
                if numeric_cols and text_cols:
                    fig = px.bar(df, x=text_cols[0], y=numeric_cols[0], color_discrete_sequence=["#1E3A5F"])
                    st.plotly_chart(fig, use_container_width=True)
            elif df is not None:
                st.info(t("no_rows_returned", LANG))

    _footer()


# ── ETL page ──────────────────────────────────────────────────────────────────

def etl_page():
    _header()
    st.markdown(f'<div class="baa-section">{t("section_etl", LANG)}</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(t("upload_csv_label", LANG), type=["csv", "xlsx", "xls"])
    sink = st.selectbox(t("destination_label", LANG), ["sqlite", "excel", "sheets", "postgres"], index=0)
    table_name = st.text_input(t("table_name_label", LANG))

    if uploaded is not None and st.button(t("clean_load_btn", LANG)):
        ext = os.path.splitext(uploaded.name)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(uploaded.read())
        tmp.close()

        try:
            with st.spinner(t("cleaning_spinner", LANG)):
                report = etl.clean_and_load(tmp.name, sink=sink, table_name=table_name or None)
            st.markdown(
                f'<div class="baa-success">{t("rows_loaded", LANG, n=report["rows_loaded"], dest=report["saved_to"])}</div>',
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            c1.metric(t("empty_rows_removed", LANG), report["empty_rows_removed"])
            c2.metric(t("cells_cleaned", LANG), report["cells_stripped"])
            c3.metric(t("columns_renamed", LANG), len(report["columns_renamed"]))
            if report["columns_renamed"]:
                st.caption(", ".join(report["columns_renamed"]))
        except Exception as e:
            _error(e)
        finally:
            os.unlink(tmp.name)

    _footer()


# ── Reports page ──────────────────────────────────────────────────────────────

def reports_page():
    _header()
    st.markdown(f'<div class="baa-section">{t("section_reports", LANG)}</div>', unsafe_allow_html=True)
    _gemini_warning()

    period_keys = ["day", "week", "month"]
    period_label_keys = {"day": "period_day", "week": "period_week", "month": "period_month"}
    period = st.selectbox(t("period_label", LANG), period_keys, index=1,
                           format_func=lambda k: t(period_label_keys[k], LANG))
    if st.button(t("generate_report_btn", LANG)):
        try:
            with st.spinner(t("generating_report_spinner", LANG)):
                report = reporting.generate_report(period, language=LANG)
            c1, c2 = st.columns(2)
            c1.metric(t("documents_processed", LANG), report["documents_count"])
            c2.metric(t("approval_requests", LANG), report["approvals_count"])
            st.markdown('<div class="baa-card">', unsafe_allow_html=True)
            st.write(report["summary"])
            st.markdown("</div>", unsafe_allow_html=True)
            if report["exported_to"]:
                st.caption(f'{t("exported_to_label", LANG)} {report["exported_to"]}')
        except Exception as e:
            _error(e)

    _footer()


# ── Router ────────────────────────────────────────────────────────────────────
_PAGES = {
    "chat": chat_page,
    "documents": documents_page,
    "inbox": inbox_page,
    "approvals": approvals_page,
    "ask_db": ask_database_page,
    "etl": etl_page,
    "reports": reports_page,
}
_PAGES[st.session_state.page]()
