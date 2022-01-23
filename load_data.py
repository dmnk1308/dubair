import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from helpers import *
import ast
import requests
from bs4 import BeautifulSoup as bs
import statsmodels.api as sm
from scipy.stats import halfnorm
import warnings


def load():
    url_listing = "http://data.insideairbnb.com/ireland/leinster/dublin/2021-11-07/data/listings.csv.gz"
    url_reviews = "http://data.insideairbnb.com/ireland/leinster/dublin/2021-11-07/data/reviews.csv.gz"
    listings = pd.read_csv(url_listing)
    reviews = pd.read_csv(url_reviews)
    variables_listing= ["id", "name", "last_scraped", "description", "neighborhood_overview", "host_id", "host_url", "host_name", "host_since", "host_location",
    "host_about", "host_is_superhost", "host_listings_count", "host_has_profile_picture","host_identity_verified",
    "neighbourhood_cleansed",
    "latitude",
    "longitude",
    "property_type",
    "room_type",
    "accommodates",
    "bathrooms_text",
    "bedrooms",
    "beds",
    "amenities",
    "minimum_nights",
    "maximum_nights",
    "has_availability",
    "availability_30",
    "availability_60",
    "availability_90",
    "availability_365",
    "number_of_reviews",
    "number_of_reviews_ltm", 
    "number_of_reviews_l30d", 
    "first_review",
    "last_review",
    "review_scores_rating",	 
    "review_scores_accuracy",	
    "review_scores_cleanliness",
    "review_scores_checkin	",
    "review_scores_communication",
    "review_scores_location",	
    "review_scores_value",
    "instant_bookable",
    "calculated_host_listings_count",
    "reviews_per_month",
    "host_has_profile_pic",
    'minimum_minimum_nights', 
	'maximum_minimum_nights', 
	'minimum_maximum_nights', 
	'maximum_maximum_nights', 
	'minimum_nights_avg_ntm', 
	'maximum_nights_avg_ntm',
	'calculated_host_listings_count_entire_homes', 
	'calculated_host_listings_count_private_rooms', 
    'calculated_host_listings_count_shared_rooms'] 
    # make price numeric
    price = listings["price"]
    price = price.str.replace("$","")
    price = price.str.replace(",","")
    price = price.astype(float)
    price = pd.DataFrame(price)
    price["log_price"] = np.log(price)
    price["id"] = listings["id"]
    price = price[["id", "price", "log_price"]]

    # get rid of Hotels
    hotel_filter = listings["room_type"] == "Hotel room"
    listings = listings[~hotel_filter]
    price = price[~hotel_filter]

    listings = listings.filter(variables_listing)
    reviews = reviews.filter(["listing_id", "comments", "date"])

    print("Data loaded.")

    return price, listings, reviews



def clean():
    price, listings, reviews = load()

