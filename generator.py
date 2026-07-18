# ============================================================
# Episteme — Generator (generator.py)
# ============================================================

import os
import re
import arxiv
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from retriever import hybrid_retrieve

load_dotenv()

GROQ_MODEL  = "llama-3.3-70b-versatile"
TEMPERATURE = 0.1

# ─── Mode Keywords ────────────────────────────────────────────
QUIZ_KEYWORDS    = ["quiz me on", "quiz on", "test me on", "mcq on", "quiz me"]
COMPARE_KEYWORDS = [" vs ", " versus ", "compare ", "difference between"]
ELI5_KEYWORDS    = ["eli5:", "eli5 ", "explain like i'm 5", "explain simply",
                    "simple explanation of", "explain like a child"]
CODE_KEYWORDS    = ["explain this code", "explain the code", "debug this",
                    "find bugs in", "review this code", "what does this code do"]
DIAGRAM_KEYWORDS = ["draw diagram", "draw a diagram", "block diagram of",
                    "flowchart of", "diagram of", "show diagram"]

# ─── Paper Keywords ───────────────────────────────────────────
PAPER_KEYWORDS = [
    "paper", "research paper", "find paper", "arxiv", "doi",
    "journal", "publication", "i need link", "give me link",
    "provide link", "source of", "link of", "download paper",
    "where can i find", "pdf of paper",
]

# ─── Non-STEM Filter ──────────────────────────────────────────
NON_STEM_TOPICS = [
    "makeup", "lipstick", "foundation", "mascara", "cosmetic",
    "skincare", "fashion", "clothing", "dress", "outfit",
    "celebrity", "actor", "actress", "bollywood", "hollywood",
    "cricket score", "football score", "match result",
    "cooking recipe", "restaurant menu",
    "politics", "election", "political party",
    "song lyrics", "movie plot", "drama episode",
    "horoscope", "astrology", "zodiac",
]

def is_stem_query(query: str) -> bool:
    q = query.lower()
    if any(topic in q for topic in NON_STEM_TOPICS):
        return False
    return True

def is_paper_query(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in PAPER_KEYWORDS)


# ─── ArXiv Search ─────────────────────────────────────────────
def search_arxiv(query: str, max_results: int = 5) -> str:
    """Search ArXiv for papers — 100% accurate, free, unlimited."""
    try:
        # Clean query — remove common words
        clean = query.lower()
        for w in ["i need", "find", "link", "source", "paper", "research paper",
                  "give me", "provide", "of", "the", "this"]:
            clean = clean.replace(w, "").strip()
        clean = clean.strip() or query

        client  = arxiv.Client()
        search  = arxiv.Search(
            query      = clean,
            max_results= max_results,
            sort_by    = arxiv.SortCriterion.Relevance,
        )
        results = list(client.results(search))

        if not results:
            return None

        answer = f"**Found {len(results)} papers on ArXiv:**\n\n"
        for i, r in enumerate(results, 1):
            authors = ", ".join([a.name for a in r.authors[:3]])
            if len(r.authors) > 3:
                authors += " et al."
            answer += f"**{i}. {r.title}**\n"
            answer += f"👥 Authors: {authors}\n"
            answer += f"📅 Published: {r.published.strftime('%B %Y')}\n"
            answer += f"🔗 ArXiv: {r.entry_id}\n"
            answer += f"📄 PDF: {r.pdf_url}\n"
            if r.summary:
                summary = r.summary[:200] + "..." if len(r.summary) > 200 else r.summary
                answer += f"📝 Abstract: {summary}\n"
            answer += "\n"

        return answer

    except Exception as e:
        return None


