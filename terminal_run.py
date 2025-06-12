import json
import os
from question_asker import QuestionAsker
from ml_selector import FieldTemplateSelector

QUESTION_LOG_PATH = "employee_with_questions_log.json"

def get_employee_input():
    print("👋 Enter employee details (fill at least 6 of the 9 optional fields):")

    record = {}
    record["Employee Name"] = input("Employee Name: ").strip()
    record["Employee ID"] = input("Employee ID: ").strip()

    fields = [
        "Phone Number", "Project Name", "Designation",
        "Date of Joining", "Date of Birth", "Email",
        "Manager Name", "Laptop ID", "Location"
    ]

    for field in fields:
        val = input(f"{field} (optional): ").strip()
        record[field] = val if val else ""

    return record

def update_question_log(employee_record, questions):
    """
    Append new field-question pairs to employee_with_questions_log.json for the current session.
    """
    if os.path.exists(QUESTION_LOG_PATH):
        with open(QUESTION_LOG_PATH, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    enriched_record = dict(employee_record)
    enriched_record["questions_asked"] = [
        {
            "field": field,
            "question": question
        } for field, _, question in questions
    ]

    existing_data.append(enriched_record)

    with open(QUESTION_LOG_PATH, "w") as f:
        json.dump(existing_data, f, indent=2)

def run_terminal_quiz():
    # Step 1: Get input
    employee = get_employee_input()
    user_id = str(employee["Employee ID"])
    user_name = employee["Employee Name"]

    # Step 2: Use existing system
    selector = FieldTemplateSelector()
    asker = QuestionAsker(selector)

    # Step 3: Ask questions only on filled fields
    questions = asker.ask_questions(user_id, employee, num_questions=3)

    if not questions:
        print("\n❌ Not enough data to generate questions.")
        return

    print(f"\n👋 Hi {user_name}! Please answer the following questions:\n")

    for i, (field, template, question_text) in enumerate(questions, 1):
        print(f"Q{i}: {question_text}")
        user_answer = input("Your Answer: ").strip()

        correct_value = employee.get(field, "")
        correct_answers = [correct_value] if not isinstance(correct_value, list) else correct_value
        asker.record_user_answer(user_id, field, template, user_answer, correct_answers)

    # Step 4: Update employee_with_questions_log.json
    update_question_log(employee, questions)

if __name__ == "__main__":
    run_terminal_quiz()
