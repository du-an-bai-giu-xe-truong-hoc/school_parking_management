import psycopg2

conn = psycopg2.connect("postgresql://postgres:abc@localhost:5432/school_parking_management")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name ILIKE 'lichsuvaora'")
cols = cur.fetchall()
print("lichsuvaora columns:", cols)

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = cur.fetchall()
print("all tables:", tables)
