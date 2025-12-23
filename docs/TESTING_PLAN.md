# FlexCube AI Assistant - Testing Plan

## Current Status
- ✅ Phase 1: Infrastructure - Complete
- ✅ Phase 2: RAG Pipeline - Complete and tested
- ✅ Phase 3: Basic API - Complete with UI enhancements
- ❌ Phase 5: Vision Support - NOT STARTED (Critical per PROJECT_SPEC.md)

---

## Next Logical Tests (Priority Order)

### Test 1: RAG Pipeline Quality Testing ⭐ HIGH PRIORITY
**Purpose:** Verify the system answers questions accurately from the 6MB PDF

**Test Cases:**
1. **Simple Factual Questions**
   - "What is FlexCube?"
   - "What types of accounts does FlexCube support?"
   - Expected: Direct answers with sources from PDF

2. **Error Code Questions**
   - "How do I resolve ERR_ACC_NOT_FOUND?"
   - "What causes ERR_INSUFFICIENT_FUNDS?"
   - Expected: Step-by-step solutions with source citations

3. **Process Questions**
   - "How do I create a microfinance account?"
   - "What is the transaction processing workflow?"
   - Expected: Detailed process explanations

4. **Complex Multi-Part Questions**
   - "Explain account management and transaction processing"
   - Expected: Comprehensive answers covering multiple topics

5. **Edge Cases**
   - Questions about topics NOT in the PDF
   - Very specific technical questions
   - Expected: Honest "I don't know" or partial answers

**Success Criteria:**
- ✅ Sources are always provided
- ✅ Answers are relevant to the question
- ✅ Sources point to correct document sections
- ✅ Response time < 30 seconds (per PROJECT_SPEC.md)

---

### Test 2: Screenshot/Image Query Support ⭐⭐ CRITICAL PRIORITY
**Purpose:** Implement and test the core feature from PROJECT_SPEC.md

**Why This is Next:**
- PROJECT_SPEC.md explicitly states: "Users often screenshot errors rather than typing them"
- This is a KEY REQUIREMENT: "Accepts screenshots of FlexCube errors"
- LLaVA model is already installed and ready

**Test Plan:**
1. **LLaVA Model Testing**
   - Test LLaVA with sample FlexCube error screenshots
   - Verify it can extract:
     - Error codes (e.g., ERR_ACC_NOT_FOUND)
     - Error messages
     - Screen names
     - Context information

2. **Integration Testing**
   - Upload screenshot via API
   - LLaVA extracts error information
   - Extracted text becomes query to RAG pipeline
   - System returns solution with sources

3. **End-to-End Testing**
   - User uploads FlexCube error screenshot
   - System identifies error and provides solution
   - Sources cited for the solution

**Implementation Steps:**
1. Create image preprocessing module
2. Build LLaVA integration for error extraction
3. Implement POST /api/query/image endpoint
4. Update UI to accept image uploads
5. Test with real FlexCube screenshots

---

### Test 3: Document Management Testing
**Purpose:** Verify document upload, indexing, and management work correctly

**Test Cases:**
1. **Document Upload**
   - Upload new PDF via API
   - Verify it gets indexed
   - Query about new document content
   - Expected: Answers include new document

2. **Reindexing**
   - Add multiple documents
   - Trigger reindex
   - Verify all documents are searchable

3. **Document Deletion** (when implemented)
   - Remove specific document
   - Verify it's no longer in index
   - Query should not return deleted content

---

### Test 4: Performance & Scalability Testing
**Purpose:** Ensure system handles expected load

**Test Cases:**
1. **Concurrent Users**
   - Simulate 10-15 concurrent queries (per PROJECT_SPEC.md)
   - Monitor response times
   - Check memory usage
   - Expected: All queries complete successfully

2. **Large Document Handling**
   - Test with larger PDFs (10MB+)
   - Verify indexing completes
   - Check query performance

3. **Memory Management**
   - Monitor RAM usage during queries
   - Verify models unload when not in use
   - Check swap usage

---

### Test 5: Production Readiness Testing
**Purpose:** Prepare for production deployment

**Test Cases:**
1. **Security**
   - Test API authentication (when added)
   - Verify CORS settings
   - Check input validation

2. **Error Handling**
   - Invalid queries
   - Network failures
   - Model errors
   - Expected: Graceful error messages

3. **Monitoring**
   - Health check endpoints
   - Logging
   - Performance metrics

---

## Recommended Next Test: Screenshot Support (Phase 5)

**Why This Should Be Next:**
1. ✅ It's explicitly required in PROJECT_SPEC.md
2. ✅ LLaVA model is already installed
3. ✅ Completes core functionality before production
4. ✅ Users expect this feature (screenshot errors)

**Estimated Implementation Time:**
- LLaVA integration: 2-3 hours
- Image preprocessing: 1 hour
- API endpoint: 1 hour
- UI updates: 1 hour
- Testing: 1-2 hours
- **Total: ~6-8 hours**

---

## Alternative: Complete Phase 3 First

If you prefer to finish Phase 3 completely before moving to Phase 5:

**Missing Phase 3 Endpoints:**
1. POST /api/documents/reindex - Rebuild index
2. DELETE /api/documents/{id} - Remove document

**Estimated Time:** 1-2 hours

---

## Recommendation

**Next Logical Test: Phase 5 - Screenshot Support**

This is the most critical missing feature and aligns with PROJECT_SPEC.md requirements. It will:
- Enable users to upload error screenshots
- Extract error information automatically
- Provide solutions based on extracted errors
- Complete the core functionality

Would you like me to proceed with implementing Phase 5 (Screenshot Support)?





