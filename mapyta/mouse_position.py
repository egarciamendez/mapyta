"""Mouse-position readout in a non-WGS84 projected CRS (e.g. RD EPSG:28992)."""

import warnings
from typing import ClassVar

from branca.element import MacroElement
from folium.elements import JSCSSMixin
from folium.template import Template
from pyproj import CRS


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
        with warnings.catch_warnings():
            # pyproj warns that round-tripping through a proj4 string loses
            # info — true in general, but proj4js needs proj4 syntax and the
            # round trip is good enough for client-side cursor display.
            warnings.simplefilter("ignore", UserWarning)
            self.proj4_def = parsed.to_proj4()

        self.crs = crs
        self.position = position
        self.separator = separator
        self.empty_string = empty_string
        self.num_digits = 6 if parsed.is_geographic else 0
