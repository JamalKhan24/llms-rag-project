import json

# Load account-based QA data
with open("data_preprocessing/output/nust_accounts_qa.json", "r", encoding="utf-8") as f:
    account_data = json.load(f)

# Load rate-based QA data
with open("data_preprocessing/output/nust_rate_qa.json", "r", encoding="utf-8") as f:
    rate_qa_data = json.load(f)

# Prepare merged QA list
merged_qa = rate_qa_data.copy()

# Append QAs from account data
for key, section in account_data.items():
    if not section:
        continue  # skip if None

    title = section.get("title")
    if not title:
        continue  # skip if title is missing/null

    title = title.strip()

    for pair in section.get("qa_pairs", []):
        question = pair.get("question", "").strip()
        answer = pair.get("answer", "").strip()
        if question and answer:
            merged_qa.append({
                "question": f"{question} for {title}",
                "answer": answer
            })

# Save combined QA to a new file
with open("data_preprocessing/output/combined_qa.json", "w", encoding="utf-8") as f:
    json.dump(merged_qa, f, indent=2, ensure_ascii=False)

print("Combined QA saved to output/combined_qa.json")
