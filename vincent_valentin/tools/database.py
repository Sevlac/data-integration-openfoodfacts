import mysql.connector
from mysql.connector import Error

class DatabaseManager:
    def __init__(self, host="localhost", user="root", password="root"):
        self.config = {
            'host': host,
            'user': user,
            'password': password
        }

    def _get_connection(self, db_name=None):
        """Méthode interne pour obtenir une connexion."""
        config = self.config.copy()
        if db_name:
            config['database'] = db_name
        return mysql.connector.connect(**config)

    def setup_database(self, db_name):
        """Supprime la base si elle existe, puis la crée à nouveau."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 1. Suppression de la base existante
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            print(f"🗑️ Ancienne base '{db_name}' supprimée.")
            
            # 2. Création de la nouvelle base
            cursor.execute(f"CREATE DATABASE {db_name} DEFAULT CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_unicode_ci'")
            print(f"✅ Base de données '{db_name}' créée à neuf.")
            
            cursor.close()
            conn.close()
            
            # 3. APPELS DES MÉTHODES DE CRÉATION DE TABLES
            # On appelle les méthodes internes pour structurer la base fraîchement créée
            self._create_silver_table(db_name)
            self._create_gold_tables(db_name)

        except Error as e:
            print(f"❌ Erreur lors de l'initialisation : {e}")

    def _create_silver_table(self, db_name):
        query = f"""
        CREATE TABLE IF NOT EXISTS {db_name}.silver_products (
            code VARCHAR(50) PRIMARY KEY,
            product_name VARCHAR(255),
            brands VARCHAR(255),
            main_category VARCHAR(255),
            categories_en TEXT,
            countries_en JSON,
            nutriscore_grade VARCHAR(20),
            energy_kcal_100g FLOAT,
            energy_kj_100g FLOAT,
            fat_100g FLOAT,
            saturated_fat_100g FLOAT,
            sugars_100g FLOAT,
            salt_100g FLOAT,
            proteins_100g FLOAT,
            fiber_100g FLOAT,
            sodium_100g FLOAT,
            completeness FLOAT,
            last_modified_t BIGINT
        ) ENGINE=InnoDB;
        """
        # On utilise ta méthode interne qui crée 'conn' localement
        conn = self._get_connection(db_name) 
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            conn.commit()  # On utilise 'conn' (la variable locale) et non 'self.conn'
            print(f"✅ Table 'silver_products' prête dans '{db_name}'.")
        except Error as e:
            print(f"❌ Erreur lors de la création de la table silver : {e}")
        finally:
            cursor.close()
            conn.close() # Très important : on ferme la connexion locale 

    def _create_gold_tables(self, db_name):
        queries = [
            # 1. Dim Time OK
            f"""CREATE TABLE IF NOT EXISTS {db_name}.dim_time (
                time_sk INT PRIMARY KEY,
                date DATE,
                year INT,
                month INT,
                day INT,
                week INT,
                iso_week INT
            ) ENGINE=InnoDB;""",

            # 2. Dim Brand OK
            f"""CREATE TABLE IF NOT EXISTS {db_name}.dim_brand (
                brand_sk INT AUTO_INCREMENT PRIMARY KEY,
                brand_name VARCHAR(500) UNIQUE
            ) ENGINE=InnoDB;""",

            # 3. Dim Country OK
            f"""CREATE TABLE IF NOT EXISTS {db_name}.dim_country (
                country_sk INT AUTO_INCREMENT PRIMARY KEY,
                countries_name JSON
            ) ENGINE=InnoDB;""",

            # 4. Dim Category OK
            f"""CREATE TABLE IF NOT EXISTS {db_name}.dim_category (
                category_sk INT AUTO_INCREMENT PRIMARY KEY,
                category_name VARCHAR(500) UNIQUE,
                parent_category_sk VARCHAR(255)
            ) ENGINE=InnoDB;""",

            # 5. Dim Product OK
            f"""CREATE TABLE IF NOT EXISTS {db_name}.dim_product (
                product_sk INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(255) UNIQUE,
                product_name VARCHAR(500),
                brand_sk INT,
                primary_category_sk INT,
                countries_multi_name JSON,
                FOREIGN KEY (brand_sk) REFERENCES dim_brand(brand_sk),
                FOREIGN KEY (primary_category_sk) REFERENCES dim_category(category_sk)
            ) ENGINE=InnoDB;""",

            # 6. Table de Faits Nutritionnels OK
            f"""CREATE TABLE IF NOT EXISTS {db_name}.fact_nutrition_snapshot (
                fact_id INT AUTO_INCREMENT PRIMARY KEY,
                product_sk INT,
                time_sk INT,
                energy_kcal_100g FLOAT,
                fat_100g FLOAT,
                saturated_fat_100g FLOAT,
                sugars_100g FLOAT,
                salt_100g FLOAT,
                proteins_100g FLOAT,
                fiber_100g FLOAT,
                sodium_100g FLOAT,
                nutriscore_grade VARCHAR(20),
                completeness_score FLOAT,
                FOREIGN KEY (product_sk) REFERENCES dim_product(product_sk),
                FOREIGN KEY (time_sk) REFERENCES dim_time(time_sk)
            ) ENGINE=InnoDB;""",
        ]
        
        conn = self._get_connection(db_name)
        cursor = conn.cursor()
        for q in queries:
            cursor.execute(q)
        conn.commit()
        cursor.close()
        conn.close()

    def get_jdbc_params(self, db_name):
        """Retourne les paramètres pour Spark."""
        url = f"jdbc:mysql://{self.config['host']}:3306/{db_name}"
        props = {
            "user": self.config['user'],
            "password": self.config['password'],
            "driver": "com.mysql.cj.jdbc.Driver"
        }
        return url, props