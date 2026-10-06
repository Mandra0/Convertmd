import streamlit as st
from markitdown import MarkItDown
import os

# 1. SET LAYOUT WIDE
st.set_page_config(page_title="Universal Markdown Converter", page_icon="📝", layout="wide")

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
    div[data-testid="stColumn"] .stButton>button { font-size: 16px !important; padding: 8px 16px !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton>button[kind="primary"] { font-size: 16px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📝 Universal To Markdown Converter")
st.write("### Seret atau pilih file apa saja (PDF, Excel, Word, PPTX) untuk diubah menjadi Markdown yang ramah AI.")

md = MarkItDown()

# Inisialisasi Kunci
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "converted_cache" not in st.session_state:
    st.session_state.converted_cache = {}
if "hidden_errors" not in st.session_state:
    st.session_state.hidden_errors = set()

# Layout Tombol Reset
col_title, col_reset = st.columns([6, 1])
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
        
        if file_name in st.session_state.hidden_errors:
            continue
            
        # 1. CEK CACHE: File dari memori langsung dibuatkan border container
        if file_name in st.session_state.converted_cache:
            md_text = st.session_state.converted_cache[file_name]
            
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
            
        # 2. PROSES BARU: Gunakan container tanpa dropdown
        with st.container(border=True):
            status_text = st.empty()
            status_text.markdown(f"**⏳ Mengonversi {file_name}...**")
            
            try:
                temp_dir = "temp_conversion"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file_path = os.path.join(temp_dir, file_name)
                
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                result = md.convert(temp_file_path)
                md_text = result.text_content
                os.remove(temp_file_path)
                
                st.session_state.converted_cache[file_name] = md_text
                
                status_text.markdown(f"**✅ {file_name} Sukses Terconvert!**")
                st.download_button(
                    label=f"📥 Download {base_name}.md",
                    data=md_text,
                    file_name=f"{base_name}.md",
                    mime="text/markdown",
                    key=f"dl_{file_name}_{idx}"
                )
                
            except Exception as e:
                status_text.markdown(f"**❌ {file_name} Gagal!**")
                if st.button(f"💥 Hapus File Eror: {file_name}", key=f"err_{file_name}_{idx}", type="primary"):
                    st.session_state.hidden_errors.add(file_name)
                    st.rerun()