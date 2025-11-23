from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when, lit
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, ArrayType
# Au début du script
import os

# Installation de psycopg2 si ce n'est pas déjà fait
try:
    import psycopg2
except ImportError:
    os.system("pip install psycopg2-binary")
    import psycopg2

# Définition du schéma pour les produits (mis à jour avec le champ source)
product_schema = StructType([
    StructField("id", IntegerType()),
    StructField("title", StringType()),
    StructField("price", DoubleType()),
    StructField("description", StringType()),
    StructField("category", StringType()),
    StructField("image", StringType()),
    StructField("rating", StructType([
        StructField("rate", DoubleType()),
        StructField("count", IntegerType())
    ])),
    StructField("source", StringType())  # Nouveau champ pour la source des données
])

def create_spark_session():
    """Crée et retourne une session Spark"""
    return SparkSession.builder \
        .appName("FakestoreProductsProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,org.postgresql:postgresql:42.3.1") \
        .config("spark.sql.shuffle.partitions", "2") \
        .master("spark://spark-master:7077") \
        .getOrCreate()

def process_products(spark):
    """Traitement des données de products"""
    # Lecture du flux Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "fakestore-products") \
        .option("startingOffsets", "earliest") \
        .load()
        
    # Décodage des valeurs JSON
    parsed_df = df.select(
        col("timestamp").alias("kafka_timestamp"),
        from_json(col("value").cast("string"), product_schema).alias("data")
    ).select("kafka_timestamp", "data.*")
        
    # Transformation des données
    transformed_df = parsed_df.withColumn(
        "price_category", 
        when(col("price") < 50, "économique")
        .when(col("price") < 100, "moyen")
        .otherwise("premium")
    )
        
    # Extraction des ratings dans une colonne séparée
    ratings_df = transformed_df.select(
        col("id"),
        col("title"),
        col("price"),
        col("category"),
        col("rating.rate").alias("rating_value"),
        col("rating.count").alias("rating_count"),
        col("price_category"),
        col("source")  # Inclure la source dans les données traitées
    )
        
    # Écriture dans PostgreSQL
    query = ratings_df \
        .writeStream \
        .foreachBatch(write_to_postgres) \
        .outputMode("update") \
        .start()
        
    query.awaitTermination()

def write_to_postgres(batch_df, batch_id):
    """Écrit un batch de données dans PostgreSQL en gérant les doublons"""
    import psycopg2
    from psycopg2.extras import execute_values
    
    # Supprimer les doublons d'ID dans le DataFrame d'entrée
    batch_df_distinct = batch_df.dropDuplicates(["id"])
    
    # Si aucune donnée à écrire, sortir
    if batch_df_distinct.count() == 0:
        print(f"Batch {batch_id}: Aucune donnée à écrire")
        return
    
    # Récupérer les données sous forme de liste de tuples
    rows = batch_df_distinct.collect()
    data = [(
        row.id, 
        row.title, 
        row.price, 
        row.category, 
        row.rating_value, 
        row.rating_count, 
        row.price_category, 
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
        INSERT INTO products (id, title, price, category, rating_value, rating_count, price_category, source)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            price = EXCLUDED.price,
            category = EXCLUDED.category,
            rating_value = EXCLUDED.rating_value,
            rating_count = EXCLUDED.rating_count,
            price_category = EXCLUDED.price_category,
            source = EXCLUDED.source
        """
        
        # Définition des templates de colonnes pour execute_values
        template = "(%(id)s, %(title)s, %(price)s, %(category)s, %(rating_value)s, %(rating_count)s, %(price_category)s, %(source)s)"
        
        # Convertir les tuples en dictionnaires pour execute_values
        data_dicts = [
            {
                'id': d[0],
                'title': d[1],
                'price': d[2],
                'category': d[3],
                'rating_value': d[4],
                'rating_count': d[5],
                'price_category': d[6],
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
        if conn:
            conn.rollback()
        raise e
        
    finally:
        # Fermer la connexion dans tous les cas
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    spark = create_spark_session()
    process_products(spark)