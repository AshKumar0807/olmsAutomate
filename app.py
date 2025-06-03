from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import threading
import time
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session handling
CORS(app)
# Store each session's driver separately
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
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.srmimthostel.net/olms")
    driver.find_element(By.NAME, "reg_and_studid").send_keys(reg_no)
    driver.find_element(By.NAME, "subval").click()

    with driver_lock:
        driver_sessions[session_id] = driver

    return jsonify({"message": "OTP sent, please enter OTP to verify."})

@app.route('/verify_otp', methods=['GET','POST'])
def verify_otp():
    otp = request.form.get('otp')
    print(otp)
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
        return jsonify({'error': str(e)}), 500

@app.route('/apply-leave', methods=['POST'])
def apply_leave():
    data = request.json
    leave_type = data.get('leave_type')

    if not leave_type:
        return jsonify({'error': 'leave_type is required'}), 400

    session_id = session.get('session_id')
    regno = session.get('regno')

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

        leave_radio = driver.find_element(By.CSS_SELECTOR, f"input[name='apply_for'][value='{form_value}']")
        leave_radio.click()
        time.sleep(1)

        if leave_type == 'outpass':
            outing_visit = data.get('outing_visit')
            outing_reason = data.get('outing_reason')
            outing_from_time = data.get('outing_from_time')
            outing_to_time = data.get('outing_to_time')

            if not all([outing_visit, outing_reason, outing_from_time, outing_to_time]):
                return jsonify({'error': 'Missing outing details'}), 400

            driver.execute_script(f"document.getElementById('vv_outing_from_date').value = '{outing_from_time}';")
            driver.execute_script(f"document.getElementById('vv_outing_to_date').value = '{outing_to_time}';")

            driver.find_element(By.NAME, "outing_visit").clear()
            driver.find_element(By.NAME, "outing_visit").send_keys(outing_visit)

            driver.find_element(By.NAME, "outing_reason").clear()
            driver.find_element(By.NAME, "outing_reason").send_keys(outing_reason)

        elif leave_type == 'leaving':
            from_date = data.get('from_date')
            to_date = data.get('to_date')
            reason = data.get('reason', '')
            visit_to = data.get('visit_to', '')

            driver.execute_script(f"document.getElementById('dates1').value = '{from_date}';")
            driver.execute_script(f"document.getElementById('dates2').value = '{to_date}';")

            driver.find_element(By.NAME, "leaving_visit").clear()
            driver.find_element(By.NAME, "leaving_visit").send_keys(visit_to)

            driver.find_element(By.NAME, "leaving_reason").clear()
            driver.find_element(By.NAME, "leaving_reason").send_keys(reason)

        elif leave_type == 'maintenance':
            reason = data.get('reason', '')
            maintenance_category = data.get('maintenance_category', '')
            maintenance_subcategory = data.get('maintenance_subcategory', '')

            if maintenance_category:
                category_select = driver.find_element(By.NAME, "maintenance_category")
                for option in category_select.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == maintenance_category:
                        option.click()
                        break
                time.sleep(1)

            if maintenance_subcategory:
                subcategory_select = driver.find_element(By.NAME, "maintenance_subcategory")
                for option in subcategory_select.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == maintenance_subcategory:
                        option.click()
                        break

            driver.find_element(By.NAME, "maintenance_reason").clear()
            driver.find_element(By.NAME, "maintenance_reason").send_keys(reason)

        submit_btn = driver.find_element(By.CSS_SELECTOR, "input.confirm-btn[value='Confirm']")
        submit_btn.click()
        time.sleep(3)

        return jsonify({"message": "Request applied successfully."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)