# Data Pipeline - Multi-Source Real-Time Data Integration

## 📋 Quick Overview

**Data Pipeline** is a sophisticated **event-driven streaming data integration system** that fetches data from multiple e-commerce APIs (FakeStore and DummyJSON), processes it in real-time using Apache Kafka and Apache Spark, and persists normalized data into PostgreSQL for analytics and visualization.

**Problem Solved**: 
- ✅ Integrate data from multiple heterogeneous e-commerce APIs
- ✅ Normalize data from different sources with different schemas
- ✅ Process large volumes of data in real-time
- ✅ Handle data consistency and deduplication
- ✅ Provide unified analytics view across all sources
- ✅ Enable real-time dashboards with Apache Superset

---

## 🏗️ Core Architecture

This is an **event-driven, microservices-based streaming architecture** using the Lambda architecture pattern (real-time + batch processing).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES LAYER                                 │
│                  (Multiple External APIs)                                   │
│  ┌─────────────────┐              ┌─────────────────┐                      │
│  │  FakeStore API  │              │  DummyJSON API  │                      │
│  │  - Products     │              │  - Products     │                      │
│  │  - Carts        │              │  - Carts        │                      │
│  │  - Users        │              │  - Users        │                      │
│  └────────┬────────┘              └────────┬────────┘                      │
└───────────┼────────────────────────────────┼───────────────────────────────┘
            │                                │ HTTP API Calls
            └────────────────┬───────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER (Kafka Producer)                       │
│                    multi_api_producer.py                                    │
│  - Fetches data from multiple APIs                                         │
│  - Normalizes heterogeneous schemas                                        │
│  - Produces to Kafka topics                                                │
│  ┌─────────────────────────────────────────────────────────┐               │
│  │ Three Kafka Topics:                                     │               │
│  │ • fakestore-products (normalized product data)          │               │
│  │ • fakestore-carts (normalized cart data)                │               │
│  │ • fakestore-users (normalized user data)                │               │
│  └─────────────────────────────────────────────────────────┘               │
└────────────────┬────────────────────────────────────────────────────────────┘
                 │ Kafka Streaming
                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STREAM PROCESSING LAYER (Apache Spark)                   │
│  ┌──────────────────────┐  ┌──────────────────────┐                       │
│  │spark_products_       │  │spark_carts_          │  process_users.py     │
│  │processor.py          │  │processor.py          │  (Kafka Consumer)     │
│  │                      │  │                      │                        │
│  │• Parse JSON schema   │  │• Parse JSON schema   │  • Consume from       │
│  │• Extract nested      │  │• Explode products    │    Kafka              │
│  │  ratings             │  │• Calculate day/month │  • Direct insert to   │
│  │• Create price        │  │• Create price        │    PostgreSQL         │
│  │  categories          │  │  categories          │                        │
│  │• Deduplication       │  │• Deduplication       │                        │
│  │• Batch write         │  │• Batch write         │                        │
│  └──────────┬───────────┘  └──────────┬───────────┘  └─────────┬──────────┘
│             │                         │                        │           │
│             └────────────────┬────────┴────────────────────────┘           │
│                              │ SQL UPSERT Queries                          │
└──────────────────────────────┼────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATA WAREHOUSE LAYER (PostgreSQL)                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │   products      │  │   cart_items     │  │      users       │          │
│  │  (normalized)   │  │  (normalized)    │  │  (normalized)    │          │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
│  Analytical Views:                                                          │
│  • vw_product_ratings - Product analysis by category                      │
│  • vw_cart_analysis - Shopping patterns by time                           │
│  • vw_cart_products - Cart-product joins                                  │
│  • vw_data_source_comparison - Cross-source statistics                    │
└────────────────┬────────────────────────────────────────────────────────────┘
                 │ JDBC Connection
                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION LAYER (Apache Superset)                    │
│                     Real-time Analytics Dashboard                          │
│  - Interactive charts and visualizations                                   │
│  - Real-time metric updates                                                │
│  - Multi-source comparison dashboards                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Key Components & Modules

