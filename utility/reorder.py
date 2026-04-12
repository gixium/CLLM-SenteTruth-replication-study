import json

# use to move first 4 string to the end
def swap_answers(input_file, output_file):
    # Load the JSON file
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Process each entry
    for item in data:
        answers = item.get("answers", [])
        if len(answers) == 10:  # only process if exactly 10 answers
            # Move first 4 to the end
            item["answers"] = answers[4:] + answers[:4]

    # Save to new file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    input_path = "input.json"   # change to your source file
    output_path = "output.json" # new file
    swap_answers(input_path, output_path)
