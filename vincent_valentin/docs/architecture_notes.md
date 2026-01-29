# Note d'architecture technique
## Projet ETL Open Food Facts

---

## 📋 Sommaire

1. [Vue d'ensemble](#vue-densemble)
2. [Choix techniques](#choix-techniques)
3. [Architecture médaillée](#architecture-médaillée)
4. [Schéma de données Gold](#schéma-de-données-gold)
5. [Stratégie de chargement](#stratégie-de-chargement)
6. [Performance et scalabilité](#performance-et-scalabilité)
7. [Sécurité et gouvernance](#sécurité-et-gouvernance)

---

## 🎯 Vue d'ensemble

### Contexte du projet

**Problématique** : Les données Open Food Facts sont volumineuses (2.3M+ produits), non structurées (215 colonnes disparates) et de qualité variable. Il est nécessaire de les transformer en un datamart analytique exploitable pour des analyses nutritionnelles.

**Objectifs** :
1. **Ingérer** ~400k produits depuis un export CSV
2. **Nettoyer** et valider les données (normalisation, déduplication, validation)
3. **Modéliser** en schéma en étoile pour requêtes OLAP
4. **Optimiser** les performances de requêtage (indexes, partitionnement)

### Architecture cible

```
┌─────────────────────────────────────────────────────────────────┐
│                         SOURCE LAYER                            │
│  Open Food Facts CSV Export (Tab-separated, UTF-8)              │
│  └─ donnees_echantillon.csv (418,676 lignes × 215 colonnes)    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (Spark Read CSV)
┌─────────────────────────────────────────────────────────────────┐
│                       BRONZE LAYER (Spark)                      │
│  DataFrame en mémoire (données brutes, aucune transformation)   │
│  └─ bronze_df (PySpark DataFrame, ~120 MB)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (Transformations PySpark)
┌─────────────────────────────────────────────────────────────────┐
│                    SILVER LAYER (MySQL InnoDB)                  │
│  Table relationnelle normalisée et nettoyée                     │
│  └─ silver_products (418,651 lignes × 17 colonnes, ~45 MB)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (Spark → MySQL JDBC)
┌─────────────────────────────────────────────────────────────────┐
│                     GOLD LAYER (MySQL InnoDB)                   │
│  Datamart analytique - Star Schema                             │
│  ├─ dim_time (50,000 dates uniques)                            │
│  ├─ dim_brand (45,123 marques)                                 │
│  ├─ dim_category (8,000 catégories)                            │
│  ├─ dim_country (180 combinaisons)                             │
│  ├─ dim_product (418,651 produits)                             │
│  └─ fact_nutrition_snapshot (418,651 snapshots)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Choix techniques

### Stack technologique

| Composant | Technologie sélectionnée | Alternatives évaluées | Justification du choix |
|-----------|--------------------------|----------------------|------------------------|
| **Processing** | Apache Spark 3.5 | Pandas | Volume > 100 MB, parallélisme natif, maturité |
| **Langage** | Python 3.11 | Java | Écosystème data science, lisibilité |
| **Stockage** | MySQL 8.0 | PostgreSQL | Simplicité, compatibilité JDBC, support transactionnel |
| **Connecteur** | MySQL Connector/J 8.0.33 | JDBC natif Spark | Driver officiel Oracle, performances optimales |
| **Environnement dev** | Jupyter Notebook | VS Code| Interactivité, visualisation en ligne |

### Justification MySQL vs PostgreSQL

| Critère | MySQL | PostgreSQL | Choix retenu |
|---------|-------|------------|--------------|
| Performance SELECT | ⭐⭐⭐ | ⭐⭐ | **MySQL** (OLAP léger) |
| JSON natif | ⭐⭐ (depuis 8.0) | ⭐⭐⭐ | PostgreSQL meilleur, mais MySQL suffisant |
| Intégration Spark | ⭐⭐⭐ (natif) | ⭐⭐⭐ (natif) | Équivalent |
| Facilité setup | ⭐⭐⭐ | ⭐⭐ | **MySQL** (plus simple) |
| Coût opérationnel | Gratuit (Community) | Gratuit (Open Source) | Équivalent |

**Décision** : MySQL retenu pour sa simplicité dans un contexte pédagogique

---

## 🥉🥈🥇 Architecture médaillée


### Couche Bronze (Raw Data)

**Rôle** : Zone de staging des données brutes

**Caractéristiques** :
- Format : DataFrame Spark en mémoire (non persisté)
- Schéma : Inféré automatiquement depuis CSV
- Transformations : **Aucune** (lecture pure)
- Durée de vie : Temporaire (session Spark)

**Implémentation** :
```python
bronze_df = spark.read \
    .option("header", "true") \
    .option("sep", "\t") \
    .option("quote", '"') \
    .option("escape", '"') \
    .option("multiLine", "true") \
    .option("mode", "PERMISSIVE") \  # Tolérance erreurs
    .csv(csv_path)
```

**Design pattern** : **Schema-on-read** (pas de validation stricte)

---

### Couche Silver (Clean Data)

**Rôle** : Zone de données nettoyées et validées

**Caractéristiques** :
- Format : Table MySQL InnoDB
- Schéma : Défini explicitement (17 colonnes)
- Transformations : Nettoyage, validation, enrichissement
- Durée de vie : Persisté (remplacé à chaque exécution)

**Transformations clés** :
1. **Sélection de colonnes** : 215 → 17 (réduction 92%)
2. **Normalisation Unicode** : NFD → ASCII
3. **Validation par plages** : Seuils nutritionnels
4. **Enrichissement** : Calcul energy_kj, sodium/sel
5. **Déduplication** : Par code-barres + date

**Mode d'écriture** :
```python
silver_final.write.jdbc(
    url=jdbc_url,
    table="silver_products",
    mode="overwrite",  # Remplacement complet
    properties=connection_props
)
```

**Design pattern** : **Data Quality Firewall** (validation stricte en entrée)

---

### Couche Gold (Analytical Data)

**Rôle** : Datamart optimisé pour requêtes OLAP

**Caractéristiques** :
- Format : 6 tables MySQL (5 dimensions + 1 fait)
- Schéma : Star Schema (dénormalisé pour performance)
- Transformations : Normalisation dimensionnelle, lookup FK
- Durée de vie : Persisté (historisation future avec SCD)

**Architecture** :
- **Modèle** : Star Schema (étoile simple, pas de flocon)
- **Granularité fait** : 1 snapshot nutritionnel par produit × date
- **Stratégie FK** : Lookup depuis Silver via jointures Spark
- **Indexes** : Sur toutes PK et FK

---

## ⭐ Schéma de données Gold

### Diagramme entité-association

```
┌─────────────────────┐
│     dim_time        │
│ ─────────────────── │
│ PK: time_sk         │◄──┐
│     date            │   │
│     year, month...  │   │
└─────────────────────┘   │
                          │
┌─────────────────────┐   │   ┌───────────────────────────┐
│    dim_brand        │   │   │  fact_nutrition_snapshot  │
│ ─────────────────── │   │   │ ───────────────────────── │
│ PK: brand_sk        │◄──┼───┤ PK: fact_id               │
│     brand_name      │   │   │ FK: product_sk            │
└─────────────────────┘   │   │ FK: time_sk               │
                          │   │     energy_kcal_100g      │
┌─────────────────────┐   │   │     fat_100g, sugars...   │
│   dim_category      │   │   │     nutriscore_grade      │
│ ─────────────────── │   │   └───────────────────────────┘
│ PK: category_sk     │◄──┤              ▲
│     category_name   │   │              │
│     parent_cat_sk   │   │              │
└─────────────────────┘   │              │
                          │   ┌──────────┴─────────┐
┌─────────────────────┐   │   │   dim_product      │
│   dim_country       │   │   │ ────────────────── │
│ ─────────────────── │   │   │ PK: product_sk     │
│ PK: country_sk      │   │   │     code           │
│     countries_name  │   │   │ FK: brand_sk       │
└─────────────────────┘   │   │ FK: primary_cat_sk │
                          └───┤     product_name   │
                              │     countries...   │
                              └────────────────────┘
```

### Types de dimensions

| Dimension | Type SCD | Historisation | Justification |
|-----------|----------|---------------|---------------|
| dim_time | Type 0 (statique) | Non | Calendrier immuable |
| dim_brand | Type 1 (overwrite) | Non | Modifications marque rares |
| dim_category | Type 1 | Non | Taxonomie stable |
| dim_country | Type 1 | Non | Géographie statique |
| dim_product | Type 1 | **À évoluer vers Type 2** | Tracking changements produits |

**Recommandation future** : Implémenter SCD Type 2 sur `dim_product` avec colonnes :
- `valid_from` (DATE)
- `valid_to` (DATE, NULL = actif)
- `is_current` (BOOLEAN)

---

## 🔄 Stratégie de chargement

### Mode actuel : Full Overwrite

**Principe** : Remplacement complet des données à chaque exécution

**Séquence** :
```sql
-- Étape 1 : Désactiver contraintes FK (éviter blocages)
SET FOREIGN_KEY_CHECKS = 0;

-- Étape 2 : Truncate des tables (vidage)
TRUNCATE TABLE dim_time;
TRUNCATE TABLE dim_brand;
TRUNCATE TABLE dim_category;
TRUNCATE TABLE dim_country;
TRUNCATE TABLE dim_product;
TRUNCATE TABLE fact_nutrition_snapshot;

-- Étape 3 : Réactiver contraintes
SET FOREIGN_KEY_CHECKS = 1;

-- Étape 4 : Insertion via Spark JDBC (mode append)
spark_df.write.jdbc(..., mode="append")
```

**Avantages** :
- ✅ Simplicité extrême (pas de gestion d'état)
- ✅ Garantie cohérence (snapshot complet)
- ✅ Idempotence (relancer = même résultat)

**Inconvénients** :
- ❌ Perte d'historique (pas de versioning)
- ❌ Temps de traitement croissant (linéaire avec volume)
- ❌ Fenêtre de downtime (tables vides pendant truncate)

---

### Évolution future : Upsert incrémental

**Stratégie recommandée pour production** :

#### Étape 1 : Détection des changements

**Source CDC** : API Open Food Facts (`/cgi/search.pl?last_modified_t>`)

```python
# Récupérer uniquement les produits modifiés depuis le dernier run
last_run_ts = get_last_watermark()  # Ex: 1640000000
new_products_df = spark.read.json(
    f"https://world.openfoodfacts.org/cgi/search.pl?json=1&last_modified_t>{last_run_ts}"
)
```

#### Étape 2 : Upsert via MERGE (MySQL 8.0.19+)

```sql
-- Insertion/Mise à jour dim_product
MERGE INTO dim_product AS target
USING staging_product AS source
ON target.code = source.code
WHEN MATCHED THEN
    UPDATE SET 
        product_name = source.product_name,
        brand_sk = source.brand_sk,
        modified_date = source.modified_date
WHEN NOT MATCHED THEN
    INSERT (code, product_name, brand_sk)
    VALUES (source.code, source.product_name, source.brand_sk);
```

**Alternative Spark** : Utiliser `.mode("overwrite")` avec condition :
```python
# Pseudo-code
existing_df = spark.read.jdbc(..., "dim_product")
new_df = silver_df.filter(col("last_modified_t") > watermark)

merged_df = existing_df.join(new_df, "code", "full_outer") \
    .select(coalesce(new_df.col, existing_df.col))

merged_df.write.jdbc(..., mode="overwrite")
```

#### Étape 3 : SCD Type 2 sur dim_product

**Schéma étendu** :
```sql
ALTER TABLE dim_product ADD COLUMN (
    valid_from DATE NOT NULL,
    valid_to DATE DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE
);
```

**Logique d'upsert** :
```python
# Si le produit existe et a changé
if product_changed:
    # 1. Fermer l'ancienne version
    UPDATE dim_product 
    SET valid_to = CURRENT_DATE, is_current = FALSE
    WHERE code = ? AND is_current = TRUE
    
    # 2. Insérer nouvelle version
    INSERT INTO dim_product (..., valid_from, is_current)
    VALUES (..., CURRENT_DATE, TRUE)
```

---

## ⚡ Performance et scalabilité

### Optimisations implémentées

#### 1. Partitionnement Spark

**Configuration locale** :
```python
spark = SparkSession.builder \
    .master("local[1]") \  # 1 seul worker (machine locale)
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.memory", "4g") \
    .getOrCreate()
```

**Configuration cluster (future)** :
```python
spark = SparkSession.builder \
    .master("spark://master:7077") \
    .config("spark.executor.instances", "4") \
    .config("spark.executor.cores", "4") \
    .config("spark.executor.memory", "8g") \
    .getOrCreate()
```

**Projection** : Avec 4 exécuteurs, traitement estimé à 2 minutes (vs 8 actuellement)

---

## 📊 Monitoring et observabilité

### Métriques clés

**Implémentation** :
```python
# Génération metrics_AAAAMMDD_HHMMSS.json
metrics = {
    "timestamp": datetime.now().isoformat(),
    "duree_minutes": (end_time - start_time).seconds / 60,
    "lignes_traitees": silver_final.count(),
    "lignes_rejetees": bronze_df.count() - silver_final.count(),
    "taux_completude_moyen": df_fact.agg({"completeness_score": "avg"}).first()[0],
    "status": "SUCCESS"
}
```