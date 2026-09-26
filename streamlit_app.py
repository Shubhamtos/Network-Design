"""Streamlit host for the bundled Network Studio interface and HiGHS solver."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="The Rookie · Network Studio", page_icon="🏭", layout="wide")

@st.cache_resource
def frontend(archive_bytes: bytes):
    # The archive is a versioned application asset, never a user upload.
    from io import BytesIO
    directory = TemporaryDirectory(prefix="rookie-network-")
    root = Path(directory.name).resolve()
    with ZipFile(BytesIO(archive_bytes)) as archive:
        for member in archive.infolist():
            target = (root / member.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Invalid frontend archive path")
        archive.extractall(root)
    component = components.declare_component("rookie_network_" + sha256(archive_bytes).hexdigest()[:12], path=str(root))
    return directory, component

st.markdown("""<style>
.block-container {padding: 0 0 1rem; max-width: 100%;}
[data-testid="stHeader"] {background: transparent; height: 0;}
[data-testid="stMainBlockContainer"] {padding-top: 0;}
iframe[title^="streamlit_app.rookie_network"] {border: 0;}
</style>""", unsafe_allow_html=True)
archive_path = Path(__file__).with_name("frontend.zip")
if not archive_path.exists():
    st.error("The bundled interface is missing. Deploy frontend.zip alongside streamlit_app.py.")
    st.stop()
_directory, network_studio = frontend(archive_path.read_bytes())
network_studio(key="network-studio", default=None)