############# CATEGORICAL VARIABLES #################

    # clean host_profile_pic
    listings["host_has_profile_pic"] = np.where(listings["host_has_profile_pic"] == "t", 1, 0)

    # clean host_location
    country_abr = pd.read_csv("https://gist.githubusercontent.com/radcliff/f09c0f88344a7fcef373/raw/2753c482ad091c54b1822288ad2e4811c021d8ec/wikipedia-iso-country-codes.csv")
    country_list = list(country_abr.iloc[:,0])
    abr_list = list(country_abr.iloc[:,1])

    listings["host_location_country"] = listings["host_location"].copy()

    for i in list(country_list):
        fil = listings["host_location"].str.contains(i, case = False, na = False)
        listings["host_location_country"][fil] = str(i)

    for i,j in enumerate(list(abr_list)):
        fil = listings["host_location"].str.contains(str(j), case = True, na = False)
        listings["host_location_country"][fil] = str(country_list[i])

    listings["host_location_country"].value_counts()

    other_filter = listings["host_location_country"].value_counts() <= 5
    other_list = list(listings["host_location_country"].value_counts().index[other_filter])

    for i, j in enumerate(other_list):
        fil = listings["host_location_country"].str.contains(j, case = True, na = False)
        listings["host_location_country"][fil] = "Others"
    listings["host_location_country"][listings["host_location_country"] == "53.357852, -6.259787"] = "Ireland"
    
    listings = listings.drop("host_location", axis = 1)

    # clean bathroom text
    na_filter = listings["bathrooms_text"].isna()
    price = price[~na_filter]
    listings = listings[~na_filter]

    bath_number = listings["bathrooms_text"].copy()
    bath_number = bath_number.str.replace("half", "0.5", case = False)
    bath_number = bath_number.str.extract('(\d+.\d|\d+)')
    listings["bath_number"] = bath_number.astype(float)

    bath_kind = listings["bathrooms_text"].copy()

    shared = bath_kind.str.contains("shared", case = False)
    private = bath_kind.str.contains("private", case = False)
    normal = ~pd.concat([shared, private], axis = 1).any(axis = 1)

    bath_kind[shared] = "Shared"
    bath_kind[private] = "Private"
    bath_kind[normal] = "Normal"

    listings["bath_kind"] = bath_kind

    listings = listings.drop("bathrooms_text", axis = 1)

    # clean hotel, hostels
    prop = listings["property_type"]
    filter_prop = prop.str.contains("hotel", case = False)
    listings = listings[~filter_prop]
    price = price[~filter_prop]

    prop = listings["property_type"]
    filter_prop = prop.str.contains("hostel", case = False)
    listings = listings[~filter_prop]
    price = price[~filter_prop]

    # clean property types
    ## sum up all properties that occur less than 10 times in "others"
    values = listings["property_type"].value_counts()
    other_list = values.where(values<=10).dropna().index

    for i, j in enumerate(other_list):
        fil = listings["property_type"].str.contains(j, case = True, na = False)
        listings["property_type"][fil] = "Others"


    # drop insignificant binary variables
    listings = listings.drop("has_availability", axis = 1)
    listings = listings.drop("instant_bookable", axis = 1)
    listings = listings.drop("host_identity_verified", axis = 1)
    listings = listings.drop("host_is_superhost", axis = 1)



