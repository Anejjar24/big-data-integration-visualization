import json
import time
import psycopg2
from kafka import KafkaConsumer

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'
KAFKA_TOPIC = 'fakestore-users'

# Configuration PostgreSQL
PG_HOST = 'postgres'
PG_DATABASE = 'data_fakestore_db'
PG_USER = 'postgres_user'
PG_PASSWORD = 'postgres_password'

def create_kafka_consumer():
    """Crée et retourne un consommateur Kafka"""
    # On ajoute des tentatives de connexion car Kafka peut être lent au démarrage
    attempts = 0
    while attempts < 10:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='user-processor-group'
            )
            print("Connexion au consumer Kafka établie avec succès")
            return consumer
        except Exception as e:
            attempts += 1
            print(f"Tentative {attempts} de connexion au consumer Kafka a échoué: {e}")
            time.sleep(10)  # Attendez 10 secondes avant de réessayer
    
    raise Exception("Impossible de se connecter au consumer Kafka après plusieurs tentatives")

def get_postgres_connection():
    """Crée et retourne une connexion PostgreSQL"""
    # On ajoute des tentatives de connexion car PostgreSQL peut être lent au démarrage
    attempts = 0
    while attempts < 10:
        try:
            conn = psycopg2.connect(
                host=PG_HOST,
                database=PG_DATABASE,
                user=PG_USER,
                password=PG_PASSWORD
            )
            print("Connexion à PostgreSQL établie avec succès")
            return conn
        except Exception as e:
            attempts += 1
            print(f"Tentative {attempts} de connexion à PostgreSQL a échoué: {e}")
            time.sleep(10)  # Attendez 10 secondes avant de réessayer
    
    raise Exception("Impossible de se connecter à PostgreSQL après plusieurs tentatives")

def process_user_data(user_data):
    """Traite les données utilisateur et les insère dans PostgreSQL"""
    # Extraction des données d'adresse et de nom
    address = user_data.get('address', {})
    name = user_data.get('name', {})
    
    # Obtention de la source de données
    source = user_data.get('source', 'fakestore')
    
    # Construction de la requête SQL
    query = """
    INSERT INTO users (
        id, email, username, first_name, last_name, 
        phone, address_street, address_city, address_zipcode, source
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        username = EXCLUDED.username,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        phone = EXCLUDED.phone,
        address_street = EXCLUDED.address_street,
        address_city = EXCLUDED.address_city,
        address_zipcode = EXCLUDED.address_zipcode,
        source = EXCLUDED.source;
    """
    
    # Valeurs pour la requête
    values = (
        user_data.get('id'),
        user_data.get('email'),
        user_data.get('username'),
        name.get('firstname'),
        name.get('lastname'),
        user_data.get('phone'),
        address.get('street'),
        address.get('city'),
        address.get('zipcode'),
        source
    )
    
    # Exécution de la requête
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            print(f"Utilisateur {user_data.get('id')} (source: {source}) traité avec succès.")

def main():
    """Fonction principale"""
    consumer = create_kafka_consumer()
    
    print(f"En attente de messages sur le topic {KAFKA_TOPIC}...")
    for message in consumer:
        try:
            process_user_data(message.value)
        except Exception as e:
            print(f"Erreur lors du traitement du message: {e}")
    
    consumer.close()

if __name__ == "__main__":
    main()