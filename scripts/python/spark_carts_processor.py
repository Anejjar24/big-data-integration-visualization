from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode, date_format
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType, TimestampType
import os

# Installation de psycopg2 si nécessaire pour gérer les doublons plus efficacement
try:
    import psycopg2
except ImportError:
    os.system("pip install psycopg2-binary")
    import psycopg2

# Définition du schéma pour les paniers
cart_schema = StructType([
    StructField("id", IntegerType()),
    StructField("userId", IntegerType()),
    StructField("date", StringType()),  # Format ISO string, sera converti en TimestampType
    StructField("products", ArrayType(
        StructType([
            StructField("productId", IntegerType()),
            StructField("quantity", IntegerType())
        ])
    )),
    StructField("source", StringType())  # Champ pour la source des données
])

def create_spark_session():
    """Crée et retourne une session Spark"""
    # IMPORTANT: Utilisation du mode local [*] pour contourner les problèmes de cluster
    return SparkSession.builder \
        .appName("FakestoreCartsProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,org.postgresql:postgresql:42.3.1") \
        .config("spark.sql.shuffle.partitions", "2") \
        .master("local[*]") \
        .getOrCreate()


def process_carts(spark):
    """Traitement des données de carts"""
    # Lecture du flux Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "fakestore-carts") \
        .option("startingOffsets", "earliest") \
        .load()
        
    # Décodage des valeurs JSON
    parsed_df = df.select(
        col("timestamp").alias("kafka_timestamp"),
        from_json(col("value").cast("string"), cart_schema).alias("data")
    ).select("kafka_timestamp", "data.*")
        
    # Conversion de la chaîne date en timestamp
    parsed_df = parsed_df.withColumn("date", col("date").cast(TimestampType()))
        
    # Explosion des produits pour avoir une ligne par produit dans le panier
    exploded_df = parsed_df.select(
        col("id").alias("cart_id"),
        col("userId"),
        col("date"),
        explode(col("products")).alias("product_detail"),
        col("source")
    )
        
    # Extraction des détails de produit
    carts_df = exploded_df.select(
        col("cart_id"),
        col("userId"),
        col("date"),
        col("product_detail.productId").alias("product_id"),
        col("product_detail.quantity"),
        col("source")
    )
        
    # Ajout de colonnes calculées
    transformed_df = carts_df \
        .withColumn("day_of_week", date_format(col("date"), "EEEE")) \
        .withColumn("month", date_format(col("date"), "MMMM"))
        
    # Écriture dans PostgreSQL
    query = transformed_df \
        .writeStream \
        .foreachBatch(write_to_postgres) \
        .outputMode("update") \
        .start()
        
    query.awaitTermination()

def write_to_postgres(batch_df, batch_id):
    """Écrit un batch de données dans PostgreSQL en gérant les doublons"""
    from psycopg2.extras import execute_values
    
    # Supprimer les doublons d'ID dans le DataFrame d'entrée
    batch_df_distinct = batch_df.dropDuplicates(["cart_id", "product_id"])
    
    # Si aucune donnée à écrire, sortir
    if batch_df_distinct.count() == 0:
        print(f"Batch {batch_id}: Aucune donnée à écrire")
        return
    
    # Récupérer les données sous forme de liste de tuples
    rows = batch_df_distinct.collect()
    data = [(
        row.cart_id, 
        row.userId, 
        row.date, 
        row.product_id, 
        row.quantity, 
        row.day_of_week, 
        row.month, 
        row.source
    ) for row in rows]
    
    # Définir les paramètres de connexion
    conn_params = {
        "dbname": "data_fakestore_db",
        "user": "postgres_user",
        "password": "postgres_password",
        "host": "postgres",
        "port": 5432
    }
    
    # Connexion à PostgreSQL et écriture des données
    try:
        # Créer une connexion à PostgreSQL
        conn = psycopg2.connect(**conn_params)
        
        # Créer un curseur
        cur = conn.cursor()
        
        # Requête d'upsert utilisant ON CONFLICT
        query = """
        INSERT INTO cart_items (cart_id, userId, date, product_id, quantity, day_of_week, month, source)
        VALUES %s
        ON CONFLICT (cart_id, product_id) DO UPDATE SET
            userId = EXCLUDED.userId,
            date = EXCLUDED.date,
            quantity = EXCLUDED.quantity,
            day_of_week = EXCLUDED.day_of_week,
            month = EXCLUDED.month,
            source = EXCLUDED.source
        """
        
        # Définition des templates de colonnes pour execute_values
        template = "(%(cart_id)s, %(userId)s, %(date)s, %(product_id)s, %(quantity)s, %(day_of_week)s, %(month)s, %(source)s)"
        
        # Convertir les tuples en dictionnaires pour execute_values
        data_dicts = [
            {
                'cart_id': d[0],
                'userId': d[1],
                'date': d[2],
                'product_id': d[3],
                'quantity': d[4],
                'day_of_week': d[5],
                'month': d[6],
                'source': d[7]
            } for d in data
        ]
        
        # Exécuter l'insertion par lots
        execute_values(cur, query, data_dicts, template=template, page_size=100)
        
        # Valider la transaction
        conn.commit()
        
        print(f"Batch {batch_id}: {len(data)} enregistrements traités avec succès")
        
    except Exception as e:
        print(f"Erreur lors du traitement du batch {batch_id}: {str(e)}")
        # Fermer proprement en cas d'erreur
        if 'conn' in locals() and conn:
            conn.rollback()
        raise e
        
    finally:
        # Fermer la connexion dans tous les cas
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    spark = create_spark_session()
    process_carts(spark)