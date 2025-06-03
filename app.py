from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import threading
import time

app = Flask(__name__)

# Global Selenium driver instance (for demo purposes, one session at a time)
driver = None
lock = threading.Lock()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start-login', methods=['POST'])
def start_login():
    global driver
    reg_no = request.form.get('regno')

    if not reg_no:
        return jsonify({"error": "Registration number is required"}), 400

    with lock:
        if driver:
            driver.quit()

        options = Options()
        #options.add_argument('--headless')  # Comment this if you want to see the browser
        options.add_argument('--disable-gpu')
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)

        driver.get("https://www.srmimthostel.net/olms")

        # Input registration number (student id)
        driver.find_element(By.NAME, "reg_and_studid").send_keys(reg_no)
        driver.find_element(By.NAME, "subval").click()

    return jsonify({"message": "OTP sent, please enter OTP to verify."})

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    global driver
    otp = request.form.get('otp')

    if not otp:
        return jsonify({"error": "OTP is required"}), 400

    with lock:
        if not driver:
            return jsonify({"error": "Please start login first."}), 400

        # Input OTP and click verify
        driver.find_element(By.NAME, "otp_text").send_keys(otp)
        driver.find_element(By.NAME, "otp_submit").click()

        # Optional: wait for some element that shows login success
        time.sleep(2)

    return jsonify({"message": "Login successful. You can now apply leave/outpass."})

@app.route('/apply-leave', methods=['POST'])
def apply_leave():
    global driver

    if not driver:
        return jsonify({"error": "Please login first."}), 400

    data = request.json
    leave_type = data.get('leave_type')

    leave_type_map = {
    "outpass": "outing",
    "leaving": "leaving",
    "maintenance": "maintenance"}
    form_value = leave_type_map.get(leave_type)

    with lock:
        driver.get("https://www.srmimthostel.net/olms/check_student_record")
        time.sleep(2)  # Wait for page to load

        # Select the radio button based on leave_type
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

            # Set datetime via JavaScript to avoid picker interference
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

        # Submit the form
        submit_btn = driver.find_element(By.CSS_SELECTOR, "input.confirm-btn[value='Confirm']")
        submit_btn.click()
        time.sleep(3)

    return jsonify({"message": "Request applied successfully."})


if __name__ == "__main__":
    app.run(debug=True)
