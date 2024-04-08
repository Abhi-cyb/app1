# Importing necessary libraries 
import streamlit as st
import os
from typing import List
import tiktoken
import json 
import dotenv

dotenv.load_dotenv()
# Importing Azure-related libraries for authentication and search functionality
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# Importing langchain libraries for chat prompts and Pydantic model definitions
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

# Importing langchain libraries for handling human messages, OpenAI chat, and output parsing
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers.openai_tools import PydanticToolsParser


class HRSearch:
    def __init__(self):
        # Load secrets
        self.api_key = os.getenv("AI_SEARCH_API_KEY")
        self.endpoint = os.getenv("AI_SEARCH_ENDPOINT")

        # Initialize search client
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name="hr-index",
            credential=AzureKeyCredential(self.api_key),
        )

    def full_text_search(self, search_text="*"):
        # Run the search query
        results = self.search_client.search(
            query_type='simple',
            search_text=search_text,
            select="Candidate_ID, candidate_name, candidate_summary",
            search_fields=["CV"],
            include_total_count=True,
            filter="JD_ID eq 'f4885285-acc3-43d0-837a-9adf436ec777' "
        )
        # Return the search results
        results = list(results)
        return results

    def search_candidates_by_job_description(self, jd_id):

        # Define the filter criteria based on the passed JD_ID
        filter_criteria = f"JD_ID eq '{jd_id}'"

        # Run the search query
        results = self.search_client.search(
            query_type="simple",
            search_text="*",
            select="Candidate_ID, JD_ID, candidate_name, candidate_summary, SemanticScore, EducationGrade, ExperienceGrade, OverallScore",
            search_fields=["CV"],
            include_total_count=True,
            filter=filter_criteria,
            order_by="OverallScore desc",
        )

        # Return the search results
        return results

    # def get_jd_cv(self, jd_id, candidate_id):

    #     # Define the filter criteria based on the passed JD_ID
    #     filter_criteria = f"JD_ID eq '{jd_id}' AND Candidate_ID eq '{candidate_id}'"

    #     # Run the search query
    #     results = self.search_client.search(
    #         query_type="simple",
    #         search_text="*",
    #         select="Candidate_ID, JD_ID, candidate_name, candidate_summary, SemanticScore, EducationGrade, ExperienceGrade, OverallScore",
    #         search_fields=["CV"],
    #         include_total_count=True,
    #         filter=filter_criteria,
    #         order_by="OverallScore desc",
    #     )

    #     # Return the search results
    #     return results

####=======================================
class CandidateData:
    def __init__(self, file_path):
        """
        Initialize the CandidateData class with JSON data loaded from the specified file path.

        Parameters:
        - file_path (str): The path to the JSON file containing candidate data.

        Example:
        ```python
        # Initialize the CandidateData class with the JSON file path
        candidate_data = CandidateData("data/candidate_data.json")

        # Get all candidate IDs
        candidate_ids = candidate_data.get_candidate_ids()
        print("All Candidate IDs:", candidate_ids)

        # Example usage: Get the record for a specific candidate
        candidate_id = "5d58705c-38ef-47a1-bad3-d30f940319fc"
        record = candidate_data.get_record_by_id(candidate_id)
        if record:
            print("Record for Candidate ID", candidate_id, ":", record)
        else:
            print("No record found for Candidate ID", candidate_id)
        ```
        """
        self.candidate_data = self.load_data(file_path)

    def load_data(self, file_path):
        """
        Load JSON data from the specified file path.
        """
        with open(file_path, "r") as file:
            return json.load(file)

    def get_candidate_names(self):
        """
        Get a list of all candidate IDs.
        """
        candidate_ids = {f'{candidate["candidate_name"]} ({candidate["File_Name"]})':candidate["Candidate_ID"]  for candidate in self.candidate_data}

        return candidate_ids

    def get_record_by_id(self, candidate_id):
        """
        Get the record corresponding to the given candidate ID.
        """
        for candidate in self.candidate_data:
            if candidate["Candidate_ID"] == candidate_id:
                return candidate
        return None
    

