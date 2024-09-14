import psycopg2

def connect_db():
    return psycopg2.connect(
        host="localhost",  #"200.115.220.122"
        database="Precios_Claros",
        user="postgres",
        password=".Pikachu12345.",
        port=5432
    )

def setup_database():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255),
            precio NUMERIC,
            tienda VARCHAR(255)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def insert_product(nombre, precio):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO productos (nombre, precio) VALUES (%s, %s)", (nombre, precio))
    conn.commit()
    cur.close()
    conn.close()
