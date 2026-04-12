import json, os
import asyncio
from googletrans import Translator

# Instantiate the translator
translator = Translator()

# Async recursive translator
async def async_translate_item(item):
    if isinstance(item, str):
        try:
            result = await translator.translate(item, src='zh-cn', dest='en')
            return result.text
        except Exception as e:
            print(f"Translation error: {e}")
            return item  # fallback: return original
    elif isinstance(item, list):
        return [await async_translate_item(i) for i in item]
    elif isinstance(item, dict):
        return {k: await async_translate_item(v) for k, v in item.items()}
    else:
        return item  # int, bool, etc.

# Main translation function
def translate_q_to_translate_file():
    base_dir = os.path.dirname(__file__)
    input_file = os.path.join(base_dir, "q1.json")
    output_file = os.path.join(base_dir, "q_1_en.json")

    # Load the JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Run translation
    translated_data = asyncio.run(async_translate_item(data))

    # Save the translated JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Translated file saved to: {output_file}")

# Execute
translate_q_to_translate_file()
