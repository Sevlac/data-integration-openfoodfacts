## 🚀 Installation et démarrage rapide

### Prérequis

- Python 3.11+
- MySQL Server 8.0+
- Java 8 ou 11 (pour Spark)
- 4 GB RAM minimum

### 1. Création du venv
**A la racine du projet**
```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```
### 2. Installation des dépendances

```bash
pip install -r requirements.txt
```
**Redemarrer le kernel après les installations**

**requirements.txt:**
```
pyspark==3.5.0
mysql-connector-python==8.0.33
jupyter==1.0.0
```
### 3. Création folder data

**Dans le répertoir Vincent créer un dossier data et placer le fichier csv télécharger **

- -> [Open Food Facts Data](https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz) 

**le renommer comme ceci : openfoodfacts.csv**

### 3. Exécution du pipeline

**Run le fichier pipeline_etl.ipynb**

---