### 1. **Ingestion Layer: `multi_api_producer.py`**

**Purpose**: Acts as the data producer, fetching data from multiple external APIs and normalizing them into Kafka topics.

**Key Functions**:

| Function | Purpose |
|----------|---------|
| `create_kafka_producer()` | Establishes Kafka connection with retry logic (10 attempts, 10s intervals) |
| `fetch_data()` | Fetches data from APIs (FakeStore, DummyJSON) |
| `normalize_product()` | Converts product schemas from different sources to unified format |
| `normalize_cart()` | Converts cart schemas to unified format |
| `normalize_user()` | Converts user schemas to unified format |
| `send_to_kafka()` | Publishes normalized data to appropriate Kafka topic |
| `main()` | Orchestrates the full pipeline (fetches all sources, normalizes, produces) |

**Data Sources**:
- **FakeStore API**: `https://fakestoreapi.com` - Simple e-commerce dataset
- **DummyJSON API**: `https://dummyjson.com` - More complex dataset with different schema

**Normalization Process**:
- Extracts common fields from both APIs
- Maps API-specific nested structures to unified format
- Adds `source` field to track data origin
- Handles different field names (e.g., `firstName` → `firstname`)

**Output Topics**:
- `fakestore-products` - Normalized product data
- `fakestore-carts` - Normalized shopping cart data
- `fakestore-users` - Normalized user data

---

### 2. **Stream Processing Layer: Spark Processors**

#### **spark_products_processor.py**

**Purpose**: Consumes product data from Kafka, transforms it with business logic, and persists to PostgreSQL.

**Key Operations**:
```
Kafka Topic (fakestore-products)
    ↓
Parse JSON with defined schema
    ↓
Extract nested rating.rate and rating.count
    ↓
Categorize price: <50€ (économique), <100€ (moyen), ≥100€ (premium)
    ↓
Deduplication by product ID
    ↓
Batch write to PostgreSQL (ON CONFLICT → UPDATE)
```

**Transformation Details**:
- Extracts nested rating structure from JSON
- Creates `price_category` column for segmentation
- Preserves `source` field for data lineage
- Batch processing with deduplication (dropDuplicates on ID)
- Handles upserts: INSERT with ON CONFLICT UPDATE clause

---

#### **spark_carts_processor.py**

**Purpose**: Consumes cart data from Kafka, explodes products, enriches with temporal data, and persists.

**Key Operations**:
```
Kafka Topic (fakestore-carts)
    ↓
Parse JSON with nested product arrays
    ↓
Explode products array (one row per product in cart)
    ↓
Extract temporal features:
  - day_of_week (Monday, Tuesday, etc.)
  - month (January, February, etc.)
    ↓
Deduplication by (cart_id, product_id)
    ↓
Batch write to PostgreSQL
```

**Transformation Details**:
- Explodes products array to create detail rows
- Converts ISO date strings to Timestamp type
- Derives day-of-week and month for temporal analysis
- Composite key deduplication (cart_id + product_id)
- Handles upserts with composite key conflict detection

---

#### **process_users.py**

**Purpose**: Lightweight Kafka consumer that processes user data directly into PostgreSQL (no Spark).

**Flow**:
```
Kafka Consumer (fakestore-users topic)
    ↓
For each user message:
    ├─ Parse nested address and name objects
    ├─ Extract all fields
    ├─ Prepare SQL INSERT with ON CONFLICT
    ↓
Direct insert to PostgreSQL (no batching)
```

**Why Different Approach?**:
- User data is simpler (fewer nested structures)
- Direct SQL upserts are sufficient
- Avoids Spark overhead for straightforward transformations

---

### 3. **Data Layer: PostgreSQL**

**Tables**:

