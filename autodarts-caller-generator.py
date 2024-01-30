import os
from pathlib import Path
import platform
import argparse
import glob
import shutil
import csv
import re
import codecs
import logging
from google.cloud import texttospeech
from boto3 import Session
from contextlib import closing
import zipfile

plat = platform.system()

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
sh.setFormatter(formatter)
logger=logging.getLogger()
logger.handlers.clear()
logger.setLevel(logging.INFO)
logger.addHandler(sh)


VERSION = '1.0.3'

DEFAULT_MAX_RETRIES = 3

TEMPLATE_FILE_EXTENSION = '.csv'
TEMPLATE_FILE_ENCODING = 'utf-8-sig'
OUTPUT_FILE_EXTENSION = '.mp3'
OUTPUT_ARCHIVE_EXTENSION = 'zip'
SERVICE_PROVIDERS = ['google', 'amazon']




def setup_environment():
    service = display_menu("Select a provider: ", SERVICE_PROVIDERS)
    if service == 'amazon':
        setup_environment_amazon()
    elif service == 'google':
        setup_environment_google()
    return service
def setup_environment_amazon():
    user_home = os.environ.get('USERPROFILE') or os.environ.get('HOME')
    credential_path = os.path.join(user_home, '.aws', 'credentials')
    config_path = os.path.join(user_home, '.aws', 'config')

    if not os.path.isfile(credential_path) or not os.access(credential_path, os.R_OK):
        raise ValueError(f"The file {credential_path} does not exist or is not readable.")
    if not os.path.isfile(config_path) or not os.access(config_path, os.R_OK):
        raise ValueError(f"The file {config_path} does not exist or is not readable.")
def setup_environment_google():
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        path_to_credential_file = None
        while path_to_credential_file is None:
            path = input("Please enter full path to 'text-to-speech-key.json' / credential-file: ")
            if os.path.isfile(path):
                if os.access(path, os.R_OK):
                    path_to_credential_file = path
                else:
                    raise ValueError("The file exists but is not readable. Please try again.")
            else:
                raise ValueError("The file does not exist. Please try again.")

        # unix -> export GOOGLE_APPLICATION_CREDENTIALS=Pfad/zu/Ihrer/Datei/text-to-speech-key.json
        # windows -> setx GOOGLE_APPLICATION_CREDENTIALS "Pfad\zu\Ihrer\Datei\text-to-speech-key.json"
        if platform.system() == "Windows":
            os.system(f'setx GOOGLE_APPLICATION_CREDENTIALS "{path_to_credential_file}"')
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path_to_credential_file
        else:
            os.system(f'export GOOGLE_APPLICATION_CREDENTIALS={path_to_credential_file}')
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path_to_credential_file


def int_dialog(question, default = 0):
    while True:
        try:
            user_input = input(question)
            if user_input == '':
                user_input = default
            user_input = int(user_input)
            if user_input >= 0:
                return user_input
            else:
                raise ValueError
        except ValueError:
            print("Invalid input. Please enter a valid integer >= 0")
def binary_dialog(question, default = 'no'):
    while True:
        user_input = input(question).lower()
        if user_input == '':
            user_input = default

        if user_input == 'yes':
            return True
        elif user_input == 'no':
            return False
        else:
            print("Invalid input. Please respond with 'yes' or 'no'.")
def display_menu(text, options):
    if not options:
        raise ValueError("No options provided.")
     
    for i, option in enumerate(options, start=1):
        print(f"{i}. {option}")

    selection = -1
    while not(1 <= selection <= len(options)):
        try:
            selection = int(input(text))
            if not(1 <= selection <= len(options)):
                print("Invalid selection, please try again.")
        except ValueError:
            print("Invalid selection, please try again.")

    return options[selection - 1]

def list_template_files():
    path = os.path.join(TEMPLATES_PATH, f'*-*-v*{TEMPLATE_FILE_EXTENSION}')
    # path = "\\\\192.168.0.121\\projects\\autodarts-caller\\*-*-v*.csv"
    if path.startswith('\\'): 
        path = f"\{path}"
    return glob.glob(path)
def choose_template_file():
    template_files = list_template_files()
    return display_menu("Select a template file to use: ", template_files)
def extract_language_code(template_file_path):
    match = re.search(r'([a-z]{2}-[A-Z]{2})-v\d+(-raw)?\.csv$', template_file_path)
    if match:
        return match.group(1)
    return None

def choose_generation_path():
    while True:
        save_path = input("Please enter a generation path: ")
        if os.path.exists(save_path):
            if os.access(save_path, os.W_OK):
                return save_path
            else:
                print("The path exists but is not writable. Please try again.")
        else:
            print("The path does not exist. Please try again.")

