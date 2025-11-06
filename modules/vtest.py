from vector_store import add_text_file_to_vector_db, query_vector_db

# Add extracted text
add_text_file_to_vector_db("uploads/processed_texts/sample.txt")

# Query it
res = query_vector_db("What is this document about?")
print(res)
