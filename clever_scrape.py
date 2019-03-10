### Import dependencies
import selenium.webdriver as webdriver, selenium.common.exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import bs4 as bs
import time
import pandas as pd

### FLOW CONTROL
login_toggle = True
district_ids_import_toggle = False
scraper_toggle = True
writer_toggle = True


### HELPER FUNCTION: Parses raw strings from district info scrape
def district_data_parser(labels, data):
    
    ## Create container of string data
    district_data = [x.text for x in data]
    district_data_labels = [y.text for y in labels]

    assert len(district_data) == len(district_data_labels), "Mismatch between labels and data!"
    
    ## Assemble row as dictionary
    row_data = dict(zip(district_data_labels, district_data))

    ## Remove 'Last Sync' time
    for k, v in row_data.items():
        if "Last sync:" in k:
            key_to_del = k

    row_data.pop(key_to_del, None)

    return row_data


### FLOW CONTROL
if __name__ == "__main__":

    if login_toggle:
        ### Read in Clever sandbox credentials
        with open("./clever_credentials.txt","r") as f:
            creds = [line.rstrip() for line in f]

        ### Start browser and naviate to Clever dev sandbox
        driver = webdriver.Chrome()
        driver.get("https://apps.clever.com/")
        wait = WebDriverWait(driver, 2)

        ### Log into Clever dev sandbox 
        try:
            login_button = wait.until(EC.element_to_be_clickable((By.TAG_NAME, 'button')))
            username = driver.find_element_by_name("email")
            password = driver.find_element_by_name("password")
            username.send_keys(creds[0])
            password.send_keys(creds[1])
            login_button.click()

        except:
            print("Login error!")

    if district_ids_import_toggle:
        nces_ids = pd.read_csv(r'./nces_ids.csv', dtype = str, header = None, index_col = 0)
        district_ids = nces_ids[1].tolist()
        
    else:
        ### Go through remaining unknowns 
        remaining_unknowns_clever = pd.read_csv(r'./remaining_unknowns_clever.csv', dtype = str, header = None, index_col = 0)
        district_ids = remaining_unknowns_clever[1].tolist()


    if scraper_toggle:
        ### Instantiate container to generate dataframe
        rows_districts_info = []

        ### Loop through all districts
        for nces_id in district_ids:
            
            ### Search for district
            search_box = wait.until(EC.element_to_be_clickable((By.NAME, 'DistrictSearch--Input')))

            ## Janky clear box
            ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            search_box.send_keys(Keys.DELETE)
            search_box.send_keys(nces_id)
            
            try:
                ## Try to reenter NCES ID and use ENTER key to select first result
                time.sleep(.5)
                search_box.send_keys(Keys.DOWN)
                ActionChains(driver).key_down(Keys.ENTER).key_up(Keys.ENTER).perform()

            except:
                ## Attempt to navigate to *some* result district page
                top_result = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'DistrictSearch--Results')))
                top_result.click()

            try:
                wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME,
                    'DistrictProfile--Highlight--content')))

                ### Time delay to load dynamic data
                time.sleep(.5)

                ### Scrape info
                html = driver.page_source
                soup = bs.BeautifulSoup(html, features='lxml')
                
                ### Extract district info
                district_info = soup.find_all("div", class_ = 'DistrictProfile--Highlight--value')
                district_info_labels = soup.find_all("div", class_ = 'DistrictProfile--Highlight--label DistrictProfile--Highlight--line')

                ### Parse and store district info
                rows_districts_info.append(district_data_parser(district_info_labels, district_info))

                ### Finish with current district
                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'OmniSearch--SearchBarLabel--closeButton'))).click()
                
            except selenium.common.exceptions.TimeoutException:
                search_box.clear()


        ### Close browser, end WebDriver
        driver.quit()

        ### Create dataframe and write to outfile
        df = pd.DataFrame(rows_districts_info)
        df.drop_duplicates(inplace = True)
        print("Done creating dataframe!")

    if writer_toggle and district_ids_import_toggle:
        filename = "clever_data_" + time.strftime("%Y-%m-%d_%H:%M:%S") + ".csv"

    elif writer_toggle and not district_ids_import_toggle:
        filename = "rediscovered_clever_data_" + time.strftime("%Y-%m-%d_%H:%M:%S") + ".csv"
        
    try:
        df.to_csv("./logs/"+filename)
        print("Wrote to log!")
    except:
        exit()
