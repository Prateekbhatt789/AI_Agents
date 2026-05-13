# from sqlalchemy import text
# from db.database import SessionLocal


# def fetch_pois(lat: float, lon: float, radius_km: float):

#     db = SessionLocal()

#     try:
#         radius_m = radius_km * 1000

#         #  Step 1: Fetch full grid data (NOT just id)
#         grid_query = text("""
#     SELECT 
#         g.id,
#         ST_Y(g.centroid) AS centroid_lat,
#         ST_X(g.centroid) AS centroid_lon,
#         g.population_per_grid,
#         ST_AsGeoJSON(g.geom) AS geom,
#         COALESCE(grm.primary_length, 0)     AS primary_length,
#         COALESCE(grm.secondary_length, 0)   AS secondary_length,
#         COALESCE(grm.total_road_length, 0)  AS total_road_length,
#         COALESCE(grm.road_density, 0)       AS road_density,
#         grm.dist_to_primary,
#         grm.dist_to_secondary,
#         grm.nearest_primary_road_id,
#         grm.nearest_secondary_road_id
#     FROM data.grids g
#     LEFT JOIN data.grid_road_metrics grm ON grm.grid_id = g.id
#     WHERE ST_DWithin(
#         geography(g.centroid),
#         geography(ST_MakePoint(:lon, :lat)),
#         :radius
#     )
# """)

#         grid_result = db.execute(grid_query, {
#             "lat": lat,
#             "lon": lon,
#             "radius": radius_m
#         })

#         grid_rows = grid_result.fetchall()

#         #  Build grid response
#         grids = [
#     {
#         "grid_id":                    row[0],
#         "lat":                        row[1],
#         "lon":                        row[2],
#         "population":                 row[3],
#         "geom":                       row[4],
#         "primary_length":             row[5],
#         "secondary_length":           row[6],
#         "total_road_length":          row[7],
#         "road_density":               row[8],
#         "dist_to_primary":            row[9],
#         "dist_to_secondary":          row[10],
#         "nearest_primary_road_id":    row[11],
#         "nearest_secondary_road_id":  row[12],
#     }
#     for row in grid_rows

#         ]

#         grid_ids = [row[0] for row in grid_rows]

#         # print("grid ids:", grid_ids)

#         if not grid_ids:
#             return {
#                 "grids": [],
#                 "pois": {},
#                 "summary": {}
#             }

#         params = {"grid_ids": grid_ids}

#         #  POI queries
#         queries = {
#             "Building": """
#                 SELECT name, sub_category, lat, lon FROM data.building
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Business": """
#                 SELECT name, sub_category, lat, lon FROM data.business
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Finance": """
#                 SELECT name, sub_category, lat, lon FROM data.finance
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Food": """
#                 SELECT name, sub_category, lat, lon FROM data.food
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Health Care": """
#                 SELECT name, sub_category, lat, lon FROM data.health_care
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Infrastructure": """
#                 SELECT name, sub_category, lat, lon FROM data.infra_str
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Tourism": """
#                 SELECT name, sub_category, lat, lon FROM data.tourism
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Transport": """
#                 SELECT name, sub_category, lat, lon FROM data.transport
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Recreation": """
#                 SELECT name, sub_category, lat, lon FROM data.recreation
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Shops": """
#                 SELECT name, sub_category, lat, lon FROM data.shops
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Education": """
#                 SELECT name, sub_category, lat, lon FROM data.education
#                 WHERE grid_id = ANY(:grid_ids)
#             """,
#             "Religious": """
#                 SELECT name, sub_category, lat, lon FROM data.religious
#                 WHERE grid_id = ANY(:grid_ids)
#             """
#         }

#         pois = {}
#         summary = {}

#         #  Execute POI queries
#         for key, query in queries.items():
#             result = db.execute(text(query), params)
#             rows = result.fetchall()

#             pois[key] = [
#                 {
#                     "name": row[0],
#                     "sub_category": row[1],
#                     "lat": row[2],
#                     "lon": row[3]
#                 }
#                 for row in rows
#             ]

#             summary[key] = len(rows)

#         #  Final response structure
#         response = {
#             "grids": grids,
#             "pois": pois,
#             "summary": summary
#         }

#         return response

#     except Exception as e:
#         return {"error": str(e)}

#     finally:
#         db.close()






from sqlalchemy import text
from db.database import SessionLocal


def _compute_road_summary(grids: list) -> dict:
    total_grids          = len(grids)
    grids_with_road      = sum(1 for g in grids if (g.get("total_road_length") or 0) > 0)
    grids_with_primary   = sum(1 for g in grids if (g.get("primary_length")    or 0) > 0)
    grids_with_secondary = sum(1 for g in grids if (g.get("secondary_length")  or 0) > 0)
    avg_density          = (
        sum(g.get("road_density") or 0 for g in grids) / total_grids
        if total_grids > 0 else 0
    )
    return {
        "total_grids":              total_grids,
        "grids_with_road":          grids_with_road,
        "primary_coverage_pct":     round(grids_with_primary   / total_grids * 100, 1) if total_grids else 0,
        "secondary_coverage_pct":   round(grids_with_secondary / total_grids * 100, 1) if total_grids else 0,
        "avg_road_density":         round(avg_density, 1),
    }


def fetch_pois(lat: float, lon: float, radius_km: float):

    db = SessionLocal()

    try:
        radius_m = radius_km * 1000

        grid_query = text("""
            SELECT 
                g.id,
                ST_Y(g.centroid) AS centroid_lat,
                ST_X(g.centroid) AS centroid_lon,
                g.population_per_grid,
                ST_AsGeoJSON(g.geom) AS geom,
                COALESCE(grm.primary_length, 0)     AS primary_length,
                COALESCE(grm.secondary_length, 0)   AS secondary_length,
                COALESCE(grm.total_road_length, 0)  AS total_road_length,
                COALESCE(grm.road_density, 0)       AS road_density,
                grm.dist_to_primary,
                grm.dist_to_secondary,
                grm.nearest_primary_road_id,
                grm.nearest_secondary_road_id
            FROM data.grids g
            LEFT JOIN data.grid_road_metrics grm ON grm.grid_id = g.id
            WHERE ST_DWithin(
                geography(g.centroid),
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

        grids = [
            {
                "grid_id":                   row[0],
                "lat":                       row[1],
                "lon":                       row[2],
                "population":                row[3],
                "geom":                      row[4],
                "primary_length":            row[5],
                "secondary_length":          row[6],
                "total_road_length":         row[7],
                "road_density":              row[8],
                "dist_to_primary":           row[9],
                "dist_to_secondary":         row[10],
                "nearest_primary_road_id":   row[11],
                "nearest_secondary_road_id": row[12],
            }
            for row in grid_rows
        ]

        grid_ids = [row[0] for row in grid_rows]

        if not grid_ids:
            return {
                "grids":        [],
                "pois":         {},
                "summary":      {},
                "road_summary": {},
            }

        params = {"grid_ids": grid_ids}

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

        pois    = {}
        summary = {}

        for key, query in queries.items():
            result = db.execute(text(query), params)
            rows   = result.fetchall()

            pois[key]    = [
                {
                    "name":         row[0],
                    "sub_category": row[1],
                    "lat":          row[2],
                    "lon":          row[3],
                }
                for row in rows
            ]
            summary[key] = len(rows)

        # Compute road summary from grids — no extra DB call needed
        road_summary = _compute_road_summary(grids)

        return {
            "grids":        grids,
            "pois":         pois,
            "summary":      summary,
            "road_summary": road_summary,   # ← new key
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        db.close()

