#!/usr/local/bin/python3


# ****** # # # # # # # # # # # # # # # # # # # # # # # ****** #
# ******                                               ****** #
# ******   Name: Siddhant Shah                         ****** #
# ******   Date: 02/05/2023                            ****** #
# ******   Desc: Tiktok SCRAPER                        ****** #
# ******   Email: siddhant.shah.1986@gmail.com         ****** #
# ******                                               ****** #
# ****** # # # # # # # # # # # # # # # # # # # # # # # ****** #


# >> imports
import requests, os, json, pyfiglet, logging, numpy
import datetime, cv2, concurrent.futures, pandas
from PIL import Image, ImageChops
from fuzzywuzzy import fuzz


# >> just for decoration
def intro():
    print()
    print(pyfiglet.figlet_format("      GeekySid"))
    print()
    print('  # # # # # # # # # # # # #  # # # # # # # # # # # # #')
    print('  #                                                  #')
    print('  #  TIKTOK SCRAPER TO GET CLOSEST MATCHING PROFILE  #')
    print('  #                By: SIDDHANT SHAH                 #')
    print('  #                  Dt: 03-05-2023                  #')
    print('  #           siddhant.shah.1986@gmail.com           #')
    print('  #         **Just for Educational Purpose**         #')
    print('  #                                                  #')
    print('  # # # # # # # # # # # # #  # # # # # # # # # # # # #')
    print()