####################### AMENITIES ###############################
    # load amenities
    amenities = listings["amenities"]

    # we hava a list as each cell of the amenities pd.Series. Unpack them
    amenities = amenities.apply(ast.literal_eval)
    mlb = MultiLabelBinarizer()
    am_array = mlb.fit_transform(amenities)
    am_df = pd.DataFrame(am_array, columns = mlb.classes_)

    # drop sum stuff that is too broad, too standard or to specific
    am_df = drop_col(am_df, "(Clothing storage)")
    am_df = drop_col(am_df, "(^Fast wifi.)")    

    am_df = drop_col(am_df, ["Bedroom comforts", "Bread maker","Carbon monoxide alarm",
    "Children’s dinnerware", "Drying rack for clothing", "Fireplace guards", "Fire extinguisher", 
    "Hot water kettle", "Hangers", "Iron", "Keypad", "Pocket wifi", "Mini fridge",
    "Mosquito net", "Outlet covers", "Pour-over coffee", "Portable fans",
    "Portable heater", "Portable air conditioning", "Radiant heating", "Record player", 
    "Rice maker", "Shower gel", "Ski-in/Ski-out", "Table corner guards", "Trash compactor",
    "Wine glasses", "Window guards", "Baking sheet", "Barbecue utensils", "Boat slip",
    "Cable TV","Changing table","Cleaning products","EV charger","Ethernet connection", 
    "Extra pillows and blankets", "First aid kit","Laundromat nearby", "Room-darkening shades",
    "Smart lock", "Smoke alarm", "Toaster", "Microwave", "Essentials", "Bathroom essentials", "Fire pit", 
    "Lock on bedroom door", "Hot water", "Beach essentials", "Board games", "Building staff", 
    "Cooking basics", "Dining table", "Dishes and silverware", "Host greets you", "Luggage dropoff allowed", 
    "Self check-in", "Pets allowed", "Suitable for events", "Ceiling fan"], regex = False)

    # summarize in new columns which gives the total number
    ### Kicked everything to binary

    # summarize in new columns which gives the availability
    am_df = in_one(am_df, "(.oven)|(^oven)", "Oven_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(.stove)|(^stove)", "Stoves_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(refrigerator.)|(refrigerator)|(^Freezer$)", "Refridgerator_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(body soap)", "Body_soap_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(garden or backyard)|(^backyard)|(^garden)", "Garden_backyard_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^free.*parking)|(^free.*garage)|(^free.*carport)", "Free_parking", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^paid.*parking)|(^paid.*garage)|(^paid.*carport)", "Paid_parking", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Children’s books and toys)", "Children_Entertainment", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Dedicated workspace)", "Workspace", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(conditioner)|(shampoo)", "Shampoo_Conditioner_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Gym)|(. gym)", "Gym_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(coffee machine)|(Nespresso)|(^Coffee maker)", "Coffee_machine_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Dryer)|(Paid dryer)|(^Free dryer)", "Dryer_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Washer)|(Paid washer)|(Free washer)", "Washer_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Hot tub)|(.hot tub)", "Hot_tub_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Pool)|(shared.*pool)|(private.*pool)", "Pool_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(patio or balcony)", "Patio_balcony_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Wifi)", "Wifi_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(air conditioning)", "AC_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(heating)", "heating_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Kitchen$)|(^Full kitchen$)", "Kitchen_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Lockbox$)|(^Safe$)", "Safe_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(sauna)", "Sauna_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Waterfront$)|(^Beachfront$)|(^Lake access$)", "Water_location", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(sound system)", "sound_system_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(HDTV)|(^\d\d..TV)|(^TV)", "TV_available", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^outdoor)", "Outdoor_stuff", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(game console)", "Game_consoles", regex = True, sum = False, drop = True)
    am_df = in_one(am_df, "(^Baby)|(^Crib$)|( crib$)|(^High chair$)", "Baby_friendly", regex = True, sum = False, drop = True)


    # sum up all luxury or extraordinary equipment
    am_df = in_one(am_df, ["Piano", "Ping pong table", "Kayak", "BBQ grill", "Bidet", "Bikes", "Sauna_available"], "Special_stuff", regex = False, sum = False, drop = True)

    # join amenities with listings
    listings = listings.join(am_df)
    # drop amenities columns
    listings = listings.drop("amenities", axis = 1)

    print("Data cleansed.")

    return price, listings, reviews


