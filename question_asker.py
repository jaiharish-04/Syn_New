import random
import json
import os
from collections import defaultdict, deque

class QuestionAsker:
    def __init__(self, selector, log_path="logs.json", question_log_path="employee_with_questions_log.json"):
        self.selector = selector
        self.cache = {}
        self.log_path = log_path
        self.log_file = question_log_path
        self.recent_session_fields = defaultdict(lambda: deque(maxlen=3))  # short-term session memory

    def _load_previous_questions(self, user_id):
        if not os.path.exists(self.log_file):
            return set()

        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read {self.log_file}: {e}")
            return set()

        asked_pairs = set()
        for entry in data:
            if str(entry.get("Employee ID")) == str(user_id):
                for q in entry.get("questions_asked", []):
                    field = q.get("field")
                    question = q.get("question")
                    if field and question:
                        asked_pairs.add((field, question))

        return asked_pairs

    def ask_questions(self, user_id, record, num_questions=3):
        populated_fields = [
            f for f in record
            if f not in ["Employee ID", "Employee Name"]
            and isinstance(record[f], str)
            and record[f].strip() != ""
        ]

        if not populated_fields:
            return []

        if not self.cache:
            try:
                self.cache = self.selector._load_template_bank(
                    "/Users/jaiharishsatheshkumar/synthetic_data_generator/templates_bank.json"
                )
            except Exception as e:
                print(f"Warning: Could not load template bank: {e}")
                return []

        valid_fields = [f for f in populated_fields if f in self.cache and self.cache[f]]
        if not valid_fields:
            return []

        previous_pairs = self._load_previous_questions(user_id)
        recent_fields = self.recent_session_fields[user_id]
        candidate_fields = [f for f in valid_fields if f not in recent_fields]

        if not candidate_fields:
            self.recent_session_fields[user_id].clear()
            candidate_fields = valid_fields

        questions = []
        used_fields = set()

        random.shuffle(candidate_fields)
        for field in candidate_fields:
            templates = self.cache.get(field, [])
            random.shuffle(templates)
            for template in templates:
                question = template.replace("{value}", str(record.get(field, "")))
                if (field, question) not in previous_pairs:
                    questions.append((field, template, question))
                    used_fields.add(field)
                    break  # move to next field
            if len(questions) >= num_questions:
                break

        for field in used_fields:
            self.recent_session_fields[user_id].append(field)

        return questions

    def record_user_answer(self, user_id, field, template, user_answer, correct_answers):
        if isinstance(correct_answers, str):
            correct_answers = [correct_answers]

        correct_answers = [ans.lower().strip() for ans in correct_answers]
        success = int(user_answer.lower().strip() in correct_answers)
        reward = 1 if success else -1

        self.selector.log_interaction(user_id, field, template, user_answer, correct_answers)
        self.selector.rl_selector.update_q(user_id, field, template, reward)
