-- USERS
INSERT INTO users (email, first_name, last_name, user_type, total_spent, purchase_count, last_device)
SELECT
  NULLIF(email,''),
  NULLIF(first_name,''),
  NULLIF(last_name,''),
  NULLIF(user_type,''),
  NULLIF(total_spent,'')::DECIMAL,
  NULLIF(purchase_count,'')::INTEGER,
  NULLIF(last_device,'')
FROM raw.users_raw
WHERE NULLIF(email,'') IS NOT NULL;

-- PURCHASES
INSERT INTO purchases (transaction_id, user_email, product_name, product_category, total_price, purchase_date)
SELECT
  NULLIF(transaction_id,''),
  NULLIF(user_email,''),
  NULLIF(product_name,''),
  NULLIF(product_category,''),
  CASE
    WHEN NULLIF(total_price,'') IS NOT NULL THEN total_price::DECIMAL
    ELSE COALESCE(NULLIF(unit_price,'')::DECIMAL,0)
         * COALESCE(NULLIF(quantity,'')::DECIMAL,1)
         - COALESCE(NULLIF(discount_amount,'')::DECIMAL,0)
         + COALESCE(NULLIF(shipping_cost,'')::DECIMAL,0)
  END,
  TO_DATE(NULLIF(purchase_date,''), 'MM/DD/YYYY')
FROM raw.purchases_raw
WHERE NULLIF(transaction_id,'') IS NOT NULL
  AND NULLIF(user_email,'')    IS NOT NULL;