# Search Quality Improvements

## Problem
When searching for topics like "blackholes", the system was returning irrelevant and low-quality sources including:
- Dictionary definitions (cppreference.com, dictionary sites)
- Completely unrelated content (Apple Recovery Key support forums)
- Foreign language content (French anatomy articles)
- Low-quality community forums

## Solutions Implemented

### 1. **Enhanced Blacklist** (`config.py`)
Added comprehensive domain blacklist to filter out:
- **Dictionaries**: merriam-webster.com, dictionary.com, thesaurus.com, etc.
- **Generic Q&A sites**: answers.com, ask.com, chacha.com
- **Unreliable forums**: reddit.com, quora.com, community sites
- **Commercial sites**: amazon.com, ebay.com, walmart.com
- **Translation sites**: translate.google.com, linguee.com
- **Other low-quality**: wikihow.com, thoughtco.com, reference.com

Total domains blocked: **40+**

### 2. **AI-Based Relevance Verification** (`research_agent.py`)
- New feature: `ENABLE_AI_RELEVANCE_CHECK = True`
- Uses LLM to verify each source actually relates to the search topic
- Filters out completely off-topic content before final selection
- Smart verification: auto-approves high-scoring trusted sources to save API calls
- Only verifies borderline or untrusted sources

Example verification:
```
Query: "black holes"
Source: "Apple Recovery Key for Reset"
AI Response: NO (filtered out)
```

### 3. **Stricter Relevance Scoring** (`config.py`)
- Increased `MIN_RELEVANCE_SCORE` from **0.25 → 0.35** (40% increase)
- Higher quality threshold ensures only relevant content passes

### 4. **Improved Dictionary Detection** (`research_agent.py`)
Enhanced dictionary content detection with:
- **27 indicators** (up from 13)
- New patterns: "part of speech", "word forms", "conjugation", "syllable"
- Title-based detection for dictionary sites
- Heavy penalty: **-0.9** (essentially filters out)
- Early detection in content extraction phase

### 5. **Foreign Language Filtering** (`research_agent.py`)
New feature to detect and penalize non-English content:
- Detects French, Spanish, German indicators
- Checks non-ASCII character ratio
- Penalties:
  - Strong signature (2+ indicators or >15% non-ASCII): **-0.8**
  - Mild signature (1 indicator or >8% non-ASCII): **-0.4**

### 6. **Expanded Trusted Scientific Domains** (`trusted_domains.py`)
Added **15+ new trusted domains** specifically for scientific content:

**Physics & Astronomy:**
- aps.org (American Physical Society)
- iop.org (Institute of Physics)
- eso.org (European Southern Observatory)
- adsabs.harvard.edu (Astrophysics Data System)
- stsci.edu (Space Telescope Science Institute)
- quantamagazine.org (Quanta Magazine)
- physicsworld.com, phys.org

**Math & Computer Science:**
- mathworld.wolfram.com
- projecteuclid.org
- ams.org (American Mathematical Society)

**Medical:**
- clinicaltrials.gov
- cochranelibrary.com

### 7. **Multi-Layer Filtering Pipeline**

The system now uses a **5-stage filtering process**:

```
Stage 1: Domain Blacklist Check
   └─> Blocks 40+ known low-quality domains

Stage 2: Content Extraction & Scoring
   └─> Dictionary penalty (-0.9)
   └─> Foreign language penalty (-0.8)
   └─> Trust boost (1.4x for trusted sources)

Stage 3: Minimum Relevance Filter
   └─> Requires score >= 0.35 (increased threshold)

Stage 4: AI Relevance Verification (NEW)
   └─> LLM verifies topic relevance
   └─> Filters completely off-topic content

Stage 5: Final Selection
   └─> Prioritizes trusted sources (50% allocation)
   └─> Ensures domain diversity
```

## Expected Results

### Before:
- ❌ Dictionary definitions
- ❌ Apple support forums
- ❌ Foreign language articles
- ❌ Generic unrelated content
- ⚠️ Low relevance scores (25%+)

### After:
- ✅ Scientific articles (NASA, ESO, Nature)
- ✅ Academic institutions (.edu domains)
- ✅ Peer-reviewed journals
- ✅ Trusted media (BBC, Scientific American)
- ✅ High relevance scores (35%+)
- ✅ English content only
- ✅ On-topic sources verified by AI

## Configuration Options

You can adjust these settings in `backend/agents/config.py`:

```python
# Quality threshold (0.0 - 1.0)
MIN_RELEVANCE_SCORE = 0.35

# Enable/disable AI verification
ENABLE_AI_RELEVANCE_CHECK = True

# Maximum sources
MAX_TOTAL_SOURCES = 8

# Add/remove blacklisted domains
BLACKLISTED_DOMAINS = {...}
```

## Performance Impact

- **AI Verification**: Adds ~1-2 seconds per search (only checks borderline sources)
- **Blacklist Check**: Negligible (<1ms per source)
- **Enhanced Scoring**: Minimal impact (<10ms per source)

## Testing Recommendations

Test with queries that previously gave poor results:
1. "black holes" - should return NASA, ESO, physics journals
2. "quantum computing" - should return academic/tech sources
3. "machine learning" - should return AI research papers

Verify:
- ✅ No dictionary definitions
- ✅ No foreign language content
- ✅ No off-topic community forums
- ✅ High percentage of trusted sources
- ✅ All sources relevant to query topic
