# Outliers - IR Programming Assignment 1

## Preprocessing

Run:

```bash
python3 outliers_preprocess.py
```

Defaults:

- Input: `cran.all.1400`
- Stop words: `stopwords.txt`
- Output: `outliers_processed.all`
- Stemmer: `outliers_porter.py`

The pipeline is: tokenize -> normalize -> stem -> remove stemmed stop words.
The output contains one `.I <docid>` / `.S` block per document, followed by one
line of processed tokens.

## For indexing

- Read tokens from `outliers_processed.all` until the next `.I` block.
- Add each document ID only once per term.
- Sort terms lexicographically and postings in ascending document-ID order.
- Name the index `outliers_cran.index`.
- Its first line must contain: `<vocabulary_size>, <maximum_docid>`.

## For Boolean search

- Parse `term1 AND term2` or `term1 OR term2` before preprocessing the terms.
- Reuse `preprocess_text()` from `outliers_preprocess.py` for each query term.
- Do not preprocess `AND` or `OR` as normal terms.
- Search the generated index, not the original collection.

Keep all submitted program and output filenames prefixed with `outliers`.
