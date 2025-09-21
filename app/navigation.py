"""Navigation helpers for the FloatChat multipage experience."""
from __future__ import annotations

from typing import Optional

import streamlit as st
from streamlit_option_menu import option_menu

NAV_ITEMS = [
    "Maps",
    "Profile",
    "Hovmöller",
    "Float Comparison",
    "Table",
    "Export",
    "Chat",
]

NAV_ICONS = [
    "map",
    "activity",
    "bar-chart",
    "shuffle",
    "table",
    "download",
    "chat-dots",
]

MAP_VARIANTS = ["Plotly", "Leaflet (fast)", "Cesium 3D"]
MAP_ROUTES = {
    "Plotly": "pages/10_Maps_Plotly",
    "Leaflet (fast)": "pages/11_Maps_Leaflet_fast",
    "Cesium 3D": "pages/12_Maps_Cesium_3D",
}

NAV_ROUTES = {
    "Profile": "pages/20_Profile.py",
    "Hovmöller": "pages/30_Hovmöller.py",
    "Float Comparison": "pages/40_Float_Comparison.py",
    "Table": "pages/50_Table.py",
    "Export": "pages/60_Export.py",
    "Chat": "pages/70_Chat.py",
}


def _switch_page(target: str) -> None:
    """Switch to another Streamlit page if possible."""

    switch = getattr(st, "switch_page", None)
    if switch is None:
        return

    for candidate in (target, f"{target}.py"):
        try:
            switch(candidate)
            return
        except Exception:
            continue


def render_header(current_page: Optional[str], current_map: Optional[str] = None) -> Optional[str]:
    """Render the persistent top navigation header.

    Parameters
    ----------
    current_page:
        Name of the active navigation item (one of :data:`NAV_ITEMS`) or ``None``
        for pages that are not part of the primary navigation (e.g., landing).
    current_map:
        Active map variant when ``current_page`` is ``"Maps"``.

    Returns
    -------
    Optional[str]
        The currently selected map variant when on the maps page.
    """

    if current_page in NAV_ITEMS:
        st.session_state["top_nav_choice"] = current_page

    default_choice = st.session_state.get("top_nav_choice")
    if default_choice not in NAV_ITEMS:
        default_choice = NAV_ITEMS[0]
        st.session_state["top_nav_choice"] = default_choice

    selected = option_menu(
        menu_title=None,
        options=NAV_ITEMS,
        icons=NAV_ICONS,
        orientation="horizontal",
        default_index=NAV_ITEMS.index(default_choice),
        key="top_navigation",
    )

    if selected != st.session_state.get("top_nav_choice"):
        st.session_state["top_nav_choice"] = selected
        if selected == "Maps":
            variant = st.session_state.get("map_variant", MAP_VARIANTS[0])
            _switch_page(MAP_ROUTES.get(variant, MAP_ROUTES[MAP_VARIANTS[0]]))
        else:
            _switch_page(NAV_ROUTES[selected])

    map_choice: Optional[str] = None
    if current_page == "Maps":
        initial_map = current_map or st.session_state.get("map_variant", MAP_VARIANTS[0])
        if initial_map not in MAP_VARIANTS:
            initial_map = MAP_VARIANTS[0]
        map_choice = st.selectbox(
            "Map view",
            MAP_VARIANTS,
            index=MAP_VARIANTS.index(initial_map),
            key="map_variant_selector",
        )
        st.session_state["map_variant"] = map_choice
        if map_choice != current_map:
            _switch_page(MAP_ROUTES.get(map_choice, MAP_ROUTES[MAP_VARIANTS[0]]))

    return map_choice
