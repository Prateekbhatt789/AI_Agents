from sqlalchemy import text
from db.database import SessionLocal


def fetch_pois(lat: float, lon: float, radius_km: float):

    db = SessionLocal()

    try:
        radius_m = radius_km * 1000

        #  Step 1: Fetch full grid data (NOT just id)
        grid_query = text("""
            SELECT 
                id,
                ST_Y(centroid) AS centroid_lat,
                ST_X(centroid) AS centroid_lon,
                population_per_grid,
                ST_AsGeoJSON(geom) AS geom
            FROM data.grids
            WHERE ST_DWithin(
                geography(centroid),
                geography(ST_MakePoint(:lon, :lat)),
                :radius
            )
        """)

        grid_result = db.execute(grid_query, {
            "lat": lat,
            "lon": lon,
            "radius": radius_m
        })

        grid_rows = grid_result.fetchall()

        #  Build grid response
        grids = [
            {
                "grid_id": row[0],
                "lat": row[1],
                "lon": row[2],
                "population": row[3],
                "geom":row[4]
            }
            for row in grid_rows
        ]

        grid_ids = [row[0] for row in grid_rows]

        # print("grid ids:", grid_ids)

        if not grid_ids:
            return {
                "grids": [],
                "pois": {},
                "summary": {}
            }

        params = {"grid_ids": grid_ids}

        #  POI queries
        queries = {
            "Building": """
                SELECT name, sub_category, lat, lon FROM data.building
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Business": """
                SELECT name, sub_category, lat, lon FROM data.business
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Finance": """
                SELECT name, sub_category, lat, lon FROM data.finance
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Food": """
                SELECT name, sub_category, lat, lon FROM data.food
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Health Care": """
                SELECT name, sub_category, lat, lon FROM data.health_care
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Infrastructure": """
                SELECT name, sub_category, lat, lon FROM data.infra_str
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Tourism": """
                SELECT name, sub_category, lat, lon FROM data.tourism
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Transport": """
                SELECT name, sub_category, lat, lon FROM data.transport
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Recreation": """
                SELECT name, sub_category, lat, lon FROM data.recreation
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Shops": """
                SELECT name, sub_category, lat, lon FROM data.shops
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Education": """
                SELECT name, sub_category, lat, lon FROM data.education
                WHERE grid_id = ANY(:grid_ids)
            """,
            "Religious": """
                SELECT name, sub_category, lat, lon FROM data.religious
                WHERE grid_id = ANY(:grid_ids)
            """
        }

        pois = {}
        summary = {}

        #  Execute POI queries
        for key, query in queries.items():
            result = db.execute(text(query), params)
            rows = result.fetchall()

            pois[key] = [
                {
                    "name": row[0],
                    "sub_category": row[1],
                    "lat": row[2],
                    "lon": row[3]
                }
                for row in rows
            ]

            summary[key] = len(rows)

        #  Final response structure
        response = {
            "grids": grids,
            "pois": pois,
            "summary": summary
        }

        return response

    except Exception as e:
        return {"error": str(e)}

    finally:
        db.close()








