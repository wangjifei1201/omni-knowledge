"""
Tests for FAISS Vector Store and Local Storage Services
"""

import os
import sys
import asyncio
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables before importing
os.environ["FAISS_INDEX_PATH"] = tempfile.mkdtemp()
os.environ["LOCAL_STORAGE_PATH"] = tempfile.mkdtemp()
os.environ["EMBEDDING_DIMENSION"] = "128"  # Small dimension for testing


async def test_faiss_vector_store():
    """Test FAISS vector store operations"""
    print("\n=== Testing FAISS Vector Store ===")
    
    from services.rag.vector_store import FAISSVectorStore
    
    # Create fresh instance for testing
    store = FAISSVectorStore()
    
    # Initialize
    await store.initialize()
    print("[PASS] FAISS store initialized")
    
    # Test adding vectors
    test_vectors = [
        [0.1] * 128,
        [0.2] * 128,
        [0.3] * 128,
    ]
    test_ids = ["chunk_1", "chunk_2", "chunk_3"]
    test_metadata = [
        {"doc_id": "doc_1", "content": "测试文档1内容", "doc_name": "测试文档1"},
        {"doc_id": "doc_1", "content": "测试文档1第二段", "doc_name": "测试文档1"},
        {"doc_id": "doc_2", "content": "测试文档2内容", "doc_name": "测试文档2"},
    ]
    
    added_ids = await store.add_vectors(test_vectors, test_ids, test_metadata)
    assert len(added_ids) == 3, f"Expected 3 added IDs, got {len(added_ids)}"
    print(f"[PASS] Added {len(added_ids)} vectors")
    
    # Test vector count
    count = await store.get_vector_count()
    assert count == 3, f"Expected count 3, got {count}"
    print(f"[PASS] Vector count: {count}")
    
    # Test document chunk count
    doc1_count = await store.get_doc_chunk_count("doc_1")
    assert doc1_count == 2, f"Expected doc_1 count 2, got {doc1_count}"
    print(f"[PASS] Doc_1 chunk count: {doc1_count}")
    
    # Test search
    query_vector = [0.15] * 128
    results = await store.search(query_vector, top_k=2)
    assert len(results) > 0, "Expected search results"
    print(f"[PASS] Search returned {len(results)} results")
    print(f"       Top result: {results[0].content} (score: {results[0].score:.4f})")
    
    # Test search with filter
    results_filtered = await store.search(
        query_vector, 
        top_k=5, 
        filters={"doc_ids": ["doc_2"]}
    )
    for r in results_filtered:
        assert r.doc_id == "doc_2", f"Filter failed: got doc_id {r.doc_id}"
    print(f"[PASS] Filtered search works correctly")
    
    # Test delete by doc_id
    deleted = await store.delete_by_doc_id("doc_1")
    assert deleted == 2, f"Expected 2 deleted, got {deleted}"
    print(f"[PASS] Deleted {deleted} vectors for doc_1")
    
    # Verify deletion
    remaining = await store.get_vector_count()
    assert remaining == 1, f"Expected 1 remaining, got {remaining}"
    print(f"[PASS] Remaining vectors: {remaining}")
    
    print("\n=== FAISS Vector Store Tests PASSED ===")
    return True