```sql
products
├─ id (PK)
├─ title
├─ price
├─ category
├─ rating_value (extracted from nested rating.rate)
├─ rating_count (extracted from nested rating.count)
├─ price_category (calculated)
└─ source (fakestore or dummyjson)

cart_items
├─ cart_id (PK)
├─ product_id (PK)
├─ userId
├─ date
├─ quantity
├─ day_of_week (calculated)
├─ month (calculated)
└─ source (fakestore or dummyjson)

users
├─ id (PK)
├─ email (UNIQUE)
├─ username
├─ first_name
├─ last_name
├─ phone
├─ address_street
├─ address_city
├─ address_zipcode
└─ source (fakestore or dummyjson)
```

**Analytical Views** (for Superset dashboards):

| View | Purpose |
|------|---------|
| `vw_product_ratings` | Group products by category/price_category, calculate avg ratings |
| `vw_cart_analysis` | Analyze carts by day of week/month, count carts, sum quantities |
| `vw_cart_products` | Join carts with products, calculate total price per item |
| `vw_data_source_comparison` | Compare record counts and metrics across data sources |

---

### 4. **Infrastructure: Docker Compose**

**Services**:

| Service | Role | Purpose |
|---------|------|---------|
| **Zookeeper** | Coordination | Manages Kafka broker state and partitions |
| **Kafka** | Message Broker | Central event streaming platform |
| **Spark Master** | Orchestration | Coordinates Spark job execution |
| **Spark Worker** | Computation | Executes Spark tasks in parallel |
| **PostgreSQL** | Data Warehouse | Persists normalized, processed data |
| **Superset** | Visualization | Creates real-time analytics dashboards |

**Volumes Mounted**:
- `./scripts/` → `/scripts` - Python processing scripts
- `./data/` → `/data` - Shared data storage
- `./logs/` → `/logs` - Application logs

---

## 🔄 Data Flow & Communication

### **End-to-End Data Flow Diagram**

```
┌─────────────┐
│  FakeStore  │──────────────────────────────────────────────┐
│    API      │                                              │
└─────────────┘                                              │
                                                              │
┌─────────────┐                                              ▼
│ DummyJSON   │──────────────────────────────────────┐  multi_api_producer.py
│    API      │                                      │   (Python)
└─────────────┘                                      │
                                                      │
                     ┌──────────────────────────────┐ │
                     │  Normalization & Mapping    │─┘
                     │  • Extract common fields    │
                     │  • Handle API differences   │
                     │  • Add source tracking      │
                     └──────────┬───────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │  Kafka Topics:        │
                    ├───────────────────────┤
                    │ products: 100 items   │
                    │ carts: 50 items       │
                    │ users: 30 items       │
                    └──────────┬────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   ┌─────────┐         ┌──────────────┐      ┌─────────────┐
   │Spark    │         │Spark         │      │Kafka        │
   │Products │         │Carts         │      │Consumer     │
   │Processor│         │Processor     │      │for Users    │
   └────┬────┘         └──────┬───────┘      └──────┬──────┘
        │                     │                     │
        │ JSON Parsing        │ JSON Parsing        │ Direct JSON
        │ Price Categorize    │ Array Explode       │ Mapping
        │ Deduplication       │ Temporal Extract    │
        │                     │ Deduplication       │
        └─────────┬───────────┴─────────┬───────────┘
                  │                     │
                  └──────────┬──────────┘
                             ▼
                    ┌──────────────────┐
                    │  PostgreSQL      │
                    │  UPSERT Queries  │
                    │  ON CONFLICT     │
                    └────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │ Data Warehouse  │
                    │ • products      │
                    │ • carts         │
                    │ • users         │
                    └────────┬────────┘
                             │
                    ┌────────▼────────────┐
                    │ Analytical Views    │
                    │ • ratings analysis  │
                    │ • cart patterns     │
                    │ • source comparison │
                    └────────┬────────────┘
                             │
                    ┌────────▼────────────┐
                    │ Apache Superset     │
                    │ Real-time Dashboard │
                    └─────────────────────┘
```

### **Component Interactions**

