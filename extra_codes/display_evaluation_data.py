import csv
import textwrap

# File path
EVALUATION_CSV = "evaluation_dataset.csv"

def load_evaluation_data():
    """Load the first 10 entries from evaluation_dataset.csv."""
    with open(EVALUATION_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader][:10]

def display_evaluation_data():
    """Display the first 10 entries with full content in a readable format."""
    data = load_evaluation_data()
    print("\nFirst 10 Entries of evaluation_dataset.csv:")
    print("=" * 150)

    for row in data:
        print(f"Chunk Index: {row['Chunk Index']}")
        print("-" * 50)
        print("Chunk Text:")
        # Wrap long text to 100 characters per line for readability
        wrapped_text = textwrap.fill(row['Chunk Text'], width=100)
        print(wrapped_text)
        print("-" * 50)
        print(f"RAKE Keywords: {row['RAKE Keywords']}")
        print(f"SpaCy Keywords: {row['SpaCy Keywords']}")
        print(f"LSA Summary: {row['LSA Summary']}")
        print(f"LexRank Summary: {row['LexRank Summary']}")
        print(f"Transformers Summary: {row['Transformer Summary']}")
        print("=" * 150)

if __name__ == "__main__":
    try:
        display_evaluation_data()
    except FileNotFoundError:
        print(f"Error: {EVALUATION_CSV} not found in the current directory.")
    except Exception as e:
        print(f"An error occurred: {e}")