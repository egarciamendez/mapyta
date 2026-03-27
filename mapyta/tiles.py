"""Tile provider definitions for Mapyta."""

TILE_PROVIDERS: dict[str, dict[str, str]] = {
    "openstreetmap": {"tiles": "OpenStreetMap", "attr": "OpenStreetMap", "name": "OpenStreetMap"},
    "cartodb_positron": {"tiles": "CartoDB positron", "attr": "CartoDB", "name": "CartoDB Positron"},
    "cartodb_dark": {"tiles": "CartoDB dark_matter", "attr": "CartoDB", "name": "CartoDB Dark"},
    "esri_satellite": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Imagery",
        "name": "Esri Satellite",
    },
    "esri_topo": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Topo Map",
        "name": "Esri Topo",
    },
    "stamen_terrain": {
        "tiles": "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
        "attr": "Stadia/Stamen Terrain",
        "name": "Stamen Terrain",
    },
    "stamen_toner": {
        "tiles": "https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}{r}.png",
        "attr": "Stadia/Stamen Toner",
        "name": "Stamen Toner",
    },
    "kadaster_brt": {
        "tiles": "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/{z}/{x}/{y}.png",
        "attr": "Kadaster BRT Achtergrondkaart",
        "name": "Kadaster BRT",
    },
    "kadaster_luchtfoto": {
        "tiles": "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z}/{x}/{y}.png",
        "attr": "Kadaster Luchtfoto",
        "name": "Kadaster Luchtfoto",
    },
    "kadaster_grijs": {
        "tiles": "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/grijs/EPSG:3857/{z}/{x}/{y}.png",
        "attr": "Kadaster BRT Grijs",
        "name": "Kadaster Grijs",
    },
    # --- Additional providers ---
    "cartodb_voyager": {
        "tiles": "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
        "name": "CartoDB Voyager",
    },
    "esri_streets": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Street Map",
        "name": "Esri Streets",
    },
    "esri_gray": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri Light Gray Canvas",
        "name": "Esri Gray",
    },
    "esri_ocean": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Ocean Base",
        "name": "Esri Ocean",
    },
    "opentopomap": {
        "tiles": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attr": "&copy; OpenStreetMap contributors, SRTM | &copy; OpenTopoMap (CC-BY-SA)",
        "name": "OpenTopoMap",
    },
    "stamen_watercolor": {
        "tiles": "https://tiles.stadiamaps.com/tiles/stamen_watercolor/{z}/{x}/{y}.jpg",
        "attr": "Stadia/Stamen Watercolor",
        "name": "Stamen Watercolor",
    },
    "stadia_alidade": {
        "tiles": "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png",
        "attr": "&copy; Stadia Maps &copy; OpenMapTiles &copy; OpenStreetMap contributors",
        "name": "Stadia Alidade Smooth",
    },
    "stadia_dark": {
        "tiles": "https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png",
        "attr": "&copy; Stadia Maps &copy; OpenMapTiles &copy; OpenStreetMap contributors",
        "name": "Stadia Alidade Dark",
    },
}
