"""BDD-style tests for the enable_draw() feature.

Each test follows the Given-When-Then pattern with a scenario
docstring and Arrange/Act/Assert comments.
"""
# ruff: noqa: SLF001

from pathlib import Path

import pytest

from mapyta import DrawConfig, Map, RawJS

# ===================================================================
# Scenarios for drawing controls on the map.
# ===================================================================


class TestEnableDraw:
    """Scenarios for enable_draw() configuration and HTML output."""

    # --- 1. Fluent chaining ---

    def test_enable_draw_returns_self(self) -> None:
        """
        Scenario: enable_draw supports fluent chaining.

        Given: An empty map
        When: enable_draw() is called
        Then: The return value is the same Map instance
        """
        # Arrange - Given
        m = Map()

        # Act - When
        result = m.enable_draw()

        # Assert - Then
        assert result is m, "enable_draw should return self for chaining"

    # --- 2. Invalid tool raises ---

    def test_invalid_tool_raises_value_error(self) -> None:
        """
        Scenario: Invalid tool name is rejected.

        Given: An empty map
        When: enable_draw is called with an invalid tool
        Then: A ValueError is raised mentioning the invalid tool
        """
        # Arrange - Given
        m = Map()

        # Act & Assert - When/Then
        with pytest.raises(ValueError, match="hexagon"):
            m.enable_draw(tools=["hexagon"])  # type: ignore[arg-type]

    # --- 3. Stores config ---

    def test_stores_draw_config(self) -> None:
        """
        Scenario: enable_draw stores the configuration.

        Given: An empty map
        When: enable_draw is called with specific tools
        Then: _draw_config holds a DrawConfig with those tools
        """
        # Arrange - Given
        m = Map()

        # Act - When
        m.enable_draw(tools=["polygon", "marker"])

        # Assert - Then
        assert isinstance(m._draw_config, DrawConfig)
        assert m._draw_config.tools == ["polygon", "marker"]

    # --- 6. HTML has draw CSS ---

    def test_html_contains_draw_css(self) -> None:
        """
        Scenario: Generated HTML includes Leaflet.draw CSS.

        Given: A map with drawing enabled
        When: HTML is rendered
        Then: The Leaflet.draw CSS CDN link is present
        """
        # Arrange - Given
        m = Map().enable_draw()

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "leaflet.draw.css" in html

    # --- 7. HTML has draw JS ---

    def test_html_contains_draw_js(self) -> None:
        """
        Scenario: Generated HTML includes Leaflet.draw JS.

        Given: A map with drawing enabled
        When: HTML is rendered
        Then: The Leaflet.draw JS CDN link is present
        """
        # Arrange - Given
        m = Map().enable_draw()

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "leaflet.draw.js" in html

    # --- 8. HTML has L.Control.Draw ---

    def test_html_contains_draw_control(self) -> None:
        """
        Scenario: Generated HTML initializes L.Control.Draw.

        Given: A map with drawing enabled
        When: HTML is rendered
        Then: L.Control.Draw appears in the script
        """
        # Arrange - Given
        m = Map().enable_draw()

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "L.Control.Draw" in html

    # --- 9. HTML has submit button ---

    def test_html_contains_submit_button(self) -> None:
        """
        Scenario: Generated HTML has a submit button with default label.

        Given: A map with drawing enabled
        When: HTML is rendered
        Then: The default submit label "Submit" is present
        """
        # Arrange - Given
        m = Map().enable_draw()

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "Submit" in html

    # --- 10. Custom submit label ---

    def test_custom_submit_label(self) -> None:
        """
        Scenario: Custom submit label appears in HTML.

        Given: A map with drawing enabled and a custom submit label
        When: HTML is rendered
        Then: The custom label appears in the HTML
        """
        # Arrange - Given
        m = Map().enable_draw(submit_label="Verstuur")

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "Verstuur" in html

    # --- 11. Download fallback ---

    def test_download_fallback(self) -> None:
        """
        Scenario: Without a callback, submit triggers a GeoJSON download.

        Given: A map with drawing enabled and no on_submit
        When: HTML is rendered
        Then: The script contains download logic with .geojson filename
        """
        # Arrange - Given
        m = Map().enable_draw()

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "download" in html
        assert ".geojson" in html

    # --- 12. URL → fetch ---

    def test_url_triggers_fetch(self, tmp_path: Path) -> None:
        """
        Scenario: URL on_submit generates a fetch POST request.

        Given: A map with on_submit set to a URL
        When: HTML is saved to a file
        Then: A fetch call to that URL appears in the HTML
        """
        # Arrange - Given
        url = "https://example.com/api/shapes"
        m = Map().enable_draw(on_submit=url)
        out = tmp_path / "fetch_map.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert f'fetch("{url}"' in html

    # --- 16. URL fetch has no Content-Type header ---

    def test_url_fetch_has_no_content_type_header(self) -> None:
        """
        Scenario: URL fetch omits Content-Type to avoid CORS preflight.

        Given: A map with on_submit set to a URL
        When: HTML is rendered
        Then: Content-Type application/json does NOT appear in the fetch call
        """
        # Arrange - Given
        url = "https://example.com/api/shapes"
        m = Map().enable_draw(on_submit=url)

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "application/json" not in html

    # --- 17. Function name ---

    def test_function_name_callback(self, tmp_path: Path) -> None:
        """
        Scenario: String on_submit calls a window function.

        Given: A map with on_submit set to a function name
        When: HTML is saved to a file
        Then: window["name"] call appears in the HTML
        """
        # Arrange - Given
        m = Map().enable_draw(on_submit="handleDrawing")
        out = tmp_path / "func_map.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert 'window["handleDrawing"]' in html

    # --- 17. RawJS inline ---

    def test_rawjs_inline(self) -> None:
        """
        Scenario: RawJS on_submit inlines the JavaScript verbatim.

        Given: A map with on_submit set to a RawJS instance
        When: HTML is rendered
        Then: The raw JS code appears in the HTML
        """
        # Arrange - Given
        js_code = "function(data) { console.log(data); }"
        m = Map().enable_draw(on_submit=RawJS(js_code))

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert js_code in html

    # --- 18. Idempotent injection ---

    def test_idempotent_injection(self) -> None:
        """
        Scenario: Rendering multiple times injects CDN links only once.

        Given: A map with drawing enabled
        When: HTML is rendered twice
        Then: The CDN URL appears exactly once
        """
        # Arrange - Given
        m = Map().enable_draw()

        # Act - When
        _ = m.to_html()
        html = m.to_html()

        # Assert - Then
        assert html.count("leaflet.draw.css") == 1

    # --- 22. Disabled tools = false ---

    def test_disabled_tools_are_false(self, tmp_path: Path) -> None:
        """
        Scenario: Tools not in the list are set to false.

        Given: A map with only marker enabled
        When: HTML is saved to a file
        Then: polygon is set to false in the draw config
        """
        # Arrange - Given
        m = Map().enable_draw(tools=["marker"])
        out = tmp_path / "tools_map.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert '"polygon": false' in html

    # --- 23. edit=False ---

    def test_edit_false_disables_remove(self, tmp_path: Path) -> None:
        """
        Scenario: edit=False disables the remove control.

        Given: A map with drawing enabled and edit=False
        When: HTML is saved to a file
        Then: remove is set to false in the edit config
        """
        # Arrange - Given
        m = Map().enable_draw(edit=False)
        out = tmp_path / "edit_map.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert '"remove": false' in html

    # --- 24. Custom draw_style ---

    def test_custom_draw_style(self) -> None:
        """
        Scenario: Custom draw_style generates shapeOptions.

        Given: A map with a custom draw_style
        When: HTML is rendered
        Then: shapeOptions appears in the HTML
        """
        # Arrange - Given
        m = Map().enable_draw(draw_style={"color": "#ff0000", "weight": 5})

        # Act - When
        html = m.to_html()

        # Assert - Then
        assert "shapeOptions" in html
        assert "#ff0000" in html

    # --- 25. File output has draw ---

    def test_rawjs_repr(self) -> None:
        """
        Scenario: RawJS __repr__ shows a truncated preview of the JS.

        Given: A RawJS instance with a long JS string
        When: repr() is called
        Then: A string starting with RawJS( is returned, truncated at 50 chars
        """
        # Arrange - Given
        short_js = "alert(1)"
        long_js = "a" * 60

        # Act - When
        short_repr = repr(RawJS(short_js))
        long_repr = repr(RawJS(long_js))

        # Assert - Then
        assert short_repr == f"RawJS({short_js!r})"
        assert "..." in long_repr

    def test_file_output_contains_draw_control(self, tmp_path: Path) -> None:
        """
        Scenario: HTML saved to file includes the draw control.

        Given: A map with drawing enabled
        When: HTML is saved to a file
        Then: The file contains L.Control.Draw
        """
        # Arrange - Given
        m = Map().enable_draw()
        out = tmp_path / "draw_map.html"

        # Act - When
        m.to_html(str(out))

        # Assert - Then
        content = out.read_text(encoding="utf-8")
        assert "L.Control.Draw" in content

    # --- 26. edit=False suppresses entire toolbar ---

    def test_edit_false_disables_both_flags(self, tmp_path: Path) -> None:
        """
        Scenario: edit=False forces both edit and remove off (toolbar hidden).

        Given: A map with edit=False
        When: HTML is saved to a file
        Then: Both edit and remove flags appear as false in the serialized config
        """
        # Arrange - Given
        m = Map().enable_draw(edit=False)
        out = tmp_path / "no_edit_toolbar.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert '"edit": false' in html
        assert '"remove": false' in html

    def test_edit_true_enables_both_flags(self, tmp_path: Path) -> None:
        """
        Scenario: edit=True enables both edit and remove buttons.

        Given: A map with edit=True (default)
        When: HTML is saved to a file
        Then: Both edit and remove flags appear as true in the serialized config
        """
        # Arrange - Given
        m = Map().enable_draw(edit=True)
        out = tmp_path / "edit_on.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert '"edit": true' in html
        assert '"remove": true' in html

    # --- 27. draw_locale mutates L.drawLocal before Draw control ---

    def test_draw_locale_injects_mutation_before_draw_control(self, tmp_path: Path) -> None:
        """
        Scenario: draw_locale strings appear in HTML before L.Control.Draw.

        Given: A map with draw_locale overriding tooltip strings
        When: HTML is saved to a file
        Then: The L.drawLocal mutation appears, and it precedes the
              `new L.Control.Draw` constructor call
        """
        # Arrange - Given
        m = Map().enable_draw(
            draw_locale={
                "draw.toolbar.buttons.polyline": "Teken/bewerk lijn",
                "draw.handlers.polyline.tooltip.start": "Klik om te beginnen",
            }
        )
        out = tmp_path / "locale.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert "L.drawLocal.draw.toolbar.buttons.polyline" in html
        assert '"Teken/bewerk lijn"' in html
        assert "L.drawLocal.draw.handlers.polyline.tooltip.start" in html
        locale_idx = html.find("L.drawLocal.draw.toolbar.buttons.polyline")
        draw_ctor_idx = html.find("new L.Control.Draw")
        assert 0 <= locale_idx < draw_ctor_idx, "locale mutation must precede L.Control.Draw constructor"

    def test_draw_locale_is_in_body_not_head(self, tmp_path: Path) -> None:
        """
        Scenario: locale mutation lives in <body>, never in <head>.

        Given: A map with draw_locale set
        When: HTML is saved to a file
        Then: The L.drawLocal mutation appears between <body> and </body>,
              and NOT inside the <head> section (where leaflet.draw.js has
              not yet loaded when an inline <script> would run).
        """
        # Arrange - Given
        m = Map().enable_draw(draw_locale={"draw.toolbar.buttons.polyline": "X"})
        out = tmp_path / "locale_position.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        body_start = html.find("<body>")
        body_end = html.find("</body>")
        head_start = html.find("<head>")
        head_end = html.find("</head>")
        locale_idx = html.find("L.drawLocal.draw.toolbar.buttons.polyline")
        assert body_start < locale_idx < body_end, "locale must be inside <body>"
        assert not (head_start < locale_idx < head_end), "locale must NOT be inside <head>"

    # --- 28. enable_handles_on_create attaches draw:created listener ---

    def test_enable_handles_on_create_attaches_editing_listener(self, tmp_path: Path) -> None:
        """
        Scenario: enable_handles_on_create wires a draw:created → editing.enable listener.

        Given: A map with enable_handles_on_create=True
        When: HTML is saved to a file
        Then: A map.on('draw:created', ...) handler that calls
              layer.editing.enable() appears in the HTML
        """
        # Arrange - Given
        m = Map().enable_draw(enable_handles_on_create=True)
        out = tmp_path / "handles_on.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert "map.on('draw:created'" in html
        assert "layer.editing.enable()" in html

    def test_enable_handles_on_create_off_by_default(self, tmp_path: Path) -> None:
        """
        Scenario: enable_handles_on_create defaults to False — listener is absent.

        Given: A map with drawing enabled and no enable_handles_on_create
        When: HTML is saved to a file
        Then: layer.editing.enable() does NOT appear in the HTML
        """
        # Arrange - Given
        m = Map().enable_draw()
        out = tmp_path / "handles_off.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert "layer.editing.enable()" not in html

    # --- 29. Combined snapshot: all three flags active ---

    def test_combined_extensions_snapshot(self, tmp_path: Path) -> None:
        """
        Scenario: All three new flags emit the expected artefacts together.

        Given: A map with edit=False, draw_locale set, enable_handles_on_create=True
        When: HTML is saved to a file
        Then: edit_options forces both flags off, the L.drawLocal mutation
              appears before the Draw constructor, and the draw:created
              listener calling editing.enable is present
        """
        # Arrange - Given
        m = Map().enable_draw(
            edit=False,
            draw_locale={"draw.toolbar.buttons.polyline": "Teken/bewerk lijn"},
            enable_handles_on_create=True,
        )
        out = tmp_path / "combined.html"

        # Act - When
        m.to_html(str(out))
        html = out.read_text(encoding="utf-8")

        # Assert - Then
        assert '"edit": false' in html
        assert '"remove": false' in html

        locale_idx = html.find("L.drawLocal.draw.toolbar.buttons.polyline")
        draw_ctor_idx = html.find("new L.Control.Draw")
        assert 0 <= locale_idx < draw_ctor_idx

        assert "map.on('draw:created'" in html
        assert "layer.editing.enable()" in html