class JobData:
    def __init__(self, file_path):
        """
        Initialize the JobData class with JSON data loaded from the specified file path.

        Parameters:
        - file_path (str): The path to the JSON file containing job data.

        Example:
        ```python
        # Initialize the JobData class with the JSON file path
        job_data = JobData("data/jd_data.json")

        # Get all job positions
        positions = job_data.get_positions()
        print("All Job Positions:", positions)

        # Example usage: Get the record for a specific position
        position = "Senior Officer Sales (Retail)"
        record = job_data.get_record_by_position(position)
        if record:
            print("Record for", position, ":", record)
        else:
            print("No record found for", position)
        ```
        """
        self.jd_data = self.load_data(file_path)

    def load_data(self, file_path):
        """
        Load JSON data from the specified file path.
        """
        with open(file_path, "r") as file:
            return json.load(file)

    def get_positions(self):
        """
        Get a list of all job positions.
        """
        positions = [job["Position"] for job in self.jd_data["List"]]
        return positions

    def get_record_by_position(self, position):
        """
        Get the record corresponding to the given job position.
        """
        for job in self.jd_data["List"]:
            if job["Position"] == position:
                return job
        return None


# -============================


# Set environment variables
os.environ['AZURE_OPENAI_ENDPOINT'] = os.getenv("AZURE_OPENAI_ENDPOINT")
os.environ['AZURE_OPENAI_API_KEY'] = os.getenv("AZURE_OPENAI_API_KEY")



class MultipleChoiceQuestion(BaseModel):
    """
    Represents a multiple-choice question in an interview.
    """
    question: str = Field(..., description="MCQ Question for Candidate")
    choices: List[str] = Field(..., min_items=3, description="List of choices for the question.")

class DescriptiveQuestion(BaseModel):
    """
    Represents an open-ended descriptive question in an interview.
    """
    question: str = Field(..., description="Descriptive question for Candidate")
    # answer: str = Field(..., description="Answer of that question")

class InterviewQuestions(BaseModel):
    """
    Represents a set of interview questions.
    """
    multiple_choice_questions: List[MultipleChoiceQuestion] = Field(..., description="List of multiple-choice questions.")
    descriptive_questions: List[DescriptiveQuestion] = Field(..., description="List of open-ended descriptive questions.")



SystemPrompt2 = """Create a list of 15 interview questions for candidate, consisting of:
- 5 multiple-choice questions to evaluate job-specific skills, problem-solving, decision-making, and role-specific knowledge.
- 10 open-ended descriptive questions to assess communication, critical thinking, past experiences, cultural fit, and alignment with company values.

Multiple-choice questions should cover:
1. Domain-specific knowledge
2. Role-specific scenarios
3. Situational judgement
4. Professional competencies

Descriptive questions should be open-ended, asking candidates to:
1. Describe their relevant skills and experiences
2. Provide examples from their past
3. Analyze situations and think critically
4. Communicate their thoughts effectively
5. Demonstrate cultural fit and value alignment

Ensure the questions cover a range of topics relevant to the job and accurately assess the candidate's suitability and qualifications."""

class InterviewQuestionGenerator:
    def __init__(self):
        self.human_template = "@Job Description\n{JD}\n\n@Candidate Resume\n{CV}"
        self.SystemPrompt   = SystemPrompt2
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def trim_to_max(self, text, max_tokens=2750):
        encoded_text = self.encoder.encode(text)
        trimmed_encoded_text = encoded_text[:max_tokens]
        trimmed_text = self.encoder.decode(trimmed_encoded_text)
        return trimmed_text

    def generate_interview_questions(self, JD, CV):
        model = AzureChatOpenAI(
            openai_api_version="2024-02-15-preview", azure_deployment="hrgpt", temperature=0.1
        )
        llm_with_tools = model.bind_tools([InterviewQuestions], tool_choice="InterviewQuestions")
        tool_chain = ChatPromptTemplate.from_messages([("system", self.SystemPrompt), ("human", self.human_template)]) | llm_with_tools | PydanticToolsParser(tools=[InterviewQuestions])

        output = tool_chain.invoke({"JD": JD, "CV": self.trim_to_max(CV, 2700)})
        return output





# # Example usage
# if __name__ == "__main__":
#     hr_search = HRSearch()
#     results = hr_search.full_text_search(jd_id="f4885285-acc3-43d0-837a-9adf436ec777")
#     # Process or display results as needed
