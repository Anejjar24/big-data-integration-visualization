CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    category VARCHAR(100) NOT NULL,
    rating_value NUMERIC(3, 1),
    rating_count INTEGER,
    price_category VARCHAR(50),
    source VARCHAR(20) DEFAULT 'fakestore'
);


CREATE TABLE cart_items (
    cart_id INTEGER,
    userId INTEGER,
    date TIMESTAMP,
    product_id INTEGER,
    quantity INTEGER,
    day_of_week VARCHAR(10),
    month VARCHAR(10),
    source VARCHAR(20) DEFAULT 'fakestore',
    PRIMARY KEY (cart_id, product_id)
);


CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(50) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    phone VARCHAR(20),
    address_street VARCHAR(100),
    address_city VARCHAR(50),
    address_zipcode VARCHAR(20),
    source VARCHAR(20) DEFAULT 'fakestore'
);


CREATE VIEW vw_product_ratings AS 
SELECT
    category,
    price_category,
    source,
    COUNT(*) as product_count,
    AVG(rating_value) as avg_rating 
FROM products 
GROUP BY category, price_category, source
ORDER BY source, category, price_category;

CREATE VIEW vw_cart_analysis AS 
SELECT
    day_of_week,
    month,
    source,
    COUNT(DISTINCT cart_id) as cart_count,
    SUM(quantity) as total_items 
FROM cart_items 
GROUP BY day_of_week, month, source
ORDER BY source, month, day_of_week;

CREATE VIEW vw_cart_products AS 
SELECT
    c.cart_id,
    c.userId,
    c.date,
    p.title as product_name,
    p.category,
    p.price,
    c.quantity,
    (p.price * c.quantity) as total_price,
    c.source
FROM cart_items c 
JOIN products p ON c.product_id = p.id;


CREATE VIEW vw_data_source_comparison AS
SELECT
    'products' as data_type,
    source,
    COUNT(*) as record_count,
    MIN(price) as min_price,
    MAX(price) as max_price,
    AVG(price) as avg_price,
    AVG(rating_value) as avg_rating
FROM products
GROUP BY source
UNION
SELECT
    'carts' as data_type,
    source,
    COUNT(DISTINCT cart_id) as record_count,
    NULL as min_price,
    NULL as max_price,
    NULL as avg_price,
    NULL as avg_rating
FROM cart_items
GROUP BY source
UNION
SELECT
    'users' as data_type,
    source,
    COUNT(*) as record_count,
    NULL as min_price,
    NULL as max_price,
    NULL as avg_price,
    NULL as avg_rating
FROM users
GROUP BY source
ORDER BY data_type, source;