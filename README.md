# Recommendation Engine using Hybrid Search & Live Reviews

A beginner-friendly web application that helps you search for products using text, images, or hybrid search methods. Built with Python and Streamlit, this app provides:

- **Smart Search**: Find products using text descriptions or by uploading photos
- **Product Reviews**: View and submit reviews for products  
- **AI-Powered Summaries**: Get automatic summaries of all product reviews
- **Easy-to-Use Interface**: Simple web interface that works in your browser

![Sample Application Screenshot](/dataset/screenshot.png)

## What You'll Need Before Starting

This guide assumes you have **no prior experience** with Python or web development. We'll walk you through everything step by step.

### System Requirements
- A computer running Windows, macOS, or Linux
- Internet connection
- About 30 minutes of setup time

### Prerequisites to Install
1. **Python 3.8 or newer** - The programming language this app uses
2. **PostgreSQL Database** - Where the app stores product and review data
3. **Git** (optional but recommended) - For downloading the code

## Step-by-Step Installation Guide

### Step 1: Install Python

**For Windows:**
1. Go to [python.org](https://www.python.org/downloads/)
2. Download Python 3.8 or newer
3. Run the installer and **check the box** "Add Python to PATH"
4. Open Command Prompt and type `python --version` to verify

**For macOS:**
1. Go to [python.org](https://www.python.org/downloads/)
2. Download Python 3.8 or newer, or use Homebrew: `brew install python`
3. Open Terminal and type `python3 --version` to verify

**For Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip
python3 --version
```

### Step 2: Install PostgreSQL Database

**For Windows:**
1. Download PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run the installer with default settings
3. Remember the password you set for the `postgres` user

**For macOS:**
```bash
# Using Homebrew (recommended)
brew install postgresql
brew services start postgresql

# Or download from postgresql.org
```

**For Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 3: Download This Project

**Option A: Using Git (Recommended)**
```bash
git clone <repository-url>
cd recommendation-engine-4.1.1
```

**Option B: Download ZIP**
1. Click the green "Code" button on GitHub
2. Select "Download ZIP"
3. Extract the files to a folder on your computer
4. Open Terminal/Command Prompt and navigate to that folder

### Step 4: Set Up the Database

1. Open your database management tool (like pgAdmin) or terminal
2. Copy the example environment file:
```bash
cp .env_example .env
```

3. Edit the `.env` file with your database details:
```
DB_NAME=vector_test
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
```

### Step 5: Install Python Dependencies

Open Terminal/Command Prompt in the project folder and run:

```bash
# For Windows
pip install -r requirements.txt

# For macOS/Linux
pip3 install -r requirements.txt
```

This will install all the necessary Python libraries:
- **Streamlit**: Creates the web interface
- **Pillow**: Handles image processing
- **psycopg2**: Connects to PostgreSQL database
- **pandas**: Manages data
- **boto3**: Works with cloud storage

### Step 6: Set Up the Database and Load Sample Data

Before running the app, you need to initialize the database with sample product data:

```bash
# For Windows
python code/connect_encode.py

# For macOS/Linux
python3 code/connect_encode.py
```

This script will:
- Create the necessary database tables
- Load sample product data from `dataset/products.csv`
- Load sample reviews from `dataset/product_reviews.csv`
- Set up the AI search capabilities

### Step 7: Run the Application

Now you're ready to start the web application:

```bash
# For Windows
streamlit run app_search_aidb.py

# For macOS/Linux
streamlit run app_search_aidb.py
```

After running this command:
1. The terminal will show a message like "Local URL: http://localhost:8501"
2. Your web browser should automatically open to this address
3. If it doesn't open automatically, copy the URL and paste it into your browser

## Using the Application

Once the app is running, you can:

1. **Search by Text**: Type keywords like "red shoes" or "black dress" in the search box
2. **Search by Image**: Upload a photo to find similar-looking products
3. **Apply Filters**: Use the category dropdown to narrow your search
4. **Read Reviews**: Click on any product to see customer reviews
5. **Write Reviews**: Submit your own reviews for products

## Troubleshooting Common Issues

### "Python not found" error
- Make sure Python is installed and added to your system PATH
- Try using `python3` instead of `python`

### Database connection errors
- Check that PostgreSQL is running
- Verify your `.env` file has the correct database credentials
- Make sure the `vector_test` database exists

### "Module not found" errors
- Run the pip install command again: `pip install -r requirements.txt`
- Make sure you're in the correct project directory

### Streamlit won't start
- Check if another application is using port 8501
- Try: `streamlit run app_search_aidb.py --server.port 8502`

## What This Application Does

### How the Search Works
- **Text Search**: Uses AI to understand the meaning of your search terms
- **Image Search**: Analyzes uploaded photos to find visually similar products  
- **Hybrid Search**: Combines both methods for better results

### Review System
- Users can submit reviews for any product
- AI automatically summarizes all reviews to highlight key themes
- Real-time updates show the latest feedback

## Project File Structure

Here's what each file and folder does:

```bash
recommendation-engine-4.1.1/
├── app_search_aidb.py           # Main application file - run this to start the app
├── pages/                       # Additional web pages
│   └── review_page.py           # Page for viewing and writing product reviews
├── code/
│   ├── connect_encode.py        # Database setup script - run this first
│   └── edb_new.png              # Logo image for the app
├── dataset/                     # Sample data files
│   ├── products.csv             # List of products to search
│   └── product_reviews.csv      # Sample customer reviews
├── utils/
│   ├── __init__.py              # Python configuration file
│   └── db_connection.py         # Handles database connections
├── requirements.txt             # List of Python libraries needed
├── .env_example                 # Template for database settings
├── .gitignore                   # Files to ignore in version control
├── LICENSE                      # Legal license information
└── README.md                    # This instruction file
```

## Getting Help

If you run into problems:

1. **Check the Troubleshooting section** above for common solutions
2. **Read error messages carefully** - they often tell you exactly what's wrong
3. **Make sure all steps were completed** in order
4. **Verify your database is running** and you can connect to it

## Sample Searches to Try

Once your app is running, try these example searches:
- `red shoes`
- `black dress`
- `women's jacket`
- `blue jeans`
- Upload a photo of clothing from your computer

## Technical Details (Advanced Users)

If you're interested in how this works:

- **Database**: PostgreSQL with aidb extension for AI-powered search
- **AI Models**: Uses OpenAI's CLIP for image understanding and sentence transformers for text
- **Framework**: Built with Streamlit for the web interface
- **Storage**: Product images stored in cloud storage (S3)
- **Search Types**: 
  - Semantic search (understands meaning)
  - Full-text search (keyword matching)
  - Image similarity search
  - Hybrid search (combines multiple methods)

## Next Steps

After getting the app running, you can:
1. **Add your own products** by editing the CSV files in the `dataset/` folder
2. **Customize the interface** by modifying the Streamlit files
3. **Connect your own database** by updating the `.env` file
4. **Deploy to the web** using Streamlit Cloud or other hosting services

---

*This project is licensed under the Apache License. See LICENSE file for details.*
