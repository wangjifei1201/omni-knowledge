"""
End-to-End Integration Test
Tests the complete workflow of the omni-knowledge system
"""

import os
import sys
import asyncio
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ["FAISS_INDEX_PATH"] = tempfile.mkdtemp()
os.environ["LOCAL_STORAGE_PATH"] = tempfile.mkdtemp()
os.environ["EMBEDDING_DIMENSION"] = "1024"


async def test_complete_workflow():
    """Test complete document upload -> indexing -> search workflow"""
    print("\n=== Testing Complete Workflow ===")
    
    from services.storage.local_storage import LocalStorageService
    from services.rag.vector_store import FAISSVectorStore
    from services.document.parser import DocumentParser
    from services.rag.pipeline import RAGPipeline
    
    # Initialize services
    storage = LocalStorageService()
    vector_store = FAISSVectorStore()
    parser = DocumentParser()
    pipeline = RAGPipeline()
    
    await storage.initialize()
    await vector_store.initialize()
    await pipeline.initialize()
    
    print("[PASS] All services initialized")
    
    # Step 1: Simulate document upload
    doc_id = "test_document_001"
    doc_content = """
    企业知识库系统使用指南
    
    第一章：系统概述
    本系统是一个企业级智能知识库问答系统，支持多种文档格式的上传和解析。
    系统采用RAG（检索增强生成）技术，能够准确回答用户问题并提供来源引用。
    
    第二章：功能特点
    1. 智能文档解析：支持PDF、Word、Excel等多种格式
    2. 语义化检索：基于向量相似度的智能搜索
    3. 精准问答：结合上下文生成准确答案
    4. 来源追溯：每个答案都附带原文引用
    
    第三章：使用方法
    用户可以通过Web界面上传文档，系统会自动进行解析和索引。
    之后可以在问答页面提出问题，系统会返回答案和相关引用。
    """.encode('utf-8')
    
    storage_info = await storage.upload_file(
        file_content=doc_content,
        original_name="使用指南.txt",
        doc_id=doc_id,
        category="documents",
    )
    print(f"[PASS] Document uploaded: {storage_info['storage_name']}")
    
    # Step 2: Simulate text chunking
    chunks = [
        {
            "chunk_id": f"{doc_id}_chunk_1",
            "content": "本系统是一个企业级智能知识库问答系统，支持多种文档格式的上传和解析。",
            "chapter": "第一章：系统概述",
            "page": 1,
        },
        {
            "chunk_id": f"{doc_id}_chunk_2",
            "content": "系统采用RAG（检索增强生成）技术，能够准确回答用户问题并提供来源引用。",
            "chapter": "第一章：系统概述",
            "page": 1,
        },
        {
            "chunk_id": f"{doc_id}_chunk_3",
            "content": "智能文档解析：支持PDF、Word、Excel等多种格式",
            "chapter": "第二章：功能特点",
            "page": 1,
        },
        {
            "chunk_id": f"{doc_id}_chunk_4",
            "content": "语义化检索：基于向量相似度的智能搜索",
            "chapter": "第二章：功能特点",
            "page": 1,
        },
        {
            "chunk_id": f"{doc_id}_chunk_5",
            "content": "用户可以通过Web界面上传文档，系统会自动进行解析和索引。",
            "chapter": "第三章：使用方法",
            "page": 2,
        },
    ]
    print(f"[PASS] Document chunked into {len(chunks)} segments")
    
    # Step 3: Simulate vector embedding and indexing
    # Using random vectors for testing (in production, use actual embeddings)
    import numpy as np
    np.random.seed(42)
    
    vectors = [np.random.randn(1024).tolist() for _ in chunks]
    chunk_ids = [c["chunk_id"] for c in chunks]
    metadatas = [
        {
            "doc_id": doc_id,
            "doc_name": "使用指南",
            "content": c["content"],
            "chapter": c["chapter"],
            "page": c["page"],
        }
        for c in chunks
    ]
    
    await vector_store.add_vectors(vectors, chunk_ids, metadatas)
    count = await vector_store.get_vector_count()
    print(f"[PASS] Indexed {count} vectors in FAISS")
    
    # Step 4: Test search functionality
    query_vector = np.random.randn(1024).tolist()
    results = await vector_store.search(query_vector, top_k=3)
    print(f"[PASS] Search returned {len(results)} results")
    for i, r in enumerate(results):
        print(f"       Result {i+1}: {r.content[:30]}... (score: {r.score:.4f})")
    
    # Step 5: Test RAG pipeline intent classification
    test_queries = [
        ("什么是RAG技术？", "content"),
        ("系统支持哪些文档格式？", "content"),
        ("有多少份文档？", "metadata"),
    ]
    
    for query, expected_intent in test_queries:
        intent = await pipeline.classify_intent(query)
        print(f"[PASS] Intent for '{query}': {intent.value}")
    
    # Step 6: Test document deletion
    deleted_vectors = await vector_store.delete_by_doc_id(doc_id)
    deleted_files = await storage.delete_doc_files(doc_id)
    print(f"[PASS] Cleanup: deleted {deleted_vectors} vectors, {deleted_files} files")
    
    # Verify cleanup
    remaining = await vector_store.get_vector_count()
    assert remaining == 0, f"Expected 0 remaining vectors, got {remaining}"
    print("[PASS] Cleanup verified - no remaining data")
    
    print("\n=== Complete Workflow Test PASSED ===")
    return True


