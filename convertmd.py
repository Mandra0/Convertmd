import io
import os
import tempfile
import zipfile
import streamlit as st
from markitdown import MarkItDown

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import pypdf
except ImportError:
    pypdf = None

# 1. SET LAYOUT WIDE & GITHUB MENU
st.set_page_config(
    page_title="Universal Markdown Converter",
    page_icon="📝",
    layout="wide",
    menu_items={
        "Get Help": "https://github.com/Mandra0/Convertmd",
        "Report a bug": "https://github.com/Mandra0/Convertmd/issues",
        "About": "### Universal Markdown Converter\n\nGitHub: [Mandra0/Convertmd](https://github.com/Mandra0/Convertmd)"
    }
)
# ==================== BLOK CSS KUSTOM ====================
st.markdown("""
    <style>
    div[data-testid="stFileUploader"] section button { font-size: 22px !important; padding: 15px 30px !important; }
    div[data-testid="stFileUploaderFileName"] { font-size: 20px !important; font-weight: bold !important; padding: 8px !important; }
    div[data-testid="stFileUploader"] div { font-size: 16px !important; }
    h1 { font-size: 40px !important; font-weight: bold !important; }
    h3 { font-size: 24px !important; }
    
    .stDownloadButton>button {
        font-size: 18px !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
        width: auto !important;
        background-color: #0f52ba !important;
        color: white !important;
        border-radius: 6px !important;
    }
    div[data-testid="stColumn"] .stButton>button, div[data-testid="stColumn"] .stDownloadButton>button, div[data-testid="stColumn"] .stLinkButton>a { font-size: 16px !important; padding: 8px 16px !important; width: 100% !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton>button[kind="primary"] { font-size: 16px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 Universal To Markdown Converter")
st.write("### Seret atau pilih file apa saja (PDF, Excel, Word, PPTX) untuk diubah menjadi Markdown yang ramah AI.")

@st.cache_resource
def get_markitdown():
    return MarkItDown()

md = get_markitdown()

def sanitize_cell(val):
    if val is None:
        return ""
    return str(val).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")

def convert_excel_fast(stream: io.BytesIO) -> str:
    stream.seek(0)
    wb = openpyxl.load_workbook(stream, read_only=True, data_only=True)
    parts = []
    for sheetname in wb.sheetnames:
        ws = wb[sheetname]
        parts.append(f"## {sheetname}\n\n")
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            continue
        cols = [sanitize_cell(c) for c in header_row]
        parts.append("| " + " | ".join(cols) + " |\n")
        parts.append("| " + " | ".join(["---"] * len(cols)) + " |\n")
        for row in rows_iter:
            parts.append("| " + " | ".join(sanitize_cell(c) for c in row) + " |\n")
        parts.append("\n")
    wb.close()
    return "".join(parts).strip()

def convert_pdf_fast(stream: io.BytesIO) -> str:
    stream.seek(0)
    reader = pypdf.PdfReader(stream)
    pages_text = []
    for page in reader.pages:
        txt = page.extract_text(extraction_mode="layout") or page.extract_text() or ""
        if txt.strip():
            pages_text.append(txt.strip())
    return "\n\n---\n\n".join(pages_text).strip()

def convert_document(file_bytes: bytes, ext: str) -> str:
    ext_lower = ext.lower()
    stream = io.BytesIO(file_bytes)
    
    # 1. Jalur cepat untuk Excel (.xlsx, .xls)
    if openpyxl and ext_lower in [".xlsx", ".xls"]:
        try:
            return convert_excel_fast(stream)
        except Exception:
            stream.seek(0)
            
    # 2. Jalur cepat untuk PDF (.pdf)
    if pypdf and ext_lower == ".pdf":
        try:
            res = convert_pdf_fast(stream)
            if res:
                return res
        except Exception:
            stream.seek(0)
            
    # 3. Konversi langsung di RAM via MarkItDown stream
    try:
        stream.seek(0)
        res = md.convert_stream(stream, file_extension=ext_lower)
        return res.text_content
    except Exception:
        # 4. Fallback file sementara jika konversi stream tidak didukung
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name
        try:
            res = md.convert(temp_file_path)
            return res.text_content
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

# Inisialisasi Kunci
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "converted_cache" not in st.session_state:
    st.session_state.converted_cache = {}
if "hidden_errors" not in st.session_state:
    st.session_state.hidden_errors = set()

# Layout Tombol Header
col_title, col_download, col_reset = st.columns([5.4, 1.3, 1.3])
download_placeholder = col_download.empty()
with col_reset:
    if st.button("🧹 Reset Semua", use_container_width=True, type="secondary"):
        st.session_state.hidden_errors.clear()
        st.session_state.converted_cache.clear()
        st.session_state.uploader_key += 1
        st.rerun()

uploaded_files = st.file_uploader(
    "Cemplungkan file kamu di sini:", 
    type=["pdf", "xlsx", "xls", "docx", "pptx", "txt", "html"], 
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

# PROSES KONVERSI 
if uploaded_files:
    st.write(f"### 🔄 Memproses {len(uploaded_files)} File:")
    
    for idx, uploaded_file in enumerate(uploaded_files):
        file_name = uploaded_file.name
        base_name, ext = os.path.splitext(file_name)
        cache_key = f"{file_name}_{uploaded_file.size}"
        
        if file_name in st.session_state.hidden_errors:
            continue
            
        # 1. CEK CACHE
        if cache_key in st.session_state.converted_cache:
            md_text = st.session_state.converted_cache[cache_key]
            
            with st.container(border=True):
                st.markdown(f"**✅ {file_name} (Loaded from Memory)**")
                st.download_button(
                    label=f"📥 Download {base_name}.md",
                    data=md_text,
                    file_name=f"{base_name}.md",
                    mime="text/markdown",
                    key=f"dl_cached_{file_name}_{idx}"
                )
            continue 
            
        # 2. PROSES KONVERSI CEPAT
        with st.container(border=True):
            status_text = st.empty()
            file_size_str = f"{uploaded_file.size / (1024*1024):.1f} MB" if uploaded_file.size >= 1024*1024 else f"{uploaded_file.size / 1024:.0f} KB"
            status_text.markdown(f"**⏳ Mengonversi {file_name} ({file_size_str})...**")
            
            try:
                with st.spinner(f"Mengonversi {file_name}..."):
                    md_text = convert_document(uploaded_file.getvalue(), ext)
                
                st.session_state.converted_cache[cache_key] = md_text
                
                status_text.markdown(f"**✅ {file_name} Sukses Terconvert!**")
                st.download_button(
                    label=f"📥 Download {base_name}.md",
                    data=md_text,
                    file_name=f"{base_name}.md",
                    mime="text/markdown",
                    key=f"dl_{file_name}_{idx}"
                )
            except Exception as e:
                status_text.markdown(f"**❌ {file_name} Gagal! Error: {e}**")
                if st.button(f"💥 Hapus File Eror: {file_name}", key=f"err_{file_name}_{idx}", type="primary"):
                    st.session_state.hidden_errors.add(file_name)
                    st.rerun()

# Tombol Download Semua (ZIP)
has_converted_files = False
if uploaded_files:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        used_names = set()
        for f in uploaded_files:
            if f.name in st.session_state.hidden_errors:
                continue
            cache_key = f"{f.name}_{f.size}"
            if cache_key in st.session_state.converted_cache:
                base_name, _ = os.path.splitext(f.name)
                base_name = base_name if base_name else "document"
                target_name = f"{base_name}.md"
                counter = 1
                while target_name in used_names:
                    target_name = f"{base_name}_{counter}.md"
                    counter += 1
                used_names.add(target_name)
                zip_file.writestr(target_name, st.session_state.converted_cache[cache_key])
        
        if used_names:
            has_converted_files = True

    if has_converted_files:
        zip_buffer.seek(0)
        download_placeholder.download_button(
            label="📥 Download Semua",
            data=zip_buffer.getvalue(),
            file_name="converted_markdowns.zip",
            mime="application/zip",
            use_container_width=True,
            key="dl_all_active"
        )

if not has_converted_files:
    download_placeholder.button("📥 Download Semua", disabled=True, use_container_width=True, key="dl_all_disabled")