def impute():
    price, listings, reviews = clean()

    ### Imputation starts here

    ## very simple imputation

    # name and description, take room_type instead
    ind = listings[listings["name"].isna()]["name"].index
    listings.loc[ind, "name"] = listings.loc[ind, "room_type"]

    ind = listings[listings["description"].isna()]["description"].index
    listings.loc[ind, "description"] = listings.loc[ind, "room_type"]

    # neighbourhood-overview (=description) just neihgbourhood cleansed
    ind = listings[listings["neighborhood_overview"].isna()]["neighborhood_overview"].index
    listings.loc[ind, "neighborhood_overview"] = listings.loc[ind, "neighbourhood_cleansed"]

    # host_about
    ind = listings[listings["host_about"].isna()]["host_about"].index
    listings.loc[ind, "host_about"] = " "

    # first and last review, you might want to think about this again
    ind = listings[listings["first_review"].isna()]["first_review"].index
    listings.loc[ind, "first_review"] = listings.loc[ind, "last_scraped"]

    ind = listings[listings["last_review"].isna()]["last_review"].index
    listings.loc[ind, "last_review"] = listings.loc[ind, "last_scraped"]

    # Reviews per Month are probably zero
    ind = listings[listings["reviews_per_month"].isna()]["reviews_per_month"].index
    listings.loc[ind, "reviews_per_month"] = listings.loc[ind, "number_of_reviews"]

    # If the host_location is not given, they are probably in Ireland
    ind = listings[listings["host_location_country"].isna()]["host_location_country"].index
    listings.loc[ind, "host_location_country"] = "Ireland"


    ## Some webscraping for host-variables -> shall be the same profiles

    ind_s = listings[listings["host_name"].isna()]["host_name"].index
    rel_URL = listings.loc[ind_s, "host_url"]
    ids = listings.loc[ind_s, "host_id"]

    name = []
    id_ver = []
    for i in range(len(ind_s)):
        listings.loc[ind_s, "host_listings_count"] = len(listings[listings.host_id == ids.values[i]])
        session = requests.Session()
        html_code = session.get(rel_URL.values[i]).content
        soup = bs(html_code, "html.parser")
        name_html = soup.select("._a0kct9 ._14i3z6h")
        # the if statement is for profiles that cannot be called for any reason
        if len(name_html) == 0:
            name.append("Anonymous")
        else:
            name.append(name_html[0].text[8:])

    listings.loc[ind_s, "host_name"] = name
    listings.loc[ind_s, "host_since"] = listings.loc[ind_s, "first_review"]


    ## Now linear Models for beds and bedrooms

    # accomodates and beds are quite linear
    # So let us estimate linear models and predict, for beds
    Y = listings["beds"]
    x = listings["accommodates"]
    X = pd.DataFrame([x]).transpose()
    X = sm.add_constant(X)  # adding a constant

    # Fit model for beds
    model = sm.OLS(Y, X, missing='drop').fit()

    ind = listings[listings["beds"].isna()]["beds"].index
    x0 = listings["accommodates"][ind]
    x0 = sm.add_constant(x0)
    predictions = model.predict(x0)
    listings.loc[ind, "beds"] = round(predictions)

    # beds and bedrooms are very linear as well
    # do the same here
    Y = listings["bedrooms"]
    x = listings["beds"]
    X = pd.DataFrame([x]).transpose()
    X = sm.add_constant(X)  # adding a constant

    # Fit model for beds
    model = sm.OLS(Y, X, missing='drop').fit()

    ind = listings[listings["bedrooms"].isna()]["bedrooms"].index
    x0 = listings["beds"][ind]
    x0 = sm.add_constant(x0)
    predictions = model.predict(x0)
    listings.loc[ind, "bedrooms"] = round(predictions)


    # All those review score variables
    review_var = ['review_scores_rating', 'review_scores_accuracy', 'review_scores_cleanliness',
                  'review_scores_communication', 'review_scores_location', 'review_scores_value']
    # they look quite halfnormal
    for i in range(len(review_var)):
        ind = listings[listings[review_var[i]].isna()][review_var[i]].index
        sd = np.nanstd(listings[review_var[i]],  ddof=0)  # ML-estimator
        sd = sd - sd / (4 * len(listings[review_var[i]]))  # MLE bias corrected
        np.random.seed(123)
        fill_ind = (halfnorm.rvs(loc=0, scale=sd, size=len(ind)) * -1) + 5
        listings.loc[ind, review_var[i]] = fill_ind


    ### Binary Stuff
    rest_var = ['Bathtub', 'Bed linens', 'Breakfast', 'Cleaning before checkout', 'Dishwasher',
                'Elevator', 'Hair dryer', 'Indoor fireplace', 'Long term stays allowed',
                'Private entrance', 'Security cameras on property', 'Single level home',
                'Special_stuff', 'TV_available', 'Outdoor_stuff', 'Baby_friendly',
                'sound_system_available', 'Oven_available', 'Stoves_available',
                'Refridgerator_available', 'Body_soap_available',
                'Garden_backyard_available', 'Free_parking',
                'Paid_parking', 'Children_Entertainment', 'Workspace',
                'Shampoo_Conditioner_available', 'Gym_available',
                'Coffee_machine_available', 'Dryer_available', 'Washer_available',
                'Hot_tub_available', 'Pool_available', 'Patio_balcony_available',
                'Wifi_available', 'AC_available', 'heating_available',
                'Kitchen_available', 'Safe_available', 'Water_location', "Game_consoles"]

    for i in range(len(rest_var)):
        ind = listings[listings[rest_var[i]].isna()][rest_var[i]].index
        m = np.nanmean(listings[rest_var[i]])
        listings.loc[ind, rest_var[i]] = np.random.binomial(n=1, p=m, size=len(ind))

    if len(listings.isna().sum()[listings.isna().sum().values > 0]) == 0:
        print("Imputation done. No NaN's are left in the data.")
    else:
        print("Imputation failed. There are NaN's left; here is where:")
        print(listings.isna().sum()[listings.isna().sum().values > 0])

    # still need to drop unnecessary things again: host_id, host_url
    listings = listings.drop(["host_id", "host_url"], axis = 1)

    listings = listings.reset_index(drop = True)
    return price, listings, reviews