def list_voice_names(provider, language_code):
    if provider == 'amazon':
        return list_amazon_voice_names(language_code)
    elif provider == 'google':
        return list_google_voice_names(language_code)
def list_amazon_voice_names(language_code):   
    # Create a client using the credentials and region defined in the [autodarts-caller] section of the AWS credentials file (~/.aws/credentials).
    # profile_name="autodarts-caller"
    session = Session()
    client = session.client("polly")

    voices = client.describe_voices(
            # 'en-GB'
            LanguageCode=language_code,
            Engine='neural'
        )
    # print(voices)
    
    results = []  
    for voice in voices['Voices']:
        voice_entry = voice['Name'] + "-" + voice['Gender']
        results.append(voice_entry)
    return results
def list_google_voice_names(language_code):
    client = texttospeech.TextToSpeechClient()

    # Performs the list voices request
    voices = client.list_voices(language_code=language_code)

    results = []  
    for voice in voices.voices:

        voice_entry = voice.name 

        # Display the supported language codes for this voice. Example: "en-US"
        # for language_code in voice.language_codes:
        #     voice_entry += "-" + language_code
        # # voice.natural_sample_rate_hertz

        ssml_gender = texttospeech.SsmlVoiceGender(voice.ssml_gender)

        # Display the SSML Voice Gender
        voice_entry += "-" + ssml_gender.name

        results.append(voice_entry)
    return results
def choose_voice_name(provider, voices):
    return display_menu(f"Select a {provider}-voice to use: ", voices)

def read_generation_keys(template_file):
    keys = []
    with codecs.open(template_file, 'r', encoding=TEMPLATE_FILE_ENCODING) as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=';')
        for row in csv_reader:
            keys.append(row[0])
    return keys
def restructure_generated_files(generation_path):
    archive_name = os.path.basename(generation_path)
    archive_dir = os.path.dirname(generation_path)

    # Liste aller Dateien und Ordner im gegebenen Pfad
    files_and_folders = os.listdir(generation_path)

    # Temporärer Ordner zum Speichern der Dateien und Ordner vor dem Zippen
    temp_dir = os.path.join(archive_dir, "temp")

    # Erstelle den temporären Ordner, wenn er nicht existiert
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Verschieben Sie alle Dateien und Ordner in den temporären Ordner
    for item in files_and_folders:
        shutil.move(os.path.join(generation_path, item), temp_dir)

    # Erstellen Sie das ZIP-Archiv aus dem temporären Ordner
    shutil.make_archive(os.path.join(archive_dir, archive_name), OUTPUT_ARCHIVE_EXTENSION, temp_dir)

    # Verschieben Sie alle Dateien und Ordner zurück in den ursprünglichen Ordner
    for item in os.listdir(temp_dir):
        shutil.move(os.path.join(temp_dir, item), generation_path)

    # Löschen Sie den temporären Ordner
    shutil.rmtree(temp_dir)
    # Löscht den Ursprungsordner
    shutil.rmtree(generation_path)


def extract_nested_zip(outer_zip_path, inner_zip_filename, extract_path):
    # Öffne die äußere Zip-Datei
    with zipfile.ZipFile(outer_zip_path, 'r') as outer_zip:
        # Extrahiere die innere Zip-Datei
        inner_zip_data = outer_zip.read(inner_zip_filename)
        
        # Erstelle eine temporäre Datei für die innere Zip-Datei
        temp_inner_zip_path = os.path.join(extract_path, 'temp_inner.zip')
        with open(temp_inner_zip_path, 'wb') as temp_inner_zip:
            temp_inner_zip.write(inner_zip_data)
        
        # Öffne die innere Zip-Datei
        with zipfile.ZipFile(temp_inner_zip_path, 'r') as inner_zip:
            # Finde den Namen des inneren Ordners
            inner_folder_name = inner_zip.namelist()[0].split('/')[0]
            
            # Extrahiere nur die Dateien aus dem inneren Ordner in das Zielverzeichnis
            extracted_files_count = 0
            for inner_file in inner_zip.namelist():
                if inner_file.startswith(inner_folder_name + '/'):
                    print("copy previous: " + inner_file)
                    inner_zip.extract(inner_file, extract_path)
                    extracted_files_count += 1

        # Lösche die temporäre innere Zip-Datei
        os.remove(temp_inner_zip_path)
        return extracted_files_count
