# Knowledge Wiki from Photographed Pamphlets

This project takes vendor pamphlets photographed at a conference, OCRs them into text, and has a team of Claude agents distill them into a **knowledge wiki** — a store of linked Markdown files where every claim has a source, aliases are merged, and conflicts stay flagged. Analyst agents then answer questions from the wiki instead of re-reading the raw documents, which is both cheaper and more accurate than searching the originals each time.

It is built on Claude [Managed Agents](https://platform.claude.com/docs/en/managed-agents/memory) and [dynamic workflows](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration#dynamic-workflows).

## What the agent does

The build runs as **one session**: you send a single message describing the goal, and a lead agent (`wiki-builder`) writes a workflow from it, starts the run, and reports. The workflow puts four kinds of worker agents on the pamphlets, in phases:

| Agent | Phase | How many | What it does |
| --- | --- | --- | --- |
| `wiki-extractor` | Extract | One per batch, in parallel | Reads its batch of pamphlet text in full and files entities, relations, metrics, and open questions by the schema |
| `wiki-resolver` | Resolve | One | Works the top open questions the extractors flagged — checking the wiki first, then the documents — and answers with a source or marks the gap unresolvable |
| `wiki-analyzer` | Analyze | One per batch, in parallel | Checks what was filed against the source documents |
| `wiki-organizer` | Organize | One | Tidies the whole wiki: merges duplicates, fixes links, updates the index |

The result is a memory store with `entities/`, `relations/`, `metrics/`, `open_questions/`, an `_index.md` catalog, and `escalations.md` for flagged items. The extractors follow rules that matter for messy sources like these: one entity file per real-world thing with all its names as aliases, superseded facts closed with `valid_to` rather than deleted, operative language quoted word for word, and "not in this document" recorded instead of global absence claims.

To query it, analyst agents mount the wiki **read-only**, one fresh session per question. They navigate the wiki's layout (index map first, then only the sections needed), cite every fact, and say "Not in the wiki" on a miss. They cannot write to the wiki, so a guess at query time never becomes the next analyst's fact.

## The pamphlets

`my_pamphlets/` holds six photographed vendor pamphlets (AI gateway, identity, dev-platform, and security products). Because they are photos rather than digital PDFs, `convert_pamphlets.py` runs a three-tier OCR pipeline, cheapest first, stopping at the first tier that yields enough text:

1. **docling**, default OCR (local, free)
2. **docling + EasyOCR**, full-page forced OCR (local, free, slower)
3. **Claude vision** (API tokens — only when both local passes fail)

Each result is cleaned (embedded images stripped, common OCR confusions like `Al` → `AI` fixed) and written to `pamphlet_corpus/` as a `.txt` file with a `[SOURCE: ...]` provenance header, which is the format the wiki build expects.

## Repository layout

```
distill_documents_into_knowledge_wiki.ipynb   The main notebook: build the wiki, query it, measure cost
utilities.py                                  Helpers: normalization, batching, workflow tracking, reports
convert_pamphlets.py                          OCR pipeline: my_pamphlets/*.pdf -> pamphlet_corpus/*.txt
prompts/                                      System prompts: lead agent, analyzer, organizer, baseline analyst
my_pamphlets/                                 The photographed pamphlet PDFs
pamphlet_corpus/                              OCR'd, provenance-stamped text ready for the wiki build
assets/                                       Diagrams and benchmark charts used by the notebook
originals/                                    Original source material
```

## Running it

1. **Setup.** Python 3.11+, then `pip install -r requirements.txt`. Authenticate with a Claude API credential (`ANTHROPIC_API_KEY` in a `.env` file, or `ant auth login`). Managed Agents (beta) must be available to your API organization.
2. **Convert the pamphlets** (needs a docling venv at `~/.venvs/docling` for the local tiers):
   ```
   python convert_pamphlets.py                 # my_pamphlets/ -> pamphlet_corpus/
   python convert_pamphlets.py --force         # redo files whose .txt already exists
   ```
3. **Build and query the wiki.** Point the notebook at the pamphlet corpus and run it top to bottom:
   ```
   set COOKBOOK_DOCS=pamphlet_corpus
   jupyter lab distill_documents_into_knowledge_wiki.ipynb
   ```
   The notebook estimates the build cost before creating any agent and stops if it exceeds the budget (`COOKBOOK_BUDGET_USD`, default $60). Models for each agent role are also set by environment variable (`COOKBOOK_BUILD_MODEL`, `COOKBOOK_CONSOLIDATE_MODEL`, `COOKBOOK_QUERY_MODEL`, `COOKBOOK_LEAD_MODEL`); the defaults use Claude Haiku 5.5 for the readers and Claude Sonnet 5.5 for the lead agent.

## Why bother with a wiki?

A search index finds passages, but the hardest facts come from *comparing* documents: two metrics with the same name, one company under three names, a figure a later document contradicts. The wiki works those out once, at build time. In the notebook's benchmark, a small model answering from the wiki scored within a point of a larger model searching the raw documents, at about 1/15 the price per answer — and about 3 points better than the same small model searching the documents itself.
