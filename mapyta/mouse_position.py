"""Mouse-position readout in a non-WGS84 projected CRS (e.g. RD EPSG:28992)."""

import warnings
from typing import ClassVar

from branca.element import MacroElement
from folium.elements import JSCSSMixin
from folium.template import Template
from pyproj import CRS

# proj4js needs +towgs84 to apply the Bessel→WGS84 datum shift; without it
# the result is ~100 m off in NL. pyproj's CRS.to_proj4() deliberately drops
# +towgs84 (modern PROJ uses grid-based shifts), so for proj4js we ship the
# legacy strings published by proj4js itself. Add CRSs here as needed.
_PROJ4_DEFS_WITH_TOWGS84: dict[str, str] = {
    "EPSG:28992": (
        "+proj=sterea +lat_0=52.15616055555555 +lon_0=5.38763888888889 "
        "+k=0.9999079 +x_0=155000 +y_0=463000 +ellps=bessel "
        "+towgs84=565.417,50.3319,465.552,-0.398957,0.343988,-1.8774,4.0725 "
        "+units=m +no_defs"
    ),
}


class MousePositionProjected(JSCSSMixin, MacroElement):
    """Show the cursor coordinates transformed to a projected CRS.

    Folium's bundled :class:`folium.plugins.MousePosition` only displays
    WGS84 lat/lon — its per-axis ``lat_formatter``/``lng_formatter`` cannot
    do a 2D projection.  This control loads proj4js on the page, registers
    the target CRS, and writes the transformed ``X | Y`` pair into a div on
    every ``mousemove``.

    Parameters
    ----------
    crs : str
        Target CRS, e.g. ``"EPSG:28992"`` for Dutch RD New.  Anything
        :func:`pyproj.CRS.from_user_input` accepts.
    position : str
        Leaflet control position (``"bottomleft"``, ``"topright"``, ...).
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}
            proj4.defs({{ this.crs|tojson }}, {{ this.proj4_def|tojson }});
            var {{ this.get_name() }} = L.control({position: {{ this.position|tojson }}});
            {{ this.get_name() }}.onAdd = function(map) {
                var div = L.DomUtil.create('div', 'leaflet-control-mouseposition');
                div.innerHTML = {{ this.empty_string|tojson }};
                map.on('mousemove', function(e) {
                    var p = proj4("EPSG:4326", {{ this.crs|tojson }}, [e.latlng.lng, e.latlng.lat]);
                    div.innerHTML = p[0].toFixed({{ this.num_digits }}) + {{ this.separator|tojson }} + p[1].toFixed({{ this.num_digits }});
                });
                map.on('mouseout', function() {
                    div.innerHTML = {{ this.empty_string|tojson }};
                });
                return div;
            };
            {{ this._parent.get_name() }}.addControl({{ this.get_name() }});
        {% endmacro %}
        """
    )

    default_js: ClassVar = [
        ("proj4_js", "https://cdn.jsdelivr.net/npm/proj4@2.11.0/dist/proj4.min.js"),
    ]
    default_css: ClassVar = [
        (
            "Control_MousePosition_css",
            "https://cdn.jsdelivr.net/gh/ardhi/Leaflet.MousePosition/src/L.Control.MousePosition.min.css",
        ),
    ]

    def __init__(
        self,
        crs: str,
        position: str = "bottomleft",
        separator: str = " | ",
        empty_string: str = "Unavailable",
    ) -> None:
        super().__init__()
        self._name = "MousePositionProjected"

        parsed = CRS.from_user_input(crs)
        authority = parsed.to_authority()
        auth_key = f"{authority[0]}:{authority[1]}" if authority else None
        canonical = _PROJ4_DEFS_WITH_TOWGS84.get(auth_key) if auth_key else None
        if canonical is not None:
            self.proj4_def = canonical
        else:
            with warnings.catch_warnings():
                # pyproj's to_proj4() drops +towgs84; for CRSs not in the
                # curated table the readout may be tens to hundreds of m off
                # the official transformation. Acceptable fallback for
                # display-only purposes.
                warnings.simplefilter("ignore", UserWarning)
                self.proj4_def = parsed.to_proj4()

        self.crs = crs
        self.position = position
        self.separator = separator
        self.empty_string = empty_string
        self.num_digits = 6 if parsed.is_geographic else 0
