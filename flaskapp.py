from flask import Flask, request, jsonify
from utils import HRSearch, JobData, InterviewQuestionGenerator, CandidateData

app = Flask(__name__)

HRSearchObject = HRSearch()
JobDataObject = JobData("data/jd_data.json")
CandidateDataObject = CandidateData("data/candidate_record_list.json")
interview_generator = InterviewQuestionGenerator()

@app.route("/")
def read_root():
    return {"message": "Welcome to TalentHub! 🚀"}

@app.route("/search_candidates/", methods=['GET'])
def search_candidates():
    keyword = request.args.get('keyword')
    if not keyword:
        return jsonify({"detail": "Keyword parameter missing"}), 400
    all_candidates_data = HRSearchObject.full_text_search(keyword)
    if not all_candidates_data:
        return jsonify({"detail": "No candidates found"}), 404
    return jsonify(all_candidates_data)

@app.route("/rank_candidates/", methods=['GET'])
def rank_candidates():
    job_position = request.args.get('job_position')
    if not job_position:
        return jsonify({"detail": "Job position parameter missing"}), 400
    job_positions = JobDataObject.get_positions()
    if job_position not in job_positions:
        return jsonify({"detail": "Job position not found"}), 404

    job_position_record = JobDataObject.get_record_by_position(job_position)
    all_candidates_data = HRSearchObject.search_candidates_by_job_description(
        jd_id=job_position_record["JD_ID"]
    )

    if not all_candidates_data:
        return jsonify({"detail": "No candidates found"}), 404
    
    ranked_candidates_info = [
        {
            "Name": candidate_data["candidate_name"],
            "SemanticScore": round(candidate_data['SemanticScore']*100, 2),
            "EducationGrade": candidate_data["EducationGrade"],
            "ExperienceGrade": candidate_data["ExperienceGrade"],
            "OverallScore": candidate_data["OverallScore"],
            "Profile Summary": candidate_data["candidate_summary"],
            "Candidate id": candidate_data["Candidate_ID"],
        }
        for candidate_data in all_candidates_data
    ]
    return jsonify(ranked_candidates_info)



@app.route("/generate_assessment/", methods=['GET'])
def generate_assessment():
    selected_profile = request.args.get('selected_profile')
    selected_candidate = request.args.get('selected_candidate')
    
    if not selected_profile or not selected_candidate:
        return jsonify({"detail": "Selected profile or candidate missing"}), 400

    candidate_name_dict = CandidateDataObject.get_candidate_names()
    key_for_value = get_key(candidate_name_dict, selected_candidate)

    CandidateRecord = CandidateDataObject.get_record_by_id(selected_candidate)

    JDRecord = JobDataObject.get_record_by_position(position=selected_profile)
    JD = JDRecord["JD_Content"]
    CV = CandidateRecord["MD_Content"]

    InterviewQuestionsObject = interview_generator.generate_interview_questions(JD, CV)
    if not InterviewQuestionsObject:
        return jsonify({"detail": "Failed to generate assessment questions"}), 500

    multiple_choice_questions = InterviewQuestionsObject[0].multiple_choice_questions
    descriptive_questions = InterviewQuestionsObject[0].descriptive_questions

    assessment_questions = []
    assessment_questions.append({
        "key_for_value": key_for_value.split('(')[1].split('.')[0],
    })
    for i, DescriptiveQuestionObject in enumerate(descriptive_questions, start=1):
        assessment_questions.append({
            "question_type": "Descriptive",
            "question_number": i,
            "question": DescriptiveQuestionObject.question
        })
    for i, MultipleChoiceObject in enumerate(multiple_choice_questions, start=1):
        assessment_questions.append({
            "question_type": "Multiple Choice",
            "question_number": i,
            "question": MultipleChoiceObject.question,
            "choices": MultipleChoiceObject.choices
        })

    return jsonify(assessment_questions)


def get_key(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None

if __name__ == "__main__":
    app.run()
