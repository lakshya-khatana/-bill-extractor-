"""
Bill Extractor v2 — Streamlit + Claude Vision API
Upload bill photos, click a thumbnail, get printed + handwritten fields extracted.

Run with:
    streamlit run app.py
"""

import os
import json
from pathlib import Path

import streamlit as st
import pandas as pd

from extractor import extract_fields, configure_gemini, FIELD_LIST, FIELD_LABELS

st.set_page_config(page_title="Bill Extractor", layout="wide", page_icon="🧾")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
    --paper: #EDE7D6;
    --paper-light: #F7F3E8;
    --ink: #232A3B;
    --stamp: #A6402E;
    --ledger: #3C5941;
    --line: #C7BEA6;
}

.stApp {
    background-color: var(--paper);
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    color: var(--ink);
}

h1, h2, h3, h4 {
    font-family: 'Space Mono', monospace;
    color: #6B4226 !important;
    font-weight: 700;
}

h1 {
    border-bottom: 2px dashed var(--line);
    padding-bottom: 0.6rem;
    margin-bottom: 1.2rem;
}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    color: #6B4226 !important;
    opacity: 1 !important;
}

.stMarkdown p, .stMarkdown small {
    color: #6B4226 !important;
}

[data-testid="stStatusWidget"], .stSpinner, .stSpinner > div {
    color: #6B4226 !important;
}

section[data-testid="stSidebar"] {
    background-color: #E4DCC6;
    border-right: 2px dashed var(--line);
}

section[data-testid="stSidebar"] h2 {
    font-size: 1.05rem;
}

.stButton > button {
    font-family: 'Space Mono', monospace;
    background-color: var(--paper-light);
    color: var(--ink);
    border: 2px solid var(--ink);
    border-radius: 3px;
    padding: 0.35rem 0.9rem;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.stButton > button:hover {
    background-color: var(--stamp);
    color: var(--paper-light);
    border-color: var(--stamp);
}

.stDownloadButton > button {
    font-family: 'Space Mono', monospace;
    background-color: var(--ledger);
    color: var(--paper-light);
    border: none;
    border-radius: 3px;
}

.stDownloadButton > button:hover {
    background-color: #2c4433;
    color: var(--paper-light);
}

div[data-testid="stImage"] img {
    border: 1px solid var(--line);
    box-shadow: 3px 3px 0px var(--line);
    border-radius: 2px;
}

.stTextInput > div > div > input {
    font-family: 'Space Mono', monospace;
    background-color: var(--paper-light);
    border: 1px solid var(--line);
    color: var(--ink);
    border-radius: 2px;
}

.stTextInput > label {
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    color: var(--ink);
}

hr {
    border: none;
    border-top: 2px dashed var(--line);
    margin: 1.5rem 0;
}

[data-testid="stMetricValue"], .stDataFrame {
    font-family: 'Space Mono', monospace;
}

.stAlert {
    border-radius: 2px;
    border-left: 4px solid var(--stamp);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

UPLOAD_DIR = Path("uploaded_bills")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_FILE = Path("results.json")

# ---- Session state ------------------------------------------------------
if "results" not in st.session_state:
    if RESULTS_FILE.exists():
        try:
            content = RESULTS_FILE.read_text(encoding="utf-8").strip()
            st.session_state.results = json.loads(content) if content else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            st.session_state.results = {}
    else:
        st.session_state.results = {}  # filename -> extracted dict

if "selected" not in st.session_state:
    st.session_state.selected = None


def save_results():
    RESULTS_FILE.write_text(
        json.dumps(st.session_state.results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_client():
    if not os.environ.get("GEMINI_API_KEY"):
        st.error(
            "GEMINI_API_KEY environment variable not set. "
            "Set it before running `streamlit run app.py`."
        )
        st.stop()
    configure_gemini()
    return None  # kept for call-site compatibility; extract_fields ignores it


# ---- Sidebar: upload -----------------------------------------------------
st.sidebar.header("Upload bills")
uploaded_files = st.sidebar.file_uploader(
    "Choose bill/warranty images",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

if uploaded_files:
    for uf in uploaded_files:
        dest = UPLOAD_DIR / uf.name
        if not dest.exists():
            dest.write_bytes(uf.getbuffer())
    st.sidebar.success(f"{len(uploaded_files)} file(s) ready.")

all_images = sorted(
    [p for p in UPLOAD_DIR.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
)

st.sidebar.markdown(f"**Total bills in queue:** {len(all_images)}")

if st.sidebar.button("Extract all remaining"):
    client = get_client()
    progress = st.sidebar.progress(0)
    for i, img_path in enumerate(all_images):
        if img_path.name not in st.session_state.results:
            try:
                st.session_state.results[img_path.name] = extract_fields(str(img_path), client)
            except Exception as e:
                st.session_state.results[img_path.name] = {"error": str(e)}
        progress.progress((i + 1) / len(all_images))
    save_results()
    st.sidebar.success("Batch extraction done.")

st.title("Bill Extractor")
st.caption("Click a bill below to pull its fields — printed or handwritten.")

if not all_images:
    st.info("Upload some bill photos from the sidebar to get started.")
    st.stop()

# ---- Thumbnail grid -------------------------------------------------------
cols = st.columns(5)
for idx, img_path in enumerate(all_images):
    col = cols[idx % 5]
    with col:
        st.image(str(img_path), use_container_width=True)
        done = img_path.name in st.session_state.results
        label = "View extracted data" if done else "Extract this bill"
        if st.button(label, key=f"btn_{img_path.name}"):
            st.session_state.selected = img_path.name
            if not done:
                client = get_client()
                with st.spinner(f"Extracting {img_path.name}..."):
                    try:
                        result = extract_fields(str(img_path), client)
                        st.session_state.results[img_path.name] = result
                        save_results()
                    except Exception as e:
                        st.error(f"Extraction failed: {e}")

st.divider()

# ---- Detail panel ----------------------------------------------------------
if st.session_state.selected and st.session_state.selected in st.session_state.results:
    sel = st.session_state.selected
    data = st.session_state.results[sel]

    left, right = st.columns([1, 1])
    with left:
        st.subheader(sel)
        st.image(str(UPLOAD_DIR / sel), use_container_width=True)

    with right:
        st.subheader("Extracted fields")
        if "error" in data:
            st.error(data["error"])
        else:
            edited = {}
            for key in FIELD_LIST:
                edited[key] = st.text_input(FIELD_LABELS[key], value=data.get(key, ""), key=f"field_{sel}_{key}")
            if st.button("💾 Save edits"):
                st.session_state.results[sel] = edited
                save_results()
                st.success("Saved.")

st.divider()

# ---- Export ------------------------------------------------------------
st.subheader("Export")
if st.session_state.results:
    rows = []
    for fname, data in st.session_state.results.items():
        if "error" in data:
            continue
        row = {"filename": fname}
        row.update({FIELD_LABELS[k]: data.get(k, "") for k in FIELD_LIST})
        rows.append(row)
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "extracted_bills.csv", "text/csv")
    else:
        st.write("No successful extractions yet.")
else:
    st.write("Nothing extracted yet.")
