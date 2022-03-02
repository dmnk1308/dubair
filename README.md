This Repo contains several files and folders. In the following a short description is given for the most relevant parts.
In general - the files in the main directory contain the most relevant code for the analysis (Data processing, Models,...)
The "load_data.py" script contains the class which handles the data loading process with several transformations


# Technical folders or files
.idea, TabNet_GS_logs, __pychache__, .DS_Store and .gitignore 


# Folders:
TabNet_selected - gridsearch, model, histories
TabNet_correlated - gridsearch, model, histories
archive - files not used anymore for several reasons
data - originally downloaded data and image variables
img_models - further folders for different image models with saved models, checkpoints and data
munich - notebooks and csv's concerning munich prediction
pcas - PCA plots for Paper
plots - Plots mainly used for Paper
text_data - saved csv's used for load_data.py as well needed Files within Text_Analysis.ipynb
xgBoost_models - results and models 

# Data generating and similar:
- Imputation_New.ipynb (looking insight variables where imputations were needed)
- OSM.ipynb (work on spatial data)
- Text_Analysis.ipynb (work on text variables)
- image_scraping.ipynb (only used for scraping images)


# Feature Selection: 
-feature_selection.ipynb


# Models including grid searches:
- CompoundModel.ipynb
- RoomModel.ipynb
- TabNet_GS_fold_Shap.ipynb (uncorrelated features)
- TabNet_GS_fold_Shap_all.ipynb (correlated features)
- image_price.ipynb
- xgBoost.ipynb


# File holding interim results
- Price.csv (for load_data.py)
- StreetData.csv
- grid_results_priceimage.csv (outcome of image_price.ipynb)
- labels_raw.json (labels of scraped images)


# Helper files:
- PCA.ipynb (used for experimenting with PCAs during feature_selection.ipynb)
- helpers.py (functions used in several scripts)
- helpers_image_classification.py (functions for image handling in RoomModel.ipynb and image_price.ipynb)
- sentiment_dictionary.csv (NLTK, for Text_Analysis.ipynb)


# Content-making for Paper
- PCA_Paper.ipynb
- plot_tables_paper.ipynb
