# Testing Guide for Backend Improvements

## Quick Test Commands

### 1. Start the Backend Server

```powershell
cd backend
python api.py
```

The server should start on `http://localhost:8000`

---

## 2. Test the Improvements

### Test Case 1: Simple Technical Query

**Query**: "What is machine learning?"

**Expected Behavior**:
1. ✅ Query validated
2. 🌐 Web search performed for context (should see: "Web search returned X results")
3. 📊 Search terms generated based on web results
4. 🔬 Deep research with generated questions
5. 🎓 PhD-grade paper generated with:
   - Abstract section
   - Introduction section
   - 3-5 body chapters
   - Discussion section
   - Conclusion section
   - Extensive citations [1][2][3]

**API Call**:
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}'
```

---

### Test Case 2: Complex Research Query

**Query**: "How does climate change affect marine biodiversity?"

**Expected Behavior**:
1. Web-informed analysis should generate specific questions like:
   - "What are the effects of ocean acidification on marine species?"
   - "How does temperature change affect coral reef ecosystems?"
   - "What are the impacts of climate change on fish migration patterns?"
2. PhD-grade paper with comprehensive chapters
3. Deep analysis with multiple perspectives
4. Professional academic structure

---

### Test Case 3: Recent Technology Query

**Query**: "Explain quantum computing algorithms"

**Expected Behavior**:
1. Web context should inform technical depth
2. Search questions should be technically sophisticated
3. Paper should include:
   - Technical abstract
   - Introduction with background
   - Multiple chapters covering different algorithm types
   - Discussion of current state and limitations
   - Conclusion with future directions

---

## 3. Verify Output Quality

### Check for PhD-Grade Structure

Open the generated research paper and verify:

- [ ] **ABSTRACT** section present (150-250 words)
- [ ] **INTRODUCTION** section with context and objectives
- [ ] **3-5 MAIN CHAPTERS** with descriptive titles
  - [ ] Each chapter has subsections
  - [ ] Each chapter has heavy citations
  - [ ] Chapters flow logically
- [ ] **DISCUSSION** section synthesizing findings
- [ ] **CONCLUSION** section with summary and implications
- [ ] **REFERENCES** section with all sources

### Check Citation Quality

- [ ] Every factual claim has citations [1][2][3]
- [ ] Citations are inline and immediate
- [ ] Important claims have multiple citations
- [ ] Citation numbers correspond to reference list

### Check Content Quality

- [ ] Academic, formal tone throughout
- [ ] Sophisticated vocabulary and concepts
- [ ] Critical analysis, not just description
- [ ] Multiple perspectives considered
- [ ] Research gaps identified
- [ ] Implications discussed
- [ ] No fabricated information

### Check Length

- [ ] Paper is substantial (typically 2000-5000 words)
- [ ] Abstract is concise (150-250 words)
- [ ] Introduction is ~10-15% of total
- [ ] Body is ~70-80% of total
- [ ] Discussion and Conclusion ~10-15% combined

---

## 4. Backend Console Output

### What to Look For

```
🔍 Processing query: [your query]

✅ Validating query...
   ✓ Query is valid

📊 Analyzing query with web search...
   🌐 Searching web for context on: [query]
   📡 Web search returned 5 results for context
   Main topic: [extracted topic]
   Search terms (web-informed): [list of questions]

🔬 Starting research...
   [Research progress]

📝 Summarizing content...
   Generated X summaries

🔍 Verifying claims...
   Verified X high-quality sources

🧠 Generating PhD-grade research paper...
   📝 Generating PhD-grade research paper with X sources...
   ✅ Academic structure verified (Abstract: True, Intro: True, Conclusion: True)
   ✅ Generated comprehensive research paper (X characters)

📚 Formatting citations...

✨ Research complete!
```

---

## 5. Common Issues & Troubleshooting

### Issue: Web Search Fails

**Symptoms**:
```
⚠️ Web search error: [error message]
⚠️ No web results, using fallback analysis
```

**Solution**: 
- Network connectivity issue
- DDGS rate limiting
- System still works with fallback
- Search terms will be generated without web context

---

### Issue: Structure Missing

**Symptoms**:
```
⚠️ Some structural elements may be missing (Abstract: False, ...)
```

**Possible Causes**:
- LLM didn't follow instructions
- Response was truncated
- Insufficient source material

**Solution**:
- Check LLM configuration (model, temperature)
- Verify sufficient sources were found
- May need to adjust prompt or increase max tokens

---

### Issue: Short Output

**Symptoms**: Paper is too short (<1000 words)

**Possible Causes**:
- Few sources found
- LLM response truncated
- Max tokens set too low

**Solution**:
- Check number of sources found
- Increase max_tokens in config
- Verify research agent found quality sources

---

## 6. API Testing with Frontend

### Start Both Services

Terminal 1:
```powershell
cd backend
python api.py
```

Terminal 2:
```powershell
cd frontend
pnpm dev
```

### Test Through UI

1. Navigate to `http://localhost:3000`
2. Enter a research query
3. Watch the progress indicators:
   - Query validation
   - **Web search and analysis** (new!)
   - Research progress
   - Summarization
   - Verification
   - **PhD-grade synthesis** (enhanced!)
   - Formatting

