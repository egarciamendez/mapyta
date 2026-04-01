# Open data — CBS & PDOK

The Netherlands publishes a wealth of geospatial open data. Two platforms cover most use cases:

| Platform | What it provides |
|----------|-----------------|
| [PDOK](https://www.pdok.nl/) | Authoritative Dutch geo-datasets via WFS/WMS — administrative boundaries (CBS gebiedsindelingen), buildings (BAG), topographic maps (BRT/BGT), and more |
| [CBS StatLine](https://opendata.cbs.nl/) | Statistics Netherlands open data — population, housing, economy — accessible via a REST API |

All examples below require only `geopandas` and `requests`, both available in any standard Python environment with mapyta installed.

---

## Provinciekaart

The PDOK CBS gebiedsindelingen service provides administrative boundary layers directly as GeoJSON. Fetching all 12 provinces takes a single call.

```python
import requests
import geopandas as gpd
from mapyta import Map

url = "https://service.pdok.nl/cbs/gebiedsindelingen/2024/wfs/v1_0"
r = requests.get(url, params={
    "service": "WFS",
    "version": "2.0.0",
    "request": "GetFeature",
    "typeNames": "gebiedsindelingen:provincie_gegeneraliseerd",
    "outputFormat": "application/json",
}, timeout=30)

gdf = gpd.GeoDataFrame.from_features(r.json()["features"], crs="EPSG:4326")

m = Map(title="Nederlandse provincies")
m = Map.from_geodataframe(
    gdf,
    hover_columns=["statnaam"],
    label_column="statnaam",
)
m.to_html("provincies.html")
```

The layer returns the following properties per feature:

| Column | Description |
|--------|-------------|
| `statcode` | CBS statistic code (e.g. `PV20`) |
| `statnaam` | Province name |
| `jrstatcode` | Year + statcode |
| `rubriek` | Feature category |

---

## Bevolkingsdichtheid per gemeente

CBS StatLine provides kerncijfers (key figures) per municipality. By joining these with PDOK municipality boundaries you can build a choropleth in a few lines.

```python
import json
import requests
import pandas as pd
import geopandas as gpd
from mapyta import Map

# 1. Municipality boundaries from PDOK
url = "https://service.pdok.nl/cbs/gebiedsindelingen/2024/wfs/v1_0"
r = requests.get(url, params={
    "service": "WFS",
    "version": "2.0.0",
    "request": "GetFeature",
    "typeNames": "gebiedsindelingen:gemeente_gegeneraliseerd",
    "outputFormat": "application/json",
}, timeout=30)
gdf = gpd.GeoDataFrame.from_features(r.json()["features"], crs="EPSG:4326")

# 2. Population density per municipality from CBS StatLine (table 70072ned)
r2 = requests.get(
    "https://opendata.cbs.nl/ODataApi/odata/70072ned/TypedDataSet",
    params={
        "$filter": "startswith(RegioS,'GM') and Perioden eq '2024JJ00'",
        "$select": "RegioS,Bevolkingsdichtheid_57,TotaleBevolking_1",
    },
    timeout=30,
)
stats = pd.DataFrame(r2.json()["value"])
stats["statcode"] = stats["RegioS"].str.strip()  # remove CBS padding spaces

# 3. Join and map
gdf = gdf.merge(
    stats[["statcode", "Bevolkingsdichtheid_57", "TotaleBevolking_1"]],
    on="statcode",
    how="left",
)
gdf = gdf.rename(columns={
    "Bevolkingsdichtheid_57": "inw_per_km2",
    "TotaleBevolking_1": "inwoners",
})

m = Map.from_geodataframe(
    gdf,
    color_column="inw_per_km2",
    hover_columns=["statnaam", "inw_per_km2", "inwoners"],
    title="Bevolkingsdichtheid per gemeente (2024)",
)
m.to_html("bevolkingsdichtheid.html")
```

!!! tip "CBS table IDs"
    CBS table `70072ned` covers *Kerncijfers wijken en buurten* (updated annually). The column `Bevolkingsdichtheid_57` is inhabitants per km². Browse all available tables at [opendata.cbs.nl](https://opendata.cbs.nl/statline/#/CBS/nl/).

### Other useful CBS columns

The same table contains hundreds of variables. A few useful ones:

| Column | Description |
|--------|-------------|
| `TotaleBevolking_1` | Total population |
| `Bevolkingsdichtheid_57` | Inhabitants per km² |
| `GemiddeldeWOZWaardeVanWoningen_98` | Average WOZ property value (€) |
| `TotaalBanen_116` | Total jobs |
| `Werkloosheid_159` | Unemployment benefit recipients |
| `AfstandTotTreinstation_238` | Average distance to train station (km) |

---

## Gebouwleeftijd in Amsterdam (BAG)

The PDOK BAG (Basisregistratie Adressen en Gebouwen) WFS provides building footprints and metadata for every registered building in the Netherlands. Because the dataset is large, always filter by a bounding box.

```python
import requests
import geopandas as gpd
from mapyta import Map

# Grachtengordel Amsterdam — RD New bounding box (EPSG:28992)
# Use srsName=EPSG:4326 so the returned geometries are already in WGS84
url = "https://service.pdok.nl/lv/bag/wfs/v2_0"
r = requests.get(url, params={
    "service": "WFS",
    "version": "2.0.0",
    "request": "GetFeature",
    "typeName": "bag:pand",
    "outputFormat": "application/json",
    "bbox": "119500,487000,121500,488500,EPSG:28992",
    "srsName": "EPSG:4326",
    "count": "500",
}, timeout=30)

gdf = gpd.GeoDataFrame.from_features(r.json()["features"], crs="EPSG:4326")

m = Map.from_geodataframe(
    gdf,
    color_column="bouwjaar",
    hover_columns=["bouwjaar", "gebruiksdoel", "status", "aantal_verblijfsobjecten"],
    title="Gebouwleeftijd — Amsterdam Grachtengordel",
)
m.to_html("bag_bouwjaar.html")
```

!!! tip "RD New bounding boxes"
    The BAG WFS expects bounding boxes in RD New (EPSG:28992). Use [epsg.io/transform](https://epsg.io/transform#s_srs=4326&t_srs=28992) to convert WGS84 coordinates. If you omit `srsName`, the returned geometries will also be in RD New — mapyta detects this automatically and reprojects them.

### BAG feature properties

| Column | Description |
|--------|-------------|
| `identificatie` | Unique BAG building ID |
| `bouwjaar` | Construction year |
| `status` | E.g. `Pand in gebruik`, `Pand gesloopt` |
| `gebruiksdoel` | Primary use: `woonfunctie`, `kantoorfunctie`, etc. |
| `oppervlakte_min` / `oppervlakte_max` | Floor area range (m²) |
| `aantal_verblijfsobjecten` | Number of address units in the building |

### Other BAG layers

The BAG WFS exposes more than just buildings:

| Layer | Description |
|-------|-------------|
| `bag:pand` | Building footprints |
| `bag:verblijfsobject` | Individual address objects (flats, offices, …) |
| `bag:woonplaats` | Place name boundaries |
| `bag:standplaats` | Permanent standplaatsen (caravan sites, etc.) |
| `bag:ligplaats` | Mooring locations for houseboats |

---

## Other useful PDOK datasets

PDOK hosts dozens of datasets beyond CBS and BAG. A selection relevant for mapping:

| Dataset | WFS base URL | Use case |
|---------|-------------|----------|
| BGT (topography) | `https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0` | Detailed topographic features |
| BRO (subsurface) | `https://publiek.broservices.nl/sr/cpt/v2/wfs` | Cone penetration test locations |
| NWB wegen | `https://service.pdok.nl/rws/nwb-wegen/wfs/v1_0` | Road network |
| Bestemmingsplannen | `https://service.pdok.nl/rvo/bestemmingsplannen/wfs/v1_0` | Zoning plans |
| CBS wijken & buurten | Same gebiedsindelingen URL, `typeNames=gebiedsindelingen:buurt_gegeneraliseerd` | Neighbourhood boundaries |
