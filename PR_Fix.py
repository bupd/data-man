import logging
from selenium.webdriver.common.by import By
from selenium.webdriver import Remote
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction
from appium.options.common import AppiumOptions
from gsheet import get_spreadsheet_data
from gsheet import post_data_to_spreadsheet
from datetime import datetime
import pandas as pd
import time
import re
import json

# Logging setup
logging.basicConfig(
    filename="appium_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

# Retry decorator
def retry(max_retries=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.warning(f"Attempt {attempt}/{max_retries} failed: {e}")
                    if attempt == max_retries:
                        logging.error(f"All {max_retries} attempts failed.")
                        raise
                    time.sleep(2)  # Delay before retry
        return wrapper
    return decorator

def is_event_match(artist, event_date, event_venue):
    """Check if the artist has a matching event date and venue in the map."""
    # Check if the artist exists in the event map
    if artist in artist_event_map:
        print(f"checking for artist: {artist}")
        for event in artist_event_map[artist]:
            # Check if the event date and venue match
            print(f"artist got event date: {event_date}, correct date: {event[2]} ")
            print(f"artist got event venue: {event_venue}, correct venue: {event[1]} ")
            if event[2] == event_date and event_venue.startswith(event[1]):
                return True  # Match found
    return False  # No match found


# Function to update event data based on the spreadsheet data
def update_event_data(event_data, spreadsheet_data):
    for event in event_data:
        # Iterate through spreadsheet data and update if there's a match
        for idx, row in enumerate(spreadsheet_data):
            # Compare Artist, Event Date, and Venue
            if (event['Artist'] == row['Artist'] and
                event['Event Date'] == row['Date'] and
                event['Venue'].startswith(row['Venue'])):  # Strip extra spaces and check for match

                date = row['Date']
                date = str(date)
                # Update Views and Timestamp
                row['Views'] = event['Views']
                row['Timestamp'] = event['Timestamp']
                row['Date'] = date
                row['rowIndex'] = idx + 2

                break  # Once matched, no need to continue checking other rows
    return spreadsheet_data



def format_date(curr_date):
    """This will fing format your date correctly if you are even out of your mind."""
    try:
        # Attempt to parse in MM/DD/YYYY format
        date = datetime.strptime(curr_date, "%m/%d/%Y").strftime("%m/%d/%Y")
        return date
    except ValueError:
        # If the above fails, try parsing in ISO format (YYYY-MM-DDTHH:mm:ss.sssZ)
        try:
            date_object = datetime.strptime(curr_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            formatted_date = date_object.strftime("%m/%d/%Y")
            return formatted_date
        except ValueError:
            # If both fail, return a default error message or handle accordingly
            return "Invalid date format"

# Scroll function
def scroll_down(driver, distance=800):
    """Scroll down using W3C-compliant actions."""
    try:
        window_size = driver.get_window_size()
        x, y = window_size['width'] / 6, window_size['height'] / 2
        action = ActionChains(driver)
        action.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, 'touch'))
        action.w3c_actions.pointer_action.move_to_location(x, y)
        action.w3c_actions.pointer_action.click_and_hold()
        action.w3c_actions.pointer_action.move_to_location(x, y - distance)
        action.w3c_actions.pointer_action.release()
        action.w3c_actions.perform()
        logging.info("Scrolled down successfully.")
        time.sleep(2)
    except Exception as e:
        logging.error(f"Error during scrolling: {e}")
        raise

# Appium configuration
appium_server_url = 'http://127.0.0.1:4723'
options = AppiumOptions()
options.set_capability("appium:platformName", "Android")
options.set_capability("appium:platformVersion", "14")
options.set_capability("appium:deviceName", "emulator-5554")
options.set_capability("appium:appPackage", "com.vividseats.android")
options.set_capability("appium:appActivity", "com.vividseats.android.MainActivity")
options.set_capability("appium:automationName", "UiAutomator2")
options.set_capability("appium:noReset", True)

# Artists list
# get artists, date, venue
# update the datastructure to map. so every artist key will have-- date and venue
artist_event_map = {}

# get the spreadsheet_data
web_app_url = "https://script.google.com/macros/s/AKfycbwyw9XXxT1Zh4YHy5w0Z6cS1i9Tpbt_yRXhLG_qObIzRMqhf9zFiR5Xq76Eg2v78x46iw/exec"
spreadsheet_data = get_spreadsheet_data(web_app_url)

# Data containers
artist_datas = []
event_datas = []

try:
    driver = Remote(command_executor=appium_server_url, options=options)
    logging.info("Appium session started.")

    @retry(max_retries=3)
    def search_artist(artist):
        """Search for the artist and return fan count."""
        try:
            search_bar = driver.find_element(By.ID, "com.vividseats.android:id/VSSearch-search-bar")
            search_bar.click()
            time.sleep(2)
            search_bar.send_keys(artist)
            logging.info(f"Searching for artist: {artist}")
            time.sleep(2)
            result = driver.find_element(By.XPATH, "//android.view.ViewGroup[starts-with(@resource-id, 'com.vividseats.android:id/list-item-performer-0')]")
            result.click()
            time.sleep(5)

            try:
                fans_count_element = driver.find_element(By.XPATH, "//android.widget.TextView[contains(@text, 'fans shopping for these tickets')]")
                fans_count_text = fans_count_element.text
                fans_count = fans_count_text.split()[0]
                logging.info(f"Fans shopping for '{artist}': {fans_count}")
            except Exception:
                fans_count = ""
                logging.warning(f"Fans count not found for '{artist}'.")
                raise

            return fans_count
        except Exception as e:
            logging.error(f"Error during artist search: {e}")
            raise

    @retry(max_retries=3)
    def collect_event_details(artist):
        """Collect event details."""
        retrieved_elements = set()
        while True:
            elements = driver.find_elements(By.XPATH, "//android.widget.Button[starts-with(@resource-id, 'com.vividseats.android:id/button-date-list-row-')]")
            new_elements_found = False

            # print("\ngoing to print elements:")
            # print(elements)
            for element in elements:
                # print("\nokay now printing the current element:")
                # print(element)
                if element in retrieved_elements:
                    continue
                retrieved_elements.add(element)
                new_elements_found = True

                content_desc = element.tag_name
                pattern = r"^(?P<month>\w+), (?P<day>\d+), .*?, (?P<event_name>.+?), (?P<time>.+?), (?P<venue>.+?)$"

                for attempt in range(2):
                    try:
                        match = re.match(pattern, content_desc)
                        if match:
                            print("\ntrying this element:")
                            print(match)
                            month = match.group("month")
                            day = match.group("day")
                            event_name = match.group("event_name")
                            time_ = match.group("time").replace("\u202f", " ") if "TBD" not in match.group("time") else ""
                            venue = match.group("venue")
                            year = datetime.now().year
                            formatted_date = datetime.strptime(f"{month} {day} {year}", "%B %d %Y").strftime("%m/%d/%Y")
                            # Check if date and venue match
                            # print(f"Formatted date: {formatted_date}, Correct date: {correct_date}")
                            # print(f"Venue: {venue}, Correct venue: {correct_venue}")

                            if is_event_match(artist, formatted_date, venue):
                                print("\nMatch found! Clicking the event.")
                                element.click()
                            else:
                                print("No match for this event.")
                                continue

                            time.sleep(10)  # Wait for the new page to load
                            try:
                                fans_count_element = driver.find_element(By.XPATH, "//android.widget.TextView[contains(@text, 'fans shopping for these tickets')]")
                                fans_count_text = fans_count_element.text
                                fans_count = fans_count_text.split()[0]  # Extract the number
                            except Exception as e:
                                if attempt == 2:
                                    fans_count = ""  # If not found, leave it blank
                                else:
                                    driver.back()
                                    time.sleep(2)
                                    raise("try again..")
                            # print(f"Number of fans shopping for tickets for '{artist}': {fans_count}")

                            event_datas.append({
                                "Artist": artist,
                                "Timestamp": datetime.now().strftime("%Y-%m-%d %H_%M_%S"),
                                "Event Date": formatted_date,
                                "Venue": venue.replace('Viewed', ''),
                                "Views": fans_count
                            })
                            ## push the event here todo: push event_datas
                            logging.info(f"Collected event: {event_name}, {formatted_date}, {time_}, {venue}")
                            driver.back()
                            time.sleep(2)
                        else:
                            if attempt == 2:
                                continue
                            else:
                                raise("try again..")
                        break
                    except Exception as e:
                        logging.warning(f"Retry {attempt + 1}: Regex match failed: {e}")
                        if attempt == 2:
                            logging.error(f"Failed to parse content_desc: {content_desc}")

            if not new_elements_found:
                logging.info("No new elements found. Stopping collection.")
                break

            try:
                show_more = driver.find_element(By.XPATH, "//android.widget.Button[starts-with(@resource-id, 'com.vividseats.android:id/button-show-more')]")
                show_more.click()
                logging.info("show_more button clicked.")
                time.sleep(5)
            except Exception:
                scroll_down(driver)

    # core logic lying here
    # print(spreadsheet_data)
    if spreadsheet_data:
        print("Data retrieved from spreadsheet.")
        # print("printing spreadsheet.")
        print(spreadsheet_data)
        for data in spreadsheet_data:
            curr_date = data['Date']  # 'Date' is assumed to be a key in each item
            # print(f"curent fucking date: {curr_date}")
            date = format_date(curr_date)
            # # try this if it fails
            # date = datetime.strptime(curr_date, "%m/%d/%Y").strftime("%m/%d/%Y")
            # # try the below
            # date_object = datetime.strptime(curr_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            # formatted_date = date_object.strftime("%m/%d/%Y")
            print("\nPrinting x data")
            print(f"Artist: {data['Artist']}, Date: {date}, Venue: {data['Venue']}")

            # Check if the artist is in our desired list of artists
            if data['Artist'] not in artist_event_map:
                artist_event_map[data['Artist']] = []
            artist_event_map[data['Artist']].append((data['Artist'], data['Venue'], date))

        # Example of how to post data back to the spreadsheet (optional)
        # post_data_to_spreadsheet(web_app_url, artist_event_map)

        print("\nArtist Event Map:", artist_event_map)
        print("Data retrieved from spreadsheet.")
        # You can post the artist_event_map back or modify spreadsheet_data with the mapping
        # for artist, events in artist_event_map.items():
        #     for event in events:
        #         print(f"Artist: {artist}, Date: {event[0]}, Venue: {event[1]}")

    for artist in artist_event_map:
        fans_count = search_artist(artist)
        artist_datas.append({"Artist": artist, "Timestamp": datetime.now().strftime("%Y-%m-%d %H_%M_%S"), "Vivid Views": fans_count})
        # push artist data to the gsheet thing
        collect_event_details(artist)
        # push event datas to the sheet
        driver.back()
        time.sleep(2)

finally:
    driver.quit()
    logging.info("Appium session closed.")
    # Save data to spreadsheet_data
    print("hello llla")
    print(event_datas)
    # Call the function to update the event data
    updated_event_data = update_event_data(event_datas, spreadsheet_data)
    print(updated_event_data)
    # for idx, row in enumerate(updated_event_data):
    #     row['rowIndex'] = idx + 2
    # print(updated_event_data)
    # Post the modified data back:
    post_response = post_data_to_spreadsheet(web_app_url, spreadsheet_data)

    if post_response:
        print("\nData posted successfully:")
        print(json.dumps(post_response, indent=2))
    else:
        print("\nData post failed")


# # Save data to Excel
# with pd.ExcelWriter("scraped_artists_data.xlsx") as writer:
#     pd.DataFrame(artist_datas).to_excel(writer, sheet_name="Vivid Artist", index=False)
#     pd.DataFrame(event_datas).to_excel(writer, sheet_name="Vivid Event", index=False)
# logging.info("Data saved to 'scraped_artists_data.xlsx' successfully.")
