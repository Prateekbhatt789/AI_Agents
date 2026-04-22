from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from db.session import get_db
from sqlalchemy import text
router = APIRouter()

@router.get('/dashboard')
def fetch_category_list(db: Session = Depends(get_db)):
    # Use double quotes for exact case matching
    query = text('SELECT table_name as key,description as label,svg_icon as icon FROM data.master')

    try:
        result = db.execute(query)
        rows = result.fetchall()

        return {
            "data": [
                {"key": row[0], "label": row[1], "icon": row[2]} 
                for row in rows
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@router.get('/subcategory')
def fetch_category_list(
    table_names: list[str] = Query(...), 
    db: Session = Depends(get_db)
):
    response = {}
    table_names = table_names[::-1]
    try:
        for table in table_names:
            if not table.isidentifier():
                response[table] = {"error": "Invalid table name"}
                continue

            query = text(f'''
                SELECT sub_category, COUNT(*) 
                FROM data."{table}"
                GROUP BY sub_category 
                ORDER BY sub_category
            ''')

            result = db.execute(query)
            rows = result.fetchall()

            response[table] = [
                {"key": row[0], "value": row[1]}
                for row in rows
            ]

        return response

    except Exception as e:
        return {"error": str(e)}