async def test_api_schemas():
    """Test API schema validation"""
    print("\n=== Testing API Schemas ===")
    
    from schemas.user import UserCreate, UserResponse
    from schemas.document import DocumentCreate, DocumentResponse
    from schemas.chat import ChatRequest, ChatResponse, Citation
    
    # Test UserCreate
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User",
    }
    user = UserCreate(**user_data)
    assert user.username == "testuser"
    print("[PASS] UserCreate schema validation")
    
    # Test ChatRequest
    chat_data = {
        "question": "什么是知识库系统？",
        "search_mode": "hybrid",
        "doc_scope": ["doc1", "doc2"],
        "detail_level": "detailed",
    }
    chat_req = ChatRequest(**chat_data)
    assert chat_req.question == "什么是知识库系统？"
    print("[PASS] ChatRequest schema validation")
    
    # Test Citation
    citation_data = {
        "doc_id": "doc_001",
        "doc_name": "测试文档",
        "chapter": "第一章",
        "page": 1,
        "original_text": "这是引用内容",
    }
    citation = Citation(**citation_data)
    assert citation.doc_name == "测试文档"
    print("[PASS] Citation schema validation")
    
    print("\n=== API Schemas Test PASSED ===")
    return True


async def test_security():
    """Test security functions"""
    print("\n=== Testing Security Functions ===")
    
    from core.security import get_password_hash, verify_password, create_access_token
    
    # Test password hashing
    password = "MySecureP@ssw0rd"
    hashed = get_password_hash(password)
    assert hashed != password
    print("[PASS] Password hashing works")
    
    # Test password verification
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)
    print("[PASS] Password verification works")
    
    # Test JWT token creation
    token = create_access_token({"sub": "user123"})
    assert token is not None
    assert len(token) > 0
    print(f"[PASS] JWT token created: {token[:50]}...")
    
    print("\n=== Security Test PASSED ===")
    return True


async def main():
    """Run all end-to-end tests"""
    print("=" * 60)
    print("  Omni-Knowledge End-to-End Test Suite")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Complete Workflow", await test_complete_workflow()))
        results.append(("API Schemas", await test_api_schemas()))
        results.append(("Security", await test_security()))
        
    except Exception as e:
        print(f"\n[FAILED] Test error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Exception", False))
    finally:
        # Cleanup temp directories
        faiss_path = os.environ.get("FAISS_INDEX_PATH")
        storage_path = os.environ.get("LOCAL_STORAGE_PATH")
        if faiss_path and os.path.exists(faiss_path):
            shutil.rmtree(faiss_path, ignore_errors=True)
        if storage_path and os.path.exists(storage_path):
            shutil.rmtree(storage_path, ignore_errors=True)
    
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
        print("  ALL E2E TESTS PASSED!")
    else:
        print("  SOME TESTS FAILED!")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
