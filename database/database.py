import psycopg2

def connect_db():
    return psycopg2.connect(
        host="200.115.220.122",  # Cambia esto a la IP de tu servidor remoto
        database="nombre_de_la_base_de_datos",
        user="tu_usuario",
        password="tu_contraseña",
        port=5432  # Asegúrate de especificar el puerto si es necesario (5432 es el predeterminado)
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