async def test_local_storage():
    """Test local file storage operations"""
    print("\n=== Testing Local Storage Service ===")
    
    from services.storage.local_storage import LocalStorageService
    
    # Create fresh instance for testing
    storage = LocalStorageService()
    
    # Initialize
    await storage.initialize()
    print("[PASS] Local storage initialized")
    
    # Test file upload
    test_content = b"This is test file content for omni-knowledge system."
    storage_info = await storage.upload_file(
        file_content=test_content,
        original_name="test_document.txt",
        doc_id="test_doc_001",
        category="documents",
    )
    
    assert storage_info["size"] == len(test_content)
    assert "storage_path" in storage_info
    print(f"[PASS] File uploaded: {storage_info['storage_name']}")
    print(f"       Size: {storage_info['size']} bytes")
    print(f"       Hash: {storage_info['hash']}")
    
    # Test file exists
    exists = await storage.file_exists(storage_info["storage_path"])
    assert exists, "File should exist"
    print("[PASS] File exists check works")
    
    # Test file download
    downloaded = await storage.download_file(storage_info["storage_path"])
    assert downloaded == test_content, "Downloaded content should match"
    print("[PASS] File download matches original content")
    
    # Test file info
    file_info = await storage.get_file_info(storage_info["storage_path"])
    assert file_info is not None
    assert file_info["size"] == len(test_content)
    print(f"[PASS] File info retrieved: {file_info['filename']}")
    
    # Test list files
    files = await storage.list_files(category="documents")
    assert len(files) >= 1, "Should have at least 1 file"
    print(f"[PASS] Listed {len(files)} files in documents")
    
    # Test storage stats
    stats = await storage.get_storage_stats()
    assert stats["file_count"] >= 1
    print(f"[PASS] Storage stats: {stats['file_count']} files, {stats['total_size']} bytes")
    
    # Test file deletion
    deleted = await storage.delete_file(storage_info["storage_path"])
    assert deleted, "File should be deleted"
    print("[PASS] File deleted successfully")
    
    # Verify deletion
    exists_after = await storage.file_exists(storage_info["storage_path"])
    assert not exists_after, "File should not exist after deletion"
    print("[PASS] File deletion verified")
    
    # Test upload and delete by doc_id
    await storage.upload_file(b"content1", "file1.txt", "doc_multi", "documents")
    await storage.upload_file(b"content2", "file2.txt", "doc_multi", "documents")
    deleted_count = await storage.delete_doc_files("doc_multi")
    assert deleted_count == 2, f"Expected 2 deleted, got {deleted_count}"
    print(f"[PASS] Deleted {deleted_count} files by doc_id")
    
    print("\n=== Local Storage Tests PASSED ===")
    return True


async def test_integration():
    """Test integration between services"""
    print("\n=== Testing Integration ===")
    
    from services.rag.vector_store import FAISSVectorStore
    from services.storage.local_storage import LocalStorageService
    
    store = FAISSVectorStore()
    storage = LocalStorageService()
    
    await store.initialize()
    await storage.initialize()
    
    # Simulate document upload and indexing workflow
    doc_id = "integration_test_doc"
    
    # 1. Upload document
    doc_content = b"This is an integration test document with some content."
    storage_info = await storage.upload_file(
        file_content=doc_content,
        original_name="integration_test.txt",
        doc_id=doc_id,
        category="documents",
    )
    print(f"[PASS] Document uploaded: {storage_info['storage_name']}")
    
    # 2. Add vectors for document chunks
    vectors = [[0.5] * 128, [0.6] * 128]
    chunk_ids = [f"{doc_id}_chunk_1", f"{doc_id}_chunk_2"]
    metadata = [
        {"doc_id": doc_id, "content": "First chunk content", "doc_name": "Integration Test"},
        {"doc_id": doc_id, "content": "Second chunk content", "doc_name": "Integration Test"},
    ]
    await store.add_vectors(vectors, chunk_ids, metadata)
    print("[PASS] Vector embeddings added")
    
    # 3. Search for document
    results = await store.search([0.55] * 128, top_k=2)
    assert len(results) > 0
    print(f"[PASS] Search found {len(results)} relevant chunks")
    
    # 4. Clean up - delete document
    await store.delete_by_doc_id(doc_id)
    await storage.delete_doc_files(doc_id)
    print("[PASS] Document cleaned up from both stores")
    
    print("\n=== Integration Tests PASSED ===")
    return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("  Omni-Knowledge Storage Services Test Suite")
    print("=" * 60)
    
    try:
        # Check if faiss is available
        try:
            import faiss
            print(f"\nFAISS version: {faiss.__version__ if hasattr(faiss, '__version__') else 'installed'}")
        except ImportError:
            print("\n[WARNING] faiss-cpu not installed. Install with: pip install faiss-cpu")
            print("Skipping FAISS tests...")
            await test_local_storage()
            return
        
        # Run all tests
        await test_faiss_vector_store()
        await test_local_storage()
        await test_integration()
        
        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FAILED] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup temp directories
        faiss_path = os.environ.get("FAISS_INDEX_PATH")
        storage_path = os.environ.get("LOCAL_STORAGE_PATH")
        if faiss_path and os.path.exists(faiss_path):
            shutil.rmtree(faiss_path, ignore_errors=True)
        if storage_path and os.path.exists(storage_path):
            shutil.rmtree(storage_path, ignore_errors=True)
    
    return True


if __name__ == "__main__":
    asyncio.run(main())
