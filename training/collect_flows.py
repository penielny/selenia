"""Snapshot pages that only appear after logging in or clicking (the URL list can't reach them).

    python collect_flows.py --out data/pages.jsonl            # all flows
    python collect_flows.py --only saucedemo orangehrm        # some flows
    python collect_flows.py --no-headless                     # watch it work

Each flow uses the public demo credentials that the site itself publishes.
If a site changes and a flow breaks, the others still run.
Copy a flow as a template for your own apps: log in, navigate, call snap().
"""
import argparse
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from collect import make_driver, snapshot


def flow_saucedemo(d, snap):
    d.get("https://www.saucedemo.com/")
    d.find_element(By.ID, "user-name").send_keys("standard_user")
    d.find_element(By.ID, "password").send_keys("secret_sauce")
    d.find_element(By.ID, "login-button").click()
    WebDriverWait(d, 15).until(EC.url_contains("inventory"))
    snap("saucedemo-inventory")
    d.find_element(By.CSS_SELECTOR, "[data-test^='add-to-cart']").click()
    d.find_element(By.CSS_SELECTOR, "[data-test='inventory-item-name']").click()
    snap("saucedemo-product")
    d.find_element(By.CSS_SELECTOR, ".shopping_cart_link").click()
    snap("saucedemo-cart")
    d.find_element(By.ID, "checkout").click()
    snap("saucedemo-checkout-info")
    d.find_element(By.ID, "react-burger-menu-btn").click()
    time.sleep(1)
    snap("saucedemo-menu-open")


def flow_orangehrm(d, snap):
    base = "https://opensource-demo.orangehrmlive.com/web/index.php"
    d.get(f"{base}/auth/login")
    WebDriverWait(d, 20).until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("Admin")
    d.find_element(By.NAME, "password").send_keys("admin123")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    WebDriverWait(d, 20).until(EC.url_contains("dashboard"))
    snap("orangehrm-dashboard")
    for path, name in [("pim/viewEmployeeList", "employees"), ("pim/addEmployee", "add-employee"),
                       ("admin/viewSystemUsers", "system-users"), ("leave/viewLeaveList", "leave-list"),
                       ("time/viewEmployeeTimesheet", "timesheets"), ("recruitment/viewCandidates", "candidates"),
                       ("pim/viewMyDetails", "my-info"), ("directory/viewDirectory", "directory")]:
        d.get(f"{base}/{path}")
        snap(f"orangehrm-{name}")


def flow_the_internet(d, snap):
    d.get("https://the-internet.herokuapp.com/login")
    d.find_element(By.ID, "username").send_keys("tomsmith")
    d.find_element(By.ID, "password").send_keys("SuperSecretPassword!")
    d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    WebDriverWait(d, 10).until(EC.url_contains("secure"))
    snap("internet-secure-area")
    for n in (1, 2):
        d.get(f"https://the-internet.herokuapp.com/dynamic_loading/{n}")
        d.find_element(By.CSS_SELECTOR, "#start button").click()
        WebDriverWait(d, 15).until(EC.visibility_of_element_located((By.ID, "finish")))
        snap(f"internet-dynamic-loading-{n}-done")
    d.get("https://the-internet.herokuapp.com/dynamic_controls")
    d.find_element(By.CSS_SELECTOR, "#checkbox-example button").click()
    WebDriverWait(d, 15).until(EC.visibility_of_element_located((By.ID, "message")))
    snap("internet-dynamic-controls-removed")


def flow_playground(d, snap):
    d.get("https://uitestingplayground.com/sampleapp")
    d.find_element(By.NAME, "UserName").send_keys("tester")
    d.find_element(By.NAME, "Password").send_keys("pwd")
    d.find_element(By.ID, "login").click()
    snap("playground-sampleapp-logged-in")
    d.get("https://uitestingplayground.com/ajax")
    d.find_element(By.ID, "ajaxButton").click()
    WebDriverWait(d, 25).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#content p")))
    snap("playground-ajax-loaded")


def flow_practicetest(d, snap):
    d.get("https://practicetestautomation.com/practice-test-login/")
    d.find_element(By.ID, "username").send_keys("student")
    d.find_element(By.ID, "password").send_keys("Password123")
    d.find_element(By.ID, "submit").click()
    WebDriverWait(d, 10).until(EC.url_contains("logged-in-successfully"))
    snap("practicetest-logged-in")


def flow_demoqa(d, snap):
    # Widgets whose interesting state only appears after interacting
    d.get("https://demoqa.com/accordian")
    snap("demoqa-accordion")
    d.get("https://demoqa.com/modal-dialogs")
    d.find_element(By.ID, "showLargeModal").click()
    WebDriverWait(d, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "modal-content")))
    snap("demoqa-modal-open")
    d.get("https://demoqa.com/date-picker")
    d.find_element(By.ID, "datePickerMonthYearInput").click()
    time.sleep(0.5)
    snap("demoqa-datepicker-open")


def flow_todomvc(d, snap):
    for fw in ("react", "vue", "svelte"):
        d.get(f"https://todomvc.com/examples/{fw}/dist/")
        box = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.new-todo")))
        for item in ("Buy milk", "Book studio session", "Pay electricity bill"):
            box.send_keys(item + "\n")
        d.find_elements(By.CSS_SELECTOR, "input.toggle")[0].click()
        snap(f"todomvc-{fw}-with-items")


FLOWS = {
    "saucedemo": flow_saucedemo, "orangehrm": flow_orangehrm, "the-internet": flow_the_internet,
    "playground": flow_playground, "practicetest": flow_practicetest, "demoqa": flow_demoqa,
    "todomvc": flow_todomvc,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/pages.jsonl")
    ap.add_argument("--only", nargs="*", choices=sorted(FLOWS), help="run only these flows")
    ap.add_argument("--no-headless", action="store_true")
    ap.add_argument("--chrome-binary")
    args = ap.parse_args()

    for name in args.only or FLOWS:
        driver = make_driver(headless=not args.no_headless, chrome_binary=args.chrome_binary)
        count = 0

        def snap(page_id):
            nonlocal count
            rec = snapshot(driver, args.out, page_id=page_id)
            count += 1
            print(f"  {page_id:40s} {len(rec['candidates']):5d} elements")

        print(f"== {name}")
        try:
            FLOWS[name](driver, snap)
        except Exception as e:  # a broken flow shouldn't stop the others
            print(f"  FAILED after {count} snapshots: {type(e).__name__}: {str(e).splitlines()[0][:150]}")
        finally:
            driver.quit()


if __name__ == "__main__":
    main()
