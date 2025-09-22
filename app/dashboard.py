"""Hero landing page for FloatChat AI."""
from __future__ import annotations

import base64
import mimetypes
import sys
from pathlib import Path
from typing import Optional

import streamlit as st

if __package__ in {None, ""}:
    current_dir = Path(__file__).resolve().parent
    for parent in (current_dir, *current_dir.parents):
        if (parent / "app").is_dir():
            sys.path.insert(0, str(parent))
            break

from app.app_layout import apply_base_styles
from app.navigation import NAV_ROUTES, render_header

st.set_page_config(page_title="🌊 FloatChat AI", layout="wide")

apply_base_styles()
render_header(current_page=None)

# ---------------- Styles ---------------- #
hero_styles = """
<style>
  .bg-video {
      position: fixed;
      top: 0;
      left: 0;
      min-width: 100%;
      min-height: 100%;
      object-fit: cover;
      z-index: -2;
  }
  .bg-fallback {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-size: cover;
      background-position: center;
      z-index: -2;
  }
  .video-overlay {
      position: fixed;
      inset: 0;
      background: rgba(11, 26, 47, 0.45);
      z-index: -1;
  }
  .landing-container {
      min-height: calc(100vh - 6rem);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      gap: 1.5rem;
      padding: 3rem 1rem 4rem;
      color: #f8fafc;
  }
  .landing-title {
      font-size: clamp(3rem, 5vw, 4.5rem);
      font-weight: 700;
      letter-spacing: 0.04em;
      margin: 0;
  }
  .landing-subtitle {
      font-size: clamp(1.2rem, 2vw, 1.6rem);
      opacity: 0.85;
      max-width: 680px;
      margin: 0 auto;
      line-height: 1.6;
  }
  .landing-container .stButton > button {
      font-size: 1.05rem;
      padding: 0.9rem 2.8rem;
      border-radius: 999px;
      box-shadow: 0 12px 30px rgba(56, 189, 248, 0.35);
  }
</style>
"""

# ---------------- Background resolution ---------------- #
def _resolve_background_path() -> tuple[Optional[Path], Optional[Path]]:
    """Return first found video or image background path."""
    current_dir = Path(__file__).resolve().parent
    video_candidates = [
        Path("app/scripts/datasets/background.mp4"),
        Path("scripts/datasets/background.mp4"),
        current_dir / "scripts" / "datasets" / "background.mp4",
        current_dir.parent / "scripts" / "datasets" / "background.mp4",
    ]
    image_candidates = [
        Path("app/scripts/datasets/background.jpg"),
        Path("scripts/datasets/background.jpg"),
        current_dir / "scripts" / "datasets" / "background.jpg",
        current_dir.parent / "scripts" / "datasets" / "background.jpg",
    ]

    video = next((p.resolve() for p in video_candidates if p.exists()), None)
    image = next((p.resolve() for p in image_candidates if p.exists()), None)
    return video, image


@st.cache_data(show_spinner=False)
def _embed_background_video(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.exists():
        return None
    try:
        data = path.read_bytes()
        if not data:
            return None
        return base64.b64encode(data).decode("utf-8")
    except Exception as e:
        st.error(f"⚠️ Could not load background video: {e}")
        return None


video_path, image_path = _resolve_background_path()
encoded_video = _embed_background_video(video_path)
encoded_image_uri: Optional[str] = None

if image_path is not None and image_path.exists():
    try:
        image_bytes = image_path.read_bytes()
        if image_bytes:
            mime_type, _ = mimetypes.guess_type(str(image_path))
            mime_type = mime_type or "image/jpeg"
            encoded_image = base64.b64encode(image_bytes).decode("utf-8")
            encoded_image_uri = f"data:{mime_type};base64,{encoded_image}"
    except Exception as exc:  # pragma: no cover - defensive logging for Streamlit runtime
        st.error(f"⚠️ Could not load background image: {exc}")

st.markdown(hero_styles, unsafe_allow_html=True)

# ---------------- Hero section ---------------- #
st.markdown(
    """
    <div class="landing-container">
        <h1 class="landing-title">FloatChat AI</h1>
        <p class="landing-subtitle">An interactive platform for oceanographic insights</p>
    </div>
    """,
    unsafe_allow_html=True,
)

cta_cols = st.columns([1, 1, 1])
with cta_cols[1]:
    if st.button("Enter the Chat", type="primary", use_container_width=True):
        st.session_state["top_nav_choice"] = "Chat"
        switch = getattr(st, "switch_page", None)
        if switch is not None:
            switch(NAV_ROUTES.get("Chat", "pages/70_Chat"))