# ─── DuckDuckGo Search ────────────────────────────────────────
def search_web(query: str, max_results: int = 4) -> str:
    """Search web via DuckDuckGo — free, unlimited."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return None

        answer = f"**Web Search Results:**\n\n"
        for i, r in enumerate(results, 1):
            answer += f"**{i}. {r.get('title', '')}**\n"
            answer += f"🔗 {r.get('href', '')}\n"
            if r.get('body'):
                body = r['body'][:200] + "..." if len(r['body']) > 200 else r['body']
                answer += f"_{body}_\n"
            answer += "\n"

        return answer

    except Exception:
        return None


# ─── Smart Paper Search ───────────────────────────────────────
def search_papers(query: str) -> str:
    """Try ArXiv first, then DuckDuckGo as backup."""

    # 1. Try ArXiv first — most accurate for papers
    arxiv_result = search_arxiv(query)
    if arxiv_result:
        return arxiv_result, True

    # 2. Fallback to DuckDuckGo
    web_result = search_web(f"{query} research paper arxiv")
    if web_result:
        return web_result, False

    # 3. Manual search links
    q_encoded = query.replace(" ", "+")
    fallback  = (
        f"Could not find papers automatically. Search manually:\n\n"
        f"🔍 **ArXiv**: https://arxiv.org/search/?query={q_encoded}\n"
        f"🔍 **Google Scholar**: https://scholar.google.com/scholar?q={q_encoded}\n"
        f"🔍 **IEEE Xplore**: https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={q_encoded}\n"
        f"🔍 **ResearchGate**: https://www.researchgate.net/search?q={q_encoded}\n"
    )
    return fallback, False


# ─── System Prompt ────────────────────────────────────────────
SYSTEM_PROMPT = """You are Episteme, an intelligent STEM knowledge assistant.
You answer questions about Science, Technology, Engineering, Mathematics,
and related academic/research topics.

LANGUAGE RULES:
1. Detect user language and respond in SAME language
2. English → English only
3. Roman Urdu → Roman Urdu only (NEVER Hindi)
4. Never mix languages

CRITICAL — NEVER HALLUCINATE LINKS:
- NEVER generate or guess paper links/DOIs/URLs
- Only use links from provided context

CONTENT RULES:
1. Answer from provided context first
2. PDF content → prioritize
3. Use LaTeX for math: $$formula$$ for block, $formula$ for inline
4. Structure: Definition → How it works → Example → Applications

END every response with:
---CONFIDENCE---
LEVEL: [HIGH/MEDIUM/LOW]
REASON: [one line]
---FOLLOWUP---
1. [follow-up question]
2. [follow-up question]
3. [follow-up question]
---END---

CONVERSATION HISTORY:
{chat_history}

CONTEXT:
{context}"""

QUIZ_PROMPT = """Generate exactly 5 MCQ questions about: {topic}

Use this EXACT format:
QUIZ_START
Q1: [Question]
A) [Option]
B) [Option]
C) [Option]
D) [Option]
ANSWER: [A/B/C/D]
EXPLANATION: [Brief explanation]

Q2: [Question]
A) [Option]
B) [Option]
C) [Option]
D) [Option]
ANSWER: [A/B/C/D]
EXPLANATION: [Brief explanation]

Q3: [Question]
A) [Option]
B) [Option]
C) [Option]
D) [Option]
ANSWER: [A/B/C/D]
EXPLANATION: [Brief explanation]

Q4: [Question]
A) [Option]
B) [Option]
C) [Option]
D) [Option]
ANSWER: [A/B/C/D]
EXPLANATION: [Brief explanation]

Q5: [Question]
A) [Option]
B) [Option]
C) [Option]
D) [Option]
ANSWER: [A/B/C/D]
EXPLANATION: [Brief explanation]
QUIZ_END"""

COMPARE_PROMPT = """You are a STEM expert. Compare {item1} and {item2}.

Use this EXACT format:
COMPARE_START
TITLE: {item1} vs {item2}
ROW: Feature | {item1} | {item2}
ROW: Type/Category | [value] | [value]
ROW: Key Function | [value] | [value]
ROW: Performance | [value] | [value]
ROW: Cost | [value] | [value]
ROW: Complexity | [value] | [value]
ROW: Power Usage | [value] | [value]
ROW: Best For | [value] | [value]
ROW: Limitations | [value] | [value]
SUMMARY: [2-3 sentences on when to use each]
COMPARE_END"""

ELI5_PROMPT = """Explain {topic} as simply as possible.
- Use everyday analogies
- No technical jargon
- Short sentences
- Real world example
- Max 150 words
End with: "In short: [one sentence]"
Topic: {topic}"""

CODE_PROMPT = """Analyze this code and explain it:

