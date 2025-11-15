from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Qdrant client with local storage
qdrant_client = QdrantClient(path="./qdrant_data")

# Initialize OpenAI
openai_client = openai.AzureOpenAI(
    azure_endpoint=os.getenv("GPT_BASE_URL"),
    api_key=os.getenv("GPT_API_KEY"),
    api_version=os.getenv("GPT_API_VERSION")
)

# Collection name
COLLECTION_NAME = "words_collection"

# Sample words
words = [
    "peace", "mountains", "apple", "travel", "dog", "art", "music", 
    "book", "sun", "ocean", "friend", "family", "home", "food", 
    "water", "sky", "earth", "fire", "wind", "rain", "snow", 
    "tree", "flower", "bird", "love"
]

class SearchRequest(BaseModel):
    user_word: str

class SearchResponse(BaseModel):
    word: str
    reason: str
    score: float

def initialize_database():
    """Initialize Qdrant collection and add sample words"""
    try:
        # Create collection if it doesn't exist
        collections = qdrant_client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if COLLECTION_NAME not in collection_names:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print("✅ Created new Qdrant collection")
        
        # Check if collection is empty and add sample words
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        if collection_info.points_count == 0:
            add_words_to_database()
            print("✅ Added words to Qdrant database")
        else:
            print("✅ Qdrant database already populated")
            
    except Exception as e:
        print(f"❌ Qdrant database initialization error: {e}")

def add_words_to_database():
    """Add words to Qdrant database"""
    embeddings = model.encode(words)
    
    points = []
    for i, (word, embedding) in enumerate(zip(words, embeddings)):
        points.append(
            PointStruct(
                id=i,
                vector=embedding.tolist(),
                payload={"word": word}
            )
        )
    
    operation_info = qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"✅ Added {len(points)} words to Qdrant")

def get_similar_words(user_word: str, limit: int = 5):
    """Find similar words using Qdrant vector similarity search"""
    user_embedding = model.encode([user_word])[0]
    
    search_results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=user_embedding.tolist(),
        limit=limit
    )
    
    return search_results

def generate_reason(user_word: str, similar_word: str) -> str:
    """Generate reason using LLM"""
    try:
        response = openai_client.chat.completions.create(
            model=os.getenv("GPT_MODEL"),
            messages=[
                {"role": "system", "content": "Give one short reason about word relationship."},
                {"role": "user", "content": f"Connect '{user_word}' and '{similar_word}' in one short sentence."}
            ],
            max_tokens=30
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return f"Both words share conceptual meaning"

@app.get("/words")
async def get_all_words():
    """Get all words in the database"""
    return {"words": words}

@app.get("/db-status")
async def get_db_status():
    """Check Qdrant database status"""
    try:
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        return {
            "status": "connected",
            "collection": COLLECTION_NAME,
            "points_count": collection_info.points_count,
            "vectors_count": collection_info.vectors_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/search")
async def search_similar_words(request: SearchRequest):
    """Search for similar words with reasons using Qdrant vector DB"""
    try:
        print(f"🔍 Searching for similar words to: {request.user_word}")
        
        # Find similar words using Qdrant vector search
        similar_results = get_similar_words(request.user_word)
        print(f"✅ Found {len(similar_results)} similar words")
        
        results = []
        for result in similar_results:
            # Convert score to Python float and round to 2 decimal places
            score = float(result.score)
            if score > 0.3:  # Filter out very low similarity scores
                reason = generate_reason(request.user_word, result.payload["word"])
                results.append({
                    "word": str(result.payload["word"]),
                    "reason": str(reason),
                    "score": round(score, 2)  # Only 2 decimal places
                })
                print(f"  - {result.payload['word']}: {score:.2f}")
        
        return results
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize database when app starts
initialize_database()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI server with Qdrant Vector DB...")
    uvicorn.run(app, host="0.0.0.0", port=8000)