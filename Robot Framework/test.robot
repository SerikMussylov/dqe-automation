*** Settings ***
Documentation     Compares the table of the BI report with the Parquet dataset it is built from.
Library           SeleniumLibrary
Library           helper.py
Test Teardown     Close All Browsers

*** Variables ***
${REPORT_FILE}       ${CURDIR}${/}generated_report${/}report.html
${PARQUET_FOLDER}    ${CURDIR}${/}parquet_data${/}facility_type_avg_time_spent_per_visit_date
${FILTER_DATE}       2026-09-26
${BROWSER}           chrome

*** Test Cases ***
Report Table Matches Parquet Data
    [Documentation]    Passes when the HTML table and the filtered Parquet data match exactly.
    ${report_uri}=    Path To File Uri    ${REPORT_FILE}
    Open Browser    ${report_uri}    ${BROWSER}
    Set Window Size    1920    1080
    Wait Until Element Is Visible    class:table    10s
    ${table}=    Get WebElement    class:table
    ${html_df}=    Read Html Table    ${table}
    ${parquet_df}=    Read Parquet Dataset    ${PARQUET_FOLDER}    ${FILTER_DATE}
    ${html_rows}=    Get Length    ${html_df}
    ${parquet_rows}=    Get Length    ${parquet_df}
    Log    HTML rows: ${html_rows}, Parquet rows (from ${FILTER_DATE}): ${parquet_rows}
    ${diff}=    Compare Dataframes    ${html_df}    ${parquet_df}
    ${diff_count}=    Get Length    ${diff}
    ${details}=    Format Differences    ${diff}
    Run Keyword If    ${diff_count} > 0    Fail    HTML table and Parquet data differ:\n${details}