4. Review the output:
   - Should see complete paper structure
   - Abstract, Introduction, Chapters, Discussion, Conclusion
   - Extensive citations
   - Professional formatting

---

## 7. Performance Metrics

### Expected Timings

- Query Validation: 1-2 seconds
- **Web Search**: 3-5 seconds (new!)
- Query Analysis: 3-5 seconds
- Research: 20-60 seconds (depends on iterations)
- Summarization: 10-20 seconds
- Verification: 10-20 seconds
- **PhD Synthesis**: 30-90 seconds (enhanced - longer due to comprehensive output)
- Formatting: 1-2 seconds

**Total**: 80-200 seconds (varies by query complexity and source availability)

### Quality Metrics

- **Search Term Relevance**: Should be >80% relevant to web results
- **Source Quality**: Average confidence score >0.6
- **Citation Density**: At least 1 citation per 2-3 sentences
- **Structure Completeness**: All 5 main sections present
- **Word Count**: 2000-5000 words typical
- **Academic Quality**: Publication-ready

---

## 8. Debugging Tips

### Enable Verbose Logging

In `api.py` or orchestrator, add print statements:

```python
print(f"DEBUG: Web results: {web_results}")
print(f"DEBUG: Generated questions: {search_terms}")
print(f"DEBUG: Paper length: {len(answer)} characters")
```

### Check Individual Agents

Test each agent separately:

```python
# Test Query Analyzer with Web Search
analyzer = QueryAnalyzerAgent()
result = await analyzer.process("quantum computing")
print(result)

# Test Reasoning Agent
reasoning = ReasoningAgent()
paper = await reasoning.process(query, summaries)
print(paper)
```

### Verify Dependencies

```powershell
cd backend
pip list | grep -E "(langchain|ddgs|fastapi)"
```

Should show:
- langchain
- langchain-openai
- duckduckgo-search (ddgs)
- fastapi
- uvicorn

---

## 9. Success Criteria

✅ **Web Search Integration**
- Web search executes after validation
- Results inform search term generation
- No errors in web search process

✅ **PhD-Grade Output**
- All 5 sections present (Abstract, Intro, Body, Discussion, Conclusion)
- Body has 3-5 structured chapters
- Each chapter has subsections
- Professional academic tone
- Extensive citations throughout

✅ **Quality Standards**
- Paper is comprehensive (2000+ words)
- Critical analysis, not just summaries
- Multiple perspectives synthesized
- Research gaps identified
- Future directions suggested

✅ **Technical Performance**
- No errors or exceptions
- Completes within reasonable time
- Handles edge cases gracefully
- Progress updates work correctly

---

## 10. Sample Expected Output Structure

```markdown
# [Research Topic]

## ABSTRACT

[150-250 word comprehensive summary covering background, objectives, 
findings, and significance - no citations]

## INTRODUCTION

Climate change represents one of the most pressing challenges... [1]
Recent studies have demonstrated significant impacts... [2][3]

This paper examines...

The structure of this paper is organized as follows...

## CHAPTER 1: THEORETICAL FOUNDATIONS

### 1.1 Climate System Dynamics
The Earth's climate system operates through... [4][5]

### 1.2 Ocean-Atmosphere Interactions
Research has shown that ocean systems... [6][7][8]

## CHAPTER 2: IMPACTS ON MARINE ECOSYSTEMS

### 2.1 Coral Reef Degradation
Coral reefs have experienced unprecedented bleaching... [9][10]

### 2.2 Species Migration Patterns
Marine species are shifting their ranges... [11][12]

## CHAPTER 3: ADAPTATION AND MITIGATION

[Content with citations]

## DISCUSSION

Synthesizing the findings across these chapters reveals...
Multiple studies converge on... [15][16][17]
However, contradictions exist in... [18][19]

## CONCLUSION

This research has demonstrated that climate change...
The implications for policy and future research...
Future investigations should focus on...

## REFERENCES

[1] Source 1 - Title, URL
[2] Source 2 - Title, URL
[3] Source 3 - Title, URL
...
```

---

## Quick Validation Checklist

After running a test query, verify:

- [ ] No errors in console
- [ ] Web search executed successfully
- [ ] Search terms are specific questions (not keywords)
- [ ] Abstract section exists
- [ ] Introduction section exists
- [ ] 3-5 main body chapters exist
- [ ] Discussion section exists
- [ ] Conclusion section exists
- [ ] Heavy citation usage [1][2][3]
- [ ] Paper is 2000+ words
- [ ] Academic, professional tone
- [ ] References list matches citations

**If all checked: SUCCESS! ✅**

---

## Support

If issues persist:
1. Check console logs for specific errors
2. Verify all dependencies installed
3. Ensure OpenAI API key is valid
4. Check network connectivity for web search
5. Review the IMPROVEMENTS_SUMMARY.md for details


