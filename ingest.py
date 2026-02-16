from pathlib import Path
from typing import List
import logging
import warnings
import pandas as pd
from pathlib import Path

from langchain_community.document_loaders import DataFrameLoader
from langchain_core.documents import Document



# Suppress library-level shadowing warnings from LangChain/Tavily
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_tavily")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_nutrition_excels(
    excel_dir: Path, 
    engine: str = "openpyxl"
) -> List[Document]:
    """
    Robustly load nutrition Excel files, avoiding empty row explosion.
    """
    if not excel_dir.exists():
        logger.error(f"Directory {excel_dir} does not exist.")
        return []

    documents: List[Document] = []
    
    for excel_path in excel_dir.glob("*.xlsx"):
        try:
            # Best Practice: Read Excel and drop completely empty rows/columns immediately
            # This prevents the "390,000 documents" issue caused by trailing empty rows
            df = pd.read_excel(excel_path, engine=engine)
            
            initial_count = len(df)
            # 1. Drop rows where all elements are missing
            df = df.dropna(how='all')
            # 2. Drop columns where all elements are missing
            df = df.dropna(axis=1, how='all')
            # 3. Strip whitespace from column names
            df.columns = [str(col).strip() for col in df.columns]
            # 4. Filter out rows where the primary key (Food Name) is missing
            if 'Food Name' in df.columns:
                df = df[df['Food Name'].notna() & (df['Food Name'].astype(str).str.strip() != "")]
            
            final_count = len(df)
            logger.info(f"File {excel_path.name}: Cleaned {initial_count} rows down to {final_count} valid entries.")

            # Fill remaining NaNs with empty strings for clean text generation
            df = df.fillna("")

            for idx, row in df.iterrows():
                # Constructing a semantic block for the LLM
                # We use a clear, labeled format which is best for RAG retrieval
                content_parts = [
                    f"Food Name: {row.get('Food Name')}",
                    f"Local Name: {row.get('Local Name')}",
                    f"Scientific Name: {row.get('Scientific Name')}",
                    f"Category: {row.get('Category')}",
                    f"Nutrients: Calories {row.get('Calories (per 100g)')}kcal, Carbs {row.get('Carbs (g)')}g, Protein {row.get('Protein (g)')}g, Fat {row.get('Fat (g)')}g, Fiber {row.get('Fiber (g)')}g",
                    f"Micronutrients: {row.get('Micronutrients')}",
                    f"Health Notes: {row.get('Health Benefits')} | {row.get('Health Risks')}",
                    f"Source: {row.get('Primary Source')}"
                ]
                
                page_content = "\n".join([p for p in content_parts if p.split(": ")[1].strip()])
                
                metadata = {
                    "source": excel_path.name,
                    "food_name": str(row.get("Food Name")),
                    "category": str(row.get("Category")),
                    "row": idx
                }
                
                documents.append(Document(page_content=page_content, metadata=metadata))

        except Exception as e:
            logger.error(f"Error processing {excel_path.name}: {e}")

    logger.info(f"Total valid documents created: {len(documents)}")
    return documents




def test_retriever(retriever, text):
  docs = retriever.invoke(text)

  if not docs:
      print("⚠️ No documents retrieved")
  else:
      print(docs[0].page_content)
