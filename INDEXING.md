# Part 2 Indexing

The indexing program creates a simple inverted index for the preprocessed Cranfield text collection.

The input is the preprocessed collection:

```
outliers_processed.all
```

The output is:

```
outliers_cran.index
```

## Running the Program

From the project directory, run:

```
python outliers_indexing.py
```

The program automatically reads:

```
outliers_processed.all
```

and generates:

```
outliers_cran.index
```

## Indexing Process

The program creates an inverted index where each token is associated with the document IDs in which it appears.

- Tokens are sorted in lexicographical order.
- Document IDs in each postings list are sorted in ascending numerical order.
- Each document ID appears at most once for a particular token.

## Error Handling

The program performs validation and handles common input errors, including:

- Missing input file
- Input path not being a file
- Invalid document IDs
- Duplicate document IDs
- `.S` appearing before a document ID
- Missing token data after `.S`
- Incorrect number of documents
- Document IDs outside the expected range of 1–1400

Errors are reported in the terminal instead of silently producing an incorrect index.

## Result

The indexing program processes the 1400-document Cranfield collection and generates a simple inverted index containing the unique tokens and their corresponding document postings lists.
