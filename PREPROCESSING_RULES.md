# Part 1 Preprocessing Decisions

| Area | Chosen rule | Example or effect |
| --- | --- | --- |
| Fields | Process `.T` and `.W`; preserve `.I`; ignore `.A` and `.B`. | Only titles and abstracts contribute tokens. |
| Processing order | Tokenize, normalize, stem, then remove stop words. | Stop words must be stemmed before comparison. |
| Case | Convert all text to lowercase. | `Flow` and `flow` become `flow`. |
| Possessives and contractions | Remove possessive endings and internal apostrophes. | `Prandtl's` becomes `prandtl`; `can't` becomes `cant`. |
| Hyphens and slashes | Treat them as token boundaries. | `boundary-layer` becomes `boundary`, `layer`. |
| Numbers | Keep integers and decimals. Remove thousands-separator commas. | `0.1` stays `0.1`; `15,000` becomes `15000`. |
| Valid tokens | Keep words, integers, and decimals matching `[a-z]+|\d+(?:\.\d+)?`. | Other punctuation is discarded. |
| Short tokens | Keep single-character tokens unless they are stop words. | Scientific variables such as `x` and `y` remain. |
| Repeated tokens | Preserve token order and repetitions. | The indexing stage will deduplicate document IDs. |
| Stemmer | Use the checked-in Python 3 `outliers_porter.py`. | The same implementation must process documents, stop words, and queries. |
| Stop words | Use the corrected `stopwords.txt`; stem its words before building the stop-word set. | `computer` stems to `comput`, so `comput` is removed after stemming. |
| Files | Use `cran.all.1400` and `stopwords.txt` by default; write `outliers_processed.all`. | Run `outliers_preprocess.py` without arguments. |
| Output format | Write `.I <docid>`, followed by `.S` and the processed tokens. | One output block is written for each document. |

## Dataset-specific parsing decision

After the first `.W` in a document, treat all following text as abstract text
until the next `.I`. Ignore any tag-only lines found inside that region. This
prevents extra `.A`, `.B`, or `.W` lines in documents 240, 576, and 578 from
causing abstract text to be lost.

## Minimum validation

- Produce 1,400 ordered document blocks with IDs 1 through 1400.
- Ensure author and bibliography text is excluded.
- Ensure every output token follows the chosen word/number pattern.
- Ensure no stemmed stop word remains.
- Use identical preprocessing for later Boolean query terms.
- Running the program twice must produce identical output.
