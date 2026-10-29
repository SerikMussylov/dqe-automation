import csv
from itertools import zip_longest
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)


BASE_DIR = Path(__file__).resolve().parent
REPORT_PATH = BASE_DIR / "report.html"
TABLE_HEADERS = ["Facility Type", "Min Average Time Spent"]


class SeleniumWebDriverContextManager:
    def __init__(self):
        self.driver = None

    def __enter__(self):
        self.driver = webdriver.Chrome()
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver is not None:
            self.driver.quit()
        return False


def validate_report(report_path):
    if not report_path.is_file():
        raise FileNotFoundError(
            f"Report not found: {report_path}. Copy the report from the container "
            "to this location before running the script."
        )

    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    if "replace this file with yours" in report_text.lower():
        raise ValueError(
            f"{report_path} is still the starter placeholder. Replace it with the "
            "HTML report copied from the container."
        )


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(rows)


def extract_table(driver):
    wait = WebDriverWait(driver, 15)
    table = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, ".table"))
    )
    columns = table.find_elements(
        By.XPATH,
        ".//*[contains(concat(' ', normalize-space(@class), ' '), ' y-column ')]",
    )
    if not columns:
        raise NoSuchElementException(
            "The report table does not contain any y-column elements."
        )

    headers = []
    values_by_column = []
    for column in columns:
        header = column.find_element(By.ID, "header").text.strip()
        headers.append(header)
        values = [
            cell.text.strip()
            for cell in column.find_elements(By.CLASS_NAME, "cell-text")
            if cell.text.strip() != header
        ]
        values_by_column.append(values)

    rows = list(zip_longest(*values_by_column, fillvalue=""))
    write_csv(BASE_DIR / "table.csv", headers, rows)


def get_chart_signature(plot):
    labels = plot.find_elements(
        By.CSS_SELECTOR, "text.slicetext[data-notex='1']"
    )
    return tuple(label.text.strip() for label in labels)


def chart_state_changed(plot, previous_state):
    try:
        return get_chart_signature(plot) != previous_state
    except StaleElementReferenceException:
        return False


def extract_chart_data(plot):
    labels = plot.find_elements(
        By.CSS_SELECTOR, "text.slicetext[data-notex='1']"
    )
    rows = []
    for label in labels:
        lines = label.find_elements(By.TAG_NAME, "tspan")
        if len(lines) >= 2:
            category = lines[0].text.strip()
            value = lines[1].text.strip()
            if category:
                rows.append([category, value])
    return rows


def capture_chart_state(plot, index):
    screenshot_path = BASE_DIR / f"screenshot{index}.png"
    csv_path = BASE_DIR / f"doughnut{index}.csv"
    plot.screenshot(str(screenshot_path))
    rows = extract_chart_data(plot)
    write_csv(csv_path, TABLE_HEADERS, rows)
    if not rows:
        print(f"Chart state {index} has no visible slices; saved an empty data CSV.")


def extract_doughnut_states(driver):
    wait = WebDriverWait(driver, 15)
    chart_layer = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "pielayer"))
    )
    plot = chart_layer.find_element(
        By.XPATH, "./ancestor::div[contains(@class, 'js-plotly-plot')][1]"
    )
    capture_chart_state(plot, 0)

    legend = plot.find_element(By.CLASS_NAME, "scrollbox")
    filter_count = len(legend.find_elements(By.CLASS_NAME, "traces"))
    output_index = 1

    for filter_index in range(filter_count):
        try:
            previous_state = get_chart_signature(plot)
            # Plotly redraws the legend after a toggle, so reacquire the item each time.
            current_legend = plot.find_element(By.CLASS_NAME, "scrollbox")
            filter_item = current_legend.find_elements(By.CLASS_NAME, "traces")[filter_index]
            wait.until(EC.element_to_be_clickable(filter_item)).click()
            wait.until(lambda _driver: chart_state_changed(plot, previous_state))
            capture_chart_state(plot, output_index)
            output_index += 1
        except (
            ElementClickInterceptedException,
            NoSuchElementException,
            StaleElementReferenceException,
            TimeoutException,
        ) as error:
            print(f"Could not apply chart filter {filter_index + 1}: {error}")


if __name__ == "__main__":
    try:
        validate_report(REPORT_PATH)
        with SeleniumWebDriverContextManager() as driver:
            driver.get(REPORT_PATH.as_uri())
            extract_table(driver)
            extract_doughnut_states(driver)
        print(f"Automation complete. Outputs saved in: {BASE_DIR}")
    except (
        FileNotFoundError,
        NoSuchElementException,
        TimeoutException,
        ValueError,
        WebDriverException,
    ) as error:
        raise SystemExit(f"Automation failed: {error}") from error
