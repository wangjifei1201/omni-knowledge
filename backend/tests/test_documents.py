"""
Document Processing Test
Tests the complete document upload -> parse -> index workflow
"""

import asyncio
import os
import shutil
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ["FAISS_INDEX_PATH"] = tempfile.mkdtemp()
os.environ["LOCAL_STORAGE_PATH"] = tempfile.mkdtemp()
os.environ["EMBEDDING_DIMENSION"] = "1024"


async def test_document_processor():
    """Test document processing pipeline"""
    print("\n=== Testing Document Processor ===")

    from services.document.processor import document_processor
    from services.rag.vector_store import faiss_vector_store
    from services.storage.local_storage import local_storage

    # Initialize services (use singleton instances)
    await local_storage.initialize()
    await faiss_vector_store.initialize()

    print("[PASS] Services initialized")

    # Test 1: Process a text file
    doc_id = "test_doc_001"
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

第四章：注意事项

请确保上传的文档内容清晰，格式正确。
系统会自动提取文档中的文字内容并进行智能分块处理。
""".encode(
        'utf-8'
    )

    # Upload document
    storage_info = await local_storage.upload_file(
        file_content=doc_content,
        original_name="使用指南.txt",
        doc_id=doc_id,
        category="documents",
    )
    print(f"[PASS] Document uploaded: {storage_info['storage_name']}")

    # Process document
    result = await document_processor.process_document(
        doc_id=doc_id,
        file_path=storage_info["storage_path"],
        file_type="txt",
        doc_name="使用指南",
    )

    print(f"[PASS] Document processed:")
    print(f"       Status: {result['status']}")
    print(f"       Chunks: {result['chunk_count']}")
    print(f"       Pages: {result['page_count']}")

    assert result["status"] == "completed", f"Expected completed, got {result['status']}"
    assert result["chunk_count"] > 0, "Expected chunks to be created"

    # Verify chunks in vector store
    chunk_count = await faiss_vector_store.get_doc_chunk_count(doc_id)
    print(f"[PASS] Verified {chunk_count} chunks in vector store")
    assert chunk_count == result["chunk_count"], f"Expected {result['chunk_count']}, got {chunk_count}"

    # Test search
    import numpy as np

    np.random.seed(42)
    query_vector = np.random.randn(1024).tolist()

    search_results = await faiss_vector_store.search(query_vector, top_k=3)
    print(f"[PASS] Search returned {len(search_results)} results")

    for i, r in enumerate(search_results):
        print(f"       Result {i+1}: {r.content[:40]}...")

    # Cleanup
    await faiss_vector_store.delete_by_doc_id(doc_id)
    await local_storage.delete_doc_files(doc_id)
    print("[PASS] Cleanup completed")

    print("\n=== Document Processor Test PASSED ===")
    return True


async def test_chunk_splitting():
    """Test text chunking logic"""
    print("\n=== Testing Chunk Splitting ===")

    from services.document.processor import DocumentProcessor

    processor = DocumentProcessor()

    # Test with short text
    short_text = "这是一段短文本。"
    chunks = processor._split_into_chunks(short_text, "doc1", "测试文档")
    assert len(chunks) == 1, "Short text should produce 1 chunk"
    print(f"[PASS] Short text: {len(chunks)} chunk")

    # Test with multi-paragraph text
    multi_para = """
第一段：这是第一段内容，包含一些重要信息。

第二段：这是第二段内容，继续描述相关内容。

第三段：这是第三段内容，总结前面的内容。
"""
    chunks = processor._split_into_chunks(multi_para, "doc2", "测试文档")
    assert len(chunks) >= 1, "Multi-paragraph should produce chunks"
    print(f"[PASS] Multi-paragraph text: {len(chunks)} chunks")

    # Test with long text
    long_text = "这是一段长文本。" * 200
    chunks = processor._split_into_chunks(long_text, "doc3", "测试文档", chunk_size=500)
    assert len(chunks) > 1, "Long text should produce multiple chunks"
    print(f"[PASS] Long text: {len(chunks)} chunks")

    # Verify chunk structure
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "content" in chunk
        assert "doc_id" in chunk
        assert "doc_name" in chunk
    print("[PASS] Chunk structure verified")

    print("\n=== Chunk Splitting Test PASSED ===")
    return True


async def test_api_imports():
    """Test that all document API modules can be imported"""
    print("\n=== Testing API Imports ===")

    try:
        from api.routes.documents import (
            download_document,
            get_document_chunks,
            preview_document,
            reparse_document,
            router,
            upload_document,
        )

        print("[PASS] Document routes imported")

        from core.security import get_current_user, get_current_user_optional

        print("[PASS] Security functions imported")

        from services.document.processor import document_processor

        print("[PASS] Document processor imported")

        print("\n=== API Imports Test PASSED ===")
        return True
    except ImportError as e:
        print(f"[FAILED] Import error: {e}")
        return False


async def main():
    """Run all document tests"""
    print("=" * 60)
    print("  Document Management Test Suite")
    print("=" * 60)

    results = []

    try:
        results.append(("API Imports", await test_api_imports()))
        results.append(("Chunk Splitting", await test_chunk_splitting()))
        results.append(("Document Processor", await test_document_processor()))

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
        print("  ALL DOCUMENT TESTS PASSED!")
    else:
        print("  SOME TESTS FAILED!")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
