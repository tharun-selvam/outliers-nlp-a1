from pathlib import Path
import argparse
import re
import sys
from outliers_porter import PorterStemmer
from outliers_preprocess import tokenize, normalize, stem_tokens

BASE_DIR = Path(__file__).resolve().parent
GROUP_NAME = "outliers"
DEFAULT_INDEX = BASE_DIR / f"{GROUP_NAME}_cran.index"
DEFAULT_OUTPUT = BASE_DIR / f"{GROUP_NAME}_boolean_results.txt"


#Loading Inverted Index
def load_index(index_path: Path):
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")
    index = {}
    with index_path.open("r", encoding="utf-8") as file:
        first_line = file.readline().strip()
        if not first_line:
            raise ValueError("Index file is empty.")
        header = first_line.split()
        if len(header) != 2:
            raise ValueError(
                "Invalid index header. "
                "Expected: <vocabulary_size> <max_docid>"
            )
        try:
            vocabulary_size = int(header[0])
            max_docid = int(header[1])
        except ValueError:
            raise ValueError(
                "Vocabulary size and maximum document ID must be integers."
            )
        for line_number, raw_line in enumerate(file, start=2):
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid index entry at line {line_number}: {line!r}"
                )
            term = parts[0]
            postings_string = parts[1]
            try:
                postings = [
                    int(docid)
                    for docid in postings_string.split(",")
                ]
            except ValueError:
                raise ValueError(
                    f"Invalid postings list at line {line_number}"
                )

            # Verify that the postings list is sorted
            if postings != sorted(postings):
                raise ValueError(
                    f"Postings list for '{term}' is not sorted."
                )

            index[term] = postings
    # Check whether vocabulary size agrees with index file
    if len(index) != vocabulary_size:
        raise ValueError(
            f"Vocabulary size mismatch: header says "
            f"{vocabulary_size}, but {len(index)} terms were read."
        )
    return index, vocabulary_size, max_docid

#Preprocessing a Query Term
def preprocess_query_term(term: str, stemmer: PorterStemmer):
    tokens = tokenize(term)
    tokens = normalize(tokens)
    if len(tokens) != 1:
        raise ValueError(
            f"Each side of the Boolean query must contain exactly "
            f"one valid query term. Received: {term!r}"
        )
    tokens = stem_tokens(tokens, stemmer)
    return tokens[0]

#Parsing Boolean Query
def parse_query(query: str):
    pattern = re.compile(
        r"^\s*(.*?)\s+(AND|OR)\s+(.*?)\s*$",
        re.IGNORECASE,
    )
    match = pattern.fullmatch(query)
    if match is None:
        raise ValueError(
            "Invalid Boolean query.\n"
            "Expected format:\n"
            "    word1 AND word2\n"
            "or\n"
            "    word1 OR word2"
        )

    term1 = match.group(1)
    operator = match.group(2).upper()
    term2 = match.group(3)
    if not term1 or not term2:
        raise ValueError("Both query terms must be present.")
    return term1, operator, term2


#Boolean AND
def intersect_postings(postings1, postings2):
    result = []
    i = 0
    j = 0
    while i < len(postings1) and j < len(postings2):
        docid1 = postings1[i]
        docid2 = postings2[j]
        if docid1 == docid2:
            result.append(docid1)
            i += 1
            j += 1
        elif docid1 < docid2:
            i += 1
        else:
            j += 1
    return result
    
#Boolean OR
def union_postings(postings1, postings2):
    result = []
    i = 0
    j = 0
    while i < len(postings1) and j < len(postings2):
        docid1 = postings1[i]
        docid2 = postings2[j]
        if docid1 == docid2:
            result.append(docid1)
            i += 1
            j += 1
        elif docid1 < docid2:
            result.append(docid1)
            i += 1
        else:
            result.append(docid2)
            j += 1
    while i < len(postings1):
        result.append(postings1[i])
        i += 1
    while j < len(postings2):
        result.append(postings2[j])
        j += 1
    return result


#Executing Boolearn Query
def boolean_search(query: str, index):
    term1, operator, term2 = parse_query(query)
    stemmer = PorterStemmer()
    #Normalizing and stemming both query terms
    processed_term1 = preprocess_query_term(
        term1,
        stemmer,
    )
    processed_term2 = preprocess_query_term(
        term2,
        stemmer,
    )
    postings1 = index.get(processed_term1, [])
    postings2 = index.get(processed_term2, [])
    #Performing Boolean Operation
    if operator == "AND":
        result = intersect_postings(
            postings1,
            postings2,
        )
    elif operator == "OR":
        result = union_postings(
            postings1,
            postings2,
        )
    else:
        raise ValueError(
            f"Unsupported Boolean operator: {operator}"
        )
    return (
        result,
        processed_term1,
        operator,
        processed_term2,
        postings1,
        postings2,
    )

#Writing Query Result
def write_results(result, output_path: Path):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with output_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:

        file.write(
            ",".join(str(docid) for docid in result)
        )

        file.write("\n")


#CLI
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Perform two-term Boolean retrieval "
            "over the Cranfield inverted index."
        )
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX,
        help="Path to the Cranfield inverted index.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="File in which matching document IDs are written.",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help='Boolean query such as "aircraft AND pressure".',
    )
    return parser.parse_args(argv)


#Main function
def main(argv=None):
    args = parse_args(argv)
    try:
        if args.query is None:
            query = input(
                "Enter Boolean query "
                "(example: aircraft AND pressure): "
            ).strip()
        else:
            query = args.query.strip()
        if not query:
            raise ValueError("Query cannot be empty.")
        (
            result,
            processed_term1,
            operator,
            processed_term2,
            postings1,
            postings2,
        ) = boolean_search(
            query,
            index,
        )
        write_results(
            result,
            args.output,
        )
        print()
        print("Boolean Retrieval")
        print("-----------------")
        print(f"Original query : {query}")
        print(
            f"Processed query: "
            f"{processed_term1} "
            f"{operator} "
            f"{processed_term2}"
        )
        print()
        print(
            f"Postings for '{processed_term1}': "
            f"{postings1}"
        )
        print(
            f"Postings for '{processed_term2}': "
            f"{postings2}"
        )
        print()
        print(
            f"Number of matching documents: "
            f"{len(result)}"
        )
        print(f"Matching docids: {result}")
        print()
        print(
            f"Vocabulary size: {vocabulary_size}"
        )
        print(
            f"Maximum docid: {max_docid}"
        )
        print()
        print(
            f"Results written to: {args.output}"
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
    ) as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