```
Sequential Execution Order:
═══════════════════════════

1. Docker Compose Startup
   ├─ Start Zookeeper
   ├─ Start Kafka (depends on Zookeeper)
   ├─ Start Spark Master
   ├─ Start Spark Worker (depends on Master)
   ├─ Start PostgreSQL
   └─ Start Superset (depends on PostgreSQL)

2. Data Ingestion Phase
   └─ Run multi_api_producer.py
      ├─ Connect to Kafka (retry logic)
      ├─ For each API source (FakeStore, DummyJSON)
      │  ├─ Fetch products, carts, users
      │  ├─ Normalize each data type
      │  └─ Send to Kafka topics
      └─ Publish ~280 total records across 3 topics

3. Stream Processing Phase
   ├─ Start spark_products_processor.py
   │  ├─ Listen to fakestore-products topic
   │  ├─ For each batch:
   │  │  ├─ Parse JSON
   │  │  ├─ Categorize prices
   │  │  ├─ Deduplicate by ID
   │  │  └─ Upsert to products table
   │  └─ Insert ~200 normalized products
   │
   ├─ Start spark_carts_processor.py
   │  ├─ Listen to fakestore-carts topic
   │  ├─ For each batch:
   │  │  ├─ Parse JSON
   │  │  ├─ Explode products array
   │  │  ├─ Extract temporal data
   │  │  ├─ Deduplicate by (cart_id, product_id)
   │  │  └─ Upsert to cart_items table
   │  └─ Insert ~500+ cart item rows
   │
   └─ Start process_users.py
      ├─ Listen to fakestore-users topic
      └─ For each message:
         ├─ Parse nested structure
         └─ Upsert to users table

4. Analytics Phase
   ├─ PostgreSQL creates views from normalized data
   └─ Superset queries views for real-time dashboards
```

---

## 🛠️ Tech Stack & Dependencies

### **Backend Technologies**

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.9 | Data processing scripting |
| **Apache Kafka** | 2.8 | Distributed event streaming |
| **Apache Spark** | 3.3.1 | Large-scale stream processing |
| **PostgreSQL** | 13 | Relational data warehouse |
| **Apache Superset** | Latest | Analytics and visualization |
| **Zookeeper** | 3.8 | Distributed coordination |

### **Python Dependencies**

```
requests==2.28.2          # HTTP API calls
kafka-python==2.0.2       # Kafka client library
pyspark==3.1.2            # Spark Python API
pandas==1.5.3             # Data manipulation
psycopg2-binary==2.9.6    # PostgreSQL adapter
```

### **Why These Technologies?**

1. **Kafka**: 
   - ✅ Decouples producers from consumers
   - ✅ Provides durable, replayable event log
   - ✅ Supports multiple consumers independently
   - ✅ Natural fit for real-time streaming

2. **Spark**: 
   - ✅ Distributed processing for large datasets
   - ✅ Structured Streaming API for real-time data
   - ✅ SQL support for complex transformations
   - ✅ Integration with PostgreSQL

3. **PostgreSQL**: 
   - ✅ ACID transactions guarantee data consistency
   - ✅ ON CONFLICT clause for efficient upserts
   - ✅ SQL views for analytical queries
   - ✅ Integrates well with Superset

4. **Superset**: 
   - ✅ Real-time dashboard capabilities
   - ✅ Multi-source data visualization
   - ✅ Interactive exploration tools
   - ✅ No-code dashboard creation

---

## 🚀 Execution Flow - Typical Workflow

### **Complete Request-to-Dashboard Flow**

