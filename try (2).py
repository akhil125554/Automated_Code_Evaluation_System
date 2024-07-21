from fastapi import FastAPI, File, UploadFile, Request, Form, Depends
from fastapi.responses import HTMLResponse
from pdfminer.high_level import extract_text
import io
import uvicorn
import requests

from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers.json import SimpleJsonOutputParser
import pandas as pd
import numpy as np
import mysql.connector
from sqlalchemy import create_engine

# Initialize the FastAPI app
app = FastAPI()

def read_pdf(file_stream):
    file_stream.seek(0)
    text = extract_text(file_stream)
    return text

eval_df = None
student_id = None

@app.get("/")
async def main():
    global eval_df
    global student_id
    content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload PDF</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                background-color: #fff;
                padding: 20px 40px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                text-align: center;
            }
            h1 {
                color: #333;
            }
            input[type="file"] {
                display: none;
            }
            label {
                display: inline-block;
                background-color: #007BFF;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            label:hover {
                background-color: #0056b3;
            }
            input[type="submit"] {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                transition: background-color 0.3s;
                margin-top: 20px;
            }
            input[type="submit"]:hover {
                background-color: #218838;
            }
            .file-name {
                margin-top: 10px;
                font-style: italic;
                color: #555;
            }
            input[type="text"] {
                margin-bottom: 20px;
                padding: 10px;
                width: calc(100% - 22px);
                border-radius: 5px;
                border: 1px solid #ccc;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Upload PDF</h1>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <input type="text" name="student_id" placeholder="Enter Student ID" required/>
                <input type="file" name="file" id="file" accept=".pdf" onchange="showFileName()"/>
                <label for="file">Choose a PDF file</label>
                <p class="file-name" id="file-name"></p>
                <input type="submit" value="Upload PDF"/>
            </form>
        </div>
        <script>
            function showFileName() {
                var fileInput = document.getElementById('file');
                var fileName = fileInput.files[0].name;
                document.getElementById('file-name').textContent = fileName;
            }
        </script>
    </body>
    </html>
    
    """
    return HTMLResponse(content)

@app.post("/upload")
async def upload_pdf(student_id: str = Form(...), file: UploadFile = File(...)):
    global eval_df
    
    # Store the student_id in a global variable
    student_id = student_id
    # Read the PDF file
    contents = await file.read()
    file_stream = io.BytesIO(contents)
        
    # Extract text from the PDF
    text = read_pdf(file_stream)
    
    llm = Ollama(model="codellama", temperature=0.7)

    code=text

    rubric_descriptions="""
    Rubric is in the format:
    Parameter name
    -low: condition for low level
    -medium: condition for medium level
    -high: condition for high level
    -expert: condition for expert level

    Here are the parameters
    Problem Solving Ability:
    - Low: Struggles to understand and solve the core problem.
    - Medium: Demonstrates basic problem-solving skills with some limitations.
    - High: Effectively approaches problems, providing clear and logical solutions.
    - Expert: Exceptional problem-solving skills, efficiently handles complex scenarios.

    Efficiency of Solutions:
    - Low: Code times out or is inefficient, failing to complete within time/space limits on basic cases.
    - Medium: Code completes within time/space limits for simple cases but not for more complex ones.
    - High: Code is efficient, completing within time/space limits for the majority of cases, including complex ones.
    - Expert: Code is optimized for efficiency, consistently performing within time/space limits in all cases, including stress tests.

    Adaptability:
    - Low: Designs rigid algorithms for specific cases.
    - Medium: Designs algorithms that can be adapted with some effort.
    - High: Designs flexible algorithms suitable for various scenarios.
    - Expert: Creates highly adaptable algorithms for diverse use cases.

    Pattern Recognition:
    - Low: Struggles to identify recurring patterns in problems.
    - Medium: Recognizes common patterns and applies them.
    - High: Quickly identifies patterns and efficiently applies appropriate solutions.
    - Expert: Exceptional ability to identify and leverage patterns for elegant solutions.

    Parallelism and Concurrency:
    - Low: Limited consideration for parallel processing or concurrency.
    - Medium: Designs algorithms with some awareness of parallelism.
    - High: Utilizes parallelism or concurrency where applicable.
    - Expert: Expertise in designing algorithms for parallel and concurrent execution.

    Readability and Maintainability:
    - Low: Code lacks structure and comments, making it unreadable by automated documentation tools.
    - Medium: Code has some structure and comments detectable by automated tools but lacks consistency.
    - High: Code is well-structured with consistent comments that are well-interpreted by automated documentation tools.
    - Expert: Code is exemplary in structure and comments, facilitating automated generation of comprehensive documentation.

    Adherence to Standards:
    - Low: Code does not adhere to standard formatting.
    - Medium: Code adheres to some standard formatting.
    - High: Code follows standard formatting.
    - Expert: Code exemplifies best practices in formatting.

    Modularity:
    - Low: Code is monolithic, lacks clear separation between different aspects or functionalities of the code.
    - Medium: Some attempts at modularity, but organization is inconsistent or unclear.
    - High: Code is modular, with distinct and reasonably well-defined components.
    - Expert: Exceptional modularity, each component has a clear purpose, and the organization is exemplary.

    Naming Conventions:
    - Low: Poor choice of names, lack of consistency.
    - Medium: Descriptive names, with some inconsistencies.
    - High: Consistent, descriptive variable and function names.
    - Expert: Exceptional naming, contributing to code clarity.

    Identification of Issues:
    - Low: Code fails basic automated debugging checks with no error handling.
    - Medium: Code passes basic debugging checks but fails under edge cases or error conditions.
    - High: Code passes extensive debugging checks, including edge cases and error conditions.
    - Expert: Code demonstrates advanced error handling and recovery, passing all debugging checks under varied conditions.

    Error Handling:
    - Low: Limited or no error handling.
    - Medium: Basic error handling, but may miss some cases.
    - High: Comprehensive error handling and graceful recovery.
    - Expert: Exceptional error handling, covers all possible scenarios.
    """

    parameters=[
        "algorithm_design",
        "problem_solving_ability",
        "efficiency_of_solutions",
        "adaptability",
        "pattern_recognition",
        "parallelism_and_concurrency",
        "readability_and_maintainability",
        "adherence_to_standards",
        "modularity",
        "naming_conventions",
        "identification_of_issues",
        "error_handling"
    ]

    # llm system setup for json object
    system_template_result = """
    Return a json object with result mapping each parameter from {parameter} to low/medium/high/expert for the code{code}, on the knowledge of {rubric_descriptions}. Do not bother giving any descriptions. 
    """
    prompt_template = ChatPromptTemplate.from_messages([("system", system_template_result)])
        #parser to output only a json object
    parser = SimpleJsonOutputParser()
    chain1 = prompt_template | llm | parser
    result = chain1.invoke({"parameter": parameters, "code": code, "rubric_descriptions":rubric_descriptions})    

    system_template_feedback = """
    Generate a string object of advisory feedback for code improvement analysing results {result} for the code {code} submitted. Mention how complete the code {code} is. Give it in points not exceeding more than 10 words.
    """
    prompt_template2 = ChatPromptTemplate.from_messages([("system", system_template_feedback)])
    chain2 = prompt_template2 | llm
    feedback = chain2.invoke({"result": result, "code": code})

    #storing result to df for score generation
    #eval_df for score generation and eval_df_t for database record
    eval_df = (pd.DataFrame(result, index=["code"], columns=["algorithm_design", "problem_solving_ability", "efficiency_of_solutions", "adaptability", "pattern_recognition", "parallelism_and_concurrency", "readability_and_maintainability", "adherence_to_standards", "modularity", "naming_conventions", "identification_of_issues", "error_handling"]))
    eval_df_T = eval_df.T   #transpose of df

    #score for parameters
    score_maps = {"low":25, "medium":50, "high":75, "expert":100}
    eval_df_T["scores"] = eval_df_T["code"].map(score_maps).fillna(eval_df_T["code"])
    eval_df = eval_df_T.T    #eval_df has two rows codelabels and codescores

    #score generation
    ratings_dict = {"low":1, "medium":2, "high":3, "expert":4}
    eval_df_T["code"] = eval_df_T["code"].map(ratings_dict).fillna(eval_df_T["code"])
    score = eval_df_T["code"].sum()*2.0833    
    score = np.round(score, 2)


    # Display the result on a simple HTML page
    result_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Performance</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background-color: #fff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                text-align: center;
                width: 400px; /* Increased width for more space */
                max-height: 80vh; /* Added max-height */
                overflow-y: auto; /* Added scrollbar if content exceeds max-height */
            }}
            h2 {{
                color: #333;
            }}
            .score-container {{
                margin-top: 20px;
                padding: 20px;
                background-color: #007BFF;
                color: white;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-size: 36px;
                font-weight: bold;
                height: 150px;
            }}
            .score-container p {{
                margin: 5px 0;
            }}
            .feedback {{
                margin-top: 15px;
                font-size: 18px;
                color: #555;
                width: 100%; /* Make feedback section take full width */
                max-height: 200px; /* Maximum height for feedback section */
                overflow-y: auto; /* Add scrollbar if content exceeds max-height */
                text-align: left; /* Align feedback text to the left */
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Performance:</h2>
            <div class="score-container">
                <p>{score}&nbsp;<small>/100</small></p>
            </div>
            <div class="feedback">
                <p>{feedback}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(result_content)


    
if __name__ == "__main__":
    uvicorn.run("try:app", host="127.0.0.1", port=8000, reload=True)
