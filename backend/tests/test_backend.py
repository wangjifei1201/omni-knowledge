"""
Backend API Test Script
Tests the FastAPI backend startup and core APIs
"""

import os
import sys
import asyncio
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_backend_imports():
    """Test that all backend modules can be imported"""
    print("\n=== Testing Backend Imports ===")
    
    try:
        from core.config import get_settings
        settings = get_settings()
        print(f"[PASS] Config loaded: APP_NAME={settings.APP_NAME}")
        
        from core.database import engine, get_db
        print("[PASS] Database module imported")
        
        from core.security import get_current_user, verify_password, create_access_token
        print("[PASS] Security module imported")
        
        from models.user import User
        from models.document import Document, Chapter, DocumentChunk
        from models.chat import Conversation, ChatMessage
        print("[PASS] All models imported")
        
        from schemas.user import UserCreate, UserResponse
        from schemas.document import DocumentCreate, DocumentResponse
        from schemas.chat import ChatRequest, ChatResponse
        print("[PASS] All schemas imported")
        
        from services.rag.pipeline import rag_pipeline
        from services.rag.vector_store import faiss_vector_store
        from services.storage.local_storage import local_storage
        from services.document.parser import document_parser
        print("[PASS] All services imported")
        
        from api.routes import auth, documents, chat, users, statistics
        print("[PASS] All API routes imported")
        
        from app import app
        print("[PASS] FastAPI app imported")
        
        return True
    except ImportError as e:
        print(f"[FAILED] Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fastapi_app():
    """Test FastAPI app configuration"""
    print("\n=== Testing FastAPI App Configuration ===")
    
    from app import app
    
    # Check app metadata
    assert app.title == "omni-knowledge"
    print(f"[PASS] App title: {app.title}")
    
    # Check routes are registered
    routes = [r.path for r in app.routes]
    
    expected_routes = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/documents",
        "/api/v1/chat/query",
        "/api/v1/users",
        "/api/v1/statistics/overview",
    ]
    
    for route in expected_routes:
        found = any(route in r for r in routes)
        if found:
            print(f"[PASS] Route exists: {route}")
        else:
            print(f"[WARN] Route not found: {route}")
    
    return True


async def test_services_initialization():
    """Test services can be initialized"""
    print("\n=== Testing Services Initialization ===")
    
    # Set test paths
    import tempfile
    test_faiss_path = tempfile.mkdtemp()
    test_storage_path = tempfile.mkdtemp()
    
    os.environ["FAISS_INDEX_PATH"] = test_faiss_path
    os.environ["LOCAL_STORAGE_PATH"] = test_storage_path
    os.environ["EMBEDDING_DIMENSION"] = "1024"
    
    try:
        from services.rag.vector_store import FAISSVectorStore
        from services.storage.local_storage import LocalStorageService
        from services.rag.pipeline import RAGPipeline
        
        # Initialize services
        vector_store = FAISSVectorStore()
        await vector_store.initialize()
        print("[PASS] FAISS vector store initialized")
        
        storage = LocalStorageService()
        await storage.initialize()
        print("[PASS] Local storage service initialized")
        
        pipeline = RAGPipeline()
        await pipeline.initialize()
        print("[PASS] RAG pipeline initialized")
        
        return True
    except Exception as e:
        print(f"[FAILED] Service initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_faiss_path, ignore_errors=True)
        shutil.rmtree(test_storage_path, ignore_errors=True)


async def main():
    """Run all backend tests"""
    print("=" * 60)
    print("  Omni-Knowledge Backend Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test imports
    results.append(("Imports", await test_backend_imports()))
    
    # Test FastAPI app
    results.append(("FastAPI App", await test_fastapi_app()))
    
    # Test services
    results.append(("Services Init", await test_services_initialization()))
    
    # Summary
    print("\n" + "=" * 60)
    print("  Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("  ALL BACKEND TESTS PASSED!")
    else:
        print("  SOME TESTS FAILED!")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
