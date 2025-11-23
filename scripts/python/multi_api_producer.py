import json
import time
import requests
from kafka import KafkaProducer

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'
KAFKA_TOPIC_PRODUCTS = 'fakestore-products'
KAFKA_TOPIC_CARTS = 'fakestore-carts'
KAFKA_TOPIC_USERS = 'fakestore-users'

# Configuration APIs
API_SOURCES = {
    'fakestore': {
        'base_url': 'https://fakestoreapi.com',
        'endpoints': {
            'products': '/products',
            'carts': '/carts',
            'users': '/users'
        }
    },
    'dummyjson': {
        'base_url': 'https://dummyjson.com',
        'endpoints': {
            'products': '/products',
            'carts': '/carts',
            'users': '/users'
        }
    }
}

def create_kafka_producer():
    """Crée et retourne un producteur Kafka"""
    # On ajoute des tentatives de connexion car Kafka peut être lent au démarrage
    attempts = 0
    while attempts < 10:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k else None
            )
            print("Connexion à Kafka établie avec succès")
            return producer
        except Exception as e:
            attempts += 1
            print(f"Tentative {attempts} de connexion à Kafka a échoué: {e}")
            time.sleep(10)  # Attendez 10 secondes avant de réessayer
    
    raise Exception("Impossible de se connecter à Kafka après plusieurs tentatives")

def fetch_data(api_source, endpoint_key, limit=None):
    source_config = API_SOURCES[api_source]
    url = f"{source_config['base_url']}{source_config['endpoints'][endpoint_key]}"
    
    params = {}
    if api_source == 'dummyjson' and limit:
        params['limit'] = limit  # Ajoute le paramètre ?limit=N

    print(f"Récupération des données depuis {url} avec paramètres {params}")
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if api_source == 'dummyjson' and isinstance(data, dict):
                if endpoint_key in data:
                    return data[endpoint_key]
            return data
        else:
            print(f"Erreur lors de la récupération des données: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception lors de la récupération des données: {e}")
        return []


def normalize_product(product, source):
    """Normalise les données de produit entre les différentes sources"""
    if source == 'dummyjson':
        # Convertir le format DummyJSON en format similaire à FakeStore
        return {
            'id': product.get('id'),
            'title': product.get('title'),
            'price': product.get('price'),
            'description': product.get('description'),
            'category': product.get('category'),
            'image': product.get('thumbnail', product.get('images', [''])[0]),
            'rating': {
                'rate': product.get('rating', 0),
                'count': product.get('stock', 0)  # Utiliser stock comme approximation du count
            },
            'source': 'dummyjson'
        }
    else:
        # FakeStore est déjà dans le format attendu, ajouter juste la source
        product['source'] = 'fakestore'
        return product

def normalize_cart(cart, source):
    """Normalise les données de panier entre les différentes sources"""
    if source == 'dummyjson':
        # Convertir le format DummyJSON en format similaire à FakeStore
        normalized_products = []
        for product in cart.get('products', []):
            normalized_products.append({
                'productId': product.get('id'),
                'quantity': product.get('quantity', 1)
            })
        
        return {
            'id': cart.get('id'),
            'userId': cart.get('userId'),
            'date': cart.get('date'),
            'products': normalized_products,
            'source': 'dummyjson'
        }
    else:
        # FakeStore est déjà dans le format attendu, ajouter juste la source
        cart['source'] = 'fakestore'
        return cart

def normalize_user(user, source):
    """Normalise les données d'utilisateur entre les différentes sources"""
    if source == 'dummyjson':
        # Convertir le format DummyJSON en format similaire à FakeStore
        return {
            'id': user.get('id'),
            'email': user.get('email'),
            'username': user.get('username'),
            'name': {
                'firstname': user.get('firstName', ''),
                'lastname': user.get('lastName', '')
            },
            'phone': user.get('phone', ''),
            'address': {
                'street': user.get('address', {}).get('address', ''),
                'city': user.get('address', {}).get('city', ''),
                'zipcode': user.get('address', {}).get('postalCode', '')
            },
            'source': 'dummyjson'
        }
    else:
        # FakeStore est déjà dans le format attendu, ajouter juste la source
        user['source'] = 'fakestore'
        return user

def normalize_data(data, data_type, source):
    """Normalise les données selon leur type et leur source"""
    normalizers = {
        'products': normalize_product,
        'carts': normalize_cart,
        'users': normalize_user
    }
    
    if data_type in normalizers:
        return [normalizers[data_type](item, source) for item in data]
    else:
        return data

def send_to_kafka(producer, topic, data, key_field='id'):
    """Envoie les données à Kafka"""
    if not data:
        print(f"Aucune donnée à envoyer au topic {topic}")
        return
    
    for item in data:
        key = item.get(key_field, None)
        producer.send(topic, key=key, value=item)
    
    producer.flush()
    print(f"Envoyé {len(data)} enregistrements au topic {topic}")

def main():
    """Fonction principale"""
    producer = create_kafka_producer()
    limit = 100  # Nombre de données à récupérer depuis DummyJSON

    # Pour chaque source d'API
    for source_name in API_SOURCES.keys():
        print(f"\nTraitement de la source: {source_name}")
        
        
        # Récupération et envoi des utilisateurs
        users = fetch_data(source_name, 'users', limit=limit)
        normalized_users = normalize_data(users, 'users', source_name)
        send_to_kafka(producer, KAFKA_TOPIC_USERS, normalized_users)
        
        # Récupération et envoi des produits
        products = fetch_data(source_name, 'products', limit=limit)
        normalized_products = normalize_data(products, 'products', source_name)
        send_to_kafka(producer, KAFKA_TOPIC_PRODUCTS, normalized_products)
        
        # Récupération et envoi des paniers
        carts = fetch_data(source_name, 'carts', limit=limit)
        normalized_carts = normalize_data(carts, 'carts', source_name)
        send_to_kafka(producer, KAFKA_TOPIC_CARTS, normalized_carts)
        

    # En mode continu (décommentez pour utiliser en production)
    # while True:
    #     for source_name in API_SOURCES.keys():
    #         print(f"\nTraitement cyclique de la source: {source_name}")
    #         
    #         # Récupération et envoi des produits
    #         products = fetch_data(source_name, 'products', limit=limit)
    #         normalized_products = normalize_data(products, 'products', source_name)
    #         send_to_kafka(producer, KAFKA_TOPIC_PRODUCTS, normalized_products)
    #         
    #         # Autres données si nécessaire...
    #     
    #     time.sleep(3600)  # toutes les heures par exemple

    producer.close()
    print("Producteur fermé avec succès")


if __name__ == "__main__":
    main()
