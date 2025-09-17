import os
import io
import time
import boto3
import psycopg2
import base64
import streamlit as st
from PIL import Image

from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from utils.db_connection import create_db_connection
from botocore.handlers import disable_signing

# Custom Header Section
logo_path = "code/edb_new.png"
primary_color = "#FF4B33"


header_css = f"""
<style>
.header {{
    padding: 10px;
    color: white;
}}
a {{
    color: {primary_color};
    padding: 0 16px;
    text-decoration: none;
    font-size: 16px;
}}
</style>
"""

st.markdown(header_css, unsafe_allow_html=True)

col1, col2 = st.columns([1, 4])

with col1:
    st.image(logo_path, width=150)

with col2:
    st.markdown(
        f"""
    <div class="header">
        <a href="#" target="_blank">Products</a>
        <a href="#" target="_blank">Solutions</a>
        <a href="#" target="_blank">Resources</a>
        <a href="#" target="_blank">Company</a>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Streamlit UI for Image Similarity Search
st.title("Intelligent Shopping Experience")
st.markdown("## EDB Postgres AI")



# Build database URL with proper error handling
db_user = os.getenv("DB_USER") or ""
db_host = os.getenv("DB_HOST") or "localhost"
db_port = os.getenv("DB_PORT") or "5432"
db_name = os.getenv("DB_NAME") or ""

DATABASE_URL = "postgresql://%s@%s:%s/%s" % (
    quote_plus(db_user), 
    db_host, 
    db_port, 
    db_name
)

engine = create_engine(DATABASE_URL)

@st.cache_data
def get_categories():
    query = text("SELECT DISTINCT masterCategory FROM products order by 1;")
    with engine.connect() as connection:
        result = connection.execute(query)
        # Fetch the result set as a list of dictionaries for easier access
        categories = [row["mastercategory"] for row in result.mappings().all()]
    return categories

@st.cache_data
def get_genders():
    query = text("SELECT DISTINCT gender FROM products order by 1;")
    with engine.connect() as connection:
        result = connection.execute(query)
        # Fetch the result set as a list of dictionaries for easier access
        genders = [row["gender"] for row in result.mappings().all()]
    return genders


@st.cache_data
def get_products_by_category(category):
    query = text(
        "SELECT productDisplayName, product_idFROM products WHERE masterCategory = :category order by 1 limit 30;"
    )
    with engine.connect() as connection:
        result = connection.execute(query, {"category": category})
        # Convert the result to a list of dictionaries
        products = [
            {
                "name": row["productdisplayname"],
                "image_path": f'dataset/images/{row["img_id"]}.jpg',
            }
            for row in result.mappings().all()
        ]
    return products


@st.cache_data
def get_product_details_in_category(img_id):
    """
    Fetch product details for a given category by image ID.

    Args:
        product_id(str): The image ID to search for in the database.

    Returns:
        dict: A dictionary containing product name and image path.
    """

    query = text(
        "SELECT productDisplayName, product_id FROM products WHERE product_id = :img_id;"
    )

    with engine.connect() as connection:
        result = connection.execute(query, {"img_id": img_id})
        # Convert  result to a list of dictionaries
        product = result.mappings().first()

        if product:
            product_details = {
                "name": product["productdisplayname"],
                "image_path": f'dataset/images/{product["img_id"]}.jpg',
            }
        else:
            product_details = None
    return product_details

def display_image_s3(image_name, staging_bucket='public-ai-images'):
    s3 = boto3.resource(
        service_name="s3",
        endpoint_url='http://s3.eu-central-1.amazonaws.com',
    )
    s3.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)
    bucket = s3.Bucket(staging_bucket)
    obj = bucket.Object(image_name)
    response = obj.get()
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    st.image(image, caption=image_name, width=150)
    
    # s3.meta.client.upload_file(f'{file_path}', 'public-ai-team', f'{image_name}')

def search_catalog(text_query, selected_gender=None):
    """
    This function aims to use  aidb.retrieve_key() to do hybrid search
    Therefore over sampling on retrieving is required to get the best results
    Args:       
        text_query (str): The text query to search for in the database.
        selected_gender (str): 'Men', 'Women', 'Boys', 'Girls' or None
    Returns:
        None
    """
    conn = st.session_state.db_conn
    cur = conn.cursor()
    
    try:
        start_time = time.time()
        if selected_gender != "None":
        # Filter products through CLIP Model
        # This is a hybrid search using text and limited only with the number of images in the S3 bucket
        # Therefore this search is replaced with text retriever over products table

            cur.execute(
            f"""WITH filtered_products AS (
            -- First get all men's products
            SELECT img_id, productdisplayname
            FROM products 
            WHERE gender = '{selected_gender}'
        )
        SELECT 
            result.key as id,
            result.distance as score
        FROM filtered_products fp
        CROSS JOIN LATERAL aidb.retrieve_text('{st.session_state.text_retriever_name}', '{text_query}', 100) AS result
        WHERE result.key = fp.img_id
        ORDER BY score ASC LIMIT 11;"""
        )
        else:
            cur.execute(
                f"""SELECT * FROM aidb.retrieve_text('{st.session_state.text_retriever_name}', '{text_query}', 11);"""
            )
        results = cur.fetchall()
        keys = [row[0].split(',')[0].strip('()') for row in results]

       # Extract only the filenames from the results
        query_time = time.time() - start_time
        st.write(f"Querying similar catalog took {query_time:.4f} seconds.")
        if keys:
            st.write(f"Number of elements retrieved: {len(keys)}")
            for product_idin keys:
                product = get_product_details_in_category(img_id)
                if product:
                    col_img, col_button = st.columns([3, 1])
                    with col_img:
                        st.write(f"**{product['name']}**")
                        # uncomment the below two lines to display the image from local dataset folder
                        # image = Image.open(product["image_path"])
                        # st.image(image, width=150)
                        # display image from S3
                        result = product_id+ ".jpg" # Image name should include the extension
                        display_image_s3(result)
                    with col_button:
                        st.link_button("Review", f"/review_page/?review_item_id={img_id}")
        else:
            st.error("No results found.")

    except Exception as e:
        st.error("An error occurred: " + str(e))
    finally:
        cur.close()

st.session_state.text_retriever_name = "recommend_products"
st.session_state.img_retriever_name = "recom_images"
st.session_state.s3_bucket_name = "public-ai-team"
if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
    st.session_state.db_conn = create_db_connection()
# Load the text information data about products into db.
# load_data_to_db(st.session_state.db_conn, 'dataset/stylesc.csv')
# Using columns to create a two-part layout
left_column, right_column = st.columns([1, 1])  # Adjust the ratio as needed

with left_column:
    # Fetch and display categories in a selectbox
    categories = get_categories()
    selected_category = st.selectbox("Select a Category:", categories)

    if selected_category:
        # Fetch and display products for the selected category
        products = get_products_by_category(selected_category)
        for product in products:
            st.subheader(product["name"])
            if product["image_path"]:
                # Display the image if the path is not None or empty
                st.image(product["image_path"], width=150)
            else:
                st.write("No image available")
with right_column:
    # Text input for search query
    search_query = st.text_input("Enter search term:", "", key="search_query")
    selected_gender = st.selectbox("Select the gender:", ["None"] + get_genders())

    # File uploader for image
    uploaded_image = st.file_uploader(
        "Or upload an image to search:",
        type=["jpg", "jpeg", "png"],
        key="uploaded_image",
    )

    # Initialize a variable to track whether the search should be executed
    execute_search = False

    # Button for text search
    if search_query and st.button("Search with Text"):
        execute_search = True
        search_mode = "text"

    # Button for image search; always shown if there is an uploaded image, regardless of text search state
    if uploaded_image is not None and st.button("Search with Image"):
        execute_search = True
        search_mode = "image"

    # Assuming 'Reset' button click handling
    if st.button("Reset"):
        # Explicitly clear the session state keys for the inputs
        if "search_query" in st.session_state:
            del st.session_state.search_query
        if "uploaded_image" in st.session_state:
            del st.session_state.uploaded_image
        # Manually reset any other app-specific state here
        # Optionally, guide users to refresh the page for a full reset
        st.info("Please refresh the page to completely reset the application.")

    if execute_search:
        if search_mode == "text":
            st.write(f"Results for '{search_query}':")
            search_catalog(search_query, selected_gender)
        elif search_mode == "image":
            try:
                # Process and display the uploaded image
                image_name = uploaded_image.name
                bytes_data = uploaded_image.getvalue()
                encoded_data = base64.b64encode(bytes_data).decode('utf-8')
                image = Image.open(io.BytesIO(bytes_data))
                
                st.image(image, caption="Uploaded Image", use_container_width=True)
                # Generate embeddings for the uploaded image and search
                start_time = time.time()
                conn = st.session_state.db_conn
                cur = conn.cursor()

                with conn.cursor() as cur:
                    if selected_gender != "None":
                        cur.execute(
                        f"""WITH filtered_products AS (
                        -- First get all men's products
                        SELECT img_id, productdisplayname
                        FROM products 
                        WHERE gender = '{selected_gender}'
                    )
                    SELECT 
                        result.key as id,
                        result.distance as score
                    FROM filtered_products fp
                    CROSS JOIN LATERAL aidb.retrieve_key('{st.session_state.img_retriever_name}', decode('{encoded_data}', 'base64'), 40) AS result
                    WHERE result.key = CONCAT(fp.img_id, '.jpg')
                    ORDER BY score ASC LIMIT 5;"""
                    )
                    else:
                        cur.execute(
                            f"""SELECT aidb.retrieve_key('{st.session_state.img_retriever_name}', decode('{encoded_data}', 'base64'), 5);"""                 
                        )

                    results = cur.fetchall()
                    keys = [row[0].split(',')[0].strip('()') for row in results]
                    vector_time = time.time() - start_time
                    st.write(f"Fetching vector took {vector_time:.4f} seconds.")
                    if keys:
                        st.write(f"Number of elements retrieved: {len(keys)}")
                        for result in keys:
                            product_id= result.split(".")[0]
                            product = get_product_details_in_category(img_id)
                            if product:
                                col_img, col_button = st.columns([3, 1])
                                with col_img:
                                    st.write(f"**{product['name']}**")
                                    # uncomment the below two lines to display the image from local dataset folder
                                    # image = Image.open(product["image_path"])
                                    # st.image(image, width=150)
                                    # display image from S3
                                    result = product_id+ ".jpg" # Image name should include the extension
                                    display_image_s3(result)
                                with col_button:
                                    st.link_button("Review", f"/review_page/?review_item_id={img_id}")
                    else:
                        st.write("No results found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
            finally:
                cur.close()
