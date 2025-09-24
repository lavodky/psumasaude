from __future__ import annotations
import json
from typing import Optional, Tuple
import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json
from . import config

POOL: Optional[pool.SimpleConnectionPool] = None

def get_pool() -> pool.SimpleConnectionPool:
    """
    Cria (uma vez) e retorna o pool de conexões.
    Garante schema ao inicializar.
    """
    global POOL
    if POOL is None:
        POOL = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASS
        )
        init_db()
    return POOL

def db_conn():
    return get_pool().getconn()

def db_put(conn):
    get_pool().putconn(conn)

def init_db():
    conn = get_pool().getconn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                patient_name TEXT,
                sex TEXT,
                age_years INTEGER NOT NULL,
                data JSONB NOT NULL
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS ref_ranges (
                id SERIAL PRIMARY KEY,
                analyte TEXT NOT NULL,
                unit TEXT,
                age_min INT,
                age_max INT,
                sex TEXT,
                ref_low DOUBLE PRECISION,
                ref_high DOUBLE PRECISION
            );
            """)
        seed_reference_ranges(conn)
    finally:
        db_put(conn)

def seed_reference_ranges(conn):
    with conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM ref_ranges;")
        count = cur.fetchone()[0]
        if count and count > 0:
            return
        refs = [
            # analyte, unit, age_min, age_max, sex, low, high
            ("GLU", "mg/dL", 18, 110, None, 70, 99),
            ("URE", "mg/dL", 18, 110, None, 15, 50),
            ("CRE", "mg/dL", 18, 110, None, 0.6, 1.2),
            ("PCR", "mg/dL", 18, 110, None, 0.0, 0.5),
            ("CA", "mg/dL", 18, 110, None, 8.6, 10.0),
            ("P", "mg/dL", 18, 110, None, 2.7, 4.5),
            ("AST", "U/L", 18, 110, None, 10, 40),
            ("ALT", "U/L", 18, 110, None, 7, 55),
            ("ALP", "U/L", 18, 110, None, 46, 116),
            ("GGT", "U/L", 18, 110, None, 1, 38),
            ("AML", "U/L", 18, 110, None, 20, 104),
            ("FE", "µg/dL", 18, 110, None, 60, 170),
            ("TIBC", "µg/dL", 18, 110, None, 250, 400),
            ("TRF", "µg/dL", 18, 110, None, 155, 355),
            ("CT", "mg/dL", 18, 110, None, 0, 190),
            ("TG", "mg/dL", 18, 110, None, 0, 150),
            ("HDL", "mg/dL", 18, 110, None, 40, 200),
            ("VLDL", "mg/dL", 18, 110, None, 5, 40),
            ("LDL", "mg/dL", 18, 110, None, 0, 130),
            ("ALB", "g/dL", 18, 110, None, 3.4, 4.8),
            ("PT", "g/dL", 18, 110, None, 6.4, 8.3),
            ("A_G", "razão", 18, 110, None, 0.8, 2.2),
            ("ALB_PCT", "%", 18, 110, None, 55.8, 66.1),
            ("A1", "%", 18, 110, None, 2.9, 4.9),
            ("A2", "%", 18, 110, None, 7.1, 11.8),
            ("B1", "%", 18, 110, None, 4.9, 7.2),
            ("B2", "%", 18, 110, None, 3.1, 6.1),
            ("GAMMA", "%", 18, 110, None, 11.1, 18.8),
            ("HBA1C", "%", 18, 110, None, 4.5, 5.6),
            ("RBC", "10^6/mm3", 18, 110, None, 4.5, 6.0),
            ("HGB", "g/dL", 18, 110, None, 13.0, 17.0),
            ("HCT", "%", 18, 110, None, 40.0, 50.0),
            ("MCV", "fL", 18, 110, None, 82, 98),
            ("MCH", "pg", 18, 110, None, 27, 32),
            ("MCHC", "g/dL", 18, 110, None, 32, 36),
            ("RDW", "%", 18, 110, None, 10, 15),
            ("WBC", "/mm3", 18, 110, None, 4000, 10000),
            ("BAND", "%", 18, 110, None, 0, 4),
            ("SEG", "%", 18, 110, None, 40, 65),
            ("EOS", "%", 18, 110, None, 1, 5),
            ("BASO", "%", 18, 110, None, 0, 1),
            ("LYMPH", "%", 18, 110, None, 20, 40),
            ("LYMPH_ATYP", "%", 18, 110, None, 0, 1),
            ("MONO", "%", 18, 110, None, 2, 12),
            ("PLT", "/mm3", 18, 110, None, 150000, 450000),
            ("MPV", "fL", 18, 110, None, 9.2, 12.6),
            ("E2", "pg/mL", 18, 110, None, 0, 40),
            ("FSH", "mUI/mL", 18, 110, None, 1.4, 18.1),
            ("INS", "µUI/mL", 18, 110, None, 2.0, 20.0),
            ("HOMA_IR", "índice", 18, 110, None, 0.0, 3.4),
            ("LH", "mUI/mL", 18, 110, None, 1.5, 9.3),
            ("PTH", "pg/mL", 18, 110, None, 12, 65),
            ("PROG", "ng/mL", 18, 110, None, 0.28, 1.22),
            ("PRL", "ng/mL", 18, 110, None, 2.1, 17.7),
            ("TESTO", "ng/dL", 18, 110, None, 300, 1000),
            ("TSH", "µUI/mL", 18, 110, None, 0.55, 4.78),
            ("FT4", "ng/dL", 18, 110, None, 0.70, 1.76),
            ("FOLATE", "ng/mL", 18, 110, None, 3.0, 17.0),
            ("ANTI_TPO", "UI/mL", 18, 110, None, 0, 60),
            ("ANTI_TG", "UI/mL", 18, 110, None, 0, 4.5),
            ("CA15_3", "U/mL", 18, 110, None, 0, 38),
            ("CA19_9", "U/mL", 18, 110, None, 0, 37),
            ("FER", "ng/mL", 18, 110, None, 22, 322),
            ("B12", "pg/mL", 18, 110, None, 193, 982),
            ("VITD", "ng/mL", 18, 110, None, 30, 100),
            ("CEA", "ng/mL", 18, 110, None, 0, 2.5),
            ("CA125", "U/mL", 18, 110, None, 0, 30.2),
            ("CORT", "µg/dL", 18, 110, None, 5.27, 22.45),
            ("C_PEP", "ng/mL", 18, 110, None, 1.10, 4.40),
            ("SHBG", "nmol/L", 18, 110, None, 10, 57),
            ("TESTO_FREE", "ng/dL", 18, 110, None, 3.0, 25.0),
            ("RT3", "ng/dL", 18, 110, None, 31, 95),
        ]
        cur.executemany("""
            INSERT INTO ref_ranges (analyte, unit, age_min, age_max, sex, ref_low, ref_high)
            VALUES (%s,%s,%s,%s,%s,%s,%s);
        """, refs)

def find_ref(analyte: str, age: int, sex: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    conn = db_conn()
    try:
        with conn, conn.cursor() as cur:
            if sex:
                cur.execute("""
                    SELECT ref_low, ref_high, unit FROM ref_ranges
                    WHERE analyte=%s AND age_min<=%s AND age_max>=%s AND (sex=%s)
                    ORDER BY age_min DESC LIMIT 1
                """, (analyte, age, age, (sex or "").upper()))
                row = cur.fetchone()
                if row:
                    return row[0], row[1], row[2]
            cur.execute("""
                SELECT ref_low, ref_high, unit FROM ref_ranges
                WHERE analyte=%s AND age_min<=%s AND age_max>=%s AND sex IS NULL
                ORDER BY age_min DESC LIMIT 1
            """, (analyte, age, age))
            row = cur.fetchone()
            if row:
                return row[0], row[1], row[2]
            return None, None, None
    finally:
        db_put(conn)
