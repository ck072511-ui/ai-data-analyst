-- Sample data for AI Data Analyst 
CREATE TABLE IF NOT EXISTS products ( 
    id SERIAL PRIMARY KEY, 
    name VARCHAR(100), 
    category VARCHAR(50), 
    price DECIMAL(10,2) 
); 
 
CREATE TABLE IF NOT EXISTS sales ( 
    id SERIAL PRIMARY KEY, 
    product_id INTEGER REFERENCES products(id), 
    sale_date DATE, 
    quantity INTEGER, 
    revenue DECIMAL(10,2), 
    region VARCHAR(50) 
); 
 
INSERT INTO products (name, category, price) VALUES 
    ('Laptop Pro', 'Electronics', 1200.00), 
    ('Smartphone X', 'Electronics', 800.00), 
    ('Office Chair', 'Furniture', 250.00), 
    ('Desk Lamp', 'Furniture', 45.00), 
    ('Running Shoes', 'Sports', 120.00); 
 
INSERT INTO sales (product_id, sale_date, quantity, revenue, region) VALUES 
    (1, '2025-01-15', 5, 6000.00, 'North'), 
    (2, '2025-01-16', 10, 8000.00, 'South'), 
    (3, '2025-01-17', 8, 2000.00, 'East'), 
    (4, '2025-01-18', 20, 900.00, 'West'), 
    (5, '2025-01-19', 15, 1800.00, 'North'); 
