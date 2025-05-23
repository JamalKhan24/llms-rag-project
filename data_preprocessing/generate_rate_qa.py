import json

# Load the JSON file
with open("data_preprocessing/output/nust_rate_list.json", "r", encoding="utf-8") as f:
    rate_data = json.load(f)

qa_pairs = []

# === Savings Accounts ===
for account_name, entries in rate_data.get("Savings Accounts", {}).items():
    full_name = f"{account_name} Savings Account"
    for field in ["Profit Payment", "Profit Rate"]:
        question = f"What is the {field.lower()} for {full_name}?"
        answer_parts = []
        for item in entries:
            value = item.get(field)
            if value:
                answer_parts.append(str(value))
        if answer_parts:
            answer = f"It is: {', '.join(answer_parts)}"
            qa_pairs.append({"question": question, "answer": answer})

# === Term Deposits ===
for deposit_name, entries in rate_data.get("Term Deposits", {}).items():
    full_name = f"{deposit_name} Term Deposit"
    for field in ["Tenor", "Payout", "Profit Rate"]:
        question = f"What is the {field.lower()} for {full_name}?"
        answer_parts = []
        for item in entries:
            value = item.get(field)
            if isinstance(value, dict):
                # Handle FCY profit rate
                currency_rates = ', '.join([f"{k}: {v}" for k, v in value.items()])
                answer_parts.append(f"{currency_rates}")
            elif value:
                answer_parts.append(str(value))
        if answer_parts:
            answer = f"It is: {', '.join(answer_parts)}"
            qa_pairs.append({"question": question, "answer": answer})

# Save QA pairs to JSON
with open("data_preprocessing/output/nust_rate_qa.json", "w", encoding="utf-8") as f:
    json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

print("QA pairs generated and saved to output/nust_rate_qa.json")