```
START: User wants to analyze e-commerce trends
│
├─ 1. START INFRASTRUCTURE
│  ├─ docker-compose up
│  ├─ Zookeeper starts on 2181
│  ├─ Kafka starts on 9092
│  ├─ Spark Master on 8083, Worker on 8081
│  ├─ PostgreSQL on 5432
│  └─ Superset on 8088
│
├─ 2. DATA INGESTION (multi_api_producer.py)
│  ├─ Connect to Kafka with retry logic
│  ├─ For FakeStore API:
│  │  ├─ GET https://fakestoreapi.com/products
│  │  │  └─ Returns: {id, title, price, category, rating}
│  │  ├─ Normalize: {id, title, price, category, rating: {rate, count}, source: 'fakestore'}
│  │  ├─ Send to fakestore-products topic
│  │  │
│  │  ├─ GET https://fakestoreapi.com/carts
│  │  │  └─ Returns: {id, userId, date, products: [{productId, quantity}]}
│  │  ├─ Normalize: Same structure + source field
│  │  ├─ Send to fakestore-carts topic
│  │  │
│  │  └─ GET https://fakestoreapi.com/users
│  │     └─ Returns: {id, email, username, name: {firstname, lastname}, ...}
│  │     └─ Normalize: Extract nested fields, add source
│  │     └─ Send to fakestore-users topic
│  │
│  ├─ For DummyJSON API:
│  │  ├─ GET https://dummyjson.com/products?limit=100
│  │  │  └─ Returns: {products: [{id, title, price, category, rating, ...}]}
│  │  ├─ Normalize: Map to FakeStore schema, add source: 'dummyjson'
│  │  ├─ Send to fakestore-products topic
│  │  │
│  │  ├─ GET https://dummyjson.com/carts?limit=100
│  │  │  └─ Returns: {carts: [{id, userId, date, products}]}
│  │  ├─ Normalize: Map nested structures, add source
│  │  ├─ Send to fakestore-carts topic
│  │  │
│  │  └─ Similar for users...
│  │
│  └─ Kafka now has ~280 total messages across 3 topics
│
├─ 3. STREAM PROCESSING
│  │
│  ├─ spark_products_processor.py:
│  │  ├─ Subscribe to fakestore-products topic
│  │  ├─ ReadStream from Kafka with earliest offsets
│  │  ├─ Parse JSON using product_schema
│  │  ├─ For each batch:
│  │  │  ├─ Extract rating.rate → rating_value
│  │  │  ├─ Extract rating.count → rating_count
│  │  │  ├─ Calculate price_category:
│  │  │  │  ├─ price < 50 → 'économique'
│  │  │  │  ├─ price < 100 → 'moyen'
│  │  │  │  └─ price ≥ 100 → 'premium'
│  │  │  ├─ Deduplicate on product ID (keep latest)
│  │  │  └─ Write batch to PostgreSQL:
│  │  │     └─ INSERT INTO products (...) VALUES (...)
│  │  │        ON CONFLICT (id) DO UPDATE SET ...
│  │  │
│  │  └─ Result: ~200 products in products table
│  │
│  ├─ spark_carts_processor.py:
│  │  ├─ Subscribe to fakestore-carts topic
│  │  ├─ ReadStream from Kafka
│  │  ├─ For each batch:
│  │  │  ├─ Parse JSON using cart_schema
│  │  │  ├─ Explode products array:
│  │  │  │  ├─ Original: {cart_id: 1, products: [{id:10, qty:2}, {id:20, qty:1}]}
│  │  │  │  └─ After explosion:
│  │  │  │     ├─ Row 1: cart_id:1, product_id:10, qty:2
│  │  │  │     └─ Row 2: cart_id:1, product_id:20, qty:1
│  │  │  ├─ Extract temporal data:
│  │  │  │  ├─ 2024-01-15 → day_of_week: 'Monday', month: 'January'
│  │  │  ├─ Deduplicate on (cart_id, product_id)
│  │  │  └─ Write to PostgreSQL:
│  │  │     └─ INSERT INTO cart_items (...) VALUES (...)
│  │  │        ON CONFLICT (cart_id, product_id) DO UPDATE SET ...
│  │  │
│  │  └─ Result: ~500+ cart items in cart_items table
│  │
│  └─ process_users.py:
│     ├─ Subscribe to fakestore-users topic
│     ├─ KafkaConsumer: group_id='user-processor-group'
│     ├─ For each message:
│     │  ├─ Parse nested user object
│     │  ├─ Extract: name.firstname → first_name, address.street → address_street
│     │  └─ INSERT or UPDATE in users table
│     │
│     └─ Result: ~60 users in users table
│
├─ 4. ANALYTICAL PROCESSING
│  ├─ PostgreSQL creates views from normalized data:
│  │  │
│  │  ├─ vw_product_ratings:
│  │  │  └─ SELECT category, price_category, source, 
│  │  │        COUNT(*) as product_count, AVG(rating_value) as avg_rating
│  │  │     FROM products
│  │  │     GROUP BY category, price_category, source
│  │  │
│  │  ├─ vw_cart_analysis:
│  │  │  └─ SELECT day_of_week, month, source,
│  │  │        COUNT(DISTINCT cart_id) as cart_count, SUM(quantity) as total_items
│  │  │     FROM cart_items
│  │  │     GROUP BY day_of_week, month, source
│  │  │
│  │  └─ vw_cart_products:
│  │     └─ SELECT cart_id, userId, p.title, c.quantity, 
│  │           (p.price * c.quantity) as total_price
│  │        FROM cart_items c JOIN products p ON ...
│  │
│  └─ Views now contain aggregated analytics
│
├─ 5. VISUALIZATION (Apache Superset)
│  ├─ User opens Superset at http://localhost:8088
│  ├─ Connect Superset to PostgreSQL
│  ├─ Create dashboards from views:
│  │  ├─ Dashboard 1: Product Analysis
│  │  │  ├─ Chart: Average Rating by Category (vw_product_ratings)
│  │  │  ├─ Chart: Price Distribution (vw_product_ratings)
│  │  │  └─ Chart: Source Comparison (vw_data_source_comparison)
│  │  │
│  │  ├─ Dashboard 2: Shopping Patterns
│  │  │  ├─ Chart: Carts by Day of Week (vw_cart_analysis)
│  │  │  ├─ Chart: Items Sold by Month (vw_cart_analysis)
│  │  │  └─ Chart: Peak Shopping Times
│  │  │
│  │  └─ Dashboard 3: Multi-Source Comparison
│  │     ├─ Table: Record Counts by Source
│  │     ├─ Chart: Average Price Differences
│  │     └─ Chart: Source Coverage
│  │
│  └─ Real-time dashboards update as new data arrives
│
└─ END: User has real-time insights into merged e-commerce data
```

