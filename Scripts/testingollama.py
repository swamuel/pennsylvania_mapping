import pandas as pd
import ollama

csv = r"G:\QGIS DAta\FemaData\File for testing mistral\FEMA_NRI.csv"
# 1. Load the file
df = pd.read_csv(csv)  # or pd.read_excel(...)

# 2. Pull out the pieces that describe the file
summary = f"""
Columns: {', '.join(df.columns)}
Shape: {df.shape[0]} rows, {df.shape[1]} columns
Dtypes:
{df.dtypes.to_string()}

Sample rows:
{df.head(5).to_string()}

Data File:
{csv}
"""
print (summary)

prompt = f"""Here is metadata about a dataset:

{summary}

I need you to generate a 2-3 sentance summary of this dataset. 
Can you focus on what the content of the file is rather than the record or row count. Draw context from the file name, the same and the datatypes. 
Avoid using Partial or suggestions, like "The file name suggests"
Avoid suggested usage of the data.
Write this like someone browsing a would know what it holds.

When looking at a files name it might look like FEMA_NRI.csv this is intentionally named to be the data source, and the source dataset.
in this example this dataset comes from FEMA's Nationl Risk Index db

A good example would be:
This dataset is a compilation of hazard information, specifically related to Avalanches, Coastal Flooding, Cold Waves, Drought, and Earthquakes.
  Each row in the file represents a distinct hazard event with attributes such as start and end years, frequency model, impact on building, population, and agriculture, period of record, and version number. 
 It's intended for use in analyzing and understanding various natural hazards over different time periods.
 
 DO not put the name of the file in you description
"""

# 4. Call the model
response = ollama.chat(
    model="mistral:7b",
    messages=[{"role": "user", "content": prompt}]
)

# 5. Print the result
print(response["message"]["content"])