# Define functions used in further()
from helpers import to_dummy_single, to_dummy

def further():
    price, listings, reviews = impute()

    # binarize baths
    step1 = np.round(listings["bath_number"], 0).astype(int)
    step2 = np.where(step1 > 3, 4, step1).astype(str)
    mlb = MultiLabelBinarizer()
    am_array = mlb.fit_transform(step2)
    col = mlb.classes_
    col[-1] = "greater3"
    baths = pd.DataFrame(am_array, columns="bath_number_" + col)

    # binarize bedrooms
    step1 = np.round(listings["bedrooms"], 0).astype(int)
    step2 = np.where(step1 > 3, 4, step1).astype(str)
    mlb = MultiLabelBinarizer()
    am_array = mlb.fit_transform(step2)
    col = mlb.classes_
    col[-1] = "greater3"
    bedrooms = pd.DataFrame(am_array, columns="bedroom_number_" + col)

    listings = pd.concat([listings, baths, bedrooms], axis=1)
    listings = listings.drop(["bath_number", "bedrooms"], axis=1)

    # let's deal with the date columns and turn them into numbers which give the difference to the last_scraped date
    date_col = ["last_scraped", "host_since", "first_review", "last_review"]
    pd.to_datetime(listings["last_scraped"], yearfirst=True)
    date_df = listings.filter(date_col).apply(pd.to_datetime)
    listings["host_since"] = date_df["last_scraped"] - date_df["host_since"]
    listings["first_review"] = date_df["last_scraped"] - date_df["first_review"]
    listings["last_review"] = date_df["last_scraped"] - date_df["last_review"]
    listings = listings.drop("last_scraped", axis=1)
    # We have a timedelta object in each cell now. We should convert it into an integer using its attribute .days
    date_col = date_col[1:]
    for i in date_col:
        listings[i] = pd.Series([j.days for j in list(listings[i])])

    # we have to create dummies for the categorical variables in order to use them for models like RandomForests, Ridge,...
    cat_col = ["neighbourhood_cleansed", "property_type", "room_type", "host_location_country", "bath_kind"]

    listings = to_dummy(listings, cat_col, cat_col)

    print("Further Modifications are done.")
    return price, listings, reviews

def string_osm_data():
    price, listings, reviews = further()

    # lengths of text columns
    listings["name_length"] = listings["name"].apply(lambda x: len(x))
    listings["description_length"] = listings["description"].apply(lambda x: len(x))
    listings["neighborhood_overview_length"] = listings["neighborhood_overview"].apply(lambda x: len(x))
    listings["host_about_length"] = listings["host_about"].apply(lambda x: len(x))

    # read in pre-created frames
    listings_reviews = pd.read_csv("text_data/listings_reviews.csv")
    host_sent = pd.read_csv("text_data/host_sent.csv")
    host_name = pd.read_csv("text_data/host_name.csv")
    listings_reviews = listings_reviews.drop(listings_reviews.columns[0], axis=1)
    host_sent = host_sent.drop(host_sent.columns[0], axis=1)
    host_name = host_name.drop(host_name.columns[0], axis=1)

    # add to listings
    listings = pd.merge(listings, listings_reviews, on="id", how="left")
    listings = pd.merge(listings, host_sent, on="id", how="left")
    listings = pd.concat([listings, host_name], axis=1)

    # drop text columns
    listings = listings.drop(["name", "description", "neighborhood_overview", "host_name", "host_about"], axis = 1)

    # Imputation, means
    listings["prop_of_eng_reviews"].fillna(listings["prop_of_eng_reviews"].mean(), inplace=True)
    listings["mean_compound"].fillna(listings["mean_compound"].mean(), inplace=True)
    listings["mean_negativity"].fillna(listings["mean_negativity"].mean(), inplace=True)
    listings["mean_neutrality"].fillna(listings["mean_neutrality"].mean(), inplace=True)
    listings["mean_positivity"].fillna(listings["mean_positivity"].mean(), inplace=True)
    listings["mean_review_length"].fillna(listings["mean_review_length"].mean(), inplace=True)
    listings["prop_of_neg_comp"].fillna(listings["prop_of_neg_comp"].mean(), inplace=True)
    listings["most_neg_compound"].fillna(listings["most_neg_compound"].mean(), inplace=True)
    listings["most_pos_compound"].fillna(listings["most_pos_compound"].mean(), inplace=True)

    # OSM
    listings_osm = pd.read_csv("StreetData.csv")
    listings_osm = listings_osm.drop(listings_osm.columns[0], axis=1)

    listings = pd.merge(listings, listings_osm, on="id", how="left")

    print("Text and Open Street Data generated.")

    return price, listings, reviews

