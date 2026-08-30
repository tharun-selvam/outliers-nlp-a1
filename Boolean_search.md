# Boolean Search on Cranfield Collection


## Overview

This program performs **Boolean retrieval** on the Cranfield document collection using a pre-built inverted index.

The Boolean search module supports queries containing exactly **two query terms** connected by either:

- `AND`
- `OR`

Example queries:

```text
aircraft AND pressure
experimental OR aerodynamic
```

The search is performed over the inverted index file:

```text
outliers_cran.index
```

---

## Files Needed-

The Boolean search program requires the following files:

```text
outliers_boolean_search.py
outliers_cran.index
outliers_preprocess.py
outliers_porter.py
```

The inverted index is generated beforehand using the preprocessing and indexing programs.

---

## Query Processing

Each query term is processed using the same normalization and stemming logic used during document preprocessing.

The query-processing steps are:

1. Tokenization
2. Normalization
3. Porter stemming
4. Lookup in the inverted index

This will ensure that query terms are represented in the same form as the terms stored in the index.

For example, a query term such as:

```text
experimental
```

is normalized and stemmed before searching the index.

---

## Index Format

The inverted index is stored in the following form:

```text
<vocabulary_size> <maximum_docid>

term1 docid1,docid2,docid3,...
term2 docid1,docid2,...
```

Example:

```text
588 1400
aerodynam 1,10,11
experiment 1,7,9,21,27
slipstream 1,532
```

The postings list associated with each term contains document IDs arranged in ascending order.

---

## Boolean AND

For a query of the form:

```text
term1 AND term2
```

the postings lists of both terms are retrieved from the index.

The intersection is computed using a **two-pointer postings-list intersection algorithm**.

Example:

```text
P1 = [1, 4, 7, 10, 15]
P2 = [2, 4, 7, 11, 15]
```

Result:

```text
[4, 7, 15]
```

The time complexity is:

```text
O(m + n)
```

where:

- `m` = length of the first postings list
- `n` = length of the second postings list

---

## Boolean OR

For a query of the form:

```text
term1 OR term2
```

the two sorted postings lists are merged.

Example:

```text
P1 = [1, 4, 7, 10]
P2 = [2, 4, 8, 10]
```

Result:

```text
[1, 2, 4, 7, 8, 10]
```

Duplicate document IDs are included only once in this case to avoid redundancy.

The time complexity is:

```text
O(m + n)
```

---

## Search Efficiency

The complete inverted index is loaded into a Python dictionary using the structure:

```text
term -> postings list
```

This allows average-case lookup of a query term in:

```text
O(1)
```

After retrieving the postings lists:

```text
AND operation: O(m + n)
OR operation : O(m + n)
```

This avoids scanning all 1400 documents for each Boolean query.

---

## How to Run

Open a terminal in the folder containing the program.

Run:

```bash
python3 outliers_boolean_search.py
```

The program will ask for a Boolean query:

```text
Enter Boolean query (example: aircraft AND pressure):
```

Enter a query such as:

```text
aircraft AND pressure
```

The program displays:

- Original query
- Processed query
- Postings list of both query terms
- Number of matching documents
- Matching document IDs

The result(resultant doc-ids) is also written to:

```text
outliers_boolean_results.txt
```

---

## Running a Query Directly from the Terminal

A query may also be supplied using the `--query` option.

### AND Query

```bash
python3 outliers_boolean_search.py --query "aircraft AND pressure"
```

### OR Query

```bash
python3 outliers_boolean_search.py --query "aircraft OR pressure"
```

---

## Output

The output file contains the document IDs that satisfy the Boolean query that was performed.

Example:

```text
4,7,15,21,35
```

The document IDs are written in ascending order.

---

## Supported Query Format

The current implementation supports exactly two query terms connected by one Boolean operator.

### Valid Queries

```text
aircraft AND pressure
aircraft OR pressure
```

The operators are case-insensitive, so the following are also accepted:

```text
aircraft and pressure
aircraft or pressure
```

### Unsupported Queries

```text
aircraft AND pressure OR wing
NOT aircraft
aircraft
```

Only `AND` and `OR` are supported, as required by the assignment.

---

## Error Handling

The program checks for:

- Missing index file
- Invalid index format
- Invalid Boolean query format
- Missing query terms
- Unsupported Boolean operators
- Query terms not found in the vocabulary

If a query term is absent from the inverted index, its postings list is treated as empty.

---

## Complexity Summary

| Operation | Time Complexity |
|---|---|
| Index loading | `O(V + P)` |
| Query term lookup | Average `O(1)` |
| Boolean AND | `O(m + n)` |
| Boolean OR | `O(m + n)` |

where:

- `V` = vocabulary size
- `P` = total number of postings
- `m` = size of the first postings list
- `n` = size of the second postings list

---

## Project Structure

```text
project-folder/
├── outliers_preprocess.py
├── outliers_porter.py
├── outliers_indexing.py
├── outliers_processed.all
├── outliers_cran.index
├── outliers_boolean_search.py
├── outliers_boolean_results.txt
└── README.md
```

---

## Notes

- The Boolean search is performed directly over the inverted index.
- Query terms are normalized and stemmed before lookup.
- No information retrieval library is used.
- Boolean AND and OR are implemented using standard postings-list algorithms.
- The implementation takes advantage of the fact that postings lists are already stored in sorted order.
