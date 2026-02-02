import os
import logging
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

logger = logging.getLogger(__name__)

# STRUCTURED OUTPUT FROM AGENTS

class CandidateEvaluation(BaseModel):
    candidate_name: str = Field(description="Full name")
    seniority_level: str = Field(description="Junior / Mid / Senior")
    seniority_alignment: str = Field(description="Alignment with JD Seniority")
    extracted_skills: List[str] = Field(description="Skills extracted from resume")
    matching_skills: List[str] = Field(description="Skills matched with JD")
    missing_skills: List[str] = Field(description="Gap analysis - skills missing")
    ats_score: int = Field(description="Score 0-100")
    red_flags: List[str] = Field(description="Career gaps, short jobs, irrelevant exp etc.")
    final_reasoning: str = Field(description="Hiring decision summary")



# MAIN CLASS

class HiringAgency:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            logger.critical("GOOGLE_API_KEY missing!")
        else:
            logger.info("Gemini API key loaded!")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=api_key
        )

        self.parser = JsonOutputParser(pydantic_object=CandidateEvaluation)

    
    # LOAD RESUME FILE
 
    def ingest_document(self, file_path):
        try:
            if file_path.endswith(".pdf"):
                pages = PyPDFLoader(file_path).load()
                text = " ".join([p.page_content for p in pages])

            elif file_path.endswith(".docx"):
                pages = Docx2txtLoader(file_path).load()
                text = " ".join([p.page_content for p in pages])

            else:
                return None

            clean_text = text.strip()
            return clean_text if clean_text else None

        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return None


    # HR MULTI-AGENT CHAIN

    def recruiter_agent(self, resume_text, jd_text):
        """
        5 AGENTS INSIDE ONE PROMPT:
        1. Skill Extraction Agent
        2. Seniority Agent
        3. Gap Analysis Agent
        4. Red Flags Agent
        5. ATS Scoring Agent
        """

        prompt = PromptTemplate(
            template="""
You are an HR Multi-Agent Recruiter AI.

Analyze the following RESUME against the JOB DESCRIPTION.

Perform these AGENTS internally:


 SKILL EXTRACTION AGENT

• Extract all technical + non-technical skills from resume.


 SENIORITY AGENT

• Identify candidate's seniority (Junior / Mid / Senior)
• Compare with JD seniority requirement.


 GAP ANALYSIS AGENT

• Find skills missing compared to JD.


 RED FLAGS AGENT

Detect:
• Long career gaps
• Too many short job cycles
• Irrelevant experience
• No progression
• Weak project depth


 ATS SCORING AGENT

• Score 0–100 based on skill match + seniority alignment.


Return FINAL structured JSON.


JOB DESCRIPTION:
{jd}

RESUME:
{resume}

{format_instructions}
""",
            input_variables=["resume", "jd"],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            }
        )

        chain = prompt | self.llm | self.parser

        try:
            result = chain.invoke({
                "resume": resume_text,
                "jd": jd_text
            })
            return result

        except Exception as e:
            logger.error(f"Recruiter Agent Error: {e}")
            return None

  
    # ENTRY POINT

    def process_application(self, file_path, jd_text):
        resume_text = self.ingest_document(file_path)
        if not resume_text:
            return None

        return self.recruiter_agent(resume_text, jd_text)