# >> setting up logger
def set_logger() -> logging:
    """function to setup logger

    Returns:
        logging: logger instance
    """

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    logger_path = os.path.join(BASE_FOLDER, "LOGs")
    if not os.path.exists(logger_path):
        os.makedirs(logger_path)

    file_handler = logging.FileHandler(os.path.join(logger_path, f"{datetime.datetime.now().strftime('%d-%m-%Y %H-%M-%S')}.log"))
    formatter = logging.Formatter("%(asctime)s - %(process)d - %(levelname)s - %(message)s", datefmt="%d-%m-%Y %H-%M-%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"SCRIPT STARTED || Time: {datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}")
    return logger


# >> function to save text in log file and also display on console
def debug(message: str="", type: str="info", separator: str="") -> None:
    """function to save text in log file and also display on console

    Args:
        message (str): message to be output to log file and display on console. Defaults to ""
        type (str): type of message, debug, info, warning, error, exception. Defaults to info
        separator (str): just for console decoration. Defaults to ""
    """

    message = str(message.encode('utf-8', 'ignore'))

    # logging to console if debug is set to true in config file
    if CONFIG["debug"]:
        print(f"{separator} {message}")

    # logging to log file depending on type
    if type.lower() == 'info':
        logger.info(message)
    elif type.lower() == 'debug':
        logger.debug(message)
    elif type.lower() == 'warning':
        logger.warning(message)
    elif type.lower() == 'info':
        logger.error(message)
    elif type.lower() == 'error':
        logger.error(message)
    elif type.lower() == 'exception':
        logger.exception(message)


# >> read config file
def read_config(): 
    config_path = os.path.join(BASE_FOLDER, 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as r:
                return json.load(r)
        except Exception as e:
            print(f"\n    [xx] Exception while reading config file || {e}")
    
    print(f"Unable to locate config file as {config_path}")


# >> making request to tiktok using Rapid API
def make_request(rapid_api_url: str, querystring: str)-> dict:
    """function to make a request to RapidAPI to get a data

    Args:
        rapid_api_url (str): url of the rapid api
        querystring (str): payload to be passed to the api call

    Returns:
        dict: response from the request made to Rapid API
    """

    headers = {
        "X-RapidAPI-Key": CONFIG['rapid_api']['key'],
        "X-RapidAPI-Host": CONFIG['rapid_api']['host']
    }

    try:
        response = requests.get(rapid_api_url, headers=headers, params=querystring)
        if response.status_code == 200:
            user_data = json.loads(response.text)
            if "msg" in user_data and user_data["msg"].lower() == "success":
                return json.loads(response.text)
        debug(message=f"Got {response.status_code}", type="error", separator="\n    [xx] ")
    except Exception as e:
        debug(message=f"Exception while making request || {e}", type="exception", separator="\n    [xx] ")
    return None


# >> function to read profiles from input file
def read_input(file_name: str) -> list:
    """function to read profiles from input file

    Args:
        file_name (str): name of input file

    Returns:
        list: list of profiles
    """    
    try:
        profiles = []
        file = os.path.join(BASE_FOLDER, file_name)

        if os.path.exists(file):
            with open(file, 'r') as r:
                profiles = [ profile.split("/@")[-1] for profile in r.read().split("\n") ]
        else:
            debug(message=f" File not found: {file}", type="error", separator="\n [xx] ")
    except Exception as e:
        debug(message=f"Exception while reading file: {file} || {e}", type="exception", separator="\n    [xx] ")
    
    return profiles


# >> formatting user details
def get_user_detail(user_data: dict) -> dict:
    """function to format user details from user dict

    Args:
        user_data (dict): user data got from request

    Returns:
        dict: formatted user details
    """

    if not ("user" in user_data and user_data["user"]):
        return None
    
    user_data = user_data["user"]

    return {
        "username": "uniqueId" in user_data and user_data["uniqueId"] or "",
        "avatar_url": ('avatarMedium' in user_data and user_data['avatarMedium']) or ('avatarThumb' in user_data and user_data['avatarThumb']) or "",
        "avatar_file": f'{"uniqueId" in user_data and user_data["uniqueId"] or ""}.jpeg',
        "fullname": "nickname" in user_data and user_data["nickname"] or "",
        "bio": "signature" in user_data and user_data["signature"] or ""
    }


# >> function to get matching profile depending on a keyword
def get_matching_profiles(keyword: str, count: int=30) -> list:
    """function that fetches matching profiles for a given keyword

    Args:
        keyword (str): keyword
        count (int, optional): number of matching profiles required. Defaults to 30.

    Returns:
        list: serialized list of profiles
    """    

    profiles = []

    # get profiles with matching name:
    matching_profiles = make_request(CONFIG['rapid_api']['search_profiles_url'], {"keywords": keyword, "count":"30", "cursor":"0"})
    if not matching_profiles:
        debug(message=f"Could not get matching profiles for {keyword}", type="error", separator="\n    [xx] ")
        return []

    elif "data" not in matching_profiles or  "user_list" not in matching_profiles["data"]:
        debug(message=f"Response json is not valid for {keyword}", type="error", separator="\n    [xx] ")
        return []

    for matching_profile in matching_profiles["data"]["user_list"]:
        profiles.append(get_user_detail(matching_profile))

    return profiles


# >> downloading profile image 
def get_profile_avatar(avatar_url: str, avatar_file: str) -> None:
    """function to download avatar from user json and save in locally

    Args:
        avatar_url (dict): url from here imag is to be downloaded
        avatar_file (str): name of the file of image

    """    

    try:
        if avatar_url:
            avatar_file = os.path.join(AVATAR_FOLDER, f"{avatar_file}")

            # Download the image and save it to the local folder
            response = requests.get(avatar_url)
            with open(avatar_file, "wb") as f:
                f.write(response.content)
    except Exception as e:
        # debug(message=f"Exception wile downloading Image || {e}", type="exception", separator="\n    [xx] ")
        pass


# >> function to remove duplicate profile from list that has same username
def sanitize_matching_profiles(profiles: list, main_username:str) -> list:
    """function to remove duplicate profile from list that has same username

    Args:
        profiles (list): input list of profiles
        main_username (str): user of the main user
    Returns:
        list: list that has not duplicate profile
    """

    unique_usernames = set()
    unique_usernames.add(main_username)
    sanitized_profiles = []

    for my_dict in profiles:
        username = my_dict['username']
        if username not in unique_usernames:
            sanitized_profiles.append(my_dict)
            unique_usernames.add(username)
        # else:
        #     print(unique_usernames, username)
    return sanitized_profiles


# >> comparing if 2 images are same
def compare_avatar_old(searched_user_avatar: str, user_avatar:str ) -> float:
    """function to compare 2 images using pillow and numpy library

    Args:
        searched_user_avatar (str): image of the profiles searched
        user_avatar (str): image of the actual profile

    Returns:
        float: score of the comparison
    """

    if not user_avatar:
        return 0.0

    try:
        # Load the images to compare
        image1 = Image.open(searched_user_avatar)
        image2 = Image.open(user_avatar)

        # Resize the images to the same size
        size = (300, 300)  # Change this to the desired size
        image1 = image1.resize(size)
        image2 = image2.resize(size)

        # Calculate the difference between the two images
        diff = ImageChops.difference(image1, image2)

        # Convert the difference image to a numpy array
        diff_array = numpy.array(diff)

        # Calculate the mean of the difference image
        mean_diff = numpy.mean(diff_array)

        # Calculate the similarity as a percentage
        similarity = 100 - (mean_diff / 255) * 100

        return similarity
    except Exception as e:
        debug(message=f"Got exception while comparing images. || {e}", type="exception", separator="\n    [xx] ")
        return 0.0


# >> comparing if 2 images are same
def compare_avatar(searched_user_avatar: str, user_avatar:str ) -> float:
    """function to compare 2 images using pillow and numpy library

    Args:
        searched_user_avatar (str): image of the profiles searched
        user_avatar (str): image of the actual profile

    Returns:
        float: score of the comparison
    """

    user_avatar = os.path.join(OUTPUT_FOLDER, "avatar", user_avatar)
    searched_user_avatar = os.path.join(OUTPUT_FOLDER, "avatar", searched_user_avatar)


    if not(os.path.exists(user_avatar) and os.path.exists(searched_user_avatar)):
        return 10000000

    try:
        original_image = cv2.imread(user_avatar)
        original_image_gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        original_image_histogram = cv2.calcHist([original_image_gray], [0], None, [256], [0, 256])

        # data1 image
        searched_image = cv2.imread(searched_user_avatar)
        searched_image_gray = cv2.cvtColor(searched_image, cv2.COLOR_BGR2GRAY)
        searched_image_histogram = cv2.calcHist([searched_image_gray], [0], None, [256], [0, 256])

        c1 = 0

        # Euclidean Distance between data1 and test
        i = 0
        while i<len(original_image_histogram) and i<len(searched_image_histogram):
            c1 += (original_image_histogram[i] - searched_image_histogram[i])**2
            i += 1
        c1 = c1**(1 / 2)

        return c1.tolist()[0]
    except Exception as e:
        debug(message=f"Got exception while comparing images. || {e}", type="exception", separator="\n    [xx] ")
        return 100000


# >> function to compare 2 strings
def compare_string(str1: str, str2: str) -> float:
    """function to compare 2 strings by using fuzzy logic

    Args:
        str1 (str): first string 
        str2 (str): second string

    Returns:
        float: score of the comparison
    """
    try:
        ratio = fuzz.ratio(str1, str2)
    except Exception as e:
        debug(message=f"Got exception while comparing strings. || {e}", type="exception", separator="\n    [xx] ")
        ratio = 0
    
    return ratio


# function to compare avatar, bio and name of 2 profiles and give scores
def compare_profiles(original_profile: dict, matching_profile: dict) -> dict:
    """function to compare avatar, bio and name of 2 profiles and give scores

    Args:
        original_profile (dict): original profile
        matching_profile (dict): profile that is to be compared

    Returns:
        dict: updated matching profile with score
    """

    matching_profile["avatar_similarity"] = compare_avatar(original_profile['avatar_file'], matching_profile['avatar_file'])      # compare image
    matching_profile["name_similarity"] = compare_string(original_profile['fullname'], matching_profile['fullname'])        # compare name
    matching_profile["bio_similarity"] = compare_string(original_profile['bio'], matching_profile['bio'])       # compare bio

    # calculating score
    avatar_similarity = 1 if matching_profile["avatar_similarity"] <= CONFIG["min_similarity"]["avatar"] else 0
    name_similarity = 1 if matching_profile["name_similarity"] >= CONFIG["min_similarity"]["name"] else 0
    bio_similarity = 1 if matching_profile["bio_similarity"] >= CONFIG["min_similarity"]["bio"] else 0
    matching_profile["comparison_score"] = (avatar_similarity * CONFIG["weightage"]["avatar"]) + (name_similarity * CONFIG["weightage"]["name"]) + (bio_similarity * CONFIG["weightage"]["bio"])
    return matching_profile


# >> function that takes list of matching profiles and returns profile with max score.
def get_closest_matching_profile(matching_profiles: list) -> dict:
    """function that takes list of matching profiles and returns profile with max score.
        If two dict have same avg, then one which highest score should be selected.

    Args:
        matching_profiles (list): lis of matching profiles

    Returns:
        dict: profile with max score
    """
    try:
        # Custom sorting key function
        def sorting_key(dictionary):
            return (-dictionary["comparison_score"], dictionary["avatar_similarity"])

        # Sort the list
        sorted_data = sorted(matching_profiles, key=sorting_key)

        # Get the maximum score
        max_score = sorted_data[0]["comparison_score"]

        # Filter dictionaries with the maximum score
        filtered_data = [d for d in sorted_data if d["comparison_score"] == max_score]

        # Sort the filtered data based on age
        final_sorted_data = sorted(filtered_data, key=lambda x: x["avatar_similarity"])

        # sorted_data = sorted(matching_profiles, key=lambda d: (-int(d['comparison_score']), -int(d['avatar_similarity'])))      # sort the data by avg and score
        result = final_sorted_data[0]     # get the dictionary with highest avg and score
        return result
    except Exception as e:
        debug(message=f"Exception while getting closest match || {e}", type="exception", separator="\n     [>>] ")
        return {
            "username": f"Exception while getting closest match || {e}",
            "comparison_score": 0
        }


# >> function to save list of dict to csv
def save_csv(profiles: list, file_name: str) -> None:
    """function to save list of dict to csv

    Args:
        profiles (list): list of profiles
        file_name (str): complete path of the file to save
    """
    try:
        path = os.path.join(OUTPUT_FOLDER, "CSVs")
        if not os.path.exists(path):
            os.makedirs(path)

        # Convert the list of dictionaries to a pandas DataFrame
        df = pandas.DataFrame(profiles)

        file_name = os.path.join(path, file_name)
        # Save the DataFrame to a CSV file
        df.to_csv(file_name, index=False)
    except Exception as e:
        debug(message=f"Exception while saving data to CSV file: {file_name} || {e}", type="exception", separator="\n    [xx] ")


# >> save_json
def save_json(json_data: dict, file: str) -> None:
    try:
        # creating path for output file
        path = os.path.join(OUTPUT_FOLDER, "JSONs")
        if not os.path.exists(path):
            os.makedirs(path)

        file = os.path.join(path, file)
        with open(file, 'w') as w:
            json.dump(json_data, w, indent=4)
    except Exception as e:
        debug(message=f"Exception while saving data to JSON file: {file} || {e}", type="exception", separator="\n    [xx] ")


# >> read json
def read_json(file: str) -> dict:
    try:
        # creating path for output file
        path = os.path.join(OUTPUT_FOLDER, "JSONs")
        file = os.path.join(path, file)

        if os.path.exists(file):
            with open(file, 'r') as r:
                return json.load(r)
        else:
            debug(message=f" File not found: {file}", type="error", separator="\n [xx] ")
            return {}
    except Exception as e:
        debug(message=f"Exception while reading file: {file} || {e}", type="exception", separator="\n    [xx] ")


# >> function to get user profile and get its matching profile. Function is intended to run in multiple threads.
def get_profile_data_thread(main_profile):

    """function to get user profile and get its matching profile. Function is intended to run in multiple threads.

    Args:
        main_profile (_type_): _description_
    """
    debug(message=f"User: {main_profile} || Getting User Info and Matching profiles.", type="info", separator=f"\n    [>] ")
    try:
        # get user info
        user_profile = make_request(CONFIG['rapid_api']['user_info_url'], {"unique_id":f"@{main_profile}"})
        if not user_profile:
            debug(message=f"Could not get user info for {main_profile}", type="error", separator="\n    [xx] ")
            return

        user = get_user_detail(user_profile["data"])
        if not user:
            debug(message=f"Could not get user detail for {main_profile}", type="error", separator="\n    [xx] ")
            return

        # get profiles with matching name
        matching_profiles = []
        if user['fullname']:
            matching_profiles += get_matching_profiles(user['fullname'], count=30)

        # get profiles with matching username
        if main_profile:
            matching_profiles += get_matching_profiles(main_profile, count=30)
        
        matching_profiles = sanitize_matching_profiles(matching_profiles, main_profile)

        final_data = {
            "main_profile": user,
            "matching_profiles": matching_profiles
        }

        # Saving profiles to respective JSONs. ONLY FOR TESTING
        save_json(final_data, f"{main_profile}.json")
    except Exception as e:
        debug(message=f"Exception while getting matching profiles for user: {main_profile} || {e}", type="exception", separator="\n    [xx] ")


# >> function to download avatars. . Function is intended to run in multiple threads.
def download_avatar_thread(avatar_url: str, avatar_file: str):
    """function to download avatars. Function is intended to run in multiple threads.

    Args:
        avatar_url (dict): url from here imag is to be downloaded
        avatar_file (str): name of the file of image
    """

    try:
        if avatar_url:
            avatar_file = os.path.join(AVATAR_FOLDER, f"{avatar_file}")

            # Download the image and save it to the local folder
            response = requests.get(avatar_url, timeout=CONFIG["requests_timeout"])
            with open(avatar_file, "wb") as f:
                f.write(response.content)
    except Exception as e:
        debug(message=f"Exception wile downloading Image || {e}", type="exception", separator="\n    [xx] ")


# >> function to calculate comparison score between each matching profiles and main profile. Function is intended to run in multiple threads.
def profile_comparison(main_profile: str) -> None:
    """function to calculate comparison score between each matching profiles and main profile. Function is intended to run in multiple threads.

    Args:
        main_profile (str): username of the main_account
    """

    main_profile_data = read_json(f"{main_profile}.json")

    # get comparison score
    main_profile_data["matching_profiles"] = [ compare_profiles(main_profile_data["main_profile"], matching_profile) for matching_profile in main_profile_data["matching_profiles"] ]
    save_json(main_profile_data, f"{main_profile}.json")


# >> function where all magic happens
def main(input_file):

    # ! READ INPUT FILE 
    main_profiles = list(set(read_input(input_file)))
    debug(message=f"Total number of main profiles = {len(main_profiles)}", type="info", separator=f"\n [+] ")


    # ! LOOP THROUGH PROFILE AND GET MATCHING PROFILES AND SAVE EACH PROFILE WITH USERNAME AS JSON 
    debug(message=f"Getting Matching Profiles for each Main Profile", type="info", separator=f"\n [+] ")
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG["max_worker_count"]) as matching_profile_thread:
        matching_profile_thread.map(get_profile_data_thread, main_profiles)
    debug(message=f"Scraped all Matching Profiles for each Main Profile", type="info", separator=f"\n [+] ")


    # ! LOOP THROUGH ALL PROFILES, READ MATCHING PROFILE JSON AND DOWNLOAD IMAGE 
    debug(message=f"Collecting all avatar URLs for downloading", type="info", separator=f"\n [+] ")
    avatars = []
    for main_profile in main_profiles:
        # read profile json file
        main_profile_data = read_json(f"{main_profile}.json")

        if main_profile_data:
            avatars.append((main_profile_data["main_profile"]["avatar_url"], main_profile_data["main_profile"]["avatar_file"]))
            avatars += [ (data["avatar_url"], data["avatar_file"]) for data in main_profile_data["matching_profiles"] ]

    debug(message=f"Downloading Avatars", type="info", separator=f"\n [+] ")
    with concurrent.futures.ThreadPoolExecutor() as download_thread:
        # download_thread.map(download_avatar_thread_2, *zip(*avatars))
        download_thread.map(download_avatar_thread, *zip(*avatars))
    debug(message=f"Done Downloading Avatars", type="info", separator=f"\n [+] ")


    # ! LOOP THROUGH ALL PROFILES, READ MATCHING PROFILE JSON AND CALCULATE COMPARISON SCORE 
    debug(message=f"Starting Profile Comparisons", type="info", separator=f"\n [+] ")
    with concurrent.futures.ThreadPoolExecutor() as profile_comparison_thread:
        profile_comparison_thread.map(profile_comparison, main_profiles)
    debug(message=f"Done Profile Comparisons", type="info", separator=f"\n [+] ")


    # ! GET CLOSEST MATCHING PROFILE FOR EACH PROFILE AND GENERATE CSV 
    debug(message=f"Starting to get closest match", type="info", separator=f"\n [+] ")
    closest_matching_profiles = []

    # looping through list of usernames
    for i, main_profile in enumerate(main_profiles, start=1):
        main_profile_data = read_json(f"{main_profile}.json")
        if not 'matching_profiles' in main_profile_data:
            continue
        closest_profile = get_closest_matching_profile(main_profile_data["matching_profiles"])

        # adding closest matching profile to desired profiles list
        closest_matching_profiles.append({
            "Real Account": f"https://www.tiktok.com/@{main_profile}",
            "Fake Account Link": f"https://www.tiktok.com/@{closest_profile['username']}",
            "Percentage": closest_profile["comparison_score"],
            "Status": True if closest_profile["comparison_score"] >= CONFIG['min_fake_score'] else False
        })

        # Saving profiles to respective JSONs. ONLY FOR TESTING
        if not CONFIG["save_json"]:
            os.remove(os.path.join(OUTPUT_FOLDER, "JSONs", f"{main_profile}.json"))
    
    # saving closest matching profiles in csv
    if closest_matching_profiles:
        save_csv(closest_matching_profiles, OUTPUT_CSV_FILE)
    else:
        debug(message=f"Not closest matching profiles profiles", type="error", separator="    [xx] ")


if __name__ == '__main__':
    try:
        time_started = datetime.datetime.now()
        intro()

        # # when we are executing script
        # BASE_FOLDER = os.path.dirname(__file__)

        # get the base folder from user when we are executing executable
        while True:
            BASE_FOLDER = input("Please enter path to the project folder: ")
            if os.path.exists(BASE_FOLDER) and os.path.exists(os.path.join(BASE_FOLDER, "scraper.exe")):
                break
            print("Not a valid path.")

        # get the input file from user
        while True:
            input_file = input("Please enter input file: ")
            if os.path.exists(os.path.join(BASE_FOLDER, input_file)):
                break
            print("Not able to locate input file in project folder.")

        #  getting name of output file
        while True:
            OUTPUT_CSV_FILE = input("Please enter name of output file: ")
            if OUTPUT_CSV_FILE.endswith(".csv"):
                break
            print("File name must end with .csv")

        OUTPUT_FOLDER = os.path.join(BASE_FOLDER, "DATA")

        # Local folder where the image will be saved
        AVATAR_FOLDER = os.path.join(OUTPUT_FOLDER, 'avatar')

        # Create the folder if it does not exist
        if not os.path.exists(AVATAR_FOLDER):
            os.makedirs(AVATAR_FOLDER)

        CONFIG = read_config()
        if CONFIG:
            logger = set_logger()
            main(input_file)
        debug(message=f"Terminating Script **********\n", type="info", separator="\n  ********** ")
    except Exception as e:
        print(f"Exception in root: {e}")
    
    time_ended = datetime.datetime.now()
    total_execution_time = time_ended - time_started
    print(f"\n Total Execution Time: {total_execution_time}")
    input("\n All Task Done. Press Enter to close script ")

# pyinstaller --onefile -c --icon=tiktok.ico --add-data "venv\Lib\site-packages\pyfiglet;./pyfiglet"  scraper.py