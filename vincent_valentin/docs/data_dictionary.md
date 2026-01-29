# Dictionnaire de données
## Projet ETL Open Food Facts

---

## 📘 Table des matières

1. [Couche Silver](#couche-silver)
2. [Couche Gold - Dimensions](#couche-gold---dimensions)
3. [Couche Gold - Table de faits](#couche-gold---table-de-faits)
4. [Règles métiers](#règles-métiers)
5. [Cardinalités](#cardinalités)

---

## 🥈 Couche Silver

### Table : `silver_products`

Table intermédiaire contenant les données nettoyées et normalisées.

| Colonne | Type | Nullable | Description | Exemple | Traitement appliqué |
|---------|------|----------|-------------|---------|---------------------|
| `code` | VARCHAR(50) | ❌ PK | Code-barres EAN/UPC du produit | `3017620422003` | Dédoublonnage, trim |
| `product_name` | VARCHAR(255) | ✅ | Nom commercial du produit | `nutella pate a tartiner` | Normalisation ASCII, minuscules |
| `brands` | VARCHAR(255) | ✅ | Marque(s) du produit | `ferrero` | Nettoyage, défaut: `"marque inconnue"` |
| `main_category` | VARCHAR(255) | ✅ | Catégorie principale | `chocolate spreads` | Extraction 1er niveau, défaut: `"non classe"` |
| `categories_en` | TEXT | ✅ | Liste complète des catégories (EN) | `snacks,sweet spreads,hazelnut` | Normalisation, séparateur virgule |
| `countries_en` | JSON | ✅ | Pays de commercialisation (format JSON) | `"france,belgium"` | Formatage JSON, défaut: `"pays inconnu"` |
| `nutriscore_grade` | VARCHAR(20) | ✅ | Score nutritionnel (A-E) | `c` | Minuscule, défaut: `"non classe"` |
| `energy_kcal_100g` | FLOAT | ✅ | Énergie en kilocalories (pour 100g) | `539.0` | Validation [0-1000], arrondi 1 décimale |
| `energy_kj_100g` | FLOAT | ✅ | Énergie en kilojoules (pour 100g) | `2254.6` | Calculé (kcal × 4.184) |
| `fat_100g` | FLOAT | ✅ | Matières grasses totales (g/100g) | `30.9` | Validation [0-100], arrondi 1 décimale |
| `saturated_fat_100g` | FLOAT | ✅ | Acides gras saturés (g/100g) | `10.6` | Validation [0-100], arrondi 1 décimale |
| `sugars_100g` | FLOAT | ✅ | Sucres (g/100g) | `56.3` | Validation [0-100], arrondi 1 décimale |
| `salt_100g` | FLOAT | ✅ | Sel (g/100g) | `0.107` | Validation [0-100], coalesce avec sodium_est |
| `proteins_100g` | FLOAT | ✅ | Protéines (g/100g) | `6.3` | Validation [0-100], arrondi 1 décimale |
| `fiber_100g` | FLOAT | ✅ | Fibres alimentaires (g/100g) | `0.0` | Validation [0-100], arrondi 1 décimale |
| `sodium_100g` | FLOAT | ✅ | Sodium (g/100g) | `0.043` | Validation [0-40], coalesce avec salt_est |
| `completeness` | FLOAT | ✅ | Taux de complétude des données (0-1) | `0.5` | Validation [0-1], arrondi 1 décimale |
| `last_modified_t` | BIGINT | ✅ | Timestamp Unix de dernière modification | `1587580724` | Conversion date effectuée en aval |

**Contraintes** :
- **PRIMARY KEY** : `code`
- **ENGINE** : InnoDB
- **CHARSET** : utf8mb4_unicode_ci

---

## 🥇 Couche Gold - Dimensions

### Table : `dim_time`

Dimension calendaire basée sur les dates de modification des produits.

| Colonne | Type | Nullable | Description | Exemple |
|---------|------|----------|-------------|---------|
| `time_sk` | INT | ❌ PK | Surrogate key (timestamp Unix) | `1587580724` |
| `date` | DATE | ✅ | Date complète | `2020-04-22` |
| `year` | INT | ✅ | Année | `2020` |
| `month` | INT | ✅ | Mois (1-12) | `4` |
| `day` | INT | ✅ | Jour du mois (1-31) | `22` |
| `week` | INT | ✅ | Semaine de l'année | `17` |
| `iso_week` | INT | ✅ | Semaine ISO 8601 | `17` |

**Cardinalité** : ~50,000 enregistrements (jours uniques 2017-2025)

---

### Table : `dim_brand`

Dimension des marques de produits alimentaires.

| Colonne | Type | Nullable | Description | Exemple |
|---------|------|----------|-------------|---------|
| `brand_sk` | INT | ❌ PK | Clé de substitution auto-incrémentée | `1` |
| `brand_name` | VARCHAR(500) | ✅ UNIQUE | Nom de la marque normalisé | `nestle` |

**Contraintes** :
- **UNIQUE** : `brand_name`

**Cardinalité** : ~45,000 marques uniques

**Valeurs spéciales** :
- `"marque inconnue"` : Produits sans marque identifiée

---

### Table : `dim_category`

Dimension des catégories de produits avec hiérarchie.

| Colonne | Type | Nullable | Description | Exemple |
|---------|------|----------|-------------|---------|
| `category_sk` | INT | ❌ PK | Clé de substitution | `1` |
| `category_name` | VARCHAR(500) | ✅ UNIQUE | Nom de la catégorie | `chocolate spreads` |
| `parent_category_sk` | VARCHAR(255) | ✅ | Catégorie parente (niveau supérieur) | `spreads` |

**Cardinalité** : ~8,000 catégories

**Hiérarchie** :
- Niveau 1 : `parent_category_sk` (catégorie générale)
- Niveau 2 : `category_name` (catégorie spécifique)

**Valeurs spéciales** :
- `"non classe"` : Produits sans catégorie

---

### Table : `dim_country`

Dimension géographique des pays de vente.

| Colonne | Type | Nullable | Description | Exemple |
|---------|------|----------|-------------|---------|
| `country_sk` | INT | ❌ PK | Clé de substitution | `1` |
| `countries_name` | JSON | ✅ | Liste des pays (format JSON) | `"france,belgium"` |

**Cardinalité** : ~180 combinaisons de pays

**Format JSON** :
```json
"france,belgium,luxembourg"
```

---

### Table : `dim_product`

Dimension centrale des produits (fait de référence).

| Colonne | Type | Nullable | Description | Exemple |
|---------|------|----------|-------------|---------|
| `product_sk` | INT | ❌ PK | Clé de substitution | `1` |
| `code` | VARCHAR(255) | ✅ UNIQUE | Code-barres original | `3017620422003` |
| `product_name` | VARCHAR(500) | ✅ | Nom du produit | `nutella pate a tartiner` |
| `brand_sk` | INT | ✅ FK | Référence vers `dim_brand` | `42` |
| `primary_category_sk` | INT | ✅ FK | Référence vers `dim_category` | `128` |
| `countries_multi_name` | JSON | ✅ | Pays de vente (copié pour dénormalisation) | `"france"` |

**Contraintes** :
- **FOREIGN KEY** : `brand_sk` → `dim_brand(brand_sk)`
- **FOREIGN KEY** : `primary_category_sk` → `dim_category(category_sk)`

**Cardinalité** : 418,651 produits uniques

---

## 🥇 Couche Gold - Table de faits

### Table : `fact_nutrition_snapshot`

Table de faits contenant les données nutritionnelles par produit et par date.

| Colonne | Type | Nullable | Description | Plage valide | Exemple |
|---------|------|----------|-------------|--------------|---------|
| `fact_id` | INT | ❌ PK | Identifiant unique du snapshot | - | `1` |
| `product_sk` | INT | ✅ FK | Référence produit | - | `12345` |
| `time_sk` | INT | ✅ FK | Référence temporelle | - | `1587580724` |
| `energy_kcal_100g` | FLOAT | ✅ | Énergie (kcal/100g) | 0-1000 | `539.0` |
| `fat_100g` | FLOAT | ✅ | Matières grasses (g/100g) | 0-100 | `30.9` |
| `saturated_fat_100g` | FLOAT | ✅ | AG saturés (g/100g) | 0-100 | `10.6` |
| `sugars_100g` | FLOAT | ✅ | Sucres (g/100g) | 0-100 | `56.3` |
| `salt_100g` | FLOAT | ✅ | Sel (g/100g) | 0-100 | `0.107` |
| `proteins_100g` | FLOAT | ✅ | Protéines (g/100g) | 0-100 | `6.3` |
| `fiber_100g` | FLOAT | ✅ | Fibres (g/100g) | 0-100 | `0.0` |
| `sodium_100g` | FLOAT | ✅ | Sodium (g/100g) | 0-40 | `0.043` |
| `nutriscore_grade` | VARCHAR(20) | ✅ | Score nutritionnel | A,B,C,D,E | `c` |
| `completeness_score` | FLOAT | ✅ | Taux de complétude | 0-1 | `0.5` |

**Contraintes** :
- **FOREIGN KEY** : `product_sk` → `dim_product(product_sk)`
- **FOREIGN KEY** : `time_sk` → `dim_time(time_sk)`

**Cardinalité** : 418,651 snapshots (1 par produit à sa date de modification)

**Granularité** : 1 ligne = 1 produit à 1 instant T

---

## 📐 Règles métiers

### Normalisation des textes

**Algorithme appliqué** :
1. Normalisation Unicode (NFKC → NFD)
2. Conversion ASCII (suppression accents)
3. Minuscules
4. Suppression caractères spéciaux (conservation alphanumérique + espaces)
5. Trim + suppression espaces multiples

**Exemple** :
```
"Côte d'Or™ Chocolat" → "cote dor chocolat"
```

---

### Gestion des valeurs manquantes

| Type de donnée | Valeur manquante | Valeur par défaut |
|----------------|------------------|-------------------|
| Marque | NULL, "", "unknown" | `"marque inconnue"` |
| Catégorie | NULL, "", "undefined" | `"non classe"` |
| Pays | NULL, "" | `"pays inconnu"` |
| Nutriscore | NULL, "", "unknown" | `"non classe"` |
| Nutriments | NULL ou hors bornes | `NULL` (conservé) |

---

### Validation nutritionnelle

**Seuils biologiques** (si dépassés → NULL) :

| Nutriment | Min | Max | Unité | Justification |
|-----------|-----|-----|-------|---------------|
| Énergie (kcal) | 0 | 1000 | kcal/100g | Max théorique : huile pure (~900 kcal) |
| Matières grasses | 0 | 100 | g/100g | 100g de gras = 100g de produit max |
| Sucres | 0 | 100 | g/100g | Sucre pur = 100g/100g |
| Sel | 0 | 100 | g/100g | Conserve validité étendue |
| Sodium | 0 | 40 | g/100g | Sel pur = 40g sodium/100g (conversion ×2.5) |
| Protéines | 0 | 100 | g/100g | Protéine isolée = 100g/100g |
| Fibres | 0 | 100 | g/100g | Psyllium pur ≈ 80g fibres/100g |
| Complétude | 0 | 1 | ratio | Score Open Food Facts normalisé |

---

### Conversion sodium ↔ sel

**Formule chimique** : NaCl (39.3% de sodium en masse)

```python
# Sel → Sodium
sodium_100g = salt_100g / 2.5

# Sodium → Sel
salt_100g = sodium_100g * 2.5
```

**Stratégie de remplissage** :
1. Si `salt_100g` existe → conservation
2. Sinon, si `sodium_100g` existe → `salt_100g = sodium_100g × 2.5`
3. Inversement pour `sodium_100g`

---

### Conversion énergétique

**Formule de conversion** :
```
1 kcal = 4.184 kJ (norme internationale)
```

**Implémentation** :
```python
energy_kj_100g = energy_kcal_100g * 4.184
```

---

## 🥇 Couche Gold - Dimensions

### dim_time

**Type** : Dimension temporelle dégénérée (time_sk = valeur métier)

**Granularité** : Jour

**Origine** : Extraction de `silver_products.last_modified_t`

**Utilisation** :
- Analyse de tendances temporelles
- Filtres par année/mois/semaine
- Tracking de l'évolution des catalogues

---

### dim_brand

**Type** : Dimension de type 1 (SCD Type 1 - pas d'historisation)

**Clé naturelle** : `brand_name`

**Normalisation** :
- Minuscules
- Suppression accents et caractères spéciaux
- Troncature à 500 caractères

**Exemples de valeurs** :
- `nestle`
- `coca cola`
- `marque inconnue` (valeur par défaut)

---

### dim_category

**Type** : Dimension hiérarchique (2 niveaux)

**Structure** :
- `category_name` : Catégorie détaillée (feuille)
- `parent_category_sk` : Catégorie parent (racine)

**Exemple de hiérarchie** :
```
spreads (parent)
  └─ chocolate spreads (enfant)
  └─ peanut butter spreads (enfant)
```

**Navigation** :
```sql
-- Récupérer la hiérarchie complète
SELECT c.category_name, c.parent_category_sk
FROM dim_category c
WHERE c.category_name = 'chocolate spreads';
```

---

### dim_country

**Type** : Dimension multi-valuée (JSON)

**Stockage** : Liste de pays séparés par virgule, encapsulés en JSON

**Exemple** :
```json
"france,belgium,luxembourg"
```

**Requête** :
```sql
-- Produits vendus en France
SELECT * FROM dim_product
WHERE countries_multi_name LIKE '%france%';
```

---

### dim_product

**Type** : Dimension de référence principale (junk dimension partielle)

**Rôle** : Catalogue des produits avec leurs attributs descriptifs

**Relations** :
- **1:N** avec `fact_nutrition_snapshot`
- **N:1** avec `dim_brand`
- **N:1** avec `dim_category`

**Dénormalisation** :
- `countries_multi_name` : Copie depuis `dim_country` pour performance

---

## 🥇 Couche Gold - Table de faits

### fact_nutrition_snapshot

**Type** : Snapshot fact table (photo à un instant T)

**Granularité** : 1 ligne = 1 produit × 1 date de modification

**Métriques** :
- **Additives** : Toutes les colonnes `*_100g` (agrégables)
- **Semi-additives** : `completeness_score` (moyenne seulement)
- **Non-additives** : `nutriscore_grade` (mode/distribution)

**Stratégie de chargement** :
- **Mode** : Overwrite complet (pas d'incrémental dans cette v1)
- **Fréquence** : Batch quotidien (recommandé)
- **Durée** : ~8 minutes pour 418k produits

**Volumétrie** :
- Lignes : 418,651
- Taille estimée : ~50 MB (avec indexes)

---

## 🔗 Cardinalités

### Modèle conceptuel

```
dim_time (1) ←──────── (N) fact_nutrition_snapshot
dim_brand (1) ←──────┐
                      │
dim_category (1) ←────┼── (N) dim_product (1) ←── (N) fact_nutrition_snapshot
                      │
dim_country (1) ←─────┘
```

### Ratios observés

| Relation | Cardinalité moyenne | Note |
|----------|---------------------|------|
| Brand → Product | 1:9 | 9 produits par marque en moyenne |
| Category → Product | 1:52 | 52 produits par catégorie |
| Product → Fact | 1:1 | Snapshot unique par produit (v1) |

---

## 📊 Statistiques descriptives

### Distributions nutritionnelles (sur données non-NULL)

| Nutriment | Médiane | Moyenne | Écart-type | Q1 | Q3 |
|-----------|---------|---------|------------|----|----|
| Énergie (kcal) | 250 | 285 | 180 | 100 | 420 |
| Graisses | 8.5 | 15.2 | 18.3 | 1.5 | 22.0 |
| Sucres | 5.0 | 12.8 | 18.5 | 0.5 | 18.0 |
| Protéines | 6.0 | 9.5 | 11.2 | 2.5 | 12.0 |
| Sel | 0.5 | 1.2 | 2.1 | 0.1 | 1.5 |

### Distribution Nutriscore

| Grade | Pourcentage | Interprétation |
|-------|-------------|----------------|
| A | 15% | Excellente qualité nutritionnelle |
| B | 22% | Bonne qualité |
| C | 28% | Qualité moyenne |
| D | 20% | Qualité médiocre |
| E | 10% | Mauvaise qualité |
| Non classé | 5% | Données insuffisantes |

---

## 🔧 Exemples d'utilisation

### Jointure complète

```sql
SELECT 
    p.product_name,
    b.brand_name,
    c.category_name,
    f.nutriscore_grade,
    f.energy_kcal_100g,
    t.date as last_modified_date
FROM fact_nutrition_snapshot f
INNER JOIN dim_product p ON f.product_sk = p.product_sk
LEFT JOIN dim_brand b ON p.brand_sk = b.brand_sk
LEFT JOIN dim_category c ON p.primary_category_sk = c.category_sk
INNER JOIN dim_time t ON f.time_sk = t.time_sk
WHERE f.nutriscore_grade = 'a'
LIMIT 10;
```

---

## 📝 Notes importantes

### Limitations connues

1. **Historisation** : Pas de SCD Type 2 → modifications écrasent les anciennes valeurs
2. **Incrémental** : Mode overwrite uniquement (pas de CDC)
3. **Pays multiples** : Stockage JSON non indexé (requiert LIKE)

### Recommandations futures

- Implémenter SCD Type 2 pour `dim_product` (tracking modifications)
- Ajouter index sur `countries_multi_name` (Full-Text Search)
- Créer une table de jonction `bridge_product_country` pour normalisation

---

## 🔍 Traçabilité

| Couche | Table source | Table cible | Transformation clé |
|--------|--------------|-------------|-------------------|
| Bronze → Silver | CSV brut | `silver_products` | Nettoyage, validation, déduplication |
| Silver → Gold | `silver_products` | 5 dimensions + 1 fait | Normalisation 3NF, FK lookup |
