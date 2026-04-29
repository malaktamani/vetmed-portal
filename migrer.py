import psycopg2

# Ancienne base Railway (URL publique)
OLD_DB = "postgresql://postgres:zehxzgpFxUSsiqqbTAtAozgxnVROAQdW@shortline.proxy.rlwy.net:50831/railway"

# Nouvelle base Render (URL interne, utilisée depuis Render)
NEW_DB = "postgresql://vetmed_db_5xf0_user:sZVrrKLnMYzQDHNs5w1FN8AHeCxadt4S@dpg-d7p3jlpj2pic73f1eog0-a:5432/vetmed_db_5xf0"

try:
    old = psycopg2.connect(OLD_DB)
    new = psycopg2.connect(NEW_DB)
    print("✅ Connecté aux deux bases")
except Exception as e:
    print("❌ Erreur de connexion :", e)
    exit()

tables = ['utilisateur', 'fichier', 'favori', 'consultation']

for table in tables:
    try:
        cur_old = old.cursor()
        cur_new = new.cursor()
        cur_old.execute(f"SELECT * FROM {table}")
        rows = cur_old.fetchall()
        if not rows:
            print(f"📭 {table} : aucune ligne à migrer.")
            continue
        cols = [desc[0] for desc in cur_old.description]
        for row in rows:
            placeholders = ', '.join(['%s'] * len(row))
            cur_new.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING", row)
        new.commit()
        print(f"✅ {table} : {len(rows)} lignes migrées.")
    except Exception as e:
        print(f"⚠️ {table} : {e}")
        new.rollback()

old.close()
new.close()
print("🎉 Migration terminée !")