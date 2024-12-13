from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

def connect_db_precios():
    password = quote_plus(".Pikachu12345.")  # Escapar caracteres especiales
    connection_string = f"postgresql://postgres:{password}@localhost:5432/PreciosClaros"
    engine = create_engine(connection_string)
    return engine

def connect_db_recetas():
    password = quote_plus(".Pikachu12345.")  # Escapar caracteres especiales
    connection_string = f"postgresql://postgres:{password}@localhost:5432/Recetas_Cocineros"
    engine = create_engine(connection_string)
    return engine

# --- Funciones para la base de datos de PreciosClaros ---

def setup_database_precios():
    engine = connect_db_precios()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255) UNIQUE,
                precio_min NUMERIC,
                precio_max NUMERIC
            )
        """))
        conn.commit()

def insert_product(nombre, precio_min, precio_max):
    engine = connect_db_precios()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO productos (nombre, precio_min, precio_max)
            VALUES (:nombre, :precio_min, :precio_max)
            ON CONFLICT (nombre) DO NOTHING
        """), {"nombre": nombre, "precio_min": precio_min, "precio_max": precio_max})
        conn.commit()

def clear_table_precios():
    engine = connect_db_precios()
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM productos"))
        conn.commit()

# --- Funciones para la base de datos de Recetas_Cocineros ---

def setup_database_recetas():
    engine = connect_db_recetas()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recetas (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255) UNIQUE,
                ingredientes TEXT,
                procedimiento TEXT
            )
        """))
        conn.commit()

def insert_receta(nombre, ingredientes, procedimiento):
    engine = connect_db_recetas()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO recetas (nombre, ingredientes, procedimiento)
            VALUES (:nombre, :ingredientes, :procedimiento)
            ON CONFLICT (nombre) DO NOTHING
        """), {"nombre": nombre, "ingredientes": ingredientes, "procedimiento": procedimiento})
        conn.commit()

def clear_recetas_table():
    engine = connect_db_recetas()
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM recetas"))
        conn.commit()
