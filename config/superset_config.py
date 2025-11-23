import os

SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'your_secret_key')
#SQLALCHEMY_DATABASE_URI = 'sqlite:////app/superset.db'
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@postgres:5432/data_fakestore_db'

# PostgreSQL connection string
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres_user')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'postgres_password')
POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'data_fakestore_db')