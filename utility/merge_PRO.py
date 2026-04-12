import json

def update_answers(main_data, source_data, output_file):
    for main_item, source_item in zip(main_data, source_data):
        answers = main_item.get("answers", [])
        # take only the first 6 answers
        answers = answers[:6]
        if source_item.get("answers"):
            new_string = source_item["answers"][0]
            # append source answer 4 times
            main_item["answers"] = answers + [new_string] * 4

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(main_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    output_file = "q_100_answers_merged.json"

    with open("./simulations_test/run_PRO_r/q_60_answers_original.json", 'r', encoding='utf-8') as f1, \
         open("./simulations_test/run_PRO_r/q_60_answers.json", 'r', encoding='utf-8') as f2:
        main_data = json.load(f1)
        source_data = json.load(f2)

    update_answers(main_data, source_data, output_file)
