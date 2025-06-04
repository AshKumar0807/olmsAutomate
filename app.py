from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import threading
import time
import uuid
import shutil

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session handling
CORS(app)

driver_sessions = {}
driver_lock = threading.Lock()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    reg_no = request.form.get('regno')
    if not reg_no:
        return jsonify({"error": "Registration number is required"}), 400

    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    session['regno'] = reg_no

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.binary_location = "/usr/bin/chromium"#for docker
    #options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" for mac
    chromedriver_path = shutil.which("chromedriver")
    service = Service(executable_path=chromedriver_path)

    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://www.srmimthostel.net/olms")
    driver.find_element(By.NAME, "reg_and_studid").send_keys(reg_no)
    driver.find_element(By.NAME, "subval").click()

    with driver_lock:
        driver_sessions[session_id] = driver

    return jsonify({"message": "OTP sent, please enter OTP to verify."})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    otp = request.form.get('otp')
    if not otp:
        return jsonify({'error': 'OTP is required'}), 400

    session_id = session.get('session_id')
    if not session_id or session_id not in driver_sessions:
        return jsonify({'error': 'Login session not found'}), 400

    driver = driver_sessions[session_id]
    try:
        driver.find_element(By.NAME, "otp_text").send_keys(otp)
        driver.find_element(By.NAME, "otp_submit").click()
        time.sleep(2)
        return jsonify({'message': 'OTP verified successfully.'}), 200
    except Exception as e:
        driver.quit()
        with driver_lock:
            driver_sessions.pop(session_id, None)
        return jsonify({'error': str(e)}), 500

@app.route('/apply-leave', methods=['POST'])
def apply_leave():
    data = request.json
    leave_type = data.get('leave_type')
    if not leave_type:
        return jsonify({'error': 'leave_type is required'}), 400

    session_id = session.get('session_id')
    if not session_id or session_id not in driver_sessions:
        return jsonify({'error': 'Login session not found'}), 400

    driver = driver_sessions[session_id]
    try:
        leave_type_map = {
            "outpass": "outing",
            "leaving": "leaving",
            "maintenance": "maintenance"
        }
        form_value = leave_type_map.get(leave_type)

        driver.get("https://www.srmimthostel.net/olms/check_student_record")
        time.sleep(2)
        driver.find_element(By.CSS_SELECTOR, f"input[name='apply_for'][value='{form_value}']").click()

        if leave_type == 'outpass':
            for field in ['outing_visit', 'outing_reason', 'outing_from_time', 'outing_to_time']:
                if not data.get(field):
                    return jsonify({'error': f'Missing {field}'}), 400

            driver.execute_script(f"document.getElementById('vv_outing_from_date').value = '{data['outing_from_time']}';")
            driver.execute_script(f"document.getElementById('vv_outing_to_date').value = '{data['outing_to_time']}';")
            driver.find_element(By.NAME, "outing_visit").send_keys(data['outing_visit'])
            driver.find_element(By.NAME, "outing_reason").send_keys(data['outing_reason'])

        elif leave_type == 'leaving':
            driver.execute_script(f"document.getElementById('dates1').value = '{data['from_date']}';")
            driver.execute_script(f"document.getElementById('dates2').value = '{data['to_date']}';")
            driver.find_element(By.NAME, "leaving_visit").send_keys(data.get('visit_to', ''))
            driver.find_element(By.NAME, "leaving_reason").send_keys(data.get('reason', ''))

        elif leave_type == 'maintenance':
            driver.find_element(By.NAME, "maintenance_reason").send_keys(data.get('reason', ''))
            category = data.get("maintenance_category")
            subcategory = data.get("maintenance_subcategory")

            if category:
                for option in driver.find_element(By.NAME, "maintenance_category").find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == category:
                        option.click()
                        break
                time.sleep(1)

            if subcategory:
                for option in driver.find_element(By.NAME, "maintenance_subcategory").find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == subcategory:
                        option.click()
                        break

        driver.find_element(By.CSS_SELECTOR, "input.confirm-btn[value='Confirm']").click()
        time.sleep(3)

        return jsonify({"message": "Request applied successfully."})
    except Exception as e:
        driver.quit()
        with driver_lock:
            driver_sessions.pop(session_id, None)
        return jsonify({'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    session_id = session.get('session_id')
    if session_id:
        with driver_lock:
            driver = driver_sessions.pop(session_id, None)
            if driver:
                driver.quit()
    session.clear()
    return jsonify({"message": "Logged out and session cleaned up."}), 200

if __name__ == "__main__":
    app.run(debug=True)