def load_data(image_data = False, drop_id = True):
    print('-'*30)
    print('Loading data...')
    print('-'*30)
    price, listings, reviews = string_osm_data()

    if image_data:
        img_df = pd.read_csv("data/img_info.csv")
        #img_df = img_df.drop(img_df.columns[0], axis = 1)
        means = img_df.mean(axis = 0)
        mean_brightness = means[2]
        mean_contrast = means[3]
        listings = listings.merge(img_df, how = "left", on = "id")
        room_cols = ["no_img_bathroom","no_img_bedroom","no_img_dining","no_img_hallway","no_img_kitchen","no_img_living","no_img_others"] #"no_img_balcony",
        listings["count"] = listings["count"].fillna(0)
        listings["brightness"] = listings["brightness"].fillna(mean_brightness)
        listings["contrast"] = listings["contrast"].fillna(mean_contrast)
        listings[room_cols] = listings[room_cols].fillna(0)
        print("Image data loaded.")

    if drop_id:
        listings = listings.drop("id", axis = 1)

    print("Have fun implementing your models.")
    return price, listings, reviews


def load_selected_data():
    print('-'*30)
    print('Selecting Features data...')
    print('-'*30)

    price, listings, reviews = load_data(image_data = True, drop_id = True)

    # t-tests

    # get binary variables
    bin_col = [col for col in listings if np.isin(listings[col].unique(), [0, 1]).all()]

    stats_val = []
    p_val = []
    names = []

    p = price["log_price"].reset_index()["log_price"]
    for i in bin_col:
        t_Test(listings[i], p, stats_val, p_val, names)
    
    p_val_sig = []
    for x in p_val:
        p_val_sig.append(x < 0.05)
    
    insig = [x for x, y in zip(names, p_val_sig) if y == False]
    print("Due to insignificant t-tests we dropped:")
    print(insig)

    if len(insig) > 0:
        listings = listings.drop(insig, axis = 1)

    # F-Tests
    # def is_cat(col_df):
    #     ints = all(col_df % 1 == 0)
    #     lengths = 2 < len(col_df.unique()) < 6
    #     if ints & lengths:
    #        r = True
    #     else:
    #         r = False

    #     return r
    
    # cats_check = []
    # for i in range(listings.shape[1]):
    #     cats_check.append(is_cat(listings.iloc[:, i]))
    
    # cat_col = listings.columns[cats_check]

    # stats_val = []
    # p_val = []
    # names = []

    # for i in cat_col:
    #     krus_test(listings[i], p, stats_val, p_val, names)
    
    # p_val_sig = []
    # for x in p_val:
    #     p_val_sig.append(x < 0.05)

    # insig = [x for x, y in zip(names, p_val_sig) if y == False]
    # print("Due to insignificant t-tests we dropped:")
    # print(insig)

    # if len(insig) > 0:
    #     listings = listings.drop(insig, axis = 1)

    return price, listings, reviews
