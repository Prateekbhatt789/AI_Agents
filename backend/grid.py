import pandas as pd
import json
import os
from db.database import get_db_conn, release_db_conn
DB_SCHEMA = os.getenv("DB_SCHEMA", "data")

GRID_CELL_SIZE = 100


def get_empty_land_grids():
    conn = get_db_conn()

    try:
        cur = conn.cursor()

        # =========================================================
        # STEP 0 — CREATE FINAL TABLE (only once)
        # =========================================================
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.grids (
                id BIGSERIAL PRIMARY KEY,
                centroid GEOMETRY(Point, 4326) NOT NULL,
                grid_size INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                geom GEOMETRY(Polygon, 4326) NOT NULL
            );
        """)

        # Indexes (safe to run multiple times)
        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_grids_geom
            ON {DB_SCHEMA}.grids
            USING GIST (geom);
        """)

        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_grids_centroid
            ON {DB_SCHEMA}.grids
            USING GIST (centroid);
        """)

        conn.commit()

        # =========================================================
        # OPTIONAL: (avoid duplicates)
        # =========================================================
        
        # cur.execute(f"TRUNCATE TABLE {DB_SCHEMA}.grids;")
        conn.commit()

        # =========================================================
        # TEMP TABLE CLEANUP
        # =========================================================
        cur.execute("DROP TABLE IF EXISTS tmp_usable_land CASCADE;")
        cur.execute("DROP TABLE IF EXISTS tmp_grid CASCADE;")
        conn.commit()

        # =========================================================
        # STEP 1 — Find empty land
        # =========================================================
        cur.execute(f"""
            CREATE TEMP TABLE tmp_usable_land AS
            SELECT 
                ST_Difference(
                    (SELECT ST_Union(geom) FROM {DB_SCHEMA}.pincode_pop),
                    (SELECT ST_Union(geom)
                     FROM {DB_SCHEMA}.land_use_classification
                     WHERE "DN" IN (1,2,4,5,8,11))
                ) AS geom;
        """)
        conn.commit()

        # =========================================================
        # STEP 2 — Create grid
        # =========================================================
        cur.execute(f"""
            CREATE TEMP TABLE tmp_grid AS
            SELECT ST_Transform(grid.geom, 4326) AS cell
            FROM (
                SELECT (ST_SquareGrid(
                    {GRID_CELL_SIZE},
                    ST_Transform((SELECT geom FROM tmp_usable_land), 3857)
                )).geom
            ) AS grid;
        """)

        # =========================================================
        # STEP 3 — INSERT INTO FINAL TABLE (CENTROID LOGIC)
        # =========================================================
        cur.execute(f"""
            INSERT INTO {DB_SCHEMA}.grids ( centroid, grid_size,geom)
            SELECT 
                
                ST_Centroid(g.cell),
                %s,
                g.cell
            FROM tmp_grid g
            WHERE ST_Contains(
                (SELECT geom FROM tmp_usable_land),
                ST_Centroid(g.cell)
            );
        """, (GRID_CELL_SIZE,))
        conn.commit()

        # =========================================================
        # STEP 4 — FETCH FOR KML (optional, same as before)
        # =========================================================
        cur.execute(f"""
            SELECT ST_AsGeoJSON(geom) AS geometry
            FROM {DB_SCHEMA}.grids;
        """)

        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columns)

        print(f"Total grids stored & fetched: {len(df)}")

        return df

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error: {e}")
    finally:
        release_db_conn(conn)


# =========================================================
# KML FUNCTION (UNCHANGED)
# =========================================================
def create_kml(df, output_file="empty_land_grids1.kml"):

    if df.empty:
        print("No data found. KML not created.")
        return

    print("Creating KML file...")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
""")

        count = 0

        for i, row in df.iterrows():
            try:
                geojson_geom = json.loads(row["geometry"])

                if geojson_geom["type"] == "Polygon":
                    polygons = [geojson_geom["coordinates"]]
                elif geojson_geom["type"] == "MultiPolygon":
                    polygons = geojson_geom["coordinates"]
                else:
                    continue

                for polygon in polygons:
                    outer_ring = polygon[0]

                    coord_str = " ".join(
                        [f"{lon},{lat},0" for lon, lat in outer_ring]
                    )

                    f.write(f"""
<Placemark>
    <name>Grid {i}</name>
    <Style>
        <LineStyle>
            <color>ff0000ff</color>
            <width>1</width>
        </LineStyle>
        <PolyStyle>
            <color>7d00ff00</color>
        </PolyStyle>
    </Style>
    <Polygon>
        <outerBoundaryIs>
            <LinearRing>
                <coordinates>{coord_str}</coordinates>
            </LinearRing>
        </outerBoundaryIs>
    </Polygon>
</Placemark>
""")
                    count += 1

            except Exception as e:
                print(f"Skipping row {i} due to error: {e}")

        f.write("""
</Document>
</kml>
""")

    print(f"✅ KML file created successfully: {output_file}")
    print(f"Total polygons written: {count}")


if __name__ == "__main__":
    df = get_empty_land_grids()
    print(df.head())

    create_kml(df)









