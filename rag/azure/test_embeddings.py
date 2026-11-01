from sentence_transformers import SentenceTransformer

# Load the pretrained embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Sample insurance sentences
sentences = [
    "Does my insurance cover hospital admission?",
    "Gold plan covers inpatient hospitalization up to INR 10 lakh."
]

# Generate embeddings
embeddings = model.encode(sentences)

# Display results
print("Number of sentences:", len(sentences))
print("Embedding shape:", embeddings.shape)
print("Dimensions per sentence:", len(embeddings[0]))

# Compare the two sentence embeddings
similarity = model.similarity(
    embeddings[0:1],
    embeddings[1:2]
)

print("Semantic similarity:", similarity.item())