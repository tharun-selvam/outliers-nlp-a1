from pathlib import Path
import argparse
import re
import sys

from outliers_porter import PorterStemmer
from outliers_preprocess import tokenize, normalize, stem_tokens


# ---------------------------------------------------------
# FILE PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

GROUP_NAME = "outliers"

DEFAULT_INDEX = BASE_DIR / f"{GROUP_NAME}_cran.index"
DEFAULT_OUTPUT = BASE_DIR / f"{GROUP_NAME}_boolean_results.txt"


# =========================================================
# 1. LOAD THE INVERTED INDEX
# =========================================================

def load_index(index_path: Path):
    """
    Reads the index file and stores it as:

        term -> list of document IDs

    Example:

        aerodynamic -> [1, 10, 11]

    Returns:
        index
        vocabulary_size
        max_docid
    """

    if not index_path.exists():
        raise FileNotFoundError(
            f"Index file not found: {index_path}"
        )

    index = {}

    with index_path.open("r", encoding="utf-8") as file:

        # -------------------------------------------------
        # Read first line:
        #
        # vocabulary_size max_docid
        #
        # Example:
        # 588 1400
        # -------------------------------------------------

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
                "Vocabulary size and maximum document ID "
                "must be integers."
            )

        # -------------------------------------------------
        # Read the actual inverted index
        # -------------------------------------------------

        for line_number, raw_line in enumerate(file, start=2):

            line = raw_line.strip()

            if not line:
                continue

            parts = line.split(maxsplit=1)

            if len(parts) != 2:
                raise ValueError(
                    f"Invalid index entry at line "
                    f"{line_number}: {line!r}"
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
                    f"Invalid postings list at line "
                    f"{line_number}"
                )

            # Verify that the postings list is sorted
            if postings != sorted(postings):
                raise ValueError(
                    f"Postings list for '{term}' is not sorted."
                )

            index[term] = postings

    # -----------------------------------------------------
    # Check vocabulary size
    # -----------------------------------------------------

    if len(index) != vocabulary_size:
        raise ValueError(
            f"Vocabulary size mismatch: header says "
            f"{vocabulary_size}, but {len(index)} terms "
            f"were read."
        )

    return index, vocabulary_size, max_docid


# =========================================================
# 2. PREPROCESS A QUERY TERM
# =========================================================

def preprocess_query_term(term: str, stemmer: PorterStemmer):
    """
    Applies the same preprocessing steps used
    for the Cranfield documents:

        tokenization
             ↓
        normalization
             ↓
        Porter stemming

    Returns the processed term.
    """

    tokens = tokenize(term)

    tokens = normalize(tokens)

    if len(tokens) != 1:
        raise ValueError(
            "Each side of the Boolean query must contain "
            "exactly one valid query term. "
            f"Received: {term!r}"
        )

    tokens = stem_tokens(tokens, stemmer)

    return tokens[0]


# =========================================================
# 3. PARSE BOOLEAN QUERY
# =========================================================

def parse_query(query: str):
    """
    Valid query forms:

        word1 AND word2
        word1 OR word2

    AND and OR are case-insensitive.

    Examples:

        aerodynamic AND experimental
        aircraft OR pressure
    """

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
        raise ValueError(
            "Both query terms must be present."
        )

    return term1, operator, term2


# =========================================================
# 4. BOOLEAN AND
# =========================================================

def intersect_postings(postings1, postings2):
    """
    Computes:

        postings1 AND postings2

    Both postings lists are sorted.

    Uses the standard two-pointer
    postings-list intersection algorithm.

    Time Complexity:

        O(m + n)
    """

    result = []

    i = 0
    j = 0

    while i < len(postings1) and j < len(postings2):

        docid1 = postings1[i]
        docid2 = postings2[j]

        # ---------------------------------------------
        # Both terms occur in this document
        # ---------------------------------------------

        if docid1 == docid2:

            result.append(docid1)

            i += 1
            j += 1

        # ---------------------------------------------
        # First document ID is smaller
        # ---------------------------------------------

        elif docid1 < docid2:

            i += 1

        # ---------------------------------------------
        # Second document ID is smaller
        # ---------------------------------------------

        else:

            j += 1

    return result


# =========================================================
# 5. BOOLEAN OR
# =========================================================

def union_postings(postings1, postings2):
    """
    Computes:

        postings1 OR postings2

    Uses the merge algorithm because both postings
    lists are sorted.

    Duplicate document IDs are included only once.

    Time Complexity:

        O(m + n)
    """

    result = []

    i = 0
    j = 0

    while i < len(postings1) and j < len(postings2):

        docid1 = postings1[i]
        docid2 = postings2[j]

        # ---------------------------------------------
        # Same document exists in both lists
        # ---------------------------------------------

        if docid1 == docid2:

            result.append(docid1)

            i += 1
            j += 1

        # ---------------------------------------------
        # Smaller element from postings1 comes first
        # ---------------------------------------------

        elif docid1 < docid2:

            result.append(docid1)

            i += 1

        # ---------------------------------------------
        # Smaller element from postings2 comes first
        # ---------------------------------------------

        else:

            result.append(docid2)

            j += 1

    # -------------------------------------------------
    # One list may still contain documents
    # -------------------------------------------------

    while i < len(postings1):

        result.append(postings1[i])

        i += 1

    while j < len(postings2):

        result.append(postings2[j])

        j += 1

    return result