---

## 🗂️ Project Structure

```
data-pipeline/
├── docker-compose.yml               # Orchestrates all services
├── Dockerfile                       # Python 3.9 + Java environment
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── config/
│   ├── init-db.sql                 # PostgreSQL schema & views
│   └── superset_config.py           # Superset configuration
│
├── scripts/
│   └── python/
│       ├── multi_api_producer.py    # Data ingestion (Kafka producer)
│       ├── process_users.py         # User data processor (Kafka consumer)
│       ├── spark_products_processor.py    # Product data processor (Spark)
│       └── spark_carts_processor.py       # Cart data processor (Spark)
│
├── data/
│   ├── postgres/                   # PostgreSQL data volume
│   └── (other data files)
│
└── logs/
    └── (application logs)
```

---

## 🚀 Quick Start

### **Prerequisites**
- Docker and Docker Compose
- 8GB RAM minimum
- ~2GB disk space

### **Installation & Startup**

```bash
# 1. Navigate to project directory
cd data-pipeline

# 2. Build and start all services
docker-compose up -d

# 3. Wait for all services to be healthy (~30 seconds)
docker-compose ps

# 4. Run data ingestion
docker-compose exec -T spark-master python /scripts/python/multi_api_producer.py

# 5. Run stream processors (in separate terminals)
docker-compose exec -T spark-master spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2 \
  --master spark://spark-master:7077 \
  /scripts/python/spark_products_processor.py

docker-compose exec -T spark-master spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2 \
  --master spark://spark-master:7077 \
  /scripts/python/spark_carts_processor.py

docker exec -T spark-master python /scripts/python/process_users.py

# 6. Access Superset
# Open browser: http://localhost:8088
# Login: admin/admin
```

---

## 📊 Database & Queries

### **Querying Results**

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U postgres_user -d data_fakestore_db

# View normalized products
SELECT * FROM products LIMIT 10;

# Analyze product ratings
SELECT * FROM vw_product_ratings;

