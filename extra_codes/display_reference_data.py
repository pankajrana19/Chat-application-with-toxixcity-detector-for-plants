import csv
import textwrap

# File path
REFERENCE_CSV = "reference_data.csv"

def load_reference_data():
    """Load the first 10 entries from reference_data.csv."""
    with open(REFERENCE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader][:10]

def display_reference_data():
    """Display the first 10 entries with full content in a readable format."""
    data = load_reference_data()
    print("\nFirst 10 Entries of reference_data.csv:")
    print("=" * 150)

    for row in data:
        print(f"Chunk Index: {row['Chunk Index']}")
        print("-" * 50)
        print("Chunk Text:")
        # Wrap long text to 100 characters per line for readability
        wrapped_text = textwrap.fill(row['Chunk Text'], width=100)
        print(wrapped_text)
        print("-" * 50)
        print(f"Summary: {row['Summary']}")
        print(f"Keywords: {row['Keywords']}")
        print("=" * 150)

if __name__ == "__main__":
    try:
        display_reference_data()
    except FileNotFoundError:
        print(f"Error: {REFERENCE_CSV} not found in the current directory.")
    except Exception as e:
        print(f"An error occurred: {e}")