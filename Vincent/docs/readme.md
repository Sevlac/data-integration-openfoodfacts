# Projet ETL Open Food Facts
## Pipeline de données nutritionnelles avec architecture médaillée

---

## 📋 Vue d'ensemble

Ce projet implémente un pipeline ETL (Extract, Transform, Load) complet pour traiter et structurer les données nutritionnelles d'Open Food Facts. Il utilise une architecture médaillée (Bronze → Silver → Gold) et transforme des données brutes en un datamart analytique optimisé.

Le travail effectué sur les données, à été réalisé sur un échantillon correspondant à 10% des données finales.

### Objectifs du projet

- **Ingestion** : Charger des données brutes (CSV) dans une zone Bronze
- **Nettoyage** : Normaliser et valider les données dans une couche Silver
- **Modélisation** : Construire un schéma en étoile (Star Schema) dans la couche Gold
- **Analyse** : Permettre des requêtes analytiques sur les données nutritionnelles

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    BRONZE LAYER                         │
│  Données brutes CSV (Open Food Facts)                  │
│  ├─ 418,676 lignes                                     │
│  └─ 215 colonnes                                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    SILVER LAYER                         │
│  Données nettoyées et normalisées (MySQL)              │
│  ├─ Table: silver_products                             │
│  ├─ 418,651 lignes (après déduplication)               │
│  └─ 17 colonnes sélectionnées                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                     GOLD LAYER                          │
│  Datamart analytique - Schéma en étoile (MySQL)        │
│  ├─ dim_time (dimension temporelle)                    │
│  ├─ dim_brand (marques)                                │
│  ├─ dim_category (catégories)                          │
│  ├─ dim_country (pays)                                 │
│  ├─ dim_product (produits)                             │
│  └─ fact_nutrition_snapshot (faits nutritionnels)      │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack technologique

| Composant | Technologie | Version | Rôle |
|-----------|-------------|---------|------|
| **Processing** | Apache Spark | 3.x | Transformation des données à grande échelle |
| **Langage** | Python | 3.11.9 | Orchestration du pipeline |
| **Base de données** | MySQL | 8.0 | Stockage Silver & Gold |
| **Connecteur** | MySQL Connector/J | 8.0.33 | JDBC pour Spark ↔ MySQL |
| **Environnement** | Jupyter Notebook | - | Développement interactif |

---

## 📂 Structure du projet

```
openfood_etl/
│
├── docs/
│   ├── README.md                    # Ce fichier
│   ├── data_dictionary.md           # Dictionnaire de données
│   ├── quality_report.md            # Cahier de qualité
│   └── architecture_notes.md        # Note d'architecture
│
├── etl/
│   ├── pipeline_etl.ipynb           # Pipeline principal Spark
│   └── tools/
│       └── database.py              # Gestionnaire MySQL
│
├── sql/
│   └── requetes_analytiques.sql     # Requêtes métiers
│
├── data/
│   └── donnees_echantillon.csv      # Données source (non versionné)
│
├── driver/
│   └── mysql-connector-j-8.0.33/    # Driver JDBC
│
│
├── requirements.txt                 # Dépendances Python
└── metrics/
    └── metrics_AAAAMMDD_HHMMSS.json # Métriques d'exécution 
```
---

## 🔄 Flux de traitement détaillé

### Phase 1️⃣ : Ingestion Bronze

**Objectif** : Charger les données brutes sans transformation

```python
bronze_df = spark.read \
    .option("header", "true") \
    .option("sep", "\t") \
    .option("multiLine", "true") \
    .csv(csv_path)
```

**Résultat** :
- ✅ 418,676 lignes chargées
- ✅ 215 colonnes préservées
- ✅ Données brutes intactes

### Phase 2️⃣ : Nettoyage Silver

**Transformations appliquées** :

1. **Sélection de colonnes** (215 → 17 colonnes pertinentes)
2. **Normalisation textuelle** :
   - Conversion en minuscules
   - Suppression des caractères spéciaux
   - Normalisation Unicode (NFD → ASCII)
   - Trim des espaces
3. **Gestion des valeurs manquantes** :
   - Remplacement par valeurs par défaut sémantiques
   - `"undefined"`, `"null"`, `"unknown"` → valeurs métiers
4. **Validation des données nutritionnelles** :
   - Filtrage par seuils biologiques (0-100g pour nutriments)
   - Conversion sodium ↔ sel (facteur 2.5)
   - Calcul energy_kj à partir de energy_kcal (×4.184)
5. **Déduplication** :
   - Basée sur le code-barres unique
   - Conservation de la version la plus récente (last_modified_t)
6. **Conversion temporelle** :
   - Unix timestamp → Date SQL

**Résultat** :
- ✅ 418,651 lignes (25 doublons supprimés)
- ✅ 17 colonnes structurées
- ✅ Données validées et cohérentes

### Phase 3️⃣ : Modélisation Gold

**Architecture en étoile (Star Schema)** :

#### Tables de dimensions

1. **dim_time** : Calendrier des modifications
   - Clé : `time_sk` (timestamp Unix)
   - Attributs : date, année, mois, jour, semaine

2. **dim_brand** : Marques de produits
   - Clé : `brand_sk` (AUTO_INCREMENT)
   - Attributs : `brand_name` (unique)

3. **dim_category** : Catégories hiérarchiques
   - Clé : `category_sk` (AUTO_INCREMENT)
   - Attributs : `category_name`, `parent_category_sk`

4. **dim_country** : Pays de vente
   - Clé : `country_sk` (AUTO_INCREMENT)
   - Attributs : `countries_name` (JSON)

5. **dim_product** : Catalogue produits
   - Clé : `product_sk` (AUTO_INCREMENT)
   - Clés étrangères : `brand_sk`, `primary_category_sk`
   - Attributs : code-barres, nom, pays

#### Table de faits

**fact_nutrition_snapshot** : Snapshots nutritionnels
- Clés étrangères : `product_sk`, `time_sk`
- Métriques : 8 nutriments + nutriscore + complétude

**Résultat** :
- ✅ Schéma normalisé (3NF dans les dimensions)
- ✅ Optimisé pour les requêtes analytiques
- ✅ Intégrité référentielle garantie

---

## 📚 Références

- [Open Food Facts](https://world.openfoodfacts.org/) - Source des données
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [MySQL 8.0 Reference](https://dev.mysql.com/doc/refman/8.0/en/)
- [Architecture médaillée Databricks](https://www.databricks.com/glossary/medallion-architecture)
