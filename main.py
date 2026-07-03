import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

# ==============================================================================
# CONFIGURATION
# ==============================================================================
TARGET_URL = "http://10.11.24.20/#/portal" # TODO: Update this URL
OUTPUT_CSV = "data/scraped_personnel.csv"
IMAGES_DIR = "images"

def init_directories():
    os.makedirs("data", exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

def run_scraper():
    print(f"Starting Scraper. Target URL: {TARGET_URL}")
    init_directories()

    with sync_playwright() as p:
        # Launch browser in non-headless mode so you can log in manually
        browser = p.chromium.launch(headless=False)
        # Gunakan no_viewport=True agar ukuran layar kembali standar dan bisa Anda ubah-ubah (resize)
        context = browser.new_context(
            accept_downloads=True,
            no_viewport=True
        )
        page = context.new_page()

        print(f"Navigating to {TARGET_URL}")
        try:
            page.goto(TARGET_URL)
        except Exception as e:
            print(f"Failed to navigate to {TARGET_URL}: {e}")
            print("Please make sure the TARGET_URL is correct.")
            return

        print("\n" + "="*50)
        print("ACTION REQUIRED:")
        print("1. Please log in to the portal if you haven't already.")
        print("2. Navigate to the page containing the personnel table.")
        print("3. Press ENTER here in the console once the table is fully loaded.")
        print("="*50 + "\n")
        
        input("Press ENTER to start scraping...")

        # Initialize list to store data
        scraped_data = []

        # ======================================================================
        # SCRAPING LOGIC (Needs adjustment based on actual HTML structure)
        # ======================================================================
        
        print("Starting scraping process...")
        
        # Example of how to iterate through pages
        # This while loop will run until there are no more pages
        page_num = 1
        has_next_page = True
        previous_first_id = None
        
        while has_next_page:
            print(f"Scraping Page {page_num}...")
            
            # Wait for table rows to be present. 
            # You might need to update the selector '.el-table__row' based on actual site
            # Hikvision usually uses Element UI or similar Vue/React frameworks
            try:
                page.wait_for_selector("tbody tr", timeout=10000)
            except Exception:
                print("Could not find table rows. Please check if you are on the right page.")
                break

            # Get all rows in the table
            rows = page.query_selector_all("tbody tr")
            print(f"Found {len(rows)} rows on this page.")
            
            for index, row in enumerate(rows):
                try:
                    # NOTE: These selectors need to be adjusted based on the actual DOM
                    # We are guessing standard table columns based on the screenshot
                    cells = row.query_selector_all("td")
                    
                    if len(cells) < 6:
                        continue # Skip invalid rows
                    
                    # Assuming column order: Checkbox, Profile Pic, Name, ID, Person/Visitor, Phone No, Person Group
                    name = cells[2].inner_text().strip()
                    person_id = cells[3].inner_text().strip()
                    person_type = cells[4].inner_text().strip()
                    phone = cells[5].inner_text().strip()
                    person_group = cells[6].inner_text().strip()
                    
                    # Try to get the image URL and save it
                    img_element = cells[1].query_selector("img")
                    img_src = ""
                    image_filename = f"{person_id}.png" if person_id else f"unknown_{index}.png"
                    image_path = os.path.join(IMAGES_DIR, image_filename)
                    
                    if img_element:
                        try:
                            # Scroll into view just in case it's lazy loaded
                            img_element.scroll_into_view_if_needed()
                            
                            # Extract base64 via canvas to ensure we get exactly what's rendered
                            base64_str = img_element.evaluate("""(img) => {
                                const canvas = document.createElement('canvas');
                                canvas.width = img.naturalWidth || img.width || 100;
                                canvas.height = img.naturalHeight || img.height || 100;
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(img, 0, 0);
                                return canvas.toDataURL('image/png');
                            }""")
                            
                            if base64_str and "," in base64_str:
                                base64_data = base64_str.split(",")[1]
                                import base64
                                with open(image_path, "wb") as f:
                                    f.write(base64.b64decode(base64_data))
                                img_src = image_path
                            else:
                                img_src = img_element.get_attribute("src") or "Error saving"
                        except Exception as e:
                            print(f"      -> Failed to save image for {name}: {e}")
                            img_src = img_element.get_attribute("src") or "Error saving"
                    
                    record = {
                        "Name": name,
                        "ID": person_id,
                        "Type": person_type,
                        "Phone": phone,
                        "Group": person_group,
                        "ImageSource": img_src
                    }
                    scraped_data.append(record)
                    print(f"  -> Scraped: {name} (ID: {person_id})")
                    
                except Exception as e:
                    print(f"  -> Error scraping a row: {e}")

            # Check if we are looping on the same page
            if scraped_data:
                current_first_id = scraped_data[-len(rows)]["ID"] if len(rows) > 0 else None
                if current_first_id == previous_first_id:
                    print("Detected same data as previous page. Assuming end of list.")
                    # Remove the duplicates we just added for this page
                    scraped_data = scraped_data[:-len(rows)]
                    break
                previous_first_id = current_first_id

            # Check if there's a next page button and if it's not disabled
            # E.g., Next button selector: '.btn-next'
            next_button = page.query_selector(".btn-next")
            
            if next_button and not next_button.get_attribute("disabled") and "is-disabled" not in next_button.get_attribute("class"):
                print("Going to next page...")
                next_button.click()
                time.sleep(3) # Wait for table to reload
                page_num += 1
            else:
                print("No more pages left.")
                has_next_page = False
        
        # Save to DataFrame
        if scraped_data:
            df = pd.DataFrame(scraped_data)
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"\nScraping complete! Saved {len(scraped_data)} records to {OUTPUT_CSV}")
        else:
            print("\nNo data was scraped.")

        # Keep browser open for a few seconds before closing
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    run_scraper()