def generate(provider, template_file, language_code, voice_name, raw_mode):
    generation_path = GENERATION_PATH
    if raw_mode:
        generation_path = GENERATION_RAW_PATH

    os.makedirs(generation_path, exist_ok=True)
    if os.access(generation_path, os.W_OK) == False:
        raise FileNotFoundError(f"{generation_path} is not writeable")

    voice_name_path = voice_name
    if not voice_name.lower().startswith(language_code.lower()):
        voice_name_path = language_code + '-' + voice_name

    generation_path_main = os.path.join(generation_path, voice_name_path)

    version_counter = 1
    if os.path.exists(f"{generation_path_main}.{OUTPUT_ARCHIVE_EXTENSION}"):     
        while 1: 
            version_counter += 1
            version = f"{generation_path_main}-v{version_counter}.{OUTPUT_ARCHIVE_EXTENSION}"
            if not os.path.exists(version):
                generation_path_main = f"{generation_path_main}-v{version_counter}"
                break
            else:
                current_version_full_path = version
            
    os.makedirs(generation_path_main, exist_ok=True)
    if os.access(generation_path_main, os.W_OK) == False:
        raise FileNotFoundError(f"{generation_path_main} is not writeable")

    generation_path = generation_path_main
    if not raw_mode:
        # add template-file to generation-path
        template_file = shutil.copy(template_file, generation_path_main)

        generation_path = os.path.join(generation_path_main, voice_name_path)
        if version_counter > 1:
            generation_path = f"{generation_path}-v{version_counter}"
        os.makedirs(generation_path, exist_ok=True)
        if os.access(generation_path, os.W_OK) == False:
            raise FileNotFoundError(f"{generation_path} is not writeable")

        # grab existing files of current/previous version and put it in new version`s folder
        generation_start_index = 0
        use_previous_version = False
        if version_counter > 1:
            use_previous_version = binary_dialog(f"Do you want to generate only new keys (Default: yes): ", default='yes')
        if use_previous_version :
            inner_zip = os.path.basename(current_version_full_path)
            generation_start_index = extract_nested_zip(current_version_full_path, inner_zip, generation_path)
            print(f"Copied {generation_start_index} files from previous version: {current_version_full_path}")
            generation_start_index = generation_start_index - 1
               
            directory, ext = os.path.splitext(inner_zip)
            
            # Define the path of the current directory
            current_directory = os.path.join(generation_path, directory)

            # Define the path of the parent directory
            parent_directory = os.path.dirname(current_directory)

            # Iterate through the current directory and move all files to the parent directory
            for file in os.listdir(current_directory):
                file_path = os.path.join(current_directory, file)
                if os.path.isfile(file_path):
                    print("move previous: " + file)
                    destination_path = os.path.join(parent_directory, file)
                    shutil.move(file_path, destination_path)
            
            # Remove parent directory
            os.rmdir(current_directory)
            # shutil.rmtree(parent_directory)



    keys = read_generation_keys(template_file)

    # Remove gender-suffix
    voice_name = voice_name.rpartition("-")[0]

    errors = 0
    if provider == 'amazon':
        errors = generate_amazon(keys, generation_path, language_code, voice_name, raw_mode, generation_start_index)
    elif provider == 'google':
        errors = generate_google(keys, generation_path, language_code, voice_name, raw_mode, generation_start_index)

    if not raw_mode:
        # Erstellen Sie die ZIP-Datei
        # Der Name des zu erstellenden Archivs (ohne .zip Erweiterung)
        archive_name = os.path.basename(generation_path)

        # Der Pfad, in dem das Archiv erstellt wird
        archive_dir = os.path.dirname(generation_path)

        # Erstellen Sie die ZIP-Datei
        shutil.make_archive(os.path.join(archive_dir, archive_name), OUTPUT_ARCHIVE_EXTENSION, archive_dir, archive_name)

        # Löscht den Ursprungsordner
        shutil.rmtree(generation_path)

        restructure_generated_files(generation_path_main)

    print(f"Generation finished with {errors} errors")
def generate_amazon(keys, generation_path, language_code, language_name, raw_mode, index):
    # Create a client using the credentials and region defined in the [default] section of the AWS credentials file (~/.aws/credentials).
    # profile_name="autodart-caller"
    session = Session()
    client = session.client("polly")

    errors = 0
    print(f"Generating {len(keys[index:])} sounds:")
    for key_index, key in enumerate(keys[index:], start=index):
        print(f"{key_index}) {key}")

        tries = 1
        success = False
        while not success and tries <= MAX_RETRIES:
            tries += 1
            try:     
                response = client.synthesize_speech(
                    Text=key, 
                    OutputFormat="mp3", 
                    VoiceId=language_name,
                    Engine='neural',
                    SampleRate='24000'
                    )

                # Access the audio stream from the response
                if "AudioStream" in response:
                        # Note: Closing the stream is important because the service throttles on the
                        # number of parallel connections. Here we are using contextlib.closing to
                        # ensure the close method of the stream object will be called automatically
                        # at the end of the with statement's scope.
                        with closing(response["AudioStream"]) as stream:
                            file_output = f"{key}{OUTPUT_FILE_EXTENSION}"
                            if not raw_mode:
                                # BL-00001_0_48k_stereo.mp3
                                file_output = f"AM-{str(key_index).zfill(5)}_{key_index}_mono{OUTPUT_FILE_EXTENSION}"

                            output_file_path = os.path.join(generation_path, file_output)

                            with open(output_file_path, "wb") as file:
                                file.write(stream.read())   
                            success = True 
            except Exception as e:
                print(str(e))
                if tries > MAX_RETRIES:
                    errors += 1            
    return errors   
