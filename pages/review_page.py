# pages/review_page.py
import streamlit as st
import os
import io
import boto3
import pandas as pd 
import re         
from PIL import Image
from botocore.handlers import disable_signing
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import psycopg2 
import streamlit_antd_components as sac

def create_db_connection():
    conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)
    return conn

# Reuse or redefine necessary functions/engine
DATABASE_URL = "postgresql://%s@%s:%s/%s" % (os.getenv("DB_USER"), os.getenv("DB_HOST"), os.getenv("DB_PORT"), os.getenv("DB_NAME"))

# Create engine within the page scope (or import from a utils file)
try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    st.error(f"Failed to create database engine: {e}")
    st.stop() # Stop execution if DB connection fails

if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
    st.session_state.db_conn = create_db_connection()

# --- Caching Functions ---
@st.cache_data # Cache the CSV reading
def load_reviews_data(csv_path):
    try:
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
        else:
            st.error(f"Reviews file not found at: {csv_path}")
            return None
    except Exception as e:
        st.error(f"Error loading reviews CSV: {e}")
        return None

# Cache the results of summary and label generation for a given product ID
# The _engine argument isn't used directly but forces rerun if engine changes (though unlikely here)
@st.cache_data(show_spinner="Generating review summary and labels...")
def get_summary_and_labels(_engine, review_string):
    """Generates summary and labels using AIDB via SQL"""
    summary_text = None
    final_labels = []
    model_name="product_review_model" # Model name for the AIDB
    if not review_string:
        st.info("No reviews available to generate summary and labels.")
        return summary_text, final_labels # Return None, empty list

    # --- Generate Summary ---
    summary_prompt = f"""Generate a concise summary (maximum 3 sentences) of the following user reviews. The summary should include positive and negative aspects of the reviews. Output *only* the summary text, without explanations or formatting. Always begin your response exactly with "Here is the summary:".

    Reviews:
    {review_string}"""
    query_summary = "SELECT decode_text FROM aidb.decode_text(%s, %s);"

    try:
        conn = st.session_state.db_conn
        with conn.cursor() as cur: # Use the passed engine
            # Execute Summary Query
            
            cur.execute(query_summary, (model_name, summary_prompt,))
            result_summary = cur.fetchone()
            if result_summary and result_summary[0]:
                raw_output = result_summary[0]
                # Clean the summary
                summary_text = re.sub(r"^Here is the summary:?\s*", "", raw_output, flags=re.IGNORECASE).strip()
                summary_text = summary_text.strip('```json').strip('```').strip() # Remove markdown fences

                if summary_text:
                    # --- Generate Labels (only if summary was successful) ---
                    label_prompt = f"""Extract a maximum of 5 concise labels (keywords or short phrases) from the following user review summary. The labels should represent both positive and negative aspects mentioned. Output *only* the labels as a single line of comma-separated values, with no introductory phrases, explanations, or formatting. Start outputting with "Here are the labels:".

                    Summary:
                    {summary_text}"""
                    query_labels = "SELECT decode_text FROM aidb.decode_text(%s, %s);"

                    cur.execute(query_labels, (model_name, label_prompt,))
                    result_labels = cur.fetchone()

                    if result_labels and result_labels[0]:
                        raw_labels_output = result_labels[0]
                        # Clean the labels
                        labels_string = raw_labels_output.strip()
                        labels_string = re.sub(r"^Here are the labels:?\s*", "", labels_string, flags=re.IGNORECASE).strip()

                        labels_list = [label.strip().rstrip('.') for label in labels_string.split(',') if label.strip()]
                        final_labels = labels_list[:5]
                    else:
                        st.warning("Failed to generate labels from the summary.")
                else:
                    st.warning("Summary generated was empty after cleaning.")
            else:
                st.warning("Failed to generate summary from the reviews.")

    except Exception as e:
        st.error(f"An error occurred during AI processing: {e}")
        # Optionally: Log the specific prompt that failed for debugging
        # st.error(f"Failed prompt (summary): {summary_prompt}")

    return summary_text, final_labels


@st.cache_data
def get_product_details_by_id(img_id):
    """ Fetch product details for a given image ID. """
    query = text("SELECT productDisplayName, product_idFROM products WHERE product_id= :img_id;")
    # Use the globally defined engine
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"img_id": img_id})
            product = result.mappings().first()
            if product:
                return {
                    "name": product["productdisplayname"],
                    "img_id": product["img_id"],
                }
            else:
                return None
    except Exception as e:
        st.error(f"Database error fetching product details: {e}")
        return None

def display_image_s3(image_name_with_extension, caption="", width=200, staging_bucket='public-ai-images'):
    """ Displays an image fetched directly from S3. """
    try:
        s3 = boto3.resource(
            service_name="s3",
            endpoint_url='http://s3.eu-central-1.amazonaws.com', # Make sure this endpoint is correct
        )
        s3.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)
        bucket = s3.Bucket(staging_bucket)
        obj = bucket.Object(image_name_with_extension)
        response = obj.get()
        image_data = response['Body'].read()
        image = Image.open(io.BytesIO(image_data))
        st.image(image, caption=caption if caption else image_name_with_extension, width=width)
        return True
    except Exception as e:
        st.error(f"Error loading image {image_name_with_extension} from S3: {e}")
        return False

