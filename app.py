from flask import Flask, render_template, request
import json
import os
from ml_selector import FieldTemplateSelector
from question_asker import QuestionAsker

app = Flask(__name__)

# Load enriched employee data
with open("enriched_employee_dataset_50000.json") as f:
    user_data = json.load(f)

# Load logs
try:
    with open("logs.json") as f:
        logs = json.load(f)
except FileNotFoundError:
    logs = []

# Initialize selector and question engine
selector = FieldTemplateSelector()
asker = QuestionAsker(selector)

# Train model from logs if available
if logs:
    for log in logs:
        reward = 1 if log.get('success', False) else -1
        selector.rl_selector.update_q(log['user_id'], log['field'], log['template'], reward)
        selector.logs.append(log)
    selector.train_supervised()


def update_question_log(employee_record, questions):
    """
    Always appends a new entry for the employee with their current questions,
    without modifying previous entries.
    """
    QUESTION_LOG_PATH = "employee_with_questions_log.json"

    if os.path.exists(QUESTION_LOG_PATH):
        with open(QUESTION_LOG_PATH) as f:
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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/verify-id', methods=['POST'])
def verify_id():
    input_id = request.form.get('employee_id', '').strip()
    record = next((r for r in user_data if str(r["Employee ID"]) == input_id), None)

    if record:
        user_id = str(record["Employee ID"])
        user_name = record.get("Employee Name", "User")
        questions = asker.ask_questions(user_id, record, num_questions=3)

        # Save questions to separate log file
        update_question_log(record, questions)

        return render_template('questions.html', user_id=user_id, user_name=user_name, questions=questions)
    else:
        return render_template("result.html",
                               status="❌ Not Found",
                               message="Employee ID not found. Please go back and try again.",
                               success=False)


@app.route('/submit-answers', methods=['POST'])
def submit_answers():
    user_id = request.form.get('user_id')
    fields = request.form.getlist('fields')
    templates = request.form.getlist('templates')
    answers = request.form.getlist('answers')

    record = next((r for r in user_data if str(r["Employee ID"]) == user_id), None)
    if not record:
        return render_template("result.html",
                               status="❌ Record Not Found",
                               message="We could not locate your record. Please try again.",
                               success=False,
                               results=[])

    results = []
    all_correct = True

    for field, template, answer in zip(fields, templates, answers):
        correct_value = record.get(field, "")
        correct_answers = [correct_value] if not isinstance(correct_value, list) else correct_value
        asker.record_user_answer(user_id, field, template, answer, correct_answers)

        is_correct = answer.lower() in [ans.lower() for ans in correct_answers]
        if not is_correct:
            all_correct = False

        results.append({
            "question": template.replace("{value}", str(correct_value)),
            "your_answer": answer,
            "correct_answer": correct_answers,
            "is_correct": is_correct
        })

    return render_template("result.html",
                           status="✅ Success" if all_correct else "❌ Failure",
                           message="You passed all checks!" if all_correct else "Some answers were incorrect.",
                           success=all_correct,
                           results=results)


if __name__ == '__main__':
    app.run(debug=True)
