import psycopg2

def connect_db():
    return psycopg2.connect(
        host="192.168.0.154",
        database="PreciosClaros",
        user="postgres",
        password=".Pikachu12345.",
        port=5432
    )

def setup_database():
    conn = connect_db()
    cur = conn.cursor()
    # Crear tabla si no existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) UNIQUE,
            precio_min NUMERIC,
            precio_max NUMERIC
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def insert_product(nombre, precio_min, precio_max):
    conn = connect_db()
    cur = conn.cursor()
    # Insertar sin manejar conflictos
    cur.execute("""
        INSERT INTO productos (nombre, precio_min, precio_max)
        VALUES (%s, %s, %s);
    """, (nombre, precio_min, precio_max))
    conn.commit()
    cur.close()
    conn.close()

def clear_table():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM productos;")
    conn.commit()
    cur.close()
    conn.close()