def generate_google(keys, generation_path, language_code, language_name, raw_mode, index):
    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Build the voice request, select the language code ("en-US") and the ssml voice gender ("neutral")
    # ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL, 
    voice = texttospeech.VoiceSelectionParams(
        # ex: "en-US"
        language_code=language_code, 
        # ex: "en-AU-Wavenet-D"
        name=language_name
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        sample_rate_hertz=44100,
        # https://cloud.google.com/text-to-speech/docs/audio-profiles?hl=de
        effects_profile_id=["large-home-entertainment-class-device"],
    )

    errors = 0
    print(f"Generating {len(keys[index:])} sounds:")
    for key_index, key in enumerate(keys[index:], start=index):
        print(f"{key_index}) {key}")

        tries = 1
        success = False
        while not success and tries <= MAX_RETRIES:
            tries += 1
            try:
                # Set the text input to be synthesized
                synthesis_input = texttospeech.SynthesisInput(text=key)

                # Perform the text-to-speech request on the text input with the selected
                # voice parameters and audio file type
                response = client.synthesize_speech(
                    input=synthesis_input, 
                    voice=voice, 
                    audio_config=audio_config
                )

                file_output = f"{key}{OUTPUT_FILE_EXTENSION}"
                if not raw_mode:
                    # BL-00001_0_48k_stereo.mp3
                    file_output = f"GO-{str(key_index).zfill(5)}_{key_index}_mono{OUTPUT_FILE_EXTENSION}"

                output_file_path = os.path.join(generation_path, file_output)

                # The response's audio_content is binary.
                with open(output_file_path, "wb") as out:
                    # Write the response to the output file.
                    out.write(response.audio_content)
                success = True
            except Exception as e:
                print(str(e))
                if tries > MAX_RETRIES:
                    errors += 1    
    return errors






if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    
    ap.add_argument("-TP", "--templates_path", required=True, help="Absolute path to your templates")
    ap.add_argument("-GP", "--generation_path", required=True, help="Absolute path to your generation path")
    ap.add_argument("-GRP", "--generation_raw_path", required=True, help="Absolute path to your generation-raw path")
    ap.add_argument("-MR", "--max_retries", type=int, default=DEFAULT_MAX_RETRIES, required=False, help="Maximum retry-count for an entry")
    ap.add_argument("-DEB", "--debug", type=int, choices=range(0, 2), default=False, required=False, help="If '1', the application will output additional information")
    args = vars(ap.parse_args())

    TEMPLATES_PATH = Path(args['templates_path'])
    GENERATION_PATH = Path(args['generation_path'])
    GENERATION_RAW_PATH = Path(args['generation_raw_path'])
    MAX_RETRIES = args['max_retries']
    DEBUG = args['debug']

    osType = plat
    osName = os.name
    osRelease = platform.release()
    print('\r\n', '')
    print('##########################################', '')
    print('       WELCOME TO AUTODARTS-CALLER-GENERATOR', '')
    print('##########################################', '')
    print('VERSION: ', VERSION, '')
    print('RUNNING OS: ' + osType + ' | ' + osName + ' | ' + osRelease, '')
    print('DONATION: bitcoin:bc1q8dcva098rrrq2uqhv38rj5hayzrqywhudvrmxa', '')
    print('\r\n', '')


    # Procedure:
    # 0) Which provider would you like to use?
    # 1) Which template would you like to work with?
    # 2) Should it be generated in 'raw' mode? (raw = yes => not structured for autodarts-caller usage)
    # 3) Which voice would you like to use? -> Display of available voices for the selected language (The language is interpreted from the template name)
    # 4) Confirm and start the generation
    # 5) Repeat from step 3)


    # 0)
    provider = setup_environment()

    # 1)
    template_file = choose_template_file() 
    language_code = extract_language_code(template_file)

    # 2) 
    raw_mode = binary_dialog("Do you want to generate in raw mode (Default: no)?: ")

    voices = list_voice_names(provider, language_code)

    # 5)
    while 1:
        # 3)
        voice_name = choose_voice_name(provider, voices)

        # 4)
        confirm = binary_dialog(f"Are you sure you want to proceed (yes/no)? You may face some bill by {provider} (Default: yes): ", default='yes')
        if confirm:
            generate(provider, template_file, language_code, voice_name, raw_mode)

                



