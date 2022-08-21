import streamlit as st
from PIL import Image
import os
import enchant
from textblob import TextBlob
import language_tool_python  
import requests
import pandas as pd

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

import time

from abydos.phonetic import Soundex, Metaphone, Caverphone, NYSIIS

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# image to text API authentication
subscription_key_imagetotext = "1780f5636509411da43040b70b5d2e22"
endpoint_imagetotext = "https://prana-------------v.cognitiveservices.azure.com/"
computervision_client = ComputerVisionClient(endpoint_imagetotext, CognitiveServicesCredentials(subscription_key_imagetotext))

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# text correction API authentication
api_key_textcorrection = "7aba4995897b4dcaa86c34ddb82a1ecf"
endpoint_textcorrection = "https://api.bing.microsoft.com/v7.0/SpellCheck"

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

my_tool = language_tool_python.LanguageTool('en-US')  

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# method for extracting the text
def image_to_text(path):
    read_image = open(path, "rb")
    read_response = computervision_client.read_in_stream(read_image, raw=True)
    read_operation_location = read_response.headers["Operation-Location"]
    operation_id = read_operation_location.split("/")[-1]

    while True:
        read_result = computervision_client.get_read_result(operation_id)
        if read_result.status.lower() not in ['notstarted', 'running']:
            break
        time.sleep(5)

    text =[]
    if read_result.status == OperationStatusCodes.succeeded:
        for text_result in read_result.analyze_result.read_results:
            for line in text_result.lines:
                text.append(line.text)
    
    return" ".join(text)

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# method for finding the spelling accuracy
def spelling_accuracy(extracted_text):
    spell_corrected  = TextBlob(extracted_text).correct()
    return ((len(extracted_text) - (enchant.utils.levenshtein(extracted_text, spell_corrected)))/(len(extracted_text)+1))*100

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# method for gramatical accuracy
def gramatical_accuracy(extracted_text):
    spell_corrected  = TextBlob(extracted_text).correct()
    correct_text = my_tool.correct(spell_corrected)  
    extracted_text_set = set(spell_corrected.split(" "))
    correct_text_set = set(correct_text.split(" "))
    n= max(len(extracted_text_set - correct_text_set), len( correct_text_set - extracted_text_set))
    return ((len(spell_corrected) - n )/(len(spell_corrected)+1))*100

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# percentage of corrections 
def percentage_of_corrections(extracted_text):
    data = {'text': extracted_text}
    params = {
        'mkt':'en-us',
        'mode':'proof'
        }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Ocp-Apim-Subscription-Key': api_key_textcorrection,
        }
    response = requests.post(endpoint_textcorrection, headers=headers, params=params, data=data)
    json_response = response.json()
    return len(json_response['flaggedTokens'])/len(extracted_text.split(" "))*100
    
# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------''' 

# percentage of phonetic accuracy
def percentage_of_phonetic_accuraccy(extracted_text: str):
    soundex = Soundex()
    metaphone = Metaphone()
    caverphone = Caverphone()
    nysiis = NYSIIS()
    spell_corrected  = TextBlob(extracted_text).correct()
    
    extracted_text_list = extracted_text.split(" ")
    extracted_phonetics_soundex = [soundex.encode(string) for string in extracted_text_list]
    extracted_phonetics_metaphone = [metaphone.encode(string) for string in extracted_text_list]
    extracted_phonetics_caverphone = [caverphone.encode(string) for string in extracted_text_list]
    extracted_phonetics_nysiis = [nysiis.encode(string) for string in extracted_text_list]
    
    extracted_soundex_string = " ".join(extracted_phonetics_soundex)
    extracted_metaphone_string = " ".join(extracted_phonetics_metaphone)
    extracted_caverphone_string = " ".join(extracted_phonetics_caverphone)
    extracted_nysiis_string = " ".join(extracted_phonetics_nysiis)
    
    
    spell_corrected_list = spell_corrected.split(" ")
    spell_corrected_phonetics_soundex = [soundex.encode(string) for string in spell_corrected_list]
    spell_corrected_phonetics_metaphone = [metaphone.encode(string) for string in spell_corrected_list]
    spell_corrected_phonetics_caverphone = [caverphone.encode(string) for string in spell_corrected_list]
    spell_corrected_phonetics_nysiis = [nysiis.encode(string) for string in spell_corrected_list]
    
    
    spell_corrected_soundex_string = " ".join(spell_corrected_phonetics_soundex)
    spell_corrected_metaphone_string = " ".join(spell_corrected_phonetics_metaphone)
    spell_corrected_caverphone_string = " ".join(spell_corrected_phonetics_caverphone)
    spell_corrected_nysiis_string = " ".join(spell_corrected_phonetics_nysiis)

    soundex_score = (len(extracted_soundex_string)-(enchant.utils.levenshtein(extracted_soundex_string, spell_corrected_soundex_string)))/(len(extracted_soundex_string)+1)
    # print(spell_corrected_soundex_string)
    # print(extracted_soundex_string)
    # print(soundex_score)
    metaphone_score = (len(extracted_metaphone_string)-(enchant.utils.levenshtein(extracted_metaphone_string, spell_corrected_metaphone_string)))/(len(extracted_metaphone_string)+1)
    # print(metaphone_score)
    caverphone_score = (len(extracted_caverphone_string)-(enchant.utils.levenshtein(extracted_caverphone_string, spell_corrected_caverphone_string)))/(len(extracted_caverphone_string)+1)
    # print(caverphone_score)
    nysiis_score = (len(extracted_nysiis_string)-(enchant.utils.levenshtein(extracted_nysiis_string, spell_corrected_nysiis_string)))/(len(extracted_nysiis_string)+1)
    # print(nysiis_score)
    return ((0.5*caverphone_score + 0.2*soundex_score + 0.2*metaphone_score + 0.1 * nysiis_score))*100

