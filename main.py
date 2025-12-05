import os
import logging
import sys
from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from resume_model import HiringAgency

# --- CONFIGURE LOGGING ---
# This ensures logs show up in Docker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Agency
try:
    agency = HiringAgency()
    logger.info(" Hiring Agency Initialized Successfully")
except Exception as e:
    logger.critical(f" Failed to Initialize Agency: {e}")

@app.route('/')
def index():
    return render_template('input.html')

@app.route('/process', methods=['POST'])
def process():
    if 'resumes' not in request.files:
        return redirect('/')
        
    files = request.files.getlist('resumes')
    jd_text = request.form.get('jd_text')

    valid_files = [f for f in files if f.filename != '']
    
    if not valid_files or not jd_text:
        return "Please provide a JD and at least one resume."

    processed_results = []
    errors = []

    logger.info(f" Starting Batch Processing for {len(valid_files)} files.")

    for file in valid_files:
        filename = secure_filename(file.filename)
        
        # Skip temporary files (common in Windows/Mac)
        if filename.startswith('~$') or filename.startswith('.'):
            logger.warning(f" Skipping temporary file: {filename}")
            continue

        if filename.endswith(('.pdf', '.docx')):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(file_path)
                logger.info(f" Processing: {filename}")
                
                # --- CALL THE AGENT ---
                analysis = agency.process_application(file_path, jd_text)
                if analysis:
                    analysis['filename'] = filename
                    processed_results.append(analysis)
                    logger.info(f" Success: {filename} (Score: {analysis.get('ats_score')})")
                else:
                    err_msg = f"{filename}: Returned None (Check Docker Logs for details)"
                    errors.append(err_msg)
                    logger.error(f" Failure: {filename} returned empty result.")
            
            except Exception as e:
                logger.error(f" Crash processing {filename}: {e}")
                errors.append(f"{filename}: {str(e)}")
            
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

    if processed_results:
        processed_results.sort(key=lambda x: x['ats_score'], reverse=True)
        winner = processed_results[0]
        return render_template('output.html', winner=winner, count=len(processed_results))
    else:
        error_summary = " | ".join(errors)
        return f"<h3>Processing Failed</h3><p><b>Errors:</b> {error_summary}</p>"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)