# Analyze shopping patterns
SELECT * FROM vw_cart_analysis;

# Compare data sources
SELECT * FROM vw_data_source_comparison;
```

### **Key Metrics Available**

1. **Product Analytics**
   - Average rating by category
   - Price distribution by source
   - Product count by price category

2. **Shopping Behavior**
   - Peak shopping days/months
   - Items purchased per cart
   - Cart value distribution

3. **Data Quality**
   - Record counts by source
   - Coverage comparison
   - Data freshness

---

## 🔐 Security & Best Practices

1. **Credentials**: Database credentials hardcoded in config (for demo only)
   - ⚠️ Change in production
   - Use environment variables or secrets manager

2. **Network**: All services on internal Docker network
   - ✅ External exposure only on necessary ports

3. **Data Validation**: 
   - ✅ ON CONFLICT handling prevents duplicates
   - ✅ Schema validation in Spark processors

4. **Error Handling**:
   - ✅ Retry logic in Kafka connections (10 attempts)
   - ✅ Exception handling in all processors
   - ✅ Rollback on database errors

---

## 🛠️ Troubleshooting

### **Common Issues**

| Issue | Cause | Solution |
|-------|-------|----------|
| Kafka connection failed | Kafka not fully started | Wait 30s, check `docker-compose ps` |
| PostgreSQL not accessible | Database not initialized | Check `docker logs postgres` |
| Spark job fails | Missing dependencies | Verify `--packages` in spark-submit |
| No data in tables | Producer not run | Execute `multi_api_producer.py` first |
| Duplicate records | Missing deduplication | Check processor's `dropDuplicates()` call |

### **Debugging**

```bash
# Check service health
docker-compose ps

# View logs
docker logs kafka
docker logs postgres
docker logs superset

# Test Kafka connectivity
docker exec -it kafka kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic fakestore-products \
  --from-beginning

# Test PostgreSQL
docker exec -it postgres psql -U postgres_user -d data_fakestore_db \
  -c "SELECT COUNT(*) FROM products;"
```

---

## 📈 Monitoring & Metrics

### **Key Performance Indicators**

- **Ingestion Rate**: Records/second from APIs
- **Processing Latency**: Time from Kafka to PostgreSQL
- **Data Freshness**: Time since last update
- **Error Rate**: Failed records percentage
- **Throughput**: Total records processed

### **Dashboards Available**

1. **Spark Master UI**: `http://localhost:8083`
   - Job status and progress
   - Executor metrics

2. **Superset**: `http://localhost:8088`
   - Real-time analytics
   - Custom visualizations

---

## 🎯 Architecture Patterns Used

1. **Event-Driven Architecture**: Kafka decouples producers/consumers
2. **Lambda Architecture**: Real-time stream + batch processing
3. **Data Normalization**: Common schema from heterogeneous sources
4. **Microservices**: Independent processors for each data type
5. **CQRS**: Separate read (views) from write (tables)

---

## 📚 Learning Outcomes

By studying this project, you'll learn:

✅ **Event Streaming**: Apache Kafka fundamentals  
✅ **Stream Processing**: Apache Spark Structured Streaming  
✅ **Data Engineering**: ETL/ELT patterns  
✅ **Data Normalization**: Handling heterogeneous schemas  
✅ **Real-time Analytics**: Streaming to data warehouse  
✅ **Docker Orchestration**: Multi-container deployments  
✅ **SQL & Analytics**: Data warehousing concepts  
✅ **Python Data Processing**: PySpark and psycopg2  

---

## 📝 License

[Specify your license - MIT, Apache 2.0, etc.]

---

## 🤝 Support

For issues or questions:
1. Check the Troubleshooting section
2. Review Docker logs: `docker logs <service_name>`
3. Verify all services are running: `docker-compose ps`
4. Check PostgreSQL directly for data: `docker exec postgres psql ...`

---

**Last Updated**: November 2024  
**Architecture**: Event-Driven Streaming Data Pipeline  
**Status**: Production Ready (with config adjustments)