# =========================================================
# 6. EXECUTE BOOLEAN QUERY
# =========================================================

def boolean_search(query: str, index):
    """
    Complete Boolean retrieval procedure.

    Steps:

        1. Parse query
        2. Normalize query terms
        3. Stem query terms
        4. Retrieve postings lists
        5. Perform AND / OR
        6. Return matching document IDs
    """

    # -------------------------------------------------
    # Parse:
    #
    # word1 AND/OR word2
    # -------------------------------------------------

    term1, operator, term2 = parse_query(query)

    stemmer = PorterStemmer()

    # -------------------------------------------------
    # Normalize and stem both query terms
    # -------------------------------------------------

    processed_term1 = preprocess_query_term(
        term1,
        stemmer,
    )

    processed_term2 = preprocess_query_term(
        term2,
        stemmer,
    )

    # -------------------------------------------------
    # Dictionary lookup
    #
    # If the term does not exist, return []
    # -------------------------------------------------

    postings1 = index.get(processed_term1, [])
    postings2 = index.get(processed_term2, [])

    # -------------------------------------------------
    # Perform Boolean operation
    # -------------------------------------------------

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

        # This normally cannot happen because
        # parse_query already validates the operator.

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


# =========================================================
# 7. WRITE QUERY RESULT
# =========================================================

def write_results(result, output_path: Path):
    """
    Writes the matching document IDs to the output file.

    Example:

        1,4,7,15,21
    """

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


# =========================================================
# 8. COMMAND-LINE ARGUMENTS
# =========================================================

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


# =========================================================
# 9. MAIN PROGRAM
# =========================================================

def main(argv=None):

    args = parse_args(argv)

    try:

        # -------------------------------------------------
        # Load the inverted index ONCE
        # -------------------------------------------------

        index, vocabulary_size, max_docid = load_index(
            args.index
        )

        print()
        print("=" * 50)
        print("          BOOLEAN RETRIEVAL SYSTEM")
        print("=" * 50)

        print(
            f"Vocabulary size : {vocabulary_size}"
        )

        print(
            f"Maximum docid   : {max_docid}"
        )

        print()

        print("Enter Boolean queries in the format:")
        print("    aircraft AND pressure")
        print("    aircraft OR pressure")

        print()

        print(
            "Type 'exit', 'quit', or 'stop' "
            "to terminate."
        )

        print("=" * 50)
        print()

        # =================================================
        # MODE 1:
        #
        # If --query is supplied from command line,
        # execute that query once and exit.
        # =================================================

        if args.query is not None:

            query = args.query.strip()

            if not query:
                raise ValueError(
                    "Query cannot be empty."
                )

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

            print(
                f"Original query : {query}"
            )

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

            print(
                f"Matching docids: {result}"
            )

            print()

            print(
                f"Results written to: {args.output}"
            )

            return 0

        # =================================================
        # MODE 2:
        #
        # INTERACTIVE MODE
        #
        # Keep accepting queries continuously.
        # =================================================

        while True:

            try:

                query = input(
                    "Enter Boolean query: "
                ).strip()

            except EOFError:

                print()
                print(
                    "End of input detected. "
                    "Exiting..."
                )

                break

            except KeyboardInterrupt:

                print()
                print()
                print(
                    "Ctrl+C detected. Exiting..."
                )

                break

            # -------------------------------------------------
            # EXIT COMMANDS
            # -------------------------------------------------

            if query.lower() in (
                "exit",
                "quit",
                "stop",
            ):

                print()
                print(
                    "Exiting Boolean Retrieval System..."
                )

                break

            # -------------------------------------------------
            # EMPTY QUERY
            # -------------------------------------------------

            if not query:

                print()
                print(
                    "Please enter a Boolean query."
                )
                print()

                continue

            # -------------------------------------------------
            # EXECUTE QUERY
            # -------------------------------------------------

            try:

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

                # ---------------------------------------------
                # Write result to output file
                # ---------------------------------------------

                write_results(
                    result,
                    args.output,
                )

                # ---------------------------------------------
                # Display information
                # ---------------------------------------------

                print()
                print("Boolean Retrieval")
                print("-----------------")

                print(
                    f"Original query : {query}"
                )

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

                print(
                    f"Matching docids: {result}"
                )

                print()

                print(
                    f"Results written to: {args.output}"
                )

                print()

            except ValueError as error:

                # ---------------------------------------------
                # IMPORTANT:
                #
                # An invalid query should NOT terminate
                # the whole program.
                # ---------------------------------------------

                print()
                print(
                    f"ERROR: {error}"
                )

                print(
                    "Please enter another query."
                )

                print()

                continue

        return 0

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


# =========================================================
# PROGRAM ENTRY POINT
# =========================================================

if __name__ == "__main__":
    raise SystemExit(main())

