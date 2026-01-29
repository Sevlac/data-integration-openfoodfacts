-- Top 10 marques par proportion de produits Nutri-Score A/B.
SELECT 
    b.brand_name,
    COUNT(DISTINCT CASE 
        WHEN f.nutriscore_grade IN ('A','B') THEN p.product_sk 
    END)
    / COUNT(DISTINCT p.product_sk) AS proportion_ab,
    COUNT(DISTINCT p.product_sk) AS nb_products
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE f.nutriscore_grade IS NOT NULL
GROUP BY b.brand_name
HAVING COUNT(DISTINCT p.product_sk) >= 10
ORDER BY proportion_ab DESC
LIMIT 10;

-- Distribution Nutri-Score par niveau 2 de catégorie.
SELECT
    c.parent_category_sk AS category_lvl1,
    c.category_name     AS category_lvl2,
    f.nutriscore_grade,
    COUNT(*) AS nb_products
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE f.nutriscore_grade IS NOT NULL
GROUP BY 
    c.parent_category_sk,
    c.category_name,
    f.nutriscore_grade
ORDER BY 
    c.category_name,
    f.nutriscore_grade;

-- Heatmap (table) pays × catégorie : moyenne sugars_100g.
SELECT
    ct.country,
    c.category_name,
    AVG(f.sugars_100g) AS avg_sugars_100g
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_category c ON p.primary_category_sk = c.category_sk
JOIN JSON_TABLE(
    p.countries_multi_name,
    '$[*]' COLUMNS (
        country VARCHAR(100) PATH '$'
    )
) ct
WHERE f.sugars_100g IS NOT NULL
GROUP BY ct.country, c.category_name
ORDER BY ct.country, c.category_name;

-- Taux de complétude des nutriments par marque.
SELECT
    b.brand_name,
    AVG(
        (
            (f.energy_kcal_100g IS NOT NULL) +
            (f.fat_100g IS NOT NULL) +
            (f.saturated_fat_100g IS NOT NULL) +
            (f.sugars_100g IS NOT NULL) +
            (f.salt_100g IS NOT NULL) +
            (f.proteins_100g IS NOT NULL) +
            (f.fiber_100g IS NOT NULL) +
            (f.sodium_100g IS NOT NULL)
        ) / 8
    ) AS completeness_rate
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_brand b ON p.brand_sk = b.brand_sk
GROUP BY b.brand_name
ORDER BY completeness_rate DESC;

-- Liste anomalies (ex. salt_100g > 25 ou sugars_100g > 80).
SELECT
    p.code,
    p.product_name,
    b.brand_name,
    f.salt_100g,
    f.sugars_100g
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE 
    f.salt_100g > 25
    OR f.sugars_100g > 80
ORDER BY 
    f.salt_100g DESC,
    f.sugars_100g DESC;

-- Évolution hebdo de la complétude (via dim_time).
SELECT
    t.year,
    t.iso_week,
    AVG(f.completeness_score) AS avg_completeness
FROM fact_nutrition_snapshot f
JOIN dim_time t ON f.time_sk = t.time_sk
GROUP BY t.year, t.iso_week
ORDER BY t.year, t.iso_week;
