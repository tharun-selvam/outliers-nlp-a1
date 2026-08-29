from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
GROUP_NAME = "outliers"
DEFAULT_INPUT = BASE_DIR / f"{GROUP_NAME}_processed.all"
DEFAULT_OUTPUT = BASE_DIR / f"{GROUP_NAME}_cran.index"
EXPECTED_DOCUMENT_COUNT = 1400

def read_processed_file(input_path:Path):
    # Inverted index
    index = {}
    # The document currently being processed
    current_docid = None
    # Keep track of document IDs
    seen_docids = set()
    # This tells us whether we have seen ".S"
    expecting_tokens = False
    with input_path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            # Remove newline and surrounding whitespace
            line = raw_line.strip()
            if not line:
                continue
            # Case 1: DocID
            # Example:
            # .I 25
            if line.startswith(".I"):
                parts = line.split()
                if len(parts) != 2 or parts[0] != ".I":
                    raise ValueError(f"Invalid document ID at line {line_number}: {line!r}")
                try:
                    docid = int(parts[1])
                except ValueError as error:
                    raise ValueError(f"Invalid document ID at line {line_number}: {line!r}") from error
                if docid <= 0:
                    raise ValueError(f"Document ID must be positive at line {line_number}: {docid}")
                if docid in seen_docids:
                    raise ValueError(f"Duplicate document ID {docid} at line {line_number}")
                seen_docids.add(docid)
                current_docid = docid
                expecting_tokens = False
                continue
            # Token list
            elif line == ".S":
                if current_docid is None:
                    raise ValueError(f".S found before a document ID at line {line_number}")
                # We now expect the next non-empty line to contain the terms
                expecting_tokens = True
                continue
            elif expecting_tokens:
                if current_docid is None:
                    raise ValueError(f"Token data found without a document at line {line_number}")
                tokens = line.split()
                # Add the current document ID to every token.
                for token in tokens:
                    # If this is the first time we have seen this token, create an empty set
                    if token not in index:
                        index[token] = set()
                    # Add the current document ID.
                    index[token].add(current_docid)
                expecting_tokens = False
                continue
            else:
                raise ValueError(f"Unexpected content at line {line_number}: {line!r}")
    # Final validation
    if expecting_tokens:
        raise ValueError("Input file ended after .S without a token line")
    if not seen_docids:
        raise ValueError("Input file contains no documents")
    if len(seen_docids) != EXPECTED_DOCUMENT_COUNT:
        raise ValueError(f"Expected {EXPECTED_DOCUMENT_COUNT} documents, but found {len(seen_docids)}")
    expected_ids = set(range(1, EXPECTED_DOCUMENT_COUNT + 1))
    if seen_docids != expected_ids:
        raise ValueError("Document IDs are not exactly 1 through 1400")
    # maximum document ID
    max_docid = max(seen_docids)
    return index, max_docid
def write_index_file(index, max_docid, output_path: Path):
    vocabulary = sorted(index.keys())
    with output_path.open("w", encoding="utf-8") as file:
        # vocabulary size (number of tokens) and the maximum docid
        file.write(f"{len(vocabulary)} {max_docid}\n")
        # Each token and its postings list
        for token in vocabulary:
            postings = sorted(index[token])
            postings_string = ",".join(str(docid) for docid in postings)
            file.write(f"{token} {postings_string}\n")
def create_index(input_filename:Path, output_filename:Path):
    if not input_filename.exists():
        raise FileNotFoundError(f"Input file not found: {input_filename}")
    if not input_filename.is_file():
        raise ValueError(f"Input path is not a file: {input_filename}")
    output_filename.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    index, max_docid = read_processed_file(input_filename)
    write_index_file(index, max_docid, output_filename)
def main()->int:
    try:
        create_index(DEFAULT_INPUT,DEFAULT_OUTPUT)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Index created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