#'''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------''' 

def get_feature_array(path: str):
    feature_array = []
    extracted_text = image_to_text(path)
    feature_array.append(spelling_accuracy(extracted_text))
    feature_array.append(gramatical_accuracy(extracted_text))
    feature_array.append(percentage_of_corrections(extracted_text))
    feature_array.append(percentage_of_phonetic_accuraccy(extracted_text))
    return feature_array

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------''' 


def generate_csv(folder : str, label : int, csv_name : str):
    arr = []
    for image in os.listdir(folder):
        path = os.path.join(folder,image)
        feature_array = get_feature_array(path)
        feature_array.append(label)
        # print(feature_array)
        arr.append(feature_array)
        print(feature_array)
    print(arr)
    pd.DataFrame(arr, columns=["spelling_accuracy", "gramatical_accuracy", " percentage_of_corrections", "percentage_of_phonetic_accuraccy", "presence_of_dyslexia"]).to_csv("test1.csv")
    
# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

def score(input):
    if input[0] <= 96.40350723266602:
        var0 = [0.0, 1.0]
    else:
        if input[1] <= 99.1046028137207:
            var0 = [0.0, 1.0]
        else:
            if input[2] <= 2.408450722694397:
                if input[2] <= 1.7936508059501648:
                    var0 = [1.0, 0.0]
                else:
                    var0 = [0.0, 1.0]
            else:
                var0 = [1.0, 0.0]
    return var0

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# deploying the model

st.title("Dyslexia Detection Using Handwriting Samples")
st.write("This is a simple web app that works based on machine learning techniques. This application can predict the presence of dyslexia from the handwriting sample of a person.")
image = st.file_uploader("Upload the handwriting sample that you want to test", type=["png", "jpg", "jpeg"])

if image is not None:
    st.write("please review the image selected")
    st.write(image.name)
    image_uploaded = Image.open(image)
    image_uploaded.save("temp.jpg")
    st.image(image_uploaded, width=224)
    
    
if st.button("Predict", help="click after uploading the correct image"):
    try:
        feature_array = get_feature_array("temp.jpg")
        result = score(feature_array)
        if result[0] == 1:
            st.write("from the tests on this handwriting sample there is very slim chance that this person is sufferning from dyslexia or dysgraphia")
        else:
            st.write("from the tests on this handwriting sample there is very high chance that this person is sufferning from dyslexia or dysgraphia")
    except:
        st.write("something went wrong at the server end please refresh the application and try again")
        
    # feature_array = get_feature_array("temp.jpg")
    # result = score(feature_array)
    # if result[0] == 1:
    #     st.write("from the tests on this handwriting sample there is very slim chance that this person is sufferning from dyslexia or dysgraphia")
    # else:
    #     st.write("from the tests on this handwriting sample there is very high chance that this person is sufferning from dyslexia or dysgraphia")