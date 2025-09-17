import pandas as pd
import psycopg2
import time
import sys
import os
import json

from typing import Tuple, List
from io import StringIO

from psycopg2.extras import execute_batch
from psycopg2 import sql

# Add the parent directory of 'code' to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.db_connection import create_db_connection


def initialize_database(conn):
    """Initialize the database with required extensions and tables."""
    with conn.cursor() as cur:
        _create_extensions(cur)
        _create_tables(cur)
        # _populate_test_images_data(cur, '/dataset/images')


def _create_extensions(cur):
    """Create required extensions if they do not exist."""
    cur.execute("CREATE EXTENSION IF NOT EXISTS aidb cascade;")
    cur.execute("CREATE EXTENSION IF NOT EXISTS pgfs;")


def _create_tables(cur):
    """Create required tables."""
    cur.execute("DROP TABLE IF EXISTS products CASCADE;")
    cur.execute("DROP TABLE IF EXISTS product_review;")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT,
            gender VARCHAR(50),
            masterCategory VARCHAR(100),
            subCategory VARCHAR(100),
            articleType VARCHAR(100),
            baseColour VARCHAR(50),
            season TEXT,
            year INTEGER,
            usage TEXT NULL,
            productDisplayName TEXT NULL
        );
    """
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS product_review(
            user_id TEXT,
            product_id TEXT,
            rating INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            review TEXT
    );"""
    )


def _populate_product_data(conn: psycopg2.extensions.connection, csv_file: str) -> None:
    # Create a string buffer
    # Read the train.csv file into a pandas dataframe, skipping bad lines
    df = pd.read_csv(csv_file, on_bad_lines="skip")
    output = StringIO()
    df_copy = df.copy()
    # Drop rows where any column value is empty
    df_copy = df_copy.dropna()
    # Convert year to integer if it's not already
    df_copy["year"] = df_copy["year"].astype("Int64")

    # Replace NaN with None for proper NULL handling in PostgreSQL
    df_copy = df_copy.replace({pd.NA: None, pd.NaT: None})
    df_copy = df_copy.where(pd.notnull(df_copy), None)
    print("Starting to populate products table")
    # Convert DataFrame to csv format in memory
    tuples: List[Tuple] = [tuple(x) for x in df_copy.to_numpy()]
    cols_list: List[str] = list(df_copy.columns)
    cols: str = ",".join(cols_list)
    placeholders: str = ",".join(
        ["%s"] * len(cols_list)
    )  # Create the correct number of placeholders
    # Create a parameterized query
    query: sql.SQL = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier("products"), sql.SQL(cols), sql.SQL(placeholders)
    )
    cursor: psycopg2.extensions.cursor = conn.cursor()
    try:
        execute_batch(cursor, query, tuples)
        conn.commit()
    except (Exception, psycopg2.Error) as error:
        print(f"Error while inserting data into PostgreSQL: {error}")
        conn.rollback()

    # Commit and close
    conn.commit()
    print("Finished populating products table")


def insert_dataframe(
    df: pd.DataFrame, table_name: str, connection: psycopg2.extensions.connection
) -> None:
    if pd.api.types.is_integer_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    tuples: List[Tuple] = [tuple(x) for x in df.to_numpy()]
    cols_list: List[str] = list(df.columns)
    cols: str = ",".join(cols_list)
    placeholders: str = ",".join(
        ["%s"] * len(cols_list)
    )  # Create the correct number of placeholders
    # Create a parameterized query
    query: sql.SQL = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name), sql.SQL(cols), sql.SQL(placeholders)
    )
    cursor: psycopg2.extensions.cursor = connection.cursor()
    try:
        execute_batch(cursor, query, tuples)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        print(f"Error while inserting data into PostgreSQL: {error}")
        connection.rollback()
    finally:
        cursor.close()