# --- Page Logic ---

st.set_page_config(page_title="Review")
st.title("Review")
query_params = st.query_params
review_item_id = query_params.get("review_item_id")


# Check if an item ID was passed via session state
if review_item_id:
    item_id_str = review_item_id # Usually a string

    # --- Attempt to convert item_id to integer for CSV lookup ---
    # Adjust type (int, str) based on your 'product_id' column in the CSV
    try:
        item_id = int(item_id_str)
    except ValueError:
        st.error(f"Invalid Product ID format: {item_id_str}. Cannot look up reviews.")
        item_id = None # Ensure it's None if conversion fails


    # Fetch product details (using the string ID is likely fine for the products table)
    product_details = get_product_details_by_id(item_id_str)

    if product_details:
        st.subheader(product_details['name'])
        display_image_s3(f"{item_id_str}.jpg", width=300) # Display larger image
        st.markdown("---")

        # --- Load Reviews and Generate Summary/Labels ---
        if item_id is not None: # Proceed only if ID conversion was successful
            try:
                with engine.connect() as connection:
                    query = text("SELECT * FROM product_review WHERE product_id = :item_id;")
                    result = connection.execute(query, {"item_id": str(item_id)})
                filtered_reviews = result.mappings().all()
                # Convert to DataFrame for easier manipulation
                filtered_reviews = pd.DataFrame(filtered_reviews)
                if not filtered_reviews.empty and 'review' in filtered_reviews.columns:
                    
                    review_list = filtered_reviews["review"].dropna().tolist()
                    review_string = "\n".join(review_list)
                    # Get summary and labels using the cached function
                    summary, labels = get_summary_and_labels(engine, review_string) # Pass engine and ID
                    # Display Summary
                    st.subheader("Review Summary")
                    if summary:
                        st.write(summary)
                    else:
                        st.write("Could not generate a summary for this product's reviews.")

                    # Display Labels
                    st.subheader("Review Labels")
                    if labels:
                        # Display labels using st.chip for better visuals
                        cols = st.columns(len(labels))
                        items = []
                        for i, label in enumerate(labels):
                            items.append(sac.ChipItem(label=label))
                        sac.chip(items, size='sm', align='center', variant='filled', radius='md', multiple=True)
                    else:
                            st.write("No labels generated or found.")
                    # --- Display Reviews ---
                    st.subheader("Reviews")
                    # Display reviews in a list format
                    # Display only the top 5 reviews if they exist
                    reviews_to_display = filtered_reviews[["user_id", "review", "rating"]]
                    st.write(f"Found {len(reviews_to_display)} review(s):")
                    # Some products have many reviews and this could be a lot of text
                    # To avoid that, display only the top 5 reviews
                    top_reviews = reviews_to_display.head(5)
                    # Display the selected columns in a scrollable dataframe
                    for index, row in top_reviews.iterrows():
                        user = row["user_id"]
                        review = row["review"]
                        rate = int(row["rating"])

                        # Display using markdown for nice formatting
                        st.markdown(f"**User:** `{user}`") # Display user ID in backticks
                        st.markdown(f"**Rating:** {rate} Stars") # Display rating
                        st.markdown(f"**Review:**")
                        st.markdown(f"{review}") # Use blockquote for the review text
                        st.markdown("---") # Add a horizontal rule between reviews
                else:
                    st.info("No reviews found for this product in the dataset.")
            except KeyError as e:
                st.error(f"Column missing in reviews CSV: {e}. Please ensure 'product_id' and 'review' columns exist.")
            except Exception as e:
                    st.error(f"Error processing reviews: {e}")
        

        # --- Display Review Submission Form ---
        st.markdown("---")
        st.subheader("Submit Your Review")
        rating = st.slider("Rating (1-5 Stars)", 1, 5, 3)
        review_text = st.text_area("Write your review:", height=150)

        if st.button("Submit Review"):
            # Placeholder for saving the review (same as before)
            st.success(f"Thank you for reviewing '{product_details['name']}'!")
            st.balloons()
            # Optionally clear state/redirect

    else:
        st.error(f"Could not load details for product ID: {item_id_str}")
        if st.button("Back to Search"):
             if hasattr(st, "switch_page"):
                 st.switch_page("app.py") # Navigate back to main app
             else:
                 st.info("Navigate back using the sidebar.")


else: # No item selected
    st.warning("No product selected for review.")
    st.info("Please go back to the search page and click 'Review' on an item.")
    if st.button("Go to Search Page"):
        if hasattr(st, "switch_page"):
            st.switch_page("app_search_aidb.py") # Navigate back to main app
        else:
            st.info("Navigate back using the sidebar.")