{code}

Provide:
## What It Does
[2-3 sentences]

## Key Lines Explained
[explain important lines]

## Bugs Found
[list any bugs or "No bugs found"]

## Improvements
[suggestions]

## Language Detected
[language/framework]"""

DIAGRAM_PROMPT = """Create a Mermaid.js diagram for: {topic}

Important rules:
- Use simple flowchart syntax only
- NO special characters in node labels
- NO parentheses in labels
- NO colons in labels
- Keep labels short and simple
- Maximum 10 nodes

Return ONLY this:
DIAGRAM_START
graph TD
    A[Start] --> B[Step 1]
    B --> C[Step 2]
DIAGRAM_END

Now create diagram for: {topic}"""

SUMMARY_PROMPT = """Create a session summary.

Conversation:
{conversation}

## Session Summary

**Topics Discussed:**
- [topics]

**Key Concepts:**
- [concepts]

**Questions Asked:**
- [questions]

**Key Takeaways:**
- [takeaways]

**Next Steps:**
- [recommendations]"""


def load_llm():
    return ChatGroq(model=GROQ_MODEL, temperature=TEMPERATURE,
                    api_key=os.getenv("GROQ_API_KEY"))


def detect_mode(query: str) -> str:
    q = query.lower()
    if any(k in q for k in QUIZ_KEYWORDS):
        return "quiz"
    if any(k in q for k in COMPARE_KEYWORDS):
        return "compare"
    if any(k in q for k in ELI5_KEYWORDS):
        return "eli5"
    if any(k in q for k in CODE_KEYWORDS):
        return "code"
    if any(k in q for k in DIAGRAM_KEYWORDS):
        return "diagram"
    return "normal"


def format_context(results: dict) -> str:
    parts = []
    for doc in results["all"]:
        dtype  = doc.metadata.get("type", "unknown")
        source = doc.metadata.get("source", "Unknown")
        title  = doc.metadata.get("title", "")
        if dtype == "pdf":
            label = f"PDF: {title}"
        elif dtype == "wikipedia_live":
            label = f"Wikipedia: {title}"
        elif dtype in ["arxiv_live", "arxiv"]:
            label = f"ArXiv: {title}"
        else:
            label = f"KB: {title}"
        parts.append(f"[{label}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def format_history(history: list) -> str:
    if not history:
        return "No previous conversation."
    out = []
    for msg in history[-4:]:
        role = "User" if msg["role"] == "user" else "Episteme"
        out.append(f"{role}: {msg['content'][:200]}")
    return "\n".join(out)


def parse_normal(text: str) -> dict:
    answer     = text
    confidence = "HIGH"
    reason     = ""
    followups  = []

    if "---CONFIDENCE---" in text:
        parts  = text.split("---CONFIDENCE---")
        answer = parts[0].strip()
        rest   = parts[1] if len(parts) > 1 else ""
        for line in rest.split("\n"):
            if line.startswith("LEVEL:"):
                confidence = line.replace("LEVEL:", "").strip()
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()

    if "---FOLLOWUP---" in text:
        fq_raw = text.split("---FOLLOWUP---")[-1].split("---END---")[0].strip()
        for line in fq_raw.split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                q = line.split(".", 1)[-1].strip()
                if q:
                    followups.append(q)

    for m in ["---CONFIDENCE---", "---FOLLOWUP---", "---END---"]:
        answer = answer.split(m)[0]
    answer = answer.strip()

    return {"answer": answer, "confidence": confidence,
            "reason": reason, "followups": followups[:3]}


def parse_quiz(text: str) -> list:
    questions = []
    if "QUIZ_START" not in text or "QUIZ_END" not in text:
        return questions
    content = text.split("QUIZ_START")[1].split("QUIZ_END")[0].strip()
    blocks  = re.split(r'\nQ\d+:', content)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines   = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        q_text  = lines[0]
        options = {}
        answer  = ""
        explain = ""
        for line in lines[1:]:
            if line.startswith("A)"):
                options["A"] = line[2:].strip()
            elif line.startswith("B)"):
                options["B"] = line[2:].strip()
            elif line.startswith("C)"):
                options["C"] = line[2:].strip()
            elif line.startswith("D)"):
                options["D"] = line[2:].strip()
            elif line.startswith("ANSWER:"):
                answer = line.replace("ANSWER:", "").strip()
            elif line.startswith("EXPLANATION:"):
                explain = line.replace("EXPLANATION:", "").strip()
        if q_text and len(options) >= 2 and answer:
            questions.append({
                "question": q_text, "options": options,
                "answer": answer, "explanation": explain
            })
    return questions


def parse_compare(text: str) -> dict:
    if "COMPARE_START" not in text:
        return {}
    content = text.split("COMPARE_START")[1].split("COMPARE_END")[0].strip()
    title   = ""
    rows    = []
    summary = ""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("ROW:"):
            parts = line.replace("ROW:", "").split("|")
            if len(parts) == 3:
                rows.append([p.strip() for p in parts])
        elif line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()
    return {"title": title, "rows": rows, "summary": summary}


def parse_diagram(text: str) -> str:
    if "DIAGRAM_START" in text and "DIAGRAM_END" in text:
        code = text.split("DIAGRAM_START")[1].split("DIAGRAM_END")[0].strip()
        code = re.sub(r'\(([^)]*)\)', r'[\1]', code)
        return code
    return ""


def generate_citation(sources: list) -> str:
    out = []
    for i, src in enumerate(sources[:3], 1):
        if "wikipedia" in src.lower():
            topic = src.split("/")[-1].replace("_", " ")
            out.append(f"[{i}] Wikipedia, \"{topic}.\" [Online]. Available: {src}")
        elif "arxiv" in src.lower():
            out.append(f"[{i}] ArXiv Paper. [Online]. Available: {src}")
        elif "pubmed" in src.lower():
            out.append(f"[{i}] PubMed Research. [Online]. Available: {src}")
        else:
            out.append(f"[{i}] {src}")
    return "\n".join(out)


def generate_answer(
    query: str,
    chat_history: list = [],
    uploaded_pdfs: list = [],
) -> dict:
    """Main answer generation with mode detection."""
    llm  = load_llm()
    mode = detect_mode(query)

    base = {
        "mode": mode, "answer": "", "sources": [], "citations": "",
        "followups": [], "confidence": "HIGH", "reason": "",
        "is_research": False, "pdf_used": False,
        "questions": [], "compare": {}, "diagram": "", "topic": ""
    }

    # ── Quiz ──────────────────────────────────────────────────
    if mode == "quiz":
        topic = query.lower()
        for k in QUIZ_KEYWORDS:
            topic = topic.replace(k, "").strip()
        topic = topic.strip(" :") or "STEM concepts"
        base["topic"] = topic
        prompt    = ChatPromptTemplate.from_messages([("human", QUIZ_PROMPT)])
        result    = (prompt | llm).invoke({"topic": topic})
        questions = parse_quiz(result.content)
        base["questions"] = questions
        base["answer"]    = f"Quiz on: {topic.title()} ({len(questions)} questions)"
        return base

    # ── Compare ───────────────────────────────────────────────
    if mode == "compare":
        q      = query.lower()
        item1, item2 = "Item 1", "Item 2"
        for sep in [" vs ", " versus ", " and "]:
            if sep in q:
                raw = q
                for k in ["compare ", "difference between ", "comparison of "]:
                    raw = raw.replace(k, "")
                parts = raw.split(sep, 1)
                item1 = parts[0].strip().title()
                item2 = parts[1].strip().title()
                break
        prompt  = ChatPromptTemplate.from_messages([("human", COMPARE_PROMPT)])
        result  = (prompt | llm).invoke({"item1": item1, "item2": item2})
        compare = parse_compare(result.content)
        if not compare.get("rows"):
            result  = (prompt | llm).invoke({"item1": item1, "item2": item2})
            compare = parse_compare(result.content)
        base["compare"] = compare
        base["answer"]  = f"Comparison: {item1} vs {item2}"
        base["topic"]   = f"{item1} vs {item2}"
        return base

    # ── ELI5 ──────────────────────────────────────────────────
    if mode == "eli5":
        topic = query.lower()
        for k in ELI5_KEYWORDS:
            topic = topic.replace(k, "").strip(" :")
        topic = topic or query
        prompt = ChatPromptTemplate.from_messages([("human", ELI5_PROMPT)])
        result = (prompt | llm).invoke({"topic": topic})
        base["answer"] = result.content
        base["topic"]  = topic
        return base

    # ── Code ──────────────────────────────────────────────────
    if mode == "code":
        prompt = ChatPromptTemplate.from_messages([("human", CODE_PROMPT)])
        result = (prompt | llm).invoke({"code": query})
        base["answer"] = result.content
        return base

    # ── Diagram ───────────────────────────────────────────────
    if mode == "diagram":
        topic = query.lower()
        for k in DIAGRAM_KEYWORDS:
            topic = topic.replace(k, "").strip()
        prompt  = ChatPromptTemplate.from_messages([("human", DIAGRAM_PROMPT)])
        result  = (prompt | llm).invoke({"topic": topic})
        diagram = parse_diagram(result.content)
        base["diagram"] = diagram
        base["topic"]   = topic
        base["answer"]  = f"Diagram: {topic}"
        return base

    # ── Paper Query — ArXiv + DuckDuckGo ──────────────────────
    if is_paper_query(query):
        answer, from_arxiv = search_papers(query)
        base["answer"]      = answer
        base["confidence"]  = "HIGH" if from_arxiv else "MEDIUM"
        base["is_research"] = True
        base["followups"]   = [
            "Can you explain what this paper is about?",
            "What are the key contributions of this research?",
            "Are there related papers on this topic?",
        ]
        return base

    # ── Normal ────────────────────────────────────────────────
    if not is_stem_query(query):
        base["answer"] = (
            "I'm Episteme, a STEM knowledge assistant. "
            "I can only help with **Science, Technology, "
            "Engineering, and Mathematics** topics. 🔬"
        )
        base["confidence"] = "HIGH"
        return base

    results = hybrid_retrieve(
        query=query, chat_history=chat_history, uploaded_pdfs=uploaded_pdfs
    )
    context = format_context(results)
    history = format_history(chat_history)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ])
    result = (prompt | llm).invoke({
        "context": context, "chat_history": history, "question": query
    })
    parsed = parse_normal(result.content)

    raw_sources = []
    for doc in results["all"]:
        src   = doc.metadata.get("source", "Unknown")
        dtype = doc.metadata.get("type", "")
        emoji = "📄" if dtype == "pdf" else "📚" if "wiki" in dtype else "🔬"
        raw_sources.append(f"{emoji} {src}")

    unique = list(set(raw_sources))
    clean  = [s.split(" ", 1)[-1] for s in unique]

    base.update({
        "answer"     : parsed["answer"],
        "confidence" : parsed["confidence"],
        "reason"     : parsed["reason"],
        "followups"  : parsed["followups"],
        "citations"  : generate_citation(clean),
        "sources"    : unique,
        "is_research": results["is_research"],
        "pdf_used"   : len(results.get("pdf", [])) > 0,
    })
    return base


def generate_summary(messages: list) -> str:
    if not messages:
        return "No conversation to summarize."
    conv = ""
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Episteme"
        conv += f"{role}: {msg['content'][:300]}\n\n"
    prompt = ChatPromptTemplate.from_messages([("human", SUMMARY_PROMPT)])
    result = (load_llm() | prompt).invoke({"conversation": conv})
    return result.content