def populate_product_review_data(
    conn: psycopg2.extensions.connection, csv_file: str
) -> None:
    try:
        product_review: pd.DataFrame = pd.read_csv(csv_file, on_bad_lines="skip")[
            ["user_id", "product_id", "rating", "timestamp", "review"]
        ]
        insert_dataframe(product_review, "product_review", conn)
        print(
            f"DataFrame successfully written to the 'product_review' table in the database."
        )

    except psycopg2.OperationalError as e:
        print(f"Error connecting to PostgreSQL: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def _populate_test_images_data(cur, image_folder):
    """Populate test_images_data table with images from the specified folder."""
    for image_name in os.listdir(image_folder):
        try:
            image_path = os.path.join(image_folder, image_name)
            print(image_path)
            cur.execute(
                """
                INSERT INTO test_images_data (name, image_data)
                VALUES (%s, pg_read_binary_file(%s)::bytea)
                ON CONFLICT (name) DO NOTHING;
            """,
                (image_name, image_path),
            )

        except Exception as e:
            pass


def create_and_refresh_retriever(conn):
    """Create and retriever with bytea image data"""

    with conn.cursor() as cur:
        start_time = time.time()
        # Run for S3 bucket
        # The idea is to create a retriever for the images bucket so the image search can run over it.
        try:
            cur.execute(
                """SELECT pgfs.create_storage_location('image_bucket_srv', 's3://public-ai-images', options => '{"region":"eu-central-1", "skip_signature": "true"}');"""
            )
            cur.execute(
                """SELECT aidb.create_volume('images_bucket_vol', 'image_bucket_srv', '/', 'Image');"""
            )
            cur.execute(
                """SELECT aidb.create_model('multimodal_clip', 'clip_local');"""
            )
            cur.execute(
                """
                SELECT aidb.create_volume_knowledge_base(
                name => 'recom_images'
                ,model_name => 'multimodal_clip'
                ,source_volume_name => 'images_bucket_vol'
                ,batch_size => 500
            );
            """
            )
            cur.execute(f"""SELECT aidb.bulk_embedding('recom_images');""")
            vector_time = time.time() - start_time
            print(
                f"Creating and refreshing recom_images retriever took {vector_time:.4f} seconds."
            )
            start_time = time.time()
            # Run retriever for products table
            # The idea is to create a retriever for the products table so the text search can run over it.
            config = json.dumps({
                "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "revision": "main"
            })
            cur.execute(
                f"""SELECT aidb.create_model('text-embedding', 
                            'bert_local', 
                            '{config}'::JSONB);"""
            )

            cur.execute(
                """SELECT aidb.create_table_knowledge_base(
                        name => 'recommend_products'
                        ,model_name => 'text-embedding'
                        ,source_table => 'products'
                        ,source_key_column => 'product_id'
                        ,source_data_column => 'productdisplayname'
                        ,source_data_format => 'Text'
                        ,auto_processing =>'Live'
                        ,batch_size => 1000
                        );"""
            )
            # Create the GenAI Model for summary and level generation
            # for the review page. If the model is already exist, aidb will skip it.
            # Use below for the NIM model creation
            genai_config = json.dumps({
                "model": "llama3.2-vision",
                "url": "http://localhost:11434/v1/chat/completions"
            })
            cur.execute(
                f"""SELECT aidb.create_model('product_review_model', 'completions', '{genai_config}'::JSONB);"""
            )

            # Use below command instead of upper one for the remote model creation
            # cur.execute(
            #     f"""select aidb.create_model('product_review_model', 'completions', '{{"model":"llama-31-8b-instruct", "url":"https://llama-31-8b-instruct-samouelian-edb-ai.apps.ai-dev01.kni.syseng.devcluster.openshift.com/v1/chat/completions"}}'::JSONB);"""
            # )
        except Exception as e:
            print(f"Error creating retriever for images: {e}")

        cur.execute(f"""SELECT aidb.bulk_embedding('recommend_products');""")
        vector_time = time.time() - start_time
        print(
            f"Creating and refreshing recom_products retriever took {vector_time:.4f} seconds."
        )


def main():
    conn = None
    try:
        conn = create_db_connection()  # Connect to the database
        conn.autocommit = True  # Enable autocommit for creating the database
        start_time = time.time()
        initialize_database(
            conn
        )  # Initialize the db with aidb, pgfs extensions and necessary tables
        _populate_product_data(
            conn, "dataset/updated_stylesc.csv"
        )  # Populate the products table with the stylesc.csv data
        populate_product_review_data(conn, "dataset/product_reviews.csv")
        create_and_refresh_retriever(
            conn
        )  # Create and refresh the retriever for the products table and images bucket
        vector_time = time.time() - start_time
        print(f"Total process time: {vector_time:.